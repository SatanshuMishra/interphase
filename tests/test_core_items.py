import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

HEADINGS = (
    "## Output files",
    "## Interview record",
    "## Items format",
    "## Designing Steps",
    "## Writing a task",
    "## Checking the result",
)

FIELDS = (
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

STEP_FILES = ("core/items.md",)


def read_guide():
    return (ROOT / "core" / "items.md").read_text(encoding="utf-8")


def section(text, heading):
    lines = text.splitlines()
    start = lines.index(heading) + 1
    rest = lines[start:]
    end = next((i for i, line in enumerate(rest) if line.startswith("## ")), len(rest))
    return "\n".join(rest[:end])


class CoreItemsTest(unittest.TestCase):
    def test_items_guide_has_every_section_in_order(self):
        lines = read_guide().splitlines()
        positions = tuple(lines.index(h) if h in lines else -1 for h in HEADINGS)
        for heading, position in zip(HEADINGS, positions):
            self.assertNotEqual(position, -1, heading)
        self.assertEqual(list(positions), sorted(positions))
        for relative in STEP_FILES:
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("mitosis", content.lower(), relative)

    def test_items_guide_documents_every_field(self):
        text = read_guide()
        for field in FIELDS:
            self.assertIn("`" + field + "`", text, field)
        items = section(text, "## Items format")
        self.assertRegex(items, re.compile(r"only value[^.\n]*`type`[^.\n]*`contract`|`type`[^\n]*only the value `contract`"))

    def test_items_guide_designs_steps_during_the_interview(self):
        text = read_guide()
        designing = section(text, "## Designing Steps")
        self.assertIn("Design the Steps during the interview", designing)
        self.assertIn("Never derive them by reading the finished spec.", designing)

    def test_items_guide_has_no_size_cap_or_ignore_rule(self):
        text = read_guide()
        for forbidden in ("400", "gitignore", "Work breakdown"):
            self.assertNotIn(forbidden, text, forbidden)

    def test_items_guide_keeps_tasks_independent_of_the_spec(self):
        text = read_guide()
        writing = section(text, "## Writing a task")
        self.assertIn("Never send the builder to the spec", writing)
        output = section(text, "## Output files")
        self.assertIn("Each must be usable without the other.", output)

    def test_items_guide_shares_logic_between_steps(self):
        text = read_guide()
        designing = section(text, "## Designing Steps")
        self.assertIn("Give logic that two Steps need to one Step, and make the others come after it.", designing)
        self.assertIn("Never keep Steps' files apart by copying logic.", designing)
        writing = section(text, "## Writing a task")
        self.assertIn(
            "Carry into the task every Reuse and change line the Step touches: what to reuse as is and never copy, what to keep separate, and which existing code to change.",
            writing,
        )

    def test_items_guide_documents_the_record(self):
        text = read_guide()
        self.assertIn("`<slug>.record.json`", section(text, "## Output files"))
        record = section(text, "## Interview record")
        for needle in (
            "`environments`",
            "`facts`",
            "`criteria`",
            "`steps`",
            "`builder_runs`",
            "`command`",
            "`unproven`",
            "scripts/check_record.py",
            "--complete",
            "scripts/render_record.py",
        ):
            self.assertIn(needle, record, needle)

    def test_items_guide_documents_the_run_status(self):
        record = section(read_guide(), "## Interview record")
        self.assertIn("and a `status`:", record)
        self.assertIn("`status` is `in-progress` from phase 1 and `handed-off` once phase 10 finishes.", record)
        self.assertIn(
            "A record without `status` predates the field: the hook treats it as finished, and `check_record.py` reports it.",
            record,
        )

    def test_items_guide_documents_varying_criteria(self):
        text = read_guide()
        record = section(text, "## Interview record")
        for needle in ("`varies`", "`input`", "`output`", "`measured`", "`cases`", "`runs`", "`pass_rate`"):
            self.assertIn(needle, record, needle)
        items = section(text, "## Items format")
        self.assertIn("The items file's fields do not change", items)

    def test_items_guide_allows_empty_acceptance_only_when_unproven(self):
        items = section(read_guide(), "## Items format")
        self.assertIn("only when every criterion the Step claims is marked unproven", items)
        self.assertNotIn("only when nothing can be tested", items)

    def test_small_requests_get_one_step_per_item(self):
        designing = section(read_guide(), "## Designing Steps").splitlines()
        self.assertIn("- Give a small request one Step per item.", designing)
        self.assertNotIn("- Give a small request one Step.", designing)


    def test_record_table_names_the_new_keys(self):
        rows = section(read_guide(), "## Interview record").splitlines()
        cells = {
            "facts": "`id` (unique), `fact`, and one citation: `path` (repository-relative), `line` (from 1) and `quote` (text that appears in that line); or `url`; or `command` and `output` (what was run and what it showed); a fact about software outside the repository also carries `outside: true` and is cited by `command` and `output`",
            "criteria": "`number` (such as `7.3`, starting with the number of the spec's Acceptance criteria section), `title`, `text`, `where` (the environments where passing proves it), `tests` (each one row, with `file`, `name`, `given`, `expect`, `env`, `step` and, when the criterion has `domains` or `gives_way`, `covers`), `domains` (each with `name`, `over`, `classes` and, when existing code reads the input, `fact`) for the inputs the behaviour reads, `gives_way` (what gives way first to last when a bound is reached), `facts` (the ids of the facts it rests on), `unproven` (the reason) only when no test the builder runs can prove it where it counts, and `varies` (`input`, `output` or `measured`) only when the behaviour differs from run to run; each test of a varying criterion also carries `cases`, `runs` (at least 2) and `pass_rate`",
            "steps": "`name`, `files`, `criteria` (the numbers its tests prove), `task` once written, `amendment` (the number of the amendment that added it) only when an amendment added it, and any optional field of the items format except `source`, `acceptance` and `spec_ref`",
        }
        for key, cell in cells.items():
            with self.subTest(key=key):
                self.assertIn("| `" + key + "` | " + cell + " |", rows)

    def test_items_guide_explains_case_tables(self):
        paragraphs = section(read_guide(), "## Interview record").split("\n\n")
        starts = tuple(
            i for i, p in enumerate(paragraphs) if p.startswith("Give every criterion a test the builder runs")
        )
        self.assertEqual(len(starts), 1)
        self.assertEqual(
            paragraphs[starts[0] + 1],
            "A criterion is a case table. Each domain lists the classes of one input that the code tells apart and, when existing code reads the input, cites the fact that shows where. Each test is one row: `given` says the input, `expect` says the result, and `covers` names what the row covers, as `<domain>: <class>` or `gives-way: <item>`. The record check reports a class or give-way item no row covers, a criterion that says every, each, any, all, whole, always, never, whatever, however or whenever with no domain, and a bound with no `gives_way`.",
        )

    def test_task_rows_are_written_literally(self):
        writing = section(read_guide(), "## Writing a task")
        self.assertIn(
            "The render script adds each acceptance test by file and name with what it is given and what it expects, and every acceptance criterion the Step proves, word for word, after the task you write.",
            writing,
        )
        self.assertIn(
            "Tell the builder to write every row into its test file literally, as the task gives it, and never to compute the rows from the code under test.",
            writing,
        )
        self.assertNotIn("with what it asserts", writing)

    def test_amendment_items_are_checked_with_the_option(self):
        checking = section(read_guide(), "## Checking the result")
        self.assertIn(
            "Check an amendment items file with `python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py\" --amendment docs/specs/<slug>.amend-<n>.items.json`; it then does not report the criteria the amendment does not claim.",
            checking,
        )


if __name__ == "__main__":
    unittest.main()
