import contextlib
import importlib.util
import io
import json
import os
import pathlib
import shlex
import shutil
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


def seed_repository(root, *init_options):
    repo = pathlib.Path(root) / "repo"
    repo.mkdir()
    git(repo, "init", "-q", *init_options)
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


def guarded(guard, root, record):
    repo = seed_repository(root)
    snapshot = repo / "docs" / "specs" / "demo.guard.json"
    code, output = run_main(
        guard,
        ["snapshot", "--repo", str(repo), "--owned", "docs/specs/demo.", "--out", str(snapshot)],
    )
    assert code == 0, output
    record_path = repo / "docs" / "specs" / "demo.record.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    return repo, snapshot, record_path


def verify_with_record(guard, repo, snapshot, record_path, *flags):
    return run_main(
        guard,
        ["verify", "--repo", str(repo), "--snapshot", str(snapshot), "--record", str(record_path), *flags],
    )


def read_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def git_as(repo, *args):
    return git(repo, "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false", *args)


def head_of(repo):
    return git(repo, "rev-parse", "HEAD").strip()


def committed(repo, name, message):
    write_file(repo / name, "another session\n")
    git(repo, "add", name)
    commit(repo, message)
    return head_of(repo)


def snapshotted(guard, root, repo):
    snapshot = pathlib.Path(root) / "guard.json"
    code, output = run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])
    assert code == 0, output
    return snapshot


def verified(guard, repo, snapshot):
    return run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])


def with_remote(root, *init_options):
    repo = seed_repository(root, *init_options)
    remote = pathlib.Path(root) / "remote.git"
    git(root, "init", "-q", "--bare", str(remote))
    git(repo, "remote", "add", "origin", str(remote))
    git_as(repo, "push", "-q", "-u", "--no-verify", "origin", "HEAD:refs/heads/trunk")
    return repo, remote


def pushed_from_another_clone(root, remote, name, branch="trunk"):
    other = pathlib.Path(root) / f"clone-{name}"
    git(root, "clone", "-q", "--branch", branch, str(remote), str(other))
    committed(other, f"{name}.txt", f"feat: {name}")
    git_as(other, "push", "-q", "--no-verify", "origin", branch)


def local_commit(repo, branch, message):
    tree = git(repo, "write-tree").strip()
    made = git_as(repo, "commit-tree", "-p", "HEAD", "-m", message, tree).strip()
    git(repo, "update-ref", f"refs/heads/{branch}", made)
    return made


def branch_of(repo):
    return git(repo, "symbolic-ref", "--short", "HEAD").strip()


def diverged(repo):
    trunk = branch_of(repo)
    git(repo, "checkout", "-q", "-b", "side")
    committed(repo, "side.txt", "feat: side work")
    git(repo, "checkout", "-q", trunk)
    committed(repo, "trunk.txt", "feat: trunk work")


def fast_forwarded_from(root, repo, remote, name):
    pushed_from_another_clone(root, remote, name)
    git(repo, "fetch", "-q", "origin")
    git_as(repo, "merge", "-q", "--ff-only", "origin/trunk")


def errors_of(output):
    return [line for line in output.splitlines() if line.startswith("error: ")]


def head_errors(output):
    return [line for line in errors_of(output) if line.startswith("error: head") or "moved the head" in line]


def dirty_worktree(repo, root, name, branch=None):
    path = pathlib.Path(root) / name
    placement = ("-b", branch) if branch else ("--detach",)
    git(repo, "worktree", "add", "-q", *placement, str(path), "HEAD")
    write_file(path / "unsaved.txt", "work in progress\n")
    write_file(path / "seed.txt", "seed\nedited in the lane\n")
    return path


LOST = "error: uncommitted changes gone since the snapshot from a worktree whose head does not hold them: "
LANE = "<lane>"


UNREADABLE_LOG_GIT = (
    "#!/bin/sh\n"
    "for argument in \"$@\"; do\n"
    "  if [ \"$argument\" = \"--walk-reflogs\" ]; then\n"
    "    echo 'fatal: cannot read the HEAD log' >&2\n"
    "    exit 128\n"
    "  fi\n"
    "done\n"
    "exec %s \"$@\"\n"
)
IN_PROGRESS = {"seams": [], "criteria": [], "steps": [], "status": "in-progress"}
PROBE_STOP = {"phase": "probe", "reason": "surface probe failed: C1.1 command python3: not found"}


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
            head = head_of(repo)
            self.assertEqual(
                set(data),
                {
                    "head",
                    "reflog_top",
                    "status",
                    "diff_sha256",
                    "worktrees",
                    "stashes",
                    "dirty_worktrees",
                    "upstream",
                    "owned",
                    "caches",
                },
            )
            self.assertEqual(data["head"], head)
            self.assertIsNone(data["upstream"])
            self.assertTrue(data["reflog_top"].startswith(head + "\t"), data["reflog_top"])
            self.assertEqual(data["stashes"], [])
            self.assertEqual(data["dirty_worktrees"], [])
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

    def test_tree_guard_reports_a_commit_made_meanwhile(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = snapshotted(guard, root, repo)
            made = committed(repo, "other.txt", "feat: another session's work")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: commit moved the head to %s, a commit by t: feat: another session's work" % made, output)

    def test_tree_guard_reports_a_commit_pushed_meanwhile(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, _ = with_remote(root)
            snapshot = snapshotted(guard, root, repo)
            made = committed(repo, "other.txt", "feat: pushed work")
            git_as(repo, "push", "-q", "--no-verify", "origin", "HEAD:refs/heads/trunk")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: commit moved the head to %s, a commit by t: feat: pushed work" % made, output)

    def test_tree_guard_passes_a_fast_forward_merge_or_pull_from_a_remote(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, remote = with_remote(root)
            snapshot = snapshotted(guard, root, repo)
            fast_forwarded_from(root, repo, remote, "merged")
            pushed_from_another_clone(root, remote, "pulled")
            git_as(repo, "pull", "-q", "--ff-only", "origin", "trunk")
            code, output = verified(guard, repo, snapshot)
            self.assertTrue((repo / "pulled.txt").is_file())
        self.assertEqual(code, 0, output)
        self.assertNotIn("error:", output)

    def test_tree_guard_reports_an_edit_made_after_a_fast_forward(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, remote = with_remote(root)
            snapshot = snapshotted(guard, root, repo)
            fast_forwarded_from(root, repo, remote, "merged")
            (repo / "merged.txt").write_text("edited here\n", encoding="utf-8")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("merged.txt", output)
        self.assertEqual(head_errors(output), [], output)

    def test_tree_guard_reports_a_fast_forward_to_a_local_commit_the_upstream_lacks(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, _ = with_remote(root)
            snapshot = snapshotted(guard, root, repo)
            local = local_commit(repo, "side", "feat: local only")
            git_as(repo, "merge", "-q", "--ff-only", "side")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: merge side moved the head to %s, a commit by t: feat: local only" % local, output)

    def test_tree_guard_reports_a_fast_forward_to_an_upstream_set_after_the_snapshot(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, _ = with_remote(root)
            snapshot = snapshotted(guard, root, repo)
            local = local_commit(repo, "side", "feat: session work")
            git(repo, "branch", "-q", "--set-upstream-to", "side")
            git_as(repo, "merge", "-q", "--ff-only", "side")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: merge side moved the head to %s, a commit by t: feat: session work" % local, output)

    def test_tree_guard_reports_every_head_move_when_the_upstream_was_a_local_branch(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, _ = with_remote(root)
            trunk = branch_of(repo)
            git(repo, "checkout", "-q", "-b", "feature", "--track", trunk)
            snapshot = snapshotted(guard, root, repo)
            lane = pathlib.Path(root) / "trunk-lane"
            git(repo, "worktree", "add", "-q", str(lane), trunk)
            made = committed(lane, "lane.txt", "feat: session work on trunk")
            git(repo, "worktree", "remove", str(lane))
            git_as(repo, "merge", "-q", "--ff-only", "@{upstream}")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("moved the head to %s, a commit by t: feat: session work on trunk" % made, output)

    def test_tree_guard_reports_a_fast_forward_of_another_branch_after_a_switch(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, remote = with_remote(root)
            git_as(repo, "push", "-q", "--no-verify", "origin", "HEAD:refs/heads/release")
            git(repo, "fetch", "-q", "origin")
            git(repo, "branch", "-q", "--track", "release", "origin/release")
            pushed_from_another_clone(root, remote, "release-work", "release")
            git(repo, "fetch", "-q", "origin")
            snapshot = snapshotted(guard, root, repo)
            git(repo, "checkout", "-q", "release")
            git_as(repo, "pull", "-q", "--ff-only")
            code, output = verified(guard, repo, snapshot)
            made = head_of(repo)
        self.assertEqual(code, 1, output)
        self.assertIn("moved the head to %s, a commit by t: feat: release-work" % made, output)

    def test_tree_guard_reports_a_reset_to_a_commit_the_upstream_holds(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, remote = with_remote(root)
            snapshot = snapshotted(guard, root, repo)
            pushed_from_another_clone(root, remote, "upstream-work")
            git(repo, "fetch", "-q", "origin")
            git_as(repo, "reset", "-q", "--hard", "origin/trunk")
            code, output = verified(guard, repo, snapshot)
            made = head_of(repo)
        self.assertEqual(code, 1, output)
        self.assertIn("error: reset moved the head to %s, a commit by t: feat: upstream-work" % made, output)

    def test_tree_guard_reports_a_pushed_commit_whose_message_reads_like_a_fast_forward(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, _ = with_remote(root)
            snapshot = snapshotted(guard, root, repo)
            made = committed(repo, "other.txt", "merge origin/trunk: Fast-forward")
            git_as(repo, "push", "-q", "--no-verify", "origin", "HEAD:refs/heads/trunk")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: commit moved the head to %s, a commit by t: merge origin/trunk: Fast-forward" % made, output)

    def test_tree_guard_reports_a_head_log_git_cannot_read(self):
        guard = load_script("tree_guard")
        real_git = shutil.which("git")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = snapshotted(guard, root, repo)
            wrapper = pathlib.Path(root) / "bin" / "git"
            write_file(wrapper, UNREADABLE_LOG_GIT % shlex.quote(real_git))
            wrapper.chmod(0o755)
            with mock.patch.dict(os.environ, {"PATH": str(wrapper.parent) + os.pathsep + os.environ["PATH"]}):
                code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: cannot read the HEAD log", output)

    def test_tree_guard_reports_a_commit_of_only_owned_files(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            code, output = run_main(
                guard, ["snapshot", "--repo", str(repo), "--owned", "docs/specs/demo.", "--out", str(snapshot)]
            )
            self.assertEqual(code, 0, output)
            made = committed(repo, "docs/specs/demo.record.json", "docs: the run's own record")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: commit moved the head to %s, a commit by t: docs: the run's own record" % made, output)

    def test_tree_guard_reports_a_rebase(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            diverged(repo)
            snapshot = snapshotted(guard, root, repo)
            git_as(repo, "rebase", "-q", "side")
            code, output = verified(guard, repo, snapshot)
            made = head_of(repo)
        self.assertEqual(code, 1, output)
        self.assertIn("error: rebase (start) moved the head to", output)
        self.assertIn("error: rebase (pick) moved the head to %s, a commit by t: feat: trunk work" % made, output)

    def test_tree_guard_reports_a_checkout_that_moves_the_head(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            first = head_of(repo)
            committed(repo, "later.txt", "feat: later")
            snapshot = snapshotted(guard, root, repo)
            git(repo, "checkout", "-q", "HEAD~1")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: checkout moved the head to %s, a commit by t: chore: seed" % first, output)

    def test_tree_guard_reports_a_cherry_pick_a_revert_and_a_merge_commit(self):
        guard = load_script("tree_guard")
        operations = {
            "cherry-pick": (("cherry-pick", "side"), "cherry-pick"),
            "revert": (("revert", "--no-edit", "HEAD"), "revert"),
            "merge commit": (("merge", "-q", "--no-ff", "--no-edit", "side"), "merge side"),
        }
        for name, (arguments, operation) in operations.items():
            with self.subTest(operation=name), tempfile.TemporaryDirectory() as root, isolated_git_config(root):
                repo = seed_repository(root)
                diverged(repo)
                snapshot = snapshotted(guard, root, repo)
                git_as(repo, *arguments)
                code, output = verified(guard, repo, snapshot)
                made = head_of(repo)
                self.assertEqual(code, 1, output)
                self.assertIn("error: %s moved the head to %s, a commit by t: " % (operation, made), output)

    def test_tree_guard_passes_a_sync_in_a_reftable_repository(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, remote = with_remote(root, "--ref-format=reftable")
            snapshot = snapshotted(guard, root, repo)
            fast_forwarded_from(root, repo, remote, "merged")
            code, output = verified(guard, repo, snapshot)
            self.assertFalse((repo / ".git" / "logs" / "HEAD").exists())
        self.assertEqual(code, 0, output)
        self.assertNotIn("error:", output)

    def test_tree_guard_passes_a_reset_that_leaves_the_head_in_place(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = snapshotted(guard, root, repo)
            (repo / "seed.txt").write_text("staged then dropped\n", encoding="utf-8")
            git(repo, "add", "seed.txt")
            git(repo, "reset", "-q")
            git(repo, "checkout", "-q", "--", "seed.txt")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 0, output)
        self.assertNotIn("error:", output)

    def test_tree_guard_reports_a_reset_made_meanwhile(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            committed(repo, "later.txt", "feat: later")
            snapshot = snapshotted(guard, root, repo)
            git_as(repo, "reset", "-q", "--hard", "HEAD~1")
            code, output = verified(guard, repo, snapshot)
            now = head_of(repo)
        self.assertEqual(code, 1, output)
        self.assertIn("error: reset moved the head to %s, a commit by t: chore: seed" % now, output)

    def test_tree_guard_reports_an_amend_made_meanwhile(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = snapshotted(guard, root, repo)
            git_as(repo, "commit", "-q", "--no-verify", "--amend", "-m", "chore: reworded seed")
            code, output = verified(guard, repo, snapshot)
            now = head_of(repo)
        self.assertEqual(code, 1, output)
        self.assertIn("error: commit (amend) moved the head to %s, a commit by t: chore: reworded seed" % now, output)

    def test_tree_guard_reports_a_commit_undone_before_the_verify(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = snapshotted(guard, root, repo)
            made = committed(repo, "other.txt", "feat: pushed then undone")
            git_as(repo, "reset", "-q", "--hard", "HEAD~1")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: commit moved the head to %s" % made, output)
        self.assertIn("error: reset moved the head to", output)

    def test_tree_guard_reports_a_head_moved_with_no_reflog_entry(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            first = head_of(repo)
            later = committed(repo, "later.txt", "feat: later")
            snapshot = snapshotted(guard, root, repo)
            branch = git(repo, "symbolic-ref", "HEAD").strip()
            (repo / ".git" / branch).write_text(first + "\n", encoding="utf-8")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn(
            "error: head moved from %s to %s with no HEAD log entry to explain it" % (later, first), output
        )

    def test_tree_guard_passes_an_emptied_log_while_the_head_stays(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = snapshotted(guard, root, repo)
            git(repo, "reflog", "expire", "--expire=now", "--expire-unreachable=now", "--all")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 0, output)
        self.assertNotIn("error:", output)

    def test_tree_guard_names_the_log_setting_when_no_log_explains_a_move(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            git(repo, "config", "core.logAllRefUpdates", "false")
            shutil.rmtree(repo / ".git" / "logs")
            first = head_of(repo)
            snapshot = snapshotted(guard, root, repo)
            later = committed(repo, "other.txt", "feat: unlogged")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: head moved from %s to %s and this checkout keeps no HEAD log" % (first, later), output)
        self.assertIn("core.logAllRefUpdates", output)

    def test_a_snapshot_of_the_released_guard_is_still_read(self):
        guard = load_script("tree_guard")
        later_keys = ("reflog_top", "stashes", "dirty_worktrees", "upstream")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = snapshotted(guard, root, repo)
            current = {key: value for key, value in read_json(snapshot).items() if key not in later_keys}
            snapshot.write_text(json.dumps({**current, "branch": "refs/heads/master", "stash": ""}), encoding="utf-8")
            clean_code, clean_output = verified(guard, repo, snapshot)
            made = committed(repo, "other.txt", "feat: another session's work")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(clean_code, 0, clean_output)
        self.assertEqual(code, 1, output)
        self.assertIn("error: commit moved the head to %s" % made, output)

    def test_tree_guard_ignores_a_branch_change_made_meanwhile(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            snapshot = pathlib.Path(root) / "guard.json"
            run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])
            git(repo, "checkout", "-q", "-b", "another-branch")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 0, output)

    def test_tree_guard_reports_a_stash_dropped_meanwhile(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            (repo / "seed.txt").write_text("stashed\n", encoding="utf-8")
            git_as(repo, "stash", "-q")
            snapshot = snapshotted(guard, root, repo)
            git(repo, "stash", "drop", "-q")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: stash entry dropped since the snapshot: ", output)

    def test_tree_guard_reports_an_outside_edit_stashed_meanwhile(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            snapshot = snapshotted(guard, root, repo)
            (repo / "seed.txt").write_text("edited outside\n", encoding="utf-8")
            git_as(repo, "stash", "-q")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: stash entry added since the snapshot: ", output)
        self.assertEqual(head_errors(output), [], output)

    def test_tree_guard_reports_a_removed_worktree_that_held_uncommitted_work(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            lane = dirty_worktree(repo, root, "lane-dirty")
            snapshot = snapshotted(guard, root, repo)
            listed = read_json(snapshot)["dirty_worktrees"]
            git(repo, "worktree", "remove", "--force", str(lane))
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(len(listed), 1, listed)
        self.assertEqual(code, 1, output)
        self.assertIn(
            "error: worktree removed since the snapshot while it held uncommitted changes: %s" % listed[0]["path"],
            output,
        )

    def test_tree_guard_reports_a_dirty_worktree_removed_and_added_again_at_its_path(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            lane = dirty_worktree(repo, root, "lane-dirty")
            snapshot = snapshotted(guard, root, repo)
            git(repo, "worktree", "remove", "--force", str(lane))
            git(repo, "worktree", "add", "-q", "--detach", str(lane), "HEAD")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn(LOST, output)
        self.assertIn("unsaved.txt", output)

    def test_tree_guard_reports_a_dirty_worktree_whose_changes_were_discarded(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            lane = dirty_worktree(repo, root, "lane-dirty")
            snapshot = snapshotted(guard, root, repo)
            (lane / "unsaved.txt").unlink()
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn(LOST, output)
        self.assertIn("unsaved.txt", output)

    def test_tree_guard_reports_a_dirty_worktree_whose_head_moved_without_its_work(self):
        guard = load_script("tree_guard")
        moves = {
            "reset to an older commit": (("lane", "reset", "-q", "--hard", "HEAD~1"),),
            "reset to a newer commit": (("lane", "reset", "-q", "--hard", "newer"),),
            "added again at another commit": (
                ("repo", "worktree", "remove", "--force", LANE),
                ("repo", "worktree", "add", "-q", "--detach", LANE, "HEAD~1"),
            ),
        }
        for move, steps in moves.items():
            with self.subTest(move=move), tempfile.TemporaryDirectory() as root, isolated_git_config(root):
                repo = seed_repository(root)
                committed(repo, "later.txt", "feat: later")
                local_commit(repo, "newer", "feat: newer")
                lane = dirty_worktree(repo, root, "lane-dirty")
                snapshot = snapshotted(guard, root, repo)
                for where, *arguments in steps:
                    git(lane if where == "lane" else repo, *(str(lane) if part == LANE else part for part in arguments))
                code, output = verified(guard, repo, snapshot)
                self.assertEqual(code, 1, output)
                self.assertIn(LOST, output)
                self.assertIn("seed.txt", output)

    def test_tree_guard_reports_a_dirty_worktree_folder_made_again_empty(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            lane = dirty_worktree(repo, root, "lane-dirty")
            snapshot = snapshotted(guard, root, repo)
            shutil.rmtree(lane)
            lane.mkdir()
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: cannot read the head or status of a worktree that held uncommitted changes: ", output)

    def test_tree_guard_reports_a_dirty_worktree_whose_head_cannot_be_read(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            lane = dirty_worktree(repo, root, "lane-dirty")
            snapshot = snapshotted(guard, root, repo)
            git(lane, "checkout", "-q", "--orphan", "fresh")
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn("error: cannot read the head or status of a worktree that held uncommitted changes: ", output)

    def test_tree_guard_reports_one_of_two_files_deleted_from_an_untracked_folder(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo = seed_repository(root)
            lane = dirty_worktree(repo, root, "lane-dirty")
            write_file(lane / "notes" / "first.txt", "first\n")
            write_file(lane / "notes" / "second.txt", "second\n")
            snapshot = snapshotted(guard, root, repo)
            (lane / "notes" / "second.txt").unlink()
            code, output = verified(guard, repo, snapshot)
        self.assertEqual(code, 1, output)
        self.assertIn(LOST, output)
        self.assertIn("notes/second.txt", output)

    def test_tree_guard_passes_a_dirty_worktree_whose_work_was_committed_or_grew(self):
        guard = load_script("tree_guard")
        for change in ("committed", "committed in part", "committed then removed", "grew", "left alone on an unborn branch"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as root, isolated_git_config(root):
                repo = seed_repository(root)
                branch = "lane" if change == "committed then removed" else None
                lane = dirty_worktree(repo, root, "lane-dirty", branch)
                if change == "left alone on an unborn branch":
                    git(lane, "checkout", "-q", "--orphan", "fresh")
                snapshot = snapshotted(guard, root, repo)
                if change == "grew":
                    write_file(lane / "more.txt", "more work\n")
                if change.startswith("committed"):
                    git(lane, "add", *(("unsaved.txt",) if change == "committed in part" else ("-A",)))
                    commit(lane, "feat: the lane's work")
                if change == "committed then removed":
                    git(repo, "worktree", "remove", str(lane))
                code, output = verified(guard, repo, snapshot)
                self.assertEqual(code, 0, output)
                self.assertNotIn("error:", output)

    def test_tree_guard_ignores_worktrees_that_are_not_probes(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo = seed_repository(root)
            gone = pathlib.Path(root) / "lane-gone"
            git(repo, "worktree", "add", "--detach", str(gone), "HEAD")
            snapshot = pathlib.Path(root) / "guard.json"
            run_main(guard, ["snapshot", "--repo", str(repo), "--out", str(snapshot)])
            git(repo, "worktree", "remove", "--force", str(gone))
            git(repo, "worktree", "add", "--detach", str(pathlib.Path(root) / "lane-added"), "HEAD")
            code, output = run_main(guard, ["verify", "--repo", str(repo), "--snapshot", str(snapshot)])
            self.assertEqual(code, 0, output)

    def test_an_unattended_difference_stops_the_record_with_its_reason(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo, snapshot, record_path = guarded(guard, root, IN_PROGRESS)
            write_file(repo / "notes.txt", "stray\n")
            code, output = verify_with_record(guard, repo, snapshot, record_path, "--unattended")
            record = read_json(record_path)
        self.assertEqual(code, 1, output)
        self.assertIn("error: status changed", output)
        self.assertEqual(record.get("status"), "stopped", output)
        self.assertEqual(record.get("stop", {}).get("phase"), "hand-off", output)
        self.assertIn("notes.txt", record.get("stop", {}).get("reason", ""))

    def test_an_attended_difference_leaves_the_record(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo, snapshot, record_path = guarded(guard, root, IN_PROGRESS)
            write_file(repo / "notes.txt", "stray\n")
            code, output = verify_with_record(guard, repo, snapshot, record_path)
            record = read_json(record_path)
        self.assertEqual(code, 1, output)
        self.assertEqual(record, IN_PROGRESS)

    def test_a_clean_verify_clears_a_hand_off_stop(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root:
            repo, snapshot, record_path = guarded(guard, root, IN_PROGRESS)
            write_file(repo / "notes.txt", "stray\n")
            verify_with_record(guard, repo, snapshot, record_path, "--unattended")
            (repo / "notes.txt").unlink()
            code, output = verify_with_record(guard, repo, snapshot, record_path, "--unattended")
            record = read_json(record_path)
        self.assertEqual(code, 0, output)
        self.assertEqual(record, IN_PROGRESS)

    def test_the_guard_keeps_a_stop_of_another_phase_and_adds_its_difference(self):
        guard = load_script("tree_guard")
        stopped = {**IN_PROGRESS, "status": "stopped", "stop": PROBE_STOP}
        with tempfile.TemporaryDirectory() as root:
            repo, snapshot, record_path = guarded(guard, root, stopped)
            clean_code, clean_output = verify_with_record(guard, repo, snapshot, record_path, "--unattended")
            after_clean = read_json(record_path)
            write_file(repo / "notes.txt", "stray\n")
            code, output = verify_with_record(guard, repo, snapshot, record_path, "--unattended")
            after_difference = read_json(record_path)
            verify_with_record(guard, repo, snapshot, record_path, "--unattended")
            after_repeat = read_json(record_path)
        self.assertEqual(clean_code, 0, clean_output)
        self.assertEqual(after_clean, stopped)
        self.assertEqual(code, 1, output)
        self.assertEqual(after_difference["status"], "stopped")
        self.assertEqual(after_difference["stop"]["phase"], "probe")
        reason = after_difference["stop"]["reason"]
        self.assertTrue(reason.startswith(PROBE_STOP["reason"] + "; the checkout differs"), reason)
        self.assertIn("notes.txt", reason)
        self.assertEqual(after_repeat, after_difference)

    def test_a_record_the_gate_refuses_is_left_as_it_was(self):
        guard = load_script("tree_guard")
        refused = {**IN_PROGRESS, "notes": "not a record key"}
        with tempfile.TemporaryDirectory() as root:
            repo, snapshot, record_path = guarded(guard, root, refused)
            write_file(repo / "notes.txt", "stray\n")
            code, output = verify_with_record(guard, repo, snapshot, record_path, "--unattended")
            record = read_json(record_path)
        self.assertEqual(code, 2, output)
        self.assertIn("error: status changed", output)
        self.assertEqual(record, refused)

    def test_tree_guard_exits_2_on_an_unreadable_record(self):
        guard = load_script("tree_guard")
        with tempfile.TemporaryDirectory() as root, isolated_git_config(root):
            repo, snapshot, record_path = guarded(guard, root, IN_PROGRESS)
            record_path.write_text("not json", encoding="utf-8")
            cache = repo / "pkg" / "__pycache__" / "x.cpython-312.pyc"
            write_file(cache)
            code, output = verify_with_record(guard, repo, snapshot, record_path, "--unattended")
            self.assertEqual(code, 2, output)
            self.assertTrue(cache.is_file(), output)

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

    def test_tree_guard_exits_2_on_a_local_upstream_or_a_malformed_worktree_in_the_snapshot(self):
        guard = load_script("tree_guard")
        lane = {"path": "/a/lane", "head": None, "changes": ["unsaved.txt"], "blobs": {"unsaved.txt": None}}
        cases = {
            "a local upstream": ("upstream", "refs/heads/side", "upstream is not a ref under refs/remotes/"),
            "a worktree path alone": ("dirty_worktrees", ["/a/lane"], "dirty_worktrees is not a list of worktrees"),
            "a worktree branch outside refs/heads": (
                "dirty_worktrees", [dict(lane, branch="--output=/tmp/x")], "dirty_worktrees is not a list of worktrees"
            ),
        }
        for case, (key, value, message) in cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root, isolated_git_config(root):
                repo = seed_repository(root)
                snapshot = snapshotted(guard, root, repo)
                snapshot.write_text(json.dumps(dict(read_json(snapshot), **{key: value})), encoding="utf-8")
                code, output = verified(guard, repo, snapshot)
                self.assertEqual(code, 2, output)
                self.assertIn(message, output)


if __name__ == "__main__":
    unittest.main()
