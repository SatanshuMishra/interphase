import contextlib
import importlib.util
import io
import pathlib
import tempfile
import unittest

TEMPLATE = "# Spec\n\n## 1. Request\n\n{{request}}\n\n## 2. Summary\n\n{{summary}}\n"
COMPLETE = "# Spec\n\n## 1. Request\n\nAdd a login page.\n\n## 2. Summary\n\nThe page accepts a name and a password.\n"


class CheckSpecTest(unittest.TestCase):
    def load(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        module_spec = importlib.util.spec_from_file_location("check_spec", root / "scripts" / "check_spec.py")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module

    def run_checker(self, spec_text, template_text=TEMPLATE):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            template_path = pathlib.Path(directory) / "template.md"
            spec_path = pathlib.Path(directory) / "spec.md"
            template_path.write_text(template_text, encoding="utf-8")
            spec_path.write_text(spec_text, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = module.main(["--template", str(template_path), str(spec_path)])
        return code, output.getvalue().splitlines()

    def lines_with(self, lines, prefix, text):
        return [line for line in lines if line.startswith(prefix) and text in line]

    def test_check_spec_passes_a_complete_spec(self):
        code, lines = self.run_checker(COMPLETE)
        self.assertEqual(code, 0)
        self.assertEqual([line for line in lines if line.startswith("error:")], [])

    def test_check_spec_reports_a_missing_section(self):
        spec = "# Spec\n\n## 1. Request\n\nAdd a login page.\n"
        code, lines = self.run_checker(spec)
        self.assertEqual(code, 1)
        self.assertTrue(self.lines_with(lines, "error:", "missing section"))
        self.assertTrue(self.lines_with(lines, "error:", "## 2. Summary"))

    def test_check_spec_reports_a_leftover_placeholder(self):
        spec = COMPLETE.replace("Add a login page.", "{{fill this in}}")
        code, lines = self.run_checker(spec)
        self.assertEqual(code, 1)
        self.assertTrue(self.lines_with(lines, "error:", "placeholder"))
        self.assertTrue(self.lines_with(lines, "error:", "line 5"))

    def test_reports_sections_out_of_order(self):
        spec = "## 2. Summary\n\nThe page accepts a name.\n\n## 1. Request\n\nAdd a login page.\n"
        code, lines = self.run_checker(spec)
        self.assertEqual(code, 1)
        self.assertTrue(self.lines_with(lines, "error:", "out of order"))

    def test_reports_an_unnumbered_heading(self):
        spec = COMPLETE + "\n## Notes\n\nNothing else.\n"
        code, lines = self.run_checker(spec)
        self.assertEqual(code, 1)
        self.assertTrue(self.lines_with(lines, "error:", "unnumbered heading"))

    def test_reports_an_unfinished_marker(self):
        spec = COMPLETE.replace("Add a login page.", "Add a login page. TODO confirm the route.")
        code, lines = self.run_checker(spec)
        self.assertEqual(code, 1)
        self.assertTrue(self.lines_with(lines, "error:", "unfinished marker"))

    def test_ignores_a_marker_inside_a_longer_word(self):
        spec = COMPLETE.replace("Add a login page.", "Add a TODOS list.")
        code, lines = self.run_checker(spec)
        self.assertEqual(code, 0)
        self.assertFalse(self.lines_with(lines, "error:", "unfinished marker"))

    def test_reports_an_empty_section(self):
        spec = "# Spec\n\n## 1. Request\n\n\n## 2. Summary\n\nThe page accepts a name.\n"
        code, lines = self.run_checker(spec)
        self.assertEqual(code, 1)
        self.assertTrue(self.lines_with(lines, "error:", "empty section"))

    def test_reports_an_empty_last_section(self):
        spec = "# Spec\n\n## 1. Request\n\nAdd a login page.\n\n## 2. Summary\n\n"
        code, lines = self.run_checker(spec)
        self.assertEqual(code, 1)
        self.assertTrue(self.lines_with(lines, "error:", "empty section"))

    def test_warns_about_a_vague_word_without_failing(self):
        spec = COMPLETE.replace("Add a login page.", "Add a Seamless login page.")
        code, lines = self.run_checker(spec)
        self.assertEqual(code, 0)
        self.assertTrue(self.lines_with(lines, "warning:", "vague word"))

    def test_warns_about_more_than_three_open_questions(self):
        template = TEMPLATE + "\n## 3. Open questions\n\n{{questions}}\n"
        questions = "".join("- Question {}?\n".format(number) for number in range(1, 5))
        spec = COMPLETE + "\n## 3. Open questions\n\n" + questions
        code, lines = self.run_checker(spec, template)
        self.assertEqual(code, 0)
        self.assertTrue(self.lines_with(lines, "warning:", "open questions"))

    def test_allows_three_open_questions(self):
        template = TEMPLATE + "\n## 3. Open questions\n\n{{questions}}\n"
        questions = "".join("- Question {}?\n".format(number) for number in range(1, 4))
        spec = COMPLETE + "\n## 3. Open questions\n\n" + questions
        code, lines = self.run_checker(spec, template)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [])

    def test_returns_two_when_an_argument_is_missing(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            template_path = pathlib.Path(directory) / "template.md"
            template_path.write_text(TEMPLATE, encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = module.main(["--template", str(template_path)])
        self.assertEqual(code, 2)

    def test_returns_two_when_the_spec_is_unreadable(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as directory:
            template_path = pathlib.Path(directory) / "template.md"
            template_path.write_text(TEMPLATE, encoding="utf-8")
            missing = pathlib.Path(directory) / "absent.md"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = module.main(["--template", str(template_path), str(missing)])
        self.assertEqual(code, 2)

    def test_check_returns_severity_line_and_message(self):
        module = self.load()
        findings = module.check(TEMPLATE, "# Spec\n\n## 1. Request\n\nAdd a login page.\n")
        self.assertIsInstance(findings, tuple)
        self.assertIn(("error", 0, "missing section: ## 2. Summary"), findings)


if __name__ == "__main__":
    unittest.main()
