import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import posixpath
import re
import shutil
import subprocess
import sys

PROBE_MARKER = "interphase-probe-"
COMPARED = ("status", "diff_sha256", "worktrees")
SNAPSHOT_FIELDS = ("head",) + COMPARED
REFLOG_TOP = "reflog_top"
STASHES = "stashes"
DIRTY_WORKTREES = "dirty_worktrees"
UPSTREAM = "upstream"
REMOTE_REFS = "refs/remotes/"
REFLOG_FORMAT = "--format=%H%x09%gd%x09%gs"
STASH_FORMAT = "--format=%H%x09%gs"
FAST_FORWARD_RE = re.compile(r"(merge [^:]+|pull( [^:]*)?): Fast-forward")
UNREADABLE_LOG = "cannot read the HEAD log"
NO_LOG = "and this checkout keeps no HEAD log to explain it: core.logAllRefUpdates is off or the log was removed"
STOPPED = "stopped"
IN_PROGRESS = "in-progress"
STOP_PHASE = "hand-off"
DIFFERENCE = "the checkout differs from the guard snapshot: "
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


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


atomic_file = load_sibling("atomic_file")


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


def read_worktrees(repo):
    result = run_git(repo, ["worktree", "list", "--porcelain"])
    lines = decode(result.stdout).splitlines() if result.returncode == 0 else []
    return sorted(line[len("worktree "):] for line in lines if line.startswith("worktree "))


def read_reflog(repo, head):
    if head is None:
        return ()
    result = run_git(
        repo,
        ["log", "--walk-reflogs", "--no-show-signature", "--date=unix", REFLOG_FORMAT, "HEAD", "--"],
    )
    lines = tuple(line for line in decode(result.stdout).split("\n") if line)
    return lines if result.returncode == 0 and all(line.count("\t") >= 2 for line in lines) else None


def read_stashes(repo):
    result = run_git(repo, ["stash", "list", "--no-show-signature", STASH_FORMAT])
    if result.returncode != 0:
        raise UsageError(f"git stash list failed: {decode(result.stderr).strip()}")
    return [line for line in decode(result.stdout).split("\n") if line]


def worktree_changes(path):
    result = run_git(path, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    return sorted(entry[3:] for entry in status_entries(result.stdout)) if result.returncode == 0 else None


def read_dirty_worktrees(repo, worktrees):
    own = os.path.realpath(repo)
    others = tuple(
        path
        for path in worktrees
        if PROBE_MARKER not in path and os.path.realpath(path) != own and os.path.isdir(path)
    )
    states = ((path, worktree_changes(path)) for path in others)
    return [{"path": path, "head": read_head(path), "changes": changes} for path, changes in states if changes]


def capture(repo, owned):
    head = read_head(repo)
    return {
        "head": head,
        "status": read_status(repo, owned),
        "diff_sha256": read_diff_digest(repo, head, owned),
        "worktrees": read_worktrees(repo),
        STASHES: read_stashes(repo),
    }


def load_snapshot(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise UsageError(f"unreadable snapshot: {path}: {error}")
    if not isinstance(data, dict) or any(field not in data for field in SNAPSHOT_FIELDS):
        raise UsageError(f"unreadable snapshot: {path}: missing fields")
    malformed = [key for key in ("owned", "caches", STASHES) if not is_string_list(data.get(key, []))]
    if malformed:
        raise UsageError(f"unreadable snapshot: {path}: {malformed[0]} is not a list of strings")
    dirty = data.get(DIRTY_WORKTREES, [])
    if not isinstance(dirty, list) or not all(is_dirty_worktree(item) for item in dirty):
        raise UsageError(f"unreadable snapshot: {path}: {DIRTY_WORKTREES} is not a list of worktrees")
    upstream = data.get(UPSTREAM)
    if upstream is not None and not (isinstance(upstream, str) and upstream.startswith(REMOTE_REFS)):
        raise UsageError(f"unreadable snapshot: {path}: {UPSTREAM} is not a ref under {REMOTE_REFS}")
    return data


def is_string_list(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def is_dirty_worktree(value):
    return (
        isinstance(value, dict)
        and isinstance(value.get("path"), str)
        and (value.get("head") is None or isinstance(value.get("head"), str))
        and is_string_list(value.get("changes"))
    )


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
    return [f"leftover probe worktree: {path}" for path in after if path not in before and PROBE_MARKER in path]


def field_findings(field, before, after):
    if before == after:
        return []
    if field == "worktrees":
        return worktree_findings(before, after)
    if field == "status":
        return [f"status changed: was {len(before)} entries, now {len(after)}: {sorted(set(after) ^ set(before))}"]
    return [f"{field} changed: was {before!r}, now {after!r}"]


def compare(snapshot, current):
    return [line for field in COMPARED for line in field_findings(field, snapshot[field], current[field])]


def stash_text(line):
    return " ".join(line.split("\t", 1))


def stash_findings(snapshot, current):
    if STASHES not in snapshot:
        return []
    before, after = snapshot[STASHES], current[STASHES]
    return [f"stash entry dropped since the snapshot: {stash_text(line)}" for line in before if line not in after] + [
        f"stash entry added since the snapshot: {stash_text(line)}" for line in after if line not in before
    ]


def lost_work(entry, worktrees):
    path = entry["path"]
    if path not in worktrees or not os.path.isdir(path):
        return [f"worktree removed since the snapshot while it held uncommitted changes: {path}"]
    if read_head(path) != entry["head"]:
        return []
    changes = worktree_changes(path)
    if changes is None:
        return [f"cannot read the status of a worktree that held uncommitted changes: {path}"]
    gone = [" from ".join(change.split("\0")) for change in entry["changes"] if change not in changes]
    if not gone:
        return []
    return [f"uncommitted changes gone since the snapshot from a worktree whose head did not move: {path}: {', '.join(gone)}"]


def lost_work_findings(snapshot, worktrees):
    return [finding for entry in snapshot.get(DIRTY_WORKTREES, []) for finding in lost_work(entry, worktrees)]


def snapshot_position(lines, snapshot):
    top = snapshot.get(REFLOG_TOP)
    if top is not None and top in lines:
        return lines.index(top)
    if snapshot["head"] is None or (REFLOG_TOP in snapshot and top is None):
        return len(lines)
    shas = tuple(line.split("\t", 1)[0] for line in lines)
    return shas.index(snapshot["head"]) if snapshot["head"] in shas else 0


def entry_parts(line):
    sha, _, subject = line.split("\t", 2)
    return sha, subject


def head_moves(entries, start):
    befores = (start,) + tuple(sha for sha, _ in entries[:-1])
    return tuple((sha, subject) for before, (sha, subject) in zip(befores, entries) if sha != before)


def read_upstream(repo):
    result = run_git(repo, ["rev-parse", "--symbolic-full-name", "--verify", "-q", "@{upstream}"])
    name = decode(result.stdout).strip() if result.returncode == 0 else ""
    return name if name.startswith(REMOTE_REFS) else None


def is_sync(repo, sha, subject, upstream):
    return (
        FAST_FORWARD_RE.fullmatch(subject) is not None
        and upstream is not None
        and run_git(repo, ["merge-base", "--is-ancestor", sha, upstream]).returncode == 0
    )


def commit_of(repo, sha):
    result = run_git(repo, ["log", "-1", "--no-show-signature", "--format=%an%x09%s", sha, "--"])
    author, _, title = decode(result.stdout).strip().partition("\t")
    return (author, title) if result.returncode == 0 and author else ("an unknown author", "an unreadable commit")


def move_finding(repo, sha, subject):
    author, title = commit_of(repo, sha)
    return f"{subject.partition(': ')[0]} moved the head to {sha}, a commit by {author}: {title}"


def head_findings(repo, snapshot, head):
    start = snapshot["head"]
    lines = read_reflog(repo, head)
    if lines is None:
        return [UNREADABLE_LOG]
    if not lines:
        return [] if head == start else [f"head moved from {start} to {head} {NO_LOG}"]
    entries = tuple(entry_parts(line) for line in reversed(lines[: snapshot_position(lines, snapshot)]))
    upstream = snapshot.get(UPSTREAM)
    moves = [
        move_finding(repo, sha, subject)
        for sha, subject in head_moves(entries, start)
        if not is_sync(repo, sha, subject, upstream)
    ]
    reached = entries[-1][0] if entries else start
    if reached == head:
        return moves
    return moves + [f"head moved from {start} to {head} with no HEAD log entry to explain it"]


def command_snapshot(args):
    repo = repository_root(args.repo)
    owned = tuple(args.owned)
    current = capture(repo, owned)
    lines = read_reflog(repo, current["head"]) or ()
    marks = {
        REFLOG_TOP: lines[0] if lines else None,
        DIRTY_WORKTREES: read_dirty_worktrees(repo, current["worktrees"]),
        UPSTREAM: read_upstream(repo),
    }
    state = dict(current, owned=list(owned), caches=read_caches(repo), **marks)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        atomic_file.replace(args.out, (json.dumps(state, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except OSError as error:
        raise UsageError(f"cannot write snapshot: {args.out}: {error}")
    return 0


def load_record(path):
    try:
        record = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, RecursionError) as error:
        raise UsageError(f"unreadable record: {path}: {error}")
    if not isinstance(record, dict):
        raise UsageError(f"unreadable record: {path}: not a JSON object")
    return record


def stopped_here(record):
    stop = record.get("stop")
    return record.get("status") == STOPPED and isinstance(stop, dict) and stop.get("phase") == STOP_PHASE


def with_difference(record, difference):
    stop = record.get("stop")
    if not isinstance(stop, dict) or difference in str(stop.get("reason", "")):
        return record
    return {**record, "stop": {**stop, "reason": f"{stop.get('reason')}; {difference}"}}


def judged(record, findings, unattended):
    if not findings:
        if not stopped_here(record):
            return record
        return {**{key: value for key, value in record.items() if key != "stop"}, "status": IN_PROGRESS}
    if not unattended:
        return record
    difference = DIFFERENCE + "; ".join(findings)
    if record.get("status") == STOPPED and not stopped_here(record):
        return with_difference(record, difference)
    return {**record, "status": STOPPED, "stop": {"phase": STOP_PHASE, "reason": difference}}


def store_record(path, before, after):
    if after == before:
        return ()
    try:
        return load_sibling("handoff_gate").write_record(path, after)
    except OSError as error:
        return (f"cannot write: {path}: {error}",)


def command_verify(args):
    repo = repository_root(args.repo)
    snapshot = load_snapshot(args.snapshot)
    record = load_record(args.record) if args.record else None
    removed, failures = remove_new_caches(repo, snapshot)
    for path in removed:
        print(f"removed cache: {path}")
    current = capture(repo, tuple(snapshot.get("owned", [])))
    findings = (
        list(failures)
        + head_findings(repo, snapshot, current["head"])
        + compare(snapshot, current)
        + stash_findings(snapshot, current)
        + lost_work_findings(snapshot, current["worktrees"])
    )
    for finding in findings:
        print(f"error: {finding}")
    refusals = () if record is None else store_record(args.record, record, judged(record, findings, args.unattended))
    if refusals:
        raise UsageError("; ".join(refusals))
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
    verify.add_argument("--record")
    verify.add_argument("--unattended", action="store_true")
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
