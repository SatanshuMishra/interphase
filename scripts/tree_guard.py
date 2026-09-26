import argparse
import hashlib
import json
import os
import posixpath
import shutil
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
PATHSPEC_VARIABLES = (
    "GIT_LITERAL_PATHSPECS",
    "GIT_GLOB_PATHSPECS",
    "GIT_NOGLOB_PATHSPECS",
    "GIT_ICASE_PATHSPECS",
)
DIFF_CONFIG = (
    "-c", "diff.noprefix=false",
    "-c", "diff.mnemonicPrefix=false",
    "-c", "diff.relative=false",
    "-c", "core.quotePath=false",
)
CACHE_FOLDERS = frozenset((
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    ".gradle",
    ".dart_tool",
    ".parcel-cache",
    ".turbo",
))
CACHE_FILE_NAMES = frozenset((".eslintcache", ".coverage"))
CACHE_SUFFIXES = (".pyc", ".pyo", ".tsbuildinfo")
UNTRACKED_OR_IGNORED = ("?? ", "!! ")


class UsageError(Exception):
    pass


def git_environment():
    stripped = ISOLATING_VARIABLES + PATHSPEC_VARIABLES
    return {key: value for key, value in os.environ.items() if key not in stripped}


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


def is_owned(path, owned):
    return any(path.startswith(prefix) for prefix in owned)


def entry_is_owned(entry, owned):
    return all(is_owned(path, owned) for path in entry[3:].split("\0"))


def read_status(repo, owned):
    result = run_git(repo, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if result.returncode != 0:
        raise UsageError(f"git status failed: {decode(result.stderr).strip()}")
    return sorted(entry for entry in status_entries(result.stdout) if not entry_is_owned(entry, owned))


def is_cache_path(path):
    segments = path.rstrip("/").split("/")
    last = segments[-1]
    return (
        any(segment in CACHE_FOLDERS for segment in segments)
        or last in CACHE_FILE_NAMES
        or last.endswith(CACHE_SUFFIXES)
    )


def read_caches(repo):
    result = run_git(
        repo,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching"],
    )
    if result.returncode != 0:
        raise UsageError(f"git status failed: {decode(result.stderr).strip()}")
    paths = (entry[3:] for entry in status_entries(result.stdout) if entry[:3] in UNTRACKED_OR_IGNORED)
    return sorted(frozenset(path for path in paths if is_cache_path(path)))


def empty_tree(repo):
    result = run_git(repo, ["hash-object", "-t", "tree", "--stdin"], input_bytes=b"")
    return decode(result.stdout).strip()


def owned_pathspec(owned):
    if not owned:
        return ()
    return ("--", ".", *(f":(exclude){prefix}*" for prefix in owned))


def read_diff_digest(repo, head, owned):
    base = head if head is not None else empty_tree(repo)
    result = run_git(
        repo,
        ["diff", "--no-ext-diff", "--no-textconv", "--no-color", "--binary", base, *owned_pathspec(owned)],
    )
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


def capture(repo, owned):
    head = read_head(repo)
    return {
        "head": head,
        "branch": read_branch(repo),
        "status": read_status(repo, owned),
        "diff_sha256": read_diff_digest(repo, head, owned),
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
    if not is_string_list(data.get("owned", [])):
        raise UsageError(f"unreadable snapshot: {path}: owned is not a list of strings")
    if not is_string_list(data.get("caches", [])):
        raise UsageError(f"unreadable snapshot: {path}: caches is not a list of strings")
    return data


def is_string_list(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def is_new_cache(path, known):
    bare = path.rstrip("/")
    return not any(
        bare == old or bare.startswith(old + "/") or old.startswith(bare + "/")
        for old in known
    )


def lies_inside(root, target):
    real_root = os.path.realpath(root)
    real_target = os.path.realpath(target)
    return real_target != real_root and os.path.commonpath([real_root, real_target]) == real_root


def is_removable(repo, path):
    bare = path.rstrip("/")
    if not bare or os.path.isabs(bare) or ".." in bare.split("/"):
        return False
    target = os.path.join(repo, bare)
    return not os.path.islink(target) and lies_inside(repo, target) and os.path.exists(target)


def cannot_remove(path, error):
    return f"cannot remove cache {path}: {error.strerror or error}"


def remove_cache(repo, path):
    target = os.path.join(repo, path.rstrip("/"))
    try:
        if path.endswith("/"):
            shutil.rmtree(target)
        else:
            os.remove(target)
    except OSError as error:
        return (), (cannot_remove(path, error),)
    return (path,), ()


def is_empty_folder(target):
    try:
        return os.path.isdir(target) and not os.path.islink(target) and not os.listdir(target)
    except OSError:
        return False


def prune_parents(repo, path):
    removed = ()
    folder = posixpath.dirname(path.rstrip("/"))
    while folder and is_cache_path(folder) and is_empty_folder(os.path.join(repo, folder)):
        try:
            os.rmdir(os.path.join(repo, folder))
        except OSError as error:
            return removed, (cannot_remove(folder + "/", error),)
        removed = removed + (folder + "/",)
        folder = posixpath.dirname(folder)
    return removed, ()


def remove_new_caches(repo, snapshot):
    if "caches" not in snapshot:
        return (), ()
    known = tuple(path.rstrip("/") for path in snapshot["caches"])
    candidates = tuple(path for path in read_caches(repo) if is_new_cache(path, known))
    removals = tuple((path, remove_cache(repo, path)) for path in candidates if is_removable(repo, path))
    removed = tuple(path for path, (_, failures) in removals if not failures)
    outcomes = tuple(outcome for _, outcome in removals) + tuple(prune_parents(repo, path) for path in removed)
    return (
        tuple(path for paths, _ in outcomes for path in paths),
        tuple(failure for _, failures in outcomes for failure in failures),
    )


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
    owned = tuple(args.owned)
    state = dict(capture(repo, owned), owned=list(owned), caches=read_caches(repo))
    try:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except OSError as error:
        raise UsageError(f"cannot write snapshot: {args.out}: {error}")
    return 0


def command_verify(args):
    repo = repository_root(args.repo)
    snapshot = load_snapshot(args.snapshot)
    removed, failures = remove_new_caches(repo, snapshot)
    for path in removed:
        print(f"removed cache: {path}")
    findings = list(failures) + compare(snapshot, capture(repo, tuple(snapshot.get("owned", []))))
    for finding in findings:
        print(f"error: {finding}")
    return 1 if findings else 0


def build_parser():
    parser = argparse.ArgumentParser(prog="tree_guard.py")
    commands = parser.add_subparsers(dest="command")
    commands.required = True
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--repo", required=True)
    snapshot.add_argument("--owned", action="append", default=[])
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
