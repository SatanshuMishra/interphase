import pathlib
import unittest

AGENT_FILES = ("agents/scout.md", "agents/spec-reviewer.md")
FORBIDDEN_TOOLS = frozenset({"Edit", "Write", "NotebookEdit", "Bash", "Agent"})
EXPECTED = {
    "agents/scout.md": {
        "name": "scout",
        "description": "Use when interphase needs facts looked up in the codebase, its documentation or outside library documentation, and the answer can come back as a short cited summary.",
        "tools": "Read, Grep, Glob, WebFetch, WebSearch",
        "model": "inherit",
    },
    "agents/spec-reviewer.md": {
        "name": "spec-reviewer",
        "description": "Use when a written interphase spec and its Steps need a fresh-eyes review before the user is asked to approve them.",
        "tools": "Read, Grep, Glob",
        "model": "inherit",
    },
}


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def read_agent(relative):
    return (repo_root() / relative).read_text(encoding="utf-8")


def strip_quotes(value):
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def split_frontmatter(text):
    lines = text.splitlines()
    fences = [index for index, line in enumerate(lines) if line == "---"][:2]
    if len(fences) < 2:
        return (), "\n".join(lines)
    return tuple(lines[fences[0] + 1:fences[1]]), "\n".join(lines[fences[1] + 1:])


def parse_frontmatter(text):
    header, _ = split_frontmatter(text)
    pairs = (line.split(":", 1) for line in header if ":" in line)
    return {key.strip(): strip_quotes(value.strip()) for key, value in pairs}


def tool_names(frontmatter):
    return frozenset(part.strip() for part in frontmatter.get("tools", "").split(","))


class AgentsTest(unittest.TestCase):
    def test_agents_are_read_only(self):
        for relative in AGENT_FILES:
            with self.subTest(agent=relative):
                text = read_agent(relative)
                frontmatter = parse_frontmatter(text)
                self.assertIn("tools", frontmatter)
                self.assertEqual(tool_names(frontmatter) & FORBIDDEN_TOOLS, frozenset())
                self.assertNotIn("mitosis", text.lower())

    def test_agents_have_their_verbatim_frontmatter(self):
        for relative, expected in EXPECTED.items():
            with self.subTest(agent=relative):
                frontmatter = parse_frontmatter(read_agent(relative))
                actual = {key: frontmatter.get(key) for key in expected}
                self.assertEqual(actual, expected)
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        for marker in ("Status:", "Approved", "Issues found"):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)

    def test_spec_reviewer_checks_the_steps(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        for marker in (
            "Review the spec and the items file",
            "- Trace:",
            "- Task drift:",
            "- Task independence:",
            "- Build order:",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)


if __name__ == "__main__":
    unittest.main()
