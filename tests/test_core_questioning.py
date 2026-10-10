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

    def test_questioning_sorts_forks_as_intent_and_reuse_as_structure(self):
        lines = read_questioning().splitlines()
        body = section_body(lines, "## Sort every unknown")
        intent_line = next(line for line in body if line.strip().startswith("| Intent |"))
        self.assertIn("whether to share code at a fork", intent_line)
        structure_line = next(line for line in body if line.strip().startswith("| Structure |"))
        self.assertIn("which existing code already does the job", structure_line)

    def test_questioning_treats_factual_wording_as_structure(self):
        lines = read_questioning().splitlines()
        body = section_body(lines, "## Sort every unknown")
        cosmetic_line = next(line for line in body if line.strip().startswith("| Cosmetic |"))
        self.assertIn("wording that states nothing about how the product behaves", cosmetic_line)
        self.assertNotIn("exact wording", cosmetic_line)
        structure_line = next(line for line in body if line.strip().startswith("| Structure |"))
        self.assertIn("whether wording that states how the product behaves is true of it", structure_line)
        self.assertIn(
            "Wording that states how the product behaves is a fact, not a cosmetic choice.",
            "\n".join(body),
        )

    def test_questioning_stops_only_when_proven_where_it_counts(self):
        text = read_questioning()
        self.assertIn(
            "1. Every Must requirement has a way to tell pass from fail where passing counts, or is marked unproven with the reason.",
            text,
        )
        record = "\n".join(section_body(text.splitlines(), "## Record each answer"))
        self.assertIn("Update the record at the same time", record)

    def test_autonomous_runs_resolve_ambiguity_from_intent_and_context(self):
        lines = read_questioning().splitlines()
        self.assertIn("## Work autonomously", lines)
        body = "\n".join(section_body(lines, "## Work autonomously"))
        for phrase in (
            "When the user's instructions, in the conversation or in the project's written instructions, say to work autonomously, ask no question and seek no approval.",
            "Never guess and never fall back to the lightest option.",
            "Resolve each unknown from the user's intent and the project's context: who the product serves, what is at stake, and the domain.",
            "Research the established practice for that context",
            "`interphase:scout`",
            "Write the concrete, specific requirements that context calls for, without avoiding complexity or added services, so there is something specific to test.",
            "Record each as an assumption naming the intent and context that decided it.",
            "`Add file uploads`",
            "a size limit and a file-type check",
            "virus scanning, encryption at rest, an access audit log and a retention rule",
        ):
            self.assertIn(phrase, body)
        for held_out in ("payroll", "allotment", "sign-in", "sign in", "accounts"):
            self.assertNotIn(held_out, body.lower(), held_out)
        self.assertNotIn("add accounts", read_questioning().lower())

    def test_autonomous_runs_keep_what_the_context_calls_for(self):
        lines = read_questioning().splitlines()
        body = "\n".join(section_body(lines, "## Work autonomously"))
        for phrase in (
            "the standards for the capability itself, and the laws and standards that govern the domain and the data the product holds",
            "Make every requirement the context calls for a goal.",
            "Never cut one to keep Musts near 60 percent of the effort, and never record one as a non-goal, a Won't, an open question or work for a later spec.",
            "Non-goals hold only what the context does not call for.",
            "Treat what the project depends on, the data it holds and where it runs as the starting point, not a limit.",
            "a new dependency, a new stored field, an added service or a change to how it is deployed",
            "When something outside the code meets a requirement",
            "still write the requirement and its acceptance criterion, and mark the criterion unproven with the reason when the builder cannot check it.",
            "When a written rule of the project forbids what the context calls for, meet the requirement within the rule if the established practice allows it. Otherwise keep the requirement and record that it overrides the rule.",
            "the spec requires what lets it, never a non-goal.",
        ):
            self.assertIn(phrase, body)
        record = body.index("Record each as an assumption naming the intent and context that decided it.")
        self.assertLess(body.index("Write the concrete, specific requirements"), record)
        self.assertLess(record, body.index("Make every requirement the context calls for a goal."))
        scope = section_body(lines, "## Push back on scope")
        self.assertEqual(
            [line for line in scope if line.startswith("- ")][-1],
            "- In an autonomous run, push back only on what the project's context does not call for, following the section Work autonomously.",
        )

    def test_stopping_needs_no_read_back_in_the_brief_lane_or_autonomous_runs(self):
        body = section_body(read_questioning().splitlines(), "## Know when to stop")
        condition = "4. The user confirmed the read-back in phase 7."
        exemption = "In the brief lane and in an autonomous run, condition 4 holds without a read-back."
        self.assertIn(condition, body)
        self.assertIn(exemption, body)
        self.assertLess(body.index(condition), body.index(exemption))


if __name__ == "__main__":
    unittest.main()
