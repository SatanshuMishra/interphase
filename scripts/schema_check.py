import json
import pathlib
import re

CONTRACTS = pathlib.Path(__file__).resolve().parents[1] / "contracts"
ANNOTATIONS = frozenset(("$schema", "$id", "title", "description"))
SCHEMA_KEYWORDS = ("items", "if", "then", "else", "not", "contains")
SCHEMA_LIST_KEYWORDS = ("anyOf", "allOf")
VALUE_KEYWORDS = (
    "type",
    "enum",
    "const",
    "pattern",
    "minLength",
    "required",
    "properties",
    "additionalProperties",
    "minItems",
    "uniqueItems",
    "minContains",
    "maxContains",
)
KEYWORDS = ANNOTATIONS | frozenset(SCHEMA_KEYWORDS + SCHEMA_LIST_KEYWORDS + VALUE_KEYWORDS)
PATTERN_TOKEN = re.compile(r"\\.|\[(?:\\.|[^\]\\])*\]|.", re.DOTALL)


def load(name):
    with open(CONTRACTS / (name + ".schema.json"), encoding="utf-8") as handle:
        return json.load(handle)


def unescape(token):
    return token.replace("~1", "/").replace("~0", "~")


def escape(token):
    return token.replace("~", "~0").replace("/", "~1")


def subschema(schema, pointer):
    if pointer == "":
        return schema
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer %r does not start with /" % pointer)
    found = schema
    for token in (unescape(part) for part in pointer.split("/")[1:]):
        found = found[int(token)] if isinstance(found, list) else found[token]
    return found


def nested(schema):
    singles = tuple(schema[key] for key in SCHEMA_KEYWORDS if key in schema)
    listed = tuple(member for key in SCHEMA_LIST_KEYWORDS for member in schema.get(key, ()))
    mapped = tuple(schema.get("properties", {}).values())
    return singles + listed + mapped


def supported(schema):
    if not isinstance(schema, dict):
        raise ValueError("schema %r is not an object" % (schema,))
    unknown = sorted(key for key in schema if key not in KEYWORDS)
    if unknown:
        raise ValueError("unsupported JSON Schema keyword %r" % unknown[0])
    if "additionalProperties" in schema and schema["additionalProperties"] is not False:
        raise ValueError("unsupported JSON Schema keyword 'additionalProperties' other than false")
    strange = tuple(name for name in type_names(schema) if name not in TYPE_CHECKS)
    if strange:
        raise ValueError("unsupported JSON Schema type %r" % (strange[0],))
    for member in nested(schema):
        supported(member)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def same(first, second):
    if isinstance(first, bool) or isinstance(second, bool):
        return isinstance(first, bool) and isinstance(second, bool) and first == second
    if is_number(first) and is_number(second):
        return first == second
    if isinstance(first, list) and isinstance(second, list):
        return len(first) == len(second) and all(same(one, other) for one, other in zip(first, second))
    if isinstance(first, dict) and isinstance(second, dict):
        return first.keys() == second.keys() and all(same(first[key], second[key]) for key in first)
    return type(first) is type(second) and first == second


TYPE_CHECKS = {
    "object": lambda value: isinstance(value, dict),
    "array": lambda value: isinstance(value, list),
    "string": lambda value: isinstance(value, str),
    "number": is_number,
    "integer": lambda value: is_number(value) and float(value).is_integer(),
    "boolean": lambda value: isinstance(value, bool),
    "null": lambda value: value is None,
}


def type_names(schema):
    if "type" not in schema:
        return ()
    return tuple(schema["type"]) if isinstance(schema["type"], list) else (schema["type"],)


def failure(pointer, keyword, message):
    return ("#%s %s: %s" % (pointer, keyword, message),)


def child(pointer, token):
    return "%s/%s" % (pointer, escape(str(token)))


def type_errors(schema, value, pointer):
    names = type_names(schema)
    if not names or any(TYPE_CHECKS[name](value) for name in names):
        return ()
    return failure(pointer, "type", "%r is not of type %s" % (value, " or ".join(names)))


def enum_errors(schema, value, pointer):
    if "enum" in schema and not any(same(value, option) for option in schema["enum"]):
        options = ", ".join(repr(option) for option in schema["enum"])
        return failure(pointer, "enum", "%r is not one of %s" % (value, options))
    return ()


def const_errors(schema, value, pointer):
    if "const" in schema and not same(value, schema["const"]):
        return failure(pointer, "const", "%r is not %r" % (value, schema["const"]))
    return ()


def ecma_pattern(pattern):
    return "".join("\\Z" if token == "$" else token for token in PATTERN_TOKEN.findall(pattern))


def string_errors(schema, value, pointer):
    if not isinstance(value, str):
        return ()
    short = (
        failure(pointer, "minLength", "%r is shorter than %d" % (value, schema["minLength"]))
        if "minLength" in schema and len(value) < schema["minLength"]
        else ()
    )
    unmatched = (
        failure(pointer, "pattern", "%r does not match %r" % (value, schema["pattern"]))
        if "pattern" in schema and re.search(ecma_pattern(schema["pattern"]), value) is None
        else ()
    )
    return short + unmatched


def object_errors(schema, value, pointer):
    if not isinstance(value, dict):
        return ()
    properties = schema.get("properties", {})
    absent = tuple(
        finding
        for key in schema.get("required", ())
        if key not in value
        for finding in failure(pointer, "required", "lacks required property %r" % key)
    )
    members = tuple(
        finding
        for key, member in properties.items()
        if key in value
        for finding in validate(member, value[key], child(pointer, key))
    )
    extra = (
        tuple(
            finding
            for key in sorted(value)
            if key not in properties
            for finding in failure(child(pointer, key), "additionalProperties", "property %r is not allowed" % key)
        )
        if schema.get("additionalProperties") is False
        else ()
    )
    return absent + members + extra


def unique_errors(schema, value, pointer):
    if not schema.get("uniqueItems"):
        return ()
    repeats = tuple(index for index, item in enumerate(value) if any(same(item, earlier) for earlier in value[:index]))
    return failure(child(pointer, repeats[0]), "uniqueItems", "item repeats an earlier item") if repeats else ()


def contains_errors(schema, value, pointer):
    if "contains" not in schema:
        return ()
    count = sum(1 for index, item in enumerate(value) if not validate(schema["contains"], item, child(pointer, index)))
    least = schema.get("minContains", 1)
    most = schema.get("maxContains")
    few = (
        failure(pointer, "minContains", "%d items match contains; at least %d needed" % (count, least))
        if count < least
        else ()
    )
    many = (
        failure(pointer, "maxContains", "%d items match contains; at most %d allowed" % (count, most))
        if most is not None and count > most
        else ()
    )
    return few + many


def array_errors(schema, value, pointer):
    if not isinstance(value, list):
        return ()
    short = (
        failure(pointer, "minItems", "%d items; at least %d needed" % (len(value), schema["minItems"]))
        if "minItems" in schema and len(value) < schema["minItems"]
        else ()
    )
    members = (
        tuple(
            finding
            for index, item in enumerate(value)
            for finding in validate(schema["items"], item, child(pointer, index))
        )
        if "items" in schema
        else ()
    )
    return short + members + unique_errors(schema, value, pointer) + contains_errors(schema, value, pointer)


def conditional_errors(schema, value, pointer):
    if "if" not in schema:
        return ()
    branch = "else" if validate(schema["if"], value, pointer) else "then"
    return validate(schema[branch], value, pointer) if branch in schema else ()


def logic_errors(schema, value, pointer):
    negated = (
        failure(pointer, "not", "value matches a schema it must not match")
        if "not" in schema and not validate(schema["not"], value, pointer)
        else ()
    )
    alternatives = (
        failure(pointer, "anyOf", "value matches none of the alternatives")
        if "anyOf" in schema and all(validate(member, value, pointer) for member in schema["anyOf"])
        else ()
    )
    combined = tuple(finding for member in schema.get("allOf", ()) for finding in validate(member, value, pointer))
    return conditional_errors(schema, value, pointer) + negated + alternatives + combined


def validate(schema, value, pointer):
    return (
        type_errors(schema, value, pointer)
        + enum_errors(schema, value, pointer)
        + const_errors(schema, value, pointer)
        + string_errors(schema, value, pointer)
        + object_errors(schema, value, pointer)
        + array_errors(schema, value, pointer)
        + logic_errors(schema, value, pointer)
    )


def errors(schema, value):
    supported(schema)
    return validate(schema, value, "")
