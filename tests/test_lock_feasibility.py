import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import unittest

TIMEOUT = 120
ROW_FILE = "tests/test_total_new.py"
ROW_NAME = "test_total_counts_every_line"
STEP = "build-total"
EARLIER_STEP = "build-new"
TOTAL = "src/total.py"
NEW_TOTAL = "src/new_total.py"
NEW_DATA = "src/new_data.json"
OLD_TEST = "tests/test_total_old.py"
HEAD_FILES = (
    (TOTAL, 'print("total 3")\n'),
    (OLD_TEST, "import src.total\n"),
)
EDITED_TOTAL = 'print("total 4")\n'
SEAM = {
    "name": "script-cli",
    "interface": "the total script run as a subprocess",
    "catches": "a wrong total or exit code",
    "misses": "how a person reads the total",
    "builder_runs": True,
}
LINE = {
    "id": "C1.1",
    "kind": "exact",
    "surface": {"family": "cli", "target": "python3"},
    "command": "python3 -m unittest tests.test_total_new",
    "pass": "the test passes",
}
PROBE = {"check": "C1.1", "probe": "command", "target": "python3", "status": "pass", "detail": "/usr/bin/python3"}
OUTCOMES = {"store": "/var/empty/trajectories.jsonl", "entries": 0, "repeated": []}
OLD_TEST_UNAFFECTED = {"file": OLD_TEST, "reason": "it only checks that the total module imports"}
USAGE_PARTS = ("lock_feasibility.py", "--record", "--repo")
CHANGED_SINCE = "the record changed since lock_feasibility.py ran"
AMENDMENT_STEP = "build-extra"
EXTRA = "src/extra.py"
ADDED_NAME = "test_total_counts"
LOCKED_TEST = "import unittest\n\n\nclass Total(unittest.TestCase):\n    def %s(self):\n        pass\n" % ROW_NAME
BUILT_BEFORE = "built before amendment"
ALREADY_PASSING = "already passing on today's code"


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def script_path(name):
    return repository_root() / "scripts" / name


def python_command(*arguments):
    return " ".join(shlex.quote(argument) for argument in (sys.executable,) + arguments)


PRINTS_TOTAL = python_command(TOTAL)
WAITS_FOR_INPUT = python_command("-c", "import sys; sys.stdin.read(); print('closed')")


def row(loads, needs, absent=None):
    base = {
        "file": ROW_FILE,
        "name": ROW_NAME,
        "given": "a list of three lines",
        "expect": "the total counts three lines",
        "step": STEP,
        "check": "C1.1",
        "loads": list(loads),
        "needs": list(needs),
    }
    return {**base, "absent": dict(absent)} if absent is not None else base


def step(name, files, after=()):
    base = {"name": name, "files": list(files), "criteria": ["5.1"], "task": "Build %s." % name}
    return {**base, "after": list(after)} if after else base


def record(test_row, steps, unaffected=(OLD_TEST_UNAFFECTED,)):
    base = {
        "status": "in-progress",
        "seams": [dict(SEAM)],
        "criteria": [
            {
                "number": "5.1",
                "title": "The total counts every line",
                "text": "WHEN the total script reads a list, THE SYSTEM SHALL print how many lines it holds.",
                "seam": "script-cli",
                "acceptance": [dict(LINE)],
                "tests": [test_row],
            }
        ],
        "steps": [dict(entry) for entry in steps],
        "locked": [ROW_FILE],
        "probes": [dict(PROBE)],
        "outcomes": dict(OUTCOMES),
    }
    return {**base, "unaffected": [dict(entry) for entry in unaffected]} if unaffected else base


def existing_row(absent=None):
    return row([TOTAL], [TOTAL], absent)


def total_absent(shows="total 3", command=PRINTS_TOTAL):
    return {"command": command, "shows": shows}


def feasible_record():
    return record(existing_row(total_absent()), [step(STEP, [TOTAL])])


def lines_with(output, *parts):
    return [line for line in output.splitlines() if all(part in line for part in parts)]


def named_lines(output, *parts):
    return [line for line in lines_with(output, *parts) if not line.startswith("pass")]


def failure_lines(output, *parts):
    return [line for line in lines_with(output, *parts) if line.startswith("fail")]


def results(stored):
    feasibility = stored.get("feasibility")
    return feasibility.get("results", []) if isinstance(feasibility, dict) else []


class FeasibilityCase(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = pathlib.Path(holder.name)
        self.home = self.root / "home"
        self.temporary = self.root / "tmp"
        self.repo = self.root / "repo"
        for folder in (self.home, self.temporary, self.repo):
            folder.mkdir()

    def environment(self):
        kept = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
        }
        return {
            **kept,
            "HOME": str(self.home),
            "TMPDIR": str(self.temporary),
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CEILING_DIRECTORIES": str(self.root),
        }

    def git(self, *arguments):
        return subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "-c",
                "user.name=Interphase Test",
                "-c",
                "user.email=test@example.invalid",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "core.hooksPath=" + os.devnull,
            ]
            + list(arguments),
            env=self.environment(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=True,
        )

    def write(self, relative, text):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def make_repository(self, extra=(), commit=True, files=HEAD_FILES):
        self.git("init", "-q")
        for relative, text in tuple(files) + tuple(extra):
            self.write(relative, text)
        if commit:
            self.git("add", "-A")
            self.git("commit", "-q", "-m", "base")

    def write_record(self, entry, folder=None):
        specs = (folder if folder is not None else self.repo) / "docs" / "specs"
        specs.mkdir(parents=True, exist_ok=True)
        path = specs / "demo.record.json"
        path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        return path

    def stored(self, path):
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))

    def run_script(self, arguments, stdin=subprocess.DEVNULL):
        try:
            result = subprocess.run(
                [sys.executable] + [str(argument) for argument in arguments],
                cwd=str(self.repo),
                env=self.environment(),
                stdin=stdin,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return None, "still waiting after %d seconds" % TIMEOUT
        return result.returncode, result.stdout + result.stderr

    def feasibility(self, record_path, extra=(), stdin=subprocess.DEVNULL, repo=None):
        target = repo if repo is not None else self.repo
        return self.run_script(
            [script_path("lock_feasibility.py"), "--record", record_path, "--repo", target] + list(extra),
            stdin=stdin,
        )

    def complete_check(self, record_path):
        return self.run_script([script_path("check_record.py"), "--complete", record_path])

    def checked(self, entry, extra=()):
        self.make_repository(extra)
        path = self.write_record(entry)
        code, output = self.feasibility(path)
        return code, output, path


class LoadAndNeedTest(FeasibilityCase):
    def test_a_load_missing_at_head_and_written_by_no_step_is_refused(self):
        entry = record(row([NEW_TOTAL], [TOTAL]), [step(STEP, [TOTAL])])
        code, output, path = self.checked(entry)
        self.assertEqual(code, 1, output)
        self.assertTrue(named_lines(output, ROW_FILE, ROW_NAME, NEW_TOTAL), output)
        complete, complete_output = self.complete_check(path)
        self.assertEqual(complete, 1, complete_output)

    def test_a_load_written_by_an_earlier_step_passes(self):
        entry = record(
            row([NEW_TOTAL], [NEW_TOTAL]),
            [step(EARLIER_STEP, [NEW_TOTAL]), step(STEP, ["src/new_report.py"], after=[EARLIER_STEP])],
        )
        code, output, path = self.checked(entry)
        self.assertEqual(code, 0, output)
        passed = [
            result
            for result in results(self.stored(path))
            if result.get("check") == "loads" and result.get("status") == "pass" and NEW_TOTAL in result.get("subject", "")
        ]
        self.assertTrue(passed, self.stored(path).get("feasibility"))

    def test_a_need_outside_every_write_set_is_refused(self):
        entry = record(row([NEW_TOTAL], [TOTAL]), [step(STEP, [NEW_TOTAL])])
        code, output, path = self.checked(entry)
        self.assertEqual(code, 1, output)
        self.assertTrue(named_lines(output, ROW_NAME, TOTAL), output)
        complete, complete_output = self.complete_check(path)
        self.assertEqual(complete, 1, complete_output)


class AbsenceTest(FeasibilityCase):
    def test_a_row_whose_behaviour_already_exists_is_refused(self):
        entry = record(existing_row(total_absent("total 3", "echo total 4")), [step(STEP, [TOTAL])])
        code, output, _ = self.checked(entry)
        self.assertEqual(code, 1, output)
        self.assertTrue(named_lines(output, ROW_NAME, "already passing on today's code"), output)

    def test_a_row_with_absent_evidence_passes(self):
        code, output, path = self.checked(feasible_record())
        self.assertEqual(code, 0, output)
        passed = [
            result
            for result in results(self.stored(path))
            if result.get("check") == "absent" and result.get("status") == "pass" and ROW_NAME in result.get("subject", "")
        ]
        self.assertTrue(passed, self.stored(path).get("feasibility"))

    def test_a_row_loading_only_existing_files_without_absent_is_refused(self):
        entry = record(existing_row(), [step(STEP, [TOTAL])])
        code, output, _ = self.checked(entry)
        self.assertEqual(code, 1, output)
        self.assertTrue(named_lines(output, ROW_NAME, "no absent"), output)

    def test_a_row_loading_a_new_file_needs_no_absent(self):
        entry = record(row([NEW_TOTAL], [NEW_TOTAL]), [step(STEP, [NEW_TOTAL])])
        code, output, _ = self.checked(entry)
        self.assertEqual(code, 0, output)

    def test_a_new_need_the_test_never_loads_still_needs_absent(self):
        entry = record(row([TOTAL], [TOTAL, NEW_DATA]), [step(STEP, [TOTAL, NEW_DATA])])
        code, output, _ = self.checked(entry)
        self.assertEqual(code, 1, output)
        self.assertTrue(named_lines(output, ROW_NAME, "no absent"), output)

    def test_the_absent_command_runs_on_committed_head(self):
        self.make_repository()
        edited = self.write(TOTAL, EDITED_TOTAL)
        path = self.write_record(feasible_record())
        code, output = self.feasibility(path)
        self.assertEqual(code, 0, output)
        self.assertEqual(edited.read_text(encoding="utf-8"), EDITED_TOTAL)

    def test_commands_get_no_input(self):
        entry = record(existing_row(total_absent("closed", WAITS_FOR_INPUT)), [step(STEP, [TOTAL])])
        self.make_repository()
        path = self.write_record(entry)
        reader, writer = os.pipe()
        try:
            code, output = self.feasibility(path, stdin=reader)
        finally:
            os.close(writer)
            os.close(reader)
        self.assertEqual(code, 0, output)
        for option in (("--timeout", "30"), ("--unattended",)):
            with self.subTest(option=option[0]):
                refused, refused_output = self.feasibility(path, extra=option)
                self.assertEqual(refused, 2, refused_output)
                usage = [line for line in lines_with(refused_output, *USAGE_PARTS) if line.startswith("usage:")]
                self.assertTrue(usage, refused_output)


class ExistingTestTest(FeasibilityCase):
    def test_an_existing_test_of_a_changed_file_must_be_owned_or_unaffected(self):
        entry = record(existing_row(total_absent()), [step(STEP, [TOTAL])], unaffected=())
        code, output, _ = self.checked(entry)
        self.assertEqual(code, 1, output)
        self.assertTrue(named_lines(output, OLD_TEST, TOTAL), output)

    def test_a_test_naming_a_changed_file_by_its_file_name_is_a_candidate(self):
        named = "tests/test_total_name.py"
        code, output, _ = self.checked(feasible_record(), extra=((named, 'TOTAL = script_path("total.py")\n'),))
        self.assertEqual(code, 1, output)
        self.assertTrue(named_lines(output, named), output)

    def test_a_python_from_import_is_a_candidate(self):
        imported = "tests/test_total_from.py"
        code, output, _ = self.checked(feasible_record(), extra=((imported, "from src import total\n"),))
        self.assertEqual(code, 1, output)
        self.assertTrue(named_lines(output, imported), output)

    def test_an_unaffected_entry_clears_the_existing_test(self):
        code, output, _ = self.checked(feasible_record())
        self.assertEqual(code, 0, output)

    def test_an_owned_existing_test_clears_itself(self):
        entry = record(existing_row(total_absent()), [step(STEP, [TOTAL, OLD_TEST])], unaffected=())
        code, output, _ = self.checked(entry)
        self.assertEqual(code, 0, output)

    def test_a_meta_test_whose_glob_matches_a_new_file_is_a_candidate(self):
        census = "tests/test_census.py"
        entry = record(row([NEW_TOTAL], [NEW_TOTAL]), [step(STEP, [NEW_TOTAL])])
        code, output, _ = self.checked(entry, extra=((census, 'PATTERN = "src/*.py"\n'),))
        self.assertEqual(code, 1, output)
        self.assertTrue(named_lines(output, census, NEW_TOTAL), output)

    def test_a_test_of_an_unchanged_file_is_no_candidate(self):
        other = "tests/test_other.py"
        extra = (("src/other.py", 'print("other")\n'), (other, "import src.other\n"))
        code, output, path = self.checked(feasible_record(), extra=extra)
        self.assertEqual(code, 0, output)
        self.assertEqual(failure_lines(output, other), [], output)
        failed = [
            result
            for result in results(self.stored(path))
            if result.get("status") != "pass" and other in result.get("subject", "")
        ]
        self.assertIn("feasibility", self.stored(path))
        self.assertEqual(failed, [])


class StoredResultTest(FeasibilityCase):
    def test_a_locked_record_without_feasibility_is_refused(self):
        path = self.write_record(feasible_record())
        code, output = self.complete_check(path)
        self.assertEqual(code, 1, output)
        self.assertIn("lock_feasibility.py", output)

    def test_an_edit_after_the_run_is_refused(self):
        code, output, path = self.checked(feasible_record())
        self.assertEqual(code, 0, output)
        stored = self.stored(path)
        grown = [{**stored["steps"][0], "files": stored["steps"][0]["files"] + ["src/extra.py"]}]
        path.write_text(json.dumps({**stored, "steps": grown + stored["steps"][1:]}, indent=2), encoding="utf-8")
        complete, complete_output = self.complete_check(path)
        self.assertEqual(complete, 1, complete_output)
        self.assertIn(CHANGED_SINCE, complete_output)

    def test_a_fresh_passing_run_is_accepted(self):
        code, output, path = self.checked(feasible_record())
        self.assertEqual(code, 0, output)
        complete, complete_output = self.complete_check(path)
        self.assertEqual(complete, 0, complete_output)

    def test_a_record_without_locked_needs_no_feasibility(self):
        unproven = {
            "status": "in-progress",
            "seams": [
                {
                    "name": "phone-screen",
                    "interface": "the total shown on the user's phone",
                    "catches": "a wrong total on the screen",
                    "misses": "nothing the phone shows",
                    "builder_runs": False,
                }
            ],
            "criteria": [
                {
                    "number": "5.1",
                    "title": "The phone shows the total",
                    "text": "WHEN the phone opens the total, THE SYSTEM SHALL show it.",
                    "seam": "phone-screen",
                    "tests": [],
                    "unproven": "only the user's phone shows the total",
                }
            ],
            "steps": [step(STEP, [TOTAL])],
            "outcomes": dict(OUTCOMES),
        }
        self.make_repository(files=(("README.md", "# Total\n"),))
        path = self.write_record(unproven)
        complete, complete_output = self.complete_check(path)
        self.assertEqual(complete, 0, complete_output)
        code, output = self.feasibility(path)
        self.assertEqual(code, 0, output)
        failed = [result for result in results(self.stored(path)) if result.get("status") != "pass"]
        self.assertEqual(failed, [])

    def test_an_unborn_head_counts_as_an_empty_tree(self):
        entry = record(row([NEW_TOTAL], [NEW_TOTAL]), [step(STEP, [NEW_TOTAL])], unaffected=())
        self.make_repository(commit=False)
        path = self.write_record(entry)
        code, output = self.feasibility(path)
        self.assertEqual(code, 0, output)
        stored = results(self.stored(path))
        self.assertTrue(stored, self.stored(path).get("feasibility"))
        self.assertEqual([result for result in stored if result.get("status") != "pass"], [])

    def test_a_folder_outside_git_exits_2(self):
        folder = self.root / "plain"
        folder.mkdir()
        path = self.write_record(feasible_record(), folder=folder)
        code, output = self.feasibility(path, repo=folder)
        self.assertEqual(code, 2, output)
        named = (str(folder), os.path.realpath(str(folder)))
        self.assertTrue(any(name in output for name in named), output)


def amendment_step(number=1, name=AMENDMENT_STEP, after=(STEP,)):
    return {**step(name, [EXTRA], after=after), "amendment": number}


def added_row(step_name=AMENDMENT_STEP, absent=None):
    return {**row([NEW_TOTAL], [EXTRA], absent), "name": ADDED_NAME, "step": step_name}


class AmendmentTest(FeasibilityCase):
    def build(self, files):
        for relative, text in files:
            self.write(relative, text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "build")

    def amend(self, path, steps, rows=()):
        stored = self.stored(path)
        first = stored["criteria"][0]
        criteria = [{**first, "tests": first["tests"] + [dict(entry) for entry in rows]}] + stored["criteria"][1:]
        amended = {**stored, "criteria": criteria, "steps": stored["steps"] + [dict(entry) for entry in steps]}
        path.write_text(json.dumps(amended, indent=2), encoding="utf-8")

    def built_new_file_record(self):
        code, output, path = self.checked(record(row([NEW_TOTAL], [NEW_TOTAL]), [step(STEP, [NEW_TOTAL])]))
        self.assertEqual(code, 0, output)
        self.build(((NEW_TOTAL, EDITED_TOTAL), (ROW_FILE, LOCKED_TEST)))
        return path

    def test_a_row_an_earlier_step_built_passes_when_an_amendment_adds_a_step(self):
        path = self.built_new_file_record()
        self.amend(path, [amendment_step()])
        code, output = self.feasibility(path)
        self.assertEqual(code, 0, output)
        self.assertTrue(lines_with(output, "pass", ROW_NAME, BUILT_BEFORE + " 1"), output)
        complete, complete_output = self.complete_check(path)
        self.assertEqual(complete, 0, complete_output)

    def test_a_built_row_with_absent_evidence_passes_when_an_amendment_adds_a_step(self):
        code, output, path = self.checked(feasible_record())
        self.assertEqual(code, 0, output)
        self.build(((TOTAL, EDITED_TOTAL), (ROW_FILE, LOCKED_TEST)))
        self.amend(path, [amendment_step()])
        code, output = self.feasibility(path)
        self.assertEqual(code, 0, output)
        self.assertEqual(failure_lines(output, ALREADY_PASSING), [], output)
        complete, complete_output = self.complete_check(path)
        self.assertEqual(complete, 0, complete_output)

    def test_a_row_the_amendment_adds_is_still_judged(self):
        path = self.built_new_file_record()
        self.amend(path, [amendment_step()], rows=[added_row()])
        code, output = self.feasibility(path)
        self.assertEqual(code, 1, output)
        self.assertTrue(failure_lines(output, ADDED_NAME, "no absent"), output)
        self.assertEqual(failure_lines(output, ROW_NAME), [], output)

    def test_a_row_no_build_delivered_is_still_judged_at_an_amendment(self):
        entry = record(existing_row(total_absent("total 3", "echo total 4")), [step(STEP, [TOTAL]), amendment_step()])
        code, output, _ = self.checked(entry)
        self.assertEqual(code, 1, output)
        self.assertTrue(failure_lines(output, ROW_NAME, ALREADY_PASSING), output)

    def test_a_record_with_no_amendment_is_judged_though_its_rows_test_is_at_head(self):
        entry = record(existing_row(), [step(STEP, [TOTAL])])
        code, output, _ = self.checked(entry, extra=((ROW_FILE, LOCKED_TEST),))
        self.assertEqual(code, 1, output)
        self.assertTrue(failure_lines(output, ROW_NAME, "no absent"), output)

    def test_an_earlier_amendments_row_whose_test_is_not_written_is_still_judged(self):
        path = self.built_new_file_record()
        later = amendment_step(2, "build-more", after=(AMENDMENT_STEP,))
        self.amend(path, [amendment_step(), {**later, "files": ["src/more.py"]}], rows=[added_row()])
        code, output = self.feasibility(path)
        self.assertEqual(code, 1, output)
        self.assertTrue(failure_lines(output, ADDED_NAME, "no absent"), output)

    def test_an_amendment_number_changed_after_the_run_is_refused(self):
        path = self.built_new_file_record()
        self.amend(path, [amendment_step()])
        code, output = self.feasibility(path)
        self.assertEqual(code, 0, output)
        stored = self.stored(path)
        renumbered = stored["steps"][:-1] + [{**stored["steps"][-1], "amendment": 2}]
        path.write_text(json.dumps({**stored, "steps": renumbered}, indent=2), encoding="utf-8")
        complete, complete_output = self.complete_check(path)
        self.assertEqual(complete, 1, complete_output)
        self.assertIn(CHANGED_SINCE, complete_output)


if __name__ == "__main__":
    unittest.main()
