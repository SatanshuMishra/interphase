import hashlib
import json
import os
import re
import sys

FIELDS = frozenset(
    (
        "name",
        "task",
        "files",
        "source",
        "acceptance",
        "after",
        "contract_group",
        "type",
        "complexity",
        "file_notes",
        "msp",
        "spec_ref",
        "assumptions",
    )
)
REQUIRED = ("name", "task", "files", "source", "acceptance")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(\d+(?:\.\d+)*)\.?[ \t]+(.*?)[ \t]*$")
FENCE_RE = re.compile(r"^ {0,3}(```|~~~)")
USAGE = "usage: python3 check_items.py ITEMS"


def error(message):
    return ("error", 0, message)


def warning(message):
    return ("warning", 0, message)


def is_text(value):
    return isinstance(value, str) and value != ""


def is_text_list(value):
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def label(index, step):
    name = step.get("name") if isinstance(step, dict) else None
    return "step %r" % name if isinstance(name, str) else "step %d" % (index + 1)


def check_fields(who, step):
    unknown = tuple(
        error("%s has unknown field %r" % (who, key)) for key in sorted(step) if key not in FIELDS
    )
    missing = tuple(
        error("%s lacks required field %r" % (who, key)) for key in REQUIRED if key not in step
    )
    return unknown + missing


def check_name(who, step):
    if "name" not in step:
        return ()
    name = step["name"]
    if not isinstance(name, str) or not NAME_RE.match(name):
        return (error("%s has a name that is not lowercase kebab-case" % who),)
    return ()


def check_task(who, step):
    if "task" in step and not is_text(step["task"]):
        return (error("%s has a task that is not a non-empty string" % who),)
    return ()


def bad_path(path):
    return os.path.isabs(path) or path.startswith("\\") or ".." in re.split(r"[\\/]", path)


def check_files(who, step):
    if "files" not in step:
        return ()
    files = step["files"]
    if not isinstance(files, list) or not files or not all(is_text(item) for item in files):
        return (error("%s has files that is not a non-empty list of non-empty strings" % who),)
    return tuple(
        error("%s has files entry %r that is absolute or holds a '..' segment" % (who, path))
        for path in files
        if bad_path(path)
    )


def step_files(step):
    files = step.get("files")
    return frozenset(item for item in files if isinstance(item, str)) if isinstance(files, list) else frozenset()


def check_acceptance_entry(who, entry, files):
    if not isinstance(entry, dict) or not is_text(entry.get("file")) or not is_text(entry.get("test")):
        return (error("%s has an acceptance entry that is not an object with non-empty string file and test" % who),)
    if entry["file"] not in files:
        return (error("%s has acceptance file %r that is not in its files" % (who, entry["file"])),)
    return ()


def check_acceptance(who, step):
    if "acceptance" not in step:
        return ()
    acceptance = step["acceptance"]
    if not isinstance(acceptance, list):
        return (error("%s has acceptance that is not a list" % who),)
    if not acceptance:
        return (warning("%s has an empty acceptance list" % who),)
    files = step_files(step)
    return tuple(finding for entry in acceptance for finding in check_acceptance_entry(who, entry, files))


def check_after_shape(who, step):
    if "after" in step and not is_text_list(step["after"]):
        return (error("%s has after that is not a list of strings" % who),)
    return ()


def check_source_shape(who, step):
    if "source" not in step:
        return ()
    source = step["source"]
    if not isinstance(source, dict):
        return (error("%s has a source that is not an object" % who),)
    path = source.get("path")
    sha = source.get("sha256")
    path_findings = () if isinstance(path, str) and os.path.isabs(path) else (
        error("%s has a source.path that is not absolute" % who),
    )
    sha_findings = () if isinstance(sha, str) and SHA_RE.match(sha) else (
        error("%s has a source.sha256 that is not 64 lowercase hex digits" % who),
    )
    return path_findings + sha_findings


def check_type(who, step):
    if "type" not in step:
        return ()
    if step["type"] != "contract":
        return (error("%s has type %r; the only allowed type is 'contract'" % (who, step["type"])),)
    if "contract_group" not in step:
        return (error("%s has type 'contract' but no contract_group" % who),)
    return ()


def check_complexity(who, step):
    if "complexity" in step and step["complexity"] not in ("simple", "complex"):
        return (error("%s has complexity that is not 'simple' or 'complex'" % who),)
    return ()


def check_file_notes(who, step):
    if "file_notes" not in step:
        return ()
    notes = step["file_notes"]
    if not isinstance(notes, dict) or not all(isinstance(value, str) for value in notes.values()):
        return (error("%s has file_notes that is not an object of string values" % who),)
    files = step_files(step)
    return tuple(
        error("%s has file_notes key %r that is not in its files" % (who, key))
        for key in sorted(notes)
        if key not in files
    )


def check_labels(who, step):
    return tuple(
        error("%s has %s that is not a non-empty string" % (who, key))
        for key in ("msp", "contract_group")
        if key in step and not is_text(step[key])
    )


def check_assumptions(who, step):
    if "assumptions" not in step:
        return ()
    assumptions = step["assumptions"]
    if not is_text_list(assumptions):
        return (error("%s has assumptions that is not a list of strings" % who),)
    if assumptions:
        return (warning("%s has a non-empty assumptions list" % who),)
    return ()


def check_spec_ref_shape(who, step):
    if "spec_ref" not in step:
        return (warning("%s has no spec_ref" % who),)
    if not is_text_list(step["spec_ref"]):
        return (error("%s has spec_ref that is not a list of strings" % who),)
    return ()


STEP_CHECKS = (
    check_fields,
    check_name,
    check_task,
    check_files,
    check_acceptance,
    check_after_shape,
    check_source_shape,
    check_type,
    check_complexity,
    check_file_notes,
    check_labels,
    check_assumptions,
    check_spec_ref_shape,
)


def check_step(index, step):
    who = label(index, step)
    if not isinstance(step, dict):
        return (error("%s is not an object" % who),)
    return tuple(finding for check in STEP_CHECKS for finding in check(who, step))


def named_steps(steps):
    return tuple(
        (index, step)
        for index, step in enumerate(steps)
        if isinstance(step, dict) and isinstance(step.get("name"), str)
    )


def check_duplicates(steps):
    names = tuple(step["name"] for _, step in named_steps(steps))
    duplicated = sorted(frozenset(name for name in names if names.count(name) > 1))
    return tuple(error("step %r: name is duplicated" % name) for name in duplicated)


def after_list(step):
    after = step.get("after", ())
    return tuple(after) if is_text_list(after) else ()


def after_graph(steps):
    pairs = tuple((step["name"], after_list(step)) for _, step in named_steps(steps))
    names = frozenset(name for name, _ in pairs)
    return {name: tuple(dep for dep in deps if dep in names) for name, deps in pairs}


def reachable(graph, start):
    seen = frozenset()
    frontier = frozenset(graph.get(start, ()))
    while frontier:
        seen = seen | frontier
        frontier = frozenset(dep for node in frontier for dep in graph.get(node, ())) - seen
    return seen


def check_after_names(steps):
    names = frozenset(step["name"] for _, step in named_steps(steps))
    return tuple(
        error("%s: after names unknown step %r" % (label(index, step), dep))
        for index, step in enumerate(steps)
        if isinstance(step, dict)
        for dep in after_list(step)
        if dep not in names
    )


def check_cycles(graph):
    members = sorted(name for name in graph if name in reachable(graph, name))
    if not members:
        return ()
    return (error("after edges form a cycle among steps: %s" % ", ".join(members)),)


def check_sources(steps):
    sourced = tuple(
        (index, step) for index, step in enumerate(steps) if isinstance(step, dict) and "source" in step
    )
    if not sourced:
        return ()
    first = sourced[0][1]["source"]
    return tuple(
        error("%s: source differs from the first step's source" % label(index, step))
        for index, step in sourced[1:]
        if step["source"] != first
    )


def contract_groups(steps):
    groups = sorted(
        frozenset(
            step["contract_group"]
            for _, step in named_steps(steps)
            if is_text(step.get("contract_group"))
        )
    )
    return tuple(
        (group, tuple(step for _, step in named_steps(steps) if step.get("contract_group") == group))
        for group in groups
    )


def check_group(group, members, graph):
    contracts = tuple(step["name"] for step in members if step.get("type") == "contract")
    if len(contracts) > 1:
        return (error("contract_group %r has more than one contract step: %s" % (group, ", ".join(contracts))),)
    if not contracts:
        return ()
    contract = contracts[0]
    return tuple(
        error(
            "step %r: in contract_group %r but does not reach contract step %r through after"
            % (step["name"], group, contract)
        )
        for step in members
        if step["name"] != contract and contract not in reachable(graph, step["name"])
    )


def check_contracts(steps, graph):
    return tuple(
        finding for group, members in contract_groups(steps) for finding in check_group(group, members, graph)
    )


def parse_headings(text):
    in_fence = False
    headings = []
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        match = None if in_fence else HEADING_RE.match(line)
        if match:
            headings.append((len(match.group(1)), match.group(2), match.group(3)))
    return tuple(headings)


def spec_source(steps):
    source = next(
        (step["source"] for step in steps if isinstance(step, dict) and isinstance(step.get("source"), dict)),
        None,
    )
    if source is None:
        return None
    path = source.get("path")
    sha = source.get("sha256")
    if not isinstance(path, str) or not os.path.isabs(path):
        return None
    return (path, sha if isinstance(sha, str) and SHA_RE.match(sha) else None)


def read_spec(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def ref_numbers(ref, headings):
    return tuple(number for _, number, title in headings if ref in (number, title, "%s %s" % (number, title)))


def spec_refs(step):
    refs = step.get("spec_ref", ())
    return tuple(refs) if is_text_list(refs) else ()


def check_spec_refs(steps, headings):
    return tuple(
        error("%s: spec_ref %r matches no numbered heading in the spec" % (label(index, step), ref))
        for index, step in enumerate(steps)
        if isinstance(step, dict)
        for ref in spec_refs(step)
        if not ref_numbers(ref, headings)
    )


def claims(number, claimed):
    return any(item == number or item.startswith(number + ".") for item in claimed)


def check_unclaimed(steps, headings):
    claimed = frozenset(
        number
        for step in steps
        if isinstance(step, dict)
        for ref in spec_refs(step)
        for number in ref_numbers(ref, headings)
    )
    return tuple(
        warning("section %s. %s is unclaimed by any step's spec_ref" % (number, title))
        for level, number, title in headings
        if level == 2 and not claims(number, claimed)
    )


def check_spec(steps):
    source = spec_source(steps)
    if source is None:
        return ()
    path, sha = source
    data = read_spec(path)
    if data is None:
        return (error("spec file %s is missing" % path),)
    digest = hashlib.sha256(data).hexdigest()
    mismatch = (
        (error("sha256 mismatch for %s: items say %s, file is %s" % (path, sha, digest)),)
        if sha is not None and sha != digest
        else ()
    )
    headings = parse_headings(data.decode("utf-8", errors="replace"))
    return mismatch + check_spec_refs(steps, headings) + check_unclaimed(steps, headings)


def check_steps(steps):
    graph = after_graph(steps)
    per_step = tuple(finding for index, step in enumerate(steps) for finding in check_step(index, step))
    return (
        per_step
        + check_duplicates(steps)
        + check_after_names(steps)
        + check_cycles(graph)
        + check_sources(steps)
        + check_contracts(steps, graph)
        + check_spec(steps)
    )


def check_text(text):
    try:
        steps = json.loads(text)
    except ValueError as exc:
        return (error("items file is not valid JSON: %s" % exc),)
    if not isinstance(steps, list):
        return (error("items file is not a JSON array"),)
    if not steps:
        return (error("items file is an empty array"),)
    return check_steps(steps)


def check_file(path):
    with open(path, "r", encoding="utf-8") as handle:
        return check_text(handle.read())


def main(argv):
    if len(argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        findings = check_file(argv[0])
    except (OSError, UnicodeDecodeError) as exc:
        print("error: cannot read %s: %s" % (argv[0], exc))
        return 2
    for severity, _, message in findings:
        print("%s: %s" % (severity, message))
    return 1 if any(severity == "error" for severity, _, _ in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
