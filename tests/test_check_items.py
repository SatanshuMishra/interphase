import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

SPEC_TEXT = (
    "# Demo spec\n\n## 1. Interface\n\nThe shared interface.\n\n## 2. Client\n\nThe client.\n\n"
    "## 3. Acceptance criteria\n\n### 3.1 Interface exists\n\nThe interface can be imported.\n\n"
    "### 3.2 Client calls it\n\nThe client calls the interface.\n"
)
AMENDMENT_SPEC_TEXT = (
    "# Demo fix\n\n## 6. Requirements\n\nThe app returns the total it is given.\n\n"
    "## 7. Acceptance criteria\n\n### 7.1 The total adds up\n\nThe total is unchanged.\n\n"
    "### 7.2 A negative total is zero\n\nThe app returns zero for a negative total.\n"
)
AMENDED_RECORD = {
    "status": "handed-off",
    "environments": [{"name": "unit-tests", "what": "python3 -m unittest on macOS", "builder_runs": True}],
    "facts": [],
    "criteria": [
        {
            "number": "7.1",
            "title": "The total adds up",
            "text": "Given a total, when the app returns it, then it is unchanged.",
            "where": ["unit-tests"],
            "tests": [
                {
                    "file": "tests/test_app.py",
                    "name": "test_total",
                    "given": "a total of 3",
                    "expect": "3 is returned",
                    "env": "unit-tests",
                    "step": "build-app",
                }
            ],
        },
        {
            "number": "7.2",
            "title": "A negative total is zero",
            "text": "Given a negative total, when the app returns it, then it is zero.",
            "where": ["unit-tests"],
            "tests": [
                {
                    "file": "tests/test_fix.py",
                    "name": "test_negative_total",
                    "given": "a total of -3",
                    "expect": "0 is returned",
                    "env": "unit-tests",
                    "step": "fix-app",
                }
            ],
        },
    ],
    "steps": [
        {
            "name": "build-app",
            "files": ["src/app.py", "tests/test_app.py"],
            "criteria": ["7.1"],
            "task": "Build the app.",
        },
        {
            "name": "fix-app",
            "files": ["src/app.py", "tests/test_fix.py"],
            "criteria": ["7.2"],
            "task": "Return zero for a negative total.",
            "amendment": 1,
            "after": ["build-app"],
        },
    ],
}


class ScriptLoader:
    def load(self, name="check_items"):
        root = pathlib.Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(name, str(root / "scripts" / (name + ".py")))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class CheckItemsTest(ScriptLoader, unittest.TestCase):
    def steps(self, spec_path, sha):
        source = {"path": str(spec_path), "sha256": sha}
        return [
            {
                "name": "interface",
                "task": "Define the interface.",
                "files": ["src/interface.py", "tests/test_interface.py"],
                "source": source,
                "acceptance": [{"file": "tests/test_interface.py", "test": "test_interface_exists"}],
                "contract_group": "api",
                "type": "contract",
                "spec_ref": ["1", "3.1"],
            },
            {
                "name": "client",
                "task": "Build the client.",
                "files": ["src/client.py", "tests/test_client.py"],
                "source": dict(source),
                "acceptance": [{"file": "tests/test_client.py", "test": "test_client_calls_the_interface"}],
                "contract_group": "api",
                "after": ["interface"],
                "spec_ref": ["2", "3.2"],
            },
        ]

    def run_check(self, change=lambda steps: steps, spec_text=SPEC_TEXT, raw=None):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = pathlib.Path(tmp) / "demo.md"
            spec_path.write_text(spec_text, encoding="utf-8")
            sha = hashlib.sha256(spec_path.read_bytes()).hexdigest()
            items_path = pathlib.Path(tmp) / "demo.items.json"
            content = raw if raw is not None else json.dumps(change(self.steps(spec_path, sha)))
            items_path.write_text(content, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = module.main([str(items_path)])
        lines = out.getvalue().splitlines()
        return (
            code,
            tuple(line for line in lines if line.startswith("error: ")),
            tuple(line for line in lines if line.startswith("warning: ")),
        )

    def assert_error(self, change, fragment, spec_text=SPEC_TEXT):
        code, errors, _ = self.run_check(change, spec_text)
        self.assertEqual(code, 1)
        self.assertTrue(any(fragment in line for line in errors), errors)

    def test_check_items_accepts_a_valid_file(self):
        code, errors, _ = self.run_check()
        self.assertEqual(code, 0)
        self.assertEqual(errors, ())

    def test_check_items_reports_a_sha256_mismatch(self):
        def change(steps):
            sha = steps[0]["source"]["sha256"]
            flipped = ("1" if sha[0] == "0" else "0") + sha[1:]
            source = {"path": steps[0]["source"]["path"], "sha256": flipped}
            return [dict(step, source=source) for step in steps]

        self.assert_error(change, "sha256 mismatch")

    def test_check_items_rejects_a_type_other_than_contract(self):
        self.assert_error(lambda steps: [dict(steps[0], type="feature"), steps[1]], "type")

    def test_check_items_reports_an_after_cycle(self):
        self.assert_error(lambda steps: [dict(steps[0], after=["client"]), steps[1]], "cycle")

    def test_check_items_reports_an_unknown_field(self):
        self.assert_error(lambda steps: [dict(steps[0], owner="someone"), steps[1]], "unknown field")

    def test_check_items_reports_a_missing_required_field(self):
        def change(steps):
            return [{key: value for key, value in steps[0].items() if key != "task"}, steps[1]]

        self.assert_error(change, "task")

    def test_check_items_reports_a_bad_name(self):
        self.assert_error(lambda steps: [steps[0], dict(steps[1], name="Client_Step")], "kebab-case")

    def test_check_items_reports_an_absolute_path_in_files(self):
        def change(steps):
            return [steps[0], dict(steps[1], files=["/src/client.py", "tests/test_client.py"])]

        self.assert_error(change, "absolute")

    def test_check_items_reports_an_acceptance_file_missing_from_files(self):
        self.assert_error(lambda steps: [steps[0], dict(steps[1], files=["src/client.py"])], "not in its files")

    def test_check_items_reports_an_unknown_after_name(self):
        self.assert_error(lambda steps: [steps[0], dict(steps[1], after=["interface", "server"])], "unknown step")

    def test_check_items_reports_differing_sources(self):
        def change(steps):
            other = {"path": steps[1]["source"]["path"] + ".other", "sha256": steps[1]["source"]["sha256"]}
            return [steps[0], dict(steps[1], source=other)]

        self.assert_error(change, "source differs")

    def test_check_items_reports_a_contract_step_without_a_group(self):
        def change(steps):
            first = {key: value for key, value in steps[0].items() if key != "contract_group"}
            second = {key: value for key, value in steps[1].items() if key != "contract_group"}
            return [first, second]

        self.assert_error(change, "no contract_group")

    def test_check_items_reports_a_group_member_that_does_not_reach_its_contract(self):
        def change(steps):
            return [steps[0], {key: value for key, value in steps[1].items() if key != "after"}]

        self.assert_error(change, "does not reach contract step")

    def test_check_items_reports_a_spec_ref_that_matches_no_heading(self):
        self.assert_error(lambda steps: [steps[0], dict(steps[1], spec_ref=["9"])], "matches no numbered heading")

    def test_check_items_accepts_a_spec_ref_of_a_dotted_subsection(self):
        spec_text = SPEC_TEXT + "\n### 2.1 Retries\n\nThe client retries.\n"
        code, errors, warnings = self.run_check(
            lambda steps: [steps[0], dict(steps[1], spec_ref=["2.1", "3.2"])], spec_text
        )
        self.assertEqual(code, 0)
        self.assertEqual(errors, ())
        self.assertFalse(any("unclaimed" in line for line in warnings), warnings)

    def test_check_items_no_longer_warns_about_unclaimed_sections(self):
        spec_text = SPEC_TEXT + "\n## 4. Extras\n\nNobody builds this.\n"
        code, errors, warnings = self.run_check(spec_text=spec_text)
        self.assertEqual(code, 0)
        self.assertEqual(errors, ())
        self.assertFalse(any("unclaimed" in line for line in warnings), warnings)

    def test_check_items_reports_an_unclaimed_acceptance_criterion(self):
        self.assert_error(lambda steps: [steps[0], dict(steps[1], spec_ref=["2"])], "acceptance criterion 3.2")

    def test_check_items_warns_about_a_step_that_claims_no_criterion(self):
        def change(steps):
            docs = {
                "name": "docs",
                "task": "Write the guide.",
                "files": ["docs/guide.md"],
                "source": dict(steps[0]["source"]),
                "acceptance": [],
                "spec_ref": ["1"],
            }
            return steps + [docs]

        code, _, warnings = self.run_check(change)
        self.assertEqual(code, 0)
        self.assertTrue(
            any("claims no acceptance criterion" in line and "docs" in line for line in warnings), warnings
        )

    def extra_step(self, steps, **fields):
        extra = {
            "name": "extra",
            "task": "Extend the client.",
            "files": ["src/client.py", "tests/test_extra.py"],
            "source": dict(steps[0]["source"]),
            "acceptance": [{"file": "tests/test_extra.py", "test": "test_extra"}],
            "spec_ref": ["3.2"],
        }
        return steps + [dict(extra, **fields)]

    def test_check_items_warns_about_a_shared_file_without_order(self):
        code, _, warnings = self.run_check(lambda steps: self.extra_step(steps))
        self.assertEqual(code, 0)
        self.assertTrue(any("share file" in line and "src/client.py" in line for line in warnings), warnings)

    def test_check_items_accepts_a_shared_file_with_order(self):
        _, _, warnings = self.run_check(lambda steps: self.extra_step(steps, after=["client"]))
        self.assertFalse(any("share file" in line for line in warnings), warnings)

    def test_check_items_warns_about_an_export_file_not_ordered_last(self):
        def change(steps):
            return [dict(steps[0], files=steps[0]["files"] + ["src/__init__.py"]), steps[1]]

        code, _, warnings = self.run_check(change)
        self.assertEqual(code, 0)
        self.assertTrue(any("export file" in line and "src/__init__.py" in line for line in warnings), warnings)

    def test_check_items_ignores_non_modules_and_subfolders_for_export_files(self):
        def change(steps):
            return [
                dict(steps[0], files=steps[0]["files"] + ["src/__init__.py"]),
                dict(steps[1], files=["src/sub/deep.py", "src/data.json", "tests/test_client.py"]),
            ]

        _, _, warnings = self.run_check(change)
        self.assertFalse(any("export file" in line for line in warnings), warnings)

    def test_check_items_accepts_sub_criteria_claimed_one_by_one(self):
        spec_text = SPEC_TEXT + (
            "\n### 3.3 Retries\n\n### 3.3.1 First retry\n\nOne.\n\n### 3.3.2 Second retry\n\nTwo.\n"
        )
        code, errors, _ = self.run_check(
            lambda steps: [steps[0], dict(steps[1], spec_ref=["2", "3.2", "3.3.1", "3.3.2"])], spec_text
        )
        self.assertEqual(code, 0)
        self.assertFalse(any("acceptance criterion" in line for line in errors), errors)

    def test_check_items_reports_invalid_json(self):
        code, errors, _ = self.run_check(raw="[{not json")
        self.assertEqual(code, 1)
        self.assertTrue(any("not valid JSON" in line for line in errors), errors)


class AmendmentItemsTest(ScriptLoader, unittest.TestCase):
    def amendment_steps(self, spec_path, sha):
        return [
            {
                "name": "fix-app",
                "task": "Return zero for a negative total.",
                "files": ["src/app.py", "tests/test_fix.py"],
                "source": {"path": str(spec_path), "sha256": sha},
                "acceptance": [{"file": "tests/test_fix.py", "test": "test_negative_total"}],
                "spec_ref": ["7.2"],
            }
        ]

    def run_amendment(self, arguments, change=lambda steps: steps):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = pathlib.Path(tmp) / "demo.md"
            spec_path.write_text(AMENDMENT_SPEC_TEXT, encoding="utf-8")
            sha = hashlib.sha256(spec_path.read_bytes()).hexdigest()
            items_path = pathlib.Path(tmp) / "demo.amend-1.items.json"
            items_path.write_text(json.dumps(change(self.amendment_steps(spec_path, sha))), encoding="utf-8")
            argv = [str(items_path) if argument == "ITEMS" else argument for argument in arguments]
            out = io.StringIO()
            err = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = module.main(argv)
        return code, out.getvalue().splitlines(), err.getvalue()

    def test_amendment_option_skips_unclaimed_criteria(self):
        code, lines, _ = self.run_amendment(["--amendment", "ITEMS"])
        self.assertEqual(code, 0, lines)
        self.assertFalse(any("7.1" in line for line in lines), lines)

    def test_amendment_option_after_the_path_is_accepted(self):
        code, lines, _ = self.run_amendment(["ITEMS", "--amendment"])
        self.assertEqual(code, 0, lines)
        self.assertFalse(any("7.1" in line for line in lines), lines)

    def test_amendment_option_keeps_other_errors(self):
        code, lines, _ = self.run_amendment(["--amendment", "ITEMS"], lambda steps: [dict(steps[0], name="Fix_App")])
        self.assertEqual(code, 1, lines)
        self.assertTrue(any(line.startswith("error: ") and "step 'Fix_App'" in line for line in lines), lines)

    def test_rendered_amendment_passes_the_items_check(self):
        render_record = self.load("render_record")
        check_items = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            record_path = base / "demo.record.json"
            spec_path = base / "demo.md"
            items_path = base / "demo.amend-1.items.json"
            record_path.write_text(json.dumps(AMENDED_RECORD), encoding="utf-8")
            spec_path.write_text(AMENDMENT_SPEC_TEXT, encoding="utf-8")
            argv = ["--record", str(record_path), "--spec", str(spec_path), "--items", str(items_path)]
            rendered = io.StringIO()
            with contextlib.redirect_stdout(rendered), contextlib.redirect_stderr(rendered):
                render_code = render_record.main(argv + ["--amendment", "1"])
            checked = io.StringIO()
            with contextlib.redirect_stdout(checked), contextlib.redirect_stderr(checked):
                code = check_items.main(["--amendment", str(items_path)])
        self.assertEqual(render_code, 0, rendered.getvalue())
        lines = checked.getvalue().splitlines()
        self.assertEqual(code, 0, lines)
        self.assertFalse(any(line.startswith("error: ") for line in lines), lines)

    def test_amendment_option_twice_is_a_usage_error(self):
        code, _, err = self.run_amendment(["--amendment", "--amendment", "ITEMS"])
        self.assertEqual(code, 2)
        self.assertEqual(err.splitlines(), ["usage: python3 check_items.py [--amendment] ITEMS"])


if __name__ == "__main__":
    unittest.main()
