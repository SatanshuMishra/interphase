import pathlib
import unittest

PLAYBOOK_HEADINGS = (
    "## Ground",
    "## Probes",
    "## Questions",
    "## Extra step",
    "## Acceptance",
    "## Steps",
)



def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def read(relative):
    return (repo_root() / relative).read_text(encoding="utf-8")


def playbook_section(heading):
    lines = read("core/pathways/bug.md").splitlines()
    start = lines.index(heading) + 1
    end = start
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    return lines[start:end]




class PathwayBugTest(unittest.TestCase):
    def test_bug_playbook_has_every_section(self):
        text = read("core/pathways/bug.md")
        lines = text.splitlines()
        found = tuple(line for line in lines if line in PLAYBOOK_HEADINGS)
        self.assertEqual(found, PLAYBOOK_HEADINGS)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/probe.py", text)
        for relative in ("core/pathways/bug.md", "core/templates/spec-bug.md"):
            self.assertNotIn("mitosis", read(relative).lower(), relative)

    def test_bug_playbook_designs_steps_during_the_interview(self):
        steps_text = "\n".join(playbook_section("## Steps"))
        self.assertIn("Design the Steps during the interview", steps_text)
        acceptance_text = "\n".join(playbook_section("## Acceptance"))
        self.assertIn("Make the draft failing test criterion 5.1.", acceptance_text)

    def test_bug_playbook_fixes_every_place_with_the_same_fault(self):
        ground = "\n".join(playbook_section("## Ground"))
        self.assertIn(
            "Follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md` to find every other place with the same fault.",
            ground,
        )
        acceptance = "\n".join(playbook_section("## Acceptance"))
        self.assertIn("Give every place with the same fault its own test that fails before the fix.", acceptance)

    def test_bug_probe_ends_at_the_cause(self):
        probes = "\n".join(playbook_section("## Probes"))
        self.assertIn("A probe ends when its hypothesis is confirmed or refuted.", probes)
        self.assertIn("Never build, test or repair the fix inside a probe", probes)
        self.assertIn(
            "follow the rule for it in Phase 3 of `${CLAUDE_PLUGIN_ROOT}/core/phases.md`",
            probes,
        )

    def test_bug_steps_use_the_record(self):
        steps = "\n".join(playbook_section("## Steps"))
        self.assertIn("Record that file and test in the record as a test of criterion 5.1", steps)
        self.assertIn("List criterion 5.1 in the fix Step's `criteria`", steps)
        self.assertNotIn("in the fix Step's `acceptance`", steps)
        self.assertNotIn("in its `spec_ref`", steps)

    def test_bug_acceptance_follows_the_variation_rules(self):
        acceptance = "\n".join(playbook_section("## Acceptance"))
        self.assertIn("`${CLAUDE_PLUGIN_ROOT}/core/variation.md`", acceptance)


    def test_bug_playbook_cites_criteria_in_the_fix_boundary(self):
        lines = read("core/pathways/bug.md").splitlines()
        expected = '  - Expected: "WHEN <condition> THE SYSTEM SHALL <right behaviour>", citing the acceptance criterion that states it.'
        unchanged = '  - Unchanged: "WHEN <other condition> THE SYSTEM SHALL CONTINUE TO <behaviour that already works>", citing the acceptance criterion that states it.'
        self.assertIn(expected, lines)
        self.assertIn(unchanged, lines)
        self.assertEqual(lines.index(unchanged), lines.index(expected) + 1)


if __name__ == "__main__":
    unittest.main()
