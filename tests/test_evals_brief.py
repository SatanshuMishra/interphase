import importlib.util
import pathlib
import re
import unittest

CASE_PREFIXES = ("lane-", "autonomy-")
BRIEF_PATTERN = "^Lane: brief\\.$"
NOT_BRIEF_PATTERN = "Lane: brief\\."
REGEX_FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}
BRIEF_TEMPLATE = "core/templates/spec-brief.md"
FULL_TEMPLATES = ("core/templates/spec-bug.md", "core/templates/spec-feature.md")
RUBRIC_START = "PASS when the spec makes"
RUBRIC_END = "as the context that decided them; FAIL otherwise."

HELDOUT_CASES = {
    "lane-tasks-per-page": (
        "7469b2bf54e3cf5952a4c0b04f2940c4bec7ce0d8efeeae375f1ea04684ce012",
        "tasks-app",
        "lane-tasks-per-page",
        ("eligible", "bug"),
    ),
    "lane-add-button-label": (
        "b2d50363f993f175002bd15b2cc4d5ba134399b86e51dfeee11d7cefe1a3c7ac",
        "tasks-app",
        "lane-add-button-label",
        ("eligible", "bug"),
    ),
    "lane-clear-completed": (
        "8c8548ba17395682d45ff6fa0125d8aa870293f6c4d3d57393ff022b5ba26ce5",
        "tasks-app",
        "lane-clear-completed",
        ("eligible", "feature"),
    ),
    "lane-sync-to-phone": (
        "f29c4c6cfed27b1c95065c52f5a020485584582046253f1d38047a2901ac06c2",
        "tasks-app",
        "lane-sync-to-phone",
        ("full", "subsystem"),
    ),
    "lane-sqlite-storage": (
        "b40273454d9c2275169d1e98ce644a0ecb48db03b49e223c564ffcf44fde619f",
        "tasks-app",
        "lane-sqlite-storage",
        ("full", "storage"),
    ),
    "lane-due-date-from-model": (
        "2139c912cd7b357eddbefc010d57ab677d4c5667a11477e1dec9e109f31226a7",
        "tasks-app",
        "lane-due-date-from-model",
        ("full", "varies"),
    ),
    "lane-scroll-stutter-on-phone": (
        "3742dbfda40011d794c64b034078897f3c77531ecfa7044b084a6ff1fda8e1f7",
        "tasks-app",
        "lane-scroll-stutter-on-phone",
        ("full", "measured"),
    ),
    "autonomy-login-coffee-shop": (
        "9f16733e48f2cba070bf32be8a96c8cd69292603fcca79399975915ba17cfdab",
        "coffee-shop",
        "login",
        ("autonomy", "low-stakes"),
    ),
    "autonomy-login-bank": (
        "9f16733e48f2cba070bf32be8a96c8cd69292603fcca79399975915ba17cfdab",
        "bank",
        "login",
        ("autonomy", "high-stakes"),
    ),
}

DEV_CASES = {
    "lane-dev-eligible-bug": (
        "Notes are listed oldest first, but the README says newest first",
        "notes-app",
        "lane-dev-eligible-bug",
        ("eligible", "bug"),
    ),
    "lane-dev-eligible-feature": (
        "Add a 'Duplicate' button beside each note's existing 'Delete' button, working the same way",
        "notes-app",
        "lane-dev-eligible-feature",
        ("eligible", "feature"),
    ),
    "lane-dev-full-subsystem": (
        "Let two people share a notebook and see each other's edits",
        "notes-app",
        "lane-dev-full-subsystem",
        ("full", "subsystem"),
    ),
    "lane-dev-full-storage": (
        "Keep every past version of a note so an earlier one can be restored",
        "notes-app",
        "lane-dev-full-storage",
        ("full", "storage"),
    ),
    "lane-dev-full-varies": (
        "Tag each note automatically with topics picked by a language model",
        "notes-app",
        "lane-dev-full-varies",
        ("full", "varies"),
    ),
    "lane-dev-full-measured": (
        "Typing in a long note lags on my old iPad",
        "notes-app",
        "lane-dev-full-measured",
        ("full", "measured"),
    ),
    "autonomy-dev-book-club": (
        "Design how people sign in",
        "book-club",
        "sign-in",
        ("autonomy", "low-stakes"),
    ),
    "autonomy-dev-clinic": (
        "Design how people sign in",
        "clinic",
        "sign-in",
        ("autonomy", "high-stakes"),
    ),
}

RUBRICS = {
    "autonomy-login-coffee-shop": (
        "a sign-in by email and password or by an emailed one-time link",
        "passwords, if used, stored only as salted hashes",
        "a limit on repeated failed sign-ins",
        "does not make multi-factor authentication, phone-number sign-in or a CAPTCHA a Must",
        "the single coffee shop and its customers",
    ),
    "autonomy-login-bank": (
        "multi-factor authentication",
        "account lockout or rate limiting after failed attempts",
        "bot protection such as a CAPTCHA or device checks",
        "a password reset that verifies identity through a second channel",
        "an idle session timeout",
        "encryption of credentials and sessions in transit and at rest",
        "the regulated retail bank",
    ),
    "autonomy-dev-book-club": (
        "a sign-in by an emailed one-time link or by email and password",
        "passwords, if used, stored only as salted hashes",
        "a limit on repeated failed sign-ins",
        "does not make multi-factor authentication, phone-number sign-in or a CAPTCHA a Must",
        "the neighbourhood book club and its members",
    ),
    "autonomy-dev-clinic": (
        "multi-factor authentication",
        "account lockout or rate limiting after failed attempts",
        "links a new account to the right patient before it shows any record",
        "a password reset that verifies identity through a second channel",
        "an idle session timeout",
        "encryption of credentials and sessions in transit and at rest",
        "an audit log of who viewed each patient's records",
        "the medical clinic and its patients' health records",
    ),
}

FIXTURE_FACTS = {
    "coffee-shop": (
        "# Bean There",
        "a loyalty app for one independent coffee shop with a single location and about 300 regular customers",
        "open it on their phones to see their stamp count",
        "staff add stamps at the counter",
        "No sign-in exists yet",
    ),
    "bank": (
        "# Northbank Online",
        "online banking for Northbank, a regulated retail bank",
        "view their account balances and statements and send transfers",
        "No sign-in exists yet",
    ),
    "book-club": (
        "a sign-up sheet for a neighbourhood book club of about 20 people",
        "No sign-in exists yet",
    ),
    "clinic": (
        "a patient portal for a medical clinic",
        "upcoming appointments",
        "test results",
        "No sign-in exists yet",
    ),
}


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def load_test_module(name):
    path = pathlib.Path(__file__).resolve().parent / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_helpers():
    return tuple(load_test_module(name) for name in ("test_evals", "test_evals_leak", "test_evals_variation"))


def spec_path(spec):
    return "docs/specs/" + spec + ".md"


def expected_graders(group, spec):
    target = {"source": "file", "path": spec_path(spec)}
    graders = {
        "eligible": {"brief.md": {"type": "regex", "target": target, "pattern": BRIEF_PATTERN, "flags": "m"}},
        "full": {
            "not-brief.md": {"type": "regex", "target": target, "pattern": NOT_BRIEF_PATTERN, "match": "not_contains"},
            "spec-written.md": {"type": "file_exists", "path": spec_path(spec), "exists": "true"},
        },
        "autonomy": {"rubric.md": {"type": "llm", "focus": target}},
    }
    return graders[group]


def grader_fields(fields, variation):
    return {
        key: variation.parse_flow_map(value) if key in ("target", "focus") else variation.yaml_scalar(value)
        for key, value in fields.items()
    }


def grader_passes(fields, text):
    flags = sum(REGEX_FLAGS[flag] for flag in fields.get("flags", ""))
    found = re.search(fields["pattern"], text, flags) is not None
    return found != (fields.get("match") == "not_contains")


def case_names(suite):
    folder = repo_root() / suite
    return sorted(path.name for path in folder.iterdir() if path.is_dir() and path.name.startswith(CASE_PREFIXES))


def readme_text(script):
    match = re.search(r"^cat > README\.md <<'EOF'\n(.*?)\nEOF$", script, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def strata(cases):
    return {stratum for *_, stratum in cases.values()}


class EvalsBriefTest(unittest.TestCase):
    def assert_case(self, helpers, suite, name, fixture, spec, group):
        evals, leak, variation = helpers
        case = repo_root() / suite / name
        prompt = case / "prompt.md"
        self.assertTrue(prompt.is_file(), str(prompt))
        fields, body = evals.parse_frontmatter(prompt.read_text(encoding="utf-8"))
        self.assertEqual(fields.get("name"), name)
        self.assertTrue(fields.get("description"))
        for key, value in variation.FULL_RUN_SETTINGS.items():
            self.assertEqual(fields.get(key), value, key)
        self.assertEqual(evals.parse_list(fields.get("allowed_tools", "")), variation.FULL_RUN_TOOLS)
        request = leak.request_text(body)
        self.assertEqual(body.strip(), variation.FULL_RUN_PROMPT.format(request, spec))
        settings = variation.parse_yaml_fields((case / "case.yaml").read_text(encoding="utf-8"), evals.strip_quotes)
        self.assertEqual(
            settings,
            {"schema_version": "1.1", "name": name, "context.scaffold_script": "scaffold.sh"},
        )
        canonical = repo_root() / suite / "fixtures" / (fixture + ".sh")
        self.assertEqual((case / "scaffold.sh").read_bytes(), canonical.read_bytes())
        bodies = self.assert_graders(helpers, case / "graders", spec, group)
        if group == "autonomy":
            self.assert_rubric(bodies["rubric.md"], RUBRICS[name])
        return request

    def assert_graders(self, helpers, folder, spec, group):
        evals, _, variation = helpers
        expected = expected_graders(group, spec)
        graders = {
            path.name: evals.parse_frontmatter(path.read_text(encoding="utf-8")) for path in folder.glob("*.md")
        }
        self.assertEqual({name: grader_fields(fields, variation) for name, (fields, _) in graders.items()}, expected)
        for _, body in graders.values():
            self.assertTrue(body.strip())
        brief = (repo_root() / BRIEF_TEMPLATE).read_text(encoding="utf-8")
        full = tuple((repo_root() / path).read_text(encoding="utf-8") for path in FULL_TEMPLATES)
        for fields in (fields for fields in expected.values() if fields["type"] == "regex"):
            self.assertEqual(grader_passes(fields, brief), group == "eligible")
            for text in full:
                self.assertEqual(grader_passes(fields, text), group == "full")
        return {name: body for name, (_, body) in graders.items()}

    def assert_rubric(self, body, phrases):
        rubric = " ".join(body.split())
        self.assertTrue(rubric.startswith(RUBRIC_START), rubric)
        self.assertTrue(rubric.endswith(RUBRIC_END), rubric)
        for phrase in phrases:
            self.assertIn(phrase, rubric)

    def assert_fixtures(self, variation, suite, cases):
        for fixture in sorted({fixture for _, fixture, _, _ in cases.values()}):
            with self.subTest(fixture=fixture):
                script = repo_root() / suite / "fixtures" / (fixture + ".sh")
                variation.EvalsVariationTest.assert_fixture_builds(self, script)
                readme = readme_text(script.read_text(encoding="utf-8"))
                for fact in FIXTURE_FACTS.get(fixture, ()):
                    self.assertIn(fact, readme)

    def test_brief_heldout_cases_match_the_spec(self):
        helpers = load_helpers()
        variation = helpers[2]
        self.assertEqual(case_names("evals-heldout"), sorted(HELDOUT_CASES))
        for name, (digest, fixture, spec, stratum) in HELDOUT_CASES.items():
            with self.subTest(case=name):
                request = self.assert_case(helpers, "evals-heldout", name, fixture, spec, stratum[0])
                self.assertEqual(variation.request_digest(request), digest, request)
        self.assert_fixtures(variation, "evals-heldout", HELDOUT_CASES)

    def test_brief_dev_cases_cover_every_stratum(self):
        self.assertEqual(strata(DEV_CASES), strata(HELDOUT_CASES))
        helpers = load_helpers()
        evals, leak, variation = helpers
        requests = leak.heldout_requests(repo_root(), evals.parse_frontmatter)
        heldout = frozenset().union(*(variation.sentences(text) for text in requests))
        self.assertTrue(heldout)
        self.assertEqual(case_names("evals-dev"), sorted(DEV_CASES))
        for name, (expected, fixture, spec, stratum) in DEV_CASES.items():
            with self.subTest(case=name):
                request = self.assert_case(helpers, "evals-dev", name, fixture, spec, stratum[0])
                self.assertEqual(request, expected)
                self.assertFalse(variation.sentences(request) & heldout, request)
        self.assert_fixtures(variation, "evals-dev", DEV_CASES)


if __name__ == "__main__":
    unittest.main()
