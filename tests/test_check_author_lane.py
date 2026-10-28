import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

TIMEOUT = 60
SEAM = {
    "name": "script-cli",
    "interface": "the scripts run as subprocesses on temporary records",
    "catches": "a wrong exit code or a missing error",
    "misses": "how a person reads the output",
    "builder_runs": True,
}
EXACT_LINE = {
    "id": "C1.1",
    "kind": "exact",
    "surface": {"family": "cli", "target": "python3"},
    "command": "python3 -m unittest tests.test_a",
    "pass": "the test passes",
}
JUDGED_LINE = {
    "id": "C2.1",
    "kind": "judged",
    "surface": {"family": "agent", "target": "claude"},
    "command": "python3 tests/judge_summary.py",
    "pass": "every trial meets the rubric",
    "rubric": "the summary names each failing check",
    "trials": 3,
}
SENTENCES = (
    "C1.1 (exact, cli python3): run `python3 -m unittest tests.test_a` from the repository root; "
    "it passes when the test passes.",
    "C2.1 (judged, agent claude): run `python3 tests/judge_summary.py` from the repository root three times "
    "and judge each run against the rubric: the summary names each failing check; "
    "it passes when every trial meets the rubric.",
)
TOTAL_TEXT = "WHEN the app is given a total, THE SYSTEM SHALL return it unchanged."
SUMMARY_TEXT = "WHEN a report has failing checks, THE SYSTEM SHALL name each one in its summary."
ROW_A = {
    "file": "tests/test_a.py",
    "name": "test_a_total_is_returned_unchanged",
    "given": "a total of 3",
    "expect": "3 is returned",
    "step": "build-a",
    "check": "C1.1",
}
ROW_B = {
    "file": "tests/test_b.py",
    "name": "test_b_summary_names_each_failure",
    "given": "a report with two failing checks",
    "expect": "the summary names both checks",
    "step": "build-b",
    "check": "C2.1",
}
LOCKED = ["tests/test_a.py", "tests/test_b.py"]
OUTCOMES = {"store": "/var/empty/trajectories.jsonl", "entries": 0, "repeated": []}
CHECK_AUTHOR = "check-author"


def load_referee():
    path = pathlib.Path(__file__).with_name("contract_referee.py")
    spec = importlib.util.spec_from_file_location("contract_referee", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


referee = load_referee()


def probe(check, name, target):
    return {"check": check, "probe": name, "target": target, "status": "pass", "detail": "/usr/local/bin/" + target}


def complete_record():
    return json.loads(
        json.dumps(
            {
                "status": "in-progress",
                "seams": [SEAM],
                "criteria": [
                    {
                        "number": "5.1",
                        "title": "The total adds up",
                        "text": TOTAL_TEXT,
                        "seam": "script-cli",
                        "acceptance": [EXACT_LINE],
                        "tests": [ROW_A],
                    },
                    {
                        "number": "5.2",
                        "title": "The summary names each failure",
                        "text": SUMMARY_TEXT,
                        "seam": "script-cli",
                        "acceptance": [JUDGED_LINE],
                        "tests": [ROW_B],
                    },
                ],
                "steps": [
                    {
                        "name": "build-a",
                        "files": ["scripts/a.py"],
                        "criteria": ["5.1"],
                        "task": "Build the total.",
                        "msp": "build",
                    },
                    {
                        "name": "build-b",
                        "files": ["scripts/b.py"],
                        "criteria": ["5.2"],
                        "task": "Build the summary.",
                        "msp": "build",
                    },
                ],
                "locked": LOCKED,
                "probes": [
                    probe("C1.1", "command", "python3"),
                    probe("C2.1", "command", "python3"),
                    probe("C2.1", "claude", "claude"),
                ],
                "outcomes": OUTCOMES,
            }
        )
    )


def environment(home):
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
    }
    return {**kept, "HOME": home, "PYTHONDONTWRITEBYTECODE": "1"}


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def script_path(name):
    return repository_root() / "scripts" / name


def run(arguments, cwd):
    with tempfile.TemporaryDirectory() as home:
        result = subprocess.run(
            [sys.executable] + [str(argument) for argument in arguments],
            cwd=str(cwd),
            env=environment(home),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
    return result.returncode, result.stdout + result.stderr


def write_record(base, record):
    path = pathlib.Path(base) / "demo.record.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def render(base, record):
    template = (repository_root() / "core" / "templates" / "spec-feature.md").read_text(encoding="utf-8")
    specs = pathlib.Path(base) / "docs" / "specs"
    specs.mkdir(parents=True)
    spec_path = specs / "demo.md"
    spec_path.write_text(template, encoding="utf-8")
    items_path = specs / "demo.items.json"
    code, output = run(
        [
            script_path("render_record.py"),
            "--record",
            write_record(base, record),
            "--spec",
            spec_path,
            "--items",
            items_path,
        ],
        base,
    )
    return code, output, items_path


def read_items(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def error_lines(output):
    return [line for line in output.splitlines() if line.startswith("error: ")]


def by_name(items):
    return {item["name"]: item for item in items}


def moved_second(items):
    return [items[1], items[0]] + items[2:]


def with_item(items, name, **fields):
    return [{**item, **fields} if item["name"] == name else item for item in items]


def without_after(items, name, dropped):
    def trimmed(item):
        kept = [entry for entry in item.get("after", []) if entry != dropped]
        rest = {key: value for key, value in item.items() if key != "after"}
        return {**rest, "after": kept} if kept else rest

    return [trimmed(item) if item["name"] == name else item for item in items]


class CheckAuthorLaneTest(unittest.TestCase):
    def assert_record_meets_the_contracts(self, record):
        k1 = referee.load("k1-acceptance")
        locked_schema = referee.subschema(referee.load("k2-locked"), "/properties/locked")
        for criterion in record["criteria"]:
            for line in criterion["acceptance"]:
                self.assertEqual(referee.errors(k1, line), (), line["id"])
        self.assertEqual(referee.errors(locked_schema, record["locked"]), ())

    def rendered_items(self, base):
        record = complete_record()
        self.assert_record_meets_the_contracts(record)
        code, output, items_path = render(base, record)
        self.assertEqual(code, 0, output)
        self.assertTrue(items_path.exists(), output)
        return read_items(items_path), items_path

    def test_render_puts_a_check_author_step_first(self):
        with tempfile.TemporaryDirectory() as base:
            items, _ = self.rendered_items(base)
        first = items[0]
        self.assertEqual(first.get("name"), CHECK_AUTHOR)
        self.assertEqual(first.get("role"), CHECK_AUTHOR)
        self.assertEqual(first.get("files"), LOCKED)
        self.assertEqual(first.get("acceptance"), [])
        refs = first.get("spec_ref", [])
        for number in ("5.1", "5.2"):
            self.assertTrue(any(ref == number or ref.startswith(number + " ") for ref in refs), refs)
        self.assertEqual(first.get("msp"), CHECK_AUTHOR)
        task = first.get("task", "")
        for text in (TOTAL_TEXT, SUMMARY_TEXT) + SENTENCES + (ROW_A["name"], ROW_B["name"]):
            self.assertIn(text, task)

    def test_every_other_step_comes_after_the_check_author(self):
        with tempfile.TemporaryDirectory() as base:
            items, _ = self.rendered_items(base)
        self.assertEqual(items[0].get("name"), CHECK_AUTHOR)
        for item in items[1:]:
            self.assertIn(CHECK_AUTHOR, item.get("after", []), item["name"])
        steps = by_name(items)
        for name, row in (("build-a", ROW_A), ("build-b", ROW_B)):
            self.assertIn(name, steps)
            self.assertEqual(
                sorted((entry["file"], entry["test"]) for entry in steps[name]["acceptance"]),
                [(row["file"], row["name"])],
            )
            self.assertIn(row["file"], LOCKED)

    def test_check_items_accepts_the_rendered_lane_and_refuses_a_broken_one(self):
        with tempfile.TemporaryDirectory() as base:
            items, items_path = self.rendered_items(base)
            code, output = run([script_path("check_items.py"), items_path], base)
            self.assertEqual(code, 0, output)
            self.assertEqual(error_lines(output), [])
            self.assertEqual(items[0].get("name"), CHECK_AUTHOR)
            broken = (
                ("moved second", moved_second(items), (CHECK_AUTHOR,)),
                (
                    "gains an acceptance test",
                    with_item(items, CHECK_AUTHOR, acceptance=[{"file": LOCKED[0], "test": ROW_A["name"]}]),
                    (CHECK_AUTHOR, "acceptance"),
                ),
                ("loses its place in another item's after", without_after(items, "build-b", CHECK_AUTHOR), ("build-b", CHECK_AUTHOR)),
                ("carries role builder", with_item(items, CHECK_AUTHOR, role="builder"), ("role",)),
                (
                    "a build item lists a locked path",
                    with_item(items, "build-a", files=["scripts/a.py", LOCKED[0]]),
                    ("build-a", LOCKED[0]),
                ),
            )
            for reason, copy, words in broken:
                with self.subTest(reason=reason):
                    path = pathlib.Path(base) / "broken.items.json"
                    path.write_text(json.dumps(copy, indent=2), encoding="utf-8")
                    code, output = run([script_path("check_items.py"), path], base)
                    self.assertEqual(code, 1, output)
                    naming = [line for line in error_lines(output) if all(word in line for word in words)]
                    self.assertNotEqual(naming, [], output)

    def test_a_record_step_named_check_author_is_refused(self):
        record = complete_record()
        self.assert_record_meets_the_contracts(record)
        renamed = {
            **record,
            "criteria": [
                record["criteria"][0],
                {**record["criteria"][1], "tests": [{**ROW_B, "step": CHECK_AUTHOR}]},
            ],
            "steps": [record["steps"][0], {**record["steps"][1], "name": CHECK_AUTHOR}],
        }
        with tempfile.TemporaryDirectory() as base:
            code, output = run([script_path("check_record.py"), write_record(base, renamed)], base)
        self.assertEqual(code, 1, output)
        self.assertIn("step name 'check-author' is reserved for the rendered check-author Step", output)


if __name__ == "__main__":
    unittest.main()
