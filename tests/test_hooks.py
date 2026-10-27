import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMMAND = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/resume_context.py"'
METRICS_COMMAND = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/metrics_hook.py"'


def consumer_names():
    source = (ROOT / "tests" / "test_skills.py").read_text(encoding="utf-8")
    return re.findall(r'assertNotIn\("([a-z]+)", text\.lower\(\)\)', source)


class HooksTest(unittest.TestCase):
    def test_the_resume_script_runs_after_compact_and_clear(self):
        text = (ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8")
        registration = json.loads(text)
        self.assertEqual(list(registration), ["hooks"])
        self.assertEqual(list(registration["hooks"]), ["SessionStart", "PostToolUse", "PostToolUseFailure"])
        entries = registration["hooks"]["SessionStart"]
        self.assertIsInstance(entries, list)
        self.assertEqual([entry["matcher"] for entry in entries], ["compact", "clear"])
        for entry in entries:
            with self.subTest(matcher=entry["matcher"]):
                self.assertEqual(entry["hooks"], [{"type": "command", "command": COMMAND, "timeout": 10}])
        self.assertTrue((ROOT / "scripts" / "resume_context.py").is_file())
        names = consumer_names()
        self.assertEqual(len(names), 1, names)
        self.assertNotIn(names[0], text.lower())

    def test_metrics_hook_registered(self):
        registration = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        hooks = registration["hooks"]
        self.assertEqual(sorted(hooks), ["PostToolUse", "PostToolUseFailure", "SessionStart"])
        expected = [{"type": "command", "command": METRICS_COMMAND, "timeout": 10}]
        self.assertEqual(hooks["PostToolUse"], [{"matcher": "^(Bash|Agent|Task|AskUserQuestion)$", "hooks": expected}])
        self.assertEqual(hooks["PostToolUseFailure"], [{"matcher": "^Bash$", "hooks": expected}])
        self.assertTrue((ROOT / "scripts" / "metrics_hook.py").is_file())


if __name__ == "__main__":
    unittest.main()
