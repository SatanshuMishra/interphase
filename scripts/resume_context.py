import contextlib
import json
import os
import pathlib
import sys

RECORD_SUFFIX = ".record.json"
DECISIONS_SUFFIX = ".decisions.md"
IN_PROGRESS = "in-progress"
HEADING = "interphase run in progress: {}"
IGNORE_UNLESS = (
    "Ignore this unless this conversation is continuing that interphase run. "
    "If it is, re-read {} and {} and {} before acting."
)


def is_folder(path):
    try:
        return path.is_dir()
    except (OSError, ValueError):
        return False


def spec_folders(start):
    origin = pathlib.Path(start).resolve()
    if not is_folder(origin):
        return ()
    return tuple(
        folder
        for folder in (base / "docs" / "specs" for base in (origin,) + tuple(origin.parents))
        if is_folder(folder)
    )


def slugs(spec_folder):
    try:
        names = tuple(entry.name for entry in spec_folder.iterdir())
    except OSError:
        return ()
    return tuple(sorted(
        name[:-len(RECORD_SUFFIX)]
        for name in names
        if name.endswith(RECORD_SUFFIX) and len(name) > len(RECORD_SUFFIX)
    ))


def read_file(path):
    try:
        return "text", path.read_bytes().decode("utf-8")
    except FileNotFoundError:
        return "missing", ""
    except (OSError, UnicodeDecodeError) as error:
        return "unreadable", str(error)


def parse_record(outcome):
    kind, value = outcome
    if kind != "text":
        return outcome
    try:
        record = json.loads(value)
    except ValueError as error:
        return "unreadable", str(error)
    if not isinstance(record, dict):
        return "unreadable", "not a JSON object"
    return "record", record


def in_progress(outcome):
    kind, value = outcome
    return kind == "unreadable" or (kind == "record" and value.get("status") == IN_PROGRESS)


def text_of(value):
    return "" if value is None else str(value)


def entries(value):
    return tuple(value) if isinstance(value, list) else ()


def joined(value):
    return ", ".join(text_of(item) for item in entries(value))


def criterion_line(criterion):
    reason = text_of(criterion.get("unproven"))
    return "- {} {} (where: {}){}".format(
        text_of(criterion.get("number")),
        text_of(criterion.get("title")),
        joined(criterion.get("where")),
        " Unproven: " + reason if reason else "",
    )


def step_line(step):
    return "- {}: files {}; criteria {}".format(
        text_of(step.get("name")),
        joined(step.get("files")),
        joined(step.get("criteria")),
    )


def objects(value):
    return tuple(entry for entry in entries(value) if isinstance(entry, dict))


def digest_lines(outcome):
    kind, value = outcome
    if kind == "missing":
        return ("No record yet.",)
    if kind == "unreadable":
        return ("The record could not be read: " + value,)
    return (
        ("Criteria:",)
        + tuple(criterion_line(criterion) for criterion in objects(value.get("criteria")))
        + ("Steps:",)
        + tuple(step_line(step) for step in objects(value.get("steps")))
    )


def decisions_text(outcome):
    kind, value = outcome
    if kind == "missing":
        return "No decisions file yet.\n"
    if kind == "unreadable":
        return "The decisions file could not be read: {}\n".format(value)
    return value if value == "" or value.endswith("\n") else value + "\n"


def block(spec_folder, slug, record, phases_path):
    record_path = spec_folder / (slug + RECORD_SUFFIX)
    decisions_path = spec_folder / (slug + DECISIONS_SUFFIX)
    return "".join((
        HEADING.format(slug) + "\n",
        IGNORE_UNLESS.format(record_path, decisions_path, phases_path) + "\n",
        "\n",
        "Decisions ({}):\n".format(decisions_path),
        decisions_text(read_file(decisions_path)),
        "\n",
        "Record digest ({}):\n".format(record_path),
        "\n".join(digest_lines(record)),
    ))


def blocks(spec_folder, phases_path):
    records = tuple(
        (slug, parse_record(read_file(spec_folder / (slug + RECORD_SUFFIX))))
        for slug in slugs(spec_folder)
    )
    return tuple(
        block(spec_folder, slug, record, phases_path)
        for slug, record in records
        if in_progress(record)
    )


def standard_input():
    try:
        return "" if sys.stdin is None else sys.stdin.read()
    except (OSError, ValueError):
        return ""


def start_folder(stdin_text):
    try:
        payload = json.loads(stdin_text)
    except ValueError:
        return os.getcwd()
    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    return cwd if isinstance(cwd, str) and cwd else os.getcwd()


def report(stdin_text):
    text = standard_input() if stdin_text is None else stdin_text
    phases_path = str(pathlib.Path(__file__).resolve().parents[1] / "core" / "phases.md")
    found = tuple(
        text_block
        for folder in spec_folders(start_folder(text))
        for text_block in blocks(folder, phases_path)
    )
    if found:
        print("\n\n".join(found))


def main(stdin_text=None):
    with contextlib.suppress(Exception):
        report(stdin_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
