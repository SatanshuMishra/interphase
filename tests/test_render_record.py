import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest

ELLIPSIS = "…"
SOURCE_TEXT = "def total_of(total):\n    return total\n"
REQUEST = (
    "# Demo feature\n\n"
    "## 1. Request\n\nAdd a total to the app.\n\n"
    "## 6. Requirements\n\nR1. The app returns the total it is given.\n\n"
)
CRITERIA = (
    "## 7. Acceptance criteria\n\n"
    "### 7.1 {{short name of the first criterion}}\n\n"
    "{{Given a starting state, when an action happens, then an observable result.}}\n\n"
)
EDGES = "## 8. Edge cases\n\nAn empty list totals zero.\n"
SPEC_TEXT = REQUEST + CRITERIA + EDGES
NO_CRITERIA_SPEC = REQUEST + EDGES
TWO_CRITERIA_SPEC = REQUEST + CRITERIA + CRITERIA.replace("## 7.", "## 9.") + EDGES
RECORD_PATH = "docs/specs/demo.record.json"
SPEC_PATH = "docs/specs/demo.md"
ITEMS_PATH = "docs/specs/demo.items.json"
ARGV = ("--record", RECORD_PATH, "--spec", SPEC_PATH, "--items", ITEMS_PATH)
BLOCK_7_1_HEAD = (
    "### 7.1 The total adds up\n\n"
    "Given a total, when the app returns it, then it is unchanged.\n\n"
    "Where passing proves it: python3 -m unittest on macOS.\n\n"
    "| Test | Runs in | Given | Expected | Covers |\n"
    "|---|---|---|---|---|\n"
)
BLOCK_7_1 = (
    BLOCK_7_1_HEAD
    + "| `tests/test_app.py` `test_total` | python3 -m unittest on macOS | a total of 3 | 3 is returned | none |"
)
ROW = {
    "file": "tests/test_app.py",
    "name": "test_total",
    "given": "a total of 3",
    "expect": "3 is returned",
    "env": "unit-tests",
    "step": "build-app",
}
PAYLOAD = {"name": "payload", "over": "the payload field agent_id", "classes": ["absent", "present"]}
PAYLOAD_ROWS = [
    {**ROW, "covers": ["payload: absent"]},
    {**ROW, "name": "test_present", "given": "a total of 4", "expect": "4 is returned", "covers": ["payload: present"]},
]
SUITE_FACT = {"id": "f2", "fact": "The suite passes", "command": "python3 -m unittest", "output": "OK"}
DOCUMENTED_FACT = {"id": "f3", "fact": "The format is documented", "url": "https://example.com/a"}
ITEM_FIELDS = frozenset(
    (
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
)


def record():
    return {
        "status": "in-progress",
        "environments": [
            {"name": "unit-tests", "what": "python3 -m unittest on macOS", "builder_runs": True},
            {"name": "phone", "what": "Galaxy Note10+, Android 12, Impeller renderer", "builder_runs": False},
        ],
        "facts": [
            {
                "id": "f1",
                "fact": "The app returns the total it is given",
                "path": "src/app.py",
                "line": 2,
                "quote": "return total",
            }
        ],
        "criteria": [
            {
                "number": "7.1",
                "title": "The total adds up",
                "text": "Given a total, when the app returns it, then it is unchanged.",
                "where": ["unit-tests"],
                "tests": [dict(ROW)],
            },
            {
                "number": "7.2",
                "title": "The total shows on the phone",
                "text": "The total appears on the phone within a second" + ELLIPSIS,
                "where": ["phone"],
                "tests": [],
                "unproven": "needs the phone",
            },
        ],
        "steps": [
            {
                "name": "build-app",
                "files": ["src/app.py", "tests/test_app.py"],
                "criteria": ["7.1"],
                "task": "Build the app.",
                "msp": "first",
            },
            {
                "name": "tune-app",
                "files": ["src/tune.py"],
                "criteria": ["7.2"],
                "task": "Tune the app for the phone.",
            },
        ],
    }


def replace_step(source, index, step):
    steps = source["steps"]
    return {**source, "steps": steps[:index] + [step] + steps[index + 1 :]}


def without_task(source):
    step = {key: value for key, value in source["steps"][0].items() if key != "task"}
    return replace_step(source, 0, step)


def renumbered(source):
    criteria = source["criteria"]
    moved = {**source, "criteria": criteria[:1] + [{**criteria[1], "number": "8.2"}]}
    return replace_step(moved, 1, {**source["steps"][1], "criteria": ["8.2"]})


def varying(source, pass_rate):
    criteria = source["criteria"]
    test = {**criteria[0]["tests"][0], "cases": 60, "runs": 3, "pass_rate": pass_rate}
    return {**source, "criteria": [{**criteria[0], "varies": "output", "tests": [test]}] + criteria[1:]}


def first_criterion(source, **fields):
    criteria = source["criteria"]
    return {**source, "criteria": [{**criteria[0], **fields}] + criteria[1:]}


def with_facts(source, *facts):
    return {**source, "facts": source["facts"] + list(facts)}


def amended(source):
    fix = {
        "name": "fix-app",
        "files": ["src/tune.py"],
        "criteria": ["7.2"],
        "task": "Tune the app for the phone.",
        "amendment": 1,
        "after": ["build-app"],
    }
    return {**source, "steps": source["steps"][:1] + [fix]}


def split_section(text):
    lines = text.splitlines()
    start = lines.index("## 7. Acceptance criteria")
    end = next((position for position in range(start + 1, len(lines)) if lines[position].startswith("## ")), len(lines))
    return lines[: start + 1], lines[start + 1 : end], lines[end:]


def spec_block(spec_text, number):
    lines = spec_text.splitlines()
    start = next(position for position, line in enumerate(lines) if line.startswith("### %s " % number))
    end = next(
        (
            position
            for position in range(start + 1, len(lines))
            if lines[position].startswith("### ") or lines[position].startswith("## ")
        ),
        len(lines),
    )
    block = lines[start:end]
    last = max(position for position, line in enumerate(block) if line.strip())
    return "\n".join(block[: last + 1])


class RenderFixture:
    def load(self, name):
        root = pathlib.Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(name, str(root / "scripts" / (name + ".py")))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def write_fixture(self, folder, source, spec_text):
        base = pathlib.Path(folder)
        (base / "src").mkdir()
        (base / "src" / "app.py").write_text(SOURCE_TEXT, encoding="utf-8")
        (base / "docs" / "specs").mkdir(parents=True)
        (base / RECORD_PATH).write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
        (base / SPEC_PATH).write_text(spec_text, encoding="utf-8")

    def run_main(self, folder, argv=ARGV):
        module = self.load("render_record")
        out = io.StringIO()
        err = io.StringIO()
        previous = os.getcwd()
        os.chdir(folder)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = module.main(list(argv))
        finally:
            os.chdir(previous)
        return code, out.getvalue(), err.getvalue()

    def rendered(self, folder, source, spec_text=SPEC_TEXT, argv=ARGV):
        self.write_fixture(folder, source, spec_text)
        code, out, err = self.run_main(folder, argv)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(out.splitlines(), ["wrote " + SPEC_PATH, "wrote " + ITEMS_PATH])
        base = pathlib.Path(folder)
        return (base / SPEC_PATH).read_bytes().decode("utf-8"), (base / ITEMS_PATH).read_bytes().decode("utf-8")

    def block_of(self, source, number):
        with tempfile.TemporaryDirectory() as folder:
            spec_text, _ = self.rendered(folder, source)
        return spec_block(spec_text, number)


class RenderRecordTest(RenderFixture, unittest.TestCase):
    def test_render_replaces_only_the_acceptance_section(self):
        with tempfile.TemporaryDirectory() as folder:
            spec_text, _ = self.rendered(folder, record())
        before, _, after = split_section(SPEC_TEXT)
        new_before, section, new_after = split_section(spec_text)
        self.assertEqual(new_before, before)
        self.assertEqual(new_after, after)
        body = "\n".join(section)
        self.assertIn("### 7.1 ", body)
        self.assertIn("### 7.2 ", body)
        self.assertLess(body.index("### 7.1 "), body.index("### 7.2 "))
        self.assertIn("Unproven: needs the phone", body)
        self.assertNotIn("{{", body)

    def test_rendered_items_pass_the_items_check(self):
        items_module = self.load("check_items")
        with tempfile.TemporaryDirectory() as folder:
            _, items_text = self.rendered(folder, record())
            base = pathlib.Path(folder)
            findings = items_module.check_file(str(base / ITEMS_PATH))
            spec_bytes = (base / SPEC_PATH).read_bytes()
            spec_path = str((base / SPEC_PATH).resolve())
        self.assertEqual(tuple(finding for finding in findings if finding[0] == "error"), ())
        items = json.loads(items_text)
        for step in items:
            with self.subTest(step=step["name"]):
                self.assertTrue(os.path.isabs(step["source"]["path"]))
                self.assertEqual(step["source"]["path"], spec_path)
                self.assertEqual(step["source"]["sha256"], hashlib.sha256(spec_bytes).hexdigest())
        steps = {step["name"]: step for step in items}
        self.assertEqual(steps["build-app"]["acceptance"], [{"file": "tests/test_app.py", "test": "test_total"}])
        self.assertEqual(steps["build-app"]["spec_ref"], ["7.1"])
        self.assertEqual(steps["tune-app"]["acceptance"], [])
        self.assertEqual(steps["tune-app"]["spec_ref"], ["7.2"])
        self.assertEqual(steps["build-app"]["msp"], "first")
        self.assertIn(ELLIPSIS, items_text)

    def test_each_task_carries_its_criteria_word_for_word(self):
        source = record()
        with tempfile.TemporaryDirectory() as folder:
            spec_text, items_text = self.rendered(folder, source)
        self.assertEqual(spec_block(spec_text, "7.1"), BLOCK_7_1)
        tasks = {step["name"]: step["task"] for step in json.loads(items_text)}
        for step in source["steps"]:
            with self.subTest(step=step["name"]):
                task = tasks[step["name"]]
                self.assertTrue(task.startswith(step["task"]))
                self.assertIn("Acceptance criteria this Step proves:", task)
                for number in step["criteria"]:
                    self.assertIn(spec_block(spec_text, number), task)

    def test_population_is_written_into_spec_and_task(self):
        for pass_rate, shown in ((0.9, "0.9"), (1, "1")):
            row = (
                "| `tests/test_app.py` `test_total` | python3 -m unittest on macOS; 60 cases, 3 runs each, "
                "pass rate at least %s | a total of 3 | 3 is returned | none |" % shown
            )
            with self.subTest(pass_rate=pass_rate), tempfile.TemporaryDirectory() as folder:
                spec_text, items_text = self.rendered(folder, varying(record(), pass_rate))
                block = spec_block(spec_text, "7.1")
                self.assertEqual(block, BLOCK_7_1_HEAD + row)
                tasks = {step["name"]: step["task"] for step in json.loads(items_text)}
                self.assertIn(block, tasks["build-app"])
                self.assertNotIn("60 cases, 3 runs each", spec_block(spec_text, "7.2"))
                self.assertNotIn("60 cases, 3 runs each", tasks["tune-app"])

    def test_items_format_is_unchanged_by_population(self):
        items_module = self.load("check_items")
        with tempfile.TemporaryDirectory() as folder:
            _, items_text = self.rendered(folder, varying(record(), 0.9))
            findings = items_module.check_file(str(pathlib.Path(folder) / ITEMS_PATH))
        self.assertEqual(tuple(finding for finding in findings if finding[0] == "error"), ())
        items = json.loads(items_text)
        for step in items:
            with self.subTest(step=step["name"]):
                self.assertEqual(frozenset(step) - ITEM_FIELDS, frozenset())
                self.assertEqual(sorted(step["source"]), ["path", "sha256"])
                for entry in step["acceptance"]:
                    self.assertEqual(sorted(entry), ["file", "test"])
        steps = {step["name"]: step for step in items}
        self.assertEqual(steps["build-app"]["acceptance"], [{"file": "tests/test_app.py", "test": "test_total"}])
        self.assertIn(
            "| python3 -m unittest on macOS; 60 cases, 3 runs each, pass rate at least 0.9 |",
            steps["build-app"]["task"],
        )

    def test_render_refuses_what_the_complete_check_rejects(self):
        cases = (
            ("a step has no task", without_task(record()), SPEC_TEXT),
            ("the spec has no Acceptance criteria section", record(), NO_CRITERIA_SPEC),
            ("the spec has two Acceptance criteria sections", record(), TWO_CRITERIA_SPEC),
            ("a criterion number is outside the section", renumbered(record()), SPEC_TEXT),
        )
        for label, source, spec_text in cases:
            with self.subTest(label), tempfile.TemporaryDirectory() as folder:
                self.write_fixture(folder, source, spec_text)
                base = pathlib.Path(folder)
                (base / ITEMS_PATH).write_text("[]", encoding="utf-8")
                spec_before = (base / SPEC_PATH).read_bytes()
                items_before = (base / ITEMS_PATH).read_bytes()
                code, out, _ = self.run_main(folder)
                self.assertEqual(code, 1)
                self.assertTrue(any(line.startswith("error:") for line in out.splitlines()), out)
                self.assertEqual((base / SPEC_PATH).read_bytes(), spec_before)
                self.assertEqual((base / ITEMS_PATH).read_bytes(), items_before)

    def test_rendering_twice_gives_identical_files(self):
        with tempfile.TemporaryDirectory() as folder:
            self.rendered(folder, record())
            base = pathlib.Path(folder)
            first = ((base / SPEC_PATH).read_bytes(), (base / ITEMS_PATH).read_bytes())
            code, out, err = self.run_main(folder)
            second = ((base / SPEC_PATH).read_bytes(), (base / ITEMS_PATH).read_bytes())
        self.assertEqual(code, 0, out + err)
        self.assertEqual(second[0], first[0])
        self.assertEqual(second[1], first[1])


class CaseTableRenderTest(RenderFixture, unittest.TestCase):
    def test_block_without_domains_has_no_inputs_or_order(self):
        block = self.block_of(record(), "7.1")
        self.assertEqual(
            block,
            "### 7.1 The total adds up\n\n"
            "Given a total, when the app returns it, then it is unchanged.\n\n"
            "Where passing proves it: python3 -m unittest on macOS.\n\n"
            "| Test | Runs in | Given | Expected | Covers |\n"
            "|---|---|---|---|---|\n"
            "| `tests/test_app.py` `test_total` | python3 -m unittest on macOS | a total of 3 | 3 is returned | none |",
        )
        for absent in ("Inputs:", "When the bound is reached", "Facts:"):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, block)

    def test_domains_render_as_inputs(self):
        block = self.block_of(first_criterion(record(), domains=[PAYLOAD], tests=PAYLOAD_ROWS), "7.1")
        self.assertIn("\n\nInputs:\n- the payload field agent_id (`payload`): absent; present\n\n", block)

    def test_gives_way_renders_as_a_numbered_order(self):
        tests = [{**ROW, "covers": ["gives-way: older lines", "gives-way: the header"]}]
        block = self.block_of(first_criterion(record(), gives_way=["older lines", "the header"], tests=tests), "7.1")
        self.assertIn(
            "\n\nWhen the bound is reached, these give way, first to last:\n1. older lines\n2. the header\n\n", block
        )

    def test_facts_render_with_their_citations(self):
        source = with_facts(
            first_criterion(record(), facts=["f1"], domains=[{**PAYLOAD, "fact": "f2"}], tests=PAYLOAD_ROWS),
            SUITE_FACT,
        )
        self.assertIn(
            "\n\nFacts:\n"
            '- The app returns the total it is given (`src/app.py`:2, quoting "return total")\n'
            '- The suite passes (ran `python3 -m unittest`, which showed "OK")\n\n',
            self.block_of(source, "7.1"),
        )

    def test_fact_cited_by_url_renders_the_url(self):
        source = with_facts(first_criterion(record(), facts=["f3"]), DOCUMENTED_FACT)
        self.assertIn(
            "\n\nFacts:\n- The format is documented (https://example.com/a)\n\n", self.block_of(source, "7.1")
        )

    def test_fact_named_twice_renders_once(self):
        source = with_facts(
            first_criterion(record(), facts=["f2"], domains=[{**PAYLOAD, "fact": "f2"}], tests=PAYLOAD_ROWS),
            SUITE_FACT,
        )
        block = self.block_of(source, "7.1")
        self.assertIn('\n\nFacts:\n- The suite passes (ran `python3 -m unittest`, which showed "OK")\n\n', block)
        self.assertEqual(block.count("- The suite passes ("), 1)

    def test_rows_render_as_a_table(self):
        block = self.block_of(first_criterion(record(), domains=[PAYLOAD], tests=PAYLOAD_ROWS), "7.1")
        self.assertIn(
            "| Test | Runs in | Given | Expected | Covers |\n"
            "|---|---|---|---|---|\n"
            "| `tests/test_app.py` `test_total` | python3 -m unittest on macOS | a total of 3 | 3 is returned "
            "| payload: absent |\n"
            "| `tests/test_app.py` `test_present` | python3 -m unittest on macOS | a total of 4 | 4 is returned "
            "| payload: present |",
            block,
        )

    def test_row_without_covers_shows_none(self):
        self.assertIn(
            "| `tests/test_app.py` `test_total` | python3 -m unittest on macOS | a total of 3 | 3 is returned | none |",
            self.block_of(record(), "7.1"),
        )

    def test_cells_escape_pipes_and_line_breaks(self):
        block = self.block_of(first_criterion(record(), tests=[{**ROW, "given": "a | b\nc"}]), "7.1")
        self.assertIn(
            "| `tests/test_app.py` `test_total` | python3 -m unittest on macOS | a \\| b c | 3 is returned | none |",
            block,
        )

    def test_varying_row_shows_its_population(self):
        self.assertIn(
            "| `tests/test_app.py` `test_total` | python3 -m unittest on macOS; 60 cases, 3 runs each, "
            "pass rate at least 0.9 | a total of 3 | 3 is returned | none |",
            self.block_of(varying(record(), 0.9), "7.1"),
        )

    def test_unproven_block_has_no_table(self):
        source = record()
        criteria = source["criteria"]
        block = self.block_of({**source, "criteria": [criteria[0], {**criteria[1], "domains": [PAYLOAD]}]}, "7.2")
        self.assertEqual(
            block,
            "### 7.2 The total shows on the phone\n\n"
            "The total appears on the phone within a second" + ELLIPSIS + "\n\n"
            "Where passing proves it: Galaxy Note10+, Android 12, Impeller renderer.\n\n"
            "Inputs:\n- the payload field agent_id (`payload`): absent; present\n\n"
            "Unproven: needs the phone",
        )
        self.assertNotIn("| Test |", block)

    def test_task_carries_the_case_table(self):
        tests = [{**ROW, "covers": ["payload: absent", "payload: present"]}]
        with tempfile.TemporaryDirectory() as folder:
            spec_text, items_text = self.rendered(folder, first_criterion(record(), domains=[PAYLOAD], tests=tests))
        block = spec_block(spec_text, "7.1")
        task = {step["name"]: step["task"] for step in json.loads(items_text)}["build-app"]
        inputs = "Inputs:\n- the payload field agent_id (`payload`): absent; present"
        table = (
            "| Test | Runs in | Given | Expected | Covers |\n"
            "|---|---|---|---|---|\n"
            "| `tests/test_app.py` `test_total` | python3 -m unittest on macOS | a total of 3 | 3 is returned "
            "| payload: absent; payload: present |"
        )
        for part in (inputs, table):
            with self.subTest(part=part):
                self.assertIn(part, block)
                self.assertIn(part, task)
        self.assertIn(block, task)


class AmendmentRenderTest(RenderFixture, unittest.TestCase):
    def test_amendment_writes_only_its_steps(self):
        with tempfile.TemporaryDirectory() as folder:
            _, items_text = self.rendered(folder, amended(record()), argv=ARGV + ("--amendment", "1"))
        self.assertEqual([item["name"] for item in json.loads(items_text)], ["fix-app"])

    def test_amendment_still_renders_the_whole_spec(self):
        with tempfile.TemporaryDirectory() as folder:
            amended_spec, _ = self.rendered(folder, amended(record()), argv=ARGV + ("--amendment", "1"))
        with tempfile.TemporaryDirectory() as folder:
            whole_spec, _ = self.rendered(folder, amended(record()))
        _, section, _ = split_section(amended_spec)
        body = "\n".join(section)
        self.assertIn("### 7.1 The total adds up", body)
        self.assertIn("### 7.2 The total shows on the phone", body)
        self.assertEqual(amended_spec, whole_spec)

    def test_amendment_no_step_carries_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            self.write_fixture(folder, amended(record()), SPEC_TEXT)
            code, out, _ = self.run_main(folder, ARGV + ("--amendment", "2"))
            base = pathlib.Path(folder)
            spec_after = (base / SPEC_PATH).read_bytes().decode("utf-8")
            items_written = (base / ITEMS_PATH).exists()
        self.assertEqual(code, 1)
        self.assertEqual(out, "error: no step has amendment 2\n")
        self.assertEqual(spec_after, SPEC_TEXT)
        self.assertFalse(items_written)

    def test_amendment_that_is_not_a_positive_number_is_a_usage_error(self):
        for value in ("0", "-1", "x", "1.5", "01"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as folder:
                self.write_fixture(folder, amended(record()), SPEC_TEXT)
                code, _, err = self.run_main(folder, ARGV + ("--amendment", value))
                base = pathlib.Path(folder)
                self.assertEqual(code, 2)
                self.assertEqual(
                    err.splitlines(),
                    ["usage: python3 render_record.py --record RECORD --spec SPEC --items ITEMS [--amendment N]"],
                )
                self.assertEqual((base / SPEC_PATH).read_bytes().decode("utf-8"), SPEC_TEXT)
                self.assertFalse((base / ITEMS_PATH).exists())

    def test_amendment_option_may_come_first(self):
        argv = ("--amendment", "1", "--record", RECORD_PATH, "--spec", SPEC_PATH, "--items", ITEMS_PATH)
        with tempfile.TemporaryDirectory() as folder:
            _, items_text = self.rendered(folder, amended(record()), argv=argv)
        self.assertEqual([item["name"] for item in json.loads(items_text)], ["fix-app"])

    def test_amended_step_drops_after_outside_its_file(self):
        with tempfile.TemporaryDirectory() as folder:
            _, items_text = self.rendered(folder, amended(record()), argv=ARGV + ("--amendment", "1"))
        items = json.loads(items_text)
        self.assertEqual(items[0]["name"], "fix-app")
        self.assertNotIn("after", items[0])

    def test_amended_step_keeps_after_inside_its_file(self):
        docs = {
            "name": "fix-docs",
            "files": ["docs/fix.md"],
            "criteria": ["7.2"],
            "task": "Describe the fix.",
            "amendment": 1,
            "after": ["build-app", "fix-app"],
        }
        source = amended(record())
        with tempfile.TemporaryDirectory() as folder:
            _, items_text = self.rendered(
                folder, {**source, "steps": source["steps"] + [docs]}, argv=ARGV + ("--amendment", "1")
            )
        items = {item["name"]: item for item in json.loads(items_text)}
        self.assertEqual(sorted(items), ["fix-app", "fix-docs"])
        self.assertEqual(items["fix-docs"]["after"], ["fix-app"])
        self.assertNotIn("after", items["fix-app"])

    def test_render_without_amendment_writes_every_step(self):
        with tempfile.TemporaryDirectory() as folder:
            _, items_text = self.rendered(folder, amended(record()))
        items = json.loads(items_text)
        self.assertEqual([item["name"] for item in items], ["build-app", "fix-app"])
        for item in items:
            with self.subTest(step=item["name"]):
                self.assertNotIn("amendment", item)


if __name__ == "__main__":
    unittest.main()
