import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "core" / "pathways" / "prototype.md"
TEMPLATE = ROOT / "core" / "templates" / "spec-prototype.md"

PLAYBOOK_HEADINGS = (
    "## Ground",
    "## Gap analysis",
    "## Questions",
    "## Extra step",
    "## Acceptance",
    "## Steps",
)

TEMPLATE_HEADINGS = (
    "## 1. Request",
    "## 2. Source artefacts",
    "## 3. Intended and incidental",
    "## 4. Screens and journeys",
    "## 5. State matrix",
    "## 6. Content variation",
    "## 7. Interactions not shown",
    "## 8. Data sources",
    "## 9. Validation and errors",
    "## 10. Auth and permissions",
    "## 11. Persistence and concurrency",
    "## 12. Accessibility",
    "## 13. Responsive behaviour",
    "## 14. Analytics",
    "## 15. Non-goals",
    "## 16. Acceptance criteria",
    "## 17. Assumptions",
    "## 18. Open questions",
    "## 19. Reuse and change",
)


def section_body(lines, heading):
    start = lines.index(heading) + 1
    rest = lines[start:]
    ends = [i for i, line in enumerate(rest) if line.startswith("## ")]
    return rest[: ends[0]] if ends else rest


class PrototypePathwayTest(unittest.TestCase):
    def test_prototype_playbook_has_every_section(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        level_two = [line for line in lines if line.startswith("## ")]
        self.assertEqual(list(PLAYBOOK_HEADINGS), level_two)
        gap = section_body(lines, "## Gap analysis")
        numbered = [line for line in gap if re.match(r"^\d+\. \S", line)]
        self.assertEqual(15, len(numbered))
        self.assertEqual(
            [str(n) for n in range(1, 16)],
            [line.split(".", 1)[0] for line in numbered],
        )

    def test_prototype_template_has_every_numbered_section(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        lines = text.splitlines()
        self.assertEqual("# {{title}}", lines[0])
        self.assertIn("Pathway: prototype.", lines)
        self.assertIn("Date: {{date}}.", lines)
        numbered = [line for line in lines if re.match(r"^## \d+\.", line)]
        self.assertEqual(list(TEMPLATE_HEADINGS), numbered)
        for heading in TEMPLATE_HEADINGS:
            body = "\n".join(section_body(lines, heading))
            self.assertIn("{{", body, heading)
        for path in (PLAYBOOK, TEMPLATE):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("mitosis", content.lower(), str(path))

    def test_prototype_template_numbers_each_acceptance_criterion(self):
        lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
        body = section_body(lines, "## 16. Acceptance criteria")
        self.assertTrue(any(line.startswith("### 16.1 ") for line in body))

    def test_prototype_playbook_designs_steps_during_the_interview(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        steps_body = "\n".join(section_body(lines, "## Steps"))
        self.assertIn("Design the Steps during the interview", steps_body)
        acceptance_body = "\n".join(section_body(lines, "## Acceptance"))
        self.assertIn("### 16.1", acceptance_body)

    def test_prototype_ground_maps_the_prototype_to_existing_code(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        ground = "\n".join(section_body(lines, "## Ground"))
        self.assertIn("Map every component and data flow in the prototype to existing code that already provides it", ground)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/core/practices.md", ground)

    def test_prototype_template_records_reuse_and_change(self):
        lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
        body = "\n".join(section_body(lines, "## 19. Reuse and change"))
        for label in ("Reused as is", "Kept separate", "Changed"):
            self.assertIn(label, body)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/core/practices.md", body)

    def test_prototype_sorts_gaps_with_the_questioning_table(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        extra = "\n".join(section_body(lines, "## Extra step"))
        self.assertIn("`${CLAUDE_PLUGIN_ROOT}/core/questioning.md`", extra)
        self.assertIn("Sort every unknown", extra)
        self.assertNotIn("- Cosmetic: default to the mockup", extra)


if __name__ == "__main__":
    unittest.main()
