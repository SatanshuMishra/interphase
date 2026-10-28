import json
import os
import pathlib
import resource
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_check_author_lane

TIMEOUT = 60
FILE_SIZE_LIMIT = 1024


def repository_root():
    return pathlib.Path(__file__).resolve().parent.parent


def script_path(name):
    return str(repository_root() / "scripts" / name)


def limit_file_size():
    resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_SIZE_LIMIT, FILE_SIZE_LIMIT))


def run(arguments, base, limited):
    home = pathlib.Path(base) / "home"
    home.mkdir(exist_ok=True)
    environment = dict(
        os.environ,
        HOME=str(home),
        RECEIPTS_TRAJECTORY_STORE=str(pathlib.Path(base) / "absent.jsonl"),
        PYTHONDONTWRITEBYTECODE="1",
    )
    result = subprocess.run(
        [sys.executable] + [str(argument) for argument in arguments],
        cwd=base,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        preexec_fn=limit_file_size if limited else None,
    )
    return result.returncode, result.stdout + result.stderr


def with_first_text(suffix):
    record = test_check_author_lane.complete_record()
    first = dict(record["criteria"][0], text=record["criteria"][0]["text"] + suffix)
    return dict(record, criteria=[first] + list(record["criteria"][1:]))


def padded_record():
    return with_first_text(" pad" * 800)


def surrogate_record():
    return with_first_text("\udc80")


def record_commands(base, record_path):
    return {
        "surface_probe.py": [script_path("surface_probe.py"), "--record", record_path, "--repo", base],
        "outcomes.py": [script_path("outcomes.py"), "--repo", base, "--record", record_path],
    }


def listing(folder):
    return sorted(os.listdir(folder))


class RecordWriteTest(unittest.TestCase):
    def assert_left_whole(self, folder, path, before, names, code, output, message):
        self.assertEqual(code, 2, output)
        self.assertIn(message + str(path), output)
        self.assertNotIn("Traceback", output)
        self.assertEqual(pathlib.Path(path).read_bytes(), before)
        self.assertEqual(listing(folder), names)

    def test_a_failed_record_rewrite_leaves_the_record_whole(self):
        cases = (("file size limit", padded_record(), True), ("unencodable text", surrogate_record(), False))
        for label, record, limited in cases:
            for name in ("surface_probe.py", "outcomes.py"):
                with self.subTest(case=label, script=name), tempfile.TemporaryDirectory() as base:
                    records = pathlib.Path(base) / "records"
                    records.mkdir()
                    record_path = records / "demo.record.json"
                    record_path.write_text(json.dumps(record), encoding="utf-8")
                    before = record_path.read_bytes()
                    names = listing(records)
                    code, output = run(record_commands(base, record_path)[name], base, limited)
                    self.assert_left_whole(records, record_path, before, names, code, output, "cannot write: ")

    def test_a_failed_spec_rewrite_leaves_the_spec_whole(self):
        with tempfile.TemporaryDirectory() as base:
            specs = pathlib.Path(base) / "docs" / "specs"
            specs.mkdir(parents=True)
            spec_path = specs / "demo.md"
            spec_path.write_text(
                (repository_root() / "core" / "templates" / "spec-feature.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            record_path = pathlib.Path(base) / "demo.record.json"
            record_path.write_text(json.dumps(padded_record()), encoding="utf-8")
            before = spec_path.read_bytes()
            names = listing(specs)
            arguments = [
                script_path("render_record.py"),
                "--record", record_path,
                "--spec", spec_path,
                "--items", specs / "demo.items.json",
            ]
            code, output = run(arguments, base, True)
            self.assert_left_whole(specs, spec_path, before, names, code, output, "cannot write: ")

    def test_a_failed_snapshot_rewrite_leaves_the_snapshot_whole(self):
        with tempfile.TemporaryDirectory() as base:
            repo = pathlib.Path(base) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            for index in range(60):
                (repo / ("untracked-file-with-a-long-name-%03d.txt" % index)).write_text("x\n", encoding="utf-8")
            snapshots = pathlib.Path(base) / "snapshots"
            snapshots.mkdir()
            snapshot = snapshots / "snapshot.json"
            snapshot.write_text("{\"previous\": true}\n", encoding="utf-8")
            before = snapshot.read_bytes()
            names = listing(snapshots)
            code, output = run(
                [script_path("tree_guard.py"), "snapshot", "--repo", repo, "--out", snapshot], base, True
            )
            self.assert_left_whole(
                snapshots, snapshot, before, names, code, output, "cannot write snapshot: "
            )


if __name__ == "__main__":
    unittest.main()
