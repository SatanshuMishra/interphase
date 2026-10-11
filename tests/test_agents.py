import pathlib
import unittest

AGENT_FILES = ("agents/scout.md", "agents/spec-reviewer.md")
FORBIDDEN_TOOLS = frozenset({"Edit", "Write", "NotebookEdit", "Bash", "Agent"})
EXPECTED = {
    "agents/scout.md": {
        "name": "scout",
        "description": "Use when interphase needs outside documentation looked up, or needs to know where something is in the codebase, and each answer can be cited and checked.",
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

    def test_scout_answers_with_locations(self):
        _, body = split_frontmatter(read_agent("agents/scout.md"))
        self.assertIn("followed by the exact text of that line, quoted", body)
        self.assertNotIn("Cite each fact with a `path:line` reference or a URL.", body)

    def test_spec_reviewer_checks_proof_environments(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        self.assertIn(
            "- Proof environment: an acceptance criterion whose tests run only where passing does not prove it for the user",
            body,
        )

    def test_reviewer_checks_variation(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        for marker in (
            "- Variation:",
            "a behaviour that varies from run to run proved by one example",
            "a Step that tunes a prompt, rule or threshold against its own acceptance cases",
            "a held-out case that appears in a prompt or rule",
            "a criterion for varying behaviour with no kind",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)
        self.assertLess(body.index("- Proof environment:"), body.index("- Variation:"))
        self.assertLess(body.index("- Variation:"), body.index("- Boundary:"))

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

    def test_spec_reviewer_checks_for_tracking_talk(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        for marker in (
            "- Tracking talk:",
            "whether git tracks interphase's own output files",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)

    def test_spec_reviewer_checks_the_design(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        for marker in (
            "- Design:",
            "copies logic that already exists",
            "bends existing code to fit a new use",
            "builds more than the request or a recorded decision asks for",
            "against the practices file and the decisions file whose paths you are also given",
            "neither the request, a recorded decision nor the practices file asks for",
            "Skip style and wording preferences.",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)


    def test_spec_reviewer_checks_autonomous_runs_against_their_context(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        for marker in (
            "- Context: in an autonomous run, a requirement the product's context calls for in the requested work",
            "what the laws, standards or established practice of its domain require",
            "that the spec does not make a goal, however it is left out: a non-goal, a Won't, an open question, a later spec, a boundary, an assumption, a note left to the deployment or silence.",
            "Also, in an autonomous run, a requirement met outside the code with no acceptance criterion",
            "a part of it the code could enforce and test that is left outside the code",
            "In an autonomous run, what the product's context calls for in the requested work counts as asked for.",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)
        self.assertLess(body.index("- Scope:"), body.index("- Context:"))
        self.assertLess(body.index("- Context:"), body.index("- Testability:"))
        self.assertLess(body.index("- Tracking talk:"), body.index("counts as asked for"))
        self.assertLess(body.index("counts as asked for"), body.index("Report only issues"))

    def test_spec_reviewer_checks_the_review_bar(self):
        text = read_agent("agents/spec-reviewer.md")
        _, body = split_frontmatter(text)
        lines = body.splitlines()
        context_index = next(
            index for index, line in enumerate(lines) if line.startswith("- Context:")
        )
        review_bar = lines[context_index + 1]
        self.assertTrue(review_bar.startswith("- Review bar:"))
        for marker in (
            "missing",
            "empty",
            "defends",
            "leaves out",
            "could check",
            "before the change",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, review_bar)
        self.assertEqual(
            sum(1 for line in lines if line.startswith("- Review bar:")), 1
        )
        expected = EXPECTED["agents/spec-reviewer.md"]
        frontmatter = parse_frontmatter(text)
        self.assertEqual({key: frontmatter.get(key) for key in expected}, expected)


if __name__ == "__main__":
    unittest.main()
