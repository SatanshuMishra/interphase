import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PRACTICES = ROOT / "core" / "practices.md"

HEADINGS = (
    "## The five rules",
    "## Find what already exists",
    "## Reuse or ask",
    "## Record the result",
)

RULES = (
    "One home per piece of logic",
    "One reason to change per piece of code",
    "Build only what the request needs",
    "Follow the project's own written rules and patterns",
    "Use what the language, libraries or project already provide",
)


def read_practices():
    return PRACTICES.read_text(encoding="utf-8")


def section(text, heading):
    lines = text.splitlines()
    start = lines.index(heading) + 1
    rest = lines[start:]
    end = next((i for i, line in enumerate(rest) if line.startswith("## ")), len(rest))
    return "\n".join(rest[:end])


class CorePracticesTest(unittest.TestCase):
    def test_practices_has_every_section_in_order(self):
        text = read_practices()
        lines = text.splitlines()
        positions = tuple(lines.index(heading) if heading in lines else -1 for heading in HEADINGS)
        self.assertNotIn(-1, positions)
        self.assertEqual(list(positions), sorted(positions))
        self.assertNotIn("mitosis", text.lower())

    def test_practices_states_the_five_rules_in_order(self):
        body = section(read_practices(), "## The five rules")
        numbered = tuple(line for line in body.splitlines() if re.match(r"^\d+\. \S", line))
        self.assertEqual(len(numbered), len(RULES))
        for number, (line, rule) in enumerate(zip(numbered, RULES), start=1):
            self.assertTrue(line.startswith(f"{number}. {rule}"), line)
        self.assertIn("The project's own written rules win when they conflict with the other four.", body)

    def test_practices_defines_a_copy_and_bending(self):
        body = section(read_practices(), "## The five rules")
        self.assertIn("A copy is the same rule written in two places that must always change together.", body)
        self.assertIn("Bending is adding a mode, flag or branch inside existing shared logic that only the new use needs.", body)
        self.assertIn("A mode or option the request itself asks for is allowed, but its difference is kept outside the shared part, such as in what each use passes in or does with the result.", body)

    def test_practices_finds_what_already_exists(self):
        body = section(read_practices(), "## Find what already exists")
        self.assertIn("search for code that already does all or part of what is asked", body)
        for sentence in (
            "When the request is a bug, the same search finds every other place with the same fault.",
            "The fix covers every such place.",
            "Raise merging them as a fork only when they are copies.",
        ):
            with self.subTest(sentence=sentence):
                self.assertIn(sentence, body)
        for source in ("CLAUDE.md", "AGENTS.md", "contributing guide", "linter"):
            with self.subTest(source=source):
                self.assertIn(source, body)

    def test_practices_asks_only_at_a_fork(self):
        body = section(read_practices(), "## Reuse or ask")
        for sentence in (
            "Reuse existing code without asking when it already does the job unchanged.",
            "Ask the user only at a fork: when sharing would mean changing existing code for a new use, or keeping apart would mean copying its logic.",
            "Ask one question per fork, in the same rounds as the other questions, with a recommendation and a one-line reason.",
            "Recommend sharing the parts that must always change together and keeping apart the parts that differ.",
            "Never offer bending as an option.",
        ):
            with self.subTest(sentence=sentence):
                self.assertIn(sentence, body)

    def test_practices_records_three_short_lists(self):
        body = section(read_practices(), "## Record the result")
        for sentence in (
            "Reuse and change",
            "Reused as is",
            "Kept separate",
            "Changed",
            "Write None for an empty list.",
            "When a project rule overrode one of the other four, add one line after the three lists that starts with Project rule followed: and names the rule and the file it is written in.",
            "Never write a proof for each rule.",
        ):
            with self.subTest(sentence=sentence):
                self.assertIn(sentence, body)


if __name__ == "__main__":
    unittest.main()
