import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_probe_and_store_advisories as advisories

MISSING = "no_such_tool_xyz"
NOT_ON_PATH = ["%s is not on PATH" % MISSING]


class ProbeRoundThreeAdvisoriesTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.sandbox = advisories.Sandbox(self.folder.name)

    def python3(self):
        return [self.sandbox.stubs["python3"]]

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

    def test_prefix_option_arguments_are_skipped_and_the_real_command_is_probed(self):
        self.assert_probes(
            {
                "env -u HOME python3 -m unittest tests.test_a": ("pass", self.python3()),
                "time -f %e python3 -V": ("pass", self.python3()),
                "exec -a name python3 -V": ("pass", self.python3()),
                "env -C tests python3 -V": ("pass", self.python3()),
                "env --unset HOME python3 -V": ("pass", self.python3()),
                "env --unset=HOME python3 -V": ("pass", self.python3()),
                "env -uHOME python3 -V": ("pass", self.python3()),
                "time -o out.txt python3 -V": ("pass", self.python3()),
                "env -u HOME %s" % MISSING: ("fail", NOT_ON_PATH),
                "time -f %%e %s" % MISSING: ("fail", NOT_ON_PATH),
                "exec -a name %s" % MISSING: ("fail", NOT_ON_PATH),
            }
        )

    def test_a_prefix_option_the_probe_does_not_know_passes_its_segment(self):
        self.assert_probes(
            {
                "nohup --unknown-option %s" % MISSING: ("pass", None),
                "env -S 'python3 -V'": ("pass", None),
            }
        )

    def test_shell_comments_are_never_tokenised(self):
        self.assert_probes(
            {
                "python3 -m unittest tests.test_a  # fast; no network": ("pass", self.python3()),
                "python3 -V # it's quick && %s" % MISSING: ("pass", self.python3()),
                "python3 -V;# %s" % MISSING: ("pass", self.python3()),
                "echo a#b": ("pass", ["echo is a shell builtin"]),
                "echo a#b; %s" % MISSING: ("fail", NOT_ON_PATH),
                "echo 'a #b'; %s" % MISSING: ("fail", NOT_ON_PATH),
                "echo a\\ #b; %s" % MISSING: ("fail", NOT_ON_PATH),
            }
        )

    def test_the_target_names_the_first_probed_word(self):
        module = advisories.load_probe_module()
        expected = {
            "(cd tests && python3 -V)": "cd",
            "python3>out": "python3",
            "python3 -V # fast": "python3",
            "env -u HOME python3 -V": "python3",
            "FOO=1 make test": "make",
            "cd web && python3 -V": "cd",
        }
        for command, target in expected.items():
            with self.subTest(command=command):
                self.assertEqual(module.command_target({"command": command}), target)
        probes = self.assert_probes({"(cd web && python3 -V)": ("pass", None), "python3>out": ("pass", None)})
        self.assertEqual(probes["(cd web && python3 -V)"]["target"], "cd")
        self.assertEqual(probes["python3>out"]["target"], "python3")


if __name__ == "__main__":
    unittest.main()
