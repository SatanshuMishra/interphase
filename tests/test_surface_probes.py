import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

TIMEOUT = 60
RUNNABLE_SEAM = {
    "name": "script-cli",
    "interface": "the product driven from the repository root",
    "catches": "a surface that does not behave",
    "misses": "how a person feels about it",
    "builder_runs": True,
}
LAB_SEAM = {
    "name": "phone-lab",
    "interface": "a person holding a phone",
    "catches": "a total drawn late",
    "misses": "a wrong total",
    "builder_runs": False,
}
CLI_LINE = {
    "id": "C1.1",
    "kind": "exact",
    "surface": {"family": "cli", "target": "python3"},
    "command": "python3 -m unittest tests.test_cli",
    "pass": "the test passes",
}
BROWSER_LINE = {
    "id": "C1.2",
    "kind": "exact",
    "surface": {"family": "browser", "target": "chromium"},
    "command": "playwright test tests/e2e/total.spec.ts",
    "pass": "the page shows the total",
}
MOBILE_LINE = {
    "id": "C1.3",
    "kind": "exact",
    "surface": {"family": "mobile", "target": "android"},
    "command": "vmlab run android tests/phone_total.yaml",
    "pass": "the phone shows the total",
}
DESKTOP_LINE = {
    "id": "C1.4",
    "kind": "exact",
    "surface": {"family": "desktop", "target": "macos"},
    "command": "vmlab run macos tests/desktop_total.yaml",
    "pass": "the window shows the total",
}
AGENT_LINE = {
    "id": "C1.5",
    "kind": "judged",
    "surface": {"family": "agent", "target": "claude"},
    "command": "claude -p 'Summarise the report'",
    "pass": "every trial meets the rubric",
    "rubric": "the summary names each failing check",
    "trials": 3,
}
FAMILY_LINES = (CLI_LINE, BROWSER_LINE, MOBILE_LINE, DESKTOP_LINE, AGENT_LINE)
EXPECTED_PROBES = (
    ("C1.1", "command", "python3"),
    ("C1.2", "command", "playwright"),
    ("C1.2", "playwright", "playwright"),
    ("C1.3", "command", "vmlab"),
    ("C1.3", "vmlab", "android"),
    ("C1.4", "command", "vmlab"),
    ("C1.4", "vmlab", "macos"),
    ("C1.5", "command", "claude"),
    ("C1.5", "claude", "claude"),
)
PROBE_KEYS = {"check", "probe", "target", "status", "detail"}
OUTCOMES = {"store": "/var/empty/trajectories.jsonl", "entries": 0, "repeated": []}
BOTH_MACHINES = '[{"name": "android-14", "platform": "android"}, {"name": "macos-15", "platform": "macos"}]'
MACOS_ONLY = '[{"name": "macos-15", "platform": "macos"}]'
STUBS = {
    "playwright": "#!/bin/sh\necho 'Version 1.40.0'\nexit 0\n",
    "claude": "#!/bin/sh\necho 'claude 2.0.0'\nexit 0\n",
}


def load_referee():
    path = pathlib.Path(__file__).with_name("contract_referee.py")
    spec = importlib.util.spec_from_file_location("contract_referee", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


referee = load_referee()


def vmlab_listing(machines):
    return "#!/bin/sh\nprintf '%%s\\n' '%s'\nexit 0\n" % machines


def vmlab_hanging():
    return "#!/bin/sh\nexec /bin/sleep 30\n"


def row(line, position):
    return {
        "file": "tests/test_surface.py",
        "name": "test_surface_%d" % (position + 1),
        "given": "the surface of line " + line["id"],
        "expect": line["pass"],
        "step": "build-surface",
        "check": line["id"],
    }


def record_of(lines, extra_criteria=(), extra_seams=()):
    return json.loads(
        json.dumps(
            {
                "status": "in-progress",
                "seams": [RUNNABLE_SEAM] + list(extra_seams),
                "criteria": [
                    {
                        "number": "5.1",
                        "title": "The total shows on every surface",
                        "text": "WHEN the app computes a total, THE SYSTEM SHALL show it on every surface.",
                        "seam": "script-cli",
                        "acceptance": list(lines),
                        "tests": [row(line, position) for position, line in enumerate(lines)],
                    }
                ]
                + list(extra_criteria),
                "steps": [
                    {
                        "name": "build-surface",
                        "files": ["scripts/drive.py"],
                        "criteria": ["5.1"] + [criterion["number"] for criterion in extra_criteria],
                        "task": "Show the total on every surface.",
                    }
                ],
                "locked": ["tests/test_surface.py"],
                "outcomes": OUTCOMES,
            }
        )
    )


def passing_probes(expected):
    return [
        {"check": check, "probe": name, "target": target, "status": "pass", "detail": "/usr/local/bin/" + target}
        for check, name, target in expected
    ]


def script_path(name):
    return pathlib.Path(__file__).resolve().parents[1] / "scripts" / name


def feature_template():
    path = pathlib.Path(__file__).resolve().parents[1] / "core" / "templates" / "spec-feature.md"
    return path.read_text(encoding="utf-8")


def path_folder(base, python=True, stubs=None):
    folder = pathlib.Path(base) / "bin"
    folder.mkdir()
    if python:
        (folder / "python3").symlink_to(sys.executable)
    for name, body in (stubs or {}).items():
        stub = folder / name
        stub.write_text(body, encoding="utf-8")
        stub.chmod(0o755)
    return folder


def isolated_environment(home, path):
    return {"HOME": str(home), "PATH": str(path), "PYTHONDONTWRITEBYTECODE": "1"}


def inherited_environment(home):
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
    }
    return {**kept, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1"}


def write_record(base, record):
    path = pathlib.Path(base) / "demo.record.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def read_record(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def home_folder(base):
    home = pathlib.Path(base) / "home"
    home.mkdir()
    return home


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


def surface_probe(base, record_path, folder, *flags):
    arguments = [script_path("surface_probe.py"), "--record", record_path, "--repo", base] + list(flags)
    return run(arguments, base, isolated_environment(home_folder(base), folder))


def check_complete(base, record_path):
    with tempfile.TemporaryDirectory() as home:
        return run([script_path("check_record.py"), "--complete", record_path], base, inherited_environment(home))


def stored_probes(record):
    return {(entry["check"], entry["probe"], entry["target"]): entry for entry in record.get("probes", [])}


def error_lines(output):
    return [line for line in output.splitlines() if line.startswith("error: ")]


class SurfaceProbesTest(unittest.TestCase):
    def assert_lines_are_k1(self, lines):
        k1 = referee.load("k1-acceptance")
        for line in lines:
            self.assertEqual(referee.errors(k1, line), (), line["id"])

    def test_each_family_is_probed_and_stored_in_the_record(self):
        self.assert_lines_are_k1(FAMILY_LINES)
        with tempfile.TemporaryDirectory() as base:
            stubs = {**STUBS, "vmlab": vmlab_listing(BOTH_MACHINES)}
            folder = path_folder(base, stubs=stubs)
            record_path = write_record(base, record_of(FAMILY_LINES))
            code, output = surface_probe(base, record_path, folder)
            self.assertEqual(code, 0, output)
            record = read_record(record_path)
        self.assertIn("probes", record, output)
        found = sorted((entry["check"], entry["probe"], entry["target"], entry["status"]) for entry in record["probes"])
        self.assertEqual(found, sorted(expected + ("pass",) for expected in EXPECTED_PROBES))
        for entry in record["probes"]:
            self.assertEqual(set(entry), PROBE_KEYS)
            self.assertIsInstance(entry["detail"], str)
            self.assertNotEqual(entry["detail"], "")

    def test_a_failed_probe_fails_the_run_and_the_complete_check(self):
        self.assert_lines_are_k1(FAMILY_LINES)
        missing = EXPECTED_PROBES[1:]
        with tempfile.TemporaryDirectory() as base:
            folder = path_folder(base)
            record_path = write_record(base, record_of(FAMILY_LINES))
            code, output = surface_probe(base, record_path, folder)
            record = read_record(record_path)
            complete_code, complete_output = check_complete(base, record_path)
        self.assertEqual(code, 1, output)
        printed = output.splitlines()
        for check, name, target in missing:
            prefix = "fail: %s %s %s: " % (check, name, target)
            self.assertNotEqual([line for line in printed if line.startswith(prefix)], [], output)
        probes = stored_probes(record)
        for expected in missing:
            self.assertIn(expected, probes, output)
            self.assertEqual(probes[expected]["status"], "fail")
        self.assertIn(EXPECTED_PROBES[0], probes)
        self.assertEqual(probes[EXPECTED_PROBES[0]]["status"], "pass")
        self.assertEqual(complete_code, 1, complete_output)
        errors = error_lines(complete_output)
        for check, name, _ in missing:
            phrase = "criterion 5.1 sits at a seam the builder runs, but the %s probe of %s failed" % (name, check)
            self.assertNotEqual([line for line in errors if phrase in line], [], complete_output)

    def test_an_unattended_failed_probe_stops_the_run(self):
        self.assert_lines_are_k1(FAMILY_LINES)
        with tempfile.TemporaryDirectory() as base:
            stubs = {"playwright": STUBS["playwright"], "vmlab": vmlab_listing(BOTH_MACHINES)}
            folder = path_folder(base, stubs=stubs)
            record_path = write_record(base, record_of(FAMILY_LINES))
            code, output = surface_probe(base, record_path, folder, "--unattended")
            record = read_record(record_path)
            specs = pathlib.Path(base) / "docs" / "specs"
            specs.mkdir(parents=True)
            spec_path = specs / "demo.md"
            items_path = specs / "demo.items.json"
            template = feature_template()
            spec_path.write_text(template, encoding="utf-8")
            with tempfile.TemporaryDirectory() as home:
                render_code, render_output = run(
                    [
                        script_path("render_record.py"),
                        "--record",
                        record_path,
                        "--spec",
                        spec_path,
                        "--items",
                        items_path,
                    ],
                    base,
                    inherited_environment(home),
                )
            spec_after = spec_path.read_text(encoding="utf-8")
            items_written = items_path.exists()
        self.assertEqual(code, 1, output)
        self.assertEqual(record.get("status"), "stopped", output)
        reason = record.get("stop", {}).get("reason", "")
        self.assertIn("C1.5", reason)
        self.assertIn("claude", reason)
        self.assertEqual(render_code, 1, render_output)
        self.assertEqual(spec_after, template)
        self.assertFalse(items_written)

        phone_line = {
            "id": "C2.1",
            "kind": "exact",
            "surface": {"family": "mobile", "target": "android"},
            "command": "python3 tests/drive_phone.py",
            "pass": "the phone shows the total",
        }
        self.assert_lines_are_k1((phone_line,))
        phone_criterion = {
            "number": "5.2",
            "title": "The total shows on the phone",
            "text": "WHEN the app computes a total, THE SYSTEM SHALL show it on the phone.",
            "seam": "phone-lab",
            "acceptance": [phone_line],
            "tests": [],
            "unproven": "a person holds the phone",
        }
        with tempfile.TemporaryDirectory() as base:
            folder = path_folder(base)
            record_path = write_record(base, record_of((CLI_LINE,), (phone_criterion,), (LAB_SEAM,)))
            code, output = surface_probe(base, record_path, folder, "--unattended")
            record = read_record(record_path)
        self.assertEqual(code, 0, output)
        self.assertEqual(record.get("status"), "in-progress")
        probes = stored_probes(record)
        self.assertIn(("C2.1", "vmlab", "android"), probes, output)
        self.assertEqual(probes[("C2.1", "vmlab", "android")]["status"], "fail")

    def test_a_hanging_probe_ends_at_its_time_limit(self):
        line = {**MOBILE_LINE, "id": "C1.1"}
        self.assert_lines_are_k1((line,))
        with tempfile.TemporaryDirectory() as base:
            folder = path_folder(base, stubs={"vmlab": vmlab_hanging()})
            record_path = write_record(base, record_of((line,)))
            started = time.monotonic()
            code, output = surface_probe(base, record_path, folder, "--timeout", "1")
            elapsed = time.monotonic() - started
            record = read_record(record_path)
        self.assertLess(elapsed, 15)
        self.assertEqual(code, 1, output)
        probes = stored_probes(record)
        self.assertIn(("C1.1", "vmlab", "android"), probes, output)
        entry = probes[("C1.1", "vmlab", "android")]
        self.assertEqual(entry["status"], "fail")
        self.assertIn("timed out", entry["detail"])

    def test_a_vmlab_target_must_name_a_machine(self):
        line = {**MOBILE_LINE, "id": "C1.1"}
        self.assert_lines_are_k1((line,))
        with tempfile.TemporaryDirectory() as base:
            folder = path_folder(base, stubs={"vmlab": vmlab_listing(MACOS_ONLY)})
            record_path = write_record(base, record_of((line,)))
            code, output = surface_probe(base, record_path, folder)
            record = read_record(record_path)
        self.assertEqual(code, 1, output)
        probes = stored_probes(record)
        self.assertIn(("C1.1", "vmlab", "android"), probes, output)
        entry = probes[("C1.1", "vmlab", "android")]
        self.assertEqual(entry["status"], "fail")
        self.assertIn("android", entry["detail"])

    def test_complete_requires_a_probe_for_every_line(self):
        self.assert_lines_are_k1(FAMILY_LINES)
        unprobed = {**record_of(FAMILY_LINES), "probes": []}
        with tempfile.TemporaryDirectory() as base:
            code, output = check_complete(base, write_record(base, unprobed))
        self.assertEqual(code, 1, output)
        errors = error_lines(output)
        for check, name, target in EXPECTED_PROBES:
            message = "acceptance line %s has no %s probe for %s; run surface_probe.py" % (check, name, target)
            self.assertNotEqual([line for line in errors if message in line], [], output)
        changed_line = {**CLI_LINE, "command": "node tests/total.test.js"}
        self.assert_lines_are_k1((changed_line,))
        stale = {
            **record_of((changed_line,) + FAMILY_LINES[1:]),
            "probes": passing_probes(EXPECTED_PROBES),
        }
        with tempfile.TemporaryDirectory() as base:
            code, output = check_complete(base, write_record(base, stale))
        self.assertEqual(code, 1, output)
        message = "acceptance line C1.1 has no command probe for node; run surface_probe.py"
        self.assertNotEqual([line for line in error_lines(output) if message in line], [], output)


if __name__ == "__main__":
    unittest.main()
