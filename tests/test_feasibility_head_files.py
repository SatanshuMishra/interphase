import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import test_lock_feasibility as lf

GITLINK = "tests/vendor"
FOREIGN_COMMIT = "1" * 40


class HeadFilesTest(lf.FeasibilityCase):
    def add_gitlink(self):
        self.git("update-index", "--add", "--cacheinfo", "160000,%s,%s" % (FOREIGN_COMMIT, GITLINK))
        self.git("commit", "-q", "-m", "submodule")

    def test_a_submodule_under_tests_leaves_feasibility_runnable(self):
        self.make_repository()
        self.add_gitlink()
        path = self.write_record(lf.feasible_record())
        code, output = self.feasibility(path)
        self.assertEqual(code, 0, output)

    def test_a_load_of_a_submodule_is_refused(self):
        self.make_repository()
        self.add_gitlink()
        entry = lf.record(lf.row([lf.TOTAL, GITLINK], [lf.TOTAL], lf.total_absent()), [lf.step(lf.STEP, [lf.TOTAL])])
        code, output = self.feasibility(self.write_record(entry))
        self.assertEqual(code, 1, output)
        self.assertIn(GITLINK, output)

    def test_a_load_differing_only_in_case_from_a_head_file_is_refused(self):
        self.make_repository()
        entry = lf.record(lf.row(["src/Total.py"], [lf.TOTAL], lf.total_absent()), [lf.step(lf.STEP, [lf.TOTAL])])
        code, output = self.feasibility(self.write_record(entry))
        self.assertEqual(code, 1, output)
        self.assertIn("src/Total.py", output)


if __name__ == "__main__":
    unittest.main()
