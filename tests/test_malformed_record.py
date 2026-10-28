import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_acceptance_lines as fixtures
import test_outcome_kinds as outcome_fixtures

UNHASHABLE = (["C1.1"], {"id": "C1.1"})


def failed_probes(record):
    return {**record, "probes": [{**entry, "status": "fail", "detail": "absent"} for entry in record["probes"]]}


def malformed_records():
    base = fixtures.complete_record()
    return tuple(
        case
        for value in UNHASHABLE
        for case in (
            ("check %r" % (value,), fixtures.with_criterion(base, 0, tests=[{**fixtures.ROW_A, "check": value}])),
            ("seam %r" % (value,), fixtures.with_criterion(failed_probes(base), 0, seam=value)),
        )
    )


def run(script, arguments, cwd, home):
    return subprocess.run(
        [sys.executable, str(fixtures.script_path(script))] + arguments,
        cwd=cwd,
        env=fixtures.environment(home),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=fixtures.TIMEOUT,
    )


def validators(path, spec, items):
    return (
        ("check_record.py", [str(path)]),
        ("check_record.py --complete", ["--complete", str(path)]),
        ("render_record.py", ["--record", str(path), "--spec", str(spec), "--items", str(items)]),
    )


class MalformedRecordTest(unittest.TestCase):
    def test_validators_refuse_a_non_string_check_or_seam_with_a_reason(self):
        for case, record in malformed_records():
            with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as home:
                path = pathlib.Path(folder) / "demo.record.json"
                spec = pathlib.Path(folder) / "demo.md"
                items = pathlib.Path(folder) / "items.json"
                for label, arguments in validators(path, spec, items):
                    with self.subTest(case=case, script=label):
                        path.write_text(json.dumps(record), encoding="utf-8")
                        spec.write_text(outcome_fixtures.SPEC_WITHOUT_KIND, encoding="utf-8")
                        result = run(label.split(" ")[0], arguments, folder, home)
                        self.assertNotIn("Traceback", result.stderr)
                        self.assertEqual(result.returncode, 1, result.stderr)
                        self.assertTrue(
                            any(line.startswith("error: ") and "5.1" in line for line in result.stdout.splitlines()),
                            result.stdout,
                        )
                        self.assertFalse(items.exists())

    def test_surface_probe_stores_probes_for_a_non_string_check_or_seam(self):
        for case, record in malformed_records():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as home:
                path = pathlib.Path(folder) / "demo.record.json"
                path.write_text(json.dumps(record), encoding="utf-8")
                result = run("surface_probe.py", ["--record", str(path), "--repo", folder, "--timeout", "5"], folder, home)
                self.assertNotIn("Traceback", result.stderr)
                self.assertIn(result.returncode, (0, 1), result.stderr)
                stored = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(stored["probes"])
                self.assertTrue(all(entry["status"] in ("pass", "fail") for entry in stored["probes"]))
                self.assertEqual(stored["criteria"], record["criteria"])


if __name__ == "__main__":
    unittest.main()
