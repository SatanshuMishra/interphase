import itertools
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SYSTEM_PYTHON = "/usr/bin/python3"
VERSION_PREFIX = "Python 3.9"
RECORD_TESTS = ("tests.test_record_inputs", "tests.test_check_record", "tests.test_render_record", "tests.test_check_items")


def reports_3_9(candidate):
    try:
        done = subprocess.run([candidate, "--version"], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    version = (done.stdout or done.stderr).strip()
    return done.returncode == 0 and version.startswith(VERSION_PREFIX)


def python_3_9(candidates):
    return next((candidate for candidate in candidates if reports_3_9(candidate)), None)


def default_candidates():
    found = shutil.which("python3.9")
    return (SYSTEM_PYTHON,) + ((found,) if found else ())


def write_script(folder, name, body):
    path = os.path.join(folder, name)
    pathlib.Path(path).write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
    os.chmod(path, 0o755)
    return path


class PythonThreeNineTest(unittest.TestCase):
    def test_record_tests_pass_on_python_3_9(self):
        interpreter = python_3_9(default_candidates())
        if interpreter is None:
            self.skipTest("no Python 3.9 at /usr/bin/python3 or as python3.9 on PATH")
        if reports_3_9(SYSTEM_PYTHON):
            self.assertEqual(interpreter, SYSTEM_PYTHON)
        done = subprocess.run(
            [interpreter, "-m", "unittest"] + list(RECORD_TESTS),
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_lookup_finds_only_an_interpreter_that_reports_3_9(self):
        with tempfile.TemporaryDirectory() as folder:
            wanted = write_script(folder, "python-3-9", "echo 'Python 3.9.6' >&2")
            newer = write_script(folder, "python-3-12", "echo 'Python 3.12.1'")
            failing = write_script(folder, "python-failing", "echo 'Python 3.9.6'\nexit 1")
            absent = os.path.join(folder, "python-absent")
            others = (newer, failing, absent)
            found = tuple(
                (order, python_3_9(order)) for order in itertools.permutations((wanted,) + others)
            )
            missed = tuple((order, python_3_9(order)) for order in itertools.permutations(others))
        for order, result in found:
            self.assertEqual(result, wanted, order)
        for order, result in missed:
            self.assertIsNone(result, order)


if __name__ == "__main__":
    unittest.main()
