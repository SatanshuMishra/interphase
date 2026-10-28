import importlib.util
import json
import pathlib
import re
import sys

USAGE = "usage: python3 check_record.py [--complete] RECORD"
COMPLETE = "--complete"
RECORD_KEYS = ("seams", "criteria", "steps")
STOPPED = "stopped"
STATUSES = ("in-progress", "handed-off", STOPPED)
OPTIONAL_RECORD_KEYS = ("status", "rounds", "locked", "probes", "stop", "outcomes")
SEAM_KEYS = ("name", "interface", "catches", "misses", "builder_runs")
CRITERION_KEYS = (
    "number",
    "title",
    "text",
    "seam",
    "tests",
    "unproven",
    "varies",
    "case_table",
    "domains",
    "acceptance",
)
CRITERION_REQUIRED = ("number", "title", "text", "seam", "tests")
CASE_TABLES = ("security", "refusal")
DOMAIN_KEYS = ("name", "over", "classes")
TEST_KEYS = ("file", "name", "given", "expect", "step")
COVERS = "covers"
CHECK = "check"
VARIES = ("input", "output", "measured")
POPULATION_KEYS = ("cases", "runs", "pass_rate")
STEP_KEYS = (
    "name",
    "files",
    "criteria",
    "task",
    "after",
    "contract_group",
    "type",
    "complexity",
    "file_notes",
    "msp",
    "assumptions",
    "amendment",
)
STEP_REQUIRED = ("name", "files", "criteria")
RESERVED_STEP = "check-author"
RENDERED_KEYS = ("source", "acceptance", "spec_ref")
NUMBER_RE = re.compile(r"[0-9]+\.[0-9]+")
ROUND_KEYS = ("kind", "questions", "changed")
ROUND_KINDS = ("intent", "frontier")
PROBE_KEYS = ("check", "probe", "target", "status", "detail")
PROBE_STATUSES = ("pass", "fail")
STOP_KEYS = ("phase", "reason")
OUTCOME_KEYS = ("store", "entries", "repeated")
REPEATED_KEYS = ("kind", "count")


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_items = load_sibling("check_items")
schema_check = load_sibling("schema_check")
surface_probe = load_sibling("surface_probe")
K1 = schema_check.load("k1-acceptance")
K2_LOCKED = schema_check.subschema(schema_check.load("k2-locked"), "/properties/locked")
ITEM_STEP_CHECKS = (
    check_items.check_name,
    check_items.check_files,
    check_items.check_after_shape,
    check_items.check_type,
    check_items.check_complexity,
    check_items.check_file_notes,
    check_items.check_labels,
    check_items.check_assumptions,
)


def error(message):
    return ("error", message)


def warning(message):
    return ("warning", message)


def missing(message, complete):
    return error(message) if complete else warning(message)


def from_items(findings):
    return tuple((severity, message) for severity, _, message in findings)


def is_count(value, least):
    return isinstance(value, int) and not isinstance(value, bool) and value >= least


def is_rate(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 < value <= 1


def duplicated(values):
    return tuple(sorted(frozenset(value for value in values if values.count(value) > 1)))


def unique(values):
    return tuple(value for position, value in enumerate(values) if value not in values[:position])


def part(record, key):
    value = record.get(key)
    return tuple(value) if isinstance(value, list) else ()


def unknown_keys(who, item, allowed):
    return tuple(error("%s has unknown key %r" % (who, key)) for key in sorted(item) if key not in allowed)


def missing_keys(who, item, required):
    return tuple(error("%s lacks required key %r" % (who, key)) for key in required if key not in item)


def text_fields(who, item, keys):
    return tuple(
        error("%s has %s that is not a non-empty string" % (who, key))
        for key in keys
        if key in item and not check_items.is_text(item[key])
    )


def check_shape(record):
    unknown = tuple(
        error("record has unknown key %r" % key)
        for key in sorted(record)
        if key not in RECORD_KEYS + OPTIONAL_RECORD_KEYS
    )
    absent = tuple(error("record lacks key %r" % key) for key in RECORD_KEYS if key not in record)
    not_lists = tuple(
        error("record key %r is not a list" % key)
        for key in RECORD_KEYS
        if key in record and not isinstance(record[key], list)
    )
    return unknown + absent + not_lists + check_status(record)


def check_status(record):
    if "status" not in record:
        return (error("record lacks key 'status'"),)
    if record["status"] in STATUSES and isinstance(record["status"], str):
        return ()
    return (error("record status %r is not %s" % (record["status"], " or ".join(repr(value) for value in STATUSES))),)


def check_missing_parts(record, complete):
    return tuple(missing("record has no %s" % key, complete) for key in RECORD_KEYS if record.get(key) == [])


def named_label(kind, index, entry, key="name"):
    name = entry.get(key) if isinstance(entry, dict) else None
    return "%s %r" % (kind, name) if check_items.is_text(name) else "%s %d" % (kind, index + 1)


def check_kebab_name(who, entry):
    if "name" not in entry:
        return ()
    name = entry["name"]
    if isinstance(name, str) and check_items.NAME_RE.match(name):
        return ()
    return (error("%s has a name that is not lowercase kebab-case" % who),)


def check_builder_runs(who, seam):
    if "builder_runs" in seam and not isinstance(seam["builder_runs"], bool):
        return (error("%s has builder_runs that is not true or false" % who),)
    return ()


def check_seam(index, seam):
    who = named_label("seam", index, seam)
    if not isinstance(seam, dict):
        return (error("%s is not an object" % who),)
    return (
        unknown_keys(who, seam, SEAM_KEYS)
        + missing_keys(who, seam, SEAM_KEYS)
        + check_kebab_name(who, seam)
        + text_fields(who, seam, ("interface", "catches", "misses"))
        + check_builder_runs(who, seam)
    )


def seam_names(seams):
    return tuple(seam["name"] for seam in seams if isinstance(seam, dict) and check_items.is_text(seam.get("name")))


def builder_seams(seams):
    return frozenset(
        seam["name"]
        for seam in seams
        if isinstance(seam, dict) and check_items.is_text(seam.get("name")) and seam.get("builder_runs") is True
    )


def check_seams(seams, criteria, complete):
    per_seam = tuple(finding for index, seam in enumerate(seams) for finding in check_seam(index, seam))
    repeated = tuple(error("seam name %r is duplicated" % name) for name in duplicated(seam_names(seams)))
    used = frozenset(criterion["seam"] for criterion in criteria if isinstance(criterion, dict) and check_items.is_text(criterion.get("seam")))
    idle = tuple(
        missing("seam %r is used by no criterion" % name, complete)
        for name in unique(seam_names(seams))
        if name not in used
    )
    return per_seam + repeated + idle


def step_criteria(step):
    claims = step.get("criteria")
    return tuple(claims) if check_items.is_text_list(claims) else ()


def steps_by_name(steps):
    return {
        step["name"]: step for step in steps if isinstance(step, dict) and isinstance(step.get("name"), str)
    }


def criterion_label(index, criterion):
    number = criterion.get("number") if isinstance(criterion, dict) else None
    return "criterion %s" % number if check_items.is_text(number) else "criterion %d" % (index + 1)


def criterion_numbers(criteria):
    return tuple(
        criterion["number"]
        for criterion in criteria
        if isinstance(criterion, dict) and check_items.is_text(criterion.get("number"))
    )


def check_number(who, criterion):
    if "number" not in criterion:
        return ()
    number = criterion["number"]
    if isinstance(number, str) and NUMBER_RE.fullmatch(number):
        return ()
    return (error("%s has a number that is not digits, one dot and digits, such as 5.3" % who),)


def check_seam_name(who, criterion, known):
    if "seam" not in criterion or not check_items.is_text(criterion["seam"]):
        return ()
    if criterion["seam"] in known:
        return ()
    return (error("%s names unknown seam %r" % (who, criterion["seam"])),)


def well_formed(test):
    return isinstance(test, dict) and all(check_items.is_text(test.get(key)) for key in TEST_KEYS)


def entry_label(who, position, test):
    name = test.get("name") if isinstance(test, dict) else None
    return "%s test %r" % (who, name) if check_items.is_text(name) else "%s test %d" % (who, position + 1)


def check_built_file(tag, test, step):
    if test["file"] in check_items.step_files(step):
        return ()
    return (error("%s has file %r, which is not in the files of step %r" % (tag, test["file"], test["step"])),)


def check_locked_file(tag, test, step, locked):
    listed = (
        (error("%s has file %s, which step %r lists in its files" % (tag, test["file"], test["step"])),)
        if test["file"] in check_items.step_files(step)
        else ()
    )
    unlocked = (
        (error("%s has file %s, which is not in the record's locked list" % (tag, test["file"])),)
        if locked is not None and test["file"] not in locked
        else ()
    )
    return listed + unlocked


def check_test_step(tag, test, criterion, by_name, locked):
    step = by_name.get(test["step"])
    if step is None:
        return (error("%s names unknown step %r" % (tag, test["step"])),)
    number = criterion.get("number")
    outside = (
        check_locked_file(tag, test, step, locked) if has_lines(criterion) else check_built_file(tag, test, step)
    )
    unclaimed = (
        ()
        if not check_items.is_text(number) or number in step_criteria(step)
        else (
            error(
                "%s names step %r, which does not list criterion %s in its criteria" % (tag, test["step"], number)
            ),
        )
    )
    return outside + unclaimed


def check_population(who, position, test):
    tag = "%s test %d" % (who, position + 1)
    counts = tuple(
        error("%s has %s that is not an integer of at least %d" % (tag, key, least))
        for key, least in (("cases", 1), ("runs", 2))
        if key in test and not is_count(test[key], least)
    )
    rate = (
        (error("%s has pass_rate that is not a number above 0 and at most 1" % tag),)
        if "pass_rate" in test and not is_rate(test["pass_rate"])
        else ()
    )
    return missing_keys(tag, test, POPULATION_KEYS) + counts + rate


def criterion_domains(criterion):
    domains = criterion.get("domains")
    if not isinstance(domains, list):
        return ()
    return tuple(domain for domain in domains if isinstance(domain, dict) and check_items.is_text(domain.get("name")))


def domain_classes(domain):
    classes = domain.get("classes")
    return tuple(name for name in classes if check_items.is_text(name)) if isinstance(classes, list) else ()


def class_pairs(criterion):
    return unique(
        tuple((domain["name"], name) for domain in criterion_domains(criterion) for name in domain_classes(domain))
    )


def check_cover(tag, entry, criterion):
    head, separator, tail = entry.partition(": ")
    if not separator:
        return (error("%s covers %r, which is not '<domain>: <class>'" % (tag, entry)),)
    if head not in frozenset(domain["name"] for domain in criterion_domains(criterion)):
        return (error("%s covers unknown domain %r" % (tag, head)),)
    if (head, tail) not in class_pairs(criterion):
        return (error("%s covers unknown class %r of domain %r" % (tag, tail, head)),)
    return ()


def check_covers(tag, test, criterion):
    if COVERS not in test:
        return ()
    covers = test[COVERS]
    if not isinstance(covers, list) or not covers or not all(check_items.is_text(entry) for entry in covers):
        return (error("%s has covers that is not a non-empty list of non-empty strings" % tag),)
    return tuple(finding for entry in covers for finding in check_cover(tag, entry, criterion))


def check_check(tag, test, criterion, complete):
    if not has_lines(criterion):
        return ()
    if CHECK not in test:
        return (missing("%s names no acceptance line in check" % tag, complete),)
    if test[CHECK] in line_ids(criterion):
        return ()
    return (error("%s names unknown acceptance line %s" % (tag, test[CHECK])),)


def check_test(who, position, test, criterion, by_name, locked, complete):
    tag = entry_label(who, position, test)
    if not well_formed(test):
        return (error("%s is not an object with non-empty string file, name, given, expect and step" % tag),)
    varying = "varies" in criterion
    tabled = "case_table" in criterion
    allowed = (
        TEST_KEYS
        + ((COVERS,) if tabled else ())
        + (POPULATION_KEYS if varying else ())
        + ((CHECK,) if has_lines(criterion) else ())
    )
    population = check_population(who, position, test) if varying else ()
    return (
        unknown_keys(tag, test, allowed)
        + check_covers(tag, test, criterion)
        + check_check(tag, test, criterion, complete)
        + population
        + check_test_step(tag, test, criterion, by_name, locked)
    )


def check_tests(who, criterion, by_name, locked, complete):
    if "tests" not in criterion:
        return ()
    tests = criterion["tests"]
    if not isinstance(tests, list):
        return (error("%s has tests that is not a list" % who),)
    return tuple(
        finding
        for position, test in enumerate(tests)
        for finding in check_test(who, position, test, criterion, by_name, locked, complete)
    )


def criterion_lines(criterion):
    lines = criterion.get("acceptance") if isinstance(criterion, dict) else None
    return tuple(lines) if isinstance(lines, list) else ()


def has_lines(criterion):
    return bool(criterion_lines(criterion))


def line_ids(criterion):
    return tuple(
        line["id"]
        for line in criterion_lines(criterion)
        if isinstance(line, dict) and check_items.is_text(line.get("id"))
    )


def check_line_id(who, criterion, position, line):
    number = criterion.get("number")
    if not isinstance(line, dict) or not check_items.is_text(line.get("id")):
        return ()
    if not isinstance(number, str) or not NUMBER_RE.fullmatch(number):
        return ()
    expected = "C%s.%d" % (number.partition(".")[2], position)
    if line["id"] == expected:
        return ()
    return (error("%s acceptance line %d has id %s; expected %s" % (who, position, line["id"], expected)),)


def check_line(who, criterion, position, line):
    shape = tuple(
        error("%s acceptance line %d does not match K1: %s" % (who, position, message))
        for message in schema_check.errors(K1, line)
    )
    return shape + check_line_id(who, criterion, position, line)


def check_acceptance(who, criterion):
    if "acceptance" not in criterion:
        return ()
    if not has_lines(criterion):
        return (error("%s has acceptance that is not a non-empty list of K1 lines" % who),)
    return tuple(
        finding
        for position, line in enumerate(criterion_lines(criterion), 1)
        for finding in check_line(who, criterion, position, line)
    )


def check_implemented(who, criterion, complete):
    if "unproven" in criterion:
        return ()
    named = frozenset(test.get(CHECK) for test in criterion_tests(criterion))
    return tuple(
        missing("%s acceptance line %s is implemented by no test" % (who, line_id), complete)
        for line_id in unique(line_ids(criterion))
        if line_id not in named
    )


def domain_label(who, position, domain):
    name = domain.get("name") if isinstance(domain, dict) else None
    return "%s domain %r" % (who, name) if check_items.is_text(name) else "%s domain %d" % (who, position + 1)


def check_classes(who, domain):
    if "classes" not in domain:
        return ()
    classes = domain["classes"]
    if not isinstance(classes, list) or len(classes) < 2 or not all(check_items.is_text(name) for name in classes):
        return (error("%s has classes that is not a list of at least two non-empty strings" % who),)
    return tuple(error("%s lists class %r more than once" % (who, name)) for name in duplicated(tuple(classes)))


def check_domain(who, position, domain):
    tag = domain_label(who, position, domain)
    if not isinstance(domain, dict):
        return (error("%s is not an object" % tag),)
    return (
        unknown_keys(tag, domain, DOMAIN_KEYS)
        + missing_keys(tag, domain, DOMAIN_KEYS)
        + check_kebab_name(tag, domain)
        + text_fields(tag, domain, ("over",))
        + check_classes(tag, domain)
    )


def domain_names(domains):
    return tuple(
        domain["name"] for domain in domains if isinstance(domain, dict) and check_items.is_text(domain.get("name"))
    )


def check_case_table(who, criterion):
    tabled = "case_table" in criterion
    if tabled and criterion["case_table"] not in CASE_TABLES:
        return (
            error(
                "%s has case_table %r, which is not %s"
                % (who, criterion["case_table"], " or ".join(repr(kind) for kind in CASE_TABLES))
            ),
        )
    if tabled and "domains" not in criterion:
        return (error("%s has case_table but no domains" % who),)
    if "domains" in criterion and not tabled:
        return (
            error("%s has domains but no case_table; a case table is only for security or refusal behaviour" % who),
        )
    return ()


def check_domains(who, criterion):
    if "domains" not in criterion:
        return ()
    domains = criterion["domains"]
    if not isinstance(domains, list) or not domains:
        return (error("%s has domains that is not a non-empty list" % who),)
    per_domain = tuple(
        finding for position, domain in enumerate(domains) for finding in check_domain(who, position, domain)
    )
    repeated = tuple(
        error("%s domain name %r is duplicated" % (who, name)) for name in duplicated(domain_names(domains))
    )
    return per_domain + repeated


def criterion_tests(criterion):
    tests = criterion.get("tests")
    return tuple(test for test in tests if well_formed(test)) if isinstance(tests, list) else ()


def covered(criterion):
    return frozenset(
        tuple(entry.partition(": ")[0::2])
        for test in criterion_tests(criterion)
        for entry in (test.get(COVERS) if isinstance(test.get(COVERS), list) else ())
        if isinstance(entry, str) and ": " in entry
    )


def check_coverage(who, criterion, complete):
    if "unproven" in criterion:
        return ()
    done = covered(criterion)
    return tuple(
        missing("%s has no test covering class %r of domain %r" % (who, name, domain), complete)
        for domain, name in class_pairs(criterion)
        if (domain, name) not in done
    )


def check_varies(who, criterion):
    if "varies" not in criterion:
        return ()
    varies = criterion["varies"]
    if isinstance(varies, str) and varies in VARIES:
        return ()
    return (error("%s has varies %r, which is not %s" % (who, varies, " or ".join(repr(kind) for kind in VARIES))),)


def check_proof(who, criterion, builders, complete):
    runnable = check_items.is_text(criterion.get("seam")) and criterion["seam"] in builders
    tests = criterion_tests(criterion)
    unproven = "unproven" in criterion
    if not runnable:
        if unproven:
            return ()
        return (missing("%s sits at a seam the builder cannot run and is not marked unproven" % who, complete),)
    tested = (
        (
            error(
                "%s is marked unproven but has tests at a seam the builder runs: %s"
                % (who, ", ".join(test["name"] for test in tests))
            ),
        )
        if unproven and tests
        else ()
    )
    unlined = (
        ()
        if has_lines(criterion)
        else (missing("%s sits at a seam the builder runs and has no acceptance line" % who, complete),)
    )
    return tested + unlined


def check_criterion(index, criterion, known, builders, by_name, locked, complete):
    who = criterion_label(index, criterion)
    if not isinstance(criterion, dict):
        return (error("%s is not an object" % who),)
    return (
        unknown_keys(who, criterion, CRITERION_KEYS)
        + missing_keys(who, criterion, CRITERION_REQUIRED)
        + check_number(who, criterion)
        + text_fields(who, criterion, ("title", "text", "seam", "unproven"))
        + check_seam_name(who, criterion, known)
        + check_varies(who, criterion)
        + check_case_table(who, criterion)
        + check_domains(who, criterion)
        + check_acceptance(who, criterion)
        + check_tests(who, criterion, by_name, locked, complete)
        + check_implemented(who, criterion, complete)
        + check_proof(who, criterion, builders, complete)
        + check_coverage(who, criterion, complete)
    )


def check_criteria(criteria, seams, steps, locked, complete):
    known = frozenset(seam_names(seams))
    builders = builder_seams(seams)
    by_name = steps_by_name(steps)
    per_criterion = tuple(
        finding
        for index, criterion in enumerate(criteria)
        for finding in check_criterion(index, criterion, known, builders, by_name, locked, complete)
    )
    numbers = criterion_numbers(criteria)
    repeated = tuple(error("criterion number %s is duplicated" % number) for number in duplicated(numbers))
    ids = tuple(line_id for criterion in criteria for line_id in line_ids(criterion))
    shared = tuple(error("acceptance line id %s is duplicated" % line_id) for line_id in duplicated(ids))
    claimed = frozenset(number for step in steps if isinstance(step, dict) for number in step_criteria(step))
    unclaimed = tuple(
        missing("criterion %s is claimed by no step" % number, complete)
        for number in unique(numbers)
        if number not in claimed
    )
    return per_criterion + repeated + shared + unclaimed


def check_step_keys(who, step):
    return tuple(
        error("%s holds %r, which the render script fills" % (who, key))
        if key in RENDERED_KEYS
        else error("%s has unknown key %r" % (who, key))
        for key in sorted(step)
        if key not in STEP_KEYS
    )


def check_reserved_name(step):
    if step.get("name") != RESERVED_STEP:
        return ()
    return (error("step name %r is reserved for the rendered %s Step" % (RESERVED_STEP, RESERVED_STEP)),)


def check_step_criteria(who, step, numbers):
    if "criteria" not in step:
        return ()
    claims = step["criteria"]
    if not isinstance(claims, list) or not claims or not all(isinstance(claim, str) for claim in claims):
        return (error("%s has criteria that is not a non-empty list of strings" % who),)
    unknown = tuple(
        error("%s claims unknown criterion %r" % (who, claim)) for claim in claims if claim not in numbers
    )
    repeated = tuple(
        error("%s lists criterion %r more than once" % (who, claim)) for claim in duplicated(tuple(claims))
    )
    return unknown + repeated


def check_step_task(who, step):
    if "task" in step and not isinstance(step["task"], str):
        return (error("%s has a task that is not a string" % who),)
    return ()


def check_amendment(who, step):
    if "amendment" in step and not is_count(step["amendment"], 1):
        return (error("%s has amendment that is not an integer of at least 1" % who),)
    return ()


def check_step(index, step, numbers):
    who = check_items.label(index, step)
    if not isinstance(step, dict):
        return (error("%s is not an object" % who),)
    return (
        check_step_keys(who, step)
        + missing_keys(who, step, STEP_REQUIRED)
        + check_reserved_name(step)
        + check_step_criteria(who, step, numbers)
        + check_step_task(who, step)
        + check_amendment(who, step)
        + tuple(finding for rule in ITEM_STEP_CHECKS for finding in from_items(rule(who, step)))
    )


def check_steps(steps, criteria):
    numbers = frozenset(criterion_numbers(criteria))
    per_step = tuple(finding for index, step in enumerate(steps) for finding in check_step(index, step, numbers))
    graph = check_items.after_graph(steps)
    shared = (
        check_items.check_duplicates(steps)
        + check_items.check_after_names(steps)
        + check_items.check_cycles(graph)
        + check_items.check_contracts(steps, graph)
        + check_items.check_hazards(steps, graph)
    )
    return per_step + from_items(shared)


def check_round_kind(who, entry):
    if "kind" not in entry or entry["kind"] in ROUND_KINDS and isinstance(entry["kind"], str):
        return ()
    return (error("%s has kind that is not %s" % (who, " or ".join(repr(kind) for kind in ROUND_KINDS))),)


def check_round_counts(who, entry):
    questions = entry.get("questions")
    asked = (
        ()
        if "questions" not in entry or is_count(questions, 1)
        else (error("%s has questions that is not a whole number of at least one" % who),)
    )
    ceiling = questions if is_count(questions, 1) else None
    changed = entry.get("changed")
    valid = is_count(changed, 0) and (ceiling is None or changed <= ceiling)
    answered = (
        ()
        if "changed" not in entry or valid
        else (error("%s has changed that is not a whole number from zero to its questions" % who),)
    )
    return asked + answered


def check_round(index, entry):
    who = "round %d" % (index + 1)
    if not isinstance(entry, dict):
        return (error("%s is not an object" % who),)
    return (
        unknown_keys(who, entry, ROUND_KEYS)
        + missing_keys(who, entry, ROUND_KEYS)
        + check_round_kind(who, entry)
        + check_round_counts(who, entry)
    )


def check_rounds(record):
    if "rounds" not in record:
        return ()
    rounds = record["rounds"]
    if not isinstance(rounds, list):
        return (error("record key 'rounds' is not a list"),)
    return tuple(finding for index, entry in enumerate(rounds) for finding in check_round(index, entry))


def record_locked(record):
    if "locked" not in record:
        return None
    paths = record["locked"]
    return frozenset(path for path in paths if isinstance(path, str)) if isinstance(paths, list) else frozenset()


def check_locked(record, criteria, steps, complete):
    if "locked" in record:
        shape = tuple(
            error("record locked does not match K2: %s" % message)
            for message in schema_check.errors(K2_LOCKED, record["locked"])
        )
    elif any(has_lines(criterion) for criterion in criteria):
        shape = (missing("record has no locked list, but criteria have acceptance lines", complete),)
    else:
        shape = ()
    locked = record_locked(record) or frozenset()
    written = tuple(
        error("%s lists locked path %s" % (check_items.label(index, step), path))
        for index, step in enumerate(steps)
        if isinstance(step, dict)
        for path in sorted(check_items.step_files(step) & locked)
    )
    return shape + written


def is_entry(entry, keys):
    return isinstance(entry, dict) and sorted(entry) == sorted(keys)


def check_probe(index, entry):
    who = "record probes entry %d" % (index + 1)
    if not is_entry(entry, PROBE_KEYS) or not all(check_items.is_text(entry[key]) for key in PROBE_KEYS):
        return (error("%s is not an object with exactly non-empty string %s" % (who, ", ".join(PROBE_KEYS))),)
    if entry["status"] in PROBE_STATUSES:
        return ()
    return (error("%s has status %r, which is not 'pass' or 'fail'" % (who, entry["status"])),)


def check_probes(record):
    if "probes" not in record:
        return ()
    probes = record["probes"]
    if not isinstance(probes, list):
        return (error("record probes is not a list"),)
    return tuple(finding for index, entry in enumerate(probes) for finding in check_probe(index, entry))


def stored_probes(record):
    probes = record.get("probes")
    return {
        (entry["check"], entry["probe"], entry["target"]): entry
        for entry in (probes if isinstance(probes, list) else ())
        if is_entry(entry, PROBE_KEYS) and all(check_items.is_text(entry[key]) for key in PROBE_KEYS)
    }


def check_probed(who, criterion, line, name, target, stored, builders):
    entry = stored.get((line["id"], name, target))
    if entry is None:
        return (error("acceptance line %s has no %s probe for %s; run surface_probe.py" % (line["id"], name, target)),)
    if entry["status"] != "fail":
        return ()
    if criterion.get("seam") in builders:
        return (
            error(
                "%s sits at a seam the builder runs, but the %s probe of %s failed: %s"
                % (who, name, line["id"], entry["detail"])
            ),
        )
    return (
        warning(
            "%s sits at a seam the builder cannot run, and the %s probe of %s failed: %s"
            % (who, name, line["id"], entry["detail"])
        ),
    )


def check_surface_probes(record, seams, complete):
    if not complete:
        return ()
    stored = stored_probes(record)
    builders = builder_seams(seams)
    criteria = part(record, "criteria")
    return tuple(
        finding
        for criterion, line, name, target in surface_probe.planned(record)
        for finding in check_probed(
            criterion_label(criteria.index(criterion), criterion), criterion, line, name, target, stored, builders
        )
    )


def check_stopped(record, complete):
    if not complete or record.get("status") != STOPPED:
        return ()
    stop = record.get("stop")
    reason = stop.get("reason") if isinstance(stop, dict) else None
    return (error("record status is stopped: %s" % (reason if check_items.is_text(reason) else "no stop reason")),)


def check_stop(record):
    stopped = record.get("status") == STOPPED
    if "stop" not in record:
        return (error("record status is 'stopped' but the record has no stop"),) if stopped else ()
    if not stopped:
        return (error("record has stop but its status is not 'stopped'"),)
    stop = record["stop"]
    if is_entry(stop, STOP_KEYS) and all(check_items.is_text(stop[key]) for key in STOP_KEYS):
        return ()
    return (error("record stop is not an object with exactly non-empty string phase and reason"),)


def is_repeated(entry):
    return is_entry(entry, REPEATED_KEYS) and check_items.is_text(entry["kind"]) and is_count(entry["count"], 2)


def check_outcomes(record):
    if "outcomes" not in record:
        return ()
    outcomes = record["outcomes"]
    if not is_entry(outcomes, OUTCOME_KEYS):
        return (error("record outcomes is not an object with exactly store, entries and repeated"),)
    repeated = outcomes["repeated"]
    rules = (
        ("store", check_items.is_text(outcomes["store"]), "a non-empty string"),
        ("entries", is_count(outcomes["entries"], 0), "an integer of at least 0"),
        (
            "repeated",
            isinstance(repeated, list) and all(is_repeated(entry) for entry in repeated),
            "a list of objects with exactly a non-empty string kind and an integer count of at least 2",
        ),
    )
    return tuple(
        error("record outcomes has %s that is not %s" % (key, shape)) for key, valid, shape in rules if not valid
    )


def check(text, complete=False):
    try:
        record = json.loads(text)
    except (ValueError, RecursionError) as exc:
        return (error("record is not valid JSON: %s" % exc),)
    if not isinstance(record, dict):
        return (error("record is not a JSON object"),)
    seams = part(record, "seams")
    criteria = part(record, "criteria")
    steps = part(record, "steps")
    return (
        check_shape(record)
        + check_seams(seams, criteria, complete)
        + check_criteria(criteria, seams, steps, record_locked(record), complete)
        + check_steps(steps, criteria)
        + check_locked(record, criteria, steps, complete)
        + check_probes(record)
        + check_surface_probes(record, seams, complete)
        + check_stop(record)
        + check_stopped(record, complete)
        + check_outcomes(record)
        + check_rounds(record)
        + check_missing_parts(record, complete)
    )


def parse_arguments(argv):
    flags = tuple(argument for argument in argv if argument == COMPLETE)
    paths = tuple(argument for argument in argv if argument != COMPLETE)
    if len(flags) > 1 or len(paths) != 1 or paths[0].startswith("-"):
        return None
    return paths[0], bool(flags)


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
    path, complete = arguments
    text = read_text(path)
    if text is None:
        print("cannot read: " + path, file=sys.stderr)
        return 2
    findings = check(text, complete)
    for severity, message in findings:
        print("%s: %s" % (severity, message))
    return 1 if any(severity == "error" for severity, _ in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
