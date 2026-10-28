import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_acceptance_lines as fixtures
import test_outcome_kinds as outcome_fixtures

NUL_COMMANDS = ("sub\u0000/run", "./bin\u0000")
SURROGATE_TEXT = "sub\ud800/run"
SEAMS = ("script-cli", "nowhere-the-builder-runs")


def with_command(record, command, seam):
    criterion = record["criteria"][0]
    line = {**criterion["acceptance"][0], "command": command}
    rest = {key: value for key, value in record.items() if key != "probes"}
    return {**rest, "criteria": [{**criterion, "seam": seam, "acceptance": [line]}] + record["criteria"][1:]}


def run(script, arguments, folder, home):
    return subprocess.run(
        [sys.executable, str(fixtures.script_path(script))] + arguments,
        cwd=folder,
        env=fixtures.environment(home),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=fixtures.TIMEOUT,
    )


class UnencodableRecordTest(unittest.TestCase):
    def test_surface_probe_fails_a_nul_command_instead_of_crashing(self):
        for command in NUL_COMMANDS:
            for seam in SEAMS:
                with self.subTest(command=command, seam=seam), tempfile.TemporaryDirectory() as folder, \
                        tempfile.TemporaryDirectory() as home:
                    path = pathlib.Path(folder) / "demo.record.json"
                    path.write_text(json.dumps(with_command(fixtures.complete_record(), command, seam)), encoding="utf-8")
                    result = run("surface_probe.py", ["--record", str(path), "--repo", folder, "--timeout", "5"], folder, home)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(result.returncode, 1 if seam == "script-cli" else 0, result.stderr)
                    stored = json.loads(path.read_text(encoding="utf-8"))
                    command_probes = [entry for entry in stored["probes"] if entry["check"] == "C1.1"]
                    self.assertEqual([entry["status"] for entry in command_probes], ["fail"])

    def test_every_record_reader_refuses_a_lone_surrogate_with_a_reason(self):
        record = with_command(fixtures.complete_record(), SURROGATE_TEXT, "script-cli")
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as home:
            path = pathlib.Path(folder) / "demo.record.json"
            spec = pathlib.Path(folder) / "demo.md"
            items = pathlib.Path(folder) / "items.json"
            runs = (
                ("check_record.py", [str(path)], 1),
                ("check_record.py", ["--complete", str(path)], 1),
                ("render_record.py", ["--record", str(path), "--spec", str(spec), "--items", str(items)], 1),
                ("read_back.py", ["--record", str(path)], 2),
                ("surface_probe.py", ["--record", str(path), "--repo", folder, "--timeout", "5"], 2),
                ("outcomes.py", ["--repo", folder, "--record", str(path)], 2),
            )
            for script, arguments, code in runs:
                with self.subTest(script=script, arguments=arguments[:1]):
                    path.write_text(json.dumps(record), encoding="utf-8")
                    spec.write_text(outcome_fixtures.SPEC_WITHOUT_KIND, encoding="utf-8")
                    result = run(script, arguments, folder, home)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(result.returncode, code, result.stderr)
                    self.assertTrue(result.stdout.strip() or result.stderr.strip())
                    self.assertEqual(path.read_text(encoding="utf-8"), json.dumps(record))
                    self.assertFalse(items.exists())


if __name__ == "__main__":
    unittest.main()
