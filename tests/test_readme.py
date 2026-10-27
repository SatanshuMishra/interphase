import pathlib
import unittest

ITEMS_FIELDS = (
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

OUTPUT_FILES = (
    "<slug>.md",
    "<slug>.decisions.md",
    "<slug>.items.json",
    "<slug>.repro",
    "<slug>.record.json",
)

SECTION_HEADINGS = (
    "## What it does",
    "## Install",
    "## Use",
    "## What it never does",
    "## What it produces",
    "## What it records",
    "## Check the output yourself",
    "## Requirements",
    "## Tests",
    "## License",
)


def read_readme():
    root = pathlib.Path(__file__).resolve().parents[1]
    return (root / "README.md").read_text(encoding="utf-8")


class ReadmeTest(unittest.TestCase):
    def test_readme_documents_every_items_field(self):
        text = read_readme()
        missing = tuple(field for field in ITEMS_FIELDS if "`" + field + "`" not in text)
        self.assertEqual(missing, ())

    def test_readme_names_every_output_file(self):
        text = read_readme()
        missing = tuple(name for name in OUTPUT_FILES if name not in text)
        self.assertEqual(missing, ())

    def test_readme_documents_the_record(self):
        text = read_readme()
        self.assertIn("scripts/check_record.py", text)
        self.assertIn("scripts/render_record.py", text)
        self.assertIn("marked unproven", text)
        self.assertNotIn("only when nothing can be tested", text)

    def test_readme_names_another_tool_at_most_once(self):
        lines = read_readme().splitlines()
        naming = tuple(line for line in lines if "mitosis" in line.lower())
        self.assertLessEqual(len(naming), 1)

    def test_readme_has_exactly_the_expected_sections(self):
        headings = tuple(line for line in read_readme().splitlines() if line.startswith("## "))
        self.assertEqual(headings, SECTION_HEADINGS)

    def test_readme_never_advises_ignoring_specs(self):
        text = read_readme().lower()
        self.assertNotIn("gitignore", text)
        self.assertNotIn("info/exclude", text)
        self.assertNotIn("keep specs out of git", text)

    def test_readme_describes_steps_designed_in_the_interview(self):
        text = read_readme()
        self.assertIn("interphase designs the Steps with you during the interview", text)
        self.assertIn("each can be used without the other", text)

    def test_readme_states_the_tracking_rule_and_cache_removal(self):
        text = read_readme()
        self.assertIn(
            "It never comments on, asks about or offers to change whether you track its output files in git.",
            text,
        )
        self.assertIn("removes the ones its run created", text)

    def test_readme_describes_compaction_recovery(self):
        lines = read_readme().splitlines()
        start = lines.index("## Use")
        end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
        section = "\n".join(lines[start:end])
        self.assertIn(
            "If the conversation is compacted or cleared during a run, a hook puts the run's decisions and a summary of its record back into the conversation",
            section,
        )
        self.assertIn(
            "each pathway tells Claude to re-read the record, the decisions and the phases before going on",
            section,
        )

    def test_readme_documents_varying_behaviour(self):
        text = read_readme()
        self.assertIn("behaviour that varies from run to run", text)
        self.assertIn("a population", text)
        self.assertIn("held-out set", text)
        self.assertIn("pass rate", text)
        for key in ("varies", "cases", "runs", "pass_rate"):
            self.assertIn("`" + key + "`", text)
        self.assertIn("Runs cell", text)

    def test_readme_states_the_programming_guarantee(self):
        text = read_readme()
        self.assertIn(
            "It never plans a copy of logic that already exists, and never bends existing code to fit a new use.",
            text,
        )
        self.assertIn("Reuse and change", text)
        self.assertIn("core/practices.md", text)

    def test_readme_documents_the_brief_lane_and_autonomy(self):
        text = read_readme()
        lines = text.splitlines()

        def section(heading):
            start = lines.index(heading)
            end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
            return "\n".join(lines[start:end])

        does = section("## What it does")
        self.assertIn("brief lane", does)
        self.assertIn("all six conditions hold", does)
        self.assertIn("one Step per item", does)
        self.assertIn("one short read-back to approve and no reviewer agent", does)
        self.assertIn("switches to the full pathway", does)
        use = section("## Use")
        self.assertIn("work autonomously", use)
        self.assertIn("it holds no interview", use)
        self.assertIn("resolves each ambiguity from that intent and the usual practice for that context", use)
        self.assertIn("names the intent line it relied on", use)
        self.assertIn("numbered plain-text rounds", use)
        self.assertIn("The only multiple-choice prompt is the last one", use)
        self.assertIn("records every choice as an assumption", use)
        self.assertIn("top risks", use)
        self.assertIn("first any that override an earlier decision", use)
        self.assertIn("never trims what the context calls for", use)
        self.assertIn("a decision record or one of your project's written rules", use)
        produces = section("## What it produces")
        self.assertIn("core/templates/spec-brief.md", produces)
        self.assertIn("5.x", produces)

    def test_readme_describes_the_interview_glossary_and_slim_spec(self):
        text = read_readme()
        for phrase in (
            "It opens with your intent (the goal, why you want it, and what success looks like)",
            "It asks only what the code, the docs and your earlier decisions cannot answer, and only when a different answer would change what gets built.",
            "any gap it finds later is filled with a reasoned guess from your recorded intent, listed as an assumption.",
            "Every spec has the same six sections: the problem, your intent, user stories (for a bug, the reproduction and cause; for a brief, the evidence), the decisions, the agreed test seams with the acceptance tests at each, and what is out of scope.",
            "Only behaviour that is security-sensitive or exists to refuse something gets a full table of input cases.",
            "`GLOSSARY.md`",
            "`docs/adr/`",
            "A spec is disposable once its change merges",
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("Review bar", text)
        headings = tuple(line for line in text.splitlines() if line.startswith("## "))
        self.assertEqual(headings, SECTION_HEADINGS)

    def test_readme_documents_the_project_pathway(self):
        text = read_readme()
        lines = text.splitlines()

        def section(heading):
            start = lines.index(heading)
            end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
            return "\n".join(lines[start:end])

        does = section("## What it does")
        self.assertIn("one of four pathways", does)
        self.assertIn("**Project**", does)
        self.assertIn("a new repository, or a new stack, build, CI or release for an existing one", does)
        self.assertIn("walking skeleton", does)
        self.assertIn("/interphase:project", section("## Use"))
        self.assertIn("spec-project.md", section("## Check the output yourself"))


    def test_readme_describes_what_it_records(self):
        text = read_readme()
        lines = text.splitlines()

        def section(heading):
            start = lines.index(heading)
            end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
            return "\n".join(lines[start:end])

        headings = tuple(line for line in lines if line.startswith("## "))
        self.assertEqual(
            headings.index("## What it records"),
            headings.index("## What it produces") + 1,
        )
        records = section("## What it records")
        for phrase in (
            "~/.plugin-metrics",
            "PLUGIN_METRICS_DIR",
            "PLUGIN_METRICS_PARENT",
            "catalogue",
            "run summary",
            "rounds",
            "interphase:metrics",
            "DuckDB",
        ):
            self.assertIn(phrase, records)
        record_rows = tuple(
            line for line in section("## What it produces").splitlines() if line.startswith("| `<slug>.record.json`")
        )
        self.assertEqual(len(record_rows), 1)
        self.assertIn("rounds", record_rows[0])
        self.assertIn("DuckDB", section("## Requirements"))

    def check_output_section(self):
        lines = read_readme().splitlines()
        start = lines.index("## Check the output yourself") + 1
        rest = lines[start:]
        end = next((i for i, line in enumerate(rest) if line.startswith("## ")), len(rest))
        return "\n".join(rest[:end])

    def test_readme_puts_population_in_the_table(self):
        section = self.check_output_section()
        self.assertIn(
            "A criterion marked `varies` (input, output or measured) must give each of its tests `cases`, `runs` (at least 2) and `pass_rate`. The render script writes them into the row's Runs cell.",
            section.split("\n\n"),
        )
        self.assertNotIn("Population line", section)

    def test_readme_explains_case_tables(self):
        paragraphs = self.check_output_section().split("\n\n")
        starts = tuple(i for i, p in enumerate(paragraphs) if p.startswith("A criterion marked `varies`"))
        self.assertEqual(len(starts), 1)
        self.assertEqual(
            paragraphs[starts[0] + 1],
            "A criterion for security-sensitive behaviour, or for behaviour that exists to refuse something, is a case table: its `case_table` is `security` or `refusal`, its `domains` list the classes of each input the code tells apart, and each of its tests is one row with `given`, `expect` and the classes it `covers`. Any other criterion is a few rows with no domains. The checker reports a class no row covers, domains on a criterion with no `case_table`, and a `case_table` with no domains.",
        )

    def test_readme_explains_the_intent_checks(self):
        paragraphs = self.check_output_section().split("\n\n")
        matching = tuple(p for p in paragraphs if p.startswith("Use `spec-bug.md`, `spec-prototype.md` or `spec-project.md`"))
        self.assertEqual(len(matching), 1)
        self.assertTrue(
            matching[0].endswith(
                "an Intent section with no `- I1` line, and an assumption that cites no intent line or one the Intent section does not have."
            )
        )

    def test_readme_explains_amendments(self):
        paragraphs = self.check_output_section().split("\n\n")
        starts = tuple(i for i, p in enumerate(paragraphs) if p.startswith("It refuses a record that the checker rejects"))
        self.assertEqual(len(starts), 1)
        self.assertEqual(
            paragraphs[starts[0] + 1],
            "To amend a handed-off spec, ask interphase to add the missed case to it by name. It adds rows and a new Step with `amendment` set, and renders that Step alone with `--amendment <n> --items docs/specs/<slug>.amend-<n>.items.json`. Check that file with `check_items.py --amendment`.",
        )


if __name__ == "__main__":
    unittest.main()
