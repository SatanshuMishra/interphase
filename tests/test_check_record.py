import contextlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest

TEST_ENTRY = {
    "file": "tests/test_app.py",
    "name": "test_total",
    "given": "a total of 3",
    "expect": "3 is returned",
    "step": "build-app",
    "check": "C1.1",
}
UNCHECKED_ENTRY = {key: value for key, value in TEST_ENTRY.items() if key != "check"}
PRESENT_ENTRY = {**TEST_ENTRY, "name": "test_present", "given": "a total of 4", "expect": "4 is returned"}
PAYLOAD_DOMAIN = {
    "name": "payload",
    "over": "the payload field agent_id",
    "classes": ["absent", "present"],
}
PAYLOAD_ROWS = [{**TEST_ENTRY, "covers": ["payload: absent"]}, {**PRESENT_ENTRY, "covers": ["payload: present"]}]
VARYING_TEST_ENTRY = {**TEST_ENTRY, "cases": 60, "runs": 3, "pass_rate": 0.9}
UNIT_SEAM = {
    "name": "unit-tests",
    "interface": "the total_of function in src/app.py",
    "catches": "a wrong total",
    "misses": "how the total is drawn on screen",
    "builder_runs": True,
}
PHONE_SEAM = {
    "name": "phone-screen",
    "interface": "the total drawn on a Galaxy Note10+",
    "catches": "a total drawn late",
    "misses": "a wrong total",
    "builder_runs": False,
}
APP_LINE = {
    "id": "C1.1",
    "kind": "exact",
    "surface": {"family": "cli", "target": "python3"},
    "command": "python3 -m unittest tests.test_app",
    "pass": "the test passes",
}
APP_PROBE = {"check": "C1.1", "probe": "command", "target": "python3", "status": "pass", "detail": "/usr/bin/python3"}
OUTCOMES = {"store": "/var/empty/trajectories.jsonl", "entries": 0, "repeated": []}
PHONE_CRITERION = {
    "number": "5.2",
    "title": "The total shows on the phone",
    "text": "The total appears on the phone.",
    "seam": "phone-screen",
    "tests": [],
    "unproven": "needs the phone",
}


def base_record():
    return {
        "status": "in-progress",
        "seams": [dict(UNIT_SEAM)],
        "criteria": [
            {
                "number": "5.1",
                "title": "The total adds up",
                "text": "Given a total, when the app returns it, then it is unchanged.",
                "seam": "unit-tests",
                "acceptance": [APP_LINE],
                "tests": [TEST_ENTRY],
            }
        ],
        "steps": [
            {
                "name": "build-app",
                "files": ["src/app.py"],
                "criteria": ["5.1"],
                "task": "Build the app.",
            }
        ],
        "locked": ["tests/test_app.py"],
        "probes": [APP_PROBE],
        "outcomes": OUTCOMES,
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


def with_table(**fields):
    return with_criterion(**{"case_table": "security", "domains": [PAYLOAD_DOMAIN], "tests": PAYLOAD_ROWS, **fields})


def with_phone():
    record = append(append(base_record(), "seams", dict(PHONE_SEAM)), "criteria", dict(PHONE_CRITERION))
    return change(record, "steps", 0, criteria=["5.1", "5.2"])


class RecordFixture:
    def load(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("check_record", str(root / "scripts" / "check_record.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def check(self, record, complete):
        return self.load().check(json.dumps(record), complete=complete)

    def run_main(self, argv, content=None):
        module = self.load()
        with tempfile.TemporaryDirectory() as folder:
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
        for label, record in (("one seam", base_record()), ("two seams", with_phone())):
            with self.subTest(label):
                self.assertEqual(self.check(record, True), ())
                for argv in (["--complete", "record.json"], ["record.json", "--complete"]):
                    with self.subTest(argv=argv):
                        code, out, _ = self.run_main(argv, json.dumps(record))
                        self.assertEqual(code, 0)
                        self.assertEqual(out, "")

    def test_unknown_names_and_mismatches_are_errors(self):
        base = base_record()
        shown = {
            "number": "5.2",
            "title": "The total is shown",
            "text": "The app shows the total.",
            "seam": "unit-tests",
            "tests": [{**TEST_ENTRY, "name": "test_total_is_shown"}],
        }
        tune = {"name": "tune-app", "files": ["src/tune.py"], "criteria": ["5.1"], "after": ["build-app"]}
        variants = (
            ("criterion names an unknown seam", "tablet", change(base, "criteria", 0, seam="tablet")),
            ("test names an unknown step", "ghost", change(base, "criteria", 0, tests=[{**TEST_ENTRY, "step": "ghost"}])),
            (
                "test file is not in its step",
                "tests/other.py",
                change(base, "criteria", 0, tests=[{**TEST_ENTRY, "file": "tests/other.py"}]),
            ),
            (
                "test step does not claim its criterion",
                "5.1",
                append(change(base, "steps", 0, criteria=["5.2"]), "criteria", shown),
            ),
            ("step claims an unknown criterion", "5.9", change(base, "steps", 0, criteria=["5.1", "5.9"])),
            ("after names an unknown step", "ghost", change(base, "steps", 0, after=["ghost"])),
            ("after edges form a cycle", "cycle", append(change(base, "steps", 0, after=["tune-app"]), "steps", tune)),
            ("complexity is not allowed", "complexity", change(base, "steps", 0, complexity="hard")),
            ("seam name is duplicated", "unit-tests", append(base, "seams", dict(UNIT_SEAM))),
            ("criterion number is duplicated", "5.1", append(base, "criteria", base["criteria"][0])),
            (
                "step holds a field the render script fills",
                "acceptance",
                change(base, "steps", 0, acceptance=[{"file": "tests/test_app.py", "test": "test_total"}]),
            ),
            ("criterion number is not digits, a dot and digits", "5.a", change(base, "criteria", 0, number="5.a")),
        )
        for label, fragment, record in variants:
            with self.subTest(label):
                errors = messages(self.check(record, False), "error")
                self.assertTrue(any(fragment in message for message in errors), errors)

    def test_missing_parts_warn_until_complete(self):
        empty = {"status": "in-progress", "seams": [], "criteria": [], "steps": []}
        expected = ("record has no seams", "record has no criteria", "record has no steps")
        loose = self.check(empty, False)
        self.assertEqual(messages(loose, "warning"), expected)
        self.assertEqual(messages(loose, "error"), ())
        strict = self.check(empty, True)
        self.assertEqual(messages(strict, "error"), expected)
        self.assertEqual(len(strict), 3, strict)
        code, _, _ = self.run_main(["record.json"], json.dumps(empty))
        self.assertEqual(code, 0)
        code, _, _ = self.run_main(["--complete", "record.json"], json.dumps(empty))
        self.assertEqual(code, 1)
        self.assertEqual(self.check(without(base_record(), "steps", 0, "task"), True), ())
        unclaimed = change(with_phone(), "steps", 0, criteria=["5.1"])
        loose = self.check(unclaimed, False)
        self.assertEqual(messages(loose, "warning"), ("criterion 5.2 is claimed by no step",))
        self.assertEqual(messages(loose, "error"), ())
        self.assertEqual(self.errors(unclaimed, True), ("criterion 5.2 is claimed by no step",))

    def test_old_record_keys_are_unknown(self):
        old = {key: value for key, value in base_record().items() if key != "seams"}
        record = {
            **old,
            "environments": [{"name": "unit-tests", "what": "python3 -m unittest", "builder_runs": True}],
            "facts": [],
        }
        errors = self.errors(record, False)
        for message in (
            "record has unknown key 'environments'",
            "record has unknown key 'facts'",
            "record lacks key 'seams'",
        ):
            with self.subTest(message=message):
                self.assertIn(message, errors)

    def test_old_criterion_and_test_keys_are_unknown(self):
        variants = (
            ("where", with_criterion(where=["unit-tests"]), "criterion 5.1 has unknown key 'where'"),
            ("facts", with_criterion(facts=["f1"]), "criterion 5.1 has unknown key 'facts'"),
            ("gives_way", with_criterion(gives_way=["older lines"]), "criterion 5.1 has unknown key 'gives_way'"),
            (
                "env",
                with_criterion(tests=[{**TEST_ENTRY, "env": "unit-tests"}]),
                "criterion 5.1 test 'test_total' has unknown key 'env'",
            ),
        )
        for label, record, message in variants:
            with self.subTest(label):
                self.assertEqual(self.errors(record, False), (message,))

    def test_criterion_lacking_a_required_key_is_an_error(self):
        for key in ("title", "text", "seam", "tests"):
            with self.subTest(key=key):
                record = without(base_record(), "criteria", 0, key)
                self.assertIn("criterion 5.1 lacks required key %r" % key, self.errors(record, False))

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
                    self.assertIn("criterion 5.1", errors[0])
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
                    self.assertIn("criterion 5.1 test 2", errors[0])
                    self.assertIn(key, errors[0])

    def test_unproven_varying_criterion_needs_no_population(self):
        for kind in ("input", "output", "measured"):
            with self.subTest(kind=kind):
                record = change(with_phone(), "criteria", 1, varies=kind)
                self.assertEqual(self.check(record, True), ())

    def test_population_keys_without_varies_are_unknown(self):
        for key in ("cases", "runs", "pass_rate"):
            with self.subTest(key=key):
                record = with_criterion(tests=[{**TEST_ENTRY, key: VARYING_TEST_ENTRY[key]}])
                self.assertEqual(self.check(record, True), (("error", "criterion 5.1 test 'test_total' has unknown key %r" % key),))
        populated = with_criterion(tests=[VARYING_TEST_ENTRY])
        self.assertEqual(
            self.errors(populated, True),
            (
                "criterion 5.1 test 'test_total' has unknown key 'cases'",
                "criterion 5.1 test 'test_total' has unknown key 'pass_rate'",
                "criterion 5.1 test 'test_total' has unknown key 'runs'",
            ),
        )
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
        code, _, err = self.run_main(["--complete", "--complete", "record.json"], record)
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)
        code, _, err = self.run_main(["missing.json"])
        self.assertEqual(code, 2)
        self.assertIn("cannot read:", err)
        code, out, _ = self.run_main(["record.json"], "{not json")
        self.assertEqual(code, 1)
        self.assertTrue(any(line.startswith("error:") for line in out.splitlines()), out)
        code, out, _ = self.run_main(["record.json"], "[]")
        self.assertEqual(code, 1)
        self.assertEqual(out, "error: record is not a JSON object\n")


class SeamRecordTest(RecordFixture, unittest.TestCase):
    def test_seams_that_is_not_a_list_is_an_error(self):
        self.assertIn("record key 'seams' is not a list", self.errors({**base_record(), "seams": {}}, False))

    def test_seam_that_is_not_an_object_is_an_error(self):
        record = append(base_record(), "seams", "phone-screen")
        self.assertEqual(self.errors(record, False), ("seam 2 is not an object",))

    def test_seam_lacking_a_key_is_an_error(self):
        for key in ("interface", "catches", "misses", "builder_runs"):
            with self.subTest(key=key):
                record = without(base_record(), "seams", 0, key)
                self.assertIn("seam 'unit-tests' lacks required key %r" % key, self.errors(record, False))
        nameless = without(base_record(), "seams", 0, "name")
        errors = self.errors(nameless, False)
        self.assertIn("seam 1 lacks required key 'name'", errors)
        self.assertIn("criterion 5.1 names unknown seam 'unit-tests'", errors)

    def test_seam_with_an_unknown_key_is_an_error(self):
        record = change(base_record(), "seams", 0, what="python3 -m unittest on macOS")
        self.assertEqual(self.errors(record, False), ("seam 'unit-tests' has unknown key 'what'",))

    def test_seam_name_that_is_not_kebab_case_is_an_error(self):
        for name in ("Unit Tests", "unit_tests", "-unit"):
            with self.subTest(name=name):
                record = change(change(base_record(), "seams", 0, name=name), "criteria", 0, seam=name)
                self.assertEqual(
                    self.errors(record, False), ("seam %r has a name that is not lowercase kebab-case" % name,)
                )

    def test_seam_with_a_blank_text_field_is_an_error(self):
        for key in ("interface", "catches", "misses"):
            for value in ("", 3, None):
                with self.subTest(key=key, value=value):
                    record = change(base_record(), "seams", 0, **{key: value})
                    self.assertEqual(
                        self.errors(record, False), ("seam 'unit-tests' has %s that is not a non-empty string" % key,)
                    )

    def test_builder_runs_that_is_not_a_boolean_is_an_error(self):
        for value in ("yes", 1, None):
            with self.subTest(value=value):
                record = change(base_record(), "seams", 0, builder_runs=value)
                self.assertEqual(
                    self.errors(record, False), ("seam 'unit-tests' has builder_runs that is not true or false",)
                )

    def test_duplicated_seam_name_is_reported_once(self):
        record = append(base_record(), "seams", dict(UNIT_SEAM))
        for complete in (False, True):
            with self.subTest(complete=complete):
                self.assertEqual(self.check(record, complete), (("error", "seam name 'unit-tests' is duplicated"),))

    def test_criterion_naming_an_unknown_seam_is_an_error(self):
        record = with_criterion(seam="tablet")
        self.assertEqual(self.errors(record, False), ("criterion 5.1 names unknown seam 'tablet'",))

    def test_criterion_seam_that_is_not_a_string_is_an_error(self):
        for value in ("", 3, None, ["a"], {"a": 1}):
            with self.subTest(value=value):
                self.assertIn(
                    "criterion 5.1 has seam that is not a non-empty string",
                    self.errors(with_criterion(seam=value), False),
                )

    def test_seam_no_criterion_uses_warns_until_complete(self):
        record = append(base_record(), "seams", dict(PHONE_SEAM))
        self.assertEqual(self.check(record, False), (("warning", "seam 'phone-screen' is used by no criterion"),))
        self.assertEqual(self.check(record, True), (("error", "seam 'phone-screen' is used by no criterion"),))
        code, _, _ = self.run_main(["record.json"], json.dumps(record))
        self.assertEqual(code, 0)
        code, out, _ = self.run_main(["--complete", "record.json"], json.dumps(record))
        self.assertEqual(code, 1)
        self.assertEqual(out, "error: seam 'phone-screen' is used by no criterion\n")


class ProofRuleRecordTest(RecordFixture, unittest.TestCase):
    def test_tested_criterion_at_a_runnable_seam_passes(self):
        self.assertEqual(self.check(base_record(), True), ())

    def test_untested_criterion_at_a_runnable_seam_warns_until_complete(self):
        record = with_criterion(tests=[])
        message = "criterion 5.1 acceptance line C1.1 is implemented by no test"
        self.assertEqual(self.check(record, False), (("warning", message),))
        self.assertEqual(self.check(record, True), (("error", message),))

    def test_unproven_criterion_at_a_runnable_seam_without_an_acceptance_line_is_refused(self):
        record = without(with_criterion(tests=[], unproven="a live exchange rate"), "criteria", 0, "acceptance")
        message = "criterion 5.1 sits at a seam the builder runs and has no acceptance line"
        self.assertEqual(self.check(record, False), (("warning", message),))
        self.assertEqual(self.check(record, True), (("error", message),))

    def test_unproven_criterion_with_tests_at_a_runnable_seam_is_an_error(self):
        record = with_criterion(unproven="needs the phone", tests=[TEST_ENTRY, PRESENT_ENTRY])
        message = "criterion 5.1 is marked unproven but has tests at a seam the builder runs: test_total, test_present"
        for complete in (False, True):
            with self.subTest(complete=complete):
                self.assertEqual(self.check(record, complete), (("error", message),))

    def test_unproven_criterion_at_an_unrunnable_seam_passes(self):
        self.assertEqual(self.check(with_phone(), True), ())

    def test_criterion_at_an_unrunnable_seam_must_be_unproven(self):
        record = without(with_phone(), "criteria", 1, "unproven")
        message = "criterion 5.2 sits at a seam the builder cannot run and is not marked unproven"
        loose = self.check(record, False)
        self.assertEqual(loose, (("warning", message),))
        code, _, _ = self.run_main(["record.json"], json.dumps(record))
        self.assertEqual(code, 0)
        self.assertEqual(self.check(record, True), (("error", message),))
        code, out, _ = self.run_main(["--complete", "record.json"], json.dumps(record))
        self.assertEqual(code, 1)
        self.assertEqual(out, "error: " + message + "\n")

    def test_tests_do_not_prove_a_criterion_at_an_unrunnable_seam(self):
        drawn = {**UNCHECKED_ENTRY, "name": "test_drawn", "file": "tests/test_drawn.py"}
        record = change(with_phone(), "criteria", 1, tests=[drawn])
        record = change(without(record, "criteria", 1, "unproven"), "steps", 0, files=["src/app.py", "tests/test_drawn.py"])
        self.assertEqual(
            self.errors(record, True),
            ("criterion 5.2 sits at a seam the builder cannot run and is not marked unproven",),
        )

    def test_seam_whose_builder_runs_is_false_is_unrunnable(self):
        record = change(base_record(), "seams", 0, builder_runs=False)
        self.assertEqual(
            self.errors(record, True),
            ("criterion 5.1 sits at a seam the builder cannot run and is not marked unproven",),
        )
        self.assertEqual(self.check(change(record, "criteria", 0, unproven="needs the phone"), True), ())

    def test_unproven_that_is_not_a_string_is_an_error(self):
        for value in ("", 3, None):
            with self.subTest(value=value):
                record = change(with_phone(), "criteria", 1, unproven=value)
                self.assertIn("criterion 5.2 has unproven that is not a non-empty string", self.errors(record, False))


class CaseTableRecordTest(RecordFixture, unittest.TestCase):
    def test_record_without_a_case_table_has_no_error(self):
        record = base_record()
        self.assertNotIn("case_table", record["criteria"][0])
        self.assertNotIn("domains", record["criteria"][0])
        self.assertEqual(self.errors(record, True), ())

    def test_each_case_table_kind_is_accepted(self):
        for kind in ("security", "refusal"):
            with self.subTest(kind=kind):
                self.assertEqual(self.check(with_table(case_table=kind), True), ())

    def test_other_case_table_values_are_errors(self):
        for value, shown in (("privacy", "'privacy'"), ("Security", "'Security'"), ("", "''"), (True, "True"), (None, "None")):
            for complete in (False, True):
                with self.subTest(value=value, complete=complete):
                    self.assertEqual(
                        self.errors(with_table(case_table=value), complete),
                        ("criterion 5.1 has case_table %s, which is not 'security' or 'refusal'" % shown,),
                    )

    def test_case_table_without_domains_is_an_error(self):
        record = with_criterion(case_table="refusal")
        for complete in (False, True):
            with self.subTest(complete=complete):
                self.assertEqual(self.errors(record, complete), ("criterion 5.1 has case_table but no domains",))

    def test_domains_without_a_case_table_is_an_error(self):
        record = with_criterion(domains=[PAYLOAD_DOMAIN], tests=[TEST_ENTRY])
        self.assertEqual(
            self.errors(record, False),
            ("criterion 5.1 has domains but no case_table; a case table is only for security or refusal behaviour",),
        )

    def test_covers_without_a_case_table_is_an_error(self):
        record = with_criterion(tests=[{**TEST_ENTRY, "covers": ["payload: absent"]}])
        self.assertIn("criterion 5.1 test 'test_total' has unknown key 'covers'", self.errors(record, False))

    def test_domains_that_is_not_a_list_is_an_error(self):
        errors = self.errors(with_table(domains="payload"), False)
        self.assertIn("criterion 5.1 has domains that is not a non-empty list", errors)

    def test_empty_domains_is_an_error(self):
        errors = self.errors(with_table(domains=[]), False)
        self.assertIn("criterion 5.1 has domains that is not a non-empty list", errors)

    def test_domain_that_is_not_an_object_is_an_error(self):
        errors = self.errors(with_table(domains=["payload"]), False)
        self.assertIn("criterion 5.1 domain 1 is not an object", errors)

    def test_domain_with_an_unknown_key_is_an_error(self):
        record = with_table(domains=[{**PAYLOAD_DOMAIN, "note": "checked by hand"}])
        self.assertEqual(self.errors(record, False), ("criterion 5.1 domain 'payload' has unknown key 'note'",))

    def test_domain_with_a_fact_is_an_error(self):
        record = with_table(domains=[{**PAYLOAD_DOMAIN, "fact": "f1"}])
        self.assertEqual(self.errors(record, False), ("criterion 5.1 domain 'payload' has unknown key 'fact'",))

    def test_domain_lacking_a_key_is_an_error(self):
        domain = {"name": "payload", "over": "the payload field agent_id"}
        errors = self.errors(with_table(domains=[domain], tests=[TEST_ENTRY]), False)
        self.assertIn("criterion 5.1 domain 'payload' lacks required key 'classes'", errors)

    def test_domain_name_that_is_not_a_string_is_an_error(self):
        errors = self.errors(with_table(domains=[{**PAYLOAD_DOMAIN, "name": 3}]), False)
        self.assertIn("criterion 5.1 domain 1 has a name that is not lowercase kebab-case", errors)

    def test_domain_name_that_is_not_kebab_case_is_an_error(self):
        errors = self.errors(with_table(domains=[{**PAYLOAD_DOMAIN, "name": "Payload Field"}]), False)
        self.assertIn("criterion 5.1 domain 'Payload Field' has a name that is not lowercase kebab-case", errors)

    def test_domain_name_used_twice_is_an_error(self):
        record = with_table(domains=[PAYLOAD_DOMAIN, PAYLOAD_DOMAIN])
        self.assertEqual(self.errors(record, False), ("criterion 5.1 domain name 'payload' is duplicated",))

    def test_domain_with_a_blank_over_is_an_error(self):
        record = with_table(domains=[{**PAYLOAD_DOMAIN, "over": ""}])
        self.assertEqual(
            self.errors(record, False), ("criterion 5.1 domain 'payload' has over that is not a non-empty string",)
        )

    def test_domain_with_one_class_is_an_error(self):
        record = with_table(domains=[{**PAYLOAD_DOMAIN, "classes": ["absent"]}])
        self.assertIn(
            "criterion 5.1 domain 'payload' has classes that is not a list of at least two non-empty strings",
            self.errors(record, False),
        )

    def test_domain_with_a_blank_class_is_an_error(self):
        record = with_table(domains=[{**PAYLOAD_DOMAIN, "classes": ["absent", ""]}])
        self.assertIn(
            "criterion 5.1 domain 'payload' has classes that is not a list of at least two non-empty strings",
            self.errors(record, False),
        )

    def test_domain_with_a_repeated_class_is_an_error(self):
        record = with_table(domains=[{**PAYLOAD_DOMAIN, "classes": ["absent", "absent", "present"]}])
        self.assertEqual(
            self.errors(record, False), ("criterion 5.1 domain 'payload' lists class 'absent' more than once",)
        )

    def test_well_formed_case_table_has_no_finding(self):
        self.assertEqual(self.check(with_table(), True), ())

    def test_row_without_covers_in_a_case_table_shows_its_gap(self):
        record = with_table(tests=[TEST_ENTRY, PAYLOAD_ROWS[1]])
        self.assertEqual(
            self.check(record, False),
            (("warning", "criterion 5.1 has no test covering class 'absent' of domain 'payload'"),),
        )

    def test_covers_that_is_not_a_list_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": "payload: absent"}, PAYLOAD_ROWS[1]]
        self.assertIn(
            "criterion 5.1 test 'test_total' has covers that is not a non-empty list of non-empty strings",
            self.errors(with_table(tests=tests), False),
        )

    def test_empty_covers_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": []}, PAYLOAD_ROWS[1]]
        self.assertIn(
            "criterion 5.1 test 'test_total' has covers that is not a non-empty list of non-empty strings",
            self.errors(with_table(tests=tests), False),
        )

    def test_covers_entry_without_a_separator_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": ["payload absent"]}, PAYLOAD_ROWS[1]]
        self.assertIn(
            "criterion 5.1 test 'test_total' covers 'payload absent', which is not '<domain>: <class>'",
            self.errors(with_table(tests=tests), False),
        )

    def test_covers_naming_an_unknown_domain_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": ["cwd: subfolder"]}, PAYLOAD_ROWS[1]]
        self.assertIn(
            "criterion 5.1 test 'test_total' covers unknown domain 'cwd'", self.errors(with_table(tests=tests), False)
        )

    def test_covers_naming_an_unknown_class_is_an_error(self):
        tests = [{**TEST_ENTRY, "covers": ["payload: truncated"]}, PAYLOAD_ROWS[1]]
        self.assertIn(
            "criterion 5.1 test 'test_total' covers unknown class 'truncated' of domain 'payload'",
            self.errors(with_table(tests=tests), False),
        )

    def test_class_holding_a_colon_is_covered(self):
        domain = {**PAYLOAD_DOMAIN, "classes": ["key: value", "absent"]}
        tests = [{**TEST_ENTRY, "covers": ["payload: key: value"]}, {**PRESENT_ENTRY, "covers": ["payload: absent"]}]
        self.assertEqual(self.check(with_table(domains=[domain], tests=tests), True), ())

    def test_uncovered_class_warns_before_complete(self):
        record = with_table(tests=PAYLOAD_ROWS[:1])
        findings = self.check(record, False)
        self.assertEqual(
            messages(findings, "warning"), ("criterion 5.1 has no test covering class 'present' of domain 'payload'",)
        )
        self.assertEqual(messages(findings, "error"), ())

    def test_uncovered_class_is_an_error_when_complete(self):
        record = with_table(tests=PAYLOAD_ROWS[:1])
        self.assertEqual(
            self.errors(record, True), ("criterion 5.1 has no test covering class 'present' of domain 'payload'",)
        )

    def test_unproven_criterion_needs_no_coverage(self):
        record = change(with_phone(), "criteria", 1, case_table="refusal", domains=[PAYLOAD_DOMAIN])
        self.assertEqual(self.check(record, True), ())

    def test_case_table_that_varies_takes_covers_and_population(self):
        tests = [{**row, "cases": 20, "runs": 2, "pass_rate": 1} for row in PAYLOAD_ROWS]
        self.assertEqual(self.check(with_table(varies="input", tests=tests), True), ())

    def test_row_without_given_is_an_error(self):
        test = {key: value for key, value in TEST_ENTRY.items() if key != "given"}
        self.assertEqual(
            self.errors(with_criterion(tests=[test]), False),
            ("criterion 5.1 test 'test_total' is not an object with non-empty string file, name, given, expect and step",),
        )

    def test_row_without_expect_is_an_error(self):
        test = {key: value for key, value in TEST_ENTRY.items() if key != "expect"}
        self.assertEqual(
            self.errors(with_criterion(tests=[test]), False),
            ("criterion 5.1 test 'test_total' is not an object with non-empty string file, name, given, expect and step",),
        )

    def test_row_with_asserts_is_an_error(self):
        test = {**TEST_ENTRY, "asserts": "the total adds up"}
        self.assertEqual(
            self.errors(with_criterion(tests=[test]), False), ("criterion 5.1 test 'test_total' has unknown key 'asserts'",)
        )


class AcceptanceRecordTest(RecordFixture, unittest.TestCase):
    def unlined(self):
        record = without(with_criterion(tests=[UNCHECKED_ENTRY]), "criteria", 0, "acceptance")
        return change(record, "steps", 0, files=["src/app.py", "tests/test_app.py"])

    def test_check_without_acceptance_lines_is_an_unknown_key(self):
        record = change(self.unlined(), "criteria", 0, tests=[TEST_ENTRY])
        self.assertIn("criterion 5.1 test 'test_total' has unknown key 'check'", self.errors(record, False))

    def test_check_naming_an_unknown_line_is_an_error(self):
        record = with_criterion(tests=[TEST_ENTRY, {**PRESENT_ENTRY, "check": "C1.2"}])
        self.assertEqual(
            self.errors(record, False), ("criterion 5.1 test 'test_present' names unknown acceptance line C1.2",)
        )

    def test_row_without_check_warns_until_complete(self):
        record = with_criterion(tests=[TEST_ENTRY, {**UNCHECKED_ENTRY, "name": "test_present"}])
        message = "criterion 5.1 test 'test_present' names no acceptance line in check"
        self.assertEqual(self.check(record, False), (("warning", message),))
        self.assertEqual(self.check(record, True), (("error", message),))

    def test_acceptance_that_is_not_a_non_empty_list_is_an_error(self):
        for value in ([], "C1.1", None):
            with self.subTest(value=value):
                self.assertIn(
                    "criterion 5.1 has acceptance that is not a non-empty list of K1 lines",
                    self.errors(with_criterion(acceptance=value), False),
                )

    def test_record_without_locked_warns_until_complete(self):
        record = {key: value for key, value in base_record().items() if key != "locked"}
        message = "record has no locked list, but criteria have acceptance lines"
        self.assertEqual(self.check(record, False), (("warning", message),))
        self.assertEqual(self.check(record, True), (("error", message),))

    def test_rows_without_acceptance_lines_keep_the_step_file_rule(self):
        record = {key: value for key, value in self.unlined().items() if key not in ("locked", "probes")}
        self.assertEqual(
            self.check(record, True),
            (("error", "criterion 5.1 sits at a seam the builder runs and has no acceptance line"),),
        )
        moved = change(record, "steps", 0, files=["src/app.py"])
        self.assertIn(
            "criterion 5.1 test 'test_total' has file 'tests/test_app.py', which is not in the files of step 'build-app'",
            self.errors(moved, False),
        )

    def test_a_locked_row_file_in_its_step_is_an_error(self):
        record = change(base_record(), "steps", 0, files=["src/app.py", "tests/test_app.py"])
        self.assertEqual(
            self.errors(record, False),
            (
                "criterion 5.1 test 'test_total' has file tests/test_app.py, which step 'build-app' lists in its files",
                "step 'build-app' lists locked path tests/test_app.py",
            ),
        )


class LaterKeysRecordTest(RecordFixture, unittest.TestCase):
    def test_a_stopped_record_with_its_stop_passes(self):
        stop = {"phase": "probe", "reason": "the claude probe of C1.1 failed"}
        self.assertEqual(self.check({**base_record(), "status": "stopped", "stop": stop}, True), ())

    def test_stop_goes_with_the_stopped_status(self):
        stop = {"phase": "probe", "reason": "the claude probe of C1.1 failed"}
        variants = (
            ({**base_record(), "status": "stopped"}, "record status is 'stopped' but the record has no stop"),
            ({**base_record(), "stop": stop}, "record has stop but its status is not 'stopped'"),
            (
                {**base_record(), "status": "stopped", "stop": {"phase": "probe"}},
                "record stop is not an object with exactly non-empty string phase and reason",
            ),
        )
        for record, message in variants:
            with self.subTest(message=message):
                self.assertEqual(self.errors(record, False), (message,))

    def test_probes_of_the_wrong_shape_are_errors(self):
        variants = (
            ({**base_record(), "probes": {}}, "record probes is not a list"),
            (
                {**base_record(), "probes": [{**APP_PROBE, "status": "skipped"}]},
                "record probes entry 1 has status 'skipped', which is not 'pass' or 'fail'",
            ),
            (
                {**base_record(), "probes": [{**APP_PROBE, "detail": ""}]},
                "record probes entry 1 is not an object with exactly non-empty string check, probe, target, status, detail",
            ),
        )
        for record, message in variants:
            with self.subTest(message=message):
                self.assertEqual(self.errors(record, False), (message,))

    def test_outcomes_of_the_wrong_shape_are_errors(self):
        self.assertEqual(
            self.check({**base_record(), "outcomes": {**OUTCOMES, "repeated": [{"kind": "flaky", "count": 2}]}}, True), ()
        )
        variants = (
            ({**OUTCOMES, "note": "x"}, "record outcomes is not an object with exactly store, entries and repeated"),
            ({**OUTCOMES, "store": ""}, "record outcomes has store that is not a non-empty string"),
            ({**OUTCOMES, "entries": -1}, "record outcomes has entries that is not an integer of at least 0"),
            (
                {**OUTCOMES, "repeated": [{"kind": "flaky", "count": 1}]},
                "record outcomes has repeated that is not a list of objects with exactly a non-empty string kind "
                "and an integer count of at least 2",
            ),
        )
        for outcomes, message in variants:
            with self.subTest(message=message):
                self.assertEqual(self.errors({**base_record(), "outcomes": outcomes}, False), (message,))


class AmendmentRecordTest(RecordFixture, unittest.TestCase):
    def test_steps_with_and_without_amendment_are_accepted(self):
        fix = {
            "name": "fix-app",
            "files": ["src/app.py"],
            "criteria": ["5.1"],
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


class RoundsRecordTest(RecordFixture, unittest.TestCase):
    def error_lines(self, record, complete=True):
        argv = ["--complete", "record.json"] if complete else ["record.json"]
        code, out, _ = self.run_main(argv, json.dumps(record))
        return code, tuple(line for line in out.splitlines() if line.startswith("error:"))

    def test_record_without_rounds_is_valid(self):
        code, out, _ = self.run_main(["--complete", "record.json"], json.dumps(base_record()))
        self.assertEqual(code, 0)
        self.assertFalse(any("round" in line for line in out.splitlines()), out)

    def test_rounds_entries_accepted(self):
        intent = {"kind": "intent", "questions": 3, "changed": 0}
        frontier = {"kind": "frontier", "questions": 5, "changed": 2}
        for rounds in ([], [intent, frontier]):
            with self.subTest(rounds=rounds):
                code, errors = self.error_lines({**base_record(), "rounds": rounds})
                self.assertEqual(code, 0)
                self.assertEqual(errors, ())

    def test_rounds_not_a_list_refused(self):
        record = {**base_record(), "rounds": {"kind": "intent", "questions": 3, "changed": 0}}
        code, errors = self.error_lines(record)
        self.assertEqual(code, 1)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("rounds", errors[0])

    def test_malformed_round_entries_refused(self):
        rounds = [
            "intent",
            {"kind": "intent", "questions": 3, "changed": 0, "note": "x"},
            {"kind": "intent", "questions": 3},
            {"kind": "readback", "questions": 1, "changed": 0},
            {"kind": "frontier", "questions": 0, "changed": 0},
            {"kind": "frontier", "questions": True, "changed": 0},
            {"kind": "frontier", "questions": 2, "changed": 3},
            {"kind": "frontier", "questions": 2, "changed": -1},
        ]
        code, errors = self.error_lines({**base_record(), "rounds": rounds})
        self.assertEqual(code, 1)
        for number in range(1, 9):
            with self.subTest(number=number):
                prefix = "round %d" % number
                self.assertTrue(
                    any(
                        prefix in line and not any(digit in line.replace(prefix, "", 1) for digit in "0123456789")
                        for line in errors
                    ),
                    errors,
                )


if __name__ == "__main__":
    unittest.main()
