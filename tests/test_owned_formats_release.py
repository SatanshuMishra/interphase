import json
import pathlib
import re
import unittest

PREVIOUS_RELEASE = (0, 14, 0)
FORMATS_RELEASE = "0.15.0"
VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
ENTRY_HEADING = "## "
NAMED_IN_ENTRY = ("H11", "H12", "validator")


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def entry_lines(lines, first=0):
    headings = tuple(position for position, line in enumerate(lines) if line.startswith(ENTRY_HEADING))
    later = tuple(position for position in headings if position >= first)
    if not later:
        return ()
    end = next((position for position in later if position > later[0]), len(lines))
    return tuple(lines[later[0] : end])


def entry_for(lines, version):
    heading = ENTRY_HEADING + version
    return entry_lines(lines, lines.index(heading)) if heading in lines else ()


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
        lines = changelog.read_text(encoding="utf-8").splitlines()
        entry = entry_lines(lines)
        self.assertNotEqual(entry, (), "CHANGELOG.md has no '## ' heading")
        self.assertEqual(entry[0], ENTRY_HEADING + version)
        formats_entry = entry_for(lines, FORMATS_RELEASE)
        self.assertNotEqual(formats_entry, (), "CHANGELOG.md has no entry for " + FORMATS_RELEASE)
        text = "\n".join(formats_entry)
        for word in NAMED_IN_ENTRY:
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()
