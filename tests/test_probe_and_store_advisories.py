import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

TIMEOUT = 60
SEAM = {
    "name": "script-cli",
    "interface": "the product driven from the repository root",
    "catches": "a surface that does not behave",
    "misses": "how a person feels about it",
    "builder_runs": True,
}


def script_path(name):
    return pathlib.Path(__file__).resolve().parents[1] / "scripts" / name


def cli_line(position, command):
    return {
        "id": "C1.%d" % (position + 1),
        "kind": "exact",
        "surface": {"family": "cli", "target": "python3"},
        "command": command,
        "pass": "the test passes",
    }


def record_of(commands):
    lines = [cli_line(position, command) for position, command in enumerate(commands)]
    return {
        "status": "in-progress",
        "seams": [SEAM],
        "criteria": [
            {
                "number": "5.1",
                "title": "The total shows",
                "text": "WHEN the app computes a total, THE SYSTEM SHALL show it.",
                "seam": "script-cli",
                "acceptance": lines,
                "tests": [],
            }
        ],
    }


def run(arguments, cwd, env):
    result = subprocess.run(
        [sys.executable] + [str(argument) for argument in arguments],
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    return result.returncode, result.stdout + result.stderr


def made_folder(path):
    path.mkdir(parents=True)
    return path


def path_folder(base):
    folder = made_folder(pathlib.Path(base) / "bin")
    (folder / "python3").symlink_to(sys.executable)
    return folder


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def command_probes(base, commands):
    repository = made_folder(pathlib.Path(base) / "repo")
    home = made_folder(pathlib.Path(base) / "home")
    env = {"HOME": str(home), "PATH": str(path_folder(base)), "PYTHONDONTWRITEBYTECODE": "1"}
    record_path = write_json(pathlib.Path(base) / "demo.record.json", record_of(commands))
    return repository, record_path, env


def probe(repository, record_path, env):
    code, output = run([script_path("surface_probe.py"), "--record", record_path, "--repo", repository], repository, env)
    entries = {entry["check"]: entry for entry in read_json(record_path).get("probes", []) if entry["probe"] == "command"}
    return code, output, entries


class CommandProbeShellWordsTest(unittest.TestCase):
    def test_builtins_and_subshells_before_a_found_executable_pass(self):
        commands = (
            "source .venv/bin/activate && python3 -m unittest tests.test_cli",
            ". ./env && python3 -m unittest tests.test_cli",
            "export X=1; python3 -m unittest tests.test_cli",
            "(cd web; python3 -m unittest tests.test_cli)",
            "cd web && python3 -m unittest tests.test_cli",
            "X=1 python3 -m unittest tests.test_cli | cat",
        )
        with tempfile.TemporaryDirectory() as base:
            repository, record_path, env = command_probes(base, commands)
            env = {**env, "PATH": env["PATH"] + os.pathsep + str(self.cat_folder(base))}
            code, output, entries = probe(repository, record_path, env)
        self.assertEqual(code, 0, output)
        self.assertEqual(len(entries), len(commands), output)
        for check, entry in entries.items():
            self.assertEqual(entry["status"], "pass", entry)

    def test_a_missing_executable_after_a_builtin_fails(self):
        with tempfile.TemporaryDirectory() as base:
            repository, record_path, env = command_probes(base, ("cd web && no-such-tool test",))
            code, output, entries = probe(repository, record_path, env)
        self.assertEqual(code, 1, output)
        entry = entries["C1.1"]
        self.assertEqual(entry["status"], "fail")
        self.assertIn("no-such-tool is not on PATH", entry["detail"])
        self.assertNotIn("cd is not on PATH", entry["detail"])

    def test_a_missing_executable_in_a_later_segment_fails(self):
        with tempfile.TemporaryDirectory() as base:
            repository, record_path, env = command_probes(base, ("python3 -m build && no-such-tool upload",))
            code, output, entries = probe(repository, record_path, env)
        self.assertEqual(code, 1, output)
        entry = entries["C1.1"]
        self.assertEqual(entry["status"], "fail")
        self.assertIn("no-such-tool is not on PATH", entry["detail"])

    def cat_folder(self, base):
        folder = made_folder(pathlib.Path(base) / "tools")
        stub = folder / "cat"
        stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        stub.chmod(0o755)
        return folder


class CommandProbeContainmentTest(unittest.TestCase):
    def test_a_path_outside_the_repository_fails(self):
        commands = ("/bin/sh -c true", "../../../../../../../../../../bin/sh -c true")
        with tempfile.TemporaryDirectory() as base:
            repository, record_path, env = command_probes(base, commands)
            code, output, entries = probe(repository, record_path, env)
        self.assertEqual(code, 1, output)
        for check in ("C1.1", "C1.2"):
            self.assertEqual(entries[check]["status"], "fail", entries[check])
            self.assertIn("outside the repository", entries[check]["detail"])

    def test_an_executable_inside_the_repository_passes(self):
        commands = ("scripts/run.sh", ".venv/bin/python -m unittest")
        with tempfile.TemporaryDirectory() as base:
            repository, record_path, env = command_probes(base, commands)
            script = made_folder(repository / "scripts") / "run.sh"
            script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            script.chmod(0o755)
            (made_folder(repository / ".venv" / "bin") / "python").symlink_to(sys.executable)
            code, output, entries = probe(repository, record_path, env)
        self.assertEqual(code, 0, output)
        for check in ("C1.1", "C1.2"):
            self.assertEqual(entries[check]["status"], "pass", entries[check])


def outcomes_environment(home, store):
    kept = {key: value for key, value in os.environ.items() if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))}
    return {**kept, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1", "RECEIPTS_TRAJECTORY_STORE": str(store)}


def run_outcomes(base, store):
    repository = made_folder(pathlib.Path(base) / "repo")
    home = made_folder(pathlib.Path(base) / "home")
    record = {"status": "in-progress"}
    record_path = write_json(pathlib.Path(base) / "demo.record.json", record)
    code, output = run(
        [script_path("outcomes.py"), "--repo", repository, "--record", record_path],
        repository,
        outcomes_environment(home, store),
    )
    return code, output, read_json(record_path)


class TrajectoryStoreReadTest(unittest.TestCase):
    def test_an_unreadable_store_is_refused(self):
        with tempfile.TemporaryDirectory() as base:
            store = made_folder(pathlib.Path(base) / "store" / "trajectories.jsonl")
            code, output, record = run_outcomes(base, store)
        self.assertEqual(code, 2, output)
        self.assertIn("cannot read the trajectory store: " + os.path.abspath(str(store)), output)
        self.assertEqual(record, {"status": "in-progress"})

    def test_a_missing_store_is_an_empty_store(self):
        with tempfile.TemporaryDirectory() as base:
            store = pathlib.Path(base) / "store" / "trajectories.jsonl"
            code, output, record = run_outcomes(base, store)
        self.assertEqual(code, 0, output)
        self.assertEqual(record["outcomes"]["entries"], 0)
        self.assertEqual(record["outcomes"]["repeated"], [])


if __name__ == "__main__":
    unittest.main()
