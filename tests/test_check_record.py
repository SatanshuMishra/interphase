import contextlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest

SOURCE_TEXT = "def total_of(total):\n    return total\n"
TEST_ENTRY = {
    "file": "tests/test_app.py",
    "name": "test_total",
    "asserts": "the total adds up",
    "env": "unit-tests",
    "step": "build-app",
}
UNCLAIMED_CRITERION = {
    "number": "7.2",
    "title": "The total shows on the phone",
    "text": "The total appears on the phone.",
    "where": ["phone"],
    "tests": [],
    "unproven": "needs the phone",
}


def base_record():
    return {
        "environments": [
            {"name": "unit-tests", "what": "python3 -m unittest on macOS", "builder_runs": True},
            {"name": "phone", "what": "Galaxy Note10+, Android 12, Impeller renderer", "builder_runs": False},
        ],
        "facts": [
            {
                "id": "f1",
                "fact": "The app returns the total it is given",
                "path": "src/app.py",
                "line": 2,
                "quote": "return total",
            },
            {"id": "f2", "fact": "The suite passes", "command": "python3 -m unittest", "output": "OK"},
        ],
        "criteria": [
            {
                "number": "7.1",
                "title": "The total adds up",
                "text": "Given a total, when the app returns it, then it is unchanged.",
                "where": ["unit-tests"],
                "tests": [TEST_ENTRY],
            }
        ],
        "steps": [
            {
                "name": "build-app",
                "files": ["src/app.py", "tests/test_app.py"],
                "criteria": ["7.1"],
                "task": "Build the app.",
            }
        ],
    }


def replace_at(record, key, index, item):
    items = record[key]
    return {**record, key: items[:index] + [item] + items[index + 1 :]}


def change(record, key, index, **fields):
    return replace_at(record, key, index, {**record[key][index], **fields})


def without(record, key, index, field):
    return replace_at(record, key, index, {name: value for name, value in record[key][index].items() if name != field})


def append(record, key, item):
    return {**record, key: record[key] + [item]}


def messages(findings, severity):
    return tuple(message for level, message in findings if level == severity)


class CheckRecordTest(unittest.TestCase):
    def load(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("check_record", str(root / "scripts" / "check_record.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def write_source(self, folder):
        source = pathlib.Path(folder) / "src"
        source.mkdir()
        (source / "app.py").write_text(SOURCE_TEXT, encoding="utf-8")

    def check(self, record, complete):
        module = self.load()
        with tempfile.TemporaryDirectory() as folder:
            self.write_source(folder)
            return module.check(json.dumps(record), folder, complete=complete)

    def run_main(self, argv, content=None):
        module = self.load()
        with tempfile.TemporaryDirectory() as folder:
            self.write_source(folder)
            if content is not None:
                (pathlib.Path(folder) / "record.json").write_text(content, encoding="utf-8")
            out = io.StringIO()
            err = io.StringIO()
            previous = os.getcwd()
            os.chdir(folder)
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = module.main(argv)
            finally:
                os.chdir(previous)
        return code, out.getvalue(), err.getvalue()

    def test_complete_record_passes(self):
        record = base_record()
        self.assertEqual(self.check(record, True), ())
        for argv in (["--complete", "record.json"], ["record.json", "--complete"]):
            with self.subTest(argv=argv):
                code, out, _ = self.run_main(argv, json.dumps(record))
                self.assertEqual(code, 0)
                self.assertEqual(out, "")

    def test_wrong_citation_is_an_error(self):
        base = base_record()
        variants = (
            ("f1", "quote not in the line", change(base, "facts", 0, quote="return subtotal")),
            ("f1", "line past the end", change(base, "facts", 0, line=99)),
            ("f1", "missing file", change(base, "facts", 0, path="src/missing.py")),
            ("f1", "absolute path", change(base, "facts", 0, path="/etc/hosts")),
            ("f1", "parent segment", change(base, "facts", 0, path="src/../../app.py")),
            ("f2", "empty output", change(base, "facts", 1, output="")),
        )
        for fact_id, label, record in variants:
            for complete in (False, True):
                with self.subTest(label, complete=complete):
                    errors = messages(self.check(record, complete), "error")
                    self.assertTrue(any(fact_id in message for message in errors), errors)
        code, out, _ = self.run_main(["record.json"], json.dumps(variants[0][2]))
        self.assertEqual(code, 1)
        self.assertTrue(any(line.startswith("error: ") and "f1" in line for line in out.splitlines()), out)
        self.assertEqual(self.check(change(base, "facts", 0, quote="  return total  "), True), ())

    def test_test_outside_where_fails_when_complete(self):
        record = change(base_record(), "criteria", 0, where=["phone"])
        loose = self.check(record, False)
        found = tuple(message for message in messages(loose, "warning") if "7.1" in message)
        self.assertTrue(found, loose)
        self.assertEqual(messages(loose, "error"), ())
        code, _, _ = self.run_main(["record.json"], json.dumps(record))
        self.assertEqual(code, 0)
        strict = messages(self.check(record, True), "error")
        self.assertTrue(all(message in strict for message in found), strict)
        code, _, _ = self.run_main(["--complete", "record.json"], json.dumps(record))
        self.assertEqual(code, 1)

    def test_unproven_mark_satisfies_the_where_rule(self):
        marked = change(base_record(), "criteria", 0, where=["phone"], unproven="needs the phone")
        self.assertEqual(self.check(marked, True), ())
        conflicting = change(base_record(), "criteria", 0, unproven="needs the phone")
        for complete in (False, True):
            with self.subTest(complete=complete):
                errors = messages(self.check(conflicting, complete), "error")
                self.assertTrue(any("7.1" in message for message in errors), errors)

    def test_unknown_names_and_mismatches_are_errors(self):
        base = base_record()
        shown = {
            "number": "7.2",
            "title": "The total is shown",
            "text": "The app shows the total.",
            "where": ["unit-tests"],
            "tests": [{**TEST_ENTRY, "name": "test_total_is_shown"}],
        }
        tune = {"name": "tune-app", "files": ["src/tune.py"], "criteria": ["7.1"], "after": ["build-app"]}
        pixel = {"name": "phone", "what": "Pixel 8, Android 14", "builder_runs": False}
        variants = (
            ("where names an unknown environment", "tablet", change(base, "criteria", 0, where=["tablet"])),
            (
                "test names an unknown environment",
                "tablet",
                change(base, "criteria", 0, tests=[{**TEST_ENTRY, "env": "tablet"}]),
            ),
            ("test names an unknown step", "ghost", change(base, "criteria", 0, tests=[{**TEST_ENTRY, "step": "ghost"}])),
            (
                "test file is not in its step",
                "tests/other.py",
                change(base, "criteria", 0, tests=[{**TEST_ENTRY, "file": "tests/other.py"}]),
            ),
            (
                "test step does not claim its criterion",
                "7.1",
                append(change(base, "steps", 0, criteria=["7.2"]), "criteria", shown),
            ),
            ("step claims an unknown criterion", "7.9", change(base, "steps", 0, criteria=["7.1", "7.9"])),
            ("after names an unknown step", "ghost", change(base, "steps", 0, after=["ghost"])),
            ("after edges form a cycle", "cycle", append(change(base, "steps", 0, after=["tune-app"]), "steps", tune)),
            ("complexity is not allowed", "complexity", change(base, "steps", 0, complexity="hard")),
            ("environment name is duplicated", "phone", append(base, "environments", pixel)),
            ("criterion number is duplicated", "7.1", append(base, "criteria", base["criteria"][0])),
            (
                "step holds a field the render script fills",
                "acceptance",
                change(base, "steps", 0, acceptance=[{"file": "tests/test_app.py", "test": "test_total"}]),
            ),
            ("criterion number is not digits, a dot and digits", "7.a", change(base, "criteria", 0, number="7.a")),
        )
        for label, fragment, record in variants:
            with self.subTest(label):
                errors = messages(self.check(record, False), "error")
                self.assertTrue(any(fragment in message for message in errors), errors)

    def test_missing_parts_warn_until_complete(self):
        empty = {"environments": [], "facts": [], "criteria": [], "steps": []}
        loose = self.check(empty, False)
        self.assertEqual(len(messages(loose, "warning")), 3, loose)
        self.assertEqual(messages(loose, "error"), ())
        strict = self.check(empty, True)
        self.assertEqual(len(messages(strict, "error")), 3, strict)
        self.assertEqual(len(strict), 3, strict)
        code, _, _ = self.run_main(["record.json"], json.dumps(empty))
        self.assertEqual(code, 0)
        code, _, _ = self.run_main(["--complete", "record.json"], json.dumps(empty))
        self.assertEqual(code, 1)
        self.assertEqual(self.check(without(base_record(), "steps", 0, "task"), True), ())
        unclaimed = append(base_record(), "criteria", UNCLAIMED_CRITERION)
        loose = self.check(unclaimed, False)
        self.assertTrue(any("7.2" in message for message in messages(loose, "warning")), loose)
        self.assertEqual(messages(loose, "error"), ())
        strict = self.check(unclaimed, True)
        self.assertTrue(any("7.2" in message for message in messages(strict, "error")), strict)

    def test_exit_codes_and_usage(self):
        record = json.dumps(base_record())
        code, _, err = self.run_main([])
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)
        code, _, err = self.run_main(["--strict", "record.json"], record)
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)
        code, _, err = self.run_main(["record.json", "src/app.py"], record)
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)
        code, _, err = self.run_main(["missing.json"])
        self.assertEqual(code, 2)
        self.assertIn("cannot read:", err)
        code, out, _ = self.run_main(["record.json"], "{not json")
        self.assertEqual(code, 1)
        self.assertTrue(any(line.startswith("error:") for line in out.splitlines()), out)


if __name__ == "__main__":
    unittest.main()
