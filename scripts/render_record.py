import hashlib
import importlib.util
import json
import os
import pathlib
import re
import sys

USAGE = "usage: python3 render_record.py --record RECORD --spec SPEC --items ITEMS [--amendment N]"
OPTIONS = ("--items", "--record", "--spec")
AMENDMENT = "--amendment"
AMENDMENT_RE = re.compile(r"[1-9][0-9]*")
PROVES = "Acceptance criteria this Step proves:"
CARRIED = ("after", "contract_group", "type", "complexity", "file_notes", "msp")
LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")
SEAMS_HEAD = "Seams:"
LINES_HEAD = "Acceptance lines:"
RISKS = "### Risks"
CHECK_AUTHOR = "check-author"
CHECK_AUTHOR_OPENING = (
    "Write the acceptance tests below before anything is built, and never write the code they test. "
    "Write each test in the file and under the name it lists, from the given and the expected result it lists, "
    "so that it runs its acceptance line: it fails on today's code because the behaviour is absent, "
    "and passes once the behaviour exists. Load the code under test inside each test, never at import time. "
    "Once committed, these files are locked: no later Step may change them. "
    "Load each module from the path its row lists after Loads, never a path you infer. "
    "Before handing back, prove each test can pass inside the planned files: write a probe implementation only "
    "inside the files its row lists after Its probe may write, and never commit it; run the test against it until "
    "it passes. Prove each test fails on today's code by an assertion failure or a missing module, never by a crash "
    "in the harness such as a TypeError, a ReferenceError, or a collection, import-time or setup error. "
    "A test that cannot pass against any probe inside those files is reported back as failed with the reason, "
    "never weakened."
)


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_record = load_sibling("check_record")
check_spec = load_sibling("check_spec")
atomic_file = load_sibling("atomic_file")


def one_line(text):
    return LINE_BREAK_RE.sub(" ", text)


def cell(text):
    return one_line(text).replace("|", "\\|")


def population(test):
    return "%s cases, %s runs each, pass rate at least %s" % (test["cases"], test["runs"], test["pass_rate"])


def columns(criterion):
    tabled = ("Covers",) if "case_table" in criterion else ()
    varying = ("Runs",) if "varies" in criterion else ()
    return ("Test", "Given", "Expected") + tabled + varying


def row(test, criterion):
    tabled = ("; ".join(test.get(check_record.COVERS, ())) or "none",) if "case_table" in criterion else ()
    varying = (population(test),) if "varies" in criterion else ()
    cells = ("`%s` `%s`" % (test["file"], test["name"]), test["given"], test["expect"]) + tabled + varying
    return "| %s |" % " | ".join(cell(text) for text in cells)


def table(criterion):
    names = columns(criterion)
    head = "| %s |\n|%s" % (" | ".join(names), "---|" * len(names))
    rows = tuple(row(test, criterion) for test in criterion["tests"])
    return ("\n".join((head,) + rows),) if rows else ()


def listed(head, lines):
    return ("\n".join((head,) + lines),) if lines else ()


def seam_line(seam):
    unrunnable = "" if seam["builder_runs"] else " The builder cannot run it."
    return one_line(
        "- `%s`: %s. Catches: %s. Misses: %s.%s"
        % (
            seam["name"],
            seam["interface"].rstrip("."),
            seam["catches"].rstrip("."),
            seam["misses"].rstrip("."),
            unrunnable,
        )
    )


def clause(text):
    return one_line(text).rstrip(".")


def line_sentence(line):
    surface = line["surface"]
    judged = (
        " three times and judge each run against the rubric: " + clause(line["rubric"])
        if line["kind"] == "judged"
        else ""
    )
    return "%s (%s, %s %s): run `%s` from the repository root%s; it passes when %s." % (
        line["id"],
        line["kind"],
        surface["family"],
        surface["target"],
        one_line(line["command"]),
        judged,
        clause(line["pass"]),
    )


def seam_text(seam):
    return one_line("Seam: `%s`, %s." % (seam["name"], seam["interface"].rstrip(".")))


def criterion_block(criterion, seams):
    inputs = tuple(
        "- %s (`%s`): %s" % (domain["over"], domain["name"], "; ".join(domain["classes"]))
        for domain in criterion.get("domains", ())
    )
    head = "Cases for %s:" % ("a security need" if criterion.get("case_table") == "security" else "a refusal")
    unproven = ("Unproven: " + criterion["unproven"],) if "unproven" in criterion else ()
    parts = (
        (
            "### %s %s" % (criterion["number"], criterion["title"]),
            criterion["text"],
            seam_text(seams[criterion["seam"]]),
        )
        + listed(LINES_HEAD, tuple("- " + line_sentence(line) for line in criterion.get("acceptance", ())))
        + listed(head, inputs)
        + table(criterion)
        + unproven
    )
    return "\n\n".join(parts)


def record_errors(record_text):
    return tuple(
        message
        for severity, message in check_record.check(record_text, complete=True)
        if severity == "error"
    )


def task_errors(steps):
    return tuple(
        "step %s has no task" % step["name"]
        for step in steps
        if not (isinstance(step.get("task"), str) and step["task"])
    )


def section_errors(sections):
    if not sections:
        return ("spec has no Test seams section",)
    if len(sections) > 1:
        return ("spec has %d Test seams sections" % len(sections),)
    return ()


def number_errors(criteria, sections):
    if len(sections) != 1:
        return ()
    section = sections[0][1]
    return tuple(
        "criterion %s is outside Test seams section %s; its number must start with '%s.'"
        % (criterion["number"], section, section)
        for criterion in criteria
        if not criterion["number"].startswith(section + ".")
    )


def assumption_errors(steps, lines):
    known = frozenset(check_spec.intent_ids(lines, check_spec.numbered_headings(lines)))
    return tuple(
        "step %s has an assumption that %s: %s" % (step["name"], problem, text)
        for step in steps
        for text in step.get("assumptions", ())
        for problem in assumption_problems(text, known)
    )


def assumption_problems(text, known):
    cited = tuple(match.group(1) for match in check_spec.RELIES.finditer(text))
    if not cited:
        return ("cites no intent line; end it with (relies on I<n>)",)
    return tuple("relies on %s, which is not an intent line of the spec" % name for name in cited if name not in known)


def risks_text(lines):
    starts = tuple(number for number, line in enumerate(lines, start=1) if line.rstrip() == RISKS)
    boundaries = tuple(
        number for number, line in enumerate(lines, start=1) if check_spec.UP_TO_LEVEL_THREE.match(line)
    )
    return one_line("".join(line for start in starts for line in check_spec.section_body(lines, start, boundaries)))


def risk_errors(record, lines):
    listed_risks = risks_text(lines)
    return tuple(
        "repeated failure kind %s is not listed under Risks" % entry["kind"]
        for entry in record["outcomes"]["repeated"]
        if one_line(entry["kind"]) not in listed_risks
    )


def amendment_errors(steps, amendment):
    if amendment is None or steps:
        return ()
    return ("no step has amendment %d" % amendment,)


def terminated(line):
    return line.splitlines()[0] != line


def replace_section(spec_text, lines, start, blocks):
    body = check_spec.section_body(lines, start, check_spec.level_two_lines(lines))
    head = "".join(lines[:start])
    tail = "".join(lines[start + len(body) :])
    joint = "" if terminated(lines[start - 1]) else "\n"
    text = head + joint + "\n" + "".join(block + "\n\n" for block in blocks) + tail
    return text if tail or spec_text.endswith("\n") else text.rstrip("\n")


def task_text(step, blocks):
    return "\n\n".join((step["task"], PROVES) + tuple(blocks[number] for number in step["criteria"]))


def acceptance(step, criteria):
    pairs = tuple(
        (test["file"], test["name"])
        for number in step["criteria"]
        for test in criteria[number]["tests"]
        if test["step"] == step["name"]
    )
    return [
        {"file": file, "test": name}
        for position, (file, name) in enumerate(pairs)
        if (file, name) not in pairs[:position]
    ]


def within(step, names):
    kept = [name for name in step.get("after", ()) if name in names]
    rest = {key: value for key, value in step.items() if key != "after"}
    return {**rest, "after": kept} if kept else rest


def chosen_steps(steps, amendment):
    if amendment is None:
        return tuple(steps)
    picked = tuple(step for step in steps if step.get("amendment") == amendment)
    names = frozenset(step["name"] for step in picked)
    return tuple(within(step, names) for step in picked)


def carried(step, keys):
    return tuple((key, step[key]) for key in keys if key in step)


def item(step, criteria, blocks, source):
    return dict(
        (
            ("name", step["name"]),
            ("task", task_text(step, blocks)),
            ("files", list(step["files"])),
            ("source", dict(source)),
            ("acceptance", acceptance(step, criteria)),
        )
        + carried(step, CARRIED)
        + (("spec_ref", list(step["criteria"])),)
        + carried(step, ("assumptions",))
    )


def author_name(msp):
    return CHECK_AUTHOR if msp is None else "%s-%s" % (CHECK_AUTHOR, msp)


def unique_values(values):
    return tuple(value for position, value in enumerate(values) if value not in values[:position])


def owned_rows(criterion, names):
    return tuple(test for test in criterion["tests"] if test["step"] in names)


def locked_criteria(record):
    return tuple(criterion for criterion in record["criteria"] if check_record.has_lines(criterion))


def owner_steps(steps, record):
    owners = frozenset(test["step"] for criterion in locked_criteria(record) for test in criterion["tests"])
    return tuple(step for step in steps if step["name"] in owners)


def probe_paths(test, steps):
    return unique_values(tuple(path for step in check_record.steps_through(test["step"], steps) for path in step["files"]))


def listed_paths(head, paths):
    return (" %s: %s." % (head, ", ".join(paths)),) if paths else ()


def row_line(test, steps):
    base = "- `%s` `%s` (%s): given %s; expects %s." % (
        test["file"],
        test["name"],
        test.get(check_record.CHECK, ""),
        clause(test["given"]),
        clause(test["expect"]),
    )
    parts = (
        listed_paths("Loads", tuple(test.get(check_record.LOADS, ())))
        + listed_paths("Needs", tuple(test.get(check_record.NEEDS, ())))
        + listed_paths("Its probe may write", probe_paths(test, steps))
    )
    return base + "".join(parts)


def authored_block(rows, block, steps):
    return "\n\n".join((block, "\n".join(row_line(test, steps) for test in rows)))


def unowned_paths(locked, record):
    held = tuple(test["file"] for criterion in locked_criteria(record) for test in criterion["tests"])
    return tuple(path for path in locked if not check_record.check_items.shared_paths((path,), held))


def author_files(locked, rows, extra):
    held = tuple(test["file"] for test in rows)
    return [path for path in locked if check_record.check_items.shared_paths((path,), held) or path in extra]


def author_assumptions(group):
    kept = list(unique_values(tuple(text for step in group for text in step.get("assumptions", ()))))
    return (("assumptions", kept),) if kept else ()


def author_group(owners, msp):
    return tuple(step for step in owners if step.get("msp") == msp)


def check_author_item(record, steps, group, msp, label, blocks, source, extra):
    names = frozenset(step["name"] for step in group)
    proved = tuple(
        (criterion, owned_rows(criterion, names))
        for criterion in locked_criteria(record)
        if owned_rows(criterion, names)
    )
    rows = tuple(test for _, test_rows in proved for test in test_rows)
    task = "\n\n".join(
        (CHECK_AUTHOR_OPENING,)
        + tuple(authored_block(test_rows, blocks[criterion["number"]], steps) for criterion, test_rows in proved)
    )
    labelled = (("msp", label),) if label is not None else ()
    return dict(
        (
            ("name", author_name(msp)),
            ("role", CHECK_AUTHOR),
            ("task", task),
            ("files", author_files(record["locked"], rows, extra)),
            ("source", dict(source)),
            ("acceptance", []),
        )
        + labelled
        + (("spec_ref", [criterion["number"] for criterion, _ in proved]),)
        + author_assumptions(group)
    )


def loader_msps(path, owners, record):
    by_name = {step["name"]: step for step in owners}
    return unique_values(
        tuple(
            by_name[test["step"]].get("msp")
            for criterion in locked_criteria(record)
            for test in criterion["tests"]
            if test["step"] in by_name
            if check_record.check_items.shared_paths((path,), tuple(test.get(check_record.LOADS, ())))
        )
    )


def unowned_by_msp(record, owners, amendment):
    if amendment is not None:
        return {}
    placed = tuple(
        (path, loaders[0] if len(loaders) == 1 else None)
        for path in unowned_paths(record["locked"], record)
        for loaders in (loader_msps(path, owners, record),)
    )
    return {msp: frozenset(path for path, owner in placed if owner == msp) for _, msp in placed}


def author_label(msp, msps, steps):
    if msp is not None:
        return msp
    if msps == (None,) and any("msp" in step for step in steps):
        return CHECK_AUTHOR
    return None


def check_author_items(record, steps, blocks, source, amendment):
    if "locked" not in record:
        return ()
    owners = owner_steps(steps, record)
    msps = unique_values(tuple(step.get("msp") for step in owners))
    extra = unowned_by_msp(record, owners, amendment)
    return tuple(
        check_author_item(
            record,
            steps,
            author_group(owners, msp),
            msp,
            author_label(msp, msps, steps),
            blocks,
            source,
            extra.get(msp, frozenset()),
        )
        for msp in msps
    )


def author_for(step, authors):
    own = author_name(step.get("msp"))
    if any(author["name"] == own for author in authors):
        return own
    if any(author.get("msp") == CHECK_AUTHOR for author in authors):
        return CHECK_AUTHOR
    return None


def after_author(entry, author):
    if author is None:
        return entry
    rest = {key: value for key, value in entry.items() if key != "after"}
    return {**rest, "after": [author] + list(entry.get("after", ()))}


def render(record_text, spec_text, spec_path, amendment=None):
    rejected = record_errors(record_text)
    if rejected:
        return (rejected, None, None)
    record = json.loads(record_text)
    steps = chosen_steps(record["steps"], amendment)
    lines = tuple(spec_text.splitlines(keepends=True))
    sections = check_spec.seam_sections(check_spec.numbered_headings(lines))
    errors = (
        task_errors(record["steps"])
        + section_errors(sections)
        + number_errors(record["criteria"], sections)
        + amendment_errors(steps, amendment)
        + assumption_errors(steps, lines)
        + risk_errors(record, lines)
    )
    if errors:
        return (errors, None, None)
    criteria = {criterion["number"]: criterion for criterion in record["criteria"]}
    by_name = {seam["name"]: seam for seam in record["seams"]}
    blocks = {number: criterion_block(criterion, by_name) for number, criterion in criteria.items()}
    seams = listed(SEAMS_HEAD, tuple(seam_line(seam) for seam in record["seams"]))
    ordered = seams + tuple(blocks[criterion["number"]] for criterion in record["criteria"])
    new_spec_text = replace_section(spec_text, lines, sections[0][0], ordered)
    source = {"path": spec_path, "sha256": hashlib.sha256(new_spec_text.encode("utf-8")).hexdigest()}
    authors = check_author_items(record, steps, blocks, source, amendment)
    items = [after_author(item(step, criteria, blocks, source), author_for(step, authors)) for step in steps]
    return ((), new_spec_text, list(authors) + items)


def parse_arguments(argv):
    pairs = tuple(zip(argv[0::2], argv[1::2]))
    options = tuple(sorted(option for option, _ in pairs))
    if len(argv) % 2 or options not in (OPTIONS, tuple(sorted(OPTIONS + (AMENDMENT,)))):
        return None
    if any(value in OPTIONS + (AMENDMENT,) for _, value in pairs):
        return None
    values = dict(pairs)
    amendment = values.get(AMENDMENT)
    if amendment is not None and not AMENDMENT_RE.fullmatch(amendment):
        return None
    return values["--record"], values["--spec"], values["--items"], None if amendment is None else int(amendment)


def read_text(path):
    try:
        return pathlib.Path(path).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def write_bytes(path, data):
    try:
        atomic_file.replace(path, data)
    except OSError:
        return False
    return True


def main(argv):
    arguments = parse_arguments(argv)
    if arguments is None:
        print(USAGE, file=sys.stderr)
        return 2
    record_path, spec_path, items_path, amendment = arguments
    texts = tuple((path, read_text(path)) for path in (record_path, spec_path))
    unreadable = tuple(path for path, text in texts if text is None)
    if unreadable:
        print("\n".join("cannot read: " + path for path in unreadable), file=sys.stderr)
        return 2
    errors, spec_text, items = render(
        texts[0][1], texts[1][1], os.path.abspath(spec_path), amendment
    )
    if errors:
        print("\n".join("error: " + message for message in errors))
        return 1
    outputs = (
        (spec_path, spec_text.encode("utf-8")),
        (items_path, (json.dumps(items, indent=2, ensure_ascii=False) + "\n").encode("utf-8")),
    )
    for path, data in outputs:
        if not write_bytes(path, data):
            print("cannot write: " + path, file=sys.stderr)
            return 2
        print("wrote " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
