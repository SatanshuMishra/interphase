import pathlib
import unittest

SCRIPT = "lock_feasibility.py"
PHASE_FOUR = "## Phase 4: Interview"
PHASE_SIX = "## Phase 6: Design the Steps"
INTERVIEW_RECORD = "## Interview record"
ROW_FIELDS = ("`loads`", "`needs`", "`absent`", "`unaffected`")
RECORD_FIELDS = ROW_FIELDS + ("`feasibility`",)


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def read(relative):
    return (repo_root() / relative).read_text(encoding="utf-8")


def section(relative, heading):
    lines = read(relative).splitlines()
    start = lines.index(heading) + 1
    end = start
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    return "\n".join(lines[start:end])


def bullets(body):
    return [line for line in body.splitlines() if line.startswith("- ")]


def positions(items, *parts):
    return [position for position, item in enumerate(items) if all(part in item for part in parts)]


class FeasibilityInstructionsTest(unittest.TestCase):
    def test_phase_six_runs_lock_feasibility_before_the_complete_check(self):
        steps = bullets(section("core/phases.md", PHASE_SIX))
        feasibility = positions(steps, SCRIPT, "--record", "--repo")
        probes = positions(steps, "surface_probe.py")
        complete = positions(steps, "check_record.py", "--complete")
        self.assertTrue(feasibility, steps)
        self.assertTrue(probes, steps)
        self.assertTrue(complete, steps)
        self.assertGreater(feasibility[0], probes[-1])
        self.assertLess(feasibility[0], complete[0])

    def test_phase_four_names_the_row_and_seam_fields(self):
        body = section("core/phases.md", PHASE_FOUR)
        for field in ROW_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, body)

    def test_items_guide_lists_the_new_record_fields(self):
        body = section("core/items.md", INTERVIEW_RECORD)
        for field in RECORD_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, body)

    def test_items_guide_describes_one_check_author_per_msp(self):
        text = read("core/items.md").replace("`", "")
        self.assertIn("one check-author Step per msp", text)
        self.assertIn("check-author-<msp>", text)

    def test_brief_lane_runs_lock_feasibility(self):
        phase_six = [line for line in read("core/brief.md").splitlines() if line.startswith("- Phase 6:")]
        self.assertEqual(len(phase_six), 1, phase_six)
        self.assertIn(SCRIPT, phase_six[0])

    def test_readme_names_lock_feasibility(self):
        self.assertIn(SCRIPT, read("README.md"))


if __name__ == "__main__":
    unittest.main()
