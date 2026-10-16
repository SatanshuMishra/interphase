import pathlib
import unittest

HEADINGS = (
    "## The hard bar",
    "## Intent round",
    "## Frontier rounds",
    "## Domain language",
    "## Test seams",
    "## Push back on scope",
    "## Record each answer",
    "## Know when to stop",
    "## After the interview",
    "## Unattended runs",
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


def section(heading):
    return "\n".join(section_body(read_questioning().splitlines(), heading))


class QuestioningTest(unittest.TestCase):
    def test_questioning_has_every_section_in_order(self):
        lines = read_questioning().splitlines()
        positions = tuple(lines.index(heading) if heading in lines else -1 for heading in HEADINGS)
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, tuple(sorted(positions)))
        for relative in STEP_FILES:
            text = (repo_root() / relative).read_text(encoding="utf-8")
            self.assertNotIn("mitosis", text.lower(), relative)

    def test_the_hard_bar_asks_only_what_cannot_be_read_and_changes_the_build(self):
        body = section("## The hard bar")
        for phrase in (
            "1. Nothing you can read answers it: not the request, the code, the docs, the project's written rules, `GLOSSARY.md`, the ADRs in `docs/adr/`, the decisions files of earlier specs, an answer already given, or a quick run.",
            "2. A different answer would change what gets built: a file, a test, an acceptance criterion or a Step.",
            "Facts are yours to find and decisions are the user's.",
            "Never ask the user to confirm something you read.",
            "A question that fails the bar is neither asked nor recorded as an assumption.",
        ):
            self.assertIn(phrase, body)

    def test_the_hard_bar_treats_factual_wording_as_a_fact_and_never_asks_cosmetics(self):
        body = section("## The hard bar")
        self.assertIn("Wording that states how the product behaves is a fact, not a cosmetic choice.", body)
        self.assertIn("Cosmetic choices, such as colour, spacing, icons and wording that states nothing about how the product behaves, are never asked", body)

    def test_the_intent_round_opens_and_is_written_as_numbered_intent_lines(self):
        body = section("## Intent round")
        for phrase in (
            "- Goal: what the change must achieve.",
            "- Why: why it is wanted now, and for whom.",
            "- Success: how the user will know it worked.",
            "so that \"yes\" accepts all three",
            "`- I1 Goal: <goal>`, `- I2 Why: <why>`, `- I3 Success: <success>`",
            "Every guess made after the interview cites one of these lines.",
        ):
            self.assertIn(phrase, body)

    def test_frontier_rounds_ask_every_settled_question_in_numbered_plain_text(self):
        body = section("## Frontier rounds")
        for phrase in (
            "The frontier is every decision whose prerequisites are settled",
            "Ask the whole frontier in one round. There is no cap on how many questions a round holds or how many rounds the interview takes.",
            "A question whose answer depends on another question still open in the same round belongs to a later round.",
            "ask the rest of the frontier now, and hold back only the questions downstream of it.",
            "Write each round as numbered plain text, never through the AskUserQuestion tool:",
            "Q1. <short title>:",
            "Recommended: <your answer>",
            "Word each question so that \"yes\" accepts the recommended answer.",
            "- The shape of the work: what ships together, what order matters and what could be thrown away.",
            "- The pre-mortem:",
        ):
            self.assertIn(phrase, body)

    def test_domain_language_challenges_terms_and_writes_the_glossary_at_once(self):
        body = section("## Domain language")
        self.assertIn("`${CLAUDE_PLUGIN_ROOT}/core/domain.md`", body)
        self.assertIn("The glossary defines X as A, but you seem to mean B. Which is it?", body)
        self.assertIn("When the user states how something works and the code disagrees, ask which is right.", body)
        self.assertIn("When a term is settled, write it to the glossary at once.", body)

    def test_seams_are_agreed_before_any_test_and_ideally_one(self):
        body = section("## Test seams")
        for phrase in (
            "Agree the seams before any acceptance criterion is written against them.",
            "the ideal number is one.",
            "one line on what it catches and one on what it misses",
            "Write no acceptance test at a seam the user has not agreed.",
        ):
            self.assertIn(phrase, body)

    def test_answers_go_to_the_decisions_section_and_the_record(self):
        body = section("## Record each answer")
        self.assertIn("Append each settled decision to the `## Decisions` section of the decisions file at once", body)
        self.assertIn("Never reword or delete an earlier line.", body)
        self.assertIn("Update the record at the same time: the seams, the criteria and the owning Steps.", body)

    def test_the_read_back_is_the_only_use_of_ask_user_question(self):
        body = section("## Know when to stop")
        self.assertIn("The interview ends when the frontier is empty", body)
        self.assertIn("the one place the AskUserQuestion tool is used", body)
        uses = [line for line in read_questioning().splitlines() if "AskUserQuestion" in line]
        self.assertEqual(len(uses), 2)

    def test_gaps_after_the_interview_are_guessed_from_the_intent_and_never_stop_the_run(self):
        body = section("## After the interview")
        for phrase in (
            "Once the user approves the read-back, ask nothing more and never stop for an answer.",
            "Take the reading the intent best supports",
            "ending `(relies on I<n>)`, naming the intent line it relied on",
            "Add the same line to the `assumptions` of every Step it shapes, so the pull request that builds the Step shows it.",
        ):
            self.assertIn(phrase, body)

    def test_unattended_runs_infer_the_intent_and_resolve_from_context(self):
        body = section("## Unattended runs")
        for phrase in (
            "When the user's instructions, in the conversation or in the project's written instructions, say to work autonomously, hold no interview: ask no question and seek no approval.",
            "Write the `## Intent` section from the request and the project's context, ending each line `(inferred)`.",
            "Never fall back to the lightest option.",
            "`interphase:scout`",
            "List the threats that practice expects for what is at stake in the requested work, and require a defence for each in the layers that practice uses at those stakes",
            "Never put one the context calls for in Out of scope.",
            "Treat what the project depends on, the data it holds and where it runs as the starting point, not a limit.",
            "a new dependency, a new stored field, an added service or a change to how it is deployed",
            "marked unproven with the reason when the builder cannot check it",
            "record the override as `${CLAUDE_PLUGIN_ROOT}/core/practices.md` says.",
            "`Add file uploads`",
            "a size limit and a file-type check",
            "virus scanning, encryption at rest, an access audit log and a retention rule",
            "A run that starts unattended stays unattended",
        ):
            self.assertIn(phrase, body)
        for held_out in ("payroll", "allotment", "sign-in", "sign in", "accounts"):
            self.assertNotIn(held_out, body.lower(), held_out)


if __name__ == "__main__":
    unittest.main()
