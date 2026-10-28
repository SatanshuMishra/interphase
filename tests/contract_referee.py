import hashlib
import json
import pathlib
import re

DIGESTS = {
    "k1-acceptance": "fe1207087cd15a1f386421182419634bd9bb141c90a4de21e287ef0338a7d357",
    "k2-locked": "4a9d4ddc1af766f694399f6ecba699ce93344fa323e108e9197c4a68c40b0e26",
    "k6-outcome": "dec9f762cc12389c487d41f6a64a847e330403c623a88337222f539f0cf9175b",
}
ANNOTATIONS = frozenset(("$schema", "$id", "title", "description"))
SINGLE_SCHEMA_KEYWORDS = ("additionalProperties", "items", "if", "then", "else", "not", "contains")
LIST_SCHEMA_KEYWORDS = ("anyOf", "allOf")
MAP_SCHEMA_KEYWORDS = ("properties",)
VALUE_KEYWORDS = (
    "type",
    "enum",
    "const",
    "pattern",
    "minLength",
    "required",
    "minItems",
    "uniqueItems",
    "minContains",
    "maxContains",
)
KEYWORDS = frozenset(SINGLE_SCHEMA_KEYWORDS + LIST_SCHEMA_KEYWORDS + MAP_SCHEMA_KEYWORDS + VALUE_KEYWORDS) | ANNOTATIONS


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def load(name):
    if name not in DIGESTS:
        raise AssertionError("no pinned digest for contract %r" % name)
    path = repository_root() / "contracts" / (name + ".schema.json")
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != DIGESTS[name]:
        raise AssertionError("contract %s has SHA-256 %s; expected %s" % (path, digest, DIGESTS[name]))
    return json.loads(data.decode("utf-8"))


def unescape(token):
    return token.replace("~1", "/").replace("~0", "~")


def subschema(schema, pointer):
    if pointer == "":
        return schema
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer %r does not start with /" % pointer)
    found = schema
    for token in (unescape(part) for part in pointer.split("/")[1:]):
        found = found[int(token)] if isinstance(found, list) else found[token]
    return found


def check_keywords(schema, where):
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise ValueError("schema at %r is not an object or a boolean" % where)
    unknown = sorted(key for key in schema if key not in KEYWORDS)
    if unknown:
        raise ValueError("schema at %r uses unsupported keyword %r" % (where, unknown[0]))
    for key in SINGLE_SCHEMA_KEYWORDS:
        if key in schema:
            check_keywords(schema[key], where + "/" + key)
    for key in LIST_SCHEMA_KEYWORDS:
        for index, member in enumerate(schema.get(key, ())):
            check_keywords(member, "%s/%s/%d" % (where, key, index))
    for key in MAP_SCHEMA_KEYWORDS:
        for name, member in schema.get(key, {}).items():
            check_keywords(member, "%s/%s/%s" % (where, key, name))


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def same(first, second):
    if isinstance(first, bool) or isinstance(second, bool):
        return isinstance(first, bool) and isinstance(second, bool) and first == second
    if is_number(first) and is_number(second):
        return first == second
    if isinstance(first, list) and isinstance(second, list):
        return len(first) == len(second) and all(same(a, b) for a, b in zip(first, second))
    if isinstance(first, dict) and isinstance(second, dict):
        return first.keys() == second.keys() and all(same(first[key], second[key]) for key in first)
    return type(first) is type(second) and first == second


def has_type(value, name):
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if name == "number":
        return is_number(value)
    if name == "integer":
        return is_number(value) and float(value).is_integer()
    raise ValueError("unsupported type %r" % name)


def fail(where, keyword, message):
    return ("%s: %s: %s" % (where or "/", keyword, message),)


def type_errors(schema, value, where):
    if "type" not in schema:
        return ()
    names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
    if any(has_type(value, name) for name in names):
        return ()
    return fail(where, "type", "%r is not of type %s" % (value, " or ".join(names)))


def enum_errors(schema, value, where):
    if "enum" in schema and not any(same(value, option) for option in schema["enum"]):
        return fail(where, "enum", "%r is not one of %r" % (value, schema["enum"]))
    return ()


def const_errors(schema, value, where):
    if "const" in schema and not same(value, schema["const"]):
        return fail(where, "const", "%r is not %r" % (value, schema["const"]))
    return ()


def string_errors(schema, value, where):
    if not isinstance(value, str):
        return ()
    short = (
        fail(where, "minLength", "%r is shorter than %d" % (value, schema["minLength"]))
        if "minLength" in schema and len(value) < schema["minLength"]
        else ()
    )
    unmatched = (
        fail(where, "pattern", "%r does not match %r" % (value, schema["pattern"]))
        if "pattern" in schema and re.search(schema["pattern"], value) is None
        else ()
    )
    return short + unmatched


def object_errors(schema, value, where):
    if not isinstance(value, dict):
        return ()
    absent = tuple(
        message
        for key in schema.get("required", ())
        if key not in value
        for message in fail(where, "required", "lacks required property %r" % key)
    )
    properties = schema.get("properties", {})
    known = tuple(
        message
        for key, member in properties.items()
        if key in value
        for message in validate(member, value[key], "%s/%s" % (where, key))
    )
    extra = (
        tuple(
            message
            for key in sorted(value)
            if key not in properties
            for message in validate(schema["additionalProperties"], value[key], "%s/%s" % (where, key))
        )
        if "additionalProperties" in schema
        else ()
    )
    return absent + known + extra


def unique_errors(schema, value, where):
    if not schema.get("uniqueItems"):
        return ()
    repeats = tuple(
        index
        for index, item in enumerate(value)
        if any(same(item, earlier) for earlier in value[:index])
    )
    return fail(where, "uniqueItems", "item %d repeats an earlier item" % repeats[0]) if repeats else ()


def contains_errors(schema, value, where):
    if "contains" not in schema:
        return ()
    count = sum(1 for item in value if not validate(schema["contains"], item, where))
    least = schema.get("minContains", 1)
    most = schema.get("maxContains")
    few = fail(where, "minContains", "%d items match contains; at least %d needed" % (count, least)) if count < least else ()
    many = (
        fail(where, "maxContains", "%d items match contains; at most %d allowed" % (count, most))
        if most is not None and count > most
        else ()
    )
    return few + many


def array_errors(schema, value, where):
    if not isinstance(value, list):
        return ()
    short = (
        fail(where, "minItems", "%d items; at least %d needed" % (len(value), schema["minItems"]))
        if "minItems" in schema and len(value) < schema["minItems"]
        else ()
    )
    members = (
        tuple(
            message
            for index, item in enumerate(value)
            for message in validate(schema["items"], item, "%s/%d" % (where, index))
        )
        if "items" in schema
        else ()
    )
    return short + members + unique_errors(schema, value, where) + contains_errors(schema, value, where)


def logic_errors(schema, value, where):
    conditional = ()
    if "if" in schema:
        branch = "then" if not validate(schema["if"], value, where) else "else"
        conditional = validate(schema[branch], value, where) if branch in schema else ()
    negated = (
        fail(where, "not", "value matches a schema it must not match")
        if "not" in schema and not validate(schema["not"], value, where)
        else ()
    )
    alternatives = (
        fail(where, "anyOf", "value matches none of the alternatives")
        if "anyOf" in schema and all(validate(member, value, where) for member in schema["anyOf"])
        else ()
    )
    combined = tuple(
        message for member in schema.get("allOf", ()) for message in validate(member, value, where)
    )
    return conditional + negated + alternatives + combined


def validate(schema, value, where):
    if schema is True:
        return ()
    if schema is False:
        return fail(where, "false", "no value is allowed here")
    return (
        type_errors(schema, value, where)
        + enum_errors(schema, value, where)
        + const_errors(schema, value, where)
        + string_errors(schema, value, where)
        + object_errors(schema, value, where)
        + array_errors(schema, value, where)
        + logic_errors(schema, value, where)
    )


def errors(schema, value):
    check_keywords(schema, "")
    return tuple(validate(schema, value, ""))
