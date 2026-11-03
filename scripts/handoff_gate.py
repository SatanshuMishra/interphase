import importlib.util
import json
import pathlib

H11 = "h11-interphase-record"
H12 = "h12-interphase-items"
SCHEMA_SUFFIX = ".schema.json"
ERROR = "error"


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


owned_formats = load_sibling("owned_formats")
check_record = load_sibling("check_record")
check_items = load_sibling("check_items")
atomic_file = load_sibling("atomic_file")


def schema_lines(path, name, value):
    return tuple(
        "%s does not match %s: %s" % (path, name + SCHEMA_SUFFIX, message)
        for message in owned_formats.errors(name, value)
    )


def parsed(text):
    try:
        return (True, json.loads(text))
    except (ValueError, RecursionError):
        return (False, None)


def record_gate(path, record_text, complete):
    readable, record = parsed(record_text)
    shape = schema_lines(path, H11, record) if readable else ()
    findings = tuple(
        "%s: %s" % (path, message)
        for severity, message in check_record.check(record_text, complete=complete)
        if severity == ERROR
    )
    return shape + findings


def item_findings(items, spec_data):
    if not isinstance(items, list):
        return (check_items.error("items file is not a JSON array"),)
    if not items:
        return (check_items.error("items file is an empty array"),)
    source = check_items.spec_source(items)
    spec = () if source is None else check_items.check_spec_bytes(items, source[0], source[1], spec_data)
    return check_items.check_step_rules(items) + spec


def items_gate(path, items, spec_text, amendment):
    shape = schema_lines(path, H12, items)
    found = item_findings(items, spec_text.encode("utf-8"))
    chosen = check_items.amendment_findings(found) if amendment else found
    return shape + tuple("%s: %s" % (path, message) for severity, _, message in chosen if severity == ERROR)


def record_text(record):
    return json.dumps(record, indent=2, ensure_ascii=False) + "\n"


def write_record(path, record):
    text = record_text(record)
    refusals = record_gate(path, text, False)
    if refusals:
        return refusals
    atomic_file.replace(path, text.encode("utf-8"))
    return ()
