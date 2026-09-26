import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "core" / "pathways" / "feature.md"
TEMPLATE = ROOT / "core" / "templates" / "spec-feature.md"

PLAYBOOK_HEADINGS = (
    "## Ground",
    "## Questions",
    "## Extra step",
    "## Acceptance",
    "## Steps",
)

TEMPLATE_HEADINGS = (
    "## 1. Request",
    "## 2. Problem and why now",
    "## 3. Users and stories",
    "## 4. Goals and non-goals",
    "## 5. Boundaries",
    "## 6. Requirements",
    "## 7. Acceptance criteria",
    "## 8. Edge cases",
    "## 9. Code map",
    "## 10. Approach and alternatives",
    "## 11. Assumptions",
    "## 12. Open questions",
    "## 13. Verification",
)

NUMBERED = re.compile(r"^## \d+\. ")


def sections_by_heading(lines):
    starts = tuple(i for i, line in enumerate(lines) if line.startswith("## "))
    ends = starts[1:] + (len(lines),)
    return {lines[s]: tuple(lines[s + 1:e]) for s, e in zip(starts, ends)}


class PathwayFeatureTest(unittest.TestCase):
    def test_feature_playbook_has_every_section(self):
        lines = tuple(PLAYBOOK.read_text(encoding="utf-8").splitlines())
        found = tuple(line for line in lines if line in PLAYBOOK_HEADINGS)
        self.assertEqual(found, PLAYBOOK_HEADINGS)
        for path in (PLAYBOOK, TEMPLATE):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("mitosis", text.lower(), str(path))

    def test_feature_template_has_every_numbered_section(self):
        lines = tuple(TEMPLATE.read_text(encoding="utf-8").splitlines())
        self.assertEqual(lines[0], "# {{title}}")
        self.assertIn("Pathway: feature.", lines)
        self.assertIn("Date: {{date}}.", lines)
        numbered = tuple(line for line in lines if NUMBERED.match(line))
        self.assertEqual(numbered, TEMPLATE_HEADINGS)
        sections = sections_by_heading(lines)
        for heading in TEMPLATE_HEADINGS:
            body = "\n".join(sections[heading])
            self.assertIn("{{", body, heading)

    def test_feature_template_numbers_each_acceptance_criterion(self):
        lines = tuple(TEMPLATE.read_text(encoding="utf-8").splitlines())
        sections = sections_by_heading(lines)
        body = sections["## 7. Acceptance criteria"]
        self.assertTrue(any(line.startswith("### 7.1 ") for line in body))

    def test_feature_playbook_designs_steps_during_the_interview(self):
        lines = tuple(PLAYBOOK.read_text(encoding="utf-8").splitlines())
        sections = sections_by_heading(lines)
        steps_body = "\n".join(sections["## Steps"])
        self.assertIn("Design the Steps during the interview", steps_body)
        acceptance_body = "\n".join(sections["## Acceptance"])
        self.assertIn("### 7.1", acceptance_body)


if __name__ == "__main__":
    unittest.main()
