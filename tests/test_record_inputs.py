import contextlib
import importlib.util
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE_TEXT = "import json, sys\n\npayload = json.load(sys.stdin)\n"


def replay_shaped_record():
    return {
        "status": "in-progress",
        "environments": [
            {"name": "unit-tests", "what": "python3 -m unittest on macOS", "builder_runs": True},
        ],
        "facts": [
            {
                "id": "reads-payload",
                "fact": "The hook reads its payload from standard input",
                "path": "src/hook.py",
                "line": 3,
                "quote": "payload = json.load(sys.stdin)",
            },
        ],
        "criteria": [
            {
                "number": "10.1",
                "title": "The hook refuses an unbound run and keeps its context inside the budget",
                "text": "WHEN the hook receives a payload THE SYSTEM SHALL refuse every run the session has not bound, and keep its context at most 9,000 code units.",
                "where": ["unit-tests"],
                "domains": [
                    {
                        "name": "payload",
                        "over": "the hook payload",
                        "classes": ["a bound run", "an unbound run"],
                        "fact": "reads-payload",
                    }
                ],
                "gives_way": ["older lines", "the goal"],
                "tests": [
                    {
                        "file": "tests/test_hook.py",
                        "name": "test_bound_run_passes",
                        "given": "a payload for a bound run",
                        "expect": "exit 0",
                        "env": "unit-tests",
                        "step": "build-hook",
                        "covers": ["payload: a bound run", "gives-way: older lines"],
                    },
                    {
                        "file": "tests/test_hook.py",
                        "name": "test_unbound_run_is_refused",
                        "given": "a payload for an unbound run",
                        "expect": "exit 2",
                        "env": "unit-tests",
                        "step": "build-hook",
                        "covers": ["payload: an unbound run", "gives-way: the goal"],
                    },
                ],
            }
        ],
        "steps": [
            {
                "name": "build-hook",
                "files": ["src/hook.py", "tests/test_hook.py"],
                "criteria": ["10.1"],
                "task": "Build the hook.",
            }
        ],
    }


def load_check_record():
    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("check_record", str(root / "scripts" / "check_record.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK_SCRIPT = str(ROOT / "scripts" / "check_record.py")
RENDER_SCRIPT = str(ROOT / "scripts" / "render_record.py")
REVIEWER_FILE = ROOT / "agents" / "spec-reviewer.md"
APP_TEXT = "def total_of(total):\n    return total\n"
SOURCE_FILES = (("src/app.py", APP_TEXT),)
BASE_SPEC = b"# The total shows\n"
CHANGED_SPEC = b"# The total shows\nchanged\n"
DECISIONS_FILES = (("docs/specs/app.decisions.md", "# Decisions for the app\n\n- Keep the total's format open.\n"),)
USAGE_LINE = "usage: python3 check_record.py [--complete | --digest] RECORD"
DIGEST_RE = re.compile(r"[0-9a-f]{64}\n")
DOMAIN = "criterion 7.1 domain 'payload'"
WHOLE_ORDER_COVERS = ["payload: a number", "gives-way: older lines", "gives-way: the header", "keeps: the total"]
ORDER_COVERS = ["payload: a number", "gives-way: older lines", "gives-way: the header"]
APPROVED = {"status": "Approved", "issues": []}
CLARITY = {"category": "Clarity", "text": "7.1 reads two ways."}
OPEN_DOMAIN = {"category": "Open domain", "text": "7.1 payload takes any total the service sends."}
GATE = {"category": "Gate", "text": "7.1 lets every total through."}
URL_FACT = {"id": "f5", "fact": "The total's format is documented", "url": "https://example.com/total"}
DECISION_FACT = {
    "id": "f6",
    "fact": "The user kept the total's format open",
    "path": "docs/specs/app.decisions.md",
    "line": 3,
    "quote": "Keep the total's format open",
}
REVIEWER_CATEGORIES = (
    "Consistency",
    "Clarity",
    "Missing input",
    "Missing class",
    "Stand-in",
    "Source",
    "Give-way",
    "Outside fact",
    "Invalid input",
    "Open domain",
    "Scope",
    "Context",
    "Review bar",
    "Testability",
    "Proof environment",
    "Variation",
    "Boundary",
    "Design",
    "Visible assumptions",
    "Task drift",
    "Task independence",
    "Build order",
    "Tracking talk",
)
INPUT_CATEGORIES = (
    "Missing input",
    "Missing class",
    "Stand-in",
    "Source",
    "Outside fact",
    "Invalid input",
    "Give-way",
    "Open domain",
)


def app_test(name, given, expect, covers):
    return {
        "file": "tests/test_app.py",
        "name": name,
        "given": given,
        "expect": expect,
        "env": "unit-tests",
        "step": "build-app",
        "covers": list(covers),
    }


def base_record():
    return {
        "status": "in-progress",
        "environments": [{"name": "unit-tests", "what": "python3 -m unittest on macOS", "builder_runs": True}],
        "facts": [
            {
                "id": "f1",
                "fact": "The app returns the total it is given",
                "path": "src/app.py",
                "line": 2,
                "quote": "return total",
            },
            {
                "id": "f2",
                "fact": "The service replies with a total",
                "command": "curl -s https://service.example/total",
                "output": "{\"total\": 3}",
                "outside": True,
            },
            {"id": "f3", "fact": "The suite passes", "command": "python3 -m unittest", "output": "OK"},
        ],
        "criteria": [
            {
                "number": "7.1",
                "title": "The total shows",
                "text": "WHEN the service sends a total THE SYSTEM SHALL show every total in at most three lines.",
                "where": ["unit-tests"],
                "domains": [
                    {
                        "name": "payload",
                        "over": "the total the service sends",
                        "source": "outside",
                        "closed": True,
                        "fact": "f2",
                        "classes": ["a number", "a missing total"],
                        "invalid": ["a missing total"],
                    }
                ],
                "gives_way": ["older lines", "the header"],
                "keeps": ["the total"],
                "tests": [
                    app_test("test_total", "a total of 3", "3 is shown", WHOLE_ORDER_COVERS),
                    app_test(
                        "test_missing_total", "a reply with no total", "the reply is refused", ["payload: a missing total"]
                    ),
                ],
            }
        ],
        "steps": [
            {
                "name": "build-app",
                "files": ["src/app.py", "tests/test_app.py"],
                "criteria": ["7.1"],
                "reads": ["payload"],
                "task": "Build the app.",
            }
        ],
    }


def updated(item, fields, dropped):
    return {**{key: value for key, value in item.items() if key not in dropped}, **fields}


def with_criterion(record, dropped=(), **fields):
    criteria = record["criteria"]
    return {**record, "criteria": [updated(criteria[0], fields, dropped)] + criteria[1:]}


def with_payload(record, dropped=(), **fields):
    domains = record["criteria"][0]["domains"]
    return with_criterion(record, domains=[updated(domains[0], fields, dropped)] + domains[1:])


def with_test(record, index, dropped=(), **fields):
    tests = record["criteria"][0]["tests"]
    return with_criterion(record, tests=tests[:index] + [updated(tests[index], fields, dropped)] + tests[index + 1 :])


def with_build_app(record, dropped=(), **fields):
    steps = record["steps"]
    return {**record, "steps": [updated(steps[0], fields, dropped)] + steps[1:]}


def with_facts(record, *facts):
    return {**record, "facts": record["facts"] + list(facts)}


def replacing_fact(record, fact):
    return {**record, "facts": [fact if item["id"] == fact["id"] else item for item in record["facts"]]}


def with_parts(record, criteria, steps):
    return {**record, "criteria": record["criteria"] + list(criteria), "steps": record["steps"] + list(steps)}


def with_reviews(record, reviews):
    return {**record, "reviews": list(reviews)}


def handed_off(record):
    return {**record, "status": "handed-off"}


def varying(record, kind):
    tests = [{**test, "cases": 20, "runs": 3, "pass_rate": 0.9} for test in record["criteria"][0]["tests"]]
    return with_payload(with_criterion(record, varies=kind, tests=tests), closed=False)


def extra_criterion(number, thing, step, *domains, covers=()):
    test = {
        "file": "tests/test_%s.py" % thing,
        "name": "test_%s" % thing,
        "given": "the app starts",
        "expect": "the %s is shown" % thing,
        "env": "unit-tests",
        "step": step,
    }
    criterion = {
        "number": number,
        "title": "The %s shows" % thing,
        "text": "WHEN the app starts THE SYSTEM SHALL show the %s." % thing,
        "where": ["unit-tests"],
        "tests": [{**test, "covers": list(covers)} if covers else test],
    }
    return {**criterion, "domains": list(domains)} if domains else criterion


def extra_step(name, thing, number, **fields):
    return {
        "name": name,
        "files": ["src/%s.py" % thing, "tests/test_%s.py" % thing],
        "criteria": [number],
        "reads": [],
        **fields,
    }


def date_criterion(*domains, covers=()):
    return extra_criterion("7.2", "date", "build-date", *domains, covers=covers)


def date_step(**fields):
    return extra_step("build-date", "date", "7.2", **fields)


def version_criterion():
    return extra_criterion("7.3", "version", "build-version")


def version_step(**fields):
    return extra_step("build-version", "version", "7.3", **fields)


def errors(findings):
    return tuple(message for level, message in findings if level == "error")


def warnings(findings):
    return tuple(message for level, message in findings if level == "warning")


def write_files(folder, files):
    for relative, text in files:
        path = pathlib.Path(folder) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def write_record(folder, text, spec=BASE_SPEC, name="t.record.json"):
    path = os.path.join(folder, name)
    pathlib.Path(path).write_text(text, encoding="utf-8")
    if spec is not None:
        pathlib.Path(folder, "t.md").write_bytes(spec)
    return path


def run_script(script, arguments, folder):
    done = subprocess.run(
        [sys.executable, script] + list(arguments), cwd=folder, capture_output=True, text=True, check=False
    )
    return done.returncode, done.stdout, done.stderr


def base_digest():
    return load_check_record().digest(base_record(), BASE_SPEC)


def open_digest():
    return load_check_record().digest(with_payload(base_record(), closed=False), BASE_SPEC)


class RecordInputsTest(unittest.TestCase):
    def test_replay_shaped_record_is_refused_when_complete(self):
        module = load_check_record()
        with tempfile.TemporaryDirectory() as folder:
            source = pathlib.Path(folder) / "src"
            source.mkdir()
            (source / "hook.py").write_text(SOURCE_TEXT, encoding="utf-8")
            findings = module.check(json.dumps(replay_shaped_record()), folder, complete=True)
        errors = tuple(message for level, message in findings if level == "error")
        self.assertIn(
            "criterion 10.1 domain 'payload' does not say where its values come from; give source repo, outside, person, stored or sent",
            errors,
        )
        self.assertIn("criterion 10.1 domain 'payload' does not say whether it is closed", errors)
        self.assertIn("criterion 10.1 sets a bound but lists nothing in keeps", errors)
        self.assertIn("step 'build-hook' does not list the inputs its code reads", errors)

    def check(self, record, complete=True, spec=BASE_SPEC, files=(), reviewer=None):
        module = load_check_record()
        options = {} if reviewer is None else {"reviewer": reviewer}
        with tempfile.TemporaryDirectory() as folder:
            write_files(folder, SOURCE_FILES + tuple(files))
            return module.check(json.dumps(record), folder, complete=complete, spec=spec, **options)

    def assert_accepted(self, record, **options):
        self.assertEqual(errors(self.check(record, **options)), ())

    def assert_refused(self, record, message, **options):
        self.assertIn(message, errors(self.check(record, **options)))

    def digest_run(self, text, spec=BASE_SPEC, name="t.record.json"):
        with tempfile.TemporaryDirectory() as folder:
            path = write_record(folder, text, spec, name)
            return run_script(CHECK_SCRIPT, ["--digest", path], folder)

    def test_domain_without_source_is_refused_when_complete(self):
        self.assert_refused(
            with_payload(base_record(), dropped=("source",)),
            DOMAIN + " does not say where its values come from; give source repo, outside, person, stored or sent",
        )

    def test_source_of_another_value_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), source="code"),
            DOMAIN + " has source 'code', which is not 'repo', 'outside', 'person', 'stored' or 'sent'",
        )

    def test_source_that_is_not_text_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), source=["repo"]),
            DOMAIN + " has source ['repo'], which is not 'repo', 'outside', 'person', 'stored' or 'sent'",
        )

    def test_person_domain_citing_where_the_repository_asks_is_accepted(self):
        self.assert_accepted(with_payload(base_record(), source="person", fact="f1"))

    def test_stored_domain_citing_where_the_repository_writes_is_accepted(self):
        self.assert_accepted(with_payload(base_record(), source="stored", fact="f1"))

    def test_sent_domain_citing_where_the_repository_sends_is_accepted(self):
        self.assert_accepted(with_payload(base_record(), source="sent", fact="f1"))

    def test_repo_domain_citing_a_location_fact_is_accepted(self):
        self.assert_accepted(with_payload(base_record(), source="repo", fact="f1"))

    def test_repo_domain_citing_a_repository_command_fact_is_accepted(self):
        self.assert_accepted(with_payload(base_record(), source="repo", fact="f3"))

    def test_repo_domain_citing_a_url_fact_is_refused(self):
        self.assert_refused(
            with_payload(with_facts(base_record(), URL_FACT), source="repo", fact="f5"),
            DOMAIN + " has source repo but names fact 'f5', which is cited by url",
        )

    def test_repo_domain_citing_an_outside_fact_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), source="repo", fact="f2"),
            DOMAIN + " has source repo but names fact 'f2', which is marked outside",
        )

    def test_repo_domain_defined_by_a_step_is_accepted(self):
        self.assert_accepted(with_payload(base_record(), dropped=("fact",), source="repo", defined_by="build-app"))

    def test_defined_by_naming_a_step_a_prover_comes_after_is_accepted(self):
        record = with_parts(with_build_app(base_record(), after=["build-date"]), [date_criterion()], [date_step()])
        self.assert_accepted(with_payload(record, dropped=("fact",), source="repo", defined_by="build-date"))

    def test_defined_by_naming_a_step_a_prover_comes_after_through_another_is_accepted(self):
        record = with_parts(
            with_build_app(base_record(), after=["build-version"]),
            [date_criterion(), version_criterion()],
            [date_step(), version_step(after=["build-date"])],
        )
        self.assert_accepted(with_payload(record, dropped=("fact",), source="repo", defined_by="build-date"))

    def test_defined_by_naming_a_step_that_comes_after_a_prover_is_refused(self):
        record = with_parts(base_record(), [date_criterion()], [date_step(after=["build-app"])])
        self.assert_refused(
            with_payload(record, dropped=("fact",), source="repo", defined_by="build-date"),
            DOMAIN + " names step 'build-date' in defined_by, which neither proves criterion 7.1 nor comes before a "
            "Step that proves it",
        )

    def test_defined_by_naming_an_unrelated_step_is_refused(self):
        record = with_parts(base_record(), [date_criterion()], [date_step()])
        self.assert_refused(
            with_payload(record, dropped=("fact",), source="repo", defined_by="build-date"),
            DOMAIN + " names step 'build-date' in defined_by, which neither proves criterion 7.1 nor comes before a "
            "Step that proves it",
        )

    def test_defined_by_naming_no_step_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), dropped=("fact",), source="repo", defined_by="build-api"),
            DOMAIN + " names unknown step 'build-api' in defined_by",
        )

    def test_defined_by_that_is_not_text_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), dropped=("fact",), source="repo", defined_by=["build-app"]),
            DOMAIN + " has defined_by that is not a non-empty string",
        )

    def test_repo_domain_with_no_fact_and_no_defined_by_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), dropped=("fact",), source="repo"),
            DOMAIN + " has source repo but names no repository fact and no step in defined_by",
        )

    def test_base_record_is_accepted(self):
        self.assert_accepted(base_record())

    def test_outside_domain_citing_a_repository_fact_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), fact="f1"),
            DOMAIN + " has source outside but names fact 'f1', which is not marked outside",
        )

    def test_outside_domain_with_no_fact_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), dropped=("fact",)),
            DOMAIN + " has source outside but names no fact marked outside",
        )

    def test_outside_domain_with_defined_by_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), defined_by="build-app"),
            DOMAIN + " has defined_by but its source is not repo, person, stored or sent",
        )

    def test_outside_domain_without_invalid_is_refused_when_complete(self):
        self.assert_refused(
            with_payload(base_record(), dropped=("invalid",)),
            DOMAIN + " has source outside but lists no invalid class",
        )

    def test_person_domain_without_invalid_is_refused_when_complete(self):
        self.assert_refused(
            with_payload(base_record(), dropped=("invalid",), source="person", fact="f1"),
            DOMAIN + " has source person but lists no invalid class",
        )

    def test_stored_domain_without_invalid_is_refused_when_complete(self):
        self.assert_refused(
            with_payload(base_record(), dropped=("invalid",), source="stored", fact="f1"),
            DOMAIN + " has source stored but lists no invalid class",
        )

    def test_sent_domain_without_invalid_is_refused_when_complete(self):
        self.assert_refused(
            with_payload(base_record(), dropped=("invalid",), source="sent", fact="f1"),
            DOMAIN + " has source sent but lists no invalid class",
        )

    def test_repo_domain_needs_no_invalid(self):
        self.assert_accepted(with_payload(base_record(), dropped=("invalid",), source="repo", fact="f1"))

    def test_invalid_naming_an_unknown_class_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), invalid=["an empty total"]),
            DOMAIN + " lists invalid class 'an empty total', which is not one of its classes",
        )

    def test_invalid_listing_a_class_twice_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), invalid=["a missing total", "a missing total"]),
            DOMAIN + " lists invalid class 'a missing total' more than once",
        )

    def test_invalid_that_is_not_a_list_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), invalid="a missing total"),
            DOMAIN + " has invalid that is not a non-empty list of non-empty strings",
        )

    def test_domain_without_closed_is_refused_when_complete(self):
        self.assert_refused(
            with_payload(base_record(), dropped=("closed",)), DOMAIN + " does not say whether it is closed"
        )

    def test_open_domain_of_a_criterion_that_varies_input_is_accepted(self):
        self.assert_accepted(varying(base_record(), "input"))

    def test_open_domain_of_a_criterion_that_varies_output_is_accepted(self):
        self.assert_accepted(varying(base_record(), "output"))

    def test_open_domain_of_a_criterion_that_varies_measured_is_accepted(self):
        self.assert_accepted(varying(base_record(), "measured"))

    def test_open_domain_kept_by_a_decision_is_accepted(self):
        record = with_payload(with_facts(base_record(), DECISION_FACT), closed=False, open_by="f6")
        self.assert_accepted(record, files=DECISIONS_FILES)

    def test_open_domain_is_refused_when_complete(self):
        self.assert_refused(
            with_payload(base_record(), closed=False),
            DOMAIN + " is not closed; decide where its input can be listed, give the criterion varies, or name in "
            "open_by the decision that keeps it open",
        )

    def test_closed_that_is_not_a_boolean_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), closed="yes"), DOMAIN + " has closed that is not true or false"
        )

    def test_open_by_citing_another_file_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), closed=False, open_by="f1"),
            DOMAIN + " names fact 'f1' in open_by, which does not cite a decisions file",
        )

    def test_open_by_naming_an_unknown_fact_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), closed=False, open_by="f9"),
            DOMAIN + " names unknown fact 'f9' in open_by",
        )

    def test_open_by_that_is_not_text_is_refused(self):
        self.assert_refused(
            with_payload(base_record(), closed=False, open_by=["f6"]),
            DOMAIN + " has open_by that is not a non-empty string",
        )

    def test_open_by_on_a_closed_domain_is_refused(self):
        record = with_payload(with_facts(base_record(), DECISION_FACT), closed=True, open_by="f6")
        self.assert_refused(record, DOMAIN + " has open_by but is closed", files=DECISIONS_FILES)

    def test_fact_with_no_citation_names_assumed(self):
        self.assert_refused(
            with_facts(base_record(), {"id": "f4", "fact": "The service sends one total a second"}),
            "fact 'f4' has no citation; give path, line and quote, or url, or command and output, or assumed for a "
            "fact marked outside",
        )

    def test_outside_fact_assumed_with_a_reason_is_accepted(self):
        fact = {
            "id": "f2",
            "fact": "The service replies with a total",
            "assumed": "needs the live service",
            "outside": True,
        }
        self.assert_accepted(replacing_fact(base_record(), fact))

    def test_assumed_fact_not_marked_outside_is_refused(self):
        fact = {"id": "f4", "fact": "The service sends one total a second", "assumed": "needs the live service"}
        self.assert_refused(with_facts(base_record(), fact), "fact 'f4' is assumed but not marked outside")

    def test_assumed_beside_a_command_is_refused(self):
        record = base_record()
        fact = {**record["facts"][1], "assumed": "needs the live service"}
        self.assert_refused(replacing_fact(record, fact), "fact 'f2' has more than one citation form")

    def test_assumed_that_is_not_text_is_refused(self):
        fact = {"id": "f4", "fact": "The service sends one total a second", "assumed": "", "outside": True}
        self.assert_refused(with_facts(base_record(), fact), "fact 'f4' has assumed that is not a non-empty string")

    def test_outside_fact_cited_by_location_is_refused(self):
        fact = {
            "id": "f4",
            "fact": "The app returns the total",
            "path": "src/app.py",
            "line": 2,
            "quote": "return total",
            "outside": True,
        }
        self.assert_refused(
            with_facts(base_record(), fact),
            "fact 'f4' is marked outside but is not cited by command and output, or assumed",
        )

    def test_bound_without_keeps_is_refused_when_complete(self):
        record = with_test(with_criterion(base_record(), dropped=("keeps",)), 0, covers=ORDER_COVERS)
        self.assert_refused(record, "criterion 7.1 sets a bound but lists nothing in keeps")

    def test_criterion_without_bound_needs_no_keeps(self):
        record = with_criterion(
            base_record(),
            dropped=("gives_way", "keeps"),
            text="WHEN the service sends a total THE SYSTEM SHALL show every total.",
        )
        self.assert_accepted(with_test(record, 0, covers=["payload: a number"]))

    def test_keeps_without_gives_way_is_refused(self):
        self.assert_refused(
            with_criterion(base_record(), dropped=("gives_way",)), "criterion 7.1 has keeps but no gives_way"
        )

    def test_keeps_that_is_not_a_list_is_refused(self):
        self.assert_refused(
            with_criterion(base_record(), keeps="the total"),
            "criterion 7.1 has keeps that is not a non-empty list of non-empty strings",
        )

    def test_keeps_item_listed_twice_is_refused(self):
        self.assert_refused(
            with_criterion(base_record(), keeps=["the total", "the total"]),
            "criterion 7.1 lists keeps item 'the total' more than once",
        )

    def test_keeps_item_also_in_gives_way_is_refused(self):
        record = with_criterion(base_record(), keeps=["the total", "the header"])
        self.assert_refused(
            with_test(record, 0, covers=WHOLE_ORDER_COVERS + ["keeps: the header"]),
            "criterion 7.1 lists 'the header' both in keeps and in gives_way",
        )

    def test_kept_item_without_a_whole_order_row_is_refused(self):
        record = with_test(base_record(), 0, covers=["payload: a number", "gives-way: older lines", "keeps: the total"])
        record = with_test(record, 1, covers=["payload: a missing total", "gives-way: the header"])
        self.assert_refused(
            record, "criterion 7.1 has no test covering keeps item 'the total' together with every give-way item"
        )

    def test_kept_item_with_no_row_is_refused(self):
        self.assert_refused(
            with_test(base_record(), 0, covers=ORDER_COVERS),
            "criterion 7.1 has no test covering keeps item 'the total' together with every give-way item",
        )

    def test_kept_item_of_an_unproven_criterion_needs_no_row(self):
        self.assert_accepted(with_criterion(base_record(), unproven="needs the live service", tests=[]))

    def test_row_covering_an_unknown_kept_item_is_refused(self):
        self.assert_refused(
            with_test(base_record(), 0, covers=WHOLE_ORDER_COVERS + ["keeps: the date"]),
            "criterion 7.1 test 'test_total' covers unknown keeps item 'the date'",
        )

    def test_cover_without_a_separator_names_every_form(self):
        self.assert_refused(
            with_test(base_record(), 0, covers=WHOLE_ORDER_COVERS + ["keeps the total"]),
            "criterion 7.1 test 'test_total' covers 'keeps the total', which is not '<domain>: <class>', "
            "'gives-way: <item>' or 'keeps: <item>'",
        )

    def test_domain_named_keeps_is_refused(self):
        record = base_record()
        kept = {
            "name": "keeps",
            "over": "the kept lines",
            "source": "repo",
            "closed": True,
            "defined_by": "build-app",
            "classes": ["one", "two"],
        }
        self.assert_refused(
            with_criterion(record, domains=record["criteria"][0]["domains"] + [kept]),
            "criterion 7.1 domain 'keeps' uses the reserved name 'keeps'",
        )

    def test_step_without_reads_is_refused_when_complete(self):
        self.assert_refused(
            with_build_app(base_record(), dropped=("reads",)), "step 'build-app' does not list the inputs its code reads"
        )

    def test_step_reading_nothing_is_accepted(self):
        self.assert_accepted(with_build_app(base_record(), reads=[]))

    def test_read_naming_no_domain_of_its_criteria_is_refused(self):
        self.assert_refused(
            with_build_app(base_record(), reads=["payload", "lines"]),
            "step 'build-app' reads 'lines', which is no domain of the criteria it proves",
        )

    def test_read_naming_a_domain_of_another_criterion_is_refused(self):
        date = {
            "name": "date",
            "over": "the date the app shows",
            "source": "repo",
            "closed": True,
            "fact": "f1",
            "classes": ["a date"],
        }
        record = with_parts(
            with_build_app(base_record(), reads=["payload", "date"]),
            [date_criterion(date, covers=["date: a date"])],
            [date_step(reads=["date"])],
        )
        self.assert_refused(record, "step 'build-app' reads 'date', which is no domain of the criteria it proves")

    def test_read_listed_twice_is_refused(self):
        self.assert_refused(
            with_build_app(base_record(), reads=["payload", "payload"]),
            "step 'build-app' lists read 'payload' more than once",
        )

    def test_reads_that_is_not_a_list_is_refused(self):
        self.assert_refused(
            with_build_app(base_record(), reads="payload"),
            "step 'build-app' has reads that is not a list of non-empty strings",
        )

    def test_handed_off_record_without_review_is_refused(self):
        self.assert_refused(handed_off(base_record()), "record is handed off but has no review")

    def test_handed_off_record_with_an_empty_review_list_is_refused(self):
        self.assert_refused(handed_off(with_reviews(base_record(), [])), "record is handed off but has no review")

    def test_last_review_without_input_issues_hands_off(self):
        reviews = [
            {"status": "Issues found", "issues": [OPEN_DOMAIN], "reviewed": open_digest()},
            {**APPROVED, "reviewed": base_digest()},
        ]
        self.assert_accepted(handed_off(with_reviews(base_record(), reviews)))

    def test_last_review_with_only_other_issues_hands_off(self):
        reviews = [{"status": "Issues found", "issues": [CLARITY], "reviewed": base_digest()}]
        self.assert_accepted(handed_off(with_reviews(base_record(), reviews)))

    def test_last_review_with_an_input_issue_is_refused(self):
        issue = {"category": "Missing input", "text": "Step build-app, open input: it reads the clock."}
        reviews = [{"status": "Issues found", "issues": [issue], "reviewed": base_digest()}]
        self.assert_refused(
            handed_off(with_reviews(base_record(), reviews)),
            "record is handed off but review 1 of the record as it stands reports Missing input: 'Step build-app, "
            "open input: it reads the clock.'",
        )

    def test_input_issue_on_the_record_as_it_stands_blocks_a_later_review(self):
        reviews = [
            {"status": "Issues found", "issues": [OPEN_DOMAIN], "reviewed": base_digest()},
            {**APPROVED, "reviewed": base_digest()},
        ]
        self.assert_refused(
            handed_off(with_reviews(base_record(), reviews)),
            "record is handed off but review 1 of the record as it stands reports Open domain: '7.1 payload takes "
            "any total the service sends.'",
        )

    def test_last_review_of_an_earlier_record_is_refused(self):
        record = handed_off(with_reviews(base_record(), [{**APPROVED, "reviewed": base_digest()}]))
        self.assert_refused(
            with_criterion(record, title="The total is shown"),
            "record is handed off but its last review read an earlier version of the record or its spec; dispatch a "
            "fresh reviewer",
        )

    def test_record_too_deep_to_check_is_refused(self):
        module = load_check_record()
        text = json.dumps({**base_record(), "status": "nested"}).replace('"nested"', "[" * 110000 + "]" * 110000)
        try:
            json.loads(text)
            accepted = True
        except RecursionError:
            accepted = False
        with tempfile.TemporaryDirectory() as folder:
            write_files(folder, SOURCE_FILES)
            findings = module.check(text, folder, complete=True, spec=BASE_SPEC)
        if accepted:
            self.assertEqual(findings, (("error", "record is nested too deeply to check"),))
        else:
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0][0], "error")
            self.assertTrue(findings[0][1].startswith("record is not valid JSON: "), findings[0][1][:200])

    def test_spec_change_after_the_last_review_is_refused(self):
        record = handed_off(with_reviews(base_record(), [{**APPROVED, "reviewed": base_digest()}]))
        self.assert_refused(
            record,
            "record is handed off but its last review read an earlier version of the record or its spec; dispatch a "
            "fresh reviewer",
            spec=CHANGED_SPEC,
        )

    def test_reviews_without_a_readable_spec_are_refused(self):
        record = with_reviews(base_record(), [{**APPROVED, "reviewed": base_digest()}])
        message = "the spec beside the record cannot be read, and the review digest covers it"
        self.assert_refused(record, message, spec=None)
        with tempfile.TemporaryDirectory() as folder:
            write_files(folder, SOURCE_FILES)
            path = write_record(folder, json.dumps(record), spec=None)
            code, out, _ = run_script(CHECK_SCRIPT, ["--complete", path], folder)
        self.assertEqual(code, 1)
        self.assertIn("error: " + message, out.splitlines())

    def test_check_reads_the_spec_beside_the_record(self):
        record = handed_off(with_reviews(base_record(), [{**APPROVED, "reviewed": base_digest()}]))
        with tempfile.TemporaryDirectory() as folder:
            write_files(folder, SOURCE_FILES)
            path = write_record(folder, json.dumps(record))
            code, out, err = run_script(CHECK_SCRIPT, ["--complete", path], folder)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(tuple(line for line in out.splitlines() if line.startswith("error: ")), ())

    def test_render_passes_the_spec_to_the_check(self):
        record = with_reviews(base_record(), [{"status": "Fine", "issues": [], "reviewed": base_digest()}])
        arguments = ["--record", "t.record.json", "--spec", "t.md", "--items", "t.items.json"]
        with tempfile.TemporaryDirectory() as folder:
            write_files(folder, SOURCE_FILES)
            write_record(folder, json.dumps(record))
            code, out, _ = run_script(RENDER_SCRIPT, arguments, folder)
            spec_after = pathlib.Path(folder, "t.md").read_bytes()
            items_written = pathlib.Path(folder, "t.items.json").exists()
        self.assertEqual(code, 1)
        self.assertIn("error: review 1 has status 'Fine', which is not 'Approved' or 'Issues found'", out.splitlines())
        self.assertEqual(spec_after, BASE_SPEC)
        self.assertFalse(items_written)

    def test_handed_off_record_with_a_malformed_last_review_is_refused(self):
        self.assert_refused(
            handed_off(with_reviews(base_record(), ["Approved"])),
            "review 1 is not an object with status, issues and reviewed",
        )

    def test_reviews_that_is_not_a_list_is_refused(self):
        self.assert_refused(handed_off({**base_record(), "reviews": {}}), "record has reviews that is not a list")

    def test_review_with_an_unknown_key_is_refused(self):
        reviews = [{**APPROVED, "by": "me", "reviewed": base_digest()}]
        self.assert_refused(with_reviews(base_record(), reviews), "review 1 has unknown key 'by'")

    def test_review_with_another_status_is_refused(self):
        reviews = [{"status": "Fine", "issues": [], "reviewed": base_digest()}]
        self.assert_refused(
            with_reviews(base_record(), reviews), "review 1 has status 'Fine', which is not 'Approved' or 'Issues found'"
        )

    def test_review_with_a_status_that_is_not_text_is_refused(self):
        reviews = [{"status": ["Approved"], "issues": [], "reviewed": base_digest()}]
        self.assert_refused(
            with_reviews(base_record(), reviews),
            "review 1 has status ['Approved'], which is not 'Approved' or 'Issues found'",
        )

    def test_unreadable_review_of_an_earlier_version_is_accepted(self):
        reviews = [
            {"status": "Fine", "issues": "none", "reviewed": open_digest()},
            {**APPROVED, "reviewed": base_digest()},
        ]
        self.assert_accepted(handed_off(with_reviews(base_record(), reviews)))

    def test_review_whose_issues_is_not_a_list_is_refused(self):
        reviews = [{"status": "Approved", "issues": "none", "reviewed": base_digest()}]
        self.assert_refused(with_reviews(base_record(), reviews), "review 1 has issues that is not a list")

    def test_reviewed_that_is_not_a_digest_is_refused(self):
        reviews = [{**APPROVED, "reviewed": "abc"}]
        self.assert_refused(with_reviews(base_record(), reviews), "review 1 has reviewed that is not a sha256 digest")

    def test_issues_found_with_no_issue_is_refused(self):
        reviews = [{"status": "Issues found", "issues": [], "reviewed": base_digest()}]
        self.assert_refused(with_reviews(base_record(), reviews), "review 1 has status 'Issues found' but no issue")

    def test_approved_review_with_an_issue_is_refused(self):
        reviews = [{"status": "Approved", "issues": [CLARITY], "reviewed": base_digest()}]
        self.assert_refused(with_reviews(base_record(), reviews), "review 1 has status 'Approved' but lists issues")

    def test_issue_with_an_unknown_category_is_refused(self):
        reviews = [{"status": "Issues found", "issues": [GATE], "reviewed": base_digest()}]
        self.assert_refused(
            with_reviews(base_record(), reviews),
            "review 1 issue 1 has category 'Gate', which is not a spec reviewer category",
        )

    def test_issue_with_a_category_that_is_not_text_is_refused(self):
        issue = {"category": ["Clarity"], "text": "7.1 reads two ways."}
        reviews = [{"status": "Issues found", "issues": [issue], "reviewed": base_digest()}]
        self.assert_refused(
            with_reviews(base_record(), reviews),
            "review 1 issue 1 has category ['Clarity'], which is not a spec reviewer category",
        )

    def test_old_category_in_a_review_of_an_earlier_version_is_accepted(self):
        reviews = [
            {"status": "Issues found", "issues": [GATE], "reviewed": open_digest()},
            {**APPROVED, "reviewed": base_digest()},
        ]
        self.assert_accepted(with_reviews(base_record(), reviews))

    def test_issue_with_empty_text_is_refused(self):
        issue = {"category": "Clarity", "text": ""}
        reviews = [{"status": "Issues found", "issues": [issue], "reviewed": base_digest()}]
        self.assert_refused(
            with_reviews(base_record(), reviews), "review 1 issue 1 has text that is not a non-empty string"
        )

    def test_issue_with_an_unknown_key_is_refused(self):
        issue = {**CLARITY, "line": 3}
        reviews = [{"status": "Issues found", "issues": [issue], "reviewed": base_digest()}]
        self.assert_refused(with_reviews(base_record(), reviews), "review 1 issue 1 has unknown key 'line'")

    def test_issue_that_is_not_an_object_is_refused(self):
        reviews = [{"status": "Issues found", "issues": ["Clarity: 7.1 reads two ways."], "reviewed": base_digest()}]
        self.assert_refused(
            handed_off(with_reviews(base_record(), reviews)),
            "review 1 issue 1 is not an object with category and text",
        )

    def test_reviewer_categories_are_read_from_the_reviewer_file(self):
        module = load_check_record()
        self.assertEqual(tuple(module.reviewer_categories(REVIEWER_FILE)), REVIEWER_CATEGORIES)
        self.assertEqual(tuple(module.INPUT_CATEGORIES), INPUT_CATEGORIES)

    def test_unreadable_reviewer_file_is_refused(self):
        record = with_reviews(base_record(), [{**APPROVED, "reviewed": base_digest()}])
        with tempfile.TemporaryDirectory() as other:
            path = os.path.join(other, "spec-reviewer.md")
            found = errors(self.check(record, reviewer=path))
        self.assertIn("cannot read the spec reviewer's categories from " + path, found)

    def test_reviewer_file_lacking_an_input_category_is_refused(self):
        record = with_reviews(base_record(), [{**APPROVED, "reviewed": base_digest()}])
        text = REVIEWER_FILE.read_text(encoding="utf-8")
        kept = "".join(line for line in text.splitlines(keepends=True) if not line.startswith("- Open domain:"))
        self.assertNotEqual(kept, text)
        with tempfile.TemporaryDirectory() as other:
            path = os.path.join(other, "spec-reviewer.md")
            pathlib.Path(path).write_text(kept, encoding="utf-8")
            found = errors(self.check(record, reviewer=path))
        self.assertIn("the spec reviewer's categories in " + path + " lack input category 'Open domain'", found)

    def test_reviewer_file_is_unread_without_a_review_of_the_record_as_it_stands(self):
        record = with_reviews(base_record(), [{**APPROVED, "reviewed": open_digest()}])
        with tempfile.TemporaryDirectory() as other:
            path = os.path.join(other, "spec-reviewer.md")
            found = errors(self.check(record, reviewer=path))
        self.assertEqual(found, ())

    def test_digest_ignores_reviews_and_status(self):
        first = self.digest_run(json.dumps(base_record()))
        second = self.digest_run(json.dumps(handed_off(with_reviews(base_record(), [APPROVED]))))
        for code, out, err in (first, second):
            self.assertEqual(code, 0, err)
            self.assertIsNotNone(DIGEST_RE.fullmatch(out), out)
        self.assertEqual(first[1], second[1])

    def test_digest_changes_with_the_record(self):
        first = self.digest_run(json.dumps(base_record()))
        second = self.digest_run(json.dumps(with_criterion(base_record(), title="The total is shown")))
        self.assertEqual((first[0], second[0]), (0, 0))
        self.assertIsNotNone(DIGEST_RE.fullmatch(first[1]), first[1])
        self.assertIsNotNone(DIGEST_RE.fullmatch(second[1]), second[1])
        self.assertNotEqual(first[1], second[1])

    def test_digest_changes_with_the_spec(self):
        first = self.digest_run(json.dumps(base_record()))
        second = self.digest_run(json.dumps(base_record()), spec=CHANGED_SPEC)
        self.assertEqual((first[0], second[0]), (0, 0))
        self.assertIsNotNone(DIGEST_RE.fullmatch(first[1]), first[1])
        self.assertIsNotNone(DIGEST_RE.fullmatch(second[1]), second[1])
        self.assertNotEqual(first[1], second[1])

    def test_digest_without_a_spec_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_record(folder, json.dumps(base_record()), spec=None)
            result = run_script(CHECK_SCRIPT, ["--digest", path], folder)
            spec_path = os.path.join(folder, "t.md")
        self.assertEqual(result, (2, "", "cannot read: " + spec_path + "\n"))

    def test_digest_of_a_record_not_named_record_json_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_record(folder, json.dumps(base_record()), name="t.json")
            result = run_script(CHECK_SCRIPT, ["--digest", path], folder)
        self.assertEqual(
            result, (2, "", "cannot find the spec of " + path + ": its name does not end with .record.json\n")
        )

    def test_digest_of_json_that_is_not_an_object_is_refused(self):
        self.assertEqual(self.digest_run("[]"), (2, "", "record is not a JSON object\n"))

    def test_digest_of_text_that_is_not_json_is_refused(self):
        code, out, err = self.digest_run("not json")
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("record is not valid JSON: "), err)
        self.assertEqual(len(err.splitlines()), 1, err)

    def test_digest_of_a_missing_file_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "missing.record.json")
            result = run_script(CHECK_SCRIPT, ["--digest", path], folder)
        self.assertEqual(result, (2, "", "cannot read: " + path + "\n"))

    def test_digest_with_other_arguments_prints_the_usage(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_record(folder, json.dumps(base_record()))
            other = write_record(folder, json.dumps(base_record()), name="u.record.json")
            results = tuple(
                run_script(CHECK_SCRIPT, arguments, folder)
                for arguments in (["--digest", "--complete", path], ["--digest"], ["--digest", path, other])
            )
        for result in results:
            self.assertEqual(result, (2, "", USAGE_LINE + "\n"))

    def test_digest_of_a_record_with_a_lone_surrogate(self):
        record = with_criterion(base_record(), title="\ud800")
        text = json.dumps(record)
        self.assertIn('"title": "\\ud800"', text)
        code, out, err = self.digest_run(text)
        self.assertEqual(code, 0, err)
        self.assertIsNotNone(DIGEST_RE.fullmatch(out), out)
        self.assertEqual(errors(self.check(record)), ())

    def test_digest_of_json_nested_too_deeply_is_refused(self):
        code, out, err = self.digest_run("[" * 1000000)
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("record is not valid JSON: "), err[:200])

    def test_record_too_deep_to_digest_is_refused(self):
        module = load_check_record()
        record = with_reviews(base_record(), [{**APPROVED, "reviewed": "0" * 64}])
        text = json.dumps(record)
        out = io.StringIO()
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            write_files(folder, SOURCE_FILES)
            path = write_record(folder, text)
            with mock.patch.object(module.json, "dumps", side_effect=RecursionError):
                digest = module.digest(record, BASE_SPEC)
                findings = module.check(text, folder, complete=True, spec=BASE_SPEC)
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = module.main(["--digest", path])
        self.assertIsNone(digest)
        self.assertIn("record is nested too deeply to digest", errors(findings))
        self.assertEqual((code, out.getvalue(), err.getvalue()), (2, "", "record is nested too deeply to digest\n"))

    def test_missing_parts_warn_without_complete(self):
        base = base_record()
        cases = (
            (
                with_payload(base, dropped=("source",)),
                DOMAIN + " does not say where its values come from; give source repo, outside, person, stored or sent",
            ),
            (with_payload(base, dropped=("closed",)), DOMAIN + " does not say whether it is closed"),
            (with_payload(base, dropped=("invalid",)), DOMAIN + " has source outside but lists no invalid class"),
            (
                with_payload(base, dropped=("invalid",), source="person", fact="f1"),
                DOMAIN + " has source person but lists no invalid class",
            ),
            (
                with_payload(base, dropped=("invalid",), source="stored", fact="f1"),
                DOMAIN + " has source stored but lists no invalid class",
            ),
            (
                with_payload(base, dropped=("invalid",), source="sent", fact="f1"),
                DOMAIN + " has source sent but lists no invalid class",
            ),
            (
                with_payload(base, closed=False),
                DOMAIN + " is not closed; decide where its input can be listed, give the criterion varies, or name in "
                "open_by the decision that keeps it open",
            ),
            (
                with_test(with_criterion(base, dropped=("keeps",)), 0, covers=ORDER_COVERS),
                "criterion 7.1 sets a bound but lists nothing in keeps",
            ),
            (
                with_test(base, 0, covers=ORDER_COVERS),
                "criterion 7.1 has no test covering keeps item 'the total' together with every give-way item",
            ),
            (with_build_app(base, dropped=("reads",)), "step 'build-app' does not list the inputs its code reads"),
            (
                with_payload(base, dropped=("fact",), source="repo"),
                DOMAIN + " has source repo but names no repository fact and no step in defined_by",
            ),
            (with_payload(base, dropped=("fact",)), DOMAIN + " has source outside but names no fact marked outside"),
        )
        for record, message in cases:
            with self.subTest(message=message):
                loose = self.check(record, complete=False)
                self.assertIn(message, warnings(loose))
                self.assertEqual(errors(loose), ())
                self.assertIn(message, errors(self.check(record)))

    def test_criterion_without_inputs_or_bound_needs_no_new_fields(self):
        criterion = {
            "number": "7.1",
            "title": "The total shows",
            "text": "WHEN the app starts THE SYSTEM SHALL show the total.",
            "where": ["unit-tests"],
            "tests": [
                {
                    "file": "tests/test_app.py",
                    "name": "test_total",
                    "given": "the app starts",
                    "expect": "the total is shown",
                    "env": "unit-tests",
                    "step": "build-app",
                }
            ],
        }
        self.assert_accepted(with_build_app({**base_record(), "criteria": [criterion]}, reads=[]))


if __name__ == "__main__":
    unittest.main()
