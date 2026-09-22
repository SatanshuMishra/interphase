import contextlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ISOLATING_VARIABLES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR")


def clean_environment():
    return {key: value for key, value in os.environ.items() if key not in ISOLATING_VARIABLES}


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean_environment(),
    ).stdout.decode()


def seed_repository(root):
    repo = pathlib.Path(root) / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    git(repo, "add", "seed.txt")
    git(
        repo,
        "-c", "user.name=t",
        "-c", "user.email=t@example.com",
        "-c", "commit.gpgsign=false",
        "commit", "-q", "--no-verify", "-m", "chore: seed",
    )
    return repo


def load_script(name):
    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_main(module, argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = module.main(argv)
    return code, buffer.getvalue()


class TreeGuardTest(unittest.TestCase):
    def test_tree_guard_passes_an_untouched_tree(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 0, output)
            self.assertNotIn("error:", output)

    def test_tree_guard_reports_an_edited_tracked_file(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            (repo / "seed.txt").write_text("edited\n", encoding="utf-8")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 1)
            self.assertTrue(any(line.startswith("error: ") for line in output.splitlines()), output)

    def test_tree_guard_snapshot_records_every_field(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])
            data = json.loads(snapshot.read_text(encoding="utf-8"))
            self.assertEqual(
                set(data),
                {"head", "branch", "status", "diff_sha256", "stash", "worktrees"},
            )
            self.assertEqual(data["head"], git(repo, "rev-parse", "HEAD").strip())
            self.assertTrue(data["branch"].startswith("refs/heads/"))
            self.assertEqual(data["status"], [])
            self.assertEqual(len(data["diff_sha256"]), 64)

    def test_tree_guard_reports_a_new_untracked_file(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])
            (repo / "extra.txt").write_text("extra\n", encoding="utf-8")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 1)
            self.assertIn("status", output)

    def test_tree_guard_reports_a_leftover_probe_worktree(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])
            probe = pathlib.Path(root) / "interphase-probe-left"
            git(repo, "worktree", "add", "--detach", str(probe), "HEAD")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 1)
            self.assertIn("leftover probe", output)

    def test_tree_guard_exits_2_outside_a_git_repository(self):
        script = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "tree_guard.py"
        with tempfile.TemporaryDirectory() as root:
            plain = pathlib.Path(root) / "plain"
            plain.mkdir()
            environment = dict(clean_environment(), GIT_CEILING_DIRECTORIES=str(pathlib.Path(root).resolve()))
            result = subprocess.run(
                [sys.executable, str(script), "snapshot", "--repo", str(plain), "--out", str(pathlib.Path(root) / "g.json")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )
            self.assertEqual(result.returncode, 2)

    def test_tree_guard_exits_2_on_an_unreadable_snapshot(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            broken = pathlib.Path(root) / "broken.json"
            broken.write_text("not json", encoding="utf-8")
            code, _ = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(broken)])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
