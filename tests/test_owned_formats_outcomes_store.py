import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

K6_FILE = "k6-outcome.schema.json"
REPOSITORY = "demo-repo"
ROOT_CAUSE = "gate red on C1.1"
COMMIT_TAG = "commit:0123456789abcdef0123456789abcdef01234567"
ENTRY = {
    "repo": REPOSITORY,
    "surface": "scripts/a.py",
    "surface_key": "demo/build",
    "outcome": "unverified-reasoned",
    "root_cause": ROOT_CAUSE,
    "tags": ["kind:gate", "run:demo", "msp:build", COMMIT_TAG, "usd:0", "minutes:1"],
}
UNKINDED = {
    **ENTRY,
    "outcome": "speculative",
    "tags": ["run:demo", "msp:build", COMMIT_TAG, "usd:0", "minutes:1"],
}
REPORTED = (4, 5, 6, 7)
COUNTED_OR_FOREIGN = (1, 2, 3)


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixtures():
    tests = repository_root() / "tests"
    lane = load_path("owned_formats_outcomes_store_lane", tests / "test_check_author_lane.py")
    kinds = load_path("owned_formats_outcomes_store_kinds", tests / "test_outcome_kinds.py")
    return lane.complete_record(), kinds.SPEC_WITHOUT_KIND


def stored(position, entry):
    stamped = {"id": "trj-%04d" % position, "ts": "2026-11-03T12:%02d:00.000Z" % position, **entry}
    return json.dumps(stamped).encode("utf-8")


def store_bytes():
    lines = (
        stored(1, ENTRY),
        stored(2, ENTRY),
        stored(3, {**ENTRY, "repo": "other-repo"}),
        b"{not json",
        b"\xff\xfe",
        b"[1, 2]",
        stored(7, UNKINDED),
    )
    return b"\n".join(lines) + b"\n"


def environment(home, store):
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
    }
    return {**kept, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1", "RECEIPTS_TRAJECTORY_STORE": str(store)}


def reported_number(text, store):
    patterns = (r"\bline(?: number)? ([0-9]+)(?![0-9])", re.escape(str(store)) + r":([0-9]+)(?![0-9])")
    found = sorted(
        (match.start(), int(match.group(1)))
        for pattern in patterns
        for match in (re.search(pattern, text),)
        if match is not None
    )
    return found[0][1] if found else None


def names_line(text, store, number):
    return reported_number(text, store) == number


class StoreThroughK6Test(unittest.TestCase):
    def test_each_store_line_that_fails_k6_is_reported_and_not_counted(self):
        record, spec_text = fixtures()
        with tempfile.TemporaryDirectory() as base:
            folder = pathlib.Path(base).resolve()
            repository = folder / REPOSITORY
            repository.mkdir()
            home = folder / "home"
            home.mkdir()
            store = folder / "store" / "trajectories.jsonl"
            store.parent.mkdir()
            store.write_bytes(store_bytes())
            (repository / "demo.md").write_text(spec_text, encoding="utf-8")
            record_path = repository / "demo.record.json"
            record_path.write_text(json.dumps(record), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(repository_root() / "scripts" / "outcomes.py"),
                    "--repo",
                    str(repository),
                    "--record",
                    str(record_path),
                ],
                cwd=str(repository),
                env=environment(home, store),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            written = json.loads(record_path.read_text(encoding="utf-8"))
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        about_store = [line for line in result.stderr.splitlines() if str(store) in line]
        reports = [line for line in about_store if K6_FILE in line]
        for number in REPORTED:
            with self.subTest(line=number):
                self.assertNotEqual([line for line in reports if names_line(line, store, number)], [], output)
        unkinded = [line for line in reports if names_line(line, store, 7) and "#/tags minContains" in line]
        self.assertNotEqual(unkinded, [], output)
        for number in COUNTED_OR_FOREIGN:
            with self.subTest(line=number):
                self.assertEqual([line for line in about_store if names_line(line, store, number)], [], output)
        outcomes = written.get("outcomes")
        self.assertIsInstance(outcomes, dict, written)
        self.assertEqual(outcomes.get("entries"), 2, outcomes)
        self.assertEqual(outcomes.get("repeated"), [{"kind": ROOT_CAUSE, "count": 2}], outcomes)


if __name__ == "__main__":
    unittest.main()
