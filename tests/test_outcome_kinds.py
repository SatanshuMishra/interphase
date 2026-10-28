import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

TIMEOUT = 60
REPOSITORY = "demo-app"
REMOTE = "https://github.com/example/demo-app.git"
OTHER_REPOSITORY = "other-app"
TAGS = [
    "kind:gate",
    "run:hr-demo",
    "msp:acceptance-lines",
    "commit:" + "a" * 40,
    "check:C1.1=fail",
    "usd:0.42",
    "minutes:3.5",
]
HOME_STORE = (".claude", "mcp-servers", "trajectory-kb", "data", "trajectories.jsonl")
SEAM = {
    "name": "script-cli",
    "interface": "the scripts run as subprocesses on temporary records",
    "catches": "a wrong exit code or a missing error",
    "misses": "how a person reads the output",
    "builder_runs": True,
}
EXACT_LINE = {
    "id": "C1.1",
    "kind": "exact",
    "surface": {"family": "cli", "target": "python3"},
    "command": "python3 -m unittest tests.test_a",
    "pass": "the test passes",
}
ROW_A = {
    "file": "tests/test_a.py",
    "name": "test_a",
    "given": "a total of 3",
    "expect": "3 is returned",
    "step": "build-a",
    "check": "C1.1",
}
REPEATED_KIND = "stale cache key"
SPEC_HEAD = (
    "# Demo feature\n\n"
    "Pathway: feature.\n\n"
    "## 1. Problem\n\nAdd a total to the app.\n\n"
    "## 2. Intent\n\n- I1 Goal: the app shows a total.\n\n"
    "## 4. Decisions\n\n1. The app returns the total it is given.\n\n"
    "### Assumptions\n\n- None\n\n"
    "### Risks\n\n"
)
SPEC_TAIL = (
    "## 5. Test seams\n\n{{written by the render script from the record}}\n\n"
    "## 6. Out of scope\n\nCurrency conversion.\n"
)
SPEC_WITHOUT_KIND = SPEC_HEAD + "- None\n\n" + SPEC_TAIL
SPEC_WITH_KIND = SPEC_HEAD + "- " + REPEATED_KIND + ": the total must read a fresh cache.\n\n" + SPEC_TAIL


def load_referee():
    path = pathlib.Path(__file__).with_name("contract_referee.py")
    spec = importlib.util.spec_from_file_location("contract_referee", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


referee = load_referee()


def complete_record(outcomes):
    record = {
        "status": "in-progress",
        "seams": [SEAM],
        "criteria": [
            {
                "number": "5.1",
                "title": "The total adds up",
                "text": "WHEN the app is given a total, THE SYSTEM SHALL return it unchanged.",
                "seam": "script-cli",
                "acceptance": [EXACT_LINE],
                "tests": [ROW_A],
            }
        ],
        "steps": [{"name": "build-a", "files": ["scripts/a.py"], "criteria": ["5.1"], "task": "Build the total."}],
        "locked": ["tests/test_a.py"],
        "probes": [
            {
                "check": "C1.1",
                "probe": "command",
                "target": "python3",
                "status": "pass",
                "detail": "/usr/local/bin/python3",
            }
        ],
    }
    return json.loads(json.dumps(record if outcomes is None else {**record, "outcomes": outcomes}))


def arguments_of(repo, outcome, root_cause=None, symptom=None):
    found = {
        "repo": repo,
        "surface": "scripts/check_record.py",
        "surface_key": "scripts/check_record",
        "outcome": outcome,
        "tags": list(TAGS),
        "files": ["scripts/check_record.py"],
        "tier": "top",
    }
    causes = {} if root_cause is None else {"root_cause": root_cause}
    symptoms = {} if symptom is None else {"symptom": symptom}
    return {**found, **causes, **symptoms}


def store_line(position, arguments):
    return json.dumps({**arguments, "id": "trj-%04d" % position, "ts": "2026-10-01T12:%02d:00.000Z" % position})


def environment(home, store=None):
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
    }
    chosen = {} if store is None else {"RECEIPTS_TRAJECTORY_STORE": str(store)}
    return {**kept, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1", **chosen}


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def script_path(name):
    return repository_root() / "scripts" / name


def run(arguments, cwd, env):
    result = subprocess.run(
        [str(argument) for argument in arguments],
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    return result.returncode, result.stdout + result.stderr


def make_repository(base, home):
    folder = pathlib.Path(base) / REPOSITORY
    folder.mkdir()
    for arguments in (("git", "init", "-q"), ("git", "remote", "add", "origin", REMOTE)):
        code, output = run(arguments, folder, environment(home))
        if code != 0:
            raise AssertionError("git setup failed: " + output)
    return folder


def make_home(base):
    home = pathlib.Path(base) / "home"
    home.mkdir()
    return home


def write_store(path, entries, extra_lines=()):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [store_line(position, entry) for position, entry in enumerate(entries)] + list(extra_lines)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def two_failures(kind):
    return [
        arguments_of(REPOSITORY, "unverified-reasoned", root_cause=kind),
        arguments_of(REPOSITORY, "reverted", root_cause=kind),
    ]


def write_record(folder, record):
    path = pathlib.Path(folder) / "demo.record.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def outcomes_run(repository, record_path, home, store=None):
    return run(
        [sys.executable, script_path("outcomes.py"), "--repo", repository, "--record", record_path],
        repository,
        environment(home, store),
    )


def read_record(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def same_file(first, second):
    return os.path.realpath(str(first)) == os.path.realpath(str(second))


class OutcomeKindsTest(unittest.TestCase):
    def assert_entries_are_k6(self, entries):
        k6 = referee.load("k6-outcome")
        for entry in entries:
            self.assertEqual(referee.errors(k6, entry), (), entry)

    def test_repeated_failure_kinds_of_this_repository_are_written_to_the_record(self):
        entries = (
            two_failures(REPEATED_KIND)
            + [
                arguments_of(REPOSITORY, "speculative", symptom="the total button does nothing"),
                arguments_of(REPOSITORY, "unverified-reasoned", symptom="the total button does nothing"),
                arguments_of(REPOSITORY, "reverted", root_cause="a typo in the config"),
                arguments_of(REPOSITORY, "fixed", root_cause="a flaky clock"),
                arguments_of(REPOSITORY, "fixed", root_cause="a flaky clock"),
                arguments_of(OTHER_REPOSITORY, "reverted", root_cause="the other app crashes"),
                arguments_of(OTHER_REPOSITORY, "speculative", root_cause="the other app crashes"),
            ]
        )
        self.assert_entries_are_k6(entries)
        with tempfile.TemporaryDirectory() as base:
            home = make_home(base)
            repository = make_repository(base, home)
            store = write_store(pathlib.Path(base) / "store" / "trajectories.jsonl", entries, ("this line is not JSON {",))
            original = complete_record(None)
            record_path = write_record(base, original)
            code, output = outcomes_run(repository, record_path, home, store)
            record = read_record(record_path)
        self.assertEqual(code, 0, output)
        self.assertIn("outcomes", record, output)
        self.assertEqual(
            record["outcomes"].get("repeated"),
            [{"kind": REPEATED_KIND, "count": 2}, {"kind": "the total button does nothing", "count": 2}],
        )
        self.assertEqual(record["outcomes"].get("entries"), 7)
        self.assertTrue(same_file(record["outcomes"].get("store", ""), store))
        for key, value in original.items():
            self.assertEqual(record.get(key), value, key)

    def test_the_store_is_found_as_receipts_finds_it(self):
        env_kind = "the env store fault"
        repo_kind = "the repo store fault"
        home_kind = "the home store fault"
        self.assert_entries_are_k6(two_failures(env_kind) + two_failures(repo_kind) + two_failures(home_kind))
        runs = ("RECEIPTS_TRAJECTORY_STORE", "receipts.config.json", "home store")
        for name in runs:
            with self.subTest(store=name), tempfile.TemporaryDirectory() as base:
                home = make_home(base)
                repository = make_repository(base, home)
                home_store = write_store(home.joinpath(*HOME_STORE), two_failures(home_kind))
                repo_store = repository / ".receipts" / "trajectories.jsonl"
                env_store = pathlib.Path(base) / "elsewhere" / "trajectories.jsonl"
                if name != "home store":
                    write_store(repo_store, two_failures(repo_kind))
                    (repository / "receipts.config.json").write_text(
                        json.dumps({"agent": {"trajectory_store": "repo"}}), encoding="utf-8"
                    )
                if name == "RECEIPTS_TRAJECTORY_STORE":
                    write_store(env_store, two_failures(env_kind))
                expected = {
                    "RECEIPTS_TRAJECTORY_STORE": (env_store, env_kind),
                    "receipts.config.json": (repo_store, repo_kind),
                    "home store": (home_store, home_kind),
                }[name]
                record_path = write_record(base, complete_record(None))
                chosen = env_store if name == "RECEIPTS_TRAJECTORY_STORE" else None
                code, output = outcomes_run(repository, record_path, home, chosen)
                record = read_record(record_path)
                self.assertEqual(code, 0, output)
                self.assertIn("outcomes", record, output)
                self.assertTrue(same_file(record["outcomes"].get("store", ""), expected[0]), record["outcomes"])
                self.assertEqual(record["outcomes"].get("repeated"), [{"kind": expected[1], "count": 2}])

    def test_render_refuses_a_spec_that_leaves_a_repeated_kind_out_of_risks(self):
        outcomes = {"store": "/var/empty/trajectories.jsonl", "entries": 2, "repeated": [{"kind": REPEATED_KIND, "count": 2}]}
        record = complete_record(outcomes)
        for spec_text, expected_code in ((SPEC_WITHOUT_KIND, 1), (SPEC_WITH_KIND, 0)):
            with tempfile.TemporaryDirectory() as base:
                home = make_home(base)
                specs = pathlib.Path(base) / "docs" / "specs"
                specs.mkdir(parents=True)
                spec_path = specs / "demo.md"
                spec_path.write_text(spec_text, encoding="utf-8")
                items_path = specs / "demo.items.json"
                code, output = run(
                    [
                        sys.executable,
                        script_path("render_record.py"),
                        "--record",
                        write_record(base, record),
                        "--spec",
                        spec_path,
                        "--items",
                        items_path,
                    ],
                    base,
                    environment(home),
                )
                spec_after = spec_path.read_text(encoding="utf-8")
                items_written = items_path.exists()
            self.assertEqual(code, expected_code, output)
            if expected_code == 1:
                self.assertIn("repeated failure kind %s is not listed under Risks" % REPEATED_KIND, output)
                self.assertEqual(spec_after, spec_text)
                self.assertFalse(items_written)
            else:
                self.assertTrue(items_written)

    def test_complete_requires_the_outcomes_to_have_been_read(self):
        with tempfile.TemporaryDirectory() as base:
            home = make_home(base)
            code, output = run(
                [sys.executable, script_path("check_record.py"), "--complete", write_record(base, complete_record(None))],
                base,
                environment(home),
            )
        self.assertEqual(code, 1, output)
        message = "record has no outcomes; run outcomes.py before planning"
        errors = [line for line in output.splitlines() if line.startswith("error: ") and message in line]
        self.assertNotEqual(errors, [], output)

    def test_every_template_has_a_risks_section(self):
        templates = sorted((repository_root() / "core" / "templates").glob("spec-*.md"))
        self.assertEqual(
            [path.name for path in templates],
            ["spec-brief.md", "spec-bug.md", "spec-feature.md", "spec-project.md", "spec-prototype.md"],
        )
        for path in templates:
            with self.subTest(template=path.name):
                lines = path.read_text(encoding="utf-8").splitlines()
                self.assertIn("### Assumptions", lines)
                self.assertIn("### Risks", lines)
                self.assertIn("## 5. Test seams", lines)
                self.assertLess(lines.index("### Assumptions"), lines.index("### Risks"))
                self.assertLess(lines.index("### Risks"), lines.index("## 5. Test seams"))


if __name__ == "__main__":
    unittest.main()
