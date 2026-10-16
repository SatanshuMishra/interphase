import pathlib
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

    def test_feature_playbook_designs_steps_during_the_interview(self):
        lines = tuple(PLAYBOOK.read_text(encoding="utf-8").splitlines())
        sections = sections_by_heading(lines)
        steps_body = "\n".join(sections["## Steps"])
        self.assertIn("Design the Steps during the interview", steps_body)
        acceptance_body = "\n".join(sections["## Acceptance"])
        self.assertIn("Number each criterion under the Test seams section, such as `5.1`, and place it at an agreed seam.", acceptance_body)

    def test_feature_pathway_never_asks_for_an_example_to_copy(self):
        for path in (PLAYBOOK, TEMPLATE):
            self.assertNotIn("example to copy", path.read_text(encoding="utf-8"), str(path))

    def test_feature_ground_looks_for_code_that_already_does_the_job(self):
        lines = tuple(PLAYBOOK.read_text(encoding="utf-8").splitlines())
        ground = "\n".join(sections_by_heading(lines)["## Ground"])
        self.assertIn("already does all or part of what is asked", ground)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/core/practices.md", ground)

    def test_feature_acceptance_follows_the_variation_rules(self):
        lines = tuple(PLAYBOOK.read_text(encoding="utf-8").splitlines())
        acceptance = "\n".join(sections_by_heading(lines)["## Acceptance"])
        self.assertIn("`${CLAUDE_PLUGIN_ROOT}/core/variation.md`", acceptance)


if __name__ == "__main__":
    unittest.main()
