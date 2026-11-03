import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

PHONE_SEAM = {
    "name": "phone-screen",
    "interface": "the total is drawn on the phone screen",
    "catches": "a total drawn with the wrong digits",
    "misses": "how a person reads the screen",
    "builder_runs": False,
}
DRAWN_ROW = {
    "file": "tests/test_c.py",
    "name": "test_c_total_is_drawn",
    "given": "a total of 3",
    "expect": "3 is drawn",
    "step": "build-c",
}
DRAWN_CRITERION = {
    "number": "5.3",
    "title": "The total is drawn",
    "text": "WHEN a total is shown, THE SYSTEM SHALL draw it on the phone screen.",
    "seam": "phone-screen",
    "unproven": "seen only on the phone",
    "tests": [DRAWN_ROW],
}
DRAW_STEP = {
    "name": "build-c",
    "files": ["scripts/c.py", "tests/test_c.py"],
    "criteria": ["5.3"],
    "task": "Draw the total.",
    "msp": "build",
}
BUILD_A_ACCEPTANCE = [{"file": "tests/test_a.py", "test": "test_a_total_is_returned_unchanged", "check": "C1.1"}]
BUILD_B_ACCEPTANCE = [{"file": "tests/test_b.py", "test": "test_b_summary_names_each_failure", "check": "C2.1"}]


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def contracts_folder():
    return repository_root() / "contracts"


def load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixtures():
    tests = repository_root() / "tests"
    lane = load_path("owned_formats_items_check_lane", tests / "test_check_author_lane.py")
    kinds = load_path("owned_formats_items_check_kinds", tests / "test_outcome_kinds.py")
    return lane.complete_record(), kinds.SPEC_WITHOUT_KIND


def vendored_errors(name, value):
    validator = load_path("owned_formats_items_check_validator", contracts_folder() / "validator.py")
    return tuple(validator.errors_against(str(contracts_folder()), name, value))


def environment(home):
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
    }
    return {**kept, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1"}


def with_drawn_total(record):
    return {
        **record,
        "seams": list(record["seams"]) + [PHONE_SEAM],
        "criteria": list(record["criteria"]) + [DRAWN_CRITERION],
        "steps": list(record["steps"]) + [DRAW_STEP],
    }


class ItemsCheckIdTest(unittest.TestCase):
    def test_items_acceptance_carries_each_rows_check(self):
        record, spec_text = fixtures()
        with tempfile.TemporaryDirectory() as base:
            folder = pathlib.Path(base).resolve()
            home = folder / "home"
            home.mkdir()
            (folder / "demo.md").write_text(spec_text, encoding="utf-8")
            record_path = folder / "demo.record.json"
            record_path.write_text(json.dumps(with_drawn_total(record)), encoding="utf-8")
            items_path = folder / "items.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(repository_root() / "scripts" / "render_record.py"),
                    "--record",
                    str(record_path),
                    "--spec",
                    str(folder / "demo.md"),
                    "--items",
                    str(items_path),
                ],
                cwd=str(folder),
                env=environment(home),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            items = json.loads(items_path.read_text(encoding="utf-8"))
        steps = {item["name"]: item for item in items}
        self.assertEqual(steps["build-a"]["acceptance"], BUILD_A_ACCEPTANCE)
        self.assertEqual(steps["build-b"]["acceptance"], BUILD_B_ACCEPTANCE)
        drawn = steps["build-c"]["acceptance"]
        self.assertEqual(len(drawn), 1, drawn)
        self.assertEqual((drawn[0].get("file"), drawn[0].get("test")), (DRAWN_ROW["file"], DRAWN_ROW["name"]))
        self.assertNotIn("check", drawn[0])
        self.assertEqual(vendored_errors("h12-interphase-items", items), ())


if __name__ == "__main__":
    unittest.main()
