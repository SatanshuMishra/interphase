import contextlib
import importlib.util
import io
import pathlib
import tempfile
import unittest

TEMPLATE = "# Spec\n\n## 1. Request\n\n{{request}}\n\n## 2. Summary\n\n{{summary}}\n"
COMPLETE = "# Spec\n\n## 1. Request\n\nAdd a login page.\n\n## 2. Summary\n\nThe page accepts a name and a password.\n"
CRITERIA_TEMPLATE = "# Spec\n\n## 1. Request\n\n{{request}}\n\n## 5. Test seams\n\n### 5.1 {{name}}\n\n{{check}}\n"
NO_SECTIONS = "# Spec\n"
INTENT_SPEC = (
    "# Spec\n"
    "\n"
    "## 1. Problem\n"
    "\n"
    "Totals are wrong.\n"
    "\n"
    "## 2. Intent\n"
    "\n"
    "- I1 Goal: the app returns totals.\n"
    "- I2 Constraint: totals stay in cents.\n"
    "\n"
    "## 4. Decisions\n"
    "\n"
    "The app sums in cents (relies on I2).\n"
    "\n"
    "### Reuse and change\n"
    "\n"
    "- Reused as is: the total_of function\n"
    "\n"
    "### Assumptions\n"
    "\n"
    "- A negative total is zero (relies on I1)\n"
    "\n"
    "## 5. Test seams\n"
    "\n"
    "### 5.1 Totals add up\n"
    "\n"
    "Given a total, the app returns it.\n"
)
TEMPLATES = ("spec-brief.md", "spec-bug.md", "spec-feature.md", "spec-project.md", "spec-prototype.md")


class SpecFixture:
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

    def checked(self, spec_text):
        return self.run_checker(spec_text, NO_SECTIONS)


class CheckSpecTest(SpecFixture, unittest.TestCase):
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

    def test_check_spec_reports_test_seams_without_a_numbered_criterion(self):
        spec = "# Spec\n\n## 1. Request\n\nAdd a login page.\n\n## 5. Test seams\n\nThe page loads.\n"
        code, lines = self.run_checker(spec, CRITERIA_TEMPLATE)
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["error: line 7: test seams has no numbered criterion heading such as ### 5.1"])

    def test_criterion_numbered_for_another_section_is_reported(self):
        spec = "# Spec\n\n## 1. Request\n\nAdd a login page.\n\n## 5. Test seams\n\n### 2.1 Page loads\n\nThe page loads.\n"
        code, lines = self.run_checker(spec, CRITERIA_TEMPLATE)
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["error: line 7: test seams has no numbered criterion heading such as ### 5.1"])

    def test_check_spec_accepts_numbered_test_seams_criteria(self):
        spec = (
            "# Spec\n\n## 1. Request\n\nAdd a login page.\n\n## 5. Test seams\n\n"
            "Seams:\n- `unit-tests`: the login route. Catches: a wrong redirect. Misses: the page layout.\n\n"
            "### 5.1 Page loads\n\nThe page loads.\n"
        )
        code, lines = self.run_checker(spec, CRITERIA_TEMPLATE)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [])

    def test_acceptance_criteria_section_is_no_longer_checked_for_criteria(self):
        spec = "# Spec\n\n## 1. Request\n\nAdd a login page.\n\n## 2. Acceptance criteria\n\nThe page loads.\n"
        self.assertEqual(self.checked(spec), (0, []))

    def test_seam_sections_finds_only_test_seams(self):
        module = self.load()
        lines = tuple(INTENT_SPEC.replace("## 4. Decisions", "## 4. Acceptance criteria").splitlines())
        self.assertEqual(module.seam_sections(module.numbered_headings(lines)), ((24, "5"),))
        self.assertFalse(hasattr(module, "acceptance_sections"))

    def test_every_template_has_one_test_seams_and_one_intent_section(self):
        module = self.load()
        root = pathlib.Path(__file__).resolve().parents[1]
        for name in TEMPLATES:
            with self.subTest(template=name):
                lines = tuple((root / "core" / "templates" / name).read_text(encoding="utf-8").splitlines())
                headings = module.numbered_headings(lines)
                self.assertEqual(len(module.seam_sections(headings)), 1)
                self.assertEqual(sum(1 for _, heading in headings if module.heading_title(heading) == "Intent"), 1)
                self.assertIn("### Assumptions", lines)

    def test_warns_about_a_vague_word_without_failing(self):
        spec = COMPLETE.replace("Add a login page.", "Add a Seamless login page.")
        code, lines = self.run_checker(spec)
        self.assertEqual(code, 0)
        self.assertTrue(self.lines_with(lines, "warning:", "vague word"))

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


class IntentSpecTest(SpecFixture, unittest.TestCase):
    def test_spec_with_intent_lines_and_cited_assumptions_passes(self):
        self.assertEqual(self.checked(INTENT_SPEC), (0, []))

    def test_spec_without_an_intent_section_needs_no_intent_line(self):
        self.assertEqual(self.checked(COMPLETE), (0, []))

    def test_intent_section_without_an_intent_line_is_an_error(self):
        spec = INTENT_SPEC.replace(
            "- I1 Goal: the app returns totals.\n- I2 Constraint: totals stay in cents.\n",
            "The goal is correct totals.\n",
        ).replace(" (relies on I2)", "").replace("- A negative total is zero (relies on I1)", "- None")
        code, lines = self.checked(spec)
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["error: line 7: intent has no line such as - I1 Goal: <goal>"])

    def test_intent_line_shapes(self):
        accepted = ("- I1 Goal: totals", "- I12 Constraint: cents", "- I3 x")
        rejected = ("-I1 Goal: totals", "* I1 Goal: totals", "- i1 Goal: totals", "- Goal: totals", "  - I1 Goal: totals")
        for line in accepted:
            with self.subTest(line=line):
                spec = "# Spec\n\n## 2. Intent\n\n" + line + "\n"
                self.assertEqual(self.checked(spec), (0, []))
        for line in rejected:
            with self.subTest(line=line):
                spec = "# Spec\n\n## 2. Intent\n\n" + line + "\n"
                self.assertEqual(
                    self.checked(spec), (1, ["error: line 3: intent has no line such as - I1 Goal: <goal>"])
                )

    def test_intent_line_outside_the_intent_section_does_not_count(self):
        spec = "# Spec\n\n## 1. Problem\n\n- I1 Goal: totals.\n\n## 2. Intent\n\nCorrect totals.\n"
        self.assertEqual(self.checked(spec), (1, ["error: line 7: intent has no line such as - I1 Goal: <goal>"]))

    def test_intent_title_in_other_case_is_checked(self):
        spec = "# Spec\n\n## 2. intent\n\nCorrect totals.\n"
        self.assertEqual(self.checked(spec), (1, ["error: line 3: intent has no line such as - I1 Goal: <goal>"]))

    def test_relying_on_an_unknown_intent_line_is_an_error(self):
        spec = INTENT_SPEC.replace("(relies on I2)", "(relies on I3)")
        self.assertEqual(self.checked(spec), (1, ["error: line 14: relies on I3, which is not an intent line"]))

    def test_unknown_intent_is_reported_in_any_section(self):
        spec = INTENT_SPEC.replace("Totals are wrong.", "Totals are wrong, which relies on I9.")
        self.assertEqual(self.checked(spec), (1, ["error: line 5: relies on I9, which is not an intent line"]))

    def test_longer_intent_id_is_not_a_shorter_one(self):
        spec = INTENT_SPEC.replace("(relies on I2)", "(relies on I10)")
        self.assertEqual(self.checked(spec), (1, ["error: line 14: relies on I10, which is not an intent line"]))

    def test_relies_on_in_other_case_is_checked(self):
        spec = INTENT_SPEC.replace("(relies on I2)", "(Relies on I2)")
        self.assertEqual(self.checked(spec), (0, []))
        spec = INTENT_SPEC.replace("(relies on I2)", "(RELIES ON I4)")
        self.assertEqual(self.checked(spec), (1, ["error: line 14: relies on I4, which is not an intent line"]))

    def test_each_unknown_citation_on_a_line_is_reported(self):
        spec = INTENT_SPEC.replace("(relies on I2)", "(relies on I1, relies on I5, relies on I6)")
        self.assertEqual(
            self.checked(spec),
            (
                1,
                [
                    "error: line 14: relies on I5, which is not an intent line",
                    "error: line 14: relies on I6, which is not an intent line",
                ],
            ),
        )

    def test_citation_without_an_intent_section_is_an_error(self):
        spec = "# Spec\n\n## 4. Decisions\n\nThe app sums in cents (relies on I1).\n"
        self.assertEqual(self.checked(spec), (1, ["error: line 5: relies on I1, which is not an intent line"]))


class AssumptionsSpecTest(SpecFixture, unittest.TestCase):
    def test_assumption_without_a_citation_is_an_error(self):
        spec = INTENT_SPEC.replace("- A negative total is zero (relies on I1)", "- A negative total is zero")
        self.assertEqual(
            self.checked(spec),
            (1, ["error: line 22: assumption cites no intent line; end it with (relies on I<n>)"]),
        )

    def test_none_line_needs_no_citation(self):
        spec = INTENT_SPEC.replace("- A negative total is zero (relies on I1)", "- None")
        self.assertEqual(self.checked(spec), (0, []))

    def test_each_uncited_assumption_is_reported(self):
        spec = INTENT_SPEC.replace(
            "- A negative total is zero (relies on I1)\n",
            "- A negative total is zero\n- Totals round down (relies on I2)\n- Totals print with two decimals\n",
        )
        self.assertEqual(
            self.checked(spec),
            (
                1,
                [
                    "error: line 22: assumption cites no intent line; end it with (relies on I<n>)",
                    "error: line 24: assumption cites no intent line; end it with (relies on I<n>)",
                ],
            ),
        )

    def test_assumption_citing_an_unknown_intent_line_is_reported_once(self):
        spec = INTENT_SPEC.replace("(relies on I1)", "(relies on I7)")
        self.assertEqual(self.checked(spec), (1, ["error: line 22: relies on I7, which is not an intent line"]))

    def test_lines_outside_assumptions_are_not_assumptions(self):
        spec = INTENT_SPEC.replace(
            "- A negative total is zero (relies on I1)\n",
            "- A negative total is zero (relies on I1)\n\n### Notes\n\n- Totals are logged\n",
        )
        self.assertEqual(self.checked(spec), (0, []))

    def test_assumptions_end_at_the_next_section(self):
        spec = INTENT_SPEC + "\n## 6. Out of scope\n\n- Currency conversion\n"
        self.assertEqual(self.checked(spec), (0, []))

    def test_only_bullet_lines_are_assumptions(self):
        spec = INTENT_SPEC.replace(
            "- A negative total is zero (relies on I1)\n",
            "- A negative total is zero (relies on I1)\n  - in every report\nTotals are rounded.\n",
        )
        self.assertEqual(self.checked(spec), (0, []))


if __name__ == "__main__":
    unittest.main()
