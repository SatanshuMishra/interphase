import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VARIATION = ROOT / "core" / "variation.md"

HEADINGS = (
    "## Kinds",
    "## Specify a population",
    "## Grade and pass",
    "## Keep the acceptance set untouched",
    "## Bugs",
    "## Measured on a device",
    "## In the record",
)


def read_variation():
    return VARIATION.read_text(encoding="utf-8")


def section(text, heading):
    lines = text.splitlines()
    start = lines.index(heading) + 1
    rest = lines[start:]
    end = next((i for i, line in enumerate(rest) if line.startswith("## ")), len(rest))
    return "\n".join(rest[:end])


class CoreVariationTest(unittest.TestCase):
    def test_variation_has_title_and_every_section_in_order(self):
        text = read_variation()
        lines = text.splitlines()
        self.assertEqual(lines[0], "# Varying behaviour")
        positions = tuple(lines.index(h) if h in lines else -1 for h in HEADINGS)
        self.assertNotIn(-1, positions)
        self.assertEqual(list(positions), sorted(positions))

    def test_variation_names_the_three_kinds_and_their_signals(self):
        kinds = section(read_variation(), "## Kinds").lower()
        for needle in (
            "open-ended input",
            "speech",
            "free text",
            "gestures",
            "speech or text-parsing api",
            "varying output",
            "model calls",
            "sampling",
            "language-model or machine-learning api",
            "temperature",
            "results measured on a device",
            "frame rate",
            "timing",
            "touch input",
            "performance target",
            "defect seen only on hardware",
            "without waiting for the user to mention it",
        ):
            self.assertIn(needle, kinds, needle)

    def test_variation_specifies_a_population_with_a_held_out_set(self):
        population = section(read_variation(), "## Specify a population").lower()
        for needle in (
            "the ways its input varies",
            "phrasing",
            "speaker",
            "accent",
            "noise",
            "pacing",
            "document state",
            "spread the cases across those ways",
            "held-out set during the interview",
            "nothing is ever tuned on",
            "a sample of at least one held-out case for each way the input varies",
            "get approval",
            "in full in the task of the step that tests them",
            "the way a bug's draft test is carried",
            "variation section",
            "not applicable: <reason>",
        ):
            self.assertIn(needle, population, needle)

    def test_variation_requires_outcome_grading_repeated_runs_and_rates(self):
        grading = section(read_variation(), "## Grade and pass").lower()
        for needle in (
            "grade the outcome",
            "never the exact output text",
            "run each case more than once",
            "pass on a stated pass rate",
            "harmful class of failure",
            "editing the wrong passage",
            "zero times",
        ):
            self.assertIn(needle, grading, needle)

    def test_variation_forbids_tuning_on_the_acceptance_set_and_requires_a_leak_test(self):
        text = section(read_variation(), "## Keep the acceptance set untouched").lower()
        for needle in (
            "no step tunes a prompt, rule or threshold against the cases that accept it",
            "development cases",
            "leak test",
            "fails when any held-out case appears in a prompt or rule",
        ):
            self.assertIn(needle, text, needle)

    def test_variation_reproduces_a_bug_as_its_class(self):
        bugs = section(read_variation(), "## Bugs").lower()
        for needle in (
            "reproduce a bug in varying behaviour as its class",
            "generate variants of the failing case",
            "each way its input varies",
            "record the failure rate",
            "pass rate on held-out variants",
            "never by the reported example alone",
        ):
            self.assertIn(needle, bugs, needle)

    def test_variation_measures_device_results_repeatedly(self):
        device = section(read_variation(), "## Measured on a device").lower()
        for needle in (
            "measure repeatedly",
            "state the statistic",
            "95th percentile",
            "number of runs",
            "unproven",
            "measurement method",
            "double click",
            "drag",
            "edge swipe",
            "long press",
            "hand check",
            "never report it as a defect",
        ):
            self.assertIn(needle, device, needle)

    def test_variation_documents_the_record_keys(self):
        record = section(read_variation(), "## In the record")
        for needle in (
            "`varies`",
            "`input`",
            "`output`",
            "`measured`",
            "`cases`",
            "`runs`",
            "`pass_rate`",
            "check_record.py",
            "Population line",
        ):
            self.assertIn(needle, record, needle)

    def test_variation_names_no_consuming_tool(self):
        self.assertNotIn("mitosis", read_variation().lower())


if __name__ == "__main__":
    unittest.main()
