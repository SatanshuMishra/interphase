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
        "description": "Use when a written interphase spec and its Steps need one fresh-eyes review before hand-off.",
        "tools": "Read, Grep, Glob",
        "model": "opus",
        "effort": "high",
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

    def test_spec_reviewer_checks_proof(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        self.assertIn("- Proof: a criterion whose tests run only where passing does not prove it for the user", body)

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
        self.assertLess(body.index("- Proof:"), body.index("- Variation:"))
        self.assertLess(body.index("- Variation:"), body.index("- Boundary:"))

    def test_spec_reviewer_checks_the_steps(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        for marker in (
            "Review the spec and the items file",
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
            "builds more than the intent or a recorded decision asks for",
            "against the practices file and the decisions file whose paths you are also given",
            "neither the request, a recorded decision nor the practices file asks for",
            "Skip style and wording preferences.",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)


    def test_spec_reviewer_reviews_once(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        self.assertIn("You review once; nobody reviews the fixes after you, so report every real issue now.", body)

    def test_spec_reviewer_checks_unattended_runs_against_their_context(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        for marker in (
            "- Context: in an unattended run, a requirement the product's context calls for in the requested work",
            "what the laws, standards or established practice of its domain require",
            "that the spec does not make a requirement, however it is left out: Out of scope, an assumption, a note left to the deployment or silence.",
            "In an unattended run, what the product's context calls for in the requested work counts as asked for.",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)
        self.assertLess(body.index("- Scope:"), body.index("- Context:"))
        self.assertLess(body.index("- Context:"), body.index("- Testability:"))
        self.assertLess(body.index("- Tracking talk:"), body.index("counts as asked for"))
        self.assertLess(body.index("counts as asked for"), body.index("Report only issues"))

    def test_spec_reviewer_checks_intent_glossary_and_seams(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        for marker in (
            "- Intent: a decision, criterion or Step that does not serve the intent lines",
            "- Assumption: an assumption that cites an intent line which does not support it",
            "- Domain language: a term used against its glossary definition",
            "a decision that reverses an ADR without saying it supersedes it",
            "- Seams: an acceptance test at a seam the spec does not list",
            "or more seams than the change needs.",
            "against the project's `GLOSSARY.md` and the ADRs in `docs/adr/` when they exist.",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)
        self.assertNotIn("Review bar", body)

    def test_spec_reviewer_skips_what_scripts_check(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        self.assertIn(
            "The record check, the render script, the spec check and the items check have already passed. Never report what they check: placeholders, empty sections, unknown keys, uncovered classes, assumptions that cite no intent line and criteria no Step claims.",
            body,
        )

    def test_spec_reviewer_keeps_case_tables_to_security_and_refusal(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        line = next(line for line in body.splitlines() if line.startswith("- Case table:"))
        for marker in (
            "behaviour that is security-sensitive or exists to refuse something with no case table",
            "a case table on any other behaviour",
            "a case table missing a class a real path delivers",
            "Name the file and line.",
        ):
            self.assertIn(marker, line)
        self.assertIn(
            "- Outside fact: a claim about software outside the repository that no recorded command and output shows and the spec does not list as an assumption.",
            body,
        )
        self.assertNotIn("- Give-way:", body)

    def test_spec_reviewer_accepts_a_sound_spec(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        self.assertIn("An issue that needs an input no real path delivers is not one.", body)
        self.assertIn("No issues is a correct result: approve a spec that would build the right thing.", body)

    def test_spec_reviewer_drops_script_checked_categories(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        lines = body.splitlines()
        self.assertEqual(tuple(line for line in lines if line.startswith("- Completeness:")), ())
        self.assertEqual(tuple(line for line in lines if line.startswith("- Trace:")), ())

    def test_spec_reviewer_writes_issues_as_dash_lines(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        self.assertIn("Then write each issue as one line starting `- ` that names the section or Step, the problem and why it matters.", body)
        self.assertIn("Start no other line with `- `.", body)
        self.assertIn("Output a `Status:` line first. It reads `Approved` or `Issues found`.", body)
        self.assertLess(body.index("Output a `Status:` line first."), body.index("Then write each issue as one line starting `- `"))


if __name__ == "__main__":
    unittest.main()
