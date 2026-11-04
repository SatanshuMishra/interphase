import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

H11_FILE = "h11-interphase-record.schema.json"
H12_FILE = "h12-interphase-items.schema.json"
CHECK_AUTHOR = "check-author"
NOT_AN_ID_PROBE = {
    "check": "not-an-id",
    "probe": "command",
    "target": "python3",
    "status": "pass",
    "detail": "/usr/bin/python3",
}
LOGGED_LINE = {
    "id": "C3.1",
    "kind": "exact",
    "surface": {"family": "cli", "target": "python3"},
    "command": "python3 -m unittest tests.test_c",
    "pass": "the test passes",
}
LOGGED_CRITERION = {
    "number": "5.3",
    "title": "Totals are logged",
    "text": "WHEN a total is computed, THE SYSTEM SHALL write it to the log.",
    "seam": "script-cli",
    "unproven": "the log is read only on the server",
    "acceptance": [LOGGED_LINE],
    "tests": [],
}
LOG_STEP = {
    "name": "log-total",
    "files": ["scripts/c.py"],
    "criteria": ["5.3"],
    "task": "Log the total.",
    "amendment": 1,
    "after": ["build-a"],
}
LOGGED_PROBE = {
    "check": "C3.1",
    "probe": "command",
    "target": "python3",
    "status": "pass",
    "detail": "/usr/local/bin/python3",
}
LOGGED_ROW = {
    "file": "tests/test_c.py",
    "name": "test_c_total_is_logged",
    "given": "a total of 3",
    "expect": "the log names 3",
    "step": "log-total",
    "check": "C3.1",
    "loads": ["scripts/c.py"],
    "needs": ["scripts/c.py"],
}


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def contracts_folder():
    return repository_root() / "contracts"


def load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gate():
    return load_path("owned_formats_render_gate", repository_root() / "scripts" / "handoff_gate.py")


def feasibility():
    return load_path("owned_formats_render_feasibility", repository_root() / "tests" / "feasibility_fixture.py")


def fixtures():
    tests = repository_root() / "tests"
    lane = load_path("owned_formats_render_lane", tests / "test_check_author_lane.py")
    kinds = load_path("owned_formats_render_kinds", tests / "test_outcome_kinds.py")
    return lane.complete_record(), kinds.SPEC_WITHOUT_KIND


def vendored_errors(name, value):
    validator = load_path("owned_formats_render_validator", contracts_folder() / "validator.py")
    return tuple(validator.errors_against(str(contracts_folder()), name, value))


def environment(home):
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
    }
    return {**kept, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1"}


def run(arguments, cwd, home):
    return subprocess.run(
        [sys.executable] + [str(argument) for argument in arguments],
        cwd=str(cwd),
        env=environment(home),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def script_path(name):
    return repository_root() / "scripts" / name


def demo_folder(base):
    folder = pathlib.Path(base).resolve()
    home = folder / "home"
    home.mkdir()
    return folder, home


def write_demo(folder, record, spec_text):
    (folder / "demo.md").write_text(spec_text, encoding="utf-8")
    path = folder / "demo.record.json"
    path.write_text(json.dumps(feasibility().feasible(record)), encoding="utf-8")
    return path


def render(folder, home, items_name, amendment=None):
    chosen = () if amendment is None else ("--amendment", str(amendment))
    return run(
        [
            script_path("render_record.py"),
            "--record",
            folder / "demo.record.json",
            "--spec",
            folder / "demo.md",
            "--items",
            folder / items_name,
        ]
        + list(chosen),
        folder,
        home,
    )


def output_of(result):
    return result.stdout + result.stderr


def error_lines(text):
    return [line for line in text.splitlines() if line.startswith("error: ")]


def naming(text, words):
    return [line for line in error_lines(text) if all(word in line for word in words)]


def with_step_amendment(record, position, amendment):
    steps = record["steps"]
    changed = {**steps[position], "amendment": amendment}
    return {**record, "steps": list(steps[:position]) + [changed] + list(steps[position + 1 :])}


def with_extra_probe(record, entry):
    return {**record, "probes": list(record["probes"]) + [entry]}


def with_outcome_entries(record, entries):
    return {**record, "outcomes": {**record["outcomes"], "entries": entries}}


def amended(record):
    return {
        **record,
        "criteria": list(record["criteria"]) + [LOGGED_CRITERION],
        "steps": list(record["steps"]) + [LOG_STEP],
        "probes": list(record["probes"]) + [LOGGED_PROBE],
    }


def proven(record):
    criterion = {key: value for key, value in LOGGED_CRITERION.items() if key != "unproven"}
    return {
        **record,
        "criteria": list(record["criteria"]) + [{**criterion, "tests": [LOGGED_ROW]}],
        "steps": list(record["steps"]) + [LOG_STEP],
        "probes": list(record["probes"]) + [LOGGED_PROBE],
        "locked": list(record["locked"]) + [LOGGED_ROW["file"]],
    }


class RenderRecordGateTest(unittest.TestCase):
    def assert_refused_before_writing(self, folder, spec_text, items_name, result):
        self.assertEqual(result.returncode, 1, output_of(result))
        self.assertEqual((folder / "demo.md").read_bytes(), spec_text.encode("utf-8"), output_of(result))
        self.assertFalse((folder / items_name).exists(), output_of(result))

    def test_render_writes_a_valid_record_and_refuses_one_that_fails_h11_only(self):
        record, spec_text = fixtures()
        with tempfile.TemporaryDirectory() as base:
            folder, home = demo_folder(base)
            write_demo(folder, record, spec_text)
            result = render(folder, home, "items.json")
            self.assertEqual(result.returncode, 0, output_of(result))
            self.assertNotEqual((folder / "demo.md").read_bytes(), spec_text.encode("utf-8"))
            self.assertTrue((folder / "items.json").is_file(), output_of(result))
            items = json.loads((folder / "items.json").read_text(encoding="utf-8"))
        self.assertEqual(vendored_errors("h12-interphase-items", items), ())
        probed = with_extra_probe(record, NOT_AN_ID_PROBE)
        with tempfile.TemporaryDirectory() as base:
            folder, home = demo_folder(base)
            record_path = write_demo(folder, probed, spec_text)
            accepted = run([script_path("check_record.py"), "--complete", record_path], folder, home)
            self.assertEqual(accepted.returncode, 0, output_of(accepted))
            result = render(folder, home, "items.json")
            self.assert_refused_before_writing(folder, spec_text, "items.json", result)
        self.assertNotEqual(
            naming(result.stdout, ("demo.record.json", H11_FILE, "#/probes/3/check")), [], output_of(result)
        )

    def test_render_names_h11_and_check_record_errors_and_writes_nothing(self):
        record, spec_text = fixtures()
        unamended = with_step_amendment(record, 0, 0)
        with tempfile.TemporaryDirectory() as base:
            folder, home = demo_folder(base)
            write_demo(folder, unamended, spec_text)
            result = render(folder, home, "items.json")
            self.assert_refused_before_writing(folder, spec_text, "items.json", result)
        self.assertNotEqual(naming(result.stdout, (H11_FILE, "#/steps/0/amendment")), [], output_of(result))
        self.assertNotEqual(
            naming(result.stdout, ("step 'build-a' has amendment that is not an integer of at least 1",)),
            [],
            output_of(result),
        )
        fractional = with_outcome_entries(record, 2.0)
        self.assertEqual(vendored_errors("h11-interphase-record", fractional), ())
        with tempfile.TemporaryDirectory() as base:
            folder, home = demo_folder(base)
            write_demo(folder, fractional, spec_text)
            result = render(folder, home, "items.json")
            self.assert_refused_before_writing(folder, spec_text, "items.json", result)
        self.assertNotEqual(
            naming(result.stdout, ("outcomes has entries that is not an integer",)), [], output_of(result)
        )
        self.assertEqual([line for line in output_of(result).splitlines() if H11_FILE in line], [], output_of(result))


class RenderItemsGateTest(unittest.TestCase):
    def test_an_amendment_with_no_test_rows_renders_valid_items_with_no_check_author(self):
        record, spec_text = fixtures()
        with tempfile.TemporaryDirectory() as base:
            folder, home = demo_folder(base)
            write_demo(folder, amended(record), spec_text)
            result = render(folder, home, "amend.items.json", amendment=1)
            output = output_of(result)
            self.assertEqual(result.returncode, 0, output)
            items = json.loads((folder / "amend.items.json").read_text(encoding="utf-8"))
        self.assertEqual([item["name"] for item in items], [LOG_STEP["name"]], items)
        self.assertEqual(vendored_errors("h12-interphase-items", items), ())

    def test_the_items_gate_refuses_a_check_author_with_no_files_and_names_each_error(self):
        record, spec_text = fixtures()
        with tempfile.TemporaryDirectory() as base:
            folder, home = demo_folder(base)
            write_demo(folder, proven(record), spec_text)
            result = render(folder, home, "amend.items.json", amendment=1)
            output = output_of(result)
            self.assertEqual(result.returncode, 0, output)
            items_path = folder / "amend.items.json"
            items = json.loads(items_path.read_text(encoding="utf-8"))
            rendered_spec = (folder / "demo.md").read_text(encoding="utf-8")
        authors = [item for item in items if isinstance(item, dict) and item.get("name") == CHECK_AUTHOR]
        self.assertEqual(len(authors), 1, items)
        self.assertIn(LOGGED_ROW["file"], authors[0].get("files", []))
        self.assertEqual(vendored_errors("h12-interphase-items", items), ())
        emptied = [{**item, "files": []} if item is authors[0] else item for item in items]
        refusals = gate().items_gate(str(items_path), emptied, rendered_spec, True)
        refused = "\n".join("error: " + line for line in refusals)
        self.assertNotEqual(naming(refused, ("amend.items.json", H12_FILE, "files minItems")), [], refused)
        self.assertNotEqual(
            naming(refused, ("step 'check-author' has files that is not a non-empty list",)), [], refused
        )


if __name__ == "__main__":
    unittest.main()
