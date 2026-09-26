import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

HEADINGS = (
    "## Output files",
    "## Items format",
    "## Designing Steps",
    "## Writing a task",
    "## Checking the result",
)

FIELDS = (
    "name",
    "task",
    "files",
    "source",
    "acceptance",
    "after",
    "contract_group",
    "type",
    "complexity",
    "file_notes",
    "msp",
    "spec_ref",
    "assumptions",
)

STEP_FILES = ("core/items.md",)


def read_guide():
    return (ROOT / "core" / "items.md").read_text(encoding="utf-8")


def section(text, heading):
    lines = text.splitlines()
    start = lines.index(heading) + 1
    rest = lines[start:]
    end = next((i for i, line in enumerate(rest) if line.startswith("## ")), len(rest))
    return "\n".join(rest[:end])


class CoreItemsTest(unittest.TestCase):
    def test_items_guide_has_every_section_in_order(self):
        lines = read_guide().splitlines()
        positions = tuple(lines.index(h) if h in lines else -1 for h in HEADINGS)
        for heading, position in zip(HEADINGS, positions):
            self.assertNotEqual(position, -1, heading)
        self.assertEqual(list(positions), sorted(positions))
        for relative in STEP_FILES:
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("mitosis", content.lower(), relative)

    def test_items_guide_documents_every_field(self):
        text = read_guide()
        for field in FIELDS:
            self.assertIn("`" + field + "`", text, field)
        items = section(text, "## Items format")
        self.assertRegex(items, re.compile(r"only value[^.\n]*`type`[^.\n]*`contract`|`type`[^\n]*only the value `contract`"))

    def test_items_guide_designs_steps_during_the_interview(self):
        text = read_guide()
        designing = section(text, "## Designing Steps")
        self.assertIn("Design the Steps during the interview", designing)
        self.assertIn("Never derive them by reading the finished spec.", designing)

    def test_items_guide_has_no_size_cap_or_ignore_rule(self):
        text = read_guide()
        for forbidden in ("400", "gitignore", "Work breakdown"):
            self.assertNotIn(forbidden, text, forbidden)

    def test_items_guide_keeps_tasks_independent_of_the_spec(self):
        text = read_guide()
        writing = section(text, "## Writing a task")
        self.assertIn("Never send the builder to the spec", writing)
        output = section(text, "## Output files")
        self.assertIn("Each must be usable without the other.", output)


if __name__ == "__main__":
    unittest.main()
