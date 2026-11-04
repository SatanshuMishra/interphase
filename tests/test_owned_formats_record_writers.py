import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

H11_FILE = "h11-interphase-record.schema.json"
REFUSED = 2
UNKNOWN_SEAM = "no-such-seam"
UNKNOWN_SEAM_MESSAGE = "criterion 5.1 names unknown seam 'no-such-seam'"
AMENDMENT_MESSAGE = "step 'build-a' has amendment that is not an integer of at least 1"
CLAUDE_STUB = "#!/bin/sh\nexit 0\n"
NOT_AN_ID_PROBE = {
    "check": "not-an-id",
    "probe": "command",
    "target": "python3",
    "status": "pass",
    "detail": "/usr/bin/python3",
}


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixtures():
    tests = repository_root() / "tests"
    lane = load_path("owned_formats_record_writers_lane", tests / "test_check_author_lane.py")
    kinds = load_path("owned_formats_record_writers_kinds", tests / "test_outcome_kinds.py")
    return lane.complete_record(), kinds.SPEC_WITHOUT_KIND


def script_path(name):
    return repository_root() / "scripts" / name


def path_folder(base):
    folder = base / "bin"
    folder.mkdir()
    (folder / "python3").symlink_to(sys.executable)
    stub = folder / "claude"
    stub.write_text(CLAUDE_STUB, encoding="utf-8")
    stub.chmod(0o755)
    return folder


def inherited_environment(home, store):
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
    }
    return {**kept, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1", "RECEIPTS_TRAJECTORY_STORE": str(store)}


def run(arguments, cwd, env):
    return subprocess.run(
        [sys.executable] + [str(argument) for argument in arguments],
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def with_step_amendment(record, position, amendment):
    steps = record["steps"]
    changed = {**steps[position], "amendment": amendment}
    return {**record, "steps": list(steps[:position]) + [changed] + list(steps[position + 1 :])}


def with_first_seam(record, seam):
    criteria = record["criteria"]
    return {**record, "criteria": [{**criteria[0], "seam": seam}] + list(criteria[1:])}


def with_extra_probe(record, entry):
    return {**record, "probes": list(record["probes"]) + [entry]}


def lines_with(text, words):
    return [line for line in text.splitlines() if all(word in line for word in words)]


def output_of(result):
    return result.stdout + result.stderr


class Workspace:
    def __init__(self, record, spec_text):
        self.record = record
        self.spec_text = spec_text

    def __enter__(self):
        self.temporary = tempfile.TemporaryDirectory()
        base = pathlib.Path(self.temporary.name).resolve()
        self.folder = base / "demo"
        self.folder.mkdir()
        self.home = base / "home"
        self.home.mkdir()
        self.bin = path_folder(base)
        self.store = base / "absent" / "trajectories.jsonl"
        (self.folder / "demo.md").write_text(self.spec_text, encoding="utf-8")
        self.record_path = self.folder / "demo.record.json"
        self.record_path.write_text(json.dumps(self.record), encoding="utf-8")
        self.before = self.record_path.read_bytes()
        return self

    def __exit__(self, *details):
        self.temporary.cleanup()
        return False

    def surface_probe(self):
        return run(
            [script_path("surface_probe.py"), "--record", self.record_path, "--repo", self.folder],
            self.folder,
            {"HOME": str(self.home), "PATH": str(self.bin), "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def outcomes(self):
        return run(
            [script_path("outcomes.py"), "--repo", self.folder, "--record", self.record_path],
            self.folder,
            inherited_environment(self.home, self.store),
        )

    def after(self):
        return self.record_path.read_bytes()


class RecordWritersGateTest(unittest.TestCase):
    def assert_refused(self, workspace, result):
        self.assertEqual(result.returncode, REFUSED, output_of(result))
        self.assertEqual(workspace.after(), workspace.before, output_of(result))

    def test_surface_probe_validates_the_record_before_rewriting_it(self):
        record, spec_text = fixtures()
        with Workspace(with_step_amendment(record, 0, 0), spec_text) as workspace:
            result = workspace.surface_probe()
            self.assert_refused(workspace, result)
        self.assertNotEqual(
            lines_with(result.stderr, ("demo.record.json", H11_FILE, "#/steps/0/amendment")), [], output_of(result)
        )
        with Workspace(with_first_seam(record, UNKNOWN_SEAM), spec_text) as workspace:
            result = workspace.surface_probe()
            self.assert_refused(workspace, result)
        self.assertNotEqual(lines_with(result.stderr, (UNKNOWN_SEAM_MESSAGE,)), [], output_of(result))
        self.assertEqual(lines_with(result.stderr, (H11_FILE,)), [], output_of(result))
        with Workspace(record, spec_text) as workspace:
            result = workspace.surface_probe()
            self.assertEqual(result.returncode, 0, output_of(result))
            self.assertNotEqual(workspace.after(), workspace.before, output_of(result))
            written = json.loads(workspace.after().decode("utf-8"))
        probes = written.get("probes")
        self.assertIsInstance(probes, list, written)
        self.assertNotEqual(probes, [], written)
        self.assertEqual([entry.get("status") for entry in probes], ["pass"] * len(probes), probes)

    def test_outcomes_validates_the_record_before_rewriting_it(self):
        record, spec_text = fixtures()
        with Workspace(with_extra_probe(record, NOT_AN_ID_PROBE), spec_text) as workspace:
            result = workspace.outcomes()
            self.assert_refused(workspace, result)
        self.assertNotEqual(
            lines_with(result.stderr, ("demo.record.json", H11_FILE, "#/probes/3/check")), [], output_of(result)
        )
        with Workspace(with_step_amendment(record, 0, 0), spec_text) as workspace:
            result = workspace.outcomes()
            self.assert_refused(workspace, result)
        self.assertNotEqual(lines_with(result.stderr, ("#/steps/0/amendment",)), [], output_of(result))
        self.assertNotEqual(lines_with(result.stderr, (AMENDMENT_MESSAGE,)), [], output_of(result))
        with Workspace(with_first_seam(record, UNKNOWN_SEAM), spec_text) as workspace:
            result = workspace.outcomes()
            self.assert_refused(workspace, result)
        self.assertNotEqual(lines_with(result.stderr, (UNKNOWN_SEAM_MESSAGE,)), [], output_of(result))
        self.assertEqual(lines_with(result.stderr, (H11_FILE,)), [], output_of(result))
        with Workspace(record, spec_text) as workspace:
            result = workspace.outcomes()
            self.assertEqual(result.returncode, 0, output_of(result))
            self.assertNotEqual(workspace.after(), workspace.before, output_of(result))
            written = json.loads(workspace.after().decode("utf-8"))
            store = str(workspace.store)
        outcomes = written.get("outcomes")
        self.assertIsInstance(outcomes, dict, written)
        self.assertEqual(outcomes.get("entries"), 0, outcomes)
        self.assertEqual(outcomes.get("repeated"), [], outcomes)
        self.assertEqual(outcomes.get("store"), store, outcomes)


if __name__ == "__main__":
    unittest.main()
