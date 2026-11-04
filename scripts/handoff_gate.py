import importlib.util
import json
import pathlib

ERROR = "error"


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


owned_names = load_sibling("owned_names")
owned_formats = load_sibling("owned_formats")
check_record = load_sibling("check_record")
check_items = load_sibling("check_items")
atomic_file = load_sibling("atomic_file")


def schema_lines(path, name, value):
    return tuple(
        owned_names.mismatch(path, name, message)
        for message in owned_formats.errors(name, value)
    )


def parsed(text):
    try:
        return (True, json.loads(text))
    except (ValueError, RecursionError):
        return (False, None)


def record_gate(path, record_text, complete):
    readable, record = parsed(record_text)
    shape = schema_lines(path, owned_names.H11, record) if readable else ()
    findings = tuple(
        "%s: %s" % (path, message)
        for severity, message in check_record.check(record_text, complete=complete)
        if severity == ERROR
    )
    return shape + findings


def item_findings(items, spec_data):
    return check_items.check_value(items, lambda steps: check_items.check_spec_data(steps, spec_data))


def items_gate(path, items, spec_text, amendment):
    shape = schema_lines(path, owned_names.H12, items)
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
