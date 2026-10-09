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
        self.assertIn("Population line", text)

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
        self.assertIn("no read-back and no reviewer agent", does)
        self.assertIn("switches to the full pathway", does)
        use = section("## Use")
        self.assertIn("work autonomously", use)
        self.assertIn("resolves each ambiguity from your intent and your project's context", use)
        self.assertIn("records every choice as an assumption", use)
        self.assertIn("top risks", use)
        self.assertIn("first any that override an earlier decision", use)
        produces = section("## What it produces")
        self.assertIn("core/templates/spec-brief.md", produces)
        self.assertIn("4.x", produces)

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


if __name__ == "__main__":
    unittest.main()
