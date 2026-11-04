import importlib.util
import pathlib

CONTRACTS = pathlib.Path(__file__).resolve().parents[1] / "contracts"
VALIDATOR_FILE = CONTRACTS / "validator.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("interphase_owned_validator", str(VALIDATOR_FILE))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator()


def schema(name):
    return validator.read_schema(validator.schema_path(str(CONTRACTS), name))


def part(name, pointer):
    return validator.at_pointer(schema(name), pointer)


def errors(name, value):
    return validator.errors_against(str(CONTRACTS), name, value)


def part_errors(name, pointer, value):
    return validator.errors(part(name, pointer), value, str(CONTRACTS))
