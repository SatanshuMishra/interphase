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
    "## Check the output yourself",
    "## Requirements",
    "## Tests and evals",
    "## License",
)

BRIEF_SENTENCE = "with no read-back; the spec reviewer still checks it, and it hands off only after a review that reports no input issue."
TOP_RISKS_SENTENCE = "At hand-off it lists as top risks every criterion it could not prove, then every fact about outside software it could not run, then its own decisions: first any that override an earlier decision, one of your project's written rules or conventions or your request's own wording, then the rest."
RECORD_USAGE = "python3 /path/to/interphase/scripts/check_record.py [--complete | --digest] docs/specs/<slug>.record.json"
DIGEST_PARAGRAPH = "`--digest` prints the digest of the record and of the spec beside it that a spec review records in `reviews`. A record written by an earlier interphase fails this checker until it is amended: it lacks the fields below, and once handed off it holds no review."
EXIT_CODES = "and `2` for a usage error or a file it cannot read, and, for `check_record.py --digest`, a record it cannot parse or digest or one with no spec beside it."
WORKING_FILES_ROW = "| `<slug>.review-copy.md`, `<slug>.review-copy.json`, `<slug>.review-diff.txt` | Working files for the spec review: the spec and the record as the last review read them, and what changed since. They are deleted when the run ends. |"
CASE_TABLE_PARAGRAPH = "Each acceptance criterion is a case table. A criterion's `domains` list the classes of each input the code tells apart, each with its `source` (`repo`, `outside`, `person`, `stored` or `sent`), whether it is `closed`, and for an outside, person, stored or sent domain its `invalid` classes; its `gives_way` lists what gives way first to last when a bound is reached and its `keeps` what never gives way; and each of its tests is one row with `given`, `expect` and the classes it `covers`. Each Step lists in `reads` the domains of the inputs its code reads, and the record keeps each spec review in `reviews`, with the digest of the record it read. The checker reports a class, give-way item or kept item no row covers, a kept item with no row that also covers every give-way item, a criterion that says every, each, any, all, whole, always, never, whatever, however or whenever with no domain, a bound with no `gives_way` or no `keeps`, a domain with no `source` or `closed`, an outside domain with no fact marked outside, an outside, person, stored or sent domain with no `invalid` class, an open domain in a criterion that does not vary from run to run unless the user's recorded decision keeps it open, a Step with no `reads`, a fact marked `outside` that is cited neither by a command and its output nor by `assumed`, and a handed-off record whose last review read an earlier version of it or of its spec, or that a review of them as they stand found an input issue in."


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
        self.assertIn("Runs in cell", text)

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
        self.assertIn("one approval of the written brief", does)
        self.assertIn(BRIEF_SENTENCE, does)
        self.assertIn("switches to the full pathway", does)
        use = section("## Use")
        self.assertIn("work autonomously", use)
        self.assertIn("resolves each ambiguity from your intent and your project's context", use)
        self.assertIn("records every choice as an assumption", use)
        self.assertIn("top risks", use)
        self.assertIn("first any that override an earlier decision", use)
        self.assertIn("never trims what the context calls for", use)
        self.assertIn("one of your project's written rules or conventions or your request's own wording", use)
        produces = section("## What it produces")
        self.assertIn("core/templates/spec-brief.md", produces)
        self.assertIn("4.x", produces)

    def test_readme_names_the_review_bar(self):
        text = read_readme()
        paragraph = next(
            block for block in text.split("\n\n") if "Reuse and change" in block and "Review bar" in block
        )
        for phrase in ("Review bar", "threats", "block", "out of scope"):
            self.assertIn(phrase, paragraph)
        self.assertNotIn("ends each spec with a short Reuse and change section", text)
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


    def check_output_section(self):
        lines = read_readme().splitlines()
        start = lines.index("## Check the output yourself") + 1
        rest = lines[start:]
        end = next((i for i, line in enumerate(rest) if line.startswith("## ")), len(rest))
        return "\n".join(rest[:end])

    def test_readme_puts_population_in_the_table(self):
        section = self.check_output_section()
        self.assertIn(
            "A criterion marked `varies` (input, output or measured) must give each of its tests `cases`, `runs` (at least 2) and `pass_rate`. The render script writes them into the row's Runs in cell.",
            section.split("\n\n"),
        )
        self.assertNotIn("Population line", section)

    def test_readme_explains_case_tables(self):
        paragraphs = self.check_output_section().split("\n\n")
        starts = tuple(i for i, p in enumerate(paragraphs) if p.startswith("A criterion marked `varies`"))
        self.assertEqual(len(starts), 1)
        self.assertEqual(
            paragraphs[starts[0] + 1],
            CASE_TABLE_PARAGRAPH,
        )

    def test_readme_explains_citations(self):
        paragraphs = self.check_output_section().split("\n\n")
        matching = tuple(p for p in paragraphs if p.startswith("Use `spec-bug.md`, `spec-prototype.md` or `spec-project.md`"))
        self.assertEqual(len(matching), 1)
        self.assertTrue(
            matching[0].endswith(
                "The spec checker also reports a line of Requirements, Edge cases, Expected or Unchanged that cites no acceptance criterion, or cites one the spec does not have."
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


    def test_readme_describes_the_input_fields(self):
        text = read_readme()
        lines = text.splitlines()
        self.assertIn(BRIEF_SENTENCE, text)
        self.assertNotIn("no read-back and no reviewer agent", text)
        self.assertIn(TOP_RISKS_SENTENCE, text)
        self.assertIn(RECORD_USAGE, lines)
        self.assertIn(EXIT_CODES, text)
        guard = lines.index("| `<slug>.guard.json` | A working file for the guard. It is deleted when the run ends. |")
        self.assertEqual(lines[guard + 1], WORKING_FILES_ROW)
        paragraphs = self.check_output_section().split("\n\n")
        checker = tuple(
            i for i, p in enumerate(paragraphs) if p.startswith("This checker confirms that every cited quote appears in its line")
        )
        self.assertEqual(len(checker), 1)
        self.assertEqual(paragraphs[checker[0] + 1], DIGEST_PARAGRAPH)
        self.assertIn(CASE_TABLE_PARAGRAPH, paragraphs)


if __name__ == "__main__":
    unittest.main()
