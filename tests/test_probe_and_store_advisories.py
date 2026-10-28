import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_acceptance_lines as fixtures

ROOT = pathlib.Path(__file__).resolve().parents[1]
STUB = "#!/bin/sh\nexit 0\n"
STUB_NAMES = ("python3", "cat", "make")
MISSING = "missing_tool_xyz"
SEAM = {
    "name": "script-cli",
    "interface": "the scripts run as subprocesses on temporary records",
    "catches": "a wrong exit code or a missing error",
    "misses": "how a person reads the output",
    "builder_runs": True,
}


def load_probe_module():
    spec = importlib.util.spec_from_file_location("surface_probe", str(ROOT / "scripts" / "surface_probe.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def acceptance_line(position, command):
    return {
        "id": "C1.%d" % (position + 1),
        "kind": "exact",
        "surface": {"family": "cli", "target": "python3"},
        "command": command,
        "pass": "the command exits 0",
    }


def record_of(commands):
    return {
        "status": "in-progress",
        "seams": [SEAM],
        "criteria": [
            {
                "number": "5.1",
                "title": "The commands run",
                "text": "WHEN a check runs, THE SYSTEM SHALL find its executables.",
                "seam": "script-cli",
                "acceptance": [acceptance_line(position, command) for position, command in enumerate(commands)],
                "tests": [],
            }
        ],
        "steps": [],
    }


def write_stub(path, mode=0o755):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(STUB, encoding="utf-8")
    os.chmod(str(path), mode)
    return path


class Sandbox:
    def __init__(self, folder):
        self.top = pathlib.Path(folder).resolve()
        self.repo = self.top / "repo"
        self.bin = self.top / "bin"
        self.home = self.top / "home"
        self.outside = self.top / "outside"
        for path in (self.repo, self.bin, self.home, self.outside):
            path.mkdir()
        (self.repo / "web").mkdir()
        self.stubs = {name: str(write_stub(self.bin / name)) for name in STUB_NAMES}
        write_stub(self.outside / "tool")
        write_stub(self.outside / "python-real")
        write_stub(self.repo / "bin" / "run")
        write_stub(self.repo / ".venv" / "bin" / "activate", 0o644)
        (self.repo / ".venv" / "bin" / "python").symlink_to(self.outside / "python-real")

    def probe(self, commands):
        record_path = self.top / "demo.record.json"
        record_path.write_text(json.dumps(record_of(commands)), encoding="utf-8")
        environment = {**fixtures.environment(str(self.home)), "PATH": str(self.bin)}
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "surface_probe.py"), "--record", str(record_path), "--repo",
             str(self.repo), "--timeout", "5"],
            cwd=str(self.repo),
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=fixtures.TIMEOUT,
        )
        stored = json.loads(record_path.read_text(encoding="utf-8"))
        probes = {entry["check"]: entry for entry in stored.get("probes", []) if entry["probe"] == "command"}
        return result, {command: probes.get("C1.%d" % (position + 1)) for position, command in enumerate(commands)}


class ProbeAdvisoriesTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.sandbox = Sandbox(self.folder.name)

    def assert_probes(self, expected):
        result, probes = self.sandbox.probe(tuple(expected))
        self.assertNotIn("Traceback", result.stderr)
        for command, (status, details) in expected.items():
            with self.subTest(command=command):
                entry = probes[command]
                self.assertIsNotNone(entry, result.stdout + result.stderr)
                self.assertEqual(entry["status"], status, entry["detail"])
                if details is not None:
                    self.assertEqual(sorted(entry["detail"].split("; ")), sorted(details), entry["detail"])
        return probes

    def stub(self, *names):
        return [self.sandbox.stubs[name] for name in names]

    def test_redirections_stay_in_their_segment_and_their_words_are_never_probed(self):
        self.assert_probes(
            {
                "python3 -m unittest tests 2>&1 | cat": ("pass", self.stub("python3", "cat")),
                "python3 x >&2": ("pass", self.stub("python3")),
                "python3 x &>/dev/null": ("pass", self.stub("python3")),
                "make test > out.txt": ("pass", self.stub("make")),
                "python3 x >| out.txt": ("pass", self.stub("python3")),
                "python3 x > %s" % MISSING: ("pass", self.stub("python3")),
                "python3 x 2>&1 | %s" % MISSING: ("fail", ["%s is not on PATH" % MISSING]),
            }
        )

    def test_leading_parentheses_assignments_and_reserved_words_are_skipped(self):
        self.assert_probes(
            {
                "( python3 -V )": ("pass", self.stub("python3")),
                "(python3 -V)": ("pass", self.stub("python3")),
                "FOO=1 BAR=2 python3 -V": ("pass", self.stub("python3")),
                "! python3 -V": ("pass", self.stub("python3")),
                "{ python3 -V; }": ("pass", self.stub("python3")),
                "if python3 -V; then make test; fi": ("pass", self.stub("python3", "make")),
                "if true; then %s; fi" % MISSING: ("fail", ["%s is not on PATH" % MISSING]),
                "while python3 -V; do cat x; done": ("pass", self.stub("python3", "cat")),
                "until python3 -V; do cat x; done": ("pass", self.stub("python3", "cat")),
                "for f in a b; do python3 $f; done": ("pass", self.stub("python3")),
                "for f in %s; do python3 $f; done" % MISSING: ("pass", self.stub("python3")),
                "for f in a; do %s; done" % MISSING: ("fail", ["%s is not on PATH" % MISSING]),
                "case x in a) python3 -V;; esac": ("pass", self.stub("python3")),
                "case x in a) python3 -V;; b) %s;; esac" % MISSING: ("fail", ["%s is not on PATH" % MISSING]),
            }
        )

    def test_prefix_commands_probe_the_next_word_that_is_not_an_option_or_assignment(self):
        self.assert_probes(
            {
                "exec python3 -V": ("pass", self.stub("python3")),
                "command -v python3": ("pass", self.stub("python3")),
                "builtin cd web": ("pass", ["cd is a shell builtin"]),
                "eval python3 -V": ("pass", self.stub("python3")),
                "nohup python3 x": ("pass", self.stub("python3")),
                "env -i FOO=1 python3 x": ("pass", self.stub("python3")),
                "time make test": ("pass", self.stub("make")),
                "nohup env FOO=1 python3 x": ("pass", self.stub("python3")),
                "exec %s" % MISSING: ("fail", ["%s is not on PATH" % MISSING]),
                "env FOO=1 %s" % MISSING: ("fail", ["%s is not on PATH" % MISSING]),
                "time %s" % MISSING: ("fail", ["%s is not on PATH" % MISSING]),
            }
        )

    def test_sourced_files_are_probed_as_repository_files(self):
        probes = self.assert_probes(
            {
                "source .venv/bin/activate && python3 -V": ("pass", None),
                ". .venv/bin/activate && python3 -V": ("pass", None),
                "source ./missing.sh": ("fail", None),
                ". ./missing.sh": ("fail", None),
                "source ../outside/tool": ("fail", ["../outside/tool is outside the repository"]),
            }
        )
        self.assertIn(self.sandbox.stubs["python3"], probes["source .venv/bin/activate && python3 -V"]["detail"])
        self.assertIn("./missing.sh", probes["source ./missing.sh"]["detail"])

    def test_posix_builtins_count_as_present(self):
        builtins = (
            "cd web", "export FOO=1", "set -e", "true", "false", "test -f x", "[ -f x ]", "echo hi", "printf x",
            "read x", "shift", "unset FOO", "umask 022", "wait", "exit 0", "return 0", "trap '' INT", "alias x=y",
            "type python3", "ulimit -n",
        )
        expected = {
            command: ("pass", ["%s is a shell builtin" % command.split()[0]]) for command in builtins
        }
        self.assert_probes(
            {
                **expected,
                "cd web && python3 -V": ("pass", ["cd is a shell builtin"] + self.stub("python3")),
                "cd web && %s" % MISSING: ("fail", ["%s is not on PATH" % MISSING]),
            }
        )

    def test_every_segment_is_probed(self):
        failed = ("fail", ["%s is not on PATH" % MISSING])
        self.assert_probes(
            {
                "python3 -V; %s" % MISSING: failed,
                "python3 -V && %s" % MISSING: failed,
                "python3 -V || %s" % MISSING: failed,
                "python3 -V | %s" % MISSING: failed,
                "python3 -V |& %s" % MISSING: failed,
                "python3 -V & %s" % MISSING: failed,
                "python3 -V && make test | cat": ("pass", self.stub("python3", "make", "cat")),
            }
        )

    def test_probe_paths_stay_inside_the_repository(self):
        outside_tool = str(self.sandbox.outside / "tool")
        self.assert_probes(
            {
                outside_tool + " -V": ("fail", ["%s is outside the repository" % outside_tool]),
                "../outside/tool -V": ("fail", ["../outside/tool is outside the repository"]),
                "python3 -V && ../outside/tool": ("fail", ["../outside/tool is outside the repository"]),
                ".venv/bin/python -V": ("pass", [str(self.sandbox.repo / ".venv/bin/python")]),
                "bin/run": ("pass", [str(self.sandbox.repo / "bin/run")]),
                "./bin/missing": ("fail", ["./bin/missing is not an executable file in the repository"]),
            }
        )

    def test_unencodable_words_fail_the_probe_instead_of_crashing(self):
        result, probes = self.sandbox.probe(("python3 -V && run\u0000x", "python3 -V; ./bin\u0000"))
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.returncode, 1, result.stderr)
        for entry in probes.values():
            self.assertEqual(entry["status"], "fail", entry["detail"])
            self.assertNotEqual(entry["detail"], "")
        module = load_probe_module()
        for command in ("python3 -V; sub\ud800/run", "python3 -V && run\ud800"):
            with self.subTest(command=command):
                status, detail = module.run_probe({"command": command}, "command", "python3", self.sandbox.repo, 5)
                self.assertEqual(status, "fail", detail)
                self.assertNotEqual(detail, "")

    def test_single_executable_commands_keep_their_target_and_detail(self):
        probes = self.assert_probes(
            {
                "python3 -m unittest tests": ("pass", self.stub("python3")),
                MISSING + " --flag": ("fail", ["%s is not on PATH" % MISSING]),
                "cd web && python3 -V": ("pass", None),
                "FOO=1 make test": ("pass", self.stub("make")),
            }
        )
        self.assertEqual(probes["cd web && python3 -V"]["target"], "cd")
        self.assertEqual(probes["FOO=1 make test"]["target"], "make")
        self.assertEqual(probes[MISSING + " --flag"]["target"], MISSING)


class StoreReadTest(unittest.TestCase):
    def run_outcomes(self, store):
        with tempfile.TemporaryDirectory() as folder:
            top = pathlib.Path(folder)
            repo = top / "repo"
            home = top / "home"
            repo.mkdir()
            home.mkdir()
            record_path = top / "demo.record.json"
            original = json.dumps(record_of(("python3 -V",)))
            record_path.write_text(original, encoding="utf-8")
            target = store(top)
            environment = {**fixtures.environment(str(home)), "RECEIPTS_TRAJECTORY_STORE": str(target)}
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "outcomes.py"), "--repo", str(repo), "--record",
                 str(record_path)],
                cwd=str(repo),
                env=environment,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=fixtures.TIMEOUT,
            )
            return result, original, record_path.read_text(encoding="utf-8"), os.path.abspath(str(target))

    def test_a_missing_store_reads_as_empty(self):
        result, _, written, path = self.run_outcomes(lambda top: top / "absent" / "trajectories.jsonl")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(written)["outcomes"], {"store": path, "entries": 0, "repeated": []})

    def test_an_unreadable_store_exits_2_without_writing_outcomes(self):
        def folder_store(top):
            path = top / "store-folder"
            path.mkdir()
            return path

        result, original, written, path = self.run_outcomes(folder_store)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("cannot read the trajectory store: " + path, result.stderr.splitlines())
        self.assertEqual(written, original)


class FilesProseTest(unittest.TestCase):
    def test_files_rows_and_record_keys_name_locked_paths_and_probe_state(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        items = (ROOT / "core" / "items.md").read_text(encoding="utf-8")
        self.assertIn(
            "It includes the Step's own test files, except locked paths, which the check-author Step writes.", readme
        )
        self.assertNotIn("It includes the Step's test files.", readme)
        self.assertIn("including its own test files, except locked paths, which the check-author Step writes |", items)
        sentence = next(line for line in items.splitlines() if "exactly these three lists" in line)
        for needle in ("`probes`", "`outcomes`", "`stop`", "`stopped`", "and a `status`:"):
            self.assertIn(needle, sentence, needle)


if __name__ == "__main__":
    unittest.main()
