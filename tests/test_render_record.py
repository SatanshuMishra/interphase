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
BLOCK_7_1 = (
    "### 7.1 The total adds up\n\n"
    "Given a total, when the app returns it, then it is unchanged.\n\n"
    "Where passing proves it: python3 -m unittest on macOS.\n\n"
    "- `tests/test_app.py` `test_total`: the total adds up Runs in: python3 -m unittest on macOS."
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
                "tests": [
                    {
                        "file": "tests/test_app.py",
                        "name": "test_total",
                        "asserts": "the total adds up",
                        "env": "unit-tests",
                        "step": "build-app",
                    }
                ],
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


class RenderRecordTest(unittest.TestCase):
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

    def run_main(self, folder):
        module = self.load("render_record")
        out = io.StringIO()
        err = io.StringIO()
        previous = os.getcwd()
        os.chdir(folder)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = module.main(list(ARGV))
        finally:
            os.chdir(previous)
        return code, out.getvalue(), err.getvalue()

    def rendered(self, folder, source, spec_text=SPEC_TEXT):
        self.write_fixture(folder, source, spec_text)
        code, out, err = self.run_main(folder)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(out.splitlines(), ["wrote " + SPEC_PATH, "wrote " + ITEMS_PATH])
        base = pathlib.Path(folder)
        return (base / SPEC_PATH).read_bytes().decode("utf-8"), (base / ITEMS_PATH).read_bytes().decode("utf-8")

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


if __name__ == "__main__":
    unittest.main()
