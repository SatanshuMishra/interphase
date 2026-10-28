import contextlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BRIEF = ROOT / "core" / "brief.md"
TEMPLATE = ROOT / "core" / "templates" / "spec-brief.md"

HEADINGS = (
    "## When",
    "## Choose and record",
    "## Switch",
    "## What changes",
)
CONDITIONS = (
    (
        "each item is one behaviour in one sentence",
        "the user asked for or that was already observed",
        "reproduced defect",
        "live-check finding",
    ),
    (
        "follows patterns the code already has",
        "no new module, dependency, interface between parts, stored-data or sync format, build or release change",
    ),
    (
        "no design choice between real alternatives",
        "no reuse fork",
        "`${claude_plugin_root}/core/practices.md`",
    ),
    (
        "every acceptance test sits at a seam the builder runs",
        "nothing is marked unproven",
    ),
    (
        "nothing it touches varies from run to run",
        "`${claude_plugin_root}/core/variation.md`",
    ),
    (
        "for a bug",
        "the cause is confirmed by reproduction",
    ),
)
OPENING = ("# {{title}}", "Pathway: {{pathway}}.", "Lane: brief.", "Date: {{date}}.")
SECTIONS = (
    "## 1. Problem",
    "## 2. Intent",
    "## 3. Evidence",
    "## 4. Decisions",
    "## 5. Test seams",
    "## 6. Out of scope",
)
CHANGE = (
    "Current: WHEN the stock report is shown THEN the system lists each product with no total row.\n"
    "Expected: WHEN the stock report is shown THE SYSTEM SHALL end it with a row holding the sum of all quantities.\n"
    "Unchanged: WHEN a product row is shown THE SYSTEM SHALL CONTINUE TO show its name and quantity.\n\n"
    "Current: WHEN the low-stock list is shown THEN the system lists products in the order they were added.\n"
    "Expected: WHEN the low-stock list is shown THE SYSTEM SHALL list products by name from A to Z.\n"
    "Unchanged: WHEN the low-stock list is shown THE SYSTEM SHALL CONTINUE TO list only products below their "
    "reorder level.\n\n"
)
FILLED_BRIEF = (
    "# Stock report total and low-stock order\n\n"
    "Pathway: feature.\n\n"
    "Lane: brief.\n\n"
    "Date: 2026-10-09.\n\n"
    "## 1. Problem\n\n"
    "Add a total row to the stock report, and list low-stock products by name as the stock report does.\n\n"
    + CHANGE
    + "## 2. Intent\n\n"
    "- I1 Goal: the stock report shows the total quantity and the low-stock list reads alphabetically (inferred).\n"
    "- I2 Why: the shop owner checks stock totals by hand today (inferred).\n"
    "- I3 Success: the report's last row holds the sum and low-stock products appear A to Z (inferred).\n\n"
    "## 3. Evidence\n\n"
    "src/report.py line 4 sorts the stock report rows by name; the low-stock list at line 9 follows the same "
    "row pattern without the sort.\n\n"
    "## 4. Decisions\n\n"
    "### Reuse and change\n\n"
    "Reused as is:\n\n- src/report.py stock_rows: the name sort the low-stock list follows.\n\n"
    "Kept separate:\n\n- None.\n\n"
    "Changed:\n\n- src/report.py: adds the total row and sorts the low-stock list.\n\n"
    "### Assumptions\n\n"
    "- The total counts products with zero stock, because the owner wants the full stock count (relies on I1).\n\n"
    "## 5. Test seams\n\n"
    "{{written by the render script from the record}}\n\n"
    "## 6. Out of scope\n\n"
    "The Unchanged statements, and any change to how a product row looks.\n"
)
TOTAL_ROW = "### 5.1 The stock report ends with a total row"
LOW_STOCK_ORDER = "### 5.2 The low-stock list is sorted by name"


def load(relative):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    return path.read_text(encoding="utf-8")


def section(text, heading):
    lines = text.splitlines()
    start = lines.index(heading) + 1
    rest = lines[start:]
    end = next((i for i, line in enumerate(rest) if line.startswith("## ")), len(rest))
    return "\n".join(rest[:end])


def bullet(text, prefix):
    return next((line for line in text.splitlines() if line.startswith(prefix)), "")


def conditions(text):
    return tuple(
        line.lower()
        for line in section(text, "## When").splitlines()
        if line[:1].isdigit() and ". " in line[:4]
    )


def report_test(name, step, given, expect, check):
    return {
        "file": "tests/test_report.py",
        "name": name,
        "given": given,
        "expect": expect,
        "step": step,
        "check": check,
    }


def report_line(line_id):
    return {
        "id": line_id,
        "kind": "exact",
        "surface": {"family": "cli", "target": "python3"},
        "command": "python3 -m unittest tests.test_report",
        "pass": "the tests pass",
    }


def criterion(number, title, text, tests, **extra):
    line_id = "C%s.1" % number.partition(".")[2]
    return {
        "number": number,
        "title": title,
        "text": text,
        "seam": "report",
        "acceptance": [report_line(line_id)],
        "tests": list(tests),
        **extra,
    }


def report_probe(line_id):
    return {"check": line_id, "probe": "command", "target": "python3", "status": "pass", "detail": "/usr/bin/python3"}


def brief_record():
    return {
        "status": "in-progress",
        "seams": [
            {
                "name": "report",
                "interface": "the rows report.render returns",
                "catches": "wrong totals and wrong order",
                "misses": "how the rows are printed",
                "builder_runs": True,
            }
        ],
        "criteria": [
            criterion(
                "5.1",
                "The stock report ends with a total row",
                "WHEN the stock report is shown THE SYSTEM SHALL end it with a row holding the sum of all quantities.",
                (
                    report_test(
                        "test_total_row",
                        "total-row",
                        "products with quantities 2 and 3",
                        "the last row holds 5",
                        "C1.1",
                    ),
                    report_test(
                        "test_total_row_without_products",
                        "total-row",
                        "no products",
                        "the last row holds 0",
                        "C1.1",
                    ),
                ),
            ),
            criterion(
                "5.2",
                "The low-stock list is sorted by name",
                "WHEN the low-stock list is shown THE SYSTEM SHALL list products by name from A to Z.",
                (
                    report_test(
                        "test_low_stock_order",
                        "low-stock-order",
                        "low-stock products Pears then Apples",
                        "Apples is listed before Pears",
                        "C2.1",
                    ),
                ),
            ),
        ],
        "steps": [
            {
                "name": "total-row",
                "files": ["src/report.py"],
                "criteria": ["5.1"],
                "task": "End the stock report with a row holding the sum of all quantities.",
            },
            {
                "name": "low-stock-order",
                "files": ["src/report.py"],
                "criteria": ["5.2"],
                "task": "Sort the low-stock list by product name, as stock_rows sorts the stock report.",
                "after": ["total-row"],
            },
        ],
        "locked": ["tests/test_report.py"],
        "probes": [report_probe("C1.1"), report_probe("C2.1")],
        "outcomes": {"store": "/var/empty/trajectories.jsonl", "entries": 0, "repeated": []},
    }


class CoreBriefTest(unittest.TestCase):
    def test_brief_lists_the_six_conditions(self):
        text = read(BRIEF)
        lines = text.splitlines()
        self.assertEqual(lines[0], "# Brief lane")
        positions = tuple(lines.index(h) if h in lines else -1 for h in HEADINGS)
        self.assertNotIn(-1, positions)
        self.assertEqual(list(positions), sorted(positions))
        self.assertIn(
            "a small request takes the brief lane only when all six hold after grounding",
            section(text, "## When").lower(),
        )
        listed = conditions(text)
        self.assertEqual(len(listed), len(CONDITIONS), listed)
        for line, needles in zip(listed, CONDITIONS):
            for needle in needles:
                self.assertIn(needle, line, needle)
        self.assertTrue(listed[4].startswith("5. "), listed[4])

    def test_brief_switches_to_the_full_pathway_and_keeps_the_record(self):
        text = read(BRIEF)
        self.assertIn("all six hold after grounding", section(text, "## When"))
        choose = section(text, "## Choose and record")
        for needle in (
            "Check the six conditions at the end of Phase 3.",
            "Say the lane in one sentence, which the user may override.",
            "Write `- Lane: brief.` to the decisions file.",
        ):
            self.assertIn(needle, choose, needle)
        switch = section(text, "## Switch")
        for needle in (
            "When any condition breaks later, switch to the full pathway.",
            "Say so in one sentence",
            "Write `- Lane: full, replacing the brief lane.` to the decisions file.",
            "Keep the record and the decisions. Criteria keep their numbers: every template numbers them 5.x.",
            "Continue with the full phases and the pathway's own template.",
            "an unattended run stays unattended.",
        ):
            self.assertIn(needle, switch, needle)

    def test_brief_reads_back_once_and_runs_the_checkers_without_a_reviewer(self):
        text = read(BRIEF)
        changes = section(text, "## What changes")
        self.assertIn("Every other phase and rule applies unchanged.", changes)
        expected = (
            ("- Phase 4:", ("ask the intent round", "only for a question that passes the hard bar", "the one seam")),
            ("- Phase 5:", ("skip the pre-mortem", "The Unchanged statements are the Out of scope section.")),
            (
                "- Phase 6:",
                (
                    "one Step per item",
                    '/scripts/surface_probe.py" --record docs/specs/<slug>.record.json --repo .`',
                    "with `--unattended` in an unattended run, before the complete check",
                ),
            ),
            (
                "- Phase 7:",
                ("read back only the intent", "as a question, each failed probe that blocks", "ask for the one approval"),
            ),
            (
                "- Phase 8:",
                ("copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-brief.md` instead of the pathway template",),
            ),
            (
                "- Phase 9:",
                (
                    '/scripts/check_spec.py" --template "${CLAUDE_PLUGIN_ROOT}/core/templates/spec-brief.md"',
                    '/scripts/check_record.py" --complete docs/specs/<slug>.record.json',
                    '/scripts/check_items.py" docs/specs/<slug>.items.json',
                    "Do not dispatch the `interphase:spec-reviewer` agent.",
                ),
            ),
        )
        for prefix, needles in expected:
            line = bullet(changes, prefix)
            self.assertTrue(line, prefix)
            for needle in needles:
                self.assertIn(needle, line, needle)
        self.assertNotIn("approval", bullet(changes, "- Phase 9:"))
        self.assertIn("An unattended run in the brief lane asks no intent round and holds no read-back", changes)

    def test_brief_template_has_its_sections(self):
        lines = read(TEMPLATE).splitlines()
        filled = tuple(line for line in lines if line.strip())
        self.assertEqual(filled[: len(OPENING)], OPENING)
        numbered = tuple(line for line in lines if line.startswith("## "))
        self.assertEqual(numbered, SECTIONS)
        text = "\n".join(lines)
        for heading in SECTIONS:
            with self.subTest(heading=heading):
                self.assertIn("{{", section(text, heading))
        for heading, needles in (
            ("## 2. Intent", ("- I1 Goal: <goal>",)),
            (
                "## 1. Problem",
                (
                    "Current: WHEN <condition> THEN the system <behaviour today>.",
                    "Expected: WHEN <condition> THE SYSTEM SHALL <behaviour wanted>.",
                    "Unchanged: WHEN <other condition> THE SYSTEM SHALL CONTINUE TO <behaviour that stays>.",
                ),
            ),
            (
                "## 3. Evidence",
                ("the reproduction, its output and the confirmed cause with path and line", "the pattern it follows"),
            ),
            ("## 4. Decisions", ("(relies on I<n>)", "`${CLAUDE_PLUGIN_ROOT}/core/practices.md`")),
        ):
            for needle in needles:
                self.assertIn(needle, section(text, heading), needle)

    def test_a_filled_brief_passes_check_spec_and_renders(self):
        check_spec = load("scripts/check_spec.py")
        render_record = load("scripts/render_record.py")
        check_items = load("scripts/check_items.py")
        with tempfile.TemporaryDirectory() as folder:
            spec_path = pathlib.Path(folder) / "stock-report.md"
            record_path = pathlib.Path(folder) / "stock-report.record.json"
            items_path = pathlib.Path(folder) / "stock-report.items.json"
            spec_path.write_text(FILLED_BRIEF, encoding="utf-8")
            record_path.write_text(json.dumps(brief_record()), encoding="utf-8")
            argv = ["--record", str(record_path), "--spec", str(spec_path), "--items", str(items_path)]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = render_record.main(argv)
            self.assertEqual(code, 0, output.getvalue())
            rendered = read(spec_path)
            lines = rendered.splitlines()
            self.assertIn(TOTAL_ROW, lines)
            self.assertIn(LOW_STOCK_ORDER, lines)
            self.assertNotIn("{{written by the render script from the record}}", lines)
            self.assertEqual(check_spec.check(read(TEMPLATE), rendered), ())
            items = json.loads(read(items_path))
            self.assertEqual([item["spec_ref"] for item in items], [["5.1"], ["5.2"]])
            self.assertEqual(check_items.check_file(str(items_path)), ())

    def test_brief_names_no_consuming_tool(self):
        names = load("tests/test_hooks.py").consumer_names()
        self.assertEqual(len(names), 1, names)
        for path in (BRIEF, TEMPLATE):
            self.assertNotIn(names[0], read(path).lower(), str(path))


if __name__ == "__main__":
    unittest.main()
