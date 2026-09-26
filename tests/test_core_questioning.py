import pathlib
import unittest

HEADINGS = (
    "## Sort every unknown",
    "## Choose the next question",
    "## Ask",
    "## Spot ambiguity",
    "## Push back on scope",
    "## Record each answer",
    "## Know when to stop",
)

STEP_FILES = ("core/questioning.md",)


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def read_questioning():
    return (repo_root() / "core" / "questioning.md").read_text(encoding="utf-8")


def section_body(lines, heading):
    start = lines.index(heading) + 1
    rest = lines[start:]
    ends = [i for i, line in enumerate(rest) if line.startswith("## ")]
    return rest[: ends[0]] if ends else rest


def first_column(table_lines):
    rows = [line for line in table_lines if line.strip().startswith("|")]
    cells = [row.strip().strip("|").split("|")[0].strip() for row in rows]
    return tuple(cell for cell in cells[2:])


class QuestioningTest(unittest.TestCase):
    def test_questioning_has_every_section_in_order(self):
        lines = read_questioning().splitlines()
        positions = tuple(
            lines.index(heading) if heading in lines else -1 for heading in HEADINGS
        )
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, tuple(sorted(positions)))
        for relative in STEP_FILES:
            text = (repo_root() / relative).read_text(encoding="utf-8")
            self.assertNotIn("mitosis", text.lower(), relative)

    def test_questioning_sorts_unknowns_into_three_classes(self):
        text = read_questioning()
        body = section_body(text.splitlines(), "## Sort every unknown")
        self.assertEqual(first_column(body), ("Intent", "Structure", "Cosmetic"))
        self.assertIn("AskUserQuestion", text)

    def test_questioning_sorts_the_shape_of_the_work_as_intent(self):
        lines = read_questioning().splitlines()
        body = section_body(lines, "## Sort every unknown")
        intent_line = next(line for line in body if line.strip().startswith("| Intent |"))
        self.assertIn("what ships together", intent_line)
        structure_line = next(line for line in body if line.strip().startswith("| Structure |"))
        self.assertIn("which files and tests each Step needs", structure_line)

    def test_questioning_stops_after_the_phase_7_read_back(self):
        text = read_questioning()
        self.assertIn("Stop asking when all four hold:", text)
        self.assertIn("2. Every acceptance criterion has a Step whose test proves it.", text)
        self.assertIn("4. The user confirmed the read-back in phase 7.", text)


if __name__ == "__main__":
    unittest.main()
