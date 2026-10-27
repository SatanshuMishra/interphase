import collections
import datetime
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "metrics_hook.py"
WRITER = ROOT / "scripts" / "metrics_writer.py"
SUMMARY = ROOT / "scripts" / "metrics_summary.py"
CATALOGUE = ROOT / "metrics" / "catalogue.json"
INHERITED_OUT = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_PLUGIN_ROOT", "PLUGIN_METRICS_DIR", "PLUGIN_METRICS_PARENT")
ENVELOPE = ("v", "ts", "plugin", "plugin_version", "kind", "event", "run", "parent", "session", "repo")
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
RUN_STAMP_FORMAT = "%Y%m%dT%H%M%SZ"
START = datetime.datetime(2026, 10, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
SLOW_BUILD_MESSAGES = 300000
SNAPSHOT = 'python3 "{root}/scripts/tree_guard.py" snapshot --repo . --owned "docs/specs/feat-a." --out docs/specs/feat-a.guard.json'
CHECK_RECORD = "python3 {root}/scripts/check_record.py docs/specs/feat-a.record.json"

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


def environment(sandbox, session="s-1"):
    inherited = {key: value for key, value in os.environ.items() if key not in INHERITED_OUT}
    return dict(inherited, HOME=str(sandbox.home), PLUGIN_METRICS_DIR=str(sandbox.store), CLAUDE_CODE_SESSION_ID=session)


def at(seconds):
    return START + datetime.timedelta(seconds=seconds)


def stamp(moment):
    return moment.strftime(TIMESTAMP_FORMAT)


def transcript_stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + "%03dZ" % (moment.microsecond // 1000)


def run_of(slug, moment=START):
    return slug + "." + moment.strftime(RUN_STAMP_FORMAT)


def folder(sandbox, kind):
    return sandbox.store / "plugin=interphase" / ("kind=" + kind) / "repo=Sample"


def write_events(sandbox, run, events):
    target = folder(sandbox, "event")
    target.mkdir(parents=True, exist_ok=True)
    lines = [
        dict(
            v=1,
            ts=stamp(moment),
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
        for moment, name, fields, session in events
    ]
    path = target / (run + ".jsonl")
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


def event(seconds, name, fields=None, session="s-1"):
    return at(seconds), name, fields or {}, session


def write_spec_file(sandbox, name, value):
    text = value if isinstance(value, str) else json.dumps(value)
    (sandbox.repo / "docs" / "specs" / name).write_text(text, encoding="utf-8")


def build(sandbox, run, slug="feat-a"):
    return subprocess.run(
        [sys.executable, str(SUMMARY), "--repo", str(sandbox.repo), "--slug", slug, "--run", run],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=environment(sandbox),
        timeout=120,
    )


def start_build(test, sandbox, run, slug="feat-a"):
    process = subprocess.Popen(
        [sys.executable, str(SUMMARY), "--repo", str(sandbox.repo), "--slug", slug, "--run", run],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=environment(sandbox),
    )
    test.addCleanup(stopped, process)
    return process


def stopped(process):
    if process.poll() is None:
        process.kill()
        process.communicate()


def load_writer():
    spec = importlib.util.spec_from_file_location("metrics_writer_under_test", str(WRITER))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summary_path(sandbox, run):
    return folder(sandbox, "summary") / (run + ".json")


def read_summary(sandbox, run):
    lines = summary_path(sandbox, run).read_text(encoding="utf-8").splitlines()
    return json.loads(lines[0])


def built(test, sandbox, run, events, slug="feat-a"):
    write_events(sandbox, run, events)
    result = build(sandbox, run, slug)
    test.assertEqual(result.returncode, 0, result.stderr)
    test.assertEqual(result.stdout, "")
    return read_summary(sandbox, run)


def usage(input_tokens=0, output_tokens=0, **extra):
    return dict({"input_tokens": input_tokens, "output_tokens": output_tokens, "cache_read_input_tokens": 0}, **extra)


def assistant(moment, model="claude-opus-5-5", tokens=None, message_id=None, content=None):
    identifier = message_id or "msg_" + transcript_stamp(moment)
    return {
        "type": "assistant",
        "uuid": "u-" + identifier,
        "timestamp": transcript_stamp(moment),
        "message": {
            "id": identifier,
            "model": model,
            "role": "assistant",
            "content": content or [{"type": "text", "text": "ok"}],
            "usage": tokens or usage(),
        },
    }


def typed(moment, text="next", origin="human", **extra):
    described = {"origin": {"kind": origin}} if origin is not None else {}
    return dict(
        {"type": "user", "uuid": "t-" + transcript_stamp(moment), "timestamp": transcript_stamp(moment), "message": {"role": "user", "content": text}},
        **described,
        **extra
    )


def tool_result(moment, tool_use_id):
    return {
        "type": "user",
        "uuid": "r-" + transcript_stamp(moment),
        "timestamp": transcript_stamp(moment),
        "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": "done"}]},
    }


def write_transcript(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def main_transcript(sandbox, session):
    return sandbox.home / ".claude" / "projects" / "-tmp-Sample" / (session + ".jsonl")


def agent_transcript(sandbox, session, agent_id, agent_type, records):
    path = sandbox.home / ".claude" / "projects" / "-tmp-Sample" / session / "subagents" / ("agent-" + agent_id + ".jsonl")
    write_transcript(path, records)
    path.with_name("agent-" + agent_id + ".meta.json").write_text(json.dumps({"agentType": agent_type}), encoding="utf-8")


def spend_run(test, sandbox, records, sessions=("s-1",)):
    write_transcript(main_transcript(sandbox, sessions[0]), records)
    run = run_of("feat-a")
    events = [event(0, "run.start", {"slug": "feat-a", "amends": None, "amending": False}, sessions[0])] + [
        event(600, "round.recorded", {}, session) for session in sessions
    ]
    return built(test, sandbox, run, events)


def hook_payload(sandbox, command, session="s-1"):
    return {
        "hook_event_name": "PostToolUse",
        "session_id": session,
        "transcript_path": str(main_transcript(sandbox, session)),
        "cwd": str(sandbox.repo),
        "tool_name": "Bash",
        "tool_input": {"command": command, "description": "run"},
        "tool_use_id": "toolu_1",
        "tool_response": {"stdout": "", "stderr": "", "interrupted": False, "isImage": False},
    }


def run_hook(sandbox, payload, session="s-1"):
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=str(sandbox.repo),
        env=environment(sandbox, session),
        timeout=30,
    )


def wait_for(path, limit):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        if path.exists():
            return True
        time.sleep(0.2)
    return path.exists()


def slow_run(sandbox):
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    started = now - datetime.timedelta(hours=1)
    run = run_of("feat-a", started)
    write_events(sandbox, run, [(started, "run.start", {"slug": "feat-a", "amends": None, "amending": False}, "s-1")])
    record = json.dumps(assistant(started + datetime.timedelta(seconds=120), tokens=usage(10, 20), message_id="msg_NUMBER"))
    transcript = main_transcript(sandbox, "s-1")
    transcript.parent.mkdir(parents=True)
    transcript.write_text(
        "".join(record.replace("NUMBER", str(index)) + "\n" for index in range(SLOW_BUILD_MESSAGES)),
        encoding="utf-8",
    )
    return run


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


def undescribed(fields, value, where):
    found = tuple(
        problem
        for key, item in value.items()
        for problem in (
            ((where + key + " is not described",) if key not in fields else described_value(fields[key], item, where + key))
        )
    )
    return found


def described_value(entry, value, where):
    if not type_matches(entry, value):
        return (where + " has the wrong type",)
    if isinstance(value, dict) and "fields" in entry:
        return undescribed(entry["fields"], value, where + ".")
    if isinstance(value, list) and "items" in entry:
        return tuple(problem for item in value for problem in described_value(entry["items"], item, where + "[]"))
    return ()


class SummaryBuildTest(unittest.TestCase):
    def test_event_starts_summary(self):
        sandbox = make_sandbox(self)
        for command in (SNAPSHOT, CHECK_RECORD):
            result = run_hook(sandbox, hook_payload(sandbox, command.format(root=ROOT)))
            self.assertEqual(result.returncode, 0, result.stderr)
        runs = sorted(folder(sandbox, "event").glob("feat-a.*.jsonl"))
        self.assertEqual(len(runs), 1)
        target = summary_path(sandbox, runs[0].name[:-len(".jsonl")])
        self.assertTrue(wait_for(target, 30))
        lines = target.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        line = json.loads(lines[0])
        self.assertEqual(line["event"], "run.summary")
        self.assertEqual(line["slug"], "feat-a")
        self.assertEqual(line["spend_scope"], "own")

    def test_hook_returns_before_summary(self):
        sandbox = make_sandbox(self)
        run = slow_run(sandbox)
        result = run_hook(sandbox, hook_payload(sandbox, CHECK_RECORD.format(root=ROOT)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(summary_path(sandbox, run).exists())
        self.assertTrue(wait_for(summary_path(sandbox, run), 60))

    def test_older_build_does_not_replace_newer(self):
        sandbox = make_sandbox(self)
        run = run_of("feat-a")
        write_events(sandbox, run, [event(0, "run.start", {"slug": "feat-a", "amends": None, "amending": False})])
        later = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        target = summary_path(sandbox, run)
        target.parent.mkdir(parents=True)
        stored = json.dumps({"v": 1, "ts": stamp(later), "plugin": "interphase", "kind": "summary", "event": "run.summary", "run": run, "slug": "feat-a"}) + "\n"
        target.write_text(stored, encoding="utf-8")
        before = target.read_bytes()
        result = build(sandbox, run)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), before)

    def test_build_skips_when_events_changed(self):
        sandbox = make_sandbox(self)
        run = slow_run(sandbox)
        process = start_build(self, sandbox, run)
        with self.assertRaises(subprocess.TimeoutExpired):
            process.wait(timeout=1.0)
        warning = load_writer().append_event(
            "interphase", "0.13.0", "Sample", run, "steps.checked", {"exit": 0, "errors": 0, "warnings": 0},
            environ=environment(sandbox),
        )
        self.assertIsNone(warning)
        out, err = process.communicate(timeout=120)
        self.assertEqual(process.returncode, 0, err)
        self.assertEqual(out, "")
        self.assertFalse(summary_path(sandbox, run).exists())

    def test_overlapping_builds_leave_the_newer_summary(self):
        sandbox = make_sandbox(self)
        run = slow_run(sandbox)
        older = start_build(self, sandbox, run)
        with self.assertRaises(subprocess.TimeoutExpired):
            older.wait(timeout=1.0)
        warning = load_writer().append_event(
            "interphase", "0.13.0", "Sample", run, "run.handoff", {"exit": 0, "errors": 0, "clean": True},
            environ=environment(sandbox),
        )
        self.assertIsNone(warning)
        newer = start_build(self, sandbox, run)
        results = tuple((process, process.communicate(timeout=120)) for process in (older, newer))
        for process, (_, err) in results:
            self.assertEqual(process.returncode, 0, err)
        self.assertEqual(read_summary(sandbox, run)["status"], "handed-off")


START_EVENT = event(0, "run.start", {"slug": "feat-a", "amends": None, "amending": False})


class SummaryCountsTest(unittest.TestCase):
    def test_interview_counts_from_rounds(self):
        sandbox = make_sandbox(self)
        write_spec_file(sandbox, "feat-a.record.json", {
            "seams": [],
            "criteria": [],
            "steps": [],
            "rounds": [
                {"kind": "intent", "questions": 3, "changed": 1},
                {"kind": "frontier", "questions": 5, "changed": 0},
                {"kind": "frontier", "questions": 2, "changed": 2},
            ],
        })
        line = built(self, sandbox, run_of("feat-a"), [START_EVENT])
        self.assertEqual(line["rounds"], 3)
        self.assertEqual(line["questions"], 10)
        self.assertEqual(line["changed"], 3)
        self.assertEqual(line["recommended"], 7)

    def test_rounds_absent_is_null(self):
        sandbox = make_sandbox(self)
        write_spec_file(sandbox, "feat-a.record.json", {"seams": [], "criteria": [], "steps": []})
        line = built(self, sandbox, run_of("feat-a"), [START_EVENT])
        for key in ("rounds", "questions", "changed", "recommended"):
            with self.subTest(key=key):
                self.assertIsNone(line[key])

    def test_record_counts(self):
        sandbox = make_sandbox(self)
        write_spec_file(sandbox, "feat-a.record.json", {
            "seams": [{"name": "a"}, {"name": "b"}],
            "criteria": [
                {"number": "5.1", "tests": [{"name": "t1"}, {"name": "t2"}], "unproven": "only on a phone"},
                {"number": "5.2", "tests": [{"name": "t3"}], "varies": "output"},
                {"number": "5.3", "tests": [{"name": "t4"}, {"name": "t5"}], "case_table": "refusal"},
            ],
            "steps": [
                {"name": "one", "msp": "a", "assumptions": ["x (relies on I1)"]},
                {"name": "two", "msp": "a", "assumptions": []},
                {"name": "three", "msp": "b"},
            ],
        })
        line = built(self, sandbox, run_of("feat-a"), [START_EVENT])
        self.assertEqual(
            {key: line[key] for key in ("seams", "criteria", "tests", "unproven", "varying", "case_tables", "steps", "msps", "steps_with_assumptions")},
            {"seams": 2, "criteria": 3, "tests": 5, "unproven": 1, "varying": 1, "case_tables": 1, "steps": 3, "msps": 2, "steps_with_assumptions": 1},
        )

    def test_spec_header_and_assumptions(self):
        sandbox = make_sandbox(self)
        write_spec_file(sandbox, "feat-a.md", "\n".join((
            "# A feature",
            "",
            "Pathway: bug.",
            "",
            "Lane: brief.",
            "",
            "## 4. Decisions",
            "",
            "### Assumptions",
            "",
            "- The cache is local (relies on I1).",
            "- The owner reads it weekly (relies on I1, I3).",
            "- Nothing else writes there (relies on I2).",
            "",
            "## 5. Test seams",
            "",
        )))
        line = built(self, sandbox, run_of("feat-a"), [START_EVENT])
        self.assertEqual(line["pathway"], "bug")
        self.assertEqual(line["lane"], "brief")
        self.assertEqual(line["assumptions"], 3)
        self.assertEqual(
            line["assumptions_by_intent"],
            [{"intent": "I1", "count": 2}, {"intent": "I2", "count": 1}, {"intent": "I3", "count": 1}],
        )

    def test_unattended_and_decisions(self):
        sandbox = make_sandbox(self)
        write_spec_file(sandbox, "feat-a.decisions.md", "\n".join((
            "# Decisions: feat-a",
            "",
            "## Intent",
            "",
            "- I1 Goal: a cache for the report (inferred)",
            "- I2 Why: the report is slow (inferred)",
            "- I3 Success: the report opens in a second (inferred)",
            "",
            "## Decisions",
            "",
            "- one",
            "- two",
            "- three",
            "- four",
            "",
        )))
        line = built(self, sandbox, run_of("feat-a"), [START_EVENT])
        self.assertIs(line["attended"], False)
        self.assertEqual(line["intent_lines"], 3)
        self.assertEqual(line["decisions"], 4)

    def test_readback_and_status(self):
        sandbox = make_sandbox(self)
        first = built(self, sandbox, run_of("feat-a", at(0)), [
            START_EVENT,
            event(10, "readback.asked"),
            event(20, "readback.asked"),
            event(30, "spec.rendered", {"exit": 0, "amendment": None}),
            event(40, "run.handoff", {"exit": 0, "errors": 0, "clean": True}),
        ])
        second = built(self, sandbox, run_of("feat-a", at(100)), [
            event(100, "run.start", {"slug": "feat-a", "amends": None, "amending": False}),
            event(110, "readback.asked"),
        ])
        third = built(self, sandbox, run_of("feat-a", at(200)), [
            event(200, "run.start", {"slug": "feat-a", "amends": None, "amending": False}),
            event(210, "run.handoff", {"exit": 1, "errors": 0, "clean": False}),
        ])
        self.assertEqual(first["readbacks"], 2)
        self.assertIs(first["approved"], True)
        self.assertEqual(first["status"], "handed-off")
        self.assertIs(second["approved"], False)
        self.assertEqual(second["status"], "in-progress")
        self.assertEqual(third["status"], "guard-difference")

    def test_checks_first_and_last(self):
        sandbox = make_sandbox(self)
        line = built(self, sandbox, run_of("feat-a"), [
            START_EVENT,
            event(10, "spec.checked", {"exit": 1, "errors": 2, "warnings": 1}),
            event(20, "spec.checked", {"exit": 0, "errors": 0, "warnings": 0}),
        ])
        self.assertIn({"check": "spec", "runs": 2, "first_errors": 2, "first_warnings": 1, "last_errors": 0}, line["checks"])
        self.assertEqual([entry for entry in line["checks"] if entry["check"] == "items"], [])

    def test_review_amendment_and_sessions(self):
        sandbox = make_sandbox(self)
        write_spec_file(sandbox, "feat-a.record.json", {
            "seams": [],
            "criteria": [],
            "steps": [{"name": "one", "amendment": 1}, {"name": "two", "amendment": 2}],
        })
        line = built(self, sandbox, run_of("feat-a"), [
            event(0, "run.start", {"slug": "feat-a", "amends": "feat-a.20261001T100000Z", "amending": True}, "s-1"),
            event(10, "review.done", {"approved": False, "issues": 2}, "s-2"),
        ])
        self.assertIs(line["review_approved"], False)
        self.assertEqual(line["review_issues"], 2)
        self.assertEqual(line["amendment"], 2)
        self.assertEqual(line["amends"], "feat-a.20261001T100000Z")
        self.assertEqual(line["sessions"], 2)

    def test_missing_files_are_null(self):
        sandbox = make_sandbox(self)
        line = built(self, sandbox, run_of("feat-a"), [START_EVENT, event(10, "readback.asked")])
        for key in ("pathway", "lane", "attended", "intent_lines", "decisions", "seams", "criteria", "steps", "assumptions"):
            with self.subTest(key=key):
                self.assertIsNone(line[key])


class SummaryRepositoryFilesTest(unittest.TestCase):
    def test_spec_files_that_are_not_plain_files_inside_the_repository_are_skipped(self):
        sandbox = make_sandbox(self)
        specs = sandbox.repo / "docs" / "specs"
        os.mkfifo(str(specs / "feat-a.md"))
        outside = sandbox.home / "elsewhere.record.json"
        outside.write_text(json.dumps({"seams": [{}], "criteria": [], "steps": []}), encoding="utf-8")
        (specs / "feat-a.record.json").symlink_to(outside)
        write_spec_file(sandbox, "feat-a.decisions.md", "## Intent\n\n- I1 Goal: x\n" + "x" * (4 * 1024 * 1024))
        line = built(self, sandbox, run_of("feat-a"), [START_EVENT])
        self.assertEqual(
            (line["pathway"], line["lane"], line["assumptions"], line["seams"], line["intent_lines"]),
            (None, None, None, None, None),
        )

    def test_snapshot_with_a_record_that_is_not_a_plain_file_still_starts_a_run(self):
        sandbox = make_sandbox(self)
        os.mkfifo(str(sandbox.repo / "docs" / "specs" / "feat-a.record.json"))
        result = run_hook(sandbox, hook_payload(sandbox, SNAPSHOT.format(root=ROOT)))
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        runs = sorted(folder(sandbox, "event").glob("feat-a.*.jsonl"))
        self.assertEqual(len(runs), 1)
        start = json.loads(runs[0].read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual((start["event"], start["amending"]), ("run.start", False))


class SummaryTimeTest(unittest.TestCase):
    def test_phase_spans_attended(self):
        sandbox = make_sandbox(self)
        line = built(self, sandbox, run_of("feat-a"), [
            START_EVENT,
            event(600, "round.recorded", {"exit": 0, "errors": 0, "warnings": 0}),
            event(900, "round.recorded", {"exit": 0, "errors": 0, "warnings": 0}),
            event(1800, "steps.checked", {"exit": 0, "errors": 0, "warnings": 0}),
            event(2000, "readback.asked"),
            event(3000, "spec.rendered", {"exit": 0, "amendment": None}),
            event(3300, "spec.checked", {"exit": 0, "errors": 0, "warnings": 0}),
            event(3600, "review.done", {"approved": True, "issues": 0}),
            event(3700, "run.handoff", {"exit": 0, "errors": 0, "clean": True}),
        ])
        self.assertEqual(line["lead_seconds"], 3700)
        self.assertEqual(line["phases"], [
            {"phase": "ground", "seconds": 600},
            {"phase": "interview", "seconds": 1200},
            {"phase": "read-back", "seconds": 200},
            {"phase": "write", "seconds": 1000},
            {"phase": "review", "seconds": 600},
            {"phase": "hand-off", "seconds": 100},
        ])

    def test_phase_spans_unattended(self):
        sandbox = make_sandbox(self)
        line = built(self, sandbox, run_of("feat-a"), [
            START_EVENT,
            event(1200, "steps.checked", {"exit": 0, "errors": 0, "warnings": 0}),
            event(2000, "spec.rendered", {"exit": 0, "amendment": None}),
            event(2100, "items.checked", {"exit": 0, "errors": 0, "warnings": 0, "amendment": False}),
            event(2200, "run.handoff", {"exit": 0, "errors": 0, "clean": True}),
        ])
        self.assertEqual(line["phases"], [
            {"phase": "ground", "seconds": 1200},
            {"phase": "write", "seconds": 800},
            {"phase": "review", "seconds": 100},
            {"phase": "hand-off", "seconds": 100},
        ])

    def test_wait_seconds_from_transcript(self):
        sandbox = make_sandbox(self)
        write_transcript(main_transcript(sandbox, "s-1"), [
            assistant(at(10)),
            typed(at(70)),
            assistant(at(80)),
            tool_result(at(90), "toolu_read"),
            assistant(at(100)),
            typed(at(400)),
        ])
        line = built(self, sandbox, run_of("feat-a"), [START_EVENT, event(600, "steps.checked", {"exit": 0, "errors": 0, "warnings": 0})])
        self.assertEqual(line["wait_seconds"], 360)

    def test_non_typed_user_records_do_not_count_as_wait(self):
        written_by_others = {
            "task notification": typed(at(70), "<task-notification>done</task-notification>", origin="task-notification"),
            "compaction summary": typed(at(70), "This session is being continued", origin=None, isCompactSummary=True, isVisibleInTranscriptOnly=True),
            "reminder only": typed(at(70), "<system-reminder>note</system-reminder>", origin=None),
            "local command output": typed(at(70), "<local-command-stdout>ok</local-command-stdout>", origin=None),
            "interrupt marker": typed(at(70), "[Request interrupted by user]", origin=None),
            "plugin prompt": typed(at(70), "/compact", origin="plugin"),
        }
        for name, record in written_by_others.items():
            with self.subTest(record=name):
                sandbox = make_sandbox(self)
                write_transcript(main_transcript(sandbox, "s-1"), [assistant(at(10)), record])
                line = built(self, sandbox, run_of("feat-a"), [START_EVENT, event(600, "steps.checked", {"exit": 0, "errors": 0, "warnings": 0})])
                self.assertEqual(line["wait_seconds"], 0)
        sandbox = make_sandbox(self)
        write_transcript(main_transcript(sandbox, "s-1"), [assistant(at(10)), typed(at(70))])
        line = built(self, sandbox, run_of("feat-a"), [START_EVENT, event(600, "steps.checked", {"exit": 0, "errors": 0, "warnings": 0})])
        self.assertEqual(line["wait_seconds"], 60)

    def test_readback_answer_counts_as_wait(self):
        sandbox = make_sandbox(self)
        question = [{"type": "tool_use", "id": "toolu_ask", "name": "AskUserQuestion", "input": {"questions": []}}]
        write_transcript(main_transcript(sandbox, "s-1"), [
            assistant(at(10), content=question),
            tool_result(at(130), "toolu_ask"),
        ])
        line = built(self, sandbox, run_of("feat-a"), [START_EVENT, event(600, "readback.asked")])
        self.assertEqual(line["wait_seconds"], 120)


class SummarySpendTest(unittest.TestCase):
    def test_spend_counts_window_only(self):
        sandbox = make_sandbox(self)
        line = spend_run(self, sandbox, [
            assistant(at(-60), tokens=usage(500, 500)),
            assistant(at(300), tokens=usage(1000, 2000)),
            assistant(at(660), tokens=usage(700, 700)),
        ])
        self.assertEqual(line["tokens"], {"input": 1000, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0, "output": 2000})
        self.assertEqual(line["usd"], 0.044)
        self.assertEqual(line["prices_date"], "2026-10-06")

    def test_duplicate_message_counted_once(self):
        sandbox = make_sandbox(self)
        message = assistant(at(300), tokens=usage(1000, 2000), message_id="msg_same")
        line = spend_run(self, sandbox, [message, message])
        rows = [row for row in line["models"] if (row["agent"], row["model"]) == ("main session", "claude-opus-5-5")]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["messages"], 1)

    def test_own_agents_only(self):
        sandbox = make_sandbox(self)
        agent_transcript(sandbox, "s-1", "a1", "interphase:spec-reviewer", [assistant(at(200), tokens=usage(10, 10), message_id="msg_review")])
        agent_transcript(sandbox, "s-1", "a2", "general-purpose", [assistant(at(250), tokens=usage(10, 10), message_id="msg_other")])
        line = spend_run(self, sandbox, [assistant(at(300), tokens=usage(1000, 2000))])
        self.assertEqual(sorted(row["agent"] for row in line["models"]), ["interphase:spec-reviewer", "main session"])

    def test_unpriced_model_makes_usd_null(self):
        sandbox = make_sandbox(self)
        line = spend_run(self, sandbox, [assistant(at(300), model="claude-unknown-1", tokens=usage(1000, 2000))])
        self.assertIsNone(line["usd"])
        self.assertEqual(line["unpriced"], ["claude-unknown-1"])
        row = [row for row in line["models"] if row["model"] == "claude-unknown-1"][0]
        self.assertIsNone(row["usd"])

    def test_spend_over_two_sessions(self):
        sandbox = make_sandbox(self)
        write_transcript(main_transcript(sandbox, "s-2"), [assistant(at(320), model="claude-sonnet-5-5", tokens=usage(1000000, 0), message_id="msg_two")])
        line = spend_run(
            self,
            sandbox,
            [assistant(at(300), model="claude-sonnet-5-5", tokens=usage(1000000, 0), message_id="msg_one")],
            sessions=("s-1", "s-2"),
        )
        self.assertEqual(line["tokens"]["input"], 2000000)
        self.assertEqual(line["usd"], 4)

    def test_cache_write_kinds(self):
        sandbox = make_sandbox(self)
        line = spend_run(self, sandbox, [
            assistant(at(300), tokens=usage(cache_creation={"ephemeral_5m_input_tokens": 10, "ephemeral_1h_input_tokens": 20}, cache_read_input_tokens=30), message_id="msg_split"),
            assistant(at(310), tokens=usage(cache_creation_input_tokens=40), message_id="msg_flat"),
        ])
        self.assertEqual(line["tokens"]["cache_write_5m"], 50)
        self.assertEqual(line["tokens"]["cache_write_1h"], 20)
        self.assertEqual(line["tokens"]["cache_read"], 30)

    def test_synthetic_records_left_out(self):
        sandbox = make_sandbox(self)
        line = spend_run(self, sandbox, [
            assistant(at(300), tokens=usage(1000, 0), message_id="msg_real"),
            assistant(at(310), model="<synthetic>", tokens=usage(0, 0), message_id="msg_synthetic"),
        ])
        self.assertEqual(line["usd"], 0.004)
        self.assertEqual(line["unpriced"], [])
        self.assertEqual([row for row in line["models"] if row["model"] == "<synthetic>"], [])

    def test_message_after_last_event_not_counted(self):
        sandbox = make_sandbox(self)
        line = spend_run(self, sandbox, [assistant(at(600.5), tokens=usage(1000, 2000))])
        self.assertEqual(line["models"], [])
        self.assertEqual(line["tokens"], {"input": 0, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0, "output": 0})


class SummaryDescribedTest(unittest.TestCase):
    def test_every_summary_field_is_described(self):
        sandbox = make_sandbox(self)
        write_spec_file(sandbox, "feat-a.record.json", {
            "seams": [{"name": "a"}],
            "criteria": [{"number": "5.1", "tests": [{"name": "t"}]}],
            "steps": [{"name": "s", "msp": "a", "assumptions": ["x (relies on I1)"]}],
            "rounds": [{"kind": "intent", "questions": 3, "changed": 1}],
        })
        write_spec_file(sandbox, "feat-a.md", "Pathway: feature.\n\n## 4. Decisions\n\n### Assumptions\n\n- x (relies on I1)\n\n## 5. Test seams\n")
        write_spec_file(sandbox, "feat-a.decisions.md", "## Intent\n\n- I1 Goal: a\n\n## Decisions\n\n- one\n")
        now = datetime.datetime.now(datetime.timezone.utc)
        write_transcript(main_transcript(sandbox, "s-1"), [assistant(now + datetime.timedelta(seconds=1), tokens=usage(10, 10))])
        commands = (
            SNAPSHOT,
            CHECK_RECORD,
            "python3 {root}/scripts/check_record.py --complete docs/specs/feat-a.record.json",
            "python3 {root}/scripts/render_record.py --record docs/specs/feat-a.record.json --spec docs/specs/feat-a.md --items docs/specs/feat-a.items.json",
            "python3 {root}/scripts/check_spec.py --template {root}/core/templates/spec-feature.md docs/specs/feat-a.md",
            "python3 {root}/scripts/check_items.py docs/specs/feat-a.items.json",
            "python3 {root}/scripts/tree_guard.py verify --repo . --snapshot docs/specs/feat-a.guard.json",
        )
        for command in commands:
            self.assertEqual(run_hook(sandbox, hook_payload(sandbox, command.format(root=ROOT))).returncode, 0)
        run = sorted(folder(sandbox, "event").glob("feat-a.*.jsonl"))[0].name[:-len(".jsonl")]
        result = build(sandbox, run)
        self.assertEqual(result.returncode, 0, result.stderr)
        line = read_summary(sandbox, run)
        with open(CATALOGUE, encoding="utf-8") as handle:
            fields = json.load(handle)["summary"]["fields"]
        plain = {key: value for key, value in line.items() if key not in ENVELOPE}
        self.assertEqual(list(plain), list(fields))
        self.assertEqual(undescribed(fields, plain, ""), ())


if __name__ == "__main__":
    unittest.main()
