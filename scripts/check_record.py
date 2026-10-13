import importlib.util
import json
import os
import pathlib
import re
import sys

USAGE = "usage: python3 check_record.py [--complete] RECORD"
COMPLETE = "--complete"
RECORD_KEYS = ("environments", "facts", "criteria", "steps")
STATUSES = ("in-progress", "handed-off")
MISSING_PARTS =("environments", "criteria", "steps")
ENVIRONMENT_KEYS = ("name", "what", "builder_runs")
LOCATION = ("path", "line", "quote")
COMMAND = ("command", "output")
CITATIONS = (LOCATION, ("url",), COMMAND)
PARTIAL_CITATIONS = {
    LOCATION: "only some of path, line and quote",
    COMMAND: "only one of command and output",
}
FACT_KEYS = ("id", "fact", "outside") + tuple(key for form in CITATIONS for key in form)
CRITERION_KEYS = (
    "number",
    "title",
    "text",
    "where",
    "tests",
    "unproven",
    "varies",
    "domains",
    "gives_way",
    "facts",
)
CRITERION_REQUIRED = ("number", "title", "text", "where", "tests")
DOMAIN_KEYS = ("name", "over", "classes", "fact")
DOMAIN_REQUIRED = ("name", "over", "classes")
GIVES_WAY = "gives-way"
TEST_KEYS = ("file", "name", "given", "expect", "env", "step")
COVERS = "covers"
QUANTIFIER_RE = re.compile(r"\b(every|each|any|all|whole|always|never|whatever|however|whenever)\b", re.IGNORECASE)
BOUND_RE = re.compile(
    r"\b(at\s+most|no\s+more\s+than|up\s+to|maximum|budget|limits?|caps?|exceed(?:s|ing)?)\b", re.IGNORECASE
)
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
RENDERED_KEYS = ("source", "acceptance", "spec_ref")
NUMBER_RE = re.compile(r"[0-9]+\.[0-9]+")


def load_items_checker():
    spec = importlib.util.spec_from_file_location("check_items", pathlib.Path(__file__).with_name("check_items.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_items = load_items_checker()
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


def is_line(value):
    return is_count(value, 1)


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
        error("record has unknown key %r" % key) for key in sorted(record) if key not in RECORD_KEYS + ("status",)
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
    return tuple(missing("record has no %s" % key, complete) for key in MISSING_PARTS if record.get(key) == [])


def environment_label(index, environment):
    name = environment.get("name") if isinstance(environment, dict) else None
    return "environment %r" % name if check_items.is_text(name) else "environment %d" % (index + 1)


def check_environment_name(who, environment):
    if "name" not in environment:
        return ()
    name = environment["name"]
    if isinstance(name, str) and check_items.NAME_RE.match(name):
        return ()
    return (error("%s has a name that is not lowercase kebab-case" % who),)


def check_builder_runs(who, environment):
    if "builder_runs" in environment and not isinstance(environment["builder_runs"], bool):
        return (error("%s has builder_runs that is not true or false" % who),)
    return ()


def check_environment(index, environment):
    who = environment_label(index, environment)
    if not isinstance(environment, dict):
        return (error("%s is not an object" % who),)
    return (
        unknown_keys(who, environment, ENVIRONMENT_KEYS)
        + missing_keys(who, environment, ENVIRONMENT_KEYS)
        + check_environment_name(who, environment)
        + text_fields(who, environment, ("what",))
        + check_builder_runs(who, environment)
    )


def environment_names(environments):
    return tuple(
        environment["name"]
        for environment in environments
        if isinstance(environment, dict) and check_items.is_text(environment.get("name"))
    )


def builder_environments(environments):
    return frozenset(
        environment["name"]
        for environment in environments
        if isinstance(environment, dict)
        and check_items.is_text(environment.get("name"))
        and environment.get("builder_runs") is True
    )


def check_environments(environments):
    per_environment = tuple(
        finding for index, environment in enumerate(environments) for finding in check_environment(index, environment)
    )
    repeated = tuple(
        error("environment name %r is duplicated" % name) for name in duplicated(environment_names(environments))
    )
    return per_environment + repeated


def fact_label(index, fact):
    fact_id = fact.get("id") if isinstance(fact, dict) else None
    return "fact %r" % fact_id if check_items.is_text(fact_id) else "fact %d" % (index + 1)


def read_lines(path):
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError):
        return None
    lines = tuple(text.split("\n"))
    return lines[:-1] if lines[-1] == "" else lines


def check_path_value(who, fact):
    path = fact["path"]
    if not check_items.is_text(path):
        return (error("%s has path that is not a non-empty string" % who),)
    if check_items.bad_path(path):
        return (error("%s has path %r, which is absolute or holds a '..' segment" % (who, path)),)
    return ()


def check_line_value(who, fact):
    if is_line(fact["line"]):
        return ()
    return (error("%s has line that is not an integer of at least 1" % who),)


def check_quote_value(who, fact):
    quote = fact["quote"]
    if not check_items.is_text(quote):
        return (error("%s has quote that is not a non-empty string" % who),)
    if not quote.strip():
        return (error("%s has quote that holds only spaces" % who),)
    return ()


def check_quote_in_file(who, fact, root):
    path = fact["path"]
    line = fact["line"]
    quote = fact["quote"].strip()
    full = os.path.join(root, path)
    if not os.path.exists(full):
        return (error("%s cites %r, which does not exist" % (who, path)),)
    lines = read_lines(full)
    if lines is None:
        return (error("%s cites %r, which cannot be read as UTF-8" % (who, path)),)
    if line > len(lines):
        return (error("%s cites line %d of %r, which ends at line %d" % (who, line, path, len(lines))),)
    if quote not in lines[line - 1]:
        return (error("%s quotes %r, which is not within line %d of %r" % (who, quote, line, path)),)
    return ()


def check_location(who, fact, root):
    shape = check_path_value(who, fact) + check_line_value(who, fact) + check_quote_value(who, fact)
    return shape if shape else check_quote_in_file(who, fact, root)


def citation_forms(fact):
    return tuple(form for form in CITATIONS if any(key in fact for key in form))


def check_citation(who, fact, root):
    forms = citation_forms(fact)
    if not forms:
        return (error("%s has no citation; give path, line and quote, or url, or command and output" % who),)
    if len(forms) > 1:
        return (error("%s has more than one citation form" % who),)
    form = forms[0]
    if not all(key in fact for key in form):
        return (error("%s has %s" % (who, PARTIAL_CITATIONS[form])),)
    if form == LOCATION:
        return check_location(who, fact, root)
    return text_fields(who, fact, form)


def check_outside(who, fact):
    if "outside" not in fact:
        return ()
    if not isinstance(fact["outside"], bool):
        return (error("%s has outside that is not true or false" % who),)
    if fact["outside"] and citation_forms(fact) != (COMMAND,):
        return (error("%s is marked outside but is not cited by command and output" % who),)
    return ()


def check_fact(index, fact, root):
    who = fact_label(index, fact)
    if not isinstance(fact, dict):
        return (error("%s is not an object" % who),)
    return (
        unknown_keys(who, fact, FACT_KEYS)
        + missing_keys(who, fact, ("id", "fact"))
        + text_fields(who, fact, ("id", "fact"))
        + check_citation(who, fact, root)
        + check_outside(who, fact)
    )


def fact_ids(facts):
    return tuple(fact["id"] for fact in facts if isinstance(fact, dict) and check_items.is_text(fact.get("id")))


def check_facts(facts, root):
    per_fact = tuple(finding for index, fact in enumerate(facts) for finding in check_fact(index, fact, root))
    repeated = tuple(error("fact id %r is duplicated" % fact_id) for fact_id in duplicated(fact_ids(facts)))
    return per_fact + repeated


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
    return (error("%s has a number that is not digits, one dot and digits, such as 7.3" % who),)


def check_where(who, criterion, known):
    if "where" not in criterion:
        return ()
    where = criterion["where"]
    if not isinstance(where, list) or not where or not all(check_items.is_text(name) for name in where):
        return (error("%s has where that is not a non-empty list of environment names" % who),)
    unknown = tuple(
        error("%s has where entry %r that names no environment" % (who, name)) for name in where if name not in known
    )
    repeated = tuple(
        error("%s lists environment %r more than once in where" % (who, name)) for name in duplicated(tuple(where))
    )
    return unknown + repeated


def well_formed(test):
    return isinstance(test, dict) and all(check_items.is_text(test.get(key)) for key in TEST_KEYS)


def entry_label(who, position, test):
    name = test.get("name") if isinstance(test, dict) else None
    return "%s test %r" % (who, name) if check_items.is_text(name) else "%s test %d" % (who, position + 1)


def check_test_env(tag, test, known):
    if test["env"] in known:
        return ()
    return (error("%s names unknown environment %r" % (tag, test["env"])),)


def check_test_step(tag, test, number, by_name):
    step = by_name.get(test["step"])
    if step is None:
        return (error("%s names unknown step %r" % (tag, test["step"])),)
    outside = (
        ()
        if test["file"] in check_items.step_files(step)
        else (error("%s has file %r, which is not in the files of step %r" % (tag, test["file"], test["step"])),)
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
    return tuple(
        domain
        for domain in domains
        if isinstance(domain, dict) and check_items.is_text(domain.get("name")) and domain["name"] != GIVES_WAY
    )


def domain_classes(domain):
    classes = domain.get("classes")
    return tuple(name for name in classes if check_items.is_text(name)) if isinstance(classes, list) else ()


def class_pairs(criterion):
    return unique(
        tuple((domain["name"], name) for domain in criterion_domains(criterion) for name in domain_classes(domain))
    )


def give_way_items(criterion):
    items = criterion.get("gives_way")
    return unique(tuple(item for item in items if check_items.is_text(item))) if isinstance(items, list) else ()


def check_cover(tag, entry, criterion):
    head, separator, tail = entry.partition(": ")
    if not separator:
        return (
            error("%s covers %r, which is not '<domain>: <class>' or 'gives-way: <item>'" % (tag, entry)),
        )
    if head == GIVES_WAY:
        if tail in give_way_items(criterion):
            return ()
        return (error("%s covers unknown give-way item %r" % (tag, tail)),)
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


def check_test(who, position, test, criterion, known, by_name):
    tag = entry_label(who, position, test)
    if not well_formed(test):
        return (
            error("%s is not an object with non-empty string file, name, given, expect, env and step" % tag),
        )
    varying = "varies" in criterion
    allowed = TEST_KEYS + (COVERS,) + (POPULATION_KEYS if varying else ())
    population = check_population(who, position, test) if varying else ()
    return (
        unknown_keys(tag, test, allowed)
        + check_covers(tag, test, criterion)
        + population
        + check_test_env(tag, test, known)
        + check_test_step(tag, test, criterion.get("number"), by_name)
    )


def check_tests(who, criterion, known, by_name):
    if "tests" not in criterion:
        return ()
    tests = criterion["tests"]
    if not isinstance(tests, list):
        return (error("%s has tests that is not a list" % who),)
    return tuple(
        finding
        for position, test in enumerate(tests)
        for finding in check_test(who, position, test, criterion, known, by_name)
    )


def domain_label(who, position, domain):
    name = domain.get("name") if isinstance(domain, dict) else None
    return "%s domain %r" % (who, name) if check_items.is_text(name) else "%s domain %d" % (who, position + 1)


def check_reserved_name(who, domain):
    if domain.get("name") == GIVES_WAY:
        return (error("%s uses the reserved name %r" % (who, GIVES_WAY)),)
    return ()


def check_classes(who, domain):
    if "classes" not in domain:
        return ()
    classes = domain["classes"]
    if not isinstance(classes, list) or len(classes) < 2 or not all(check_items.is_text(name) for name in classes):
        return (error("%s has classes that is not a list of at least two non-empty strings" % who),)
    return tuple(error("%s lists class %r more than once" % (who, name)) for name in duplicated(tuple(classes)))


def check_domain_fact(who, domain, ids):
    fact = domain.get("fact")
    if check_items.is_text(fact) and fact not in ids:
        return (error("%s names unknown fact %r" % (who, fact)),)
    return ()


def check_domain(who, position, domain, ids):
    tag = domain_label(who, position, domain)
    if not isinstance(domain, dict):
        return (error("%s is not an object" % tag),)
    return (
        unknown_keys(tag, domain, DOMAIN_KEYS)
        + missing_keys(tag, domain, DOMAIN_REQUIRED)
        + check_environment_name(tag, domain)
        + check_reserved_name(tag, domain)
        + text_fields(tag, domain, ("over", "fact"))
        + check_classes(tag, domain)
        + check_domain_fact(tag, domain, ids)
    )


def domain_names(domains):
    return tuple(
        domain["name"] for domain in domains if isinstance(domain, dict) and check_items.is_text(domain.get("name"))
    )


def check_domains(who, criterion, ids):
    if "domains" not in criterion:
        return ()
    domains = criterion["domains"]
    if not isinstance(domains, list) or not domains:
        return (error("%s has domains that is not a non-empty list" % who),)
    per_domain = tuple(
        finding for position, domain in enumerate(domains) for finding in check_domain(who, position, domain, ids)
    )
    repeated = tuple(
        error("%s domain name %r is duplicated" % (who, name)) for name in duplicated(domain_names(domains))
    )
    return per_domain + repeated


def check_gives_way(who, criterion):
    if "gives_way" not in criterion:
        return ()
    items = criterion["gives_way"]
    if not isinstance(items, list) or not items or not all(check_items.is_text(item) for item in items):
        return (error("%s has gives_way that is not a non-empty list of non-empty strings" % who),)
    return tuple(
        error("%s lists give-way item %r more than once" % (who, item)) for item in duplicated(tuple(items))
    )


def check_criterion_facts(who, criterion, ids):
    if "facts" not in criterion:
        return ()
    facts = criterion["facts"]
    if not isinstance(facts, list) or not facts or not all(isinstance(fact, str) for fact in facts):
        return (error("%s has facts that is not a non-empty list of strings" % who),)
    unknown = tuple(
        error("%s names unknown fact %r" % (who, fact)) for fact in unique(tuple(facts)) if fact not in ids
    )
    repeated = tuple(error("%s lists fact %r more than once" % (who, fact)) for fact in duplicated(tuple(facts)))
    return unknown + repeated


def first_match(pattern, criterion):
    text = criterion.get("text")
    found = pattern.search(text) if isinstance(text, str) else None
    return re.sub(r"\s+", " ", found.group(1)).lower() if found else None


def check_quantifier(who, criterion, complete):
    word = first_match(QUANTIFIER_RE, criterion)
    if word is None or "domains" in criterion:
        return ()
    return (missing("%s says %r but declares no domains" % (who, word), complete),)


def check_bound(who, criterion, complete):
    phrase = first_match(BOUND_RE, criterion)
    if phrase is None or "gives_way" in criterion:
        return ()
    return (missing("%s sets a bound with %r but lists nothing in gives_way" % (who, phrase), complete),)


def cover_pairs(test):
    covers = test.get(COVERS)
    if not isinstance(covers, list):
        return ()
    return tuple(tuple(entry.partition(": ")[0::2]) for entry in covers if isinstance(entry, str) and ": " in entry)


def covered(criterion):
    return frozenset(pair for test in criterion_tests(criterion) for pair in cover_pairs(test))


def check_coverage(who, criterion, complete):
    if "unproven" in criterion:
        return ()
    done = covered(criterion)
    classes = tuple(
        missing("%s has no test covering class %r of domain %r" % (who, name, domain), complete)
        for domain, name in class_pairs(criterion)
        if (domain, name) not in done
    )
    items = tuple(
        missing("%s has no test covering give-way item %r" % (who, item), complete)
        for item in give_way_items(criterion)
        if (GIVES_WAY, item) not in done
    )
    return classes + items


def check_varies(who, criterion):
    if "varies" not in criterion:
        return ()
    varies = criterion["varies"]
    if isinstance(varies, str) and varies in VARIES:
        return ()
    return (error("%s has varies %r, which is not %s" % (who, varies, " or ".join(repr(kind) for kind in VARIES))),)


def where_names(criterion):
    where = criterion.get("where")
    return frozenset(where) if check_items.is_text_list(where) else frozenset()


def criterion_tests(criterion):
    tests = criterion.get("tests")
    return tuple(test for test in tests if well_formed(test)) if isinstance(tests, list) else ()


def check_proof(who, criterion, builders, complete):
    counted = where_names(criterion) & builders
    proving = tuple(test["name"] for test in criterion_tests(criterion) if test["env"] in counted)
    if "unproven" in criterion:
        if proving:
            return (
                error(
                    "%s is marked unproven but has a test the builder runs in its where environments: %s"
                    % (who, ", ".join(proving))
                ),
            )
        return ()
    if proving:
        return ()
    return (
        missing(
            "%s has no test the builder runs in its where environments and is not marked unproven" % who, complete
        ),
    )


def check_criterion(index, criterion, known, builders, by_name, ids, complete):
    who = criterion_label(index, criterion)
    if not isinstance(criterion, dict):
        return (error("%s is not an object" % who),)
    return (
        unknown_keys(who, criterion, CRITERION_KEYS)
        + missing_keys(who, criterion, CRITERION_REQUIRED)
        + check_number(who, criterion)
        + text_fields(who, criterion, ("title", "text", "unproven"))
        + check_where(who, criterion, known)
        + check_varies(who, criterion)
        + check_domains(who, criterion, ids)
        + check_gives_way(who, criterion)
        + check_criterion_facts(who, criterion, ids)
        + check_tests(who, criterion, known, by_name)
        + check_proof(who, criterion, builders, complete)
        + check_quantifier(who, criterion, complete)
        + check_bound(who, criterion, complete)
        + check_coverage(who, criterion, complete)
    )


def check_criteria(criteria, environments, steps, facts, complete):
    known = frozenset(environment_names(environments))
    builders = builder_environments(environments)
    by_name = steps_by_name(steps)
    ids = frozenset(fact_ids(facts))
    per_criterion = tuple(
        finding
        for index, criterion in enumerate(criteria)
        for finding in check_criterion(index, criterion, known, builders, by_name, ids, complete)
    )
    numbers = criterion_numbers(criteria)
    repeated = tuple(error("criterion number %s is duplicated" % number) for number in duplicated(numbers))
    claimed = frozenset(number for step in steps if isinstance(step, dict) for number in step_criteria(step))
    unclaimed = tuple(
        missing("criterion %s is claimed by no step" % number, complete)
        for number in unique(numbers)
        if number not in claimed
    )
    return per_criterion + repeated + unclaimed


def check_step_keys(who, step):
    return tuple(
        error("%s holds %r, which the render script fills" % (who, key))
        if key in RENDERED_KEYS
        else error("%s has unknown key %r" % (who, key))
        for key in sorted(step)
        if key not in STEP_KEYS
    )


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


def check(text, root, complete=False):
    try:
        record = json.loads(text)
    except (ValueError, RecursionError) as exc:
        return (error("record is not valid JSON: %s" % exc),)
    if not isinstance(record, dict):
        return (error("record is not a JSON object"),)
    environments = part(record, "environments")
    facts = part(record, "facts")
    criteria = part(record, "criteria")
    steps = part(record, "steps")
    return (
        check_shape(record)
        + check_environments(environments)
        + check_facts(facts, root)
        + check_criteria(criteria, environments, steps, facts, complete)
        + check_steps(steps, criteria)
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
    findings = check(text, os.getcwd(), complete)
    for severity, message in findings:
        print("%s: %s" % (severity, message))
    return 1 if any(severity == "error" for severity, _ in findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
