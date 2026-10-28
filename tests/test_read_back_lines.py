import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

TIMEOUT = 60
RUNNABLE_SEAM = {
    "name": "script-cli",
    "interface": "the scripts run as subprocesses on temporary records",
    "catches": "a wrong exit code or a missing error",
    "misses": "how a person reads the output",
    "builder_runs": True,
}
LAB_SEAM = {
    "name": "phone-lab",
    "interface": "a person holding a phone",
    "catches": "a total drawn late",
    "misses": "a wrong total",
    "builder_runs": False,
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
    "pass": "every trial meets the rubric.",
    "rubric": "The summary names each failing check.",
    "trials": 3,
}
PHONE_LINE = {
    "id": "C3.1",
    "kind": "exact",
    "surface": {"family": "mobile", "target": "android"},
    "command": "python3 tests/drive_phone.py",
    "pass": "the phone shows the total",
}
EXACT_SENTENCE = (
    "C1.1 (exact, cli python3): run `python3 -m unittest tests.test_a` from the repository root; "
    "it passes when the test passes."
)
JUDGED_SENTENCE = (
    "C2.1 (judged, agent claude): run `python3 tests/judge_summary.py` from the repository root three times "
    "and judge each run against the rubric: The summary names each failing check; "
    "it passes when every trial meets the rubric."
)
SURFACES_HEADING = "Surfaces that could not be driven"
CLAUDE_QUESTION = (
    "- C2.1 needs claude for claude, which failed: claude is not on PATH. "
    "Fix the surface and probe again, or move criterion 5.2 to a seam the builder cannot run?"
)
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
OUTCOMES = {"store": "/var/empty/trajectories.jsonl", "entries": 0, "repeated": []}


def load_referee():
    path = pathlib.Path(__file__).with_name("contract_referee.py")
    spec = importlib.util.spec_from_file_location("contract_referee", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


referee = load_referee()


def probe(check, name, target, status="pass", detail=None):
    return {
        "check": check,
        "probe": name,
        "target": target,
        "status": status,
        "detail": detail or "/usr/local/bin/" + target,
    }


def complete_record():
    return json.loads(
        json.dumps(
            {
                "status": "in-progress",
                "seams": [RUNNABLE_SEAM],
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
                "locked": ["tests/test_a.py", "tests/test_b.py"],
                "probes": [
                    probe("C1.1", "command", "python3"),
                    probe("C2.1", "command", "python3"),
                    probe("C2.1", "claude", "claude"),
                ],
                "outcomes": OUTCOMES,
            }
        )
    )


def record_with_failed_probes():
    record = complete_record()
    phone = {
        "number": "5.3",
        "title": "The total shows on the phone",
        "text": "WHEN the app computes a total, THE SYSTEM SHALL show it on the phone.",
        "seam": "phone-lab",
        "acceptance": [PHONE_LINE],
        "tests": [],
        "unproven": "a person holds the phone",
    }
    phone_step = {"name": "build-phone", "files": ["scripts/phone.py"], "criteria": ["5.3"], "task": "Draw it."}
    return {
        **record,
        "seams": record["seams"] + [LAB_SEAM],
        "criteria": record["criteria"] + [phone],
        "steps": record["steps"] + [phone_step],
        "probes": [
            probe("C1.1", "command", "python3"),
            probe("C2.1", "command", "python3"),
            probe("C2.1", "claude", "claude", "fail", "claude is not on PATH"),
            probe("C3.1", "command", "python3"),
            probe("C3.1", "vmlab", "android", "fail", "vmlab is not on PATH"),
        ],
    }


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


def read_back(base, record):
    return run([script_path("read_back.py"), "--record", write_record(base, record)], base)


def section(text, heading):
    lines = text.splitlines()
    starts = [position for position, line in enumerate(lines) if line == heading]
    if not starts:
        return ""
    start = starts[0]
    ends = [position for position in range(start + 1, len(lines)) if lines[position].startswith("## ")]
    return "\n".join(lines[start : ends[0] if ends else len(lines)])


class ReadBackLinesTest(unittest.TestCase):
    def assert_lines_are_k1(self, lines):
        k1 = referee.load("k1-acceptance")
        for line in lines:
            self.assertEqual(referee.errors(k1, line), (), line["id"])

    def test_the_read_back_lists_each_acceptance_line_in_plain_words(self):
        self.assert_lines_are_k1((EXACT_LINE, JUDGED_LINE))
        with tempfile.TemporaryDirectory() as base:
            code, output = read_back(base, complete_record())
        self.assertEqual(code, 0, output)
        printed = output.splitlines()
        self.assertIn("- " + EXACT_SENTENCE, printed)
        self.assertIn("- " + JUDGED_SENTENCE, printed)
        self.assertNotIn("{", output)
        self.assertNotIn("}", output)

    def test_the_read_back_turns_each_failed_probe_into_a_question(self):
        self.assert_lines_are_k1((EXACT_LINE, JUDGED_LINE, PHONE_LINE))
        with tempfile.TemporaryDirectory() as base:
            code, output = read_back(base, record_with_failed_probes())
        self.assertEqual(code, 0, output)
        printed = output.splitlines()
        self.assertIn(SURFACES_HEADING, printed)
        questions = printed[printed.index(SURFACES_HEADING) + 1 :]
        self.assertIn(CLAUDE_QUESTION, questions)
        self.assertTrue(CLAUDE_QUESTION.endswith("?"))
        self.assertEqual([line for line in questions if "C3.1" in line], [])

    def test_the_spec_lists_each_acceptance_line(self):
        self.assert_lines_are_k1((EXACT_LINE, JUDGED_LINE))
        template = (repository_root() / "core" / "templates" / "spec-feature.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as base:
            specs = pathlib.Path(base) / "docs" / "specs"
            specs.mkdir(parents=True)
            spec_path = specs / "demo.md"
            spec_path.write_text(template, encoding="utf-8")
            record_path = write_record(base, complete_record())
            code, output = run(
                [
                    script_path("render_record.py"),
                    "--record",
                    record_path,
                    "--spec",
                    spec_path,
                    "--items",
                    specs / "demo.items.json",
                ],
                base,
            )
            spec_text = spec_path.read_text(encoding="utf-8")
            read_code, read_output = run([script_path("read_back.py"), "--record", record_path], base)
        self.assertEqual(code, 0, output)
        self.assertEqual(read_code, 0, read_output)
        printed = read_output.splitlines()
        for sentence in (EXACT_SENTENCE, JUDGED_SENTENCE):
            self.assertIn("- " + sentence, printed)
            self.assertIn("Acceptance lines:\n- " + sentence, spec_text)

    def test_phase_seven_reads_back_the_script_output(self):
        phases = (repository_root() / "core" / "phases.md").read_text(encoding="utf-8")
        body = section(phases, "## Phase 7: Read back")
        self.assertNotEqual(body, "")
        self.assertIn("scripts/read_back.py", body)
        self.assertIn("word for word", body)


if __name__ == "__main__":
    unittest.main()
