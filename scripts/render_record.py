import hashlib
import importlib.util
import json
import os
import pathlib
import sys

USAGE = "usage: python3 render_record.py --record RECORD --spec SPEC --items ITEMS"
OPTIONS = ("--items", "--record", "--spec")
PROVES = "Acceptance criteria this Step proves:"
CARRIED = ("after", "contract_group", "type", "complexity", "file_notes", "msp")


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_record = load_sibling("check_record")
check_spec = load_sibling("check_spec")


def criterion_block(criterion, what):
    where = "Where passing proves it: %s." % "; ".join(what[name] for name in criterion["where"])
    tests = tuple(
        "- `%s` `%s`: %s Runs in: %s." % (test["file"], test["name"], test["asserts"], what[test["env"]])
        for test in criterion["tests"]
    )
    unproven = ("Unproven: " + criterion["unproven"],) if "unproven" in criterion else ()
    parts = (
        ("### %s %s" % (criterion["number"], criterion["title"]), criterion["text"], where)
        + (("\n".join(tests),) if tests else ())
        + unproven
    )
    return "\n\n".join(parts)


def record_errors(record_text, root):
    return tuple(
        message
        for severity, message in check_record.check(record_text, root, complete=True)
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


def render(record_text, spec_text, spec_path, root):
    rejected = record_errors(record_text, root)
    if rejected:
        return (rejected, None, None)
    record = json.loads(record_text)
    lines = tuple(spec_text.splitlines(keepends=True))
    sections = check_spec.acceptance_sections(check_spec.numbered_headings(lines))
    errors = task_errors(record["steps"]) + section_errors(sections) + number_errors(record["criteria"], sections)
    if errors:
        return (errors, None, None)
    what = {environment["name"]: environment["what"] for environment in record["environments"]}
    criteria = {criterion["number"]: criterion for criterion in record["criteria"]}
    blocks = {number: criterion_block(criterion, what) for number, criterion in criteria.items()}
    ordered = tuple(blocks[criterion["number"]] for criterion in record["criteria"])
    new_spec_text = replace_section(spec_text, lines, sections[0][0], ordered)
    source = {"path": spec_path, "sha256": hashlib.sha256(new_spec_text.encode("utf-8")).hexdigest()}
    items = [item(step, criteria, blocks, source) for step in record["steps"]]
    return ((), new_spec_text, items)


def parse_arguments(argv):
    pairs = tuple(zip(argv[0::2], argv[1::2]))
    if len(argv) != 6 or tuple(sorted(option for option, _ in pairs)) != OPTIONS:
        return None
    if any(value in OPTIONS for _, value in pairs):
        return None
    values = dict(pairs)
    return values["--record"], values["--spec"], values["--items"]


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
    record_path, spec_path, items_path = arguments
    texts = tuple((path, read_text(path)) for path in (record_path, spec_path))
    unreadable = tuple(path for path, text in texts if text is None)
    if unreadable:
        print("\n".join("cannot read: " + path for path in unreadable), file=sys.stderr)
        return 2
    errors, spec_text, items = render(texts[0][1], texts[1][1], os.path.abspath(spec_path), os.getcwd())
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
