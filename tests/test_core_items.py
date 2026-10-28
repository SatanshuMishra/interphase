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
    "role",
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
            "`seams`",
            "`criteria`",
            "`steps`",
            "`builder_runs`",
            "`unproven`",
            "scripts/check_record.py",
            "--complete",
            "scripts/render_record.py",
        ):
            self.assertIn(needle, record, needle)

    def test_record_lists_rounds(self):
        record = section(read_guide(), "## Interview record")
        rows = [line for line in record.splitlines() if line.startswith("| `rounds` |")]
        self.assertEqual(len(rows), 1)
        for word in ("kind", "questions", "changed"):
            self.assertIn(word, rows[0], word)
        self.assertIn("without rounds", record)

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
            "seams": "`name` (lowercase kebab-case, unique), `interface` (the public interface tests observe behaviour at), `catches` (what tests there catch), `misses` (what they miss), `builder_runs` (`true` when whoever builds a Step can run tests there)",
            "criteria": "`number` (such as `5.3`, starting with the number of the spec's Test seams section), `title`, `text`, `seam` (the name of the agreed seam its tests sit at), `acceptance` (its acceptance lines, each as `${CLAUDE_PLUGIN_ROOT}/contracts/k1-acceptance.schema.json` states it) for every criterion at a seam the builder runs, `tests` (each one row, with `file`, `name`, `given`, `expect`, `step`, `check` (the id of the acceptance line it implements) when the criterion has acceptance lines and, when the criterion has a case table, `covers`), `unproven` (the reason) only when no test the builder runs can prove it, `varies` (`input`, `output` or `measured`) only when the behaviour differs from run to run, and, only for security-sensitive or refusal behaviour, `case_table` (`security` or `refusal`) with `domains` (each with `name`, `over` and `classes`) for the inputs it reads; each test of a varying criterion also carries `cases`, `runs` (at least 2) and `pass_rate`",
            "steps": "`name` (never `check-author`, which the render script reserves), `files`, `criteria` (the numbers its tests prove), `task` once written, `amendment` (the number of the amendment that added it) only when an amendment added it, and any optional field of the items format except `source`, `acceptance`, `spec_ref` and `role`",
            "locked": "the repository-relative path of every test file a row of a criterion with acceptance lines names, as `${CLAUDE_PLUGIN_ROOT}/contracts/k2-locked.schema.json` states it; no Step lists a locked path in its `files`",
        }
        for key, cell in cells.items():
            with self.subTest(key=key):
                self.assertIn("| `" + key + "` | " + cell + " |", rows)

    def test_items_guide_documents_the_check_author_step(self):
        text = read_guide()
        items = section(text, "## Items format")
        self.assertIn("the only value `role` may take is `check-author`.", items)
        record = section(text, "## Interview record")
        self.assertIn("When the record has a `locked` list, it writes one more Step first: the check-author Step", record)
        designing = section(text, "## Designing Steps").splitlines()
        self.assertIn(
            "- Never design the check-author Step and never name a Step `check-author`. The render script writes it first from the record's `locked` list and puts it in every other Step's `after`, so the locked tests ship before anything is built and no later Step changes them.",
            designing,
        )
        self.assertIn(
            "- List in `files` every path the Step creates or changes, including its tests, except a locked path. A write outside `files` is reported as a fault.",
            designing,
        )

    def test_items_guide_explains_case_tables(self):
        paragraphs = section(read_guide(), "## Interview record").split("\n\n")
        starts = tuple(
            i for i, p in enumerate(paragraphs) if p.startswith("Give every criterion a test at a seam the builder runs")
        )
        self.assertEqual(len(starts), 1)
        self.assertEqual(
            paragraphs[starts[0] + 1],
            "In a case table, each domain lists the classes of one input that the code tells apart, and each test covers some of them, named `<domain>: <class>`. The record check reports a class no row covers, domains on a criterion with no `case_table`, and a `case_table` with no domains.",
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
