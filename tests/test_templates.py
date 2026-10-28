import contextlib
import importlib.util
import io
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
SHAPE = (
    "## 1. Problem",
    "## 2. Intent",
    "## 3. {}",
    "## 4. Decisions",
    "## 5. Test seams",
    "## 6. Out of scope",
)
THIRD = {
    "spec-feature.md": "User stories",
    "spec-prototype.md": "User stories",
    "spec-project.md": "User stories",
    "spec-bug.md": "Reproduction and cause",
    "spec-brief.md": "Evidence",
}
INTENT = "- I1 Goal: share the list with one friend\n- I2 Why: friends plan errands together\n- I3 Success: the friend opens the list\n"
CRITERION = "### 5.1 The friend opens the list\n\nWHEN the friend opens the link THE SYSTEM SHALL show the list.\n"
ASSUMPTION = "- Links never expire, because the user wants one link to keep working (relies on I1)."


def headings(text):
    return tuple(line for line in text.splitlines() if NUMBERED.match(line))


def fill(text):
    return PLACEHOLDER.sub(lambda match: NAMED.get(match.group(0), FILLER), text)


def replace_body(text, heading, body):
    lines = text.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.rstrip() == heading)
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(("## ", "### "))), len(lines))
    return "".join(lines[: start + 1]) + "\n" + body + "\n" + "".join(lines[end:])


def filled(name):
    text = fill((TEMPLATES / name).read_text(encoding="utf-8"))
    text = replace_body(text, "## 2. Intent", INTENT)
    text = replace_body(text, "### Assumptions", ASSUMPTION + "\n")
    return replace_body(text, "## 5. Test seams", CRITERION)


def load_check_spec():
    module_spec = importlib.util.spec_from_file_location("check_spec", ROOT / "scripts" / "check_spec.py")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def run_check_spec(template_path, spec_text):
    with tempfile.TemporaryDirectory() as folder:
        spec_path = pathlib.Path(folder) / "spec.md"
        spec_path.write_text(spec_text, encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = load_check_spec().main(["--template", str(template_path), str(spec_path)])
    return code, output.getvalue().splitlines()


class TemplatesTest(unittest.TestCase):
    def test_every_template_has_the_six_section_shape(self):
        self.assertEqual(sorted(path.name for path in TEMPLATES.glob("*.md")), sorted(THIRD))
        for name, third in THIRD.items():
            with self.subTest(template=name):
                text = (TEMPLATES / name).read_text(encoding="utf-8")
                self.assertEqual(headings(text), tuple(heading.format(third) for heading in SHAPE))
                self.assertNotIn("mitosis", text.lower())
                self.assertNotIn("Review bar", text)

    def test_every_template_carries_the_intent_reuse_and_assumptions(self):
        for name in THIRD:
            with self.subTest(template=name):
                text = (TEMPLATES / name).read_text(encoding="utf-8")
                lines = text.splitlines()
                self.assertIn("- I1 Goal: <goal>", text)
                self.assertIn("### Reuse and change", lines)
                self.assertIn("### Assumptions", lines)
                self.assertEqual(lines[lines.index("### Assumptions") + 4], "### Risks")
                self.assertIn(
                    "{{every repeated failure kind outcomes.py wrote to the record, then every other risk, or - None}}",
                    lines,
                )
                self.assertIn("(relies on I<n>)", text)
                self.assertIn("`${CLAUDE_PLUGIN_ROOT}/core/practices.md`", text)
                self.assertIn("written by the render script from the record", text)

    def test_a_filled_template_passes_the_spec_check(self):
        for name in THIRD:
            with self.subTest(template=name):
                text = filled(name)
                self.assertNotIn("{{", text)
                self.assertEqual(run_check_spec(TEMPLATES / name, text), (0, []))

    def test_a_filled_template_missing_its_out_of_scope_section_fails(self):
        text = filled("spec-feature.md")
        cut = text[: text.index("## 6. Out of scope")]
        code, output = run_check_spec(TEMPLATES / "spec-feature.md", cut)
        self.assertEqual((code, output), (1, ["error: missing section: ## 6. Out of scope"]))

    def test_an_assumption_without_its_intent_line_fails(self):
        text = filled("spec-bug.md").replace(" (relies on I1).", ".")
        code, output = run_check_spec(TEMPLATES / "spec-bug.md", text)
        self.assertEqual(code, 1)
        self.assertEqual(len(output), 1)
        self.assertIn("assumption cites no intent line", output[0])

    def test_prototype_template_names_the_ui_quality_floor(self):
        text = (TEMPLATES / "spec-prototype.md").read_text(encoding="utf-8")
        self.assertIn("the UI quality floor (gap analysis item 11)", text)
        decisions = text[text.index("## 4. Decisions") : text.index("### Reuse and change")]
        self.assertNotIn("accessibility", decisions)


if __name__ == "__main__":
    unittest.main()
