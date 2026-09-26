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

    def test_readme_names_another_tool_at_most_once(self):
        lines = read_readme().splitlines()
        naming = tuple(line for line in lines if "mitosis" in line.lower())
        self.assertLessEqual(len(naming), 1)
        headings = tuple(line for line in lines if line in SECTION_HEADINGS)
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


if __name__ == "__main__":
    unittest.main()
