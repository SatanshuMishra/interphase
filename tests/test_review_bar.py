import contextlib
import importlib.util
import io
import itertools
import pathlib
import re
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "core" / "templates"
NUMBERED = re.compile(r"^## \d+\. ")
PLACEHOLDER = re.compile(r"\{\{.*?\}\}")
NAMED = {"{{title}}": "Shared task list", "{{date}}": "2026-10-10", "{{pathway}}": "feature"}
FILLER = "Written answer"
CITED_SECTIONS = ("requirements", "edge cases")
CITED_SUB_SECTIONS = ("expected", "unchanged")

THREATS = ("threats", "level of defence", "defended", "none beyond its acceptance criteria")
OUT_OF_SCOPE = ("out of scope for review", "before the change", "hardening beyond the named threats")
BLOCK = "block on beyond the acceptance criteria"

REVIEW_BARS = {
    "spec-feature.md": (
        (
            "## 1. Request",
            "## 2. Problem and why now",
            "## 3. Users and stories",
            "## 4. Goals and non-goals",
            "## 5. Boundaries",
            "## 6. Requirements",
            "## 7. Acceptance criteria",
            "## 8. Edge cases",
            "## 9. Code map",
            "## 10. Approach and alternatives",
            "## 11. Assumptions",
            "## 12. Open questions",
            "## 13. Verification",
            "## 14. Reuse and change",
            "## 15. Variation",
        ),
        "## 16. Review bar",
        (THREATS, (BLOCK, "the requirements", "the boundaries", "the non-goals"), OUT_OF_SCOPE),
    ),
    "spec-bug.md": (
        (
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
            "## 14. Reuse and change",
            "## 15. Variation",
        ),
        "## 16. Review bar",
        (THREATS, (BLOCK, "the Expected and Unchanged statements of the Fix boundary"), OUT_OF_SCOPE),
    ),
    "spec-prototype.md": (
        (
            "## 1. Request",
            "## 2. Source artefacts",
            "## 3. Intended and incidental",
            "## 4. Screens and journeys",
            "## 5. State matrix",
            "## 6. Content variation",
            "## 7. Interactions not shown",
            "## 8. Data sources",
            "## 9. Validation and errors",
            "## 10. Auth and permissions",
            "## 11. Persistence and concurrency",
            "## 12. Accessibility",
            "## 13. Responsive behaviour",
            "## 14. Analytics",
            "## 15. Non-goals",
            "## 16. Acceptance criteria",
            "## 17. Assumptions",
            "## 18. Open questions",
            "## 19. Reuse and change",
            "## 20. Variation",
        ),
        "## 21. Review bar",
        (THREATS, (BLOCK, "the behaviours sections 4 to 14 specify", "the non-goals"), OUT_OF_SCOPE),
    ),
    "spec-project.md": (
        (
            "## 1. Request",
            "## 2. Problem and why now",
            "## 3. Users and stories",
            "## 4. Stage and definition of done",
            "## 5. Goals and non-goals",
            "## 6. Platforms and environments",
            "## 7. Stack and alternatives",
            "## 8. Repository and tooling",
            "## 9. Test strategy",
            "## 10. Delivery",
            "## 11. Operations",
            "## 12. Requirements",
            "## 13. Acceptance criteria",
            "## 14. Edge cases",
            "## 15. Walking skeleton and slices",
            "## 16. Assumptions",
            "## 17. Open questions",
            "## 18. Verification",
            "## 19. Reuse and change",
            "## 20. Variation",
        ),
        "## 21. Review bar",
        (
            THREATS,
            (BLOCK, "the requirements", "the stage and definition of done", "the non-goals"),
            OUT_OF_SCOPE,
        ),
    ),
    "spec-brief.md": (
        (
            "## 1. Request",
            "## 2. Change",
            "## 3. Evidence",
            "## 4. Acceptance criteria",
            "## 5. Assumptions",
            "## 6. Reuse and change",
        ),
        "## 7. Review bar",
        (
            (
                "one or two lines",
                "threats",
                "none beyond its acceptance criteria",
                BLOCK,
                "the Unchanged statements",
                "out of scope for review",
                "before the change",
            ),
        ),
    ),
}


def paragraphs(lines):
    blocks = re.split(r"\n[ \t]*\n", "\n".join(lines))
    return tuple(block.strip() for block in blocks if block.strip())


def fill(text):
    return PLACEHOLDER.sub(lambda match: NAMED.get(match.group(0), FILLER), text)


def section_titles(titles, line):
    heading = re.match(r"^(#{1,3}) (?:\d+\. )?(.*)$", line)
    if not heading:
        return titles
    title = heading.group(2).strip().lower()
    return {1: ("", ""), 2: (title, ""), 3: (titles[0], title)}[len(heading.group(1))]


def cite(text):
    number = re.search(r"^### (\d+\.1) ", text, re.MULTILINE).group(1)
    lines = text.splitlines()
    titles = tuple(itertools.accumulate(lines, section_titles, initial=("", "")))[1:]
    return "".join(
        line + " ({})".format(number) + "\n"
        if line.strip() and not line.startswith("#") and (two in CITED_SECTIONS or three in CITED_SUB_SECTIONS)
        else line + "\n"
        for line, (two, three) in zip(lines, titles)
    )


def without_section(text, heading):
    lines = text.splitlines()
    return "\n".join(lines[: lines.index(heading)]).rstrip("\n") + "\n"


class ReviewBarTest(unittest.TestCase):
    def load_check_spec(self):
        module_spec = importlib.util.spec_from_file_location("check_spec", ROOT / "scripts" / "check_spec.py")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module

    def run_check_spec(self, module, template_path, spec_text):
        with tempfile.TemporaryDirectory() as folder:
            spec_path = pathlib.Path(folder) / "spec.md"
            spec_path.write_text(spec_text, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = module.main(["--template", str(template_path), str(spec_path)])
        return code, output.getvalue().splitlines()

    def test_every_spec_template_ends_with_a_review_bar_section(self):
        self.assertEqual(sorted(path.name for path in TEMPLATES.glob("*.md")), sorted(REVIEW_BARS))
        for name, (earlier, heading, parts) in REVIEW_BARS.items():
            with self.subTest(template=name):
                text = (TEMPLATES / name).read_text(encoding="utf-8")
                self.assertNotIn("mitosis", text.lower())
                lines = text.splitlines()
                numbered = tuple(line for line in lines if NUMBERED.match(line))
                self.assertEqual(numbered[-1], heading)
                self.assertEqual(numbered[:-1], earlier)
                level_two = tuple(line for line in lines if line.startswith("## "))
                self.assertEqual(level_two[-1], heading)
                body = paragraphs(lines[lines.index(heading) + 1 :])
                self.assertEqual(len(body), len(parts), body)
                for paragraph, needles in zip(body, parts):
                    self.assertIn("{{", paragraph)
                    for needle in needles:
                        self.assertIn(needle, paragraph, needle)

    def test_check_spec_accepts_a_filled_review_bar_and_reports_a_missing_one(self):
        check_spec = self.load_check_spec()
        for name, (_, heading, _) in REVIEW_BARS.items():
            with self.subTest(template=name):
                template_path = TEMPLATES / name
                filled = cite(fill(template_path.read_text(encoding="utf-8")))
                lines = filled.splitlines()
                self.assertEqual(lines[0], "# Shared task list")
                self.assertIn("Date: 2026-10-10.", lines)
                self.assertTrue(any(re.match(r"^### \d+\.1 " + FILLER + "$", line) for line in lines))
                self.assertNotIn("{{", filled)
                self.assertIn(heading, lines)
                self.assertEqual(self.run_check_spec(check_spec, template_path, filled), (0, []))
                code, output = self.run_check_spec(check_spec, template_path, without_section(filled, heading))
                self.assertEqual(code, 1, output)
                self.assertEqual(output, ["error: missing section: " + heading])


if __name__ == "__main__":
    unittest.main()
