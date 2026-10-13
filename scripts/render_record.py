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
GIVE_WAY_HEAD = "When the bound is reached, these give way, first to last:"
KEEPS_HEAD = "These never give way:"
INVALID_MARK = " (invalid)"
TABLE_HEAD = "| Test | Runs in | Given | Expected | Covers |\n|---|---|---|---|---|"
LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_record = load_sibling("check_record")
check_spec = load_sibling("check_spec")


def one_line(text):
    return LINE_BREAK_RE.sub(" ", text)


def cell(text):
    return one_line(text).replace("|", "\\|")


def runs_in(test, what):
    if not all(key in test for key in check_record.POPULATION_KEYS):
        return what[test["env"]]
    return "%s; %s cases, %s runs each, pass rate at least %s" % (
        what[test["env"]],
        test["cases"],
        test["runs"],
        test["pass_rate"],
    )


def row(test, what):
    cells = (
        "`%s` `%s`" % (test["file"], test["name"]),
        runs_in(test, what),
        test["given"],
        test["expect"],
        "; ".join(test.get(check_record.COVERS, ())) or "none",
    )
    return "| %s |" % " | ".join(cell(text) for text in cells)


def citation(fact):
    if "url" in fact:
        return fact["url"]
    if "command" in fact:
        return 'ran `%s`, which showed "%s"' % (fact["command"], fact["output"])
    if "assumed" in fact:
        return "assumed, not run: " + fact["assumed"]
    return '`%s`:%s, quoting "%s"' % (fact["path"], fact["line"], fact["quote"])


def class_text(name, invalid):
    return name + INVALID_MARK if name in invalid else name


def input_line(domain):
    invalid = tuple(domain.get("invalid", ()))
    return "- %s (`%s`, %s source, %s): %s" % (
        domain["over"],
        domain["name"],
        domain["source"],
        "closed" if domain["closed"] else "open",
        "; ".join(class_text(name, invalid) for name in domain["classes"]),
    )


def cited_facts(criterion):
    domain_facts = tuple(domain["fact"] for domain in criterion.get("domains", ()) if "fact" in domain)
    return check_record.unique(tuple(criterion.get("facts", ())) + domain_facts)


def listed(head, lines):
    return ("\n".join((head,) + lines),) if lines else ()


def criterion_block(criterion, what, facts):
    where = "Where passing proves it: %s." % "; ".join(what[name] for name in criterion["where"])
    inputs = tuple(input_line(domain) for domain in criterion.get("domains", ()))
    order = tuple("%d. %s" % (position + 1, item) for position, item in enumerate(criterion.get("gives_way", ())))
    kept = tuple("- %s" % item for item in criterion.get("keeps", ()))
    cited = tuple(
        one_line("- %s (%s)" % (facts[fact_id]["fact"], citation(facts[fact_id])))
        for fact_id in cited_facts(criterion)
    )
    rows = tuple(row(test, what) for test in criterion["tests"])
    unproven = ("Unproven: " + criterion["unproven"],) if "unproven" in criterion else ()
    parts = (
        ("### %s %s" % (criterion["number"], criterion["title"]), criterion["text"], where)
        + listed("Inputs:", inputs)
        + listed(GIVE_WAY_HEAD, order)
        + listed(KEEPS_HEAD, kept)
        + listed("Facts:", cited)
        + listed(TABLE_HEAD, rows)
        + unproven
    )
    return "\n\n".join(parts)


def record_errors(record_text, root, spec):
    return tuple(
        message
        for severity, message in check_record.check(record_text, root, complete=True, spec=spec)
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
        return ("spec has no Acceptance criteria section",)
    if len(sections) > 1:
        return ("spec has %d Acceptance criteria sections" % len(sections),)
    return ()


def number_errors(criteria, sections):
    if len(sections) != 1:
        return ()
    section = sections[0][1]
    return tuple(
        "criterion %s is outside Acceptance criteria section %s; its number must start with '%s.'"
        % (criterion["number"], section, section)
        for criterion in criteria
        if not criterion["number"].startswith(section + ".")
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


def render(record_text, spec_text, spec_path, root, amendment=None):
    rejected = record_errors(record_text, root, spec_text.encode("utf-8"))
    if rejected:
        return (rejected, None, None)
    record = json.loads(record_text)
    steps = chosen_steps(record["steps"], amendment)
    lines = tuple(spec_text.splitlines(keepends=True))
    sections = check_spec.acceptance_sections(check_spec.numbered_headings(lines))
    errors = (
        task_errors(record["steps"])
        + section_errors(sections)
        + number_errors(record["criteria"], sections)
        + amendment_errors(steps, amendment)
    )
    if errors:
        return (errors, None, None)
    what = {environment["name"]: environment["what"] for environment in record["environments"]}
    facts = {fact["id"]: fact for fact in record["facts"]}
    criteria = {criterion["number"]: criterion for criterion in record["criteria"]}
    blocks = {number: criterion_block(criterion, what, facts) for number, criterion in criteria.items()}
    ordered = tuple(blocks[criterion["number"]] for criterion in record["criteria"])
    new_spec_text = replace_section(spec_text, lines, sections[0][0], ordered)
    source = {"path": spec_path, "sha256": hashlib.sha256(new_spec_text.encode("utf-8")).hexdigest()}
    items = [item(step, criteria, blocks, source) for step in steps]
    return ((), new_spec_text, items)


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
        pathlib.Path(path).write_bytes(data)
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
        texts[0][1], texts[1][1], os.path.abspath(spec_path), os.getcwd(), amendment
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
