import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

OWNED_SCHEMAS = ("h11-interphase-record", "h12-interphase-items", "k1-acceptance", "k2-locked", "k6-outcome")
SCHEMA_SUFFIX = ".schema.json"
VALIDATOR = "validator.py"
PROGRAM_FOLDER = (".mitosis", "harness-redesign", "contracts")
CHECK_COPIES = "check_copies.py"
OLD_VALIDATOR = "schema_check"
EXPECTED_REFERENCES = {
    "h11-interphase-record": ("k1-acceptance.schema.json", "k2-locked.schema.json"),
    "h12-interphase-items": ("h11-interphase-record.schema.json", "k1-acceptance.schema.json"),
}
RESOLVE_ERRORS = (ValueError, KeyError, IndexError, TypeError, OSError)


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def contracts_folder():
    return repository_root() / "contracts"


def load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixtures():
    tests = repository_root() / "tests"
    lane = load_path("owned_formats_vendored_lane", tests / "test_check_author_lane.py")
    kinds = load_path("owned_formats_vendored_kinds", tests / "test_outcome_kinds.py")
    return lane.complete_record(), kinds.SPEC_WITHOUT_KIND


def environment(home):
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
    }
    return {**kept, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1"}


def run(arguments, cwd, env):
    return subprocess.run(
        [sys.executable] + [str(argument) for argument in arguments],
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def references(value):
    if isinstance(value, dict):
        own = (value["$ref"],) if isinstance(value.get("$ref"), str) else ()
        return own + tuple(found for member in value.values() for found in references(member))
    if isinstance(value, list):
        return tuple(found for member in value for found in references(member))
    return ()


def with_first_line_kind(record, kind):
    first = record["criteria"][0]
    line = {**first["acceptance"][0], "kind": kind}
    changed = {**first, "acceptance": [line] + list(first["acceptance"][1:])}
    return {**record, "criteria": [changed] + list(record["criteria"][1:])}


def write_demo(folder, record, spec_text):
    (folder / "demo.md").write_text(spec_text, encoding="utf-8")
    path = folder / "demo.record.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def mentions_old_validator(path):
    return OLD_VALIDATOR in path.read_bytes().decode("utf-8", "replace")


class VendoredContractsTest(unittest.TestCase):
    def test_contracts_folder_holds_each_owned_format_and_every_ref_resolves(self):
        contracts = contracts_folder()
        self.assertTrue((contracts / VALIDATOR).is_file(), "contracts/validator.py is missing")
        for name in OWNED_SCHEMAS:
            self.assertTrue((contracts / (name + SCHEMA_SUFFIX)).is_file(), name + SCHEMA_SUFFIX)
        validator = load_path("owned_formats_vendored_validator", contracts / VALIDATOR)
        found = {}
        for name in OWNED_SCHEMAS:
            schema = json.loads((contracts / (name + SCHEMA_SUFFIX)).read_text(encoding="utf-8"))
            validator.supported(schema)
            scope = validator.Scope(str(contracts), schema)
            found = {**found, name: references(schema)}
            for reference in found[name]:
                with self.subTest(schema=name, reference=reference):
                    try:
                        _, target = validator.resolve(scope, reference)
                    except RESOLVE_ERRORS as exc:
                        self.fail("%s: $ref %s does not resolve: %s" % (name, reference, exc))
                    validator.supported(target)
        for name, targets in EXPECTED_REFERENCES.items():
            for target in targets:
                landing = [reference for reference in found[name] if reference.partition("#")[0] == target]
                self.assertNotEqual(landing, [], "%s has no $ref into %s" % (name, target))

    def test_record_checks_run_through_the_vendored_validator(self):
        root = repository_root()
        self.assertFalse((root / "scripts" / (OLD_VALIDATOR + ".py")).exists())
        this_file = pathlib.Path(__file__).resolve()
        naming = sorted(
            str(path.relative_to(root))
            for folder in ("scripts", "tests")
            for path in (root / folder).rglob("*.py")
            if path.resolve() != this_file and mentions_old_validator(path)
        )
        self.assertEqual(naming, [])
        record, spec_text = fixtures()
        fuzzy = with_first_line_kind(record, "fuzzy")
        with tempfile.TemporaryDirectory() as base:
            folder = pathlib.Path(base).resolve()
            home = folder / "home"
            home.mkdir()
            path = write_demo(folder, fuzzy, spec_text)
            result = run([root / "scripts" / "check_record.py", path], folder, environment(home))
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1, output)
        naming = [
            line
            for line in result.stdout.splitlines()
            if line.startswith("error: ") and "criterion 5.1" in line and "#/kind enum" in line
        ]
        self.assertNotEqual(naming, [], output)


class ProgramCopiesTest(unittest.TestCase):
    def test_check_copies_finds_every_owned_copy_identical_to_the_program_copy(self):
        program = pathlib.Path(os.path.expanduser("~")).joinpath(*PROGRAM_FOLDER)
        script = program / CHECK_COPIES
        if not script.is_file():
            self.skipTest("the program contracts folder %s holds no %s" % (program, CHECK_COPIES))
        root = repository_root()
        result = subprocess.run(
            [sys.executable, str(script), str(root)],
            cwd=str(root),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        verdicts = tuple(json.loads(line) for line in result.stdout.splitlines() if line.strip())
        same = frozenset(
            str(verdict.get("file", "")).replace(os.sep, "/")
            for verdict in verdicts
            if isinstance(verdict, dict) and verdict.get("same") is True
        )
        expected = ("contracts/" + VALIDATOR,) + tuple("contracts/" + name + SCHEMA_SUFFIX for name in OWNED_SCHEMAS)
        for name in expected:
            self.assertIn(name, same, output)


if __name__ == "__main__":
    unittest.main()
