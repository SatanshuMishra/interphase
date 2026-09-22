import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest

SPEC_TEXT = "# Demo spec\n\n## 1. Interface\n\nThe shared interface.\n\n## 2. Client\n\nThe client.\n"


class CheckItemsTest(unittest.TestCase):
    def load(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("check_items", str(root / "scripts" / "check_items.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

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
                "spec_ref": ["1"],
            },
            {
                "name": "client",
                "task": "Build the client.",
                "files": ["src/client.py", "tests/test_client.py"],
                "source": dict(source),
                "acceptance": [{"file": "tests/test_client.py", "test": "test_client_calls_the_interface"}],
                "contract_group": "api",
                "after": ["interface"],
                "spec_ref": ["2"],
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
            lambda steps: [steps[0], dict(steps[1], spec_ref=["2.1"])], spec_text
        )
        self.assertEqual(code, 0)
        self.assertEqual(errors, ())
        self.assertFalse(any("unclaimed" in line for line in warnings), warnings)

    def test_check_items_warns_about_an_unclaimed_section(self):
        spec_text = SPEC_TEXT + "\n## 3. Extras\n\nNobody builds this.\n"
        code, errors, warnings = self.run_check(spec_text=spec_text)
        self.assertEqual(code, 0)
        self.assertEqual(errors, ())
        self.assertTrue(any("unclaimed" in line and "3" in line for line in warnings), warnings)

    def test_check_items_reports_invalid_json(self):
        code, errors, _ = self.run_check(raw="[{not json")
        self.assertEqual(code, 1)
        self.assertTrue(any("not valid JSON" in line for line in errors), errors)


if __name__ == "__main__":
    unittest.main()
