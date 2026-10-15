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
    "given": "a total of 3",
    "expect": "3 is returned",
    "env": "unit-tests",
    "step": "build-app",
}
PRESENT_ENTRY = {**TEST_ENTRY, "name": "test_present", "given": "a total of 4", "expect": "4 is returned"}
PAYLOAD_DOMAIN = {
    "name": "payload",
    "over": "the payload field agent_id",
    "classes": ["absent", "present"],
    "fact": "f1",
}
PAYLOAD_ROWS = [{**TEST_ENTRY, "covers": ["payload: absent"]}, {**PRESENT_ENTRY, "covers": ["payload: present"]}]
GIVE_WAY_ROWS = [
    {**TEST_ENTRY, "covers": ["gives-way: older lines"]},
    {**TEST_ENTRY, "name": "test_header", "covers": ["gives-way: the header"]},
]
VARYING_TEST_ENTRY = {**TEST_ENTRY, "cases": 60, "runs": 3, "pass_rate": 0.9}
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
        "status": "in-progress",
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


def varying(record, kind, *tests):
    return change(record, "criteria", 0, varies=kind, tests=[VARYING_TEST_ENTRY] + list(tests))


def with_criterion(**fields):
    return change(base_record(), "criteria", 0, **fields)


class RecordFixture:
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

    def errors(self, record, complete):
        return messages(self.check(record, complete), "error")


class CheckRecordTest(RecordFixture, unittest.TestCase):
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
        empty = {"status": "in-progress", "environments": [], "facts": [], "criteria": [], "steps": []}
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

    def test_status_marks_the_run(self):
        base = base_record()
        for status in ("in-progress", "handed-off"):
            for complete in (False, True):
                with self.subTest(status=status, complete=complete):
                    self.assertEqual(self.check({**base, "status": status}, complete), ())
        absent = {key: value for key, value in base.items() if key != "status"}
        for complete in (False, True):
            for label, record in (("missing", absent), ("done", {**base, "status": "done"}), ("number", {**base, "status": 3})):
                with self.subTest(label, complete=complete):
                    errors = messages(self.check(record, complete), "error")
                    self.assertTrue(any("status" in message for message in errors), errors)

    def test_varies_accepts_only_the_three_kinds(self):
        for kind in ("input", "output", "measured"):
            with self.subTest(kind=kind):
                self.assertEqual(self.check(varying(base_record(), kind), True), ())
        for kind in ("sometimes", "Input", "", True, None, ["input"]):
            for complete in (False, True):
                with self.subTest(kind=kind, complete=complete):
                    errors = messages(self.check(varying(base_record(), kind), complete), "error")
                    self.assertEqual(len(errors), 1, errors)
                    self.assertIn("criterion 7.1", errors[0])
                    self.assertIn("varies", errors[0])

    def test_varying_test_needs_cases_runs_and_pass_rate(self):
        second = {**VARYING_TEST_ENTRY, "name": "test_total_again"}
        self.assertEqual(self.check(varying(base_record(), "output"), True), ())
        for label, fields in (
            ("one case", {"cases": 1}),
            ("two runs", {"runs": 2}),
            ("pass rate of 1", {"pass_rate": 1}),
            ("pass rate of 1.0", {"pass_rate": 1.0}),
        ):
            with self.subTest(label):
                self.assertEqual(self.check(varying(base_record(), "output", {**second, **fields}), True), ())
        removed = tuple(
            ("without %s" % key, key, {name: value for name, value in second.items() if name != key})
            for key in ("cases", "runs", "pass_rate")
        )
        broken = tuple(
            ("%s of %r" % (key, value), key, {**second, key: value})
            for key, value in (
                ("cases", 0),
                ("cases", True),
                ("cases", 60.0),
                ("cases", "60"),
                ("runs", 1),
                ("runs", True),
                ("runs", 3.5),
                ("runs", None),
                ("pass_rate", 0),
                ("pass_rate", 1.5),
                ("pass_rate", -0.5),
                ("pass_rate", True),
                ("pass_rate", "0.9"),
            )
        )
        for label, key, test in removed + broken:
            for complete in (False, True):
                with self.subTest(label, complete=complete):
                    errors = messages(self.check(varying(base_record(), "input", test), complete), "error")
                    self.assertEqual(len(errors), 1, errors)
                    self.assertIn("criterion 7.1 test 2", errors[0])
                    self.assertIn(key, errors[0])

    def test_unproven_varying_criterion_needs_no_population(self):
        for kind in ("input", "output", "measured"):
            with self.subTest(kind=kind):
                record = change(
                    base_record(), "criteria", 0, varies=kind, where=["phone"], tests=[], unproven="needs the phone"
                )
                self.assertEqual(self.check(record, True), ())

    def test_records_without_varies_check_as_before(self):
        base = base_record()
        self.assertEqual(self.check(base, True), ())
        for key in ("cases", "runs", "pass_rate"):
            value = VARYING_TEST_ENTRY[key]
            with self.subTest(key=key):
                named = change(base, "criteria", 0, tests=[{**TEST_ENTRY, key: value}])
                other = change(base, "criteria", 0, tests=[{**TEST_ENTRY, "colour": value}])
                expected = tuple(
                    (level, message.replace("'colour'", repr(key))) for level, message in self.check(other, True)
                )
                self.assertTrue(expected)
                self.assertEqual(self.check(named, True), expected)
        populated = change(base, "criteria", 0, tests=[VARYING_TEST_ENTRY])
        self.assertEqual(len(messages(self.check(populated, True), "error")), 3)
        self.assertEqual(self.check(change(populated, "criteria", 0, varies="output"), True), ())

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


class CaseTableRecordTest(RecordFixture, unittest.TestCase):
    def test_record_without_domains_has_no_error(self):
        record = base_record()
        self.assertNotIn("domains", record["criteria"][0])
        self.assertEqual(record["criteria"][0]["tests"][0]["given"], "a total of 3")
        self.assertEqual(record["criteria"][0]["tests"][0]["expect"], "3 is returned")
        self.assertEqual(self.errors(record, True), ())

    def test_domains_that_is_not_a_list_is_an_error(self):
        errors = self.errors(with_criterion(domains="payload"), False)
        self.assertIn("criterion 7.1 has domains that is not a non-empty list", errors)

    def test_empty_domains_is_an_error(self):
        errors = self.errors(with_criterion(domains=[]), False)
        self.assertIn("criterion 7.1 has domains that is not a non-empty list", errors)

    def test_domain_that_is_not_an_object_is_an_error(self):
        errors = self.errors(with_criterion(domains=["payload"]), False)
        self.assertIn("criterion 7.1 domain 1 is not an object", errors)

    def test_domain_with_an_unknown_key_is_an_error(self):
        record = with_criterion(domains=[{**PAYLOAD_DOMAIN, "note": "checked by hand"}], tests=PAYLOAD_ROWS)
        self.assertIn("criterion 7.1 domain 'payload' has unknown key 'note'", self.errors(record, False))

    def test_domain_lacking_a_key_is_an_error(self):
        domain = {"name": "payload", "over": "the payload field agent_id", "fact": "f1"}
        errors = self.errors(with_criterion(domains=[domain]), False)
        self.assertIn("criterion 7.1 domain 'payload' lacks required key 'classes'", errors)

    def test_domain_name_that_is_not_a_string_is_an_error(self):
        errors = self.errors(with_criterion(domains=[{**PAYLOAD_DOMAIN, "name": 3}]), False)
        self.assertIn("criterion 7.1 domain 1 has a name that is not lowercase kebab-case", errors)

    def test_domain_without_a_fact_is_accepted(self):
        domain = {"name": "payload", "over": "the payload field agent_id", "classes": ["absent", "present"]}
        record = with_criterion(domains=[domain], tests=PAYLOAD_ROWS)
        self.assertEqual(self.errors(record, True), ())

    def test_domain_fact_that_is_not_a_string_is_an_error(self):
        record = with_criterion(domains=[{**PAYLOAD_DOMAIN, "fact": ["f1"]}], tests=PAYLOAD_ROWS)
        errors = self.errors(record, False)
        self.assertIn("criterion 7.1 domain 'payload' has fact that is not a non-empty string", errors)

    def test_domain_name_that_is_not_kebab_case_is_an_error(self):
        errors = self.errors(with_criterion(domains=[{**PAYLOAD_DOMAIN, "name": "Payload Field"}]), False)
        self.assertIn("criterion 7.1 domain 'Payload Field' has a name that is not lowercase kebab-case", errors)

    def test_domain_with_the_reserved_name_is_an_error(self):
        errors = self.errors(with_criterion(domains=[{**PAYLOAD_DOMAIN, "name": "gives-way"}]), False)
        self.assertIn("criterion 7.1 domain 'gives-way' uses the reserved name 'gives-way'", errors)

    def test_domain_name_used_twice_is_an_error(self):
        record = with_criterion(domains=[PAYLOAD_DOMAIN, PAYLOAD_DOMAIN], tests=PAYLOAD_ROWS)
        self.assertIn("criterion 7.1 domain name 'payload' is duplicated", self.errors(record, False))

    def test_domain_with_a_blank_over_is_an_error(self):
        record = with_criterion(domains=[{**PAYLOAD_DOMAIN, "over": ""}], tests=PAYLOAD_ROWS)
        errors = self.errors(record, False)
        self.assertIn("criterion 7.1 domain 'payload' has over that is not a non-empty string", errors)

    def test_domain_with_one_class_is_an_error(self):
        record = with_criterion(domains=[{**PAYLOAD_DOMAIN, "classes": ["absent"]}], tests=PAYLOAD_ROWS)
        self.assertIn(
            "criterion 7.1 domain 'payload' has classes that is not a list of at least two non-empty strings",
            self.errors(record, False),
        )

    def test_domain_with_a_blank_class_is_an_error(self):
        record = with_criterion(domains=[{**PAYLOAD_DOMAIN, "classes": ["absent", ""]}], tests=PAYLOAD_ROWS)
        self.assertIn(
            "criterion 7.1 domain 'payload' has classes that is not a list of at least two non-empty strings",
            self.errors(record, False),
        )

    def test_domain_with_a_repeated_class_is_an_error(self):
        domain = {**PAYLOAD_DOMAIN, "classes": ["absent", "absent", "present"]}
        record = with_criterion(domains=[domain], tests=PAYLOAD_ROWS)
        self.assertIn("criterion 7.1 domain 'payload' lists class 'absent' more than once", self.errors(record, False))

    def test_domain_naming_an_unknown_fact_is_an_error(self):
        record = with_criterion(domains=[{**PAYLOAD_DOMAIN, "fact": "f9"}], tests=PAYLOAD_ROWS)
        self.assertIn("criterion 7.1 domain 'payload' names unknown fact 'f9'", self.errors(record, False))

    def test_well_formed_domain_has_no_error(self):
        record = with_criterion(domains=[PAYLOAD_DOMAIN], tests=PAYLOAD_ROWS)
        self.assertEqual(self.errors(record, True), ())

    def test_gives_way_that_is_not_a_list_is_an_error(self):
        errors = self.errors(with_criterion(gives_way="older lines"), False)
        self.assertIn("criterion 7.1 has gives_way that is not a non-empty list of non-empty strings", errors)

    def test_empty_gives_way_is_an_error(self):
        errors = self.errors(with_criterion(gives_way=[]), False)
        self.assertIn("criterion 7.1 has gives_way that is not a non-empty list of non-empty strings", errors)

    def test_gives_way_with_a_blank_item_is_an_error(self):
        errors = self.errors(with_criterion(gives_way=["older lines", ""]), False)
        self.assertIn("criterion 7.1 has gives_way that is not a non-empty list of non-empty strings", errors)

    def test_gives_way_with_a_repeated_item_is_an_error(self):
        record = with_criterion(gives_way=["older lines", "older lines"], tests=GIVE_WAY_ROWS[:1])
        self.assertIn("criterion 7.1 lists give-way item 'older lines' more than once", self.errors(record, False))

    def test_well_formed_gives_way_has_no_error(self):
        record = with_criterion(
            text="WHEN the log is shown THE SYSTEM SHALL show at most 40 lines",
            gives_way=["older lines", "the header"],
            tests=GIVE_WAY_ROWS,
        )
        self.assertEqual(self.errors(record, True), ())

    def test_criterion_facts_that_is_not_a_list_is_an_error(self):
        errors = self.errors(with_criterion(facts="f1"), False)
        self.assertIn("criterion 7.1 has facts that is not a non-empty list of strings", errors)

    def test_empty_criterion_facts_is_an_error(self):
        errors = self.errors(with_criterion(facts=[]), False)
        self.assertIn("criterion 7.1 has facts that is not a non-empty list of strings", errors)

    def test_criterion_fact_with_an_unknown_id_is_an_error(self):
        errors = self.errors(with_criterion(facts=["f9"]), False)
        self.assertIn("criterion 7.1 names unknown fact 'f9'", errors)

    def test_criterion_fact_listed_twice_is_an_error(self):
        errors = self.errors(with_criterion(facts=["f1", "f1"]), False)
        self.assertIn("criterion 7.1 lists fact 'f1' more than once", errors)

    def test_well_formed_criterion_facts_have_no_error(self):
        self.assertEqual(self.errors(with_criterion(facts=["f1"]), True), ())

    def test_quantifier_word_needs_no_domain(self):
        for word in ("every", "each", "any", "all", "whole", "always", "never", "whatever", "however", "whenever"):
            with self.subTest(word=word):
                record = with_criterion(text="WHEN a line is shown THE SYSTEM SHALL keep %s field" % word)
                self.assertEqual(self.check(record, True), ())

    def test_each_bound_phrase_warns_without_a_give_way_order(self):
        phrases = (
            "at most",
            "no more than",
            "up to",
            "maximum",
            "budget",
            "limit",
            "limits",
            "cap",
            "caps",
            "exceed",
            "exceeds",
            "exceeding",
        )
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                record = with_criterion(text="WHEN the log is shown THE SYSTEM SHALL show %s 40 lines" % phrase)
                findings = self.check(record, True)
                self.assertEqual(
                    messages(findings, "warning"),
                    ("criterion 7.1 sets a bound with '%s' but lists nothing in gives_way" % phrase,),
                )
                self.assertEqual(messages(findings, "error"), ())

    def test_bound_without_give_way_warns_when_complete_too(self):
        record = with_criterion(text="WHEN the log is shown THE SYSTEM SHALL show at most 40 lines")
        findings = self.check(record, True)
        self.assertIn(
            "criterion 7.1 sets a bound with 'at most' but lists nothing in gives_way", messages(findings, "warning")
        )
        self.assertEqual(messages(findings, "error"), ())

    def test_bound_with_give_way_has_no_bound_finding(self):
        record = with_criterion(
            text="WHEN the log is shown THE SYSTEM SHALL show at most 40 lines",
            gives_way=["older lines", "the header"],
            tests=GIVE_WAY_ROWS,
        )
        self.assertEqual(self.errors(record, True), ())

    def test_bound_phrase_in_capitals_and_across_lines_is_matched(self):
        record = with_criterion(text="WHEN the log is shown THE SYSTEM SHALL show AT\nMOST 40 lines")
        self.assertEqual(
            messages(self.check(record, True), "warning"), ("criterion 7.1 sets a bound with 'at most' but lists nothing in gives_way",)
        )

    def test_bound_inside_a_longer_word_is_ignored(self):
        text = "WHEN the capture of capital upstream data is shown THE SYSTEM SHALL maximise its use"
        self.assertEqual(self.check(with_criterion(text=text), True), ())
        self.assertEqual(
            messages(self.check(with_criterion(text=text + " up to 3 times"), True), "warning"),
            ("criterion 7.1 sets a bound with 'up to' but lists nothing in gives_way",),
        )

    def test_row_without_covers_is_accepted(self):
        record = base_record()
        self.assertNotIn("covers", record["criteria"][0]["tests"][0])
        self.assertEqual(self.errors(record, True), ())

    def test_covers_that_is_not_a_list_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": "payload: absent"}, PAYLOAD_ROWS[1]]
        errors = self.errors(with_criterion(domains=[PAYLOAD_DOMAIN], tests=tests), False)
        self.assertIn(
            "criterion 7.1 test 'test_total' has covers that is not a non-empty list of non-empty strings", errors
        )

    def test_empty_covers_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": []}, PAYLOAD_ROWS[1]]
        errors = self.errors(with_criterion(domains=[PAYLOAD_DOMAIN], tests=tests), False)
        self.assertIn(
            "criterion 7.1 test 'test_total' has covers that is not a non-empty list of non-empty strings", errors
        )

    def test_covers_entry_without_a_separator_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": ["payload absent"]}, PAYLOAD_ROWS[1]]
        errors = self.errors(with_criterion(domains=[PAYLOAD_DOMAIN], tests=tests), False)
        self.assertIn(
            "criterion 7.1 test 'test_total' covers 'payload absent', which is not '<domain>: <class>' or "
            "'gives-way: <item>'",
            errors,
        )

    def test_covers_naming_an_unknown_domain_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": ["cwd: subfolder"]}, PAYLOAD_ROWS[1]]
        errors = self.errors(with_criterion(domains=[PAYLOAD_DOMAIN], tests=tests), False)
        self.assertIn("criterion 7.1 test 'test_total' covers unknown domain 'cwd'", errors)

    def test_covers_naming_an_unknown_class_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": ["payload: truncated"]}, PAYLOAD_ROWS[1]]
        errors = self.errors(with_criterion(domains=[PAYLOAD_DOMAIN], tests=tests), False)
        self.assertIn("criterion 7.1 test 'test_total' covers unknown class 'truncated' of domain 'payload'", errors)

    def test_covers_naming_an_unknown_give_way_item_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": ["gives-way: newest lines"]}, GIVE_WAY_ROWS[1]]
        errors = self.errors(with_criterion(gives_way=["older lines", "the header"], tests=tests), False)
        self.assertIn("criterion 7.1 test 'test_total' covers unknown give-way item 'newest lines'", errors)

    def test_class_holding_a_colon_is_covered(self):
        domain = {**PAYLOAD_DOMAIN, "classes": ["key: value", "absent"]}
        tests = [{**TEST_ENTRY, "covers": ["payload: key: value"]}, {**PRESENT_ENTRY, "covers": ["payload: absent"]}]
        self.assertEqual(self.errors(with_criterion(domains=[domain], tests=tests), True), ())

    def test_uncovered_class_warns_before_complete(self):
        record = with_criterion(domains=[PAYLOAD_DOMAIN], tests=[{**TEST_ENTRY, "covers": ["payload: absent"]}])
        findings = self.check(record, False)
        self.assertIn(
            "criterion 7.1 has no test covering class 'present' of domain 'payload'", messages(findings, "warning")
        )
        self.assertEqual(messages(findings, "error"), ())

    def test_uncovered_class_is_an_error_when_complete(self):
        record = with_criterion(domains=[PAYLOAD_DOMAIN], tests=[{**TEST_ENTRY, "covers": ["payload: absent"]}])
        self.assertIn(
            "criterion 7.1 has no test covering class 'present' of domain 'payload'", self.errors(record, True)
        )

    def test_uncovered_give_way_item_is_an_error_when_complete(self):
        record = with_criterion(
            gives_way=["older lines", "the header"], tests=[{**TEST_ENTRY, "covers": ["gives-way: older lines"]}]
        )
        self.assertIn("criterion 7.1 has no test covering give-way item 'the header'", self.errors(record, True))

    def test_unproven_criterion_needs_no_coverage(self):
        record = with_criterion(domains=[PAYLOAD_DOMAIN], where=["phone"], tests=[], unproven="needs the phone")
        self.assertEqual(self.check(record, True), ())

    def test_row_without_given_is_an_error(self):
        test = {
            "file": "tests/test_app.py",
            "name": "test_total",
            "expect": "3 is returned",
            "env": "unit-tests",
            "step": "build-app",
        }
        self.assertIn(
            "criterion 7.1 test 'test_total' is not an object with non-empty string file, name, given, expect, env "
            "and step",
            self.errors(with_criterion(tests=[test]), False),
        )

    def test_row_without_expect_is_an_error(self):
        test = {
            "file": "tests/test_app.py",
            "name": "test_total",
            "given": "a total of 3",
            "env": "unit-tests",
            "step": "build-app",
        }
        self.assertIn(
            "criterion 7.1 test 'test_total' is not an object with non-empty string file, name, given, expect, env "
            "and step",
            self.errors(with_criterion(tests=[test]), False),
        )

    def test_row_with_asserts_is_an_error(self):
        test = {**TEST_ENTRY, "asserts": "the total adds up"}
        self.assertIn(
            "criterion 7.1 test 'test_total' has unknown key 'asserts'",
            self.errors(with_criterion(tests=[test]), False),
        )

    def test_row_with_given_and_expect_is_accepted(self):
        test = {
            "file": "tests/test_app.py",
            "name": "test_total",
            "given": "a total of 3",
            "expect": "3 is returned",
            "env": "unit-tests",
            "step": "build-app",
        }
        self.assertEqual(self.errors(with_criterion(tests=[test]), True), ())

    def test_outside_fact_cited_by_command_is_accepted(self):
        record = change(base_record(), "facts", 1, outside=True)
        self.assertEqual(record["facts"][1]["command"], "python3 -m unittest")
        self.assertEqual(self.errors(record, True), ())

    def test_outside_fact_cited_by_location_is_an_error(self):
        record = change(base_record(), "facts", 0, outside=True)
        self.assertIn(
            "fact 'f1' is marked outside but is not cited by command and output", self.errors(record, False)
        )

    def test_outside_fact_cited_by_url_is_an_error(self):
        fact = {"id": "f3", "fact": "The format is documented", "url": "https://example.com/a", "outside": True}
        record = append(base_record(), "facts", fact)
        self.assertIn(
            "fact 'f3' is marked outside but is not cited by command and output", self.errors(record, False)
        )

    def test_outside_that_is_not_a_boolean_is_an_error(self):
        record = change(base_record(), "facts", 0, outside="yes")
        self.assertIn("fact 'f1' has outside that is not true or false", self.errors(record, False))

    def test_inside_fact_cited_by_location_is_accepted(self):
        record = change(base_record(), "facts", 0, outside=False)
        self.assertNotIn("outside", record["facts"][1])
        self.assertEqual(self.errors(record, True), ())


class AmendmentRecordTest(RecordFixture, unittest.TestCase):
    def test_steps_with_and_without_amendment_are_accepted(self):
        fix = {
            "name": "fix-app",
            "files": ["src/app.py"],
            "criteria": ["7.1"],
            "task": "Fix the app.",
            "amendment": 1,
            "after": ["build-app"],
        }
        record = append(base_record(), "steps", fix)
        self.assertNotIn("amendment", record["steps"][0])
        self.assertEqual(self.errors(record, True), ())

    def test_amendment_zero_is_an_error(self):
        record = change(base_record(), "steps", 0, amendment=0)
        self.assertIn(
            "step 'build-app' has amendment that is not an integer of at least 1", self.errors(record, False)
        )

    def test_amendment_true_is_an_error(self):
        record = change(base_record(), "steps", 0, amendment=True)
        self.assertIn(
            "step 'build-app' has amendment that is not an integer of at least 1", self.errors(record, False)
        )

    def test_amendment_string_is_an_error(self):
        record = change(base_record(), "steps", 0, amendment="1")
        self.assertIn(
            "step 'build-app' has amendment that is not an integer of at least 1", self.errors(record, False)
        )


if __name__ == "__main__":
    unittest.main()
