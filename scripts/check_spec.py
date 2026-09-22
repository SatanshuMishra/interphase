import re
import sys

NUMBERED = re.compile(r"^## (\d+)\. (.+)$")
LEVEL_TWO = re.compile(r"^## ")
PLACEHOLDER = re.compile(r"\{\{")
MARKER = re.compile(r"\b(TBD|TODO|FIXME|XXX)\b")
VAGUE_WORDS = (
    "robust", "intuitive", "user-friendly", "seamless", "seamlessly", "fast",
    "quickly", "easy", "easily", "simple", "simply", "gracefully", "reasonable",
    "appropriate", "appropriately", "efficient", "efficiently", "scalable",
    "flexible", "clean", "nice", "better", "optimal",
)
VAGUE = re.compile(r"\b(" + "|".join(re.escape(word) for word in VAGUE_WORDS) + r")\b", re.IGNORECASE)
OPEN_QUESTIONS_LIMIT = 3
USAGE = "usage: check_spec.py --template TEMPLATE SPEC"


def numbered_headings(lines):
    return tuple(
        (number, line.rstrip())
        for number, line in enumerate(lines, start=1)
        if NUMBERED.match(line.rstrip())
    )


def level_two_lines(lines):
    return tuple(
        number for number, line in enumerate(lines, start=1) if LEVEL_TWO.match(line)
    )


def section_body(lines, start, boundaries):
    following = tuple(number for number in boundaries if number > start)
    end = following[0] if following else len(lines) + 1
    return tuple(lines[start:end - 1])


def missing_sections(template_headings, spec_headings):
    present = frozenset(heading for _, heading in spec_headings)
    return tuple(
        ("error", 0, "missing section: " + heading)
        for _, heading in template_headings
        if heading not in present
    )


def out_of_order(template_headings, spec_headings):
    positions = {heading: index for index, (_, heading) in enumerate(template_headings)}
    ranked = tuple(
        (number, heading, positions[heading])
        for number, heading in spec_headings
        if heading in positions
    )
    return tuple(
        ("error", current[0], "line {}: out of order: {} comes after {}".format(current[0], current[1], previous[1]))
        for previous, current in zip(ranked, ranked[1:])
        if current[2] <= previous[2]
    )


def unnumbered_headings(lines):
    return tuple(
        ("error", number, "line {}: unnumbered heading: {}".format(number, line.rstrip()))
        for number, line in enumerate(lines, start=1)
        if LEVEL_TWO.match(line) and not NUMBERED.match(line.rstrip())
    )


def placeholders(lines):
    return tuple(
        ("error", number, "line {}: placeholder left in spec".format(number))
        for number, line in enumerate(lines, start=1)
        if PLACEHOLDER.search(line)
    )


def unfinished_markers(lines):
    return tuple(
        ("error", number, "line {}: unfinished marker {}".format(number, match.group(1)))
        for number, line in enumerate(lines, start=1)
        for match in MARKER.finditer(line)
    )


def empty_sections(lines, spec_headings):
    boundaries = level_two_lines(lines)
    return tuple(
        ("error", number, "line {}: empty section: {}".format(number, heading))
        for number, heading in spec_headings
        if not any(line.strip() for line in section_body(lines, number, boundaries))
    )


def vague_words(lines):
    return tuple(
        ("warning", number, "line {}: vague word {}".format(number, match.group(1)))
        for number, line in enumerate(lines, start=1)
        for match in VAGUE.finditer(line)
    )


def heading_title(line):
    numbered = NUMBERED.match(line.rstrip())
    return numbered.group(2).strip() if numbered else line.rstrip()[3:].strip()


def open_questions(lines):
    boundaries = level_two_lines(lines)
    counts = tuple(
        (number, sum(1 for line in section_body(lines, number, boundaries) if line.startswith("- ")))
        for number in boundaries
        if heading_title(lines[number - 1]).lower() == "open questions"
    )
    return tuple(
        ("warning", number, "line {}: {} open questions, more than {}".format(number, count, OPEN_QUESTIONS_LIMIT))
        for number, count in counts
        if count > OPEN_QUESTIONS_LIMIT
    )


def check(template_text, spec_text):
    template_lines = tuple(template_text.splitlines())
    spec_lines = tuple(spec_text.splitlines())
    template_headings = numbered_headings(template_lines)
    spec_headings = numbered_headings(spec_lines)
    return (
        missing_sections(template_headings, spec_headings)
        + out_of_order(template_headings, spec_headings)
        + unnumbered_headings(spec_lines)
        + placeholders(spec_lines)
        + unfinished_markers(spec_lines)
        + empty_sections(spec_lines, spec_headings)
        + vague_words(spec_lines)
        + open_questions(spec_lines)
    )


def parse_arguments(argv):
    if len(argv) != 3:
        return None
    if argv[0] == "--template":
        return argv[1], argv[2]
    if argv[1] == "--template":
        return argv[2], argv[0]
    return None


def read_text(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


def main(argv):
    arguments = parse_arguments(argv)
    if arguments is None:
        print(USAGE, file=sys.stderr)
        return 2
    template_path, spec_path = arguments
    texts = tuple((path, read_text(path)) for path in (template_path, spec_path))
    unreadable = tuple(path for path, text in texts if text is None)
    if unreadable:
        print("cannot read: " + ", ".join(unreadable), file=sys.stderr)
        return 2
    findings = check(texts[0][1], texts[1][1])
    for severity, _, message in findings:
        print("{}: {}".format(severity, message))
    return 1 if any(severity == "error" for severity, _, _ in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
