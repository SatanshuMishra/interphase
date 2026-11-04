import importlib.util
import json
import pathlib
import sys

USAGE = "usage: python3 read_back.py --record RECORD"
HEADING = "How we will know it works"
SURFACES_HEADING = "Surfaces that could not be driven"


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


owned_names = load_sibling("owned_names")
render_record = load_sibling("render_record")
check_record = render_record.check_record
record_seams = check_record.record_seams
owned_formats = check_record.owned_formats


def refusals(path, record):
    return tuple(
        owned_names.mismatch(owned_names.written_by_interphase(path), owned_names.H11, message)
        for message in owned_formats.errors(owned_names.H11, record)
    )


def line_rows(criterion):
    return tuple("- " + render_record.line_sentence(line) for line in check_record.criterion_lines(criterion))


def criterion_rows(criterion):
    return ("%s %s" % (criterion["number"], render_record.one_line(criterion["title"])),) + line_rows(criterion)


def seam_rows(seam, criteria):
    head = "Seam %s: %s." % (seam["name"], render_record.clause(seam["interface"]))
    return (head,) + tuple(
        row for criterion in criteria if criterion["seam"] == seam["name"] for row in criterion_rows(criterion)
    )


def question(entry, criterion):
    return (
        "- %s needs %s for %s, which failed: %s. "
        "Fix the surface and probe again, or move criterion %s to a seam the builder cannot run?"
        % (
            entry["check"],
            entry["probe"],
            entry["target"],
            render_record.clause(entry["detail"]),
            criterion["number"],
        )
    )


def questions(record, criteria):
    builders = record_seams.builder_seams(tuple(record["seams"]))
    owners = {
        line["id"]: criterion
        for criterion in criteria
        for line in check_record.criterion_lines(criterion)
    }
    return tuple(
        question(entry, owners[entry["check"]])
        for entry in check_record.stored_probes(record).values()
        if entry["check"] in owners and record_seams.is_blocking(owners[entry["check"]], entry["status"], builders)
    )


def read_back(record):
    seams = tuple(record["seams"])
    criteria = tuple(record["criteria"])
    blocks = tuple("\n".join(seam_rows(seam, criteria)) for seam in seams)
    asked = questions(record, criteria)
    surfaces = ("\n".join((SURFACES_HEADING,) + asked),) if asked else ()
    return "\n\n".join((HEADING,) + blocks + surfaces)


def parse_arguments(argv):
    if len(argv) != 2 or argv[0] != "--record" or argv[1].startswith("-"):
        return None
    return argv[1]


def load_record(text):
    try:
        record = json.loads(text)
    except (ValueError, RecursionError):
        return (None, "record is not a JSON object")
    if not isinstance(record, dict):
        return (None, "record is not a JSON object")
    if not check_record.check_items.is_unicode(record):
        return (None, check_record.NOT_UNICODE)
    return (record, None)


def main(argv):
    path = parse_arguments(argv)
    if path is None:
        print(USAGE, file=sys.stderr)
        return 2
    text = render_record.read_text(path)
    if text is None:
        print("cannot read: " + path, file=sys.stderr)
        return 2
    record, problem = load_record(text)
    if record is None:
        print("%s: %s" % (problem, path), file=sys.stderr)
        return 2
    refused = refusals(path, record)
    if refused:
        print("\n".join(refused), file=sys.stderr)
        return 1
    print(read_back(record))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
