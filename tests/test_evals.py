import pathlib
import unittest

CASES = {
    "bug-report-starts-bug-pathway": (
        "The export button on the invoices page doesn't work as expected. "
        "It downloads an empty file instead of the invoice PDF. "
        "Determine the cause of the issue.",
        "interphase:bug",
        {"min": "1"},
    ),
    "new-capability-starts-feature-pathway": (
        "I want users to be able to export all of their invoices as a CSV file. "
        "Nothing like this exists yet. "
        "Help me pin down exactly what it should do before anyone builds it.",
        "interphase:feature",
        {"min": "1"},
    ),
    "mockup-starts-prototype-pathway": (
        "I have a checkout page mockup exported from Claude Design as checkout.html. "
        "I want it shipped as a real, working checkout flow in this app.",
        "interphase:prototype",
        {"min": "1"},
    ),
    "router-never-starts-itself": (
        "Help me figure out what to build next for this project.",
        "interphase:interphase",
        {"min": "0", "max": "0"},
    ),
}


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def strip_quotes(value):
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def parse_frontmatter(text):
    lines = text.splitlines()
    fences = [index for index, line in enumerate(lines) if line == "---"][:2]
    if len(fences) < 2:
        return {}, text
    pairs = [
        line.split(":", 1)
        for line in lines[fences[0] + 1:fences[1]]
        if ":" in line
    ]
    fields = {key.strip(): strip_quotes(value.strip()) for key, value in pairs}
    body = "\n".join(lines[fences[1] + 1:])
    return fields, body


def parse_list(value):
    inner = value.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1]
    return [item.strip() for item in inner.split(",") if item.strip()]


class EvalsTest(unittest.TestCase):
    def test_evals_cover_every_trigger_case(self):
        root = repo_root()
        for case, (prompt, _, _) in CASES.items():
            with self.subTest(case=case):
                path = root / "evals" / case / "prompt.md"
                self.assertTrue(path.is_file(), str(path))
                fields, body = parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual(fields.get("name"), case)
                self.assertTrue(fields.get("description"))
                self.assertEqual(fields.get("runs"), "3")
                self.assertEqual(fields.get("max_turns"), "3")
                self.assertIn("Skill", parse_list(fields.get("allowed_tools", "")))
                self.assertEqual(body.strip(), prompt)
        step_files = [
            root / "evals" / case / name
            for case in CASES
            for name in ("prompt.md", "graders/skill-fired.md")
        ]
        for path in step_files:
            with self.subTest(file=str(path)):
                self.assertTrue(path.is_file(), str(path))
                self.assertNotIn("mitosis", path.read_text(encoding="utf-8").lower())

    def test_evals_graders_check_the_skill_tool(self):
        root = repo_root()
        for case, (_, match, bounds) in CASES.items():
            with self.subTest(case=case):
                path = root / "evals" / case / "graders" / "skill-fired.md"
                self.assertTrue(path.is_file(), str(path))
                fields, body = parse_frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual(fields.get("type"), "tool_used")
                self.assertEqual(fields.get("tool"), "Skill")
                self.assertEqual(fields.get("input_match"), match)
                for key, value in bounds.items():
                    self.assertEqual(fields.get(key), value)
                if "max" not in bounds:
                    self.assertNotIn("max", fields)
                self.assertTrue(body.strip())


if __name__ == "__main__":
    unittest.main()
