import pathlib
import re
import unittest

PLAYBOOK_HEADINGS = (
    "## Ground",
    "## Probes",
    "## Questions",
    "## Extra step",
    "## Acceptance",
    "## Steps",
)

TEMPLATE_HEADINGS = (
    "## 1. Request",
    "## 2. Summary",
    "## 3. Environment",
    "## 4. Steps to reproduce",
    "## 5. Expected and actual",
    "## 6. Evidence",
    "## 7. Severity and workaround",
    "## 8. Root cause",
    "## 9. Fix boundary",
    "## 10. Acceptance criteria",
    "## 11. Assumptions",
    "## 12. Open questions",
    "## 13. Prevention",
)


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def read(relative):
    return (repo_root() / relative).read_text(encoding="utf-8")


def sections(lines):
    starts = [i for i, line in enumerate(lines) if re.match(r"^## \d+\. ", line)]
    ends = starts[1:] + [len(lines)]
    return tuple((lines[s], lines[s + 1:e]) for s, e in zip(starts, ends))


class PathwayBugTest(unittest.TestCase):
    def test_bug_playbook_has_every_section(self):
        text = read("core/pathways/bug.md")
        lines = text.splitlines()
        found = tuple(line for line in lines if line in PLAYBOOK_HEADINGS)
        self.assertEqual(found, PLAYBOOK_HEADINGS)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/probe.py", text)
        for relative in ("core/pathways/bug.md", "core/templates/spec-bug.md"):
            self.assertNotIn("mitosis", read(relative).lower(), relative)

    def test_bug_template_has_every_numbered_section(self):
        lines = read("core/templates/spec-bug.md").splitlines()
        self.assertEqual(lines[0], "# {{title}}")
        self.assertIn("Pathway: bug.", lines)
        self.assertIn("Date: {{date}}.", lines)
        numbered = tuple(line for line in lines if re.match(r"^## \d+\. ", line))
        self.assertEqual(numbered, TEMPLATE_HEADINGS)
        for heading, body in sections(lines):
            self.assertTrue(any("{{" in line for line in body), heading)
        fix_boundary = dict(sections(lines))["## 9. Fix boundary"]
        joined = "\n".join(fix_boundary)
        self.assertIn("THEN the system", joined)
        self.assertIn("THE SYSTEM SHALL <", joined)
        self.assertIn("THE SYSTEM SHALL CONTINUE TO", joined)

    def test_bug_template_numbers_each_acceptance_criterion(self):
        lines = read("core/templates/spec-bug.md").splitlines()
        body = dict(sections(lines))["## 10. Acceptance criteria"]
        self.assertTrue(any(line.startswith("### 10.1 ") for line in body))
        self.assertTrue(any(line.startswith("### 10.2 ") for line in body))

    def test_bug_playbook_designs_steps_during_the_interview(self):
        lines = read("core/pathways/bug.md").splitlines()

        def section_lines(heading):
            start = lines.index(heading) + 1
            end = start
            while end < len(lines) and not lines[end].startswith("## "):
                end += 1
            return lines[start:end]

        steps_text = "\n".join(section_lines("## Steps"))
        self.assertIn("Design the Steps during the interview", steps_text)
        acceptance_text = "\n".join(section_lines("## Acceptance"))
        self.assertIn("### 10.1", acceptance_text)


if __name__ == "__main__":
    unittest.main()
