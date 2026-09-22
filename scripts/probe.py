import argparse
import os
import shutil
import subprocess
import sys
import tempfile

PROBE_PREFIX = "interphase-probe-"
ISOLATING_VARIABLES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
)
SAFE_CONFIG = (
    "-c", f"core.hooksPath={os.devnull}",
    "-c", "diff.noprefix=false",
    "-c", "diff.mnemonicPrefix=false",
    "-c", "diff.relative=false",
)


class UsageError(Exception):
    pass


class ProbeError(Exception):
    pass


def git_environment():
    return {key: value for key, value in os.environ.items() if key not in ISOLATING_VARIABLES}


def run_git(repo, args, input_bytes=None):
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", repo, *SAFE_CONFIG, *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=git_environment(),
    )


def decode(raw):
    return raw.decode("utf-8", "surrogateescape")


def failure(result):
    return decode(result.stderr).strip() or decode(result.stdout).strip()


def repository_root(path):
    if not os.path.isdir(path):
        raise UsageError(f"not a git repository: {path}")
    result = run_git(path, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        raise UsageError(f"not a git repository: {path}")
    return decode(result.stdout).rstrip("\n")


def worktree_paths(repo):
    result = run_git(repo, ["worktree", "list", "--porcelain"])
    if result.returncode != 0:
        raise ProbeError(f"git worktree list failed: {failure(result)}")
    lines = decode(result.stdout).splitlines()
    return tuple(line[len("worktree "):] for line in lines if line.startswith("worktree "))


def is_probe_name(path):
    return os.path.basename(os.path.normpath(path)).startswith(PROBE_PREFIX)


def same_path(first, second):
    return os.path.realpath(first) == os.path.realpath(second)


def probe_paths(repo):
    paths = worktree_paths(repo)
    return tuple(path for path in paths[1:] if is_probe_name(path))


def diff_against_head(repo):
    result = run_git(repo, ["diff", "--no-ext-diff", "--no-textconv", "--no-color", "--binary", "HEAD"])
    if result.returncode != 0:
        raise ProbeError(f"git diff failed: {failure(result)}")
    return result.stdout


def untracked_files(repo):
    result = run_git(repo, ["ls-files", "--others", "--exclude-standard", "-z"])
    if result.returncode != 0:
        raise ProbeError(f"git ls-files failed: {failure(result)}")
    return tuple(name for name in decode(result.stdout).split("\0") if name)


def apply_diff(worktree, diff):
    if not diff:
        return
    result = run_git(worktree, ["apply", "--binary", "--whitespace=nowarn", "-"], input_bytes=diff)
    if result.returncode != 0:
        raise ProbeError(f"git apply failed: {failure(result)}")


def copy_untracked(repo, worktree, names):
    for name in names:
        source = os.path.join(repo, name)
        target = os.path.join(worktree, name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=False)


def carry_uncommitted(repo, worktree):
    apply_diff(worktree, diff_against_head(repo))
    copy_untracked(repo, worktree, untracked_files(repo))


def discard_probe(repo, worktree):
    run_git(repo, ["worktree", "remove", "--force", worktree])
    run_git(repo, ["worktree", "prune"])
    shutil.rmtree(worktree, ignore_errors=True)


def command_create(args):
    repo = repository_root(args.repo)
    if run_git(repo, ["rev-parse", "--verify", "-q", "HEAD"]).returncode != 0:
        raise ProbeError("HEAD has no commit to check out")
    worktree = tempfile.mkdtemp(prefix=PROBE_PREFIX)
    result = run_git(repo, ["worktree", "add", "--detach", worktree, "HEAD"])
    if result.returncode != 0:
        shutil.rmtree(worktree, ignore_errors=True)
        raise ProbeError(f"git worktree add failed: {failure(result)}")
    try:
        if args.with_uncommitted:
            carry_uncommitted(repo, worktree)
    except (ProbeError, OSError) as error:
        discard_probe(repo, worktree)
        raise ProbeError(str(error))
    print(worktree)
    return 0


def refusal(repo, path):
    if not is_probe_name(path):
        return f"refusing to remove {path}: its name does not start with {PROBE_PREFIX}"
    main_tree = worktree_paths(repo)[0]
    if same_path(path, main_tree) or same_path(path, repo):
        return f"refusing to remove {path}: it is the main worktree"
    return None


def command_remove(args):
    repo = repository_root(args.repo)
    path = os.path.abspath(args.path)
    reason = refusal(repo, path)
    if reason is not None:
        print(f"error: {reason}")
        return 1
    result = run_git(repo, ["worktree", "remove", "--force", path])
    if result.returncode != 0:
        print(f"error: git worktree remove failed: {failure(result)}")
        return 1
    run_git(repo, ["worktree", "prune"])
    return 0


def command_list(args):
    repo = repository_root(args.repo)
    for path in probe_paths(repo):
        print(path)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="probe.py")
    commands = parser.add_subparsers(dest="command")
    commands.required = True
    create = commands.add_parser("create")
    create.add_argument("--repo", required=True)
    create.add_argument("--with-uncommitted", action="store_true")
    create.set_defaults(handler=command_create)
    remove = commands.add_parser("remove")
    remove.add_argument("--repo", required=True)
    remove.add_argument("--path", required=True)
    remove.set_defaults(handler=command_remove)
    listing = commands.add_parser("list")
    listing.add_argument("--repo", required=True)
    listing.set_defaults(handler=command_list)
    return parser


def parse(argv):
    try:
        return build_parser().parse_args(argv), None
    except SystemExit as exit_signal:
        return None, 2 if exit_signal.code else 0


def main(argv):
    args, code = parse(argv)
    if args is None:
        return code
    try:
        return args.handler(args)
    except UsageError as error:
        print(f"error: {error}")
        return 2
    except ProbeError as error:
        print(f"error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
