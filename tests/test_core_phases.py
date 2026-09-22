import pathlib
import unittest

HEADINGS = (
    "## Phase 1: Intake",
    "## Phase 2: Classify",
    "## Phase 3: Ground",
    "## Phase 4: Interrogate",
    "## Phase 5: Challenge",
    "## Phase 6: Read back",
    "## Phase 7: Write the spec",
    "## Phase 8: Review",
    "## Phase 9: Split into Steps",
    "## Phase 10: Hand off",
)

RULES = (
    "Never create, edit or delete a tracked file in the user's working tree, except adding the spec folder to .gitignore when the user chooses that in phase 1.",
    "Never commit, push, stash, reset, check out or rebase in the user's repository.",
    "Never implement: the spec states the cause, the boundary and the acceptance test, never the patch.",
    "Look up facts yourself; ask the user only for decisions.",
    "Never answer your own decision question; recommend an answer and wait for the user's explicit yes.",
    "Write every default you choose into the spec as an assumption.",
    "Save each answer to the decisions file the moment it is given.",
    "Silence, \"just do it\", and your own judgement that the spec is fine are not approval.",
    "Only the main conversation talks to the user; agents never ask the user anything.",
    "Never name, detect or invoke any tool that might consume the spec.",
)

STEP_FILES = ("core/phases.md",)


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def read_phases():
    return (repo_root() / "core" / "phases.md").read_text(encoding="utf-8")


class CorePhasesTest(unittest.TestCase):
    def test_phases_lists_all_ten_phases_in_order(self):
        lines = read_phases().splitlines()
        positions = tuple(
            lines.index(heading) if heading in lines else -1 for heading in HEADINGS
        )
        self.assertNotIn(-1, positions)
        self.assertEqual(list(positions), sorted(positions))

    def test_phases_states_every_rule_verbatim(self):
        text = read_phases()
        lines = text.splitlines()
        self.assertIn("## Rules", lines)
        self.assertIn(HEADINGS[0], lines)
        rules_line = lines.index("## Rules")
        self.assertLess(rules_line, lines.index(HEADINGS[0]))
        rules_block = "\n".join(lines[rules_line:lines.index(HEADINGS[0])])
        positions = tuple(
            rules_block.find(f"{number}. {rule}")
            for number, rule in enumerate(RULES, start=1)
        )
        self.assertNotIn(-1, positions)
        self.assertEqual(list(positions), sorted(positions))
        for relative in STEP_FILES:
            content = (repo_root() / relative).read_text(encoding="utf-8")
            self.assertNotIn("mitosis", content.lower(), relative)


if __name__ == "__main__":
    unittest.main()
