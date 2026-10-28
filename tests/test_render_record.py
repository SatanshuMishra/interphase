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
REQUEST = (
    "# Demo feature\n\n"
    "## 1. Problem\n\nAdd a total to the app.\n\n"
    "## 4. Decisions\n\nThe app returns the total it is given.\n\n"
)
SEAMS_SECTION = (
    "## 5. Test seams\n\n"
    "{{written by the render script from the record: the agreed seams, then one numbered heading per acceptance "
    "criterion}}\n\n"
)
TAIL = "## 6. Out of scope\n\nCurrency conversion.\n"
SPEC_TEXT = REQUEST + SEAMS_SECTION + TAIL
NO_SEAMS_SPEC = REQUEST + TAIL
OLD_SECTION_SPEC = REQUEST + "## 5. Acceptance criteria\n\n### 5.1 {{name}}\n\n" + TAIL
TWO_SEAMS_SPEC = REQUEST + SEAMS_SECTION + SEAMS_SECTION.replace("## 5.", "## 9.") + TAIL
RECORD_PATH = "docs/specs/demo.record.json"
SPEC_PATH = "docs/specs/demo.md"
ITEMS_PATH = "docs/specs/demo.items.json"
ARGV = ("--record", RECORD_PATH, "--spec", SPEC_PATH, "--items", ITEMS_PATH)
UNIT_SEAM_LINE = (
    "- `unit-tests`: the total_of function in src/app.py. Catches: a wrong total. "
    "Misses: how the total is drawn on screen."
)
PHONE_SEAM_LINE = (
    "- `phone-screen`: the total drawn on a Galaxy Note10+. Catches: a total drawn late. "
    "Misses: a wrong total. The builder cannot run it."
)
SEAMS_LIST = "Seams:\n" + UNIT_SEAM_LINE + "\n" + PHONE_SEAM_LINE
UNIT_SEAM_TEXT = "Seam: `unit-tests`, the total_of function in src/app.py."
APP_LINES = (
    "Acceptance lines:\n- C1.1 (exact, cli python3): run `python3 -m unittest tests.test_app` "
    "from the repository root; it passes when the test passes."
)
PHONE_SEAM_TEXT = "Seam: `phone-screen`, the total drawn on a Galaxy Note10+."
BLOCK_5_1_HEAD = (
    "### 5.1 The total adds up\n\n"
    "Given a total, when the app returns it, then it is unchanged.\n\n" + UNIT_SEAM_TEXT + "\n\n" + APP_LINES + "\n\n"
)
PLAIN_HEAD = "| Test | Given | Expected |\n|---|---|---|\n"
TOTAL_ROW = "| `tests/test_app.py` `test_total` | a total of 3 | 3 is returned |"
BLOCK_5_1 = BLOCK_5_1_HEAD + PLAIN_HEAD + TOTAL_ROW
BLOCK_5_2 = (
    "### 5.2 The total shows on the phone\n\n"
    "The total appears on the phone within a second" + ELLIPSIS + "\n\n" + PHONE_SEAM_TEXT + "\n\n"
    "Unproven: needs the phone"
)
RENDERED_SPEC = (
    REQUEST + "## 5. Test seams\n\n" + SEAMS_LIST + "\n\n" + BLOCK_5_1 + "\n\n" + BLOCK_5_2 + "\n\n" + TAIL
)
PROVES = "Acceptance criteria this Step proves:"
ROW = {
    "file": "tests/test_app.py",
    "name": "test_total",
    "given": "a total of 3",
    "expect": "3 is returned",
    "step": "build-app",
    "check": "C1.1",
}
APP_LINE = {
    "id": "C1.1",
    "kind": "exact",
    "surface": {"family": "cli", "target": "python3"},
    "command": "python3 -m unittest tests.test_app",
    "pass": "the test passes",
}
OUTCOMES = {"store": "/var/empty/trajectories.jsonl", "entries": 0, "repeated": []}
PAYLOAD = {"name": "payload", "over": "the payload field agent_id", "classes": ["absent", "present"]}
PAYLOAD_ROWS = [
    {**ROW, "covers": ["payload: absent"]},
    {**ROW, "name": "test_present", "given": "a total of 4", "expect": "4 is returned", "covers": ["payload: present"]},
]
PAYLOAD_CASES = "- the payload field agent_id (`payload`): absent; present"
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


def probe(check):
    return {"check": check, "probe": "command", "target": "python3", "status": "pass", "detail": "/usr/bin/python3"}


def record():
    return {
        "status": "in-progress",
        "seams": [
            {
                "name": "unit-tests",
                "interface": "the total_of function in src/app.py",
                "catches": "a wrong total",
                "misses": "how the total is drawn on screen",
                "builder_runs": True,
            },
            {
                "name": "phone-screen",
                "interface": "the total drawn on a Galaxy Note10+",
                "catches": "a total drawn late",
                "misses": "a wrong total",
                "builder_runs": False,
            },
        ],
        "criteria": [
            {
                "number": "5.1",
                "title": "The total adds up",
                "text": "Given a total, when the app returns it, then it is unchanged.",
                "seam": "unit-tests",
                "acceptance": [dict(APP_LINE)],
                "tests": [dict(ROW)],
            },
            {
                "number": "5.2",
                "title": "The total shows on the phone",
                "text": "The total appears on the phone within a second" + ELLIPSIS,
                "seam": "phone-screen",
                "tests": [],
                "unproven": "needs the phone",
            },
        ],
        "steps": [
            {
                "name": "build-app",
                "files": ["src/app.py"],
                "criteria": ["5.1"],
                "task": "Build the app.",
                "msp": "first",
            },
            {
                "name": "tune-app",
                "files": ["src/tune.py"],
                "criteria": ["5.2"],
                "task": "Tune the app for the phone.",
            },
        ],
        "locked": ["tests/test_app.py"],
        "probes": [probe("C1.1")],
        "outcomes": OUTCOMES,
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


def second_criterion(source, **fields):
    criteria = source["criteria"]
    return {**source, "criteria": criteria[:1] + [{**criteria[1], **fields}]}


def first_seam(source, **fields):
    seams = source["seams"]
    return {**source, "seams": [{**seams[0], **fields}] + seams[1:]}


def tabled(source, kind, tests=PAYLOAD_ROWS, **fields):
    return first_criterion(source, case_table=kind, domains=[PAYLOAD], tests=tests, **fields)


def amended(source):
    fix = {
        "name": "fix-app",
        "files": ["src/tune.py"],
        "criteria": ["5.2"],
        "task": "Tune the app for the phone.",
        "amendment": 1,
        "after": ["build-app"],
    }
    return {**source, "steps": source["steps"][:1] + [fix]}


def split_section(text):
    lines = text.splitlines()
    start = lines.index("## 5. Test seams")
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

    def tasks_of(self, source):
        with tempfile.TemporaryDirectory() as folder:
            _, items_text = self.rendered(folder, source)
        return {step["name"]: step["task"] for step in json.loads(items_text)}

    def refused(self, source, spec_text):
        with tempfile.TemporaryDirectory() as folder:
            self.write_fixture(folder, source, spec_text)
            base = pathlib.Path(folder)
            (base / ITEMS_PATH).write_text("[]", encoding="utf-8")
            code, out, _ = self.run_main(folder)
            spec_after = (base / SPEC_PATH).read_bytes().decode("utf-8")
            items_after = (base / ITEMS_PATH).read_bytes().decode("utf-8")
        self.assertEqual(code, 1)
        self.assertEqual(spec_after, spec_text)
        self.assertEqual(items_after, "[]")
        return out


class RenderRecordTest(RenderFixture, unittest.TestCase):
    def test_render_writes_the_whole_test_seams_section(self):
        with tempfile.TemporaryDirectory() as folder:
            spec_text, _ = self.rendered(folder, record())
        self.assertEqual(spec_text, RENDERED_SPEC)

    def test_render_replaces_only_the_test_seams_section(self):
        with tempfile.TemporaryDirectory() as folder:
            spec_text, _ = self.rendered(folder, record())
        before, _, after = split_section(SPEC_TEXT)
        new_before, section, new_after = split_section(spec_text)
        self.assertEqual(new_before, before)
        self.assertEqual(new_after, after)
        body = "\n".join(section)
        self.assertLess(body.index("Seams:"), body.index("### 5.1 "))
        self.assertLess(body.index("### 5.1 "), body.index("### 5.2 "))
        self.assertNotIn("{{", body)

    def test_render_function_takes_no_root(self):
        module = self.load("render_record")
        errors, spec_text, items = module.render(json.dumps(record()), SPEC_TEXT, "/specs/demo.md")
        self.assertEqual(errors, ())
        self.assertEqual(spec_text, RENDERED_SPEC)
        self.assertEqual(
            items[0]["source"],
            {"path": "/specs/demo.md", "sha256": hashlib.sha256(RENDERED_SPEC.encode("utf-8")).hexdigest()},
        )

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
        self.assertEqual(steps["build-app"]["spec_ref"], ["5.1"])
        self.assertEqual(steps["tune-app"]["acceptance"], [])
        self.assertEqual(steps["tune-app"]["spec_ref"], ["5.2"])
        self.assertEqual(steps["build-app"]["msp"], "first")
        self.assertIn(ELLIPSIS, items_text)

    def test_each_task_carries_its_criteria_and_seam_word_for_word(self):
        tasks = self.tasks_of(record())
        self.assertEqual(tasks["build-app"], "Build the app.\n\n" + PROVES + "\n\n" + BLOCK_5_1)
        self.assertEqual(tasks["tune-app"], "Tune the app for the phone.\n\n" + PROVES + "\n\n" + BLOCK_5_2)
        self.assertIn(UNIT_SEAM_TEXT, tasks["build-app"])
        self.assertIn(PHONE_SEAM_TEXT, tasks["tune-app"])
        for task in tasks.values():
            with self.subTest(task=task):
                self.assertNotIn("Seams:", task)

    def test_task_of_a_step_proving_two_criteria_carries_both_blocks(self):
        source = replace_step(record(), 0, {**record()["steps"][0], "criteria": ["5.1", "5.2"]})
        source = {**source, "steps": source["steps"][:1]}
        tasks = self.tasks_of(source)
        self.assertEqual(
            tasks["build-app"], "Build the app.\n\n" + PROVES + "\n\n" + BLOCK_5_1 + "\n\n" + BLOCK_5_2
        )

    def test_population_is_written_into_spec_and_task(self):
        for pass_rate, shown in ((0.9, "0.9"), (1, "1")):
            expected = (
                BLOCK_5_1_HEAD
                + "| Test | Given | Expected | Runs |\n"
                + "|---|---|---|---|\n"
                + "| `tests/test_app.py` `test_total` | a total of 3 | 3 is returned "
                + "| 60 cases, 3 runs each, pass rate at least %s |" % shown
            )
            with self.subTest(pass_rate=pass_rate), tempfile.TemporaryDirectory() as folder:
                spec_text, items_text = self.rendered(folder, varying(record(), pass_rate))
                self.assertEqual(spec_block(spec_text, "5.1"), expected)
                tasks = {step["name"]: step["task"] for step in json.loads(items_text)}
                self.assertIn(expected, tasks["build-app"])
                self.assertNotIn("60 cases, 3 runs each", spec_block(spec_text, "5.2"))
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
        self.assertIn("| 60 cases, 3 runs each, pass rate at least 0.9 |", steps["build-app"]["task"])

    def test_render_refuses_what_the_complete_check_rejects(self):
        cases = (
            ("a step has no task", without_task(record()), SPEC_TEXT, "error: step build-app has no task\n"),
            ("the spec has no Test seams section", record(), NO_SEAMS_SPEC, "error: spec has no Test seams section\n"),
            (
                "the spec has only an Acceptance criteria section",
                record(),
                OLD_SECTION_SPEC,
                "error: spec has no Test seams section\n",
            ),
            ("the spec has two Test seams sections", record(), TWO_SEAMS_SPEC, "error: spec has 2 Test seams sections\n"),
            (
                "a criterion number is outside the section",
                renumbered(record()),
                SPEC_TEXT,
                "error: criterion 8.2 is outside Test seams section 5; its number must start with '5.'\n",
            ),
            (
                "a seam no criterion uses",
                {**record(), "seams": record()["seams"] + [{**record()["seams"][0], "name": "tablet"}]},
                SPEC_TEXT,
                "error: seam 'tablet' is used by no criterion\n",
            ),
            (
                "a criterion has an unproven reason that is not text",
                second_criterion(record(), unproven=None),
                SPEC_TEXT,
                "error: criterion 5.2 has unproven that is not a non-empty string\n",
            ),
        )
        for label, source, spec_text, expected in cases:
            with self.subTest(label):
                self.assertEqual(self.refused(source, spec_text), expected)

    def test_render_refuses_a_proof_rule_breach(self):
        criteria = record()["criteria"]
        source = {**record(), "criteria": criteria[:1] + [{key: value for key, value in criteria[1].items() if key != "unproven"}]}
        self.assertEqual(
            self.refused(source, SPEC_TEXT),
            "error: criterion 5.2 sits at a seam the builder cannot run and is not marked unproven\n",
        )

    def test_render_refuses_a_step_assumption_without_a_known_intent_line(self):
        intent_spec = SPEC_TEXT.replace("## 4. Decisions", "## 2. Intent\n\n- I1 Goal: show the total.\n\n## 4. Decisions")
        cases = (
            (
                "Totals use whole numbers.",
                "error: step build-app has an assumption that cites no intent line; end it with (relies on I<n>): Totals use whole numbers.\n",
            ),
            (
                "Totals use whole numbers (relies on I9).",
                "error: step build-app has an assumption that relies on I9, which is not an intent line of the spec: "
                "Totals use whole numbers (relies on I9).\n",
            ),
        )
        for text, expected in cases:
            with self.subTest(text):
                step = {**record()["steps"][0], "assumptions": [text]}
                self.assertEqual(self.refused(replace_step(record(), 0, step), intent_spec), expected)
        cited = {**record()["steps"][0], "assumptions": ["Totals use whole numbers (relies on I1)."]}
        with tempfile.TemporaryDirectory() as folder:
            _, items_text = self.rendered(folder, replace_step(record(), 0, cited), intent_spec)
        self.assertEqual(json.loads(items_text)[0]["assumptions"], ["Totals use whole numbers (relies on I1)."])

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


class SeamRenderTest(RenderFixture, unittest.TestCase):
    def test_seams_list_has_one_line_per_seam_in_record_order(self):
        with tempfile.TemporaryDirectory() as folder:
            spec_text, _ = self.rendered(folder, record())
        _, section, _ = split_section(spec_text)
        self.assertEqual(section[:4], ["", "Seams:", UNIT_SEAM_LINE, PHONE_SEAM_LINE])

    def test_only_an_unrunnable_seam_says_the_builder_cannot_run_it(self):
        with tempfile.TemporaryDirectory() as folder:
            spec_text, _ = self.rendered(folder, record())
        self.assertEqual(spec_text.count("The builder cannot run it."), 1)
        self.assertIn(PHONE_SEAM_LINE + "\n", spec_text)

    def test_seam_line_does_not_double_a_closing_full_stop(self):
        source = first_seam(
            record(),
            interface="the total_of function in src/app.py.",
            catches="a wrong total.",
            misses="how the total is drawn on screen.",
        )
        with tempfile.TemporaryDirectory() as folder:
            spec_text, _ = self.rendered(folder, source)
        self.assertIn(UNIT_SEAM_LINE + "\n", spec_text)
        self.assertEqual(spec_block(spec_text, "5.1"), BLOCK_5_1)

    def test_seam_line_joins_line_breaks(self):
        source = first_seam(record(), interface="the total_of function\nin src/app.py", catches="a wrong\r\ntotal")
        with tempfile.TemporaryDirectory() as folder:
            spec_text, _ = self.rendered(folder, source)
        self.assertIn(UNIT_SEAM_LINE + "\n", spec_text)
        self.assertIn("\n\n" + UNIT_SEAM_TEXT + "\n\n", spec_text)

    def test_each_block_names_its_seam_and_interface(self):
        self.assertIn("\n\n" + UNIT_SEAM_TEXT + "\n\n", self.block_of(record(), "5.1"))
        self.assertIn("\n\n" + PHONE_SEAM_TEXT + "\n\n", self.block_of(record(), "5.2"))

    def test_two_criteria_at_one_seam_each_name_it(self):
        criteria = record()["criteria"]
        shown = {
            "number": "5.3",
            "title": "The total is shown",
            "text": "The app shows the total.",
            "seam": "unit-tests",
            "acceptance": [{**APP_LINE, "id": "C3.1"}],
            "tests": [{**ROW, "name": "test_total_is_shown", "check": "C3.1"}],
        }
        source = {**record(), "criteria": criteria + [shown], "probes": [probe("C1.1"), probe("C3.1")]}
        source = replace_step(source, 0, {**source["steps"][0], "criteria": ["5.1", "5.3"]})
        with tempfile.TemporaryDirectory() as folder:
            spec_text, items_text = self.rendered(folder, source)
        self.assertEqual(
            spec_block(spec_text, "5.3"),
            "### 5.3 The total is shown\n\nThe app shows the total.\n\n" + UNIT_SEAM_TEXT + "\n\n"
            + APP_LINES.replace("C1.1", "C3.1") + "\n\n" + PLAIN_HEAD
            + "| `tests/test_app.py` `test_total_is_shown` | a total of 3 | 3 is returned |",
        )
        task = {step["name"]: step["task"] for step in json.loads(items_text)}["build-app"]
        self.assertEqual(task.count(UNIT_SEAM_TEXT), 2)


class LineSentenceTest(RenderFixture, unittest.TestCase):
    def test_exact_line_is_one_sentence(self):
        sentence = self.load("render_record").line_sentence(APP_LINE)
        self.assertEqual("Acceptance lines:\n- " + sentence, APP_LINES)

    def test_judged_line_joins_its_lines_and_drops_closing_full_stops(self):
        line = {
            "id": "C1.2",
            "kind": "judged",
            "surface": {"family": "agent", "target": "claude"},
            "command": "python3 tests/judge.py",
            "pass": "every trial\nmeets the rubric.",
            "rubric": "The summary names\neach failing check.",
            "trials": 3,
        }
        self.assertEqual(
            self.load("render_record").line_sentence(line),
            "C1.2 (judged, agent claude): run `python3 tests/judge.py` from the repository root three times "
            "and judge each run against the rubric: The summary names each failing check; "
            "it passes when every trial meets the rubric.",
        )


class CaseTableRenderTest(RenderFixture, unittest.TestCase):
    def test_plain_block_has_three_columns_and_no_cases(self):
        block = self.block_of(record(), "5.1")
        self.assertEqual(block, BLOCK_5_1)
        for absent in ("Cases for", "Covers", "Runs", "Runs in", "Where passing proves it", "Facts:", "Inputs:"):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, block)

    def test_security_case_table_renders_cases_and_covers(self):
        self.assertEqual(
            self.block_of(tabled(record(), "security"), "5.1"),
            BLOCK_5_1_HEAD
            + "Cases for a security need:\n" + PAYLOAD_CASES + "\n\n"
            + "| Test | Given | Expected | Covers |\n"
            + "|---|---|---|---|\n"
            + "| `tests/test_app.py` `test_total` | a total of 3 | 3 is returned | payload: absent |\n"
            + "| `tests/test_app.py` `test_present` | a total of 4 | 4 is returned | payload: present |",
        )

    def test_refusal_case_table_renders_its_own_heading(self):
        block = self.block_of(tabled(record(), "refusal"), "5.1")
        self.assertIn("\n\nCases for a refusal:\n" + PAYLOAD_CASES + "\n\n", block)
        self.assertNotIn("security", block)

    def test_each_domain_renders_one_case_line(self):
        cwd = {"name": "cwd", "over": "the working folder", "classes": ["root", "subfolder", "outside"]}
        tests = [
            {**PAYLOAD_ROWS[0], "covers": ["payload: absent", "cwd: root"]},
            {**PAYLOAD_ROWS[1], "covers": ["payload: present", "cwd: subfolder", "cwd: outside"]},
        ]
        block = self.block_of(first_criterion(tabled(record(), "security", tests), domains=[PAYLOAD, cwd]), "5.1")
        self.assertIn(
            "\n\nCases for a security need:\n" + PAYLOAD_CASES + "\n- the working folder (`cwd`): root; subfolder; outside\n\n",
            block,
        )
        self.assertIn("| payload: present; cwd: subfolder; cwd: outside |", block)

    def test_row_without_covers_in_a_case_table_shows_none(self):
        tests = [{**ROW, "name": "test_plain"}] + PAYLOAD_ROWS
        self.assertIn(
            "| `tests/test_app.py` `test_plain` | a total of 3 | 3 is returned | none |",
            self.block_of(tabled(record(), "security", tests), "5.1"),
        )

    def test_varying_case_table_has_covers_and_runs(self):
        tests = [{**row, "cases": 20, "runs": 2, "pass_rate": 0.95} for row in PAYLOAD_ROWS]
        block = self.block_of(tabled(record(), "refusal", tests, varies="input"), "5.1")
        self.assertIn(
            "| Test | Given | Expected | Covers | Runs |\n"
            "|---|---|---|---|---|\n"
            "| `tests/test_app.py` `test_total` | a total of 3 | 3 is returned | payload: absent "
            "| 20 cases, 2 runs each, pass rate at least 0.95 |\n",
            block,
        )

    def test_cells_escape_pipes_and_line_breaks(self):
        block = self.block_of(first_criterion(record(), tests=[{**ROW, "given": "a | b\nc"}]), "5.1")
        self.assertIn("| `tests/test_app.py` `test_total` | a \\| b c | 3 is returned |", block)

    def test_unproven_block_has_no_table(self):
        source = second_criterion(record(), case_table="refusal", domains=[PAYLOAD])
        block = self.block_of(source, "5.2")
        self.assertEqual(
            block,
            "### 5.2 The total shows on the phone\n\n"
            "The total appears on the phone within a second" + ELLIPSIS + "\n\n"
            + PHONE_SEAM_TEXT + "\n\n"
            + "Cases for a refusal:\n" + PAYLOAD_CASES + "\n\n"
            + "Unproven: needs the phone",
        )
        self.assertNotIn("| Test |", block)

    def test_unproven_block_at_a_runnable_seam_has_no_table(self):
        source = first_criterion(record(), tests=[], unproven="the rate comes from a live exchange")
        self.assertEqual(
            self.block_of(source, "5.1"),
            BLOCK_5_1_HEAD + "Unproven: the rate comes from a live exchange",
        )

    def test_task_carries_the_case_table(self):
        tests = [{**ROW, "covers": ["payload: absent", "payload: present"]}]
        with tempfile.TemporaryDirectory() as folder:
            spec_text, items_text = self.rendered(folder, tabled(record(), "security", tests))
        block = spec_block(spec_text, "5.1")
        task = {step["name"]: step["task"] for step in json.loads(items_text)}["build-app"]
        self.assertEqual(
            block,
            BLOCK_5_1_HEAD
            + "Cases for a security need:\n" + PAYLOAD_CASES + "\n\n"
            + "| Test | Given | Expected | Covers |\n"
            + "|---|---|---|---|\n"
            + "| `tests/test_app.py` `test_total` | a total of 3 | 3 is returned | payload: absent; payload: present |",
        )
        self.assertEqual(task, "Build the app.\n\n" + PROVES + "\n\n" + block)


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
        self.assertEqual(amended_spec, RENDERED_SPEC)
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
            "criteria": ["5.2"],
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
