import pathlib
import unittest

FEATURE_SENTENCE = (
    "Give every behaviour acceptance lines for its error state, its empty state and its permission state."
)
BUG_SENTENCE = (
    "Give the fault an acceptance line that reproduces it on the old code, and give every other place a sweep "
    "of the same class finds its own acceptance line."
)
PROJECT_SENTENCE = "Give the foundations acceptance lines for the build and for CI."
PROTOTYPE_SENTENCE = "Give every screen state a judged acceptance line with a rubric and three trials."


def acceptance_section(pathway):
    path = pathlib.Path(__file__).resolve().parents[1] / "core" / "pathways" / (pathway + ".md")
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = [position for position, line in enumerate(lines) if line == "## Acceptance"]
    if not starts:
        return ""
    start = starts[0]
    ends = [position for position in range(start + 1, len(lines)) if lines[position].startswith("## ")]
    return "\n".join(lines[start + 1 : ends[0] if ends else len(lines)])


class PathwayLineKindsTest(unittest.TestCase):
    def assert_acceptance_holds(self, pathway, sentence):
        body = acceptance_section(pathway)
        self.assertNotEqual(body, "", pathway)
        self.assertIn(sentence, body)

    def test_feature_requires_error_empty_and_permission_lines(self):
        self.assert_acceptance_holds("feature", FEATURE_SENTENCE)

    def test_bug_requires_reproduction_and_class_sweep_lines(self):
        self.assert_acceptance_holds("bug", BUG_SENTENCE)

    def test_project_requires_build_and_ci_lines(self):
        self.assert_acceptance_holds("project", PROJECT_SENTENCE)

    def test_prototype_requires_judged_lines_with_a_rubric(self):
        self.assert_acceptance_holds("prototype", PROTOTYPE_SENTENCE)


if __name__ == "__main__":
    unittest.main()
