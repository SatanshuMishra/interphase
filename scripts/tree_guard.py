import argparse
import hashlib
import json
import os
import subprocess
import sys

PROBE_MARKER = "interphase-probe-"
FIELDS = ("head", "branch", "status", "diff_sha256", "stash", "worktrees")
ISOLATING_VARIABLES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
)
DIFF_CONFIG = (
    "-c", "diff.noprefix=false",
    "-c", "diff.mnemonicPrefix=false",
    "-c", "diff.relative=false",
    "-c", "core.quotePath=false",
)


class UsageError(Exception):
    pass


def git_environment():
    return {key: value for key, value in os.environ.items() if key not in ISOLATING_VARIABLES}


def run_git(repo, args, input_bytes=None):
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", repo, *DIFF_CONFIG, *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=git_environment(),
    )


def decode(raw):
    return raw.decode("utf-8", "surrogateescape")


def repository_root(path):
    if not os.path.isdir(path):
        raise UsageError(f"not a git repository: {path}")
    result = run_git(path, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        raise UsageError(f"not a git repository: {path}")
    return decode(result.stdout).rstrip("\n")


def read_head(repo):
    result = run_git(repo, ["rev-parse", "--verify", "-q", "HEAD"])
    return decode(result.stdout).strip() if result.returncode == 0 else None


def read_branch(repo):
    result = run_git(repo, ["symbolic-ref", "-q", "HEAD"])
    return decode(result.stdout).strip() if result.returncode == 0 else None


def status_entries(raw):
    tokens = [token for token in decode(raw).split("\0") if token]
    return tuple(join_renames(tokens, 0, ()))


def join_renames(tokens, index, collected):
    while index < len(tokens):
        token = tokens[index]
        if token[:1] in ("R", "C") and index + 1 < len(tokens):
            collected = collected + (token + "\0" + tokens[index + 1],)
            index += 2
        else:
            collected = collected + (token,)
            index += 1
    return collected


def read_status(repo):
    result = run_git(repo, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if result.returncode != 0:
        raise UsageError(f"git status failed: {decode(result.stderr).strip()}")
    return sorted(status_entries(result.stdout))


def empty_tree(repo):
    result = run_git(repo, ["hash-object", "-t", "tree", "--stdin"], input_bytes=b"")
    return decode(result.stdout).strip()


def read_diff_digest(repo, head):
    base = head if head is not None else empty_tree(repo)
    result = run_git(repo, ["diff", "--no-ext-diff", "--no-textconv", "--no-color", "--binary", base])
    if result.returncode != 0:
        raise UsageError(f"git diff failed: {decode(result.stderr).strip()}")
    return hashlib.sha256(result.stdout).hexdigest()


def read_stash(repo):
    result = run_git(repo, ["stash", "list"])
    return decode(result.stdout) if result.returncode == 0 else ""


def read_worktrees(repo):
    result = run_git(repo, ["worktree", "list", "--porcelain"])
    lines = decode(result.stdout).splitlines() if result.returncode == 0 else []
    return sorted(line[len("worktree "):] for line in lines if line.startswith("worktree "))


def capture(repo):
    head = read_head(repo)
    return {
        "head": head,
        "branch": read_branch(repo),
        "status": read_status(repo),
        "diff_sha256": read_diff_digest(repo, head),
        "stash": read_stash(repo),
        "worktrees": read_worktrees(repo),
    }


def load_snapshot(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise UsageError(f"unreadable snapshot: {path}: {error}")
    if not isinstance(data, dict) or any(field not in data for field in FIELDS):
        raise UsageError(f"unreadable snapshot: {path}: missing fields")
    return data


def worktree_findings(before, after):
    added = [path for path in after if path not in before]
    removed = [path for path in before if path not in after]
    probes = [path for path in added if PROBE_MARKER in path]
    others = [path for path in added if PROBE_MARKER not in path]
    probe_lines = [f"leftover probe worktree: {path}" for path in probes]
    change_lines = (
        [f"worktrees changed: added {others}, removed {removed}"] if others or removed else []
    )
    return probe_lines + change_lines


def field_findings(field, before, after):
    if before == after:
        return []
    if field == "worktrees":
        return worktree_findings(before, after)
    if field == "status":
        return [f"status changed: was {len(before)} entries, now {len(after)}: {sorted(set(after) ^ set(before))}"]
    return [f"{field} changed: was {before!r}, now {after!r}"]


def compare(snapshot, current):
    return [line for field in FIELDS for line in field_findings(field, snapshot[field], current[field])]


def command_snapshot(args):
    repo = repository_root(args.repo)
    state = capture(repo)
    try:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except OSError as error:
        raise UsageError(f"cannot write snapshot: {args.out}: {error}")
    return 0


def command_verify(args):
    repo = repository_root(args.repo)
    snapshot = load_snapshot(args.snapshot)
    findings = compare(snapshot, capture(repo))
    for finding in findings:
        print(f"error: {finding}")
    return 1 if findings else 0


def build_parser():
    parser = argparse.ArgumentParser(prog="tree_guard.py")
    commands = parser.add_subparsers(dest="command")
    commands.required = True
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--repo", required=True)
    snapshot.add_argument("--out", required=True)
    snapshot.set_defaults(handler=command_snapshot)
    verify = commands.add_parser("verify")
    verify.add_argument("--repo", required=True)
    verify.add_argument("--snapshot", required=True)
    verify.set_defaults(handler=command_verify)
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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
