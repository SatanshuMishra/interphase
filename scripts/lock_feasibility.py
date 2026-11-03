import fnmatch
import importlib.util
import json
import os
import pathlib
import posixpath
import re
import subprocess
import sys

USAGE = "usage: python3 lock_feasibility.py --record RECORD --repo ROOT"
OPTIONS = ("--record", "--repo")
PASSED = "pass"
FAILED = "fail"
ISOLATING_VARIABLES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
)
QUIET_VARIABLES = {"GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat", "PAGER": "cat", "CI": "1"}
TEST_FOLDERS = frozenset(("test", "tests", "__tests__", "spec"))
TEST_NAMES = ("test_*", "*_test.*", "*.test.*", "*.spec.*")
GENERIC_STEMS = frozenset(
    ("index", "page", "layout", "route", "template", "loading", "error", "main", "mod", "lib", "utils", "__init__")
)
QUOTED_RE = re.compile(r"'([^'\n]*)'|\"([^\"\n]*)\"")


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


atomic_file = load_sibling("atomic_file")
check_items = load_sibling("check_items")
check_record = load_sibling("check_record")


class CannotStart(Exception):
    pass


def environment():
    kept = {key: value for key, value in os.environ.items() if key not in ISOLATING_VARIABLES}
    return {**kept, **QUIET_VARIABLES}


def run(arguments, cwd, shell=False):
    try:
        return subprocess.run(
            arguments,
            cwd=cwd,
            shell=shell,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment(),
        )
    except OSError as exc:
        raise CannotStart(str(exc))


def decode(raw):
    return raw.decode("utf-8", "replace")


def git(root, *arguments):
    return run(["git", "--no-optional-locks", "-C", root] + list(arguments), root)


def failure_text(result):
    return decode(result.stderr).strip() or decode(result.stdout).strip() or "exit %d" % result.returncode


def work_tree_root(path):
    if not pathlib.Path(path).is_dir():
        return None
    try:
        inside = git(path, "rev-parse", "--is-inside-work-tree")
        if inside.returncode != 0 or decode(inside.stdout).strip() != "true":
            return None
        top = git(path, "rev-parse", "--show-toplevel")
    except CannotStart:
        return None
    return decode(top.stdout).rstrip("\n") if top.returncode == 0 else None


def has_head(root):
    return git(root, "rev-parse", "--verify", "-q", "HEAD").returncode == 0


def head_files(root):
    if not has_head(root):
        return ()
    listed = git(root, "ls-tree", "-r", "-z", "--full-tree", "--name-only", "HEAD")
    if listed.returncode != 0:
        raise CannotStart("git ls-tree failed: " + failure_text(listed))
    return tuple(sorted(name for name in decode(listed.stdout).split("\0") if name))


def head_text(root, path):
    shown = git(root, "show", "HEAD:" + path)
    if shown.returncode != 0:
        raise CannotStart("git show HEAD:%s failed: %s" % (path, failure_text(shown)))
    return decode(shown.stdout)


def result(check, subject, passed, detail):
    return {"check": check, "subject": subject, "status": PASSED if passed else FAILED, "detail": detail}


def record_steps(record):
    steps = record.get("steps")
    return tuple(step for step in steps if isinstance(step, dict)) if isinstance(steps, list) else ()


def record_locked(record):
    return check_record.record_locked(record) or frozenset()


def path_list(row, key):
    value = row.get(key)
    return tuple(path for path in value if check_items.is_text(path)) if isinstance(value, list) else ()


def locked_rows(record):
    criteria = record.get("criteria")
    return tuple(
        row
        for criterion in (criteria if isinstance(criteria, list) else ())
        if check_record.has_lines(criterion)
        for row in check_record.criterion_tests(criterion)
    )


def written_files(step_name, steps):
    by_name = check_record.steps_by_name(steps)
    if step_name not in by_name:
        return frozenset()
    graph = check_items.after_graph(steps)
    owners = frozenset((step_name,)) | check_items.reachable(graph, step_name)
    return frozenset(path for owner in owners if owner in by_name for path in check_items.step_files(by_name[owner]))


def is_at(path, paths):
    return bool(check_items.shared_paths((path,), paths))


def row_subject(row):
    return "%s::%s" % (row["file"], row["name"])


def load_detail(path, step, at_head, writable, locked):
    if is_at(path, at_head):
        return (True, "at HEAD")
    if is_at(path, writable):
        return (True, "written by %s or a Step it comes after" % step)
    if is_at(path, locked):
        return (True, "a locked path")
    return (False, "not at HEAD and written by no Step at or before %s" % step)


def load_results(row, at_head, writable, locked):
    return tuple(
        result("loads", "%s %s" % (row_subject(row), path), passed, detail)
        for path in path_list(row, check_record.LOADS)
        for passed, detail in (load_detail(path, row["step"], at_head, writable, locked),)
    )


def need_results(row, writable):
    return tuple(
        result(
            "needs",
            "%s %s" % (row_subject(row), path),
            is_at(path, writable),
            "written by %s or a Step it comes after" % row["step"]
            if is_at(path, writable)
            else "outside the write-sets of %s and the Steps it comes after" % row["step"],
        )
        for path in path_list(row, check_record.NEEDS)
    )


def loads_exist(row, at_head):
    return all(is_at(path, at_head) for path in path_list(row, check_record.LOADS))


class Checkout:
    def __init__(self, root):
        self.root = root
        self.made = None

    def path(self):
        if self.made is None:
            self.made = self.create()
        return self.made

    def create(self):
        try:
            created = run([sys.executable, "probe.py", "create", "--repo", self.root], str(script_folder()))
        except CannotStart as exc:
            return (None, "cannot make a checkout of HEAD: %s" % exc)
        lines = decode(created.stdout).splitlines()
        if created.returncode != 0 or not lines:
            return (None, "cannot make a checkout of HEAD: %s" % failure_text(created))
        return (lines[-1], None)

    def remove(self):
        if self.made is None or self.made[0] is None:
            return None
        try:
            removed = run(
                [sys.executable, "probe.py", "remove", "--repo", self.root, "--path", self.made[0]],
                str(script_folder()),
            )
        except CannotStart as exc:
            return "cannot remove the checkout %s: %s" % (self.made[0], exc)
        return None if removed.returncode == 0 else "cannot remove the checkout %s: %s" % (
            self.made[0],
            failure_text(removed),
        )


def script_folder():
    return pathlib.Path(__file__).resolve().parent


def absent_outcome(absent, checkout):
    folder, problem = checkout.path()
    if folder is None:
        return (False, problem)
    try:
        ran = run(absent["command"], folder, shell=True)
    except CannotStart as exc:
        return (False, "cannot run the absent command: %s" % exc)
    if absent["shows"] in decode(ran.stdout) or absent["shows"] in decode(ran.stderr):
        return (True, "the output shows %s" % absent["shows"])
    return (False, "already passing on today's code: the output lacks %s" % absent["shows"])


def absent_results(row, at_head, checkout):
    if not loads_exist(row, at_head):
        return ()
    absent = row.get(check_record.ABSENT)
    if absent is None:
        return (result("absent", row_subject(row), False, "no absent, though every load exists at HEAD"),)
    if not check_record.is_absent(absent):
        return (
            result("absent", row_subject(row), False, "absent is not an object with exactly command and shows"),
        )
    passed, detail = absent_outcome(absent, checkout)
    return (result("absent", row_subject(row), passed, detail),)


def row_results(row, steps, at_head, locked, checkout):
    writable = written_files(row["step"], steps)
    return (
        load_results(row, at_head, writable, locked)
        + need_results(row, writable)
        + absent_results(row, at_head, checkout)
    )


def is_test_file(path):
    parts = path.split("/")
    name = parts[-1]
    return bool(TEST_FOLDERS.intersection(parts[:-1])) or any(
        fnmatch.fnmatchcase(name, pattern) for pattern in TEST_NAMES
    )


def path_refs(test, changed):
    stem_path, _ = posixpath.splitext(changed)
    folder = posixpath.dirname(changed)
    name = posixpath.basename(changed)
    stem = posixpath.splitext(name)[0]
    last = posixpath.basename(folder)
    nested = (last + "/" + stem, last + "." + stem, "from %s import %s" % (last, stem)) if last else ()
    sibling = ("./" + stem,) if posixpath.dirname(test) == folder else ()
    return (stem_path,) + nested + sibling


def names_file(text, changed):
    name = posixpath.basename(changed)
    if posixpath.splitext(name)[0] in GENERIC_STEMS:
        return False
    return re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text) is not None


def refers_to_changed(test, text, changed):
    return any(ref in text for ref in path_refs(test, changed)) or names_file(text, changed)


def quoted_globs(text):
    return tuple(
        quoted
        for match in QUOTED_RE.finditer(text)
        for quoted in (match.group(1) if match.group(1) is not None else match.group(2),)
        if "*" in quoted
    )


def refers_to_new(text, new):
    return any(fnmatch.fnmatchcase(new, glob) for glob in quoted_globs(text))


def first_writer(path, steps):
    writers = tuple(
        step["name"]
        for step in steps
        if check_items.is_text(step.get("name")) and is_at(path, check_items.step_files(step))
    )
    return writers[0] if writers else "a Step"


def unaffected_reasons(record):
    entries = record.get("unaffected")
    return tuple(
        (entry["file"], entry["reason"])
        for entry in (entries if isinstance(entries, list) else ())
        if isinstance(entry, dict)
        and all(check_items.is_text(entry.get(key)) for key in check_record.UNAFFECTED_KEYS)
    )


def reason_for(path, reasons):
    return next((reason for listed, reason in reasons if is_at(path, (listed,))), None)


def candidate_results(test, referred, steps, reasons):
    reason = reason_for(test, reasons)
    return tuple(
        result(
            "unaffected",
            test,
            reason is not None,
            "listed in unaffected: %s" % reason
            if reason is not None
            else "refers to %s, which %s writes; give it to a Step or list it in unaffected"
            % (path, first_writer(path, steps)),
        )
        for path in referred
    )


def unaffected_results(record, steps, at_head, locked, root):
    listed = frozenset(path for step in steps for path in check_items.step_files(step))
    changed = tuple(path for path in at_head if is_at(path, listed))
    created = tuple(sorted(path for path in listed if not is_at(path, at_head)))
    if not changed and not created:
        return ()
    owned = listed | locked
    candidates = tuple(path for path in at_head if is_test_file(path) and not is_at(path, owned))
    reasons = unaffected_reasons(record)
    return tuple(
        entry
        for test in candidates
        for text in (head_text(root, test),)
        for entry in candidate_results(
            test,
            tuple(path for path in changed if refers_to_changed(test, text, path))
            + tuple(path for path in created if refers_to_new(text, path)),
            steps,
            reasons,
        )
    )


def all_results(record, root, checkout):
    at_head = head_files(root)
    steps = record_steps(record)
    locked = record_locked(record)
    rows = tuple(
        entry for row in locked_rows(record) for entry in row_results(row, steps, at_head, locked, checkout)
    )
    return rows + unaffected_results(record, steps, at_head, locked, root)


def checked(record, root):
    checkout = Checkout(root)
    try:
        results = all_results(record, root, checkout)
    finally:
        leftover = checkout.remove()
    return results, leftover


def parse_arguments(argv):
    if len(argv) != 4:
        return None
    pairs = dict(zip(argv[0::2], argv[1::2]))
    if sorted(pairs) != sorted(OPTIONS) or any(value.startswith("-") for value in pairs.values()):
        return None
    return pairs["--record"], pairs["--repo"]


def read_record(path):
    try:
        record = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, RecursionError):
        return None
    return record if isinstance(record, dict) and check_items.is_unicode(record) else None


def write_record(path, record):
    try:
        atomic_file.replace(path, (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    except (OSError, UnicodeEncodeError):
        return False
    return True


def main(argv):
    arguments = parse_arguments(argv)
    if arguments is None:
        print(USAGE, file=sys.stderr)
        return 2
    record_path, repo = arguments
    root = work_tree_root(repo)
    if root is None:
        print("cannot read: " + repo, file=sys.stderr)
        return 2
    record = read_record(record_path)
    if record is None:
        print("cannot read: " + record_path, file=sys.stderr)
        return 2
    try:
        results, leftover = checked(record, root)
    except CannotStart as exc:
        print("cannot run git in %s: %s" % (repo, exc), file=sys.stderr)
        return 2
    feasibility = {"digest": check_record.feasibility_digest(record, results), "results": list(results)}
    if not write_record(record_path, {**record, "feasibility": feasibility}):
        print("cannot write: " + record_path, file=sys.stderr)
        return 2
    for entry in results:
        print("%s: %s %s: %s" % (entry["status"], entry["check"], entry["subject"], entry["detail"]))
    if leftover is not None:
        print("warning: " + leftover, file=sys.stderr)
    return 0 if all(entry["status"] == PASSED for entry in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
