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
from unittest import mock

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


def commit(repo, message):
    git(
        repo,
        "-c", "user.name=t",
        "-c", "user.email=t@example.com",
        "-c", "commit.gpgsign=false",
        "commit", "-q", "--no-verify", "-m", message,
    )


def write_file(path, text="cache\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def isolated_git_config(root):
    config_home = pathlib.Path(root) / "config-home"
    config_home.mkdir()
    return mock.patch.dict(
        os.environ,
        {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "XDG_CONFIG_HOME": str(config_home)},
    )


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

    def test_tree_guard_snapshot_creates_the_output_folder(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = repo / "docs" / "specs" / "guard.json"
            code, output = run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])
            self.assertEqual(code, 0, output)
            self.assertTrue(snapshot.is_file())

    def test_tree_guard_snapshot_records_every_field(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])
            data = json.loads(snapshot.read_text(encoding="utf-8"))
            self.assertEqual(
                set(data),
                {"head", "branch", "status", "diff_sha256", "stash", "worktrees", "owned", "caches"},
            )
            self.assertEqual(data["head"], git(repo, "rev-parse", "HEAD").strip())
            self.assertTrue(data["branch"].startswith("refs/heads/"))
            self.assertEqual(data["status"], [])
            self.assertEqual(len(data["diff_sha256"]), 64)
            self.assertEqual(data["owned"], [])
            self.assertEqual(data["caches"], [])

    def test_tree_guard_ignores_new_files_under_an_owned_prefix(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = repo / "docs" / "specs" / "demo.guard.json"
            code, output = run_main(
                guard,
                ["snapshot", "--repo", str(repo), "--owned", "docs/specs/demo.", "--out", str(snapshot)],
            )
            self.assertEqual(code, 0, output)
            (repo / "docs" / "specs" / "demo.md").write_text("spec\n", encoding="utf-8")
            (repo / "docs" / "specs" / "demo.decisions.md").write_text("decisions\n", encoding="utf-8")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 0, output)
            self.assertNotIn("error:", output)

    def test_tree_guard_ignores_edits_to_a_tracked_owned_file(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            spec = repo / "docs" / "specs" / "demo.md"
            spec.parent.mkdir(parents=True)
            spec.write_text("spec\n", encoding="utf-8")
            git(repo, "add", "docs/specs/demo.md")
            git(
                repo,
                "-c", "user.name=t",
                "-c", "user.email=t@example.com",
                "-c", "commit.gpgsign=false",
                "commit", "-q", "--no-verify", "-m", "docs: add demo spec",
            )
            snapshot = pathlib.Path(root) / "guard.json"
            code, output = run_main(
                guard,
                ["snapshot", "--repo", str(repo), "--owned", "docs/specs/demo.", "--out", str(snapshot)],
            )
            self.assertEqual(code, 0, output)
            spec.write_text("revised spec\n", encoding="utf-8")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 0, output)

    def test_tree_guard_still_reports_a_change_outside_the_owned_prefix(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            code, output = run_main(
                guard,
                ["snapshot", "--repo", str(repo), "--owned", "docs/specs/demo.", "--out", str(snapshot)],
            )
            self.assertEqual(code, 0, output)
            other = repo / "docs" / "specs" / "other.md"
            other.parent.mkdir(parents=True)
            other.write_text("other\n", encoding="utf-8")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 1, output)
            self.assertIn("docs/specs/other.md", output)

    def test_tree_guard_snapshot_records_the_owned_prefixes(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            code, output = run_main(
                guard,
                ["snapshot", "--repo", str(repo), "--owned", "docs/specs/demo.", "--out", str(snapshot)],
            )
            self.assertEqual(code, 0, output)
            data = json.loads(snapshot.read_text(encoding="utf-8"))
            self.assertEqual(data["owned"], ["docs/specs/demo."])

    def test_tree_guard_ignores_owned_edits_when_pathspecs_are_literal(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            spec = repo / "docs" / "specs" / "demo.md"
            spec.parent.mkdir(parents=True)
            spec.write_text("spec\n", encoding="utf-8")
            git(repo, "add", "docs/specs/demo.md")
            git(
                repo,
                "-c", "user.name=t",
                "-c", "user.email=t@example.com",
                "-c", "commit.gpgsign=false",
                "commit", "-q", "--no-verify", "-m", "docs: add demo spec",
            )
            snapshot = pathlib.Path(root) / "guard.json"
            with mock.patch.dict(os.environ, {"GIT_LITERAL_PATHSPECS": "1", "GIT_NOGLOB_PATHSPECS": "1"}):
                code, output = run_main(
                    guard,
                    ["snapshot", "--repo", str(repo), "--owned", "docs/specs/demo.", "--out", str(snapshot)],
                )
                self.assertEqual(code, 0, output)
                spec.write_text("revised spec\n", encoding="utf-8")
                code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 0, output)

    def test_tree_guard_exits_2_on_a_malformed_owned_field(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])
            data = json.loads(snapshot.read_text(encoding="utf-8"))
            snapshot.write_text(json.dumps(dict(data, owned="seed.txt")), encoding="utf-8")
            (repo / "seed.txt").write_text("edited\n", encoding="utf-8")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 2, output)

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

    def test_tree_guard_removes_caches_created_after_the_snapshot(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            write_file(repo / "app" / "__pycache__" / "core.cpython-312.pyc")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 0, output)
            self.assertFalse((repo / "app" / "__pycache__").exists(), output)

    def test_tree_guard_removes_new_ignored_and_tool_caches(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            write_file(repo / ".gitignore", "__pycache__/\n")
            git(repo, "add", ".gitignore")
            commit(repo, "chore: ignore caches")
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            write_file(repo / "pkg" / "__pycache__" / "x.cpython-312.pyc")
            write_file(repo / ".pytest_cache" / "v" / "cache" / "lastfailed")
            write_file(repo / ".eslintcache")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 0, output)
            self.assertFalse((repo / "pkg" / "__pycache__").exists(), output)
            self.assertFalse((repo / ".pytest_cache").exists(), output)
            self.assertFalse((repo / ".eslintcache").exists(), output)
            self.assertIn("removed cache", output)

    def test_tree_guard_snapshot_records_existing_caches(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            write_file(repo / "pkg" / "__pycache__" / "old.cpython-312.pyc")
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            data = json.loads(snapshot.read_text(encoding="utf-8"))
            self.assertEqual(data["caches"], ["pkg/__pycache__/old.cpython-312.pyc"])

    def test_tree_guard_keeps_caches_that_existed_at_the_snapshot(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            old = repo / "pkg" / "__pycache__" / "old.cpython-312.pyc"
            write_file(old)
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 0, output)
            self.assertTrue(old.is_file(), output)

    def test_tree_guard_keeps_an_old_cache_beside_a_new_one(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            old = repo / "pkg" / "__pycache__" / "old.cpython-312.pyc"
            new = repo / "pkg" / "__pycache__" / "new.cpython-312.pyc"
            write_file(old)
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            write_file(new)
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 0, output)
            self.assertTrue(old.is_file(), output)
            self.assertFalse(new.exists(), output)

    def test_tree_guard_keeps_old_caches_when_ignore_rules_change(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            old = repo / "pkg" / "__pycache__" / "old.cpython-312.pyc"
            write_file(old)
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            write_file(repo / ".gitignore", "__pycache__/\n")
            write_file(repo / "pkg" / "__pycache__" / "new.cpython-312.pyc")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 1, output)
            self.assertTrue(old.is_file(), output)

    def test_tree_guard_never_removes_a_symlink_into_the_repository(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            source = repo / "src" / "app.py"
            write_file(source, "print('app')\n")
            git(repo, "add", "src/app.py")
            commit(repo, "feat: add app")
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            link = repo / "__pycache__"
            link.symlink_to(repo / "src", target_is_directory=True)
            _, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertTrue(source.is_file(), output)
            self.assertTrue(link.is_symlink(), output)

    def test_tree_guard_keeps_a_tracked_file_that_looks_like_a_cache(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            compiled = repo / "legacy" / "compiled.pyc"
            write_file(compiled, "compiled\n")
            git(repo, "add", "-f", "legacy/compiled.pyc")
            commit(repo, "chore: add compiled file")
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            compiled.write_bytes(b"recompiled\n")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 1, output)
            self.assertTrue(compiled.is_file(), output)

    def test_tree_guard_still_reports_a_new_non_cache_file(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            notes = repo / "notes.txt"
            write_file(notes, "notes\n")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 1, output)
            self.assertTrue(notes.is_file(), output)

    def test_tree_guard_removes_nothing_for_a_snapshot_without_caches(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            data = json.loads(snapshot.read_text(encoding="utf-8"))
            snapshot.write_text(
                json.dumps({key: value for key, value in data.items() if key != "caches"}),
                encoding="utf-8",
            )
            cache = repo / "pkg" / "__pycache__" / "x.cpython-312.pyc"
            write_file(cache)
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 1, output)
            self.assertTrue(cache.is_file(), output)

    def test_tree_guard_never_follows_a_symlink_named_like_a_cache(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            keep = pathlib.Path(root) / "outside" / "keep.txt"
            write_file(keep, "keep\n")
            snapshot = pathlib.Path(root) / "guard.json"
            self.assertEqual(run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])[0], 0)
            link = repo / "__pycache__"
            link.symlink_to(keep.parent, target_is_directory=True)
            _, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertTrue(keep.is_file(), output)
            self.assertTrue(link.is_symlink(), output)

    def test_tree_guard_exits_2_on_a_malformed_caches_field(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])
            data = json.loads(snapshot.read_text(encoding="utf-8"))
            snapshot.write_text(json.dumps(dict(data, caches="pkg/__pycache__/")), encoding="utf-8")
            write_file(repo / "pkg" / "__pycache__" / "x.cpython-312.pyc")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 2, output)
            self.assertIn("caches is not a list of strings", output)
            self.assertTrue((repo / "pkg" / "__pycache__" / "x.cpython-312.pyc").is_file(), output)


if __name__ == "__main__":
    unittest.main()
