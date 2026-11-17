import contextlib
import copy
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from feasibility_fixture import feasible

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEXT_SEAM = "authored-text"
NO_TEXT_FEASIBILITY = "record holds a text criterion but no feasibility results; run lock_feasibility.py"
STALE = "the record changed since lock_feasibility.py ran; run it again"
RESERVED = "seam 'authored-text' is reserved for text criteria and must have builder_runs true"
OUTCOMES = {"store": "/var/empty/trajectories.jsonl", "entries": 0, "repeated": []}
SPEC_TEXT = (
    "# Demo feature\n\nPathway: feature.\n\nDate: 2026-11-16.\n\n"
    "## 1. Problem\n\nThe README lacks the route.\n\n"
    "## 2. Intent\n\n- I1 Goal: the README lists the route.\n\n"
    "## 3. User stories\n\n1. As a reader, I want the route listed, so that I find it.\n\n"
    "## 4. Decisions\n\n1. The README gains a route list.\n\n"
    "### Reuse and change\n\nReused as is: nothing.\n\n"
    "### Assumptions\n\n- None\n\n"
    "### Risks\n\n- None\n\n"
    "## 5. Test seams\n\n"
    "{{written by the render script from the record: the agreed seams, then one numbered heading per acceptance "
    "criterion, 5.1, 5.2 and so on}}\n\n"
    "## 6. Out of scope\n\nA changelog.\n"
)


def load_script(name):
    spec = importlib.util.spec_from_file_location(name + "_text_under_test", str(ROOT / "scripts" / (name + ".py")))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_record = load_script("check_record")


def seam(name):
    return {
        "name": name,
        "interface": "the %s surface" % name,
        "catches": "a wrong result",
        "misses": "how it reads",
        "builder_runs": True,
    }


def line(check, command):
    return {
        "id": check,
        "kind": "exact",
        "surface": {"family": "cli", "target": "python3"},
        "command": command,
        "pass": "the command exits 0",
    }


def probe(check):
    return {"check": check, "probe": "command", "target": "python3", "status": "pass", "detail": "/usr/bin/python3"}


def criterion(number, seam_name, check, command, rows=()):
    return {
        "number": number,
        "title": "Criterion %s holds" % number,
        "text": "WHEN it runs, THE SYSTEM SHALL meet criterion %s." % number,
        "seam": seam_name,
        "acceptance": [line(check, command)],
        "tests": list(rows),
    }


def row(file, name, step, check):
    return {
        "file": file,
        "name": name,
        "given": "a total of 3",
        "expect": "3 is returned",
        "step": step,
        "check": check,
        "loads": ["src/app.py"] if file == "tests/test_app.py" else ["README.md"],
        "needs": ["src/app.py"] if file == "tests/test_app.py" else ["README.md"],
    }


def step(name, files, numbers):
    return {"name": name, "files": list(files), "criteria": list(numbers), "task": "Build %s." % name}


def text_only_record():
    return {
        "status": "in-progress",
        "seams": [seam(TEXT_SEAM)],
        "criteria": [criterion("5.1", TEXT_SEAM, "C1.1", "python3 scripts/lint_readme.py")],
        "steps": [step("write-readme", ("README.md", "scripts/lint_readme.py"), ("5.1",))],
        "probes": [probe("C1.1")],
        "outcomes": dict(OUTCOMES),
    }


def sealed(record, results=()):
    digest = check_record.feasibility_digest(record, results)
    return {**record, "feasibility": {"digest": digest, "results": list(results)}}


def run_check(record, complete):
    return check_record.check(json.dumps(record), complete=complete)


class TextCriterionRecordTest(unittest.TestCase):
    def test_text_criterion_without_rows_passes_the_complete_check(self):
        record = sealed(text_only_record())
        self.assertEqual(run_check(record, True), ())
        self.assertEqual(run_check(record, False), ())

    def test_text_and_behaviour_criteria_pass_together(self):
        record = {
            "status": "in-progress",
            "seams": [seam("unit-tests"), seam(TEXT_SEAM)],
            "criteria": [
                criterion(
                    "5.1",
                    "unit-tests",
                    "C1.1",
                    "python3 -m unittest tests.test_app",
                    [row("tests/test_app.py", "test_total", "build-app", "C1.1")],
                ),
                criterion("5.2", TEXT_SEAM, "C2.1", "python3 scripts/lint_readme.py"),
            ],
            "steps": [
                step("build-app", ("src/app.py",), ("5.1",)),
                step("write-readme", ("README.md", "scripts/lint_readme.py"), ("5.2",)),
            ],
            "locked": ["tests/test_app.py"],
            "probes": [probe("C1.1"), probe("C2.1")],
            "outcomes": dict(OUTCOMES),
        }
        self.assertEqual(run_check(feasible(record), True), ())

    def test_text_criterion_without_feasibility_results_is_refused(self):
        record = text_only_record()
        stale = {**record, "feasibility": {"digest": "0" * 64, "results": []}}
        self.assertIn(("error", NO_TEXT_FEASIBILITY), run_check(record, True))
        self.assertIn(("error", STALE), run_check(stale, True))
        for candidate in (record, stale):
            messages = tuple(message for _, message in run_check(candidate, False))
            self.assertNotIn(NO_TEXT_FEASIBILITY, messages)
            self.assertNotIn(STALE, messages)

    def test_text_criterion_with_a_test_row_is_refused(self):
        record = text_only_record()
        record["criteria"][0]["tests"] = [row("tests/test_readme.py", "test_readme_lists_route", "write-readme", "C1.1")]
        record["locked"] = ["tests/test_readme.py"]
        expected = (
            "criterion 5.1 is a text criterion and carries test row 'test_readme_lists_route'; "
            "a lint command decides it, never a test"
        )
        for complete in (False, True):
            with self.subTest(complete=complete):
                self.assertIn(("error", expected), run_check(sealed(record), complete))

    def test_reserved_seam_the_builder_cannot_run_is_refused(self):
        record = text_only_record()
        record["seams"][0]["builder_runs"] = False
        for complete in (False, True):
            with self.subTest(complete=complete):
                self.assertIn(("error", RESERVED), run_check(sealed(record), complete))


class TextOnlyStepRenderTest(unittest.TestCase):
    def test_text_only_step_renders_and_passes_the_items_check(self):
        render_record = load_script("render_record")
        check_items = load_script("check_items")
        record = sealed(copy.deepcopy(text_only_record()))
        errors, spec_text, items = render_record.render(json.dumps(record), SPEC_TEXT, "docs/specs/demo.md")
        self.assertEqual(errors, ())
        self.assertEqual([item["name"] for item in items], ["write-readme"])
        self.assertEqual(items[0]["acceptance"], [])
        self.assertEqual(items[0]["spec_ref"], ["5.1"])
        self.assertNotIn("check-author", [item.get("role") for item in items])
        with tempfile.TemporaryDirectory() as folder:
            base = pathlib.Path(folder)
            spec_path = base / "demo.md"
            items_path = base / "demo.items.json"
            spec_path.write_text(spec_text, encoding="utf-8")
            items_path.write_text(
                json.dumps([{**item, "source": {**item["source"], "path": str(spec_path)}} for item in items]),
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = check_items.main([str(items_path)])
        self.assertEqual(code, 0)
        self.assertFalse([text for text in output.getvalue().splitlines() if text.startswith("error:")])


if __name__ == "__main__":
    unittest.main()
