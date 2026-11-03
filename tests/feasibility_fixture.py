import importlib.util
import pathlib


def load_check_record():
    path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_record.py"
    spec = importlib.util.spec_from_file_location("check_record", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


record_checker = load_check_record()


def listed(value):
    return value if isinstance(value, list) else []


def passed_results(record):
    return [
        {"check": key, "subject": "%s::%s %s" % (row["file"], row["name"], path), "status": "pass", "detail": key}
        for criterion in listed(record.get("criteria"))
        if isinstance(criterion, dict) and criterion.get("acceptance")
        for row in listed(criterion.get("tests"))
        if isinstance(row, dict) and isinstance(row.get("file"), str) and isinstance(row.get("name"), str)
        for key in ("loads", "needs")
        for path in listed(row.get(key))
        if isinstance(path, str)
    ]


def feasible(record):
    if not isinstance(record, dict) or not isinstance(record.get("locked"), list):
        return record
    feasibility = {"digest": record_checker.feasibility_digest(record), "results": passed_results(record)}
    return {**record, "feasibility": feasibility}
