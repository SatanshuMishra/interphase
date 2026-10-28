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
ROW_A = {
    "file": "tests/test_a.py",
    "name": "test_a",
    "given": "a total of 3",
    "expect": "3 is returned",
    "step": "build-a",
    "check": "C1.1",
}
ROW_B = {
    "file": "tests/test_b.py",
    "name": "test_b",
    "given": "a report with two failing checks",
    "expect": "the summary names both checks",
    "step": "build-b",
    "check": "C2.1",
}
LOCKED = ["tests/test_a.py", "tests/test_b.py"]
OUTCOMES = {"store": "/var/empty/trajectories.jsonl", "entries": 0, "repeated": []}


def load_referee():
    path = pathlib.Path(__file__).with_name("contract_referee.py")
    spec = importlib.util.spec_from_file_location("contract_referee", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


referee = load_referee()


def probe(check, name, target):
    return {"check": check, "probe": name, "target": target, "status": "pass", "detail": "/usr/bin/" + target}


PROBES = [
    probe("C1.1", "command", "python3"),
    probe("C2.1", "command", "python3"),
    probe("C2.1", "claude", "claude"),
]


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
                        "text": "WHEN the app is given a total, THE SYSTEM SHALL return it unchanged.",
                        "seam": "script-cli",
                        "acceptance": [EXACT_LINE],
                        "tests": [ROW_A],
                    },
                    {
                        "number": "5.2",
                        "title": "The summary names each failure",
                        "text": "WHEN a report has failing checks, THE SYSTEM SHALL name each one in its summary.",
                        "seam": "script-cli",
                        "acceptance": [JUDGED_LINE],
                        "tests": [ROW_B],
                    },
                ],
                "steps": [
                    {"name": "build-a", "files": ["scripts/a.py"], "criteria": ["5.1"], "task": "Build the total."},
                    {
                        "name": "build-b",
                        "files": ["scripts/b.py"],
                        "criteria": ["5.2"],
                        "task": "Build the summary.",
                        "after": ["build-a"],
                    },
                ],
                "locked": LOCKED,
                "probes": PROBES,
                "outcomes": OUTCOMES,
            }
        )
    )


def with_criterion(record, index, **fields):
    criteria = record["criteria"]
    return {**record, "criteria": criteria[:index] + [{**criteria[index], **fields}] + criteria[index + 1 :]}


def with_step(record, index, **fields):
    steps = record["steps"]
    return {**record, "steps": steps[:index] + [{**steps[index], **fields}] + steps[index + 1 :]}


def environment(home):
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
    }
    return {**kept, "HOME": home, "PYTHONDONTWRITEBYTECODE": "1"}


def script_path(name):
    return pathlib.Path(__file__).resolve().parents[1] / "scripts" / name


def check_record(record, complete):
    script = script_path("check_record.py")
    with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as home:
        path = pathlib.Path(folder) / "demo.record.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        flags = ["--complete"] if complete else []
        result = subprocess.run(
            [sys.executable, str(script)] + flags + [str(path)],
            cwd=folder,
            env=environment(home),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
    return result.returncode, result.stdout + result.stderr


def findings(output, severity):
    prefix = severity + ": "
    return [line[len(prefix) :] for line in output.splitlines() if line.startswith(prefix)]


def holding(lines, *words):
    return [line for line in lines if all(word in line for word in words)]


class AcceptanceLinesTest(unittest.TestCase):
    def test_a_record_with_k1_acceptance_lines_passes_the_complete_check(self):
        k1 = referee.load("k1-acceptance")
        locked_schema = referee.subschema(referee.load("k2-locked"), "/properties/locked")
        record = complete_record()
        self.assertEqual(referee.errors(k1, EXACT_LINE), ())
        self.assertEqual(referee.errors(k1, JUDGED_LINE), ())
        self.assertEqual(referee.errors(locked_schema, record["locked"]), ())
        code, output = check_record(record, complete=True)
        self.assertEqual(code, 0, output)
        self.assertEqual(findings(output, "error"), [])

    def test_a_line_that_breaks_k1_is_refused(self):
        k1 = referee.load("k1-acceptance")
        judged_as_first = {**JUDGED_LINE, "id": "C1.1"}
        broken = (
            ("an unknown key", {**EXACT_LINE, "note": "run it twice"}),
            ("a family outside the eight", {**EXACT_LINE, "surface": {"family": "fax", "target": "python3"}}),
            ("a judged line without rubric", {key: value for key, value in judged_as_first.items() if key != "rubric"}),
            ("an exact line with trials", {**EXACT_LINE, "trials": 3}),
            ("an empty command", {**EXACT_LINE, "command": ""}),
        )
        for reason, line in broken:
            with self.subTest(reason=reason):
                self.assertNotEqual(referee.errors(k1, line), ())
                code, output = check_record(with_criterion(complete_record(), 0, acceptance=[line]), complete=False)
                self.assertEqual(code, 1, output)
                self.assertNotEqual(
                    holding(findings(output, "error"), "criterion 5.1 acceptance line 1 does not match K1"),
                    [],
                    output,
                )

    def test_an_acceptance_line_id_must_follow_its_criterion_number(self):
        k1 = referee.load("k1-acceptance")
        misnumbered_line = {**EXACT_LINE, "id": "C4.1"}
        self.assertEqual(referee.errors(k1, misnumbered_line), ())
        misnumbered = with_step(
            with_criterion(
                complete_record(),
                0,
                number="5.3",
                acceptance=[misnumbered_line],
                tests=[{**ROW_A, "check": "C4.1"}],
            ),
            0,
            criteria=["5.3"],
        )
        code, output = check_record(misnumbered, complete=False)
        self.assertEqual(code, 1, output)
        self.assertNotEqual(
            holding(findings(output, "error"), "criterion 5.3 acceptance line 1 has id C4.1; expected C3.1"),
            [],
            output,
        )
        shared_line = {**JUDGED_LINE, "id": "C1.1"}
        self.assertEqual(referee.errors(k1, shared_line), ())
        shared = with_step(
            with_criterion(
                complete_record(),
                1,
                number="6.1",
                acceptance=[shared_line],
                tests=[{**ROW_B, "check": "C1.1"}],
            ),
            1,
            criteria=["6.1"],
        )
        code, output = check_record(shared, complete=False)
        self.assertEqual(code, 1, output)
        self.assertNotEqual(holding(findings(output, "error"), "C1.1"), [], output)

    def test_complete_refuses_a_runnable_criterion_without_an_acceptance_line(self):
        record = {
            "status": "in-progress",
            "seams": [SEAM],
            "criteria": [
                {
                    "number": "5.1",
                    "title": "The total adds up",
                    "text": "WHEN the app is given a total, THE SYSTEM SHALL return it unchanged.",
                    "seam": "script-cli",
                    "tests": [{key: value for key, value in ROW_A.items() if key != "check"}],
                },
                {
                    "number": "5.2",
                    "title": "The summary names each failure",
                    "text": "WHEN a report has failing checks, THE SYSTEM SHALL name each one in its summary.",
                    "seam": "script-cli",
                    "tests": [],
                    "unproven": "a person judges the summary",
                },
            ],
            "steps": [
                {
                    "name": "build-a",
                    "files": ["scripts/a.py", "tests/test_a.py"],
                    "criteria": ["5.1"],
                    "task": "Build the total.",
                },
                {"name": "build-b", "files": ["scripts/b.py"], "criteria": ["5.2"], "task": "Build the summary."},
            ],
            "outcomes": OUTCOMES,
        }
        messages = tuple(
            "criterion %s sits at a seam the builder runs and has no acceptance line" % number
            for number in ("5.1", "5.2")
        )
        code, output = check_record(record, complete=True)
        self.assertEqual(code, 1, output)
        for message in messages:
            self.assertNotEqual(holding(findings(output, "error"), message), [], output)
        code, output = check_record(record, complete=False)
        self.assertEqual(code, 0, output)
        for message in messages:
            self.assertNotEqual(holding(findings(output, "warning"), message), [], output)

    def test_locked_holds_every_acceptance_test_file_and_no_step_writes_it(self):
        locked_schema = referee.subschema(referee.load("k2-locked"), "/properties/locked")
        short = {**complete_record(), "locked": ["tests/test_a.py"]}
        self.assertEqual(referee.errors(locked_schema, short["locked"]), ())
        code, output = check_record(short, complete=True)
        self.assertEqual(code, 1, output)
        self.assertNotEqual(holding(findings(output, "error"), "tests/test_b.py", "locked"), [], output)
        absolute = {**complete_record(), "locked": ["/work/demo/tests/test_a.py", "tests/test_b.py"]}
        self.assertNotEqual(referee.errors(locked_schema, absolute["locked"]), ())
        code, output = check_record(absolute, complete=True)
        self.assertEqual(code, 1, output)
        self.assertNotEqual(holding(findings(output, "error"), "record locked does not match K2"), [], output)
        written = with_step(complete_record(), 0, files=["scripts/a.py", "tests/test_a.py"])
        code, output = check_record(written, complete=True)
        self.assertEqual(code, 1, output)
        self.assertNotEqual(holding(findings(output, "error"), "build-a", "tests/test_a.py", "locked"), [], output)


if __name__ == "__main__":
    unittest.main()
