import pathlib
import unittest

TEXT_CRITERION_SENTENCES = (
    "A text criterion is a criterion about the repository's own authored text: a document, a README, a changelog, a version file, or the wording of a skill, a prompt or a brief.",
    "To tell a text criterion from a behaviour criterion, ask whether a change to shipped code alone can make it fail; when it cannot, it is a text criterion.",
    "Place a text criterion at the seam `authored-text`, which interphase reserves for text criteria and declares with `builder_runs` true, and give it acceptance lines and no test row: each line's command is a lint check the repository's lint stage runs, an existing one or one a Step adds beside the repository's other lint checks, and it exits 0 when the text is right and 1 when it is not.",
    "The Step that claims a text criterion lists the file of every lint check it adds and, when the lint stage names its checks one by one, the file that names them, so the check is registered there; it has an empty acceptance list when it claims only text criteria, and adds no locked path.",
    "When the repository has no lint stage, place a criterion about authored text at an ordinary seam and give it a test row like any other criterion, never at the seam `authored-text`.",
    "Start the command of a lint check a Step adds with a program already installed, such as `python3 scripts/check_changelog.py` or `sh scripts/check_changelog.sh`, because the surface probe runs before the Step adds the file.",
)
ACCEPTANCE_ROW = "| `acceptance` |"


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def read(relative):
    return (repo_root() / relative).read_text(encoding="utf-8")


def section(relative, heading):
    lines = read(relative).splitlines()
    start = lines.index(heading) + 1
    end = start
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    return "\n".join(lines[start:end])


def only_line(body, prefix):
    matches = [line for line in body.splitlines() if line.startswith(prefix)]
    if len(matches) != 1:
        raise AssertionError(f"expected one line starting {prefix!r}, found {len(matches)}")
    return matches[0]


class TextCriterionInstructionsTest(unittest.TestCase):
    def assert_defines_a_text_criterion(self, relative, heading):
        body = section(relative, heading)
        for sentence in TEXT_CRITERION_SENTENCES:
            with self.subTest(sentence=sentence):
                self.assertIn(sentence, body)

    def test_items_guide_defines_a_text_criterion(self):
        self.assert_defines_a_text_criterion("core/items.md", "## Interview record")

    def test_phases_define_a_text_criterion(self):
        self.assert_defines_a_text_criterion("core/phases.md", "## Phase 4: Interview")

    def test_feature_playbook_defines_a_text_criterion(self):
        self.assert_defines_a_text_criterion("core/pathways/feature.md", "## Acceptance")

    def test_bug_playbook_defines_a_text_criterion(self):
        self.assert_defines_a_text_criterion("core/pathways/bug.md", "## Acceptance")

    def test_project_playbook_defines_a_text_criterion(self):
        self.assert_defines_a_text_criterion("core/pathways/project.md", "## Acceptance")

    def test_prototype_playbook_defines_a_text_criterion(self):
        self.assert_defines_a_text_criterion("core/pathways/prototype.md", "## Acceptance")

    def test_grounding_finds_the_lint_stage(self):
        body = section("core/phases.md", "## Phase 3: Ground")
        self.assertIn(
            "- Find the repository's lint stage: the lint checks its CI, its build file or its written rules run.",
            body.splitlines(),
        )

    def test_items_format_allows_an_empty_list_for_text_criteria(self):
        row = only_line(section("core/items.md", "## Items format"), ACCEPTANCE_ROW)
        self.assertIn(
            "the list is empty on the check-author Step and on a Step whose every criterion is marked unproven, which the items check warns about",
            row,
        )
        self.assertIn("and on a Step whose every criterion is a text criterion", row)

    def test_readme_allows_an_empty_list_for_text_criteria(self):
        row = only_line(read("README.md"), ACCEPTANCE_ROW)
        self.assertIn(
            "The list may be empty only when every criterion the Step claims is marked unproven or is a text criterion, and must be empty on the check-author Step.",
            row,
        )

    def test_questioning_admits_the_reserved_seam(self):
        body = section("core/questioning.md", "## Test seams")
        self.assertIn(
            "The seam `authored-text` is the one seam that is neither a part nor a meeting point: it holds the text criteria, which their acceptance lines' lint commands decide, as `${CLAUDE_PLUGIN_ROOT}/core/items.md` says.",
            body,
        )

    def test_reviewer_admits_the_reserved_seam(self):
        bullet = only_line(read("agents/spec-reviewer.md"), "- Seams:")
        self.assertIn(
            "or a seam that no part and no meeting point the request changes or must cross calls for.",
            bullet,
        )
        self.assertIn(
            "The seam `authored-text` is reserved for text criteria and is never a seam no part and no meeting point calls for; report a text criterion that carries a test row, or one placed at that seam in a repository with no lint stage.",
            bullet,
        )


if __name__ == "__main__":
    unittest.main()
