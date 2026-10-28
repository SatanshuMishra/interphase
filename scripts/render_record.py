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
    "Once committed, these files are locked: no later Step may change them."
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


def covered_numbers(steps, criteria):
    claimed = frozenset(number for step in steps for number in step["criteria"])
    return tuple(
        number for number, criterion in criteria.items() if number in claimed and check_record.has_lines(criterion)
    )


def row_line(test):
    return "- `%s` `%s` (%s): given %s; expects %s." % (
        test["file"],
        test["name"],
        test.get(check_record.CHECK, ""),
        clause(test["given"]),
        clause(test["expect"]),
    )


def authored_block(criterion, block):
    return "\n\n".join((block, "\n".join(row_line(test) for test in criterion["tests"])))


def author_files(locked, covered, criteria, amendment):
    if amendment is None:
        return list(locked)
    held = tuple(test["file"] for number in covered for test in criteria[number]["tests"])
    return [path for path in locked if check_record.check_items.shared_paths((path,), held)]


def author_assumptions(steps, covered):
    texts = tuple(
        text
        for step in steps
        if any(number in covered for number in step["criteria"])
        for text in step.get("assumptions", ())
    )
    kept = [text for position, text in enumerate(texts) if text not in texts[:position]]
    return (("assumptions", kept),) if kept else ()


def check_author_item(record, steps, criteria, blocks, source, amendment):
    covered = covered_numbers(steps, criteria)
    if "locked" not in record or not covered:
        return None
    task = "\n\n".join(
        (CHECK_AUTHOR_OPENING,) + tuple(authored_block(criteria[number], blocks[number]) for number in covered)
    )
    msp = (("msp", CHECK_AUTHOR),) if any("msp" in step for step in steps) else ()
    return dict(
        (
            ("name", CHECK_AUTHOR),
            ("role", CHECK_AUTHOR),
            ("task", task),
            ("files", author_files(record["locked"], covered, criteria, amendment)),
            ("source", dict(source)),
            ("acceptance", []),
        )
        + msp
        + (("spec_ref", list(covered)),)
        + author_assumptions(steps, covered)
    )


def after_author(entry):
    rest = {key: value for key, value in entry.items() if key != "after"}
    return {**rest, "after": [CHECK_AUTHOR] + list(entry.get("after", ()))}


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
    items = [item(step, criteria, blocks, source) for step in steps]
    author = check_author_item(record, steps, criteria, blocks, source, amendment)
    if author is None:
        return ((), new_spec_text, items)
    return ((), new_spec_text, [author] + [after_author(entry) for entry in items])


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
