import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_acceptance_lines as acc
import test_check_author_lane as lane

CANON = "tests/test_a.py"
ALIASES = ("./tests/test_a.py", "tests//test_a.py", "tests/./test_a.py", "Tests/test_a.py", "tests/test_a.py/")


def load_schema_check():
    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "schema_check.py"
    spec = importlib.util.spec_from_file_location("schema_check", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


schema_check = load_schema_check()


class LockedPathAliasTest(unittest.TestCase):
    def test_a_step_listing_an_alias_of_a_locked_path_is_refused(self):
        base = acc.complete_record()
        for alias in ALIASES:
            with self.subTest(alias=alias):
                record = acc.with_step(base, 0, files=["scripts/a.py", alias])
                code, output = acc.check_record(record, complete=True)
                self.assertEqual(code, 1, output)
                naming = acc.holding(acc.findings(output, "error"), "build-a", alias, "locked")
                self.assertNotEqual(naming, [], output)

    def test_a_locked_alias_is_matched_against_the_canonical_step_file(self):
        base = acc.complete_record()
        for alias in ALIASES:
            with self.subTest(alias=alias):
                row = {**acc.ROW_A, "file": alias}
                record = acc.with_step(
                    acc.with_criterion({**base, "locked": [alias, "tests/test_b.py"]}, 0, tests=[row]),
                    0,
                    files=["scripts/a.py", CANON],
                )
                code, output = acc.check_record(record, complete=True)
                self.assertEqual(code, 1, output)
                self.assertNotEqual(acc.holding(acc.findings(output, "error"), "build-a"), [], output)

    def test_check_items_refuses_a_build_item_listing_an_alias_of_a_check_author_file(self):
        with tempfile.TemporaryDirectory() as folder:
            code, output, items_path = lane.render(folder, lane.complete_record())
            self.assertEqual(code, 0, output)
            items = lane.read_items(items_path)
            self.assertIn(CANON, lane.by_name(items)[lane.CHECK_AUTHOR]["files"])
            for alias in ALIASES:
                with self.subTest(alias=alias):
                    path = pathlib.Path(folder) / "alias.items.json"
                    copy = lane.with_item(items, "build-a", files=["scripts/a.py", alias])
                    path.write_text(json.dumps(copy, indent=2), encoding="utf-8")
                    code, output = lane.run([lane.script_path("check_items.py"), path], folder)
                    self.assertEqual(code, 1, output)
                    naming = [line for line in lane.error_lines(output) if "build-a" in line and alias in line]
                    self.assertNotEqual(naming, [], output)

    def test_schema_patterns_refuse_a_match_that_ends_before_a_trailing_newline(self):
        locked_schema = schema_check.subschema(schema_check.load("k2-locked"), "/properties/locked")
        id_schema = schema_check.subschema(schema_check.load("k1-acceptance"), "/properties/id")
        self.assertEqual(schema_check.errors(locked_schema, [CANON]), ())
        self.assertEqual(schema_check.errors(id_schema, "C1.1"), ())
        self.assertNotEqual(schema_check.errors(locked_schema, [CANON + "\n"]), ())
        self.assertNotEqual(schema_check.errors(id_schema, "C1.1\n"), ())


if __name__ == "__main__":
    unittest.main()
