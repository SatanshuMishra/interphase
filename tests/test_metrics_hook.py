import collections
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "metrics_hook.py"
CATALOGUE = ROOT / "metrics" / "catalogue.json"
INHERITED_OUT = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_PLUGIN_ROOT", "PLUGIN_METRICS_DIR", "PLUGIN_METRICS_PARENT", "Q")
ENVELOPE = ("v", "ts", "plugin", "plugin_version", "kind", "event", "run", "parent", "session", "repo")
STAMPED_RUN = re.compile(r"feat-a\.[0-9]{8}T[0-9]{6}Z\.jsonl")
EARLIER_RUN = "feat-a.20261001T100000Z"
SNAPSHOT = 'python3 "{root}/scripts/tree_guard.py" snapshot --repo . --owned "docs/specs/feat-a." --out docs/specs/feat-a.guard.json'

Sandbox = collections.namedtuple("Sandbox", ("repo", "home", "store"))


def make_sandbox(test):
    base = pathlib.Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, str(base), True)
    repo = base / "Sample"
    (repo / ".git").mkdir(parents=True)
    (repo / "docs" / "specs").mkdir(parents=True)
    home = base / "home"
    home.mkdir()
    return Sandbox(repo, home, base / "store")


def environment(sandbox, session="s-1", extra=None):
    inherited = {key: value for key, value in os.environ.items() if key not in INHERITED_OUT}
    chosen = dict(
        inherited,
        HOME=str(sandbox.home),
        PLUGIN_METRICS_DIR=str(sandbox.store),
        CLAUDE_CODE_SESSION_ID=session,
    )
    return dict(chosen, **(extra or {}))


def run_hook(sandbox, payload, session="s-1", extra=None):
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=str(sandbox.repo),
        env=environment(sandbox, session, extra),
        timeout=30,
    )


def base_payload(sandbox, event, tool, tool_input, session="s-1"):
    return {
        "hook_event_name": event,
        "session_id": session,
        "transcript_path": str(sandbox.home / ".claude" / "projects" / "Sample" / (session + ".jsonl")),
        "cwd": str(sandbox.repo),
        "tool_name": tool,
        "tool_input": tool_input,
        "tool_use_id": "toolu_1",
    }


def bash(sandbox, command, stdout="", stderr="", session="s-1"):
    return dict(
        base_payload(sandbox, "PostToolUse", "Bash", {"command": command, "description": "run"}, session),
        tool_response={"stdout": stdout, "stderr": stderr, "interrupted": False, "isImage": False},
    )


def failure(sandbox, command, error, interrupt=False, session="s-1"):
    return dict(
        base_payload(sandbox, "PostToolUseFailure", "Bash", {"command": command, "description": "run"}, session),
        error=error,
        is_interrupt=interrupt,
    )


def ask(sandbox, session="s-1"):
    return dict(
        base_payload(sandbox, "PostToolUse", "AskUserQuestion", {"questions": [{"question": "Approve?"}]}, session),
        tool_response={"answers": {"Approve?": "Yes"}},
    )


def agent(sandbox, subagent_type, text, session="s-1"):
    return dict(
        base_payload(sandbox, "PostToolUse", "Agent", {"subagent_type": subagent_type, "prompt": "review"}, session),
        tool_response={"status": "completed", "content": [{"type": "text", "text": text}]},
    )


def event_folder(sandbox):
    return sandbox.store / "plugin=interphase" / "kind=event" / "repo=Sample"


def event_files(sandbox):
    folder = event_folder(sandbox)
    return sorted(folder.glob("*.jsonl")) if folder.is_dir() else []


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def every_line(sandbox):
    return [line for path in event_files(sandbox) for line in read_lines(path)]


def event_state(sandbox):
    return {path.name: path.read_bytes() for path in event_files(sandbox)}


def store_files(sandbox):
    return sorted(path for path in sandbox.store.rglob("*") if path.is_file()) if sandbox.store.exists() else []


def snapshot_command():
    return SNAPSHOT.format(root=ROOT)


def start_run(test, sandbox, session="s-1"):
    result = run_hook(sandbox, bash(sandbox, snapshot_command(), session=session), session)
    test.assertEqual(result.returncode, 0, result.stderr)
    files = event_files(sandbox)
    test.assertEqual(len(files), 1)
    return files[0]


def newest_line(path):
    return read_lines(path)[-1]


def seed_run(sandbox, run, events, session="s-1"):
    folder = event_folder(sandbox)
    folder.mkdir(parents=True, exist_ok=True)
    lines = [
        dict(
            v=1,
            ts="2026-10-01T10:00:00Z",
            plugin="interphase",
            plugin_version="0.12.0",
            kind="event",
            event=name,
            run=run,
            parent=None,
            session=session,
            repo="Sample",
            **fields
        )
        for name, fields in events
    ]
    path = folder / (run + ".jsonl")
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


def write_spec_file(sandbox, name, value):
    path = sandbox.repo / "docs" / "specs" / name
    text = value if isinstance(value, str) else json.dumps(value)
    path.write_text(text, encoding="utf-8")
    return path


def plain(line):
    return {key: value for key, value in line.items() if key not in ENVELOPE}


def type_matches(entry, value):
    if value is None:
        return True
    kind = entry["type"]
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "enum":
        return value in entry.get("values", [])
    if kind == "object":
        return isinstance(value, dict)
    return kind == "array" and isinstance(value, list)


class SnapshotTest(unittest.TestCase):
    def test_snapshot_starts_a_run(self):
        sandbox = make_sandbox(self)
        result = run_hook(sandbox, bash(sandbox, snapshot_command()))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        files = event_files(sandbox)
        self.assertEqual(len(files), 1)
        self.assertRegex(files[0].name, STAMPED_RUN)
        lines = read_lines(files[0])
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line["event"], "run.start")
        self.assertEqual(line["plugin"], "interphase")
        self.assertEqual(line["slug"], "feat-a")
        self.assertIsNone(line["amends"])
        self.assertIs(line["amending"], False)

    def test_parent_and_session_from_environment(self):
        sandbox = make_sandbox(self)
        result = run_hook(
            sandbox,
            bash(sandbox, snapshot_command()),
            session="s-1",
            extra={"PLUGIN_METRICS_PARENT": "harness/feat-a.20261001T100000Z"},
        )
        self.assertEqual(result.returncode, 0)
        line = read_lines(event_files(sandbox)[0])[0]
        self.assertEqual(line["parent"], "harness/feat-a.20261001T100000Z")
        self.assertEqual(line["session"], "s-1")

    def test_amendment_run_names_the_earlier_run(self):
        sandbox = make_sandbox(self)
        earlier = seed_run(sandbox, EARLIER_RUN, [("run.start", {"slug": "feat-a", "amends": None, "amending": False})])
        before = earlier.read_bytes()
        write_spec_file(sandbox, "feat-a.record.json", {"status": "handed-off", "seams": [], "criteria": [], "steps": []})
        result = run_hook(sandbox, bash(sandbox, snapshot_command()))
        self.assertEqual(result.returncode, 0)
        files = event_files(sandbox)
        self.assertEqual(len(files), 2)
        newer = [path for path in files if path.name != EARLIER_RUN + ".jsonl"][0]
        line = read_lines(newer)[0]
        self.assertEqual(line["event"], "run.start")
        self.assertEqual(line["amends"], "feat-a.20261001T100000Z")
        self.assertIs(line["amending"], True)
        self.assertEqual(earlier.read_bytes(), before)

    def test_catalogue_copied_on_event(self):
        sandbox = make_sandbox(self)
        result = run_hook(sandbox, bash(sandbox, snapshot_command()))
        self.assertEqual(result.returncode, 0)
        copied = sandbox.store / "plugin=interphase" / "catalogue.json"
        with open(copied, encoding="utf-8") as handle:
            stored = json.load(handle)
        with open(CATALOGUE, encoding="utf-8") as handle:
            shipped = json.load(handle)
        self.assertEqual(stored, shipped)

    def test_command_forms_recognised(self):
        forms = (
            ("unquoted", lambda repo: "python3 {}/scripts/tree_guard.py snapshot --repo . --out docs/specs/feat-a.guard.json".format(ROOT), {}),
            ("single quotes", lambda repo: "python3 '{}/scripts/tree_guard.py' snapshot --repo . --out docs/specs/feat-a.guard.json".format(ROOT), {}),
            ("cd first", lambda repo: "cd {} && python3 {}/scripts/tree_guard.py snapshot --repo . --out docs/specs/feat-a.guard.json".format(repo, ROOT), {}),
            ("variables", lambda repo: 'P={}; S=docs/specs; python3 $P/scripts/tree_guard.py snapshot --repo . --owned "$S/feat-a." --out $S/feat-a.guard.json'.format(ROOT), {}),
            ("braced variable", lambda repo: 'P={} && python3 "${{P}}/scripts/tree_guard.py" snapshot --repo . --out docs/specs/feat-a.guard.json'.format(ROOT), {}),
            ("plugin root", lambda repo: 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tree_guard.py" snapshot --repo . --out docs/specs/feat-a.guard.json', {"CLAUDE_PLUGIN_ROOT": str(ROOT)}),
        )
        for label, command, extra in forms:
            with self.subTest(form=label):
                sandbox = make_sandbox(self)
                result = run_hook(sandbox, bash(sandbox, command(sandbox.repo)), extra=extra)
                self.assertEqual(result.returncode, 0)
                self.assertEqual([(line["event"], line["slug"]) for line in every_line(sandbox)], [("run.start", "feat-a")])

    def test_unexpandable_variable_is_not_a_script(self):
        sandbox = make_sandbox(self)
        command = "python3 $Q/scripts/tree_guard.py snapshot --repo . --out docs/specs/feat-a.guard.json"
        result = run_hook(sandbox, bash(sandbox, command))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(event_files(sandbox), [])

    def test_failed_snapshot_starts_no_run(self):
        sandbox = make_sandbox(self)
        result = run_hook(sandbox, failure(sandbox, snapshot_command(), "Exit code 2\ntree_guard.py: error: x"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(event_files(sandbox), [])

    def test_reused_slug_is_not_an_amendment(self):
        sandbox = make_sandbox(self)
        seed_run(sandbox, EARLIER_RUN, [("run.start", {"slug": "feat-a", "amends": None, "amending": False})])
        result = run_hook(sandbox, bash(sandbox, snapshot_command()))
        self.assertEqual(result.returncode, 0)
        newer = [path for path in event_files(sandbox) if path.name != EARLIER_RUN + ".jsonl"]
        self.assertEqual(len(newer), 1)
        line = read_lines(newer[0])[0]
        self.assertIs(line["amending"], False)
        self.assertIsNone(line["amends"])


class ScriptEventsTest(unittest.TestCase):
    def test_record_check_writes_round_recorded(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox)
        write_spec_file(sandbox, "feat-a.record.json", {
            "seams": [{"name": "a"}, {"name": "b"}],
            "criteria": [{"number": "5.1"}, {"number": "5.2"}, {"number": "5.3"}],
            "steps": [{"name": "s"}],
            "rounds": [{"kind": "intent", "questions": 3, "changed": 1}, {"kind": "frontier", "questions": 2, "changed": 0}],
        })
        command = "python3 {}/scripts/check_record.py docs/specs/feat-a.record.json".format(ROOT)
        result = run_hook(sandbox, bash(sandbox, command, stdout="warning: x"))
        self.assertEqual(result.returncode, 0)
        line = newest_line(run)
        self.assertEqual(line["event"], "round.recorded")
        self.assertEqual(
            plain(line),
            {"exit": 0, "errors": 0, "warnings": 1, "seams": 2, "criteria": 3, "steps": 1, "rounds": 2},
        )

    def test_record_without_rounds_counts_null(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox)
        write_spec_file(sandbox, "feat-a.record.json", {"seams": [{"name": "a"}], "criteria": [], "steps": []})
        command = "python3 {}/scripts/check_record.py docs/specs/feat-a.record.json".format(ROOT)
        run_hook(sandbox, bash(sandbox, command, stdout="warning: x"))
        line = newest_line(run)
        self.assertEqual(line["event"], "round.recorded")
        self.assertIsNone(line["rounds"])

    def test_complete_check_writes_steps_checked(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox)
        command = "python3 {}/scripts/check_record.py --complete docs/specs/feat-a.record.json".format(ROOT)
        run_hook(sandbox, bash(sandbox, command))
        line = newest_line(run)
        self.assertEqual(line["event"], "steps.checked")
        self.assertEqual(plain(line), {"exit": 0, "errors": 0, "warnings": 0})

    def test_failed_check_counts_errors(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox)
        command = "python3 {0}/scripts/check_spec.py --template {0}/core/templates/spec-feature.md docs/specs/feat-a.md".format(ROOT)
        run_hook(sandbox, failure(sandbox, command, "Exit code 1\nerror: a\nerror: b\nwarning: c"))
        line = newest_line(run)
        self.assertEqual(line["event"], "spec.checked")
        self.assertEqual(plain(line), {"exit": 1, "errors": 2, "warnings": 1})

    def test_render_items_and_verify_events(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox)
        commands = (
            "python3 {}/scripts/render_record.py --record docs/specs/feat-a.record.json --spec docs/specs/feat-a.md --items docs/specs/feat-a.amend-1.items.json --amendment 1".format(ROOT),
            "python3 {}/scripts/check_items.py --amendment docs/specs/feat-a.amend-1.items.json".format(ROOT),
            "python3 {}/scripts/tree_guard.py verify --repo . --snapshot docs/specs/feat-a.guard.json".format(ROOT),
        )
        for command in commands:
            self.assertEqual(run_hook(sandbox, bash(sandbox, command)).returncode, 0)
        rendered, items, handoff = read_lines(run)[-3:]
        self.assertEqual(rendered["event"], "spec.rendered")
        self.assertEqual(rendered["exit"], 0)
        self.assertEqual(rendered["amendment"], 1)
        self.assertEqual(items["event"], "items.checked")
        self.assertIs(items["amendment"], True)
        self.assertEqual(handoff["event"], "run.handoff")
        self.assertEqual(handoff["exit"], 0)
        self.assertIs(handoff["clean"], True)

    def test_verify_difference_is_not_clean(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox)
        command = "python3 {}/scripts/tree_guard.py verify --repo . --snapshot docs/specs/feat-a.guard.json".format(ROOT)
        run_hook(sandbox, failure(sandbox, command, "Exit code 1\nchanged: a.txt"))
        line = newest_line(run)
        self.assertEqual(line["event"], "run.handoff")
        self.assertEqual(line["exit"], 1)
        self.assertIs(line["clean"], False)

    def test_interrupted_command_has_no_exit(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox)
        command = "python3 {}/scripts/check_items.py docs/specs/feat-a.items.json".format(ROOT)
        run_hook(sandbox, failure(sandbox, command, "Exit code 130\n", interrupt=True))
        line = newest_line(run)
        self.assertEqual(line["event"], "items.checked")
        self.assertIsNone(line["exit"])

    def test_masked_exit_is_null(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox)
        command = 'python3 {}/scripts/tree_guard.py verify --repo . --snapshot docs/specs/feat-a.guard.json; echo "rc=$?"'.format(ROOT)
        run_hook(sandbox, bash(sandbox, command, stdout="error: changed: a.txt\nrc=1"))
        line = newest_line(run)
        self.assertEqual(line["event"], "run.handoff")
        self.assertIsNone(line["exit"])
        self.assertEqual(line["errors"], 1)
        self.assertIs(line["clean"], False)

    def test_several_scripts_in_one_command(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox)
        command = (
            'P={}; python3 $P/scripts/check_spec.py --template $P/core/templates/spec-feature.md docs/specs/feat-a.md; '
            'echo "spec rc=$?"; python3 $P/scripts/check_items.py docs/specs/feat-a.items.json'
        ).format(ROOT)
        run_hook(sandbox, bash(sandbox, command, stdout="warning: a\nspec rc=0"))
        spec, items = read_lines(run)[-2:]
        self.assertEqual(spec["event"], "spec.checked")
        self.assertEqual(items["event"], "items.checked")
        for line in (spec, items):
            with self.subTest(event=line["event"]):
                self.assertIsNone(line["exit"])
                self.assertIsNone(line["errors"])
                self.assertIsNone(line["warnings"])


class NothingWrittenTest(unittest.TestCase):
    def test_interphase_script_with_a_run_is_recorded(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox)
        before = len(read_lines(run))
        command = "python3 {}/scripts/check_items.py docs/specs/feat-a.items.json".format(ROOT)
        result = run_hook(sandbox, bash(sandbox, command))
        self.assertEqual(result.stdout, "")
        lines = read_lines(run)
        self.assertEqual(len(lines), before + 1)
        self.assertEqual(lines[-1]["event"], "items.checked")

    def test_unrelated_calls_write_nothing(self):
        sandbox = make_sandbox(self)
        start_run(self, sandbox)
        before = event_state(sandbox)
        read_payload = dict(
            base_payload(sandbox, "PostToolUse", "Read", {"file_path": str(sandbox.repo / "docs" / "specs" / "feat-a.md")}),
            tool_response={"type": "text", "file": {"content": "x"}},
        )
        for payload in (read_payload, bash(sandbox, "ls docs/specs", stdout="feat-a.md")):
            with self.subTest(tool=payload["tool_name"]):
                result = run_hook(sandbox, payload)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(event_state(sandbox), before)

    def test_scripts_from_another_folder_ignored(self):
        sandbox = make_sandbox(self)
        start_run(self, sandbox)
        before = event_state(sandbox)
        run_hook(sandbox, bash(sandbox, "python3 /tmp/elsewhere/scripts/check_record.py docs/specs/feat-a.record.json"))
        self.assertEqual(event_state(sandbox), before)

    def test_unbalanced_quoting_writes_nothing(self):
        sandbox = make_sandbox(self)
        start_run(self, sandbox)
        before = event_state(sandbox)
        command = 'python3 "{}/scripts/check_record.py docs/specs/feat-a.record.json'.format(ROOT)
        result = run_hook(sandbox, bash(sandbox, command))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(event_state(sandbox), before)

    def test_script_before_any_run_writes_nothing(self):
        sandbox = make_sandbox(self)
        command = "python3 {}/scripts/check_record.py docs/specs/feat-a.record.json".format(ROOT)
        result = run_hook(sandbox, bash(sandbox, command))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(store_files(sandbox), [])

    def test_bad_stdin_exits_zero(self):
        for stdin in ("not json", ""):
            with self.subTest(stdin=stdin):
                sandbox = make_sandbox(self)
                result = run_hook(sandbox, stdin)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(store_files(sandbox), [])

    def test_calls_without_an_open_run_write_nothing(self):
        sandbox = make_sandbox(self)
        seed_run(
            sandbox,
            EARLIER_RUN,
            [
                ("run.start", {"slug": "feat-a", "amends": None, "amending": False}),
                ("run.handoff", {"exit": 0, "errors": 0, "clean": True}),
            ],
            session="s-1",
        )
        before = event_state(sandbox)
        for payload in (ask(sandbox, "s-1"), agent(sandbox, "interphase:spec-reviewer", "Status: Approved\n", "s-1")):
            with self.subTest(tool=payload["tool_name"]):
                result = run_hook(sandbox, payload)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(event_state(sandbox), before)

    def test_other_agents_write_nothing(self):
        sandbox = make_sandbox(self)
        start_run(self, sandbox, session="s-1")
        before = event_state(sandbox)
        run_hook(sandbox, agent(sandbox, "general-purpose", "Status: Approved\n", "s-1"))
        self.assertEqual(event_state(sandbox), before)

    def test_unexpandable_variable_writes_nothing(self):
        sandbox = make_sandbox(self)
        start_run(self, sandbox)
        before = event_state(sandbox)
        run_hook(sandbox, bash(sandbox, "python3 $Q/scripts/check_record.py docs/specs/feat-a.record.json"))
        self.assertEqual(event_state(sandbox), before)


class SessionEventsTest(unittest.TestCase):
    def test_readback_recorded(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox, session="s-1")
        run_hook(sandbox, ask(sandbox, "s-1"))
        self.assertEqual(newest_line(run)["event"], "readback.asked")

    def test_review_issues_counted(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox, session="s-1")
        text = "Status: Issues found\n\nI checked the date arithmetic in every example.\n- Section 4: a\n\n- Step b: c\nThat is all.\n"
        run_hook(sandbox, agent(sandbox, "interphase:spec-reviewer", text, "s-1"))
        line = newest_line(run)
        self.assertEqual(line["event"], "review.done")
        self.assertIs(line["approved"], False)
        self.assertEqual(line["issues"], 2)

    def test_review_approved(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox, session="s-1")
        text = "Status: Approved\n\nThe spec would build the right thing.\n"
        run_hook(sandbox, agent(sandbox, "interphase:spec-reviewer", text, "s-1"))
        line = newest_line(run)
        self.assertEqual(line["event"], "review.done")
        self.assertIs(line["approved"], True)
        self.assertEqual(line["issues"], 0)

    def test_review_without_status(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox, session="s-1")
        run_hook(sandbox, agent(sandbox, "interphase:spec-reviewer", "I could not read the items file.", "s-1"))
        line = newest_line(run)
        self.assertEqual(line["event"], "review.done")
        self.assertIsNone(line["approved"])
        self.assertIsNone(line["issues"])


class UnwritableStoreTest(unittest.TestCase):
    def test_unwritable_store_warns_on_stderr(self):
        sandbox = make_sandbox(self)
        blocker = sandbox.home / "store-file"
        blocker.write_text("not a folder\n", encoding="utf-8")
        result = run_hook(sandbox, bash(sandbox, snapshot_command()), extra={"PLUGIN_METRICS_DIR": str(blocker)})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("metrics not written: "), result.stderr)


class DescribedFieldsTest(unittest.TestCase):
    def test_every_event_field_is_described(self):
        sandbox = make_sandbox(self)
        run = start_run(self, sandbox, session="s-1")
        write_spec_file(sandbox, "feat-a.record.json", {
            "seams": [{"name": "a"}],
            "criteria": [{"number": "5.1"}],
            "steps": [{"name": "s"}],
            "rounds": [{"kind": "intent", "questions": 3, "changed": 1}],
        })
        payloads = (
            bash(sandbox, "python3 {}/scripts/check_record.py docs/specs/feat-a.record.json".format(ROOT), stdout="warning: x"),
            bash(sandbox, "python3 {}/scripts/check_record.py --complete docs/specs/feat-a.record.json".format(ROOT)),
            ask(sandbox, "s-1"),
            bash(sandbox, "python3 {}/scripts/render_record.py --record docs/specs/feat-a.record.json --spec docs/specs/feat-a.md --items docs/specs/feat-a.items.json".format(ROOT)),
            failure(sandbox, "python3 {0}/scripts/check_spec.py --template {0}/core/templates/spec-feature.md docs/specs/feat-a.md".format(ROOT), "Exit code 1\nerror: a"),
            bash(sandbox, "python3 {}/scripts/check_items.py docs/specs/feat-a.items.json".format(ROOT)),
            agent(sandbox, "interphase:spec-reviewer", "Status: Issues found\n- Section 4: a\n", "s-1"),
            bash(sandbox, "python3 {}/scripts/tree_guard.py verify --repo . --snapshot docs/specs/feat-a.guard.json".format(ROOT)),
        )
        for payload in payloads:
            self.assertEqual(run_hook(sandbox, payload).returncode, 0)
        with open(CATALOGUE, encoding="utf-8") as handle:
            events = json.load(handle)["events"]
        lines = read_lines(run)
        self.assertEqual(
            [line["event"] for line in lines],
            ["run.start", "round.recorded", "steps.checked", "readback.asked", "spec.rendered", "spec.checked", "items.checked", "review.done", "run.handoff"],
        )
        for line in lines:
            described = events[line["event"]]["fields"]
            for key, value in plain(line).items():
                with self.subTest(event=line["event"], field=key):
                    self.assertIn(key, described)
                    self.assertTrue(type_matches(described[key], value), value)


if __name__ == "__main__":
    unittest.main()
