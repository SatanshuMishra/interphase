import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_render_record as rr

HELPER = "tests/helpers.py"
APP_TEST = "tests/test_app.py"
TUNE_TEST = "tests/test_tune.py"


def unlabelled(step):
    return {key: value for key, value in step.items() if key != "msp"}


def owner_unlabelled(source):
    return rr.replace_step(source, 0, unlabelled(source["steps"][0]))


def with_helper(source, loaded=True):
    first = source["criteria"][0]
    rows = [{**row, "loads": list(row["loads"]) + [HELPER]} if loaded else row for row in first["tests"]]
    criteria = [{**first, "tests": rows}] + source["criteria"][1:]
    return {**source, "criteria": criteria, "locked": [APP_TEST, HELPER]}


def named(items):
    return {entry["name"]: entry for entry in items}


class CheckAuthorScopeTest(rr.RenderFixture, unittest.TestCase):
    items_of = rr.CheckAuthorRenderTest.items_of

    def test_an_unlabelled_owner_among_labelled_steps_renders_the_check_author_as_before(self):
        items = named(self.items_of(owner_unlabelled(rr.record())))
        self.assertEqual(items["check-author"].get("msp"), "check-author")
        for name in ("build-app", "tune-app"):
            with self.subTest(step=name):
                self.assertEqual(items[name].get("after", [])[:1], ["check-author"])

    def test_a_locked_helper_no_row_holds_goes_to_the_check_author_of_its_loaders(self):
        items = named(self.items_of(with_helper(rr.record())))
        self.assertEqual(items["check-author-first"]["files"], [APP_TEST, HELPER])

    def test_a_locked_helper_no_row_holds_or_loads_is_refused_in_a_labelled_record(self):
        out = self.refused(with_helper(rr.record(), loaded=False), rr.SPEC_TEXT)
        self.assertIn(HELPER, out)

    def test_a_locked_helper_loaded_by_rows_of_two_msps_is_refused(self):
        source = with_helper(rr.record())
        second = {**source["criteria"][0]["tests"][0], "file": TUNE_TEST, "step": "tune-app"}
        criteria = [{**source["criteria"][0], "tests": source["criteria"][0]["tests"] + [second]}] + source["criteria"][1:]
        moved = {**source, "criteria": criteria, "locked": source["locked"] + [TUNE_TEST]}
        tuned = rr.replace_step(moved, 1, {**source["steps"][1], "msp": "second", "criteria": ["5.1", "5.2"]})
        out = self.refused(tuned, rr.SPEC_TEXT)
        self.assertIn(HELPER, out)


if __name__ == "__main__":
    unittest.main()
