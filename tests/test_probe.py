import contextlib
import importlib.util
import io
import os
import pathlib
import shutil
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


def seed_repository(root, name="repo"):
    repo = pathlib.Path(root) / name
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


def load_probe():
    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "probe.py"
    spec = importlib.util.spec_from_file_location("probe_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_main(module, argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = module.main(argv)
    return code, buffer.getvalue()


def created_path(output):
    return pathlib.Path(output.strip().splitlines()[-1])


def tree_state(repo):
    return (
        git(repo, "status", "--porcelain"),
        git(repo, "rev-parse", "HEAD"),
        git(repo, "branch", "--list"),
    )


class ProbeTest(unittest.TestCase):
    def remove_probe(self, probe, repo, path):
        run_main(probe, ["remove", "--repo", str(repo), "--path", str(path)])
        shutil.rmtree(path, ignore_errors=True)

    def test_probe_create_leaves_the_main_tree_untouched(self):
        probe = load_probe()
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            before = tree_state(repo)
            code, output = run_main(probe, ["create", "--repo", str(repo)])
            self.assertEqual(code, 0, output)
            path = created_path(output)
            try:
                self.assertEqual(tree_state(repo), before)
                self.assertTrue(path.name.startswith("interphase-probe-"))
                self.assertEqual((path / "seed.txt").read_text(encoding="utf-8"), "seed\n")
            finally:
                self.remove_probe(probe, repo, path)
            self.assertFalse(path.exists())

    def test_probe_remove_refuses_the_main_tree(self):
        probe = load_probe()
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root, "interphase-probe-main")
            code, output = run_main(probe, ["remove", "--repo", str(repo), "--path", str(repo)])
            self.assertEqual(code, 1, output)
            self.assertTrue(repo.is_dir())
            self.assertTrue((repo / "seed.txt").is_file())

    def test_probe_remove_refuses_a_path_without_the_probe_prefix(self):
        probe = load_probe()
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            code, _ = run_main(probe, ["remove", "--repo", str(repo), "--path", str(repo)])
            self.assertEqual(code, 1)
            self.assertTrue((repo / "seed.txt").is_file())

    def test_probe_with_uncommitted_carries_edits_into_the_probe(self):
        probe = load_probe()
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            (repo / "seed.txt").write_text("edited\n", encoding="utf-8")
            (repo / "fresh.txt").write_text("fresh\n", encoding="utf-8")
            before = tree_state(repo)
            code, output = run_main(probe, ["create", "--repo", str(repo), "--with-uncommitted"])
            self.assertEqual(code, 0, output)
            path = created_path(output)
            try:
                self.assertEqual((path / "seed.txt").read_text(encoding="utf-8"), "edited\n")
                self.assertEqual((path / "fresh.txt").read_text(encoding="utf-8"), "fresh\n")
                self.assertEqual(tree_state(repo), before)
                self.assertEqual((repo / "seed.txt").read_text(encoding="utf-8"), "edited\n")
            finally:
                self.remove_probe(probe, repo, path)

    def test_probe_without_uncommitted_starts_from_head(self):
        probe = load_probe()
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            (repo / "seed.txt").write_text("edited\n", encoding="utf-8")
            code, output = run_main(probe, ["create", "--repo", str(repo)])
            self.assertEqual(code, 0, output)
            path = created_path(output)
            try:
                self.assertEqual((path / "seed.txt").read_text(encoding="utf-8"), "seed\n")
            finally:
                self.remove_probe(probe, repo, path)

    def test_probe_list_prints_the_probe_path(self):
        probe = load_probe()
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            code, output = run_main(probe, ["create", "--repo", str(repo)])
            self.assertEqual(code, 0, output)
            path = created_path(output)
            try:
                code, listing = run_main(probe, ["list", "--repo", str(repo)])
                self.assertEqual(code, 0)
                listed = [os.path.realpath(line) for line in listing.splitlines() if line]
                self.assertEqual(listed, [os.path.realpath(str(path))])
            finally:
                self.remove_probe(probe, repo, path)
            self.assertEqual(run_main(probe, ["list", "--repo", str(repo)])[1].strip(), "")

    def test_tree_guard_reports_a_leftover_probe_from_create(self):
        probe = load_probe()
        guard_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "tree_guard.py"
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            environment = clean_environment()
            subprocess.run(
                [sys.executable, str(guard_path), "snapshot", "--repo", str(repo), "--out", str(snapshot)],
                check=True,
                stdout=subprocess.PIPE,
                env=environment,
            )
            code, output = run_main(probe, ["create", "--repo", str(repo)])
            self.assertEqual(code, 0, output)
            path = created_path(output)
            try:
                result = subprocess.run(
                    [sys.executable, str(guard_path), "verify", "--repo", str(repo), "--snapshot", str(snapshot)],
                    stdout=subprocess.PIPE,
                    env=environment,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("leftover probe", result.stdout.decode())
            finally:
                self.remove_probe(probe, repo, path)
            final = subprocess.run(
                [sys.executable, str(guard_path), "verify", "--repo", str(repo), "--snapshot", str(snapshot)],
                stdout=subprocess.PIPE,
                env=environment,
            )
            self.assertEqual(final.returncode, 0, final.stdout.decode())

    def test_probe_exits_2_outside_a_git_repository(self):
        script = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "probe.py"
        with tempfile.TemporaryDirectory() as root:
            plain = pathlib.Path(root) / "plain"
            plain.mkdir()
            environment = dict(clean_environment(), GIT_CEILING_DIRECTORIES=str(pathlib.Path(root).resolve()))
            for command in (["create"], ["list"], ["remove", "--path", str(plain)]):
                result = subprocess.run(
                    [sys.executable, str(script), *command[:1], "--repo", str(plain), *command[1:]],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=environment,
                )
                self.assertEqual(result.returncode, 2, command)

    def test_probe_exits_2_on_a_usage_error(self):
        probe = load_probe()
        with contextlib.redirect_stderr(io.StringIO()):
            code, _ = run_main(probe, ["remove", "--repo", "."])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
