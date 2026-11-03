import json
import pathlib
import re
import unittest

PREVIOUS_RELEASE = (0, 14, 0)
VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
ENTRY_HEADING = "## "
NAMED_IN_ENTRY = ("H11", "H12", "validator")


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def entry_lines(lines):
    headings = tuple(position for position, line in enumerate(lines) if line.startswith(ENTRY_HEADING))
    if not headings:
        return ()
    end = headings[1] if len(headings) > 1 else len(lines)
    return tuple(lines[headings[0] : end])


class ReleaseTest(unittest.TestCase):
    def test_release_is_newer_than_0_14_0_and_heads_the_changelog(self):
        root = repository_root()
        manifest = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        version = manifest.get("version")
        self.assertIsInstance(version, str, manifest)
        self.assertIsNotNone(VERSION_RE.fullmatch(version), version)
        self.assertGreater(tuple(int(part) for part in version.split(".")), PREVIOUS_RELEASE, version)
        changelog = root / "CHANGELOG.md"
        self.assertTrue(changelog.is_file(), "CHANGELOG.md is missing at the repository root")
        entry = entry_lines(changelog.read_text(encoding="utf-8").splitlines())
        self.assertNotEqual(entry, (), "CHANGELOG.md has no '## ' heading")
        self.assertEqual(entry[0], ENTRY_HEADING + version)
        text = "\n".join(entry)
        for word in NAMED_IN_ENTRY:
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
