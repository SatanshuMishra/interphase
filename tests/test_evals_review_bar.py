import importlib.util
import pathlib
import unittest

CASE_PREFIX = "reviewbar-"
FIXTURE = "evals-heldout/fixtures/tasks-app.sh"
PROMPT_FIELDS = {"name", "description", "runs", "max_turns", "timeout_seconds", "allowed_tools"}
GRADERS = ["review-bar.md", "rubric.md", "spec-written.md"]
REVIEW_BAR_PATTERN = "## \\d+\\. Review bar"
RUBRIC_PHRASES = ("Review bar", "out of scope", "before the change", "FAIL")
THREAT = "threat"
NO_THREATS = "no threats beyond"

HELDOUT_CASES = {
    "reviewbar-shared-list": (
        "1cfeb2f51efd524fe21660ecc70ad1039f22459fc1fcd37a2fa9c3783c3f417b",
        True,
    ),
    "reviewbar-sort-by-due": (
        "b25f8993b0bed9344f5811a1a331b14d851c3f565e0397b3fd40d84fa0ac8cda",
        False,
    ),
}

DEV_CASES = {
    "reviewbar-dev-csv-export": (
        "Add a button that downloads every task as a CSV file. "
        "Work autonomously. Name the spec reviewbar-dev-csv-export.",
        True,
    ),
    "reviewbar-dev-button-label": (
        "Rename the Done button to Complete. "
        "Work autonomously. Name the spec reviewbar-dev-button-label.",
        False,
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


def case_names(suite):
    folder = repo_root() / suite
    return sorted(path.name for path in folder.iterdir() if path.is_dir() and path.name.startswith(CASE_PREFIX))


def spec_path(name):
    return "docs/specs/" + name + ".md"


class EvalsReviewBarTest(unittest.TestCase):
    def assert_case(self, helpers, suite, name):
        evals, leak, variation = helpers
        case = repo_root() / suite / name
        prompt = case / "prompt.md"
        self.assertTrue(prompt.is_file(), str(prompt))
        fields, body = evals.parse_frontmatter(prompt.read_text(encoding="utf-8"))
        self.assertEqual(set(fields), PROMPT_FIELDS)
        self.assertEqual(fields.get("name"), name)
        self.assertTrue(fields.get("description"))
        for key, value in variation.FULL_RUN_SETTINGS.items():
            self.assertEqual(fields.get(key), value, key)
        self.assertEqual(evals.parse_list(fields.get("allowed_tools", "")), variation.FULL_RUN_TOOLS)
        request = leak.without_prefix(body.strip(), leak.FULL_RUN_PREFIX)
        self.assertEqual(body.strip(), leak.FULL_RUN_PREFIX + request)
        self.assertEqual(body.strip(), variation.FULL_RUN_PROMPT.format(leak.request_text(body), name))
        settings = variation.parse_yaml_fields((case / "case.yaml").read_text(encoding="utf-8"), evals.strip_quotes)
        self.assertEqual(
            settings,
            {"schema_version": "1.1", "name": name, "context.scaffold_script": "scaffold.sh"},
        )
        self.assertEqual((case / "scaffold.sh").read_bytes(), (repo_root() / FIXTURE).read_bytes())
        rubric = self.assert_graders(helpers, case / "graders", name)
        return request, rubric

    def assert_graders(self, helpers, folder, name):
        evals, _, variation = helpers
        self.assertEqual(sorted(path.name for path in folder.iterdir()), GRADERS)
        graders = {
            path.name: evals.parse_frontmatter(path.read_text(encoding="utf-8")) for path in folder.glob("*.md")
        }
        for grader, (_, body) in graders.items():
            self.assertEqual(len(variation.sentences(body)), 1, grader)
        spec = spec_path(name)
        fields, _ = graders["spec-written.md"]
        self.assertEqual(fields, {"type": "file_exists", "path": spec, "exists": "true"})
        fields, _ = graders["review-bar.md"]
        self.assertEqual(set(fields), {"type", "target", "pattern", "match"})
        self.assertEqual(fields["type"], "regex")
        self.assertEqual(variation.parse_flow_map(fields["target"]), {"source": "file", "path": spec})
        self.assertEqual(variation.yaml_scalar(fields["pattern"]), REVIEW_BAR_PATTERN)
        self.assertEqual(fields["match"], "contains")
        fields, body = graders["rubric.md"]
        self.assertEqual(set(fields), {"type", "focus"})
        self.assertEqual(fields["type"], "llm")
        self.assertEqual(variation.parse_flow_map(fields["focus"]), {"source": "file", "path": spec})
        return " ".join(body.split())

    def assert_rubric(self, rubric, threatened):
        self.assertTrue(rubric.startswith("PASS when"), rubric)
        for phrase in RUBRIC_PHRASES:
            self.assertIn(phrase, rubric)
        if threatened:
            self.assertIn(THREAT, rubric)
            self.assertNotIn(NO_THREATS, rubric)
        else:
            self.assertIn(NO_THREATS, rubric)

    def test_review_bar_eval_cases_match_the_spec(self):
        helpers = load_helpers()
        evals, leak, variation = helpers
        self.assertEqual(case_names("evals-heldout"), sorted(HELDOUT_CASES))
        self.assertEqual(case_names("evals-dev"), sorted(DEV_CASES))
        for name, (digest, threatened) in HELDOUT_CASES.items():
            with self.subTest(case=name):
                request, rubric = self.assert_case(helpers, "evals-heldout", name)
                self.assertEqual(variation.request_digest(request), digest, request)
                self.assert_rubric(rubric, threatened)
        requests = leak.heldout_requests(repo_root(), evals.parse_frontmatter)
        heldout = frozenset().union(*(variation.sentences(text) for text in requests))
        self.assertTrue(heldout)
        for name, (expected, threatened) in DEV_CASES.items():
            with self.subTest(case=name):
                request, rubric = self.assert_case(helpers, "evals-dev", name)
                self.assertEqual(request, expected)
                self.assertFalse(variation.sentences(request) & heldout, request)
                self.assert_rubric(rubric, threatened)


if __name__ == "__main__":
    unittest.main()
