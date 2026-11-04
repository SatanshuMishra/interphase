import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

TIMEOUT = 60
ROLE = "check-author"
SEAM = {
    "name": "script-cli",
    "interface": "the scripts run as subprocesses on temporary records",
    "catches": "a wrong exit code or a missing error",
    "misses": "how a person reads the output",
    "builder_runs": True,
}
OUTCOMES = {"store": "/var/empty/trajectories.jsonl", "entries": 0, "repeated": []}
ROW_A_NAME = "test_a_total_is_returned_unchanged"
ROW_B_NAME = "test_b_summary_names_each_failure"
ROW_C_NAME = "test_c_report_lists_every_total"
PROBE_SENTENCE = (
    "write a probe implementation only inside the files its row lists after Its probe may write, and never commit it"
)
FAILURE_SENTENCE = (
    "fails on today's code by an assertion failure or a missing module, never by a crash in the harness "
    "such as a TypeError, a ReferenceError, or a collection, import-time or setup error"
)
ROW_B_ENDING = "Loads: src/a.py, src/b.py. Needs: src/b.py. Its probe may write: src/a.py, src/b.py."
PROBE_HEAD = "Its probe may write: "
RESERVED_ERROR = "error: step name 'check-author-alpha' is reserved for the rendered check-author Step"


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def script_path(name):
    return repository_root() / "scripts" / name


def load_script(name):
    spec = importlib.util.spec_from_file_location(name + "_under_test", str(script_path(name + ".py")))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def line(check, test_module):
    return {
        "id": check,
        "kind": "exact",
        "surface": {"family": "cli", "target": "python3"},
        "command": "python3 -m unittest tests." + test_module,
        "pass": "the test passes",
    }


def probe(check):
    return {"check": check, "probe": "command", "target": "python3", "status": "pass", "detail": "/usr/bin/python3"}


def locked_row(file, name, owner, check, loads, needs):
    return {
        "file": file,
        "name": name,
        "given": "a report with a total of 3",
        "expect": "the report shows 3",
        "step": owner,
        "check": check,
        "loads": list(loads),
        "needs": list(needs),
    }


def criterion(number, check, rows):
    return {
        "number": number,
        "title": "Criterion %s holds" % number,
        "text": "WHEN the report runs, THE SYSTEM SHALL meet criterion %s." % number,
        "seam": "script-cli",
        "acceptance": [line(check, "test_" + number.replace(".", "_"))],
        "tests": list(rows),
    }


def build_step(name, files, numbers, **fields):
    return {"name": name, "files": list(files), "criteria": list(numbers), "task": "Build %s." % name, **fields}


def base_record(criteria, steps, locked):
    return {
        "status": "in-progress",
        "seams": [dict(SEAM)],
        "criteria": list(criteria),
        "steps": list(steps),
        "locked": list(locked),
        "probes": [probe(entry["acceptance"][0]["id"]) for entry in criteria],
        "outcomes": dict(OUTCOMES),
    }


def feasible(record):
    check_record = load_script("check_record")
    digest = getattr(check_record, "feasibility_digest", None)
    if digest is None:
        return record
    results = [
        {
            "check": "loads",
            "subject": "%s::%s %s" % (row["file"], row["name"], path),
            "status": "pass",
            "detail": "written by " + row["step"],
        }
        for entry in record["criteria"]
        for row in entry["tests"]
        for path in row.get("loads", ())
    ]
    return {**record, "feasibility": {"digest": digest(record), "results": results}}


def row_a(file="tests/test_a.py"):
    return locked_row(file, ROW_A_NAME, "build-a", "C1.1", ["src/a.py"], ["src/a.py"])


def row_b(file="tests/test_b.py", loads=("src/b.py",)):
    return locked_row(file, ROW_B_NAME, "build-b", "C2.1", loads, ["src/b.py"])


def two_msp_record():
    return base_record(
        [criterion("5.1", "C1.1", [row_a()]), criterion("5.2", "C2.1", [row_b()])],
        [
            build_step("build-a", ["src/a.py"], ["5.1"], msp="alpha"),
            build_step("build-b", ["src/b.py"], ["5.2"], msp="beta"),
        ],
        ["tests/test_a.py", "tests/test_b.py"],
    )


def ordered_record():
    return base_record(
        [criterion("5.1", "C1.1", [row_a()]), criterion("5.2", "C2.1", [row_b(loads=("src/a.py", "src/b.py"))])],
        [
            build_step("build-a", ["src/a.py"], ["5.1"]),
            build_step("build-b", ["src/b.py"], ["5.2"], after=["build-a"]),
        ],
        ["tests/test_a.py", "tests/test_b.py"],
    )


def shared_file_record():
    return base_record(
        [criterion("5.1", "C1.1", [row_a()]), criterion("5.2", "C2.1", [row_b(file="tests/test_a.py")])],
        [
            build_step("build-a", ["src/a.py"], ["5.1"], msp="alpha"),
            build_step("build-b", ["src/b.py"], ["5.2"], msp="beta"),
        ],
        ["tests/test_a.py"],
    )


def amended_record():
    source = two_msp_record()
    row_c = locked_row("tests/test_c.py", ROW_C_NAME, "build-c", "C3.1", ["src/c.py"], ["src/c.py"])
    criteria = source["criteria"] + [criterion("5.3", "C3.1", [row_c])]
    steps = source["steps"] + [build_step("build-c", ["src/c.py"], ["5.3"], msp="alpha-amend-1", amendment=1)]
    return base_record(criteria, steps, source["locked"] + ["tests/test_c.py"])


def by_name(items):
    return {entry["name"]: entry for entry in items}


def authors(items):
    return [entry for entry in items if entry.get("role") == ROLE]


def error_lines(output):
    return [text for text in output.splitlines() if text.startswith("error: ")]


def row_line(task, file, name):
    head = "- `%s` `%s`" % (file, name)
    found = [text for text in task.splitlines() if text.startswith(head)]
    return found[0] if found else ""


class RenderCase(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = pathlib.Path(holder.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.specs = self.root / "docs" / "specs"
        self.specs.mkdir(parents=True)

    def environment(self):
        kept = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
        }
        return {**kept, "HOME": str(self.home), "PYTHONDONTWRITEBYTECODE": "1"}

    def run_script(self, arguments):
        result = subprocess.run(
            [sys.executable] + [str(argument) for argument in arguments],
            cwd=str(self.root),
            env=self.environment(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        return result.returncode, result.stdout + result.stderr

    def write_record(self, record):
        path = self.specs / "demo.record.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return path

    def render(self, record, amendment=None):
        template = (repository_root() / "core" / "templates" / "spec-feature.md").read_text(encoding="utf-8")
        spec_path = self.specs / "demo.md"
        spec_path.write_text(template, encoding="utf-8")
        items_path = self.specs / "demo.items.json"
        extra = ["--amendment", str(amendment)] if amendment is not None else []
        code, output = self.run_script(
            [
                script_path("render_record.py"),
                "--record",
                self.write_record(record),
                "--spec",
                spec_path,
                "--items",
                items_path,
            ]
            + extra
        )
        return code, output, items_path

    def items(self, record, amendment=None):
        code, output, items_path = self.render(record, amendment)
        self.assertEqual(code, 0, output)
        return json.loads(items_path.read_text(encoding="utf-8"))

    def check_items(self, items):
        path = self.specs / "edited.items.json"
        path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        return self.run_script([script_path("check_items.py"), path])


class ProbeInstructionTest(RenderCase):
    def author_task(self):
        found = authors(self.items(feasible(ordered_record())))
        self.assertEqual(len(found), 1, found)
        return found[0]["task"]

    def test_each_row_lists_the_files_its_probe_may_write(self):
        task = self.author_task()
        line_b = row_line(task, "tests/test_b.py", ROW_B_NAME)
        self.assertTrue(line_b.endswith(" " + ROW_B_ENDING), line_b)
        line_a = row_line(task, "tests/test_a.py", ROW_A_NAME)
        self.assertIn(PROBE_HEAD, line_a)
        probe_files = line_a.split(PROBE_HEAD, 1)[1]
        self.assertIn("src/a.py", probe_files)
        self.assertNotIn("src/b.py", probe_files)

    def test_the_task_requires_a_passing_probe_and_an_assertion_failure_today(self):
        task = self.author_task()
        self.assertIn(PROBE_SENTENCE, task)
        self.assertIn(FAILURE_SENTENCE, task)


class PerMspRenderTest(RenderCase):
    def test_render_writes_one_check_author_per_msp(self):
        items = self.items(feasible(two_msp_record()))
        expected = (("check-author-alpha", "alpha", ["tests/test_a.py"]), ("check-author-beta", "beta", ["tests/test_b.py"]))
        self.assertEqual([entry["name"] for entry in items[:2]], [name for name, _, _ in expected])
        for entry, (name, msp, files) in zip(items[:2], expected):
            with self.subTest(name=name):
                self.assertEqual(entry["role"], ROLE)
                self.assertEqual(entry["msp"], msp)
                self.assertEqual(entry["files"], files)
                self.assertEqual(entry["acceptance"], [])

    def test_each_check_author_task_holds_only_its_msps_rows(self):
        alpha = by_name(self.items(feasible(two_msp_record()))).get("check-author-alpha")
        self.assertIsNotNone(alpha)
        self.assertIn(ROW_A_NAME, alpha["task"])
        self.assertNotIn(ROW_B_NAME, alpha["task"])
        self.assertEqual(alpha["spec_ref"], ["5.1"])

    def test_each_step_comes_after_only_its_own_msps_check_author(self):
        named = by_name(self.items(feasible(two_msp_record())))
        self.assertIn("check-author-alpha", named["build-a"].get("after", []))
        self.assertNotIn("check-author-beta", named["build-a"].get("after", []))
        self.assertIn("check-author-beta", named["build-b"].get("after", []))
        self.assertNotIn("check-author-alpha", named["build-b"].get("after", []))

    def test_an_unlabelled_record_keeps_one_check_author(self):
        items = self.items(feasible(ordered_record()))
        found = authors(items)
        self.assertEqual(len(found), 1, [entry["name"] for entry in items])
        author = found[0]
        self.assertEqual(author["name"], ROLE)
        self.assertEqual(author["files"], ["tests/test_a.py", "tests/test_b.py"])
        self.assertNotIn("msp", author)
        for entry in items:
            if entry.get("role") != ROLE:
                with self.subTest(step=entry["name"]):
                    self.assertIn(ROLE, entry.get("after", []))

    def test_a_locked_file_shared_by_two_msps_is_refused(self):
        record = feasible(shared_file_record())
        code, output = self.run_script([script_path("check_record.py"), "--complete", self.write_record(record)])
        self.assertEqual(code, 1, output)
        named = [text for text in error_lines(output) if all(part in text for part in ("tests/test_a.py", "alpha", "beta"))]
        self.assertTrue(named, output)
        render_code, render_output, items_path = self.render(record)
        self.assertEqual(render_code, 1, render_output)
        self.assertFalse(items_path.exists())

    def test_a_step_named_with_the_check_author_prefix_is_refused(self):
        source = two_msp_record()
        reserved = build_step("check-author-alpha", ["src/c.py"], ["5.1"])
        code, output = self.run_script(
            [script_path("check_record.py"), self.write_record({**source, "steps": source["steps"] + [reserved]})]
        )
        self.assertEqual(code, 1, output)
        self.assertIn(RESERVED_ERROR, output.splitlines())

    def test_an_amendment_writes_check_authors_for_its_own_msps(self):
        items = self.items(feasible(amended_record()), amendment=1)
        self.assertEqual([entry["name"] for entry in items], ["check-author-alpha-amend-1", "build-c"])
        self.assertEqual(items[0]["files"], ["tests/test_c.py"])
        self.assertIn("check-author-alpha-amend-1", items[1].get("after", []))


class PerMspItemsCheckTest(RenderCase):
    def rendered(self):
        return self.items(feasible(two_msp_record()))

    def test_check_items_accepts_rendered_per_msp_check_authors(self):
        code, output = self.check_items(self.rendered())
        self.assertEqual(code, 0, output)
        self.assertEqual(error_lines(output), [])

    def test_check_items_refuses_an_acceptance_file_of_another_msp(self):
        items = self.rendered()
        leaked = [
            {
                **entry,
                "acceptance": entry["acceptance"] + [{"file": "tests/test_b.py", "test": ROW_B_NAME}],
                "after": entry.get("after", []) + ["check-author-beta"],
            }
            if entry["name"] == "build-a"
            else entry
            for entry in items
        ]
        code, output = self.check_items(leaked)
        self.assertEqual(code, 1, output)
        named = [text for text in error_lines(output) if "build-a" in text and "check-author-beta" in text]
        self.assertTrue(named, output)

    def test_check_items_refuses_two_check_authors_of_one_msp(self):
        items = self.rendered()
        shared = [{**entry, "msp": "alpha"} if entry["name"] == "check-author-beta" else entry for entry in items]
        code, output = self.check_items(shared)
        self.assertEqual(code, 1, output)
        named = [text for text in error_lines(output) if "check-author-alpha" in text and "check-author-beta" in text]
        self.assertTrue(named, output)


if __name__ == "__main__":
    unittest.main()
