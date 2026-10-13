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
            "Review the spec, the items file and the record",
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


    def test_spec_reviewer_skips_what_scripts_check(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        paragraphs = body.split("\n\n")
        starts = tuple(
            i for i, p in enumerate(paragraphs) if p.startswith("Review the spec, the items file and the record at the paths you are given")
        )
        self.assertEqual(len(starts), 1)
        self.assertEqual(
            paragraphs[starts[0] + 1],
            "The record check, the render script, the spec check and the items check have already passed. Never report what they check: placeholders, empty sections, unknown keys, uncited lines, uncovered classes, criteria no Step claims, and a missing `source`, `closed`, `invalid`, `keeps` or `reads`. Check instead whether what the record declares is true of the code and the request.",
        )

    def test_spec_reviewer_checks_closed_contracts(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        lines = body.splitlines()
        positions = tuple(i for i, line in enumerate(lines) if line.startswith("- Clarity:"))
        self.assertEqual(len(positions), 1)
        start = positions[0] + 1
        self.assertEqual(
            lines[start:start + 8],
            [
            "- Missing input: an input a Step's code will read, found in its task, in the files it changes or in the code those files call, that neither the Step's `reads` nor any domain of the criteria it proves names. Name the file and line or the sentence of the task.",
            "- Missing class: an input the code reads, at a line a domain cites or that you find by searching the code, with a class no domain lists, such as an absent field, an empty value, a renamed file, a subfolder or a truncated value; a class that the place defining the values tells apart, such as a schema, a parser or the reply of the program that produces them, that the domain leaves out; a criterion that says every, each, any, all, whole, always, never, whatever, however or whenever with no domain over some kind of thing the word ranges over; or a value whose size or count nothing bounds, with no class beyond every bound the behaviour sets. Name the file and line.",
            "- Stand-in: a domain over a value the code reads to learn another, with no class where the two differ.",
            "- Source: a domain whose `source` is not what produces its values. It is `outside` whenever a program, tool, system or service outside the repository produces them, even when the repository's code parses them; `person` when a person types, picks or says them; `stored` when the code reads them back from a file, database or other store it wrote earlier; `sent` when the repository's own code in another process, such as its client, a producer or another deployed version, sends them over a network, a queue, a pipe or another channel; and `repo` only otherwise. Also a `fact` or `defined_by` that does not show where the values are defined, asked for, written or sent, and classes that come from a description of the values rather than from where they are defined.",
            "- Give-way: a bound whose order of what gives way is missing or leaves a choice open; anything the criterion promises that `keeps` does not list, whether it sits in the order, is folded into a broader item there or is in neither list; or a kept item whose row does not make every item in the order give way.",
            "- Outside fact: a claim about software outside the repository that no recorded command and output shows, including one listed as an assumption or marked `assumed` although it could be run here.",
            "- Invalid input: an outside, person, stored or sent domain whose `invalid` classes leave out a way its input can arrive other than promised, such as missing, empty, malformed, of another type, cut short or written by an older version; or a behaviour that exists to refuse something and does not refuse on an invalid class, unless the user decided otherwise.",
            "- Open domain: a domain whose classes cannot all be listed, such as free text or shell commands, that the design still decides on, or a domain marked closed whose classes do not cover every value its input can take. Name a value that falls in no class, or in a class for every other value although it needs a different result. A domain kept open by `varies` for a behaviour that does not vary from run to run or that exists to refuse something counts, and so does one kept open by `open_by` in an autonomous run, or by a cited line that is not the user's own decision to keep this domain open. Report it even when the request names the mechanism that reads the input.",
            ],
        )

    def test_spec_reviewer_drops_script_checked_categories(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        lines = body.splitlines()
        self.assertEqual(tuple(line for line in lines if line.startswith("- Completeness:")), ())
        self.assertEqual(tuple(line for line in lines if line.startswith("- Trace:")), ())

    def test_spec_reviewer_reviews_the_record(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        self.assertIn(
            "Review the spec, the items file and the record at the paths you are given, against the practices file and the decisions file whose paths you are also given. Check them against these categories:",
            body,
        )
        self.assertIn(
            "The record check, the render script, the spec check and the items check have already passed. Never report what they check: placeholders, empty sections, unknown keys, uncited lines, uncovered classes, criteria no Step claims, and a missing `source`, `closed`, `invalid`, `keeps` or `reads`. Check instead whether what the record declares is true of the code and the request.",
            body,
        )

    def test_spec_reviewer_names_the_input_categories(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        for line in (
                "- Missing input: an input a Step's code will read, found in its task, in the files it changes or in the code those files call, that neither the Step's `reads` nor any domain of the criteria it proves names. Name the file and line or the sentence of the task.",
                "- Missing class: an input the code reads, at a line a domain cites or that you find by searching the code, with a class no domain lists, such as an absent field, an empty value, a renamed file, a subfolder or a truncated value; a class that the place defining the values tells apart, such as a schema, a parser or the reply of the program that produces them, that the domain leaves out; a criterion that says every, each, any, all, whole, always, never, whatever, however or whenever with no domain over some kind of thing the word ranges over; or a value whose size or count nothing bounds, with no class beyond every bound the behaviour sets. Name the file and line.",
                "- Stand-in: a domain over a value the code reads to learn another, with no class where the two differ.",
                "- Source: a domain whose `source` is not what produces its values. It is `outside` whenever a program, tool, system or service outside the repository produces them, even when the repository's code parses them; `person` when a person types, picks or says them; `stored` when the code reads them back from a file, database or other store it wrote earlier; `sent` when the repository's own code in another process, such as its client, a producer or another deployed version, sends them over a network, a queue, a pipe or another channel; and `repo` only otherwise. Also a `fact` or `defined_by` that does not show where the values are defined, asked for, written or sent, and classes that come from a description of the values rather than from where they are defined.",
                "- Give-way: a bound whose order of what gives way is missing or leaves a choice open; anything the criterion promises that `keeps` does not list, whether it sits in the order, is folded into a broader item there or is in neither list; or a kept item whose row does not make every item in the order give way.",
                "- Outside fact: a claim about software outside the repository that no recorded command and output shows, including one listed as an assumption or marked `assumed` although it could be run here.",
                "- Invalid input: an outside, person, stored or sent domain whose `invalid` classes leave out a way its input can arrive other than promised, such as missing, empty, malformed, of another type, cut short or written by an older version; or a behaviour that exists to refuse something and does not refuse on an invalid class, unless the user decided otherwise.",
                "- Open domain: a domain whose classes cannot all be listed, such as free text or shell commands, that the design still decides on, or a domain marked closed whose classes do not cover every value its input can take. Name a value that falls in no class, or in a class for every other value although it needs a different result. A domain kept open by `varies` for a behaviour that does not vary from run to run or that exists to refuse something counts, and so does one kept open by `open_by` in an autonomous run, or by a cited line that is not the user's own decision to keep this domain open. Report it even when the request names the mechanism that reads the input.",
        ):
            with self.subTest(line=line[:24]):
                self.assertIn(line + "\n", body)
        self.assertNotIn("that no recorded command and output shows and the spec does not list as an assumption.", body)
        self.assertNotIn("and the spec does not list as an assumption.", body)

    def test_spec_reviewer_writes_its_issues_in_a_json_block(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        self.assertIn(
            "Output a `Status:` line first. It reads `Approved` or `Issues found`." + "\n\n" + "Then end your reply with a fenced `json` block holding one object: `status`, as your Status line gives it, and `issues`, one object per issue, each with `category`, the category's name exactly as this list writes it, and `text`, which names the section or Step, the problem and why it matters. With no issue, `issues` is an empty list. Write no issue outside the block.",
            body,
        )
        self.assertNotIn("Then write one line per issue.", body)

    def test_spec_reviewer_scopes_a_follow_up_review(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        filing = "When an issue fits one of Missing input, Missing class, Stand-in, Source, Outside fact, Invalid input, Give-way or Open domain and another category too, file it under that input category. In an autonomous run, a decision made on the user's behalf never settles an issue under one of those eight categories."
        follow_up = "When you are given a diff file and the issues of the last review, this is a follow-up review. Check that the change fixes each of those issues, and review the changed lines and whatever in the spec, the items file or the record they contradict. Report an earlier issue the change does not fix and an issue in or caused by the changed lines, and nothing else."
        self.assertIn(filing + "\n\n" + follow_up + "\n\n", body)

    def test_spec_reviewer_files_input_gaps_under_input_categories(self):
        _, body = split_frontmatter(read_agent("agents/spec-reviewer.md"))
        filing = "When an issue fits one of Missing input, Missing class, Stand-in, Source, Outside fact, Invalid input, Give-way or Open domain and another category too, file it under that input category. In an autonomous run, a decision made on the user's behalf never settles an issue under one of those eight categories."
        self.assertIn(filing, body)
        self.assertLess(body.index("- Tracking talk:"), body.index(filing))
        self.assertLess(
            body.index(filing),
            body.index("In an autonomous run, what the product's context calls for in the requested work counts as asked for."),
        )


if __name__ == "__main__":
    unittest.main()
