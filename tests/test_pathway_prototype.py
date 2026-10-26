import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "core" / "pathways" / "prototype.md"

PLAYBOOK_HEADINGS = (
    "## Ground",
    "## Gap analysis",
    "## Questions",
    "## Extra step",
    "## Acceptance",
    "## Steps",
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

    def test_prototype_playbook_designs_steps_during_the_interview(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        steps_body = "\n".join(section_body(lines, "## Steps"))
        self.assertIn("Design the Steps during the interview", steps_body)
        acceptance_body = "\n".join(section_body(lines, "## Acceptance"))
        self.assertIn("Number each check under the Test seams section, such as `5.1`, and place it at an agreed seam.", acceptance_body)

    def test_prototype_ground_maps_the_prototype_to_existing_code(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        ground = "\n".join(section_body(lines, "## Ground"))
        self.assertIn("Map every component and data flow in the prototype to existing code that already provides it", ground)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/core/practices.md", ground)

    def test_prototype_sorts_gaps_with_the_hard_bar(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        extra = "\n".join(section_body(lines, "## Extra step"))
        self.assertIn("`${CLAUDE_PLUGIN_ROOT}/core/questioning.md`", extra)
        self.assertIn("a gap that passes the hard bar", extra)
        self.assertIn("a cosmetic gap takes the mockup's choice as an assumption", extra)
        self.assertNotIn("- Cosmetic: default to the mockup", extra)

    def test_prototype_acceptance_follows_the_variation_rules(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        acceptance = "\n".join(section_body(lines, "## Acceptance"))
        self.assertIn("`${CLAUDE_PLUGIN_ROOT}/core/variation.md`", acceptance)

    def test_prototype_points_the_ui_floor_at_impeccable(self):
        text = PLAYBOOK.read_text(encoding="utf-8")
        gap = section_body(text.splitlines(), "## Gap analysis")
        numbered = [line for line in gap if re.match(r"^\d+\. \S", line)]
        self.assertEqual([str(n) for n in range(1, 16)], [line.split(".", 1)[0] for line in numbered])
        item = numbered[10]
        for phrase in (
            "impeccable standard",
            "each platform the product ships",
            "judge every mockup choice against it",
            "role",
            "surface",
            "states",
            "form factors",
            "input methods",
            "where that command is not available",
            "WCAG 2.2 AA",
        ):
            self.assertIn(phrase, item)
        self.assertNotIn("24 by 24", text)

    def test_prototype_standard_overrides_the_mockup(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        extra = "\n".join(section_body(lines, "## Extra step"))
        self.assertIn("a cosmetic gap takes the mockup's choice as an assumption", extra)
        self.assertIn("A mockup choice that breaks the UI standard of item 11, cosmetic or behavioural, and whether or not it was called deliberate, is never kept and never asked: the spec states the corrected behaviour as an assumption.", extra)

    def test_prototype_never_asks_the_accessibility_level(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        questions = section_body(lines, "## Questions")
        self.assertEqual([], [line for line in questions if "accessibility level" in line.lower()])

    def test_prototype_comparison_expects_the_correction(self):
        lines = PLAYBOOK.read_text(encoding="utf-8").splitlines()
        acceptance = "\n".join(section_body(lines, "## Acceptance"))
        self.assertIn("compared with the mockup", acceptance)
        self.assertIn("expects the corrected behaviour where the build corrects a standard violation", acceptance)


if __name__ == "__main__":
    unittest.main()
