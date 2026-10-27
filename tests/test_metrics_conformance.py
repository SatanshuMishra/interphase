import datetime
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts" / "metrics_writer.py"
FIXTURES = ROOT / "metrics" / "fixtures"
PREFIX = "metrics not written: "
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
STANDIN = ("<root>", "<home>")
INHERITED_OUT = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_PLUGIN_ROOT", "PLUGIN_METRICS_DIR", "PLUGIN_METRICS_PARENT")
WRITER_CALLABLES = ["append_event", "write_summary", "write_catalogue", "run_id", "prune"]
SELF_CONTAINED_LOAD = (
    "import importlib.util, json, os, sys\n"
    "writer_path, repository = sys.argv[1], os.path.realpath(sys.argv[2])\n"
    "def inside(entry):\n"
    "    resolved = os.path.realpath(entry or os.getcwd())\n"
    "    return resolved == repository or resolved.startswith(repository + os.sep)\n"
    "sys.path = [entry for entry in sys.path if not inside(entry)]\n"
    "spec = importlib.util.spec_from_file_location('metrics_writer_alone', writer_path)\n"
    "module = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(module)\n"
    "print(json.dumps({\n"
    "    'inside': [entry for entry in sys.path if inside(entry)],\n"
    "    'callables': [name for name in json.loads(sys.argv[3]) if callable(getattr(module, name, None))],\n"
    "}))\n"
)


def load_writer():
    spec = importlib.util.spec_from_file_location("metrics_writer_under_test", str(WRITER))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(name):
    with open(FIXTURES / name, encoding="utf-8") as handle:
        return json.load(handle)


def moment(text):
    return datetime.datetime.strptime(text, TIMESTAMP_FORMAT).replace(tzinfo=datetime.timezone.utc)


def substituted(value, root, home):
    return dict(zip(STANDIN, (root, home))).get(value, value) if isinstance(value, str) else value


def relative(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def reported(result, root):
    if isinstance(result, tuple):
        return [relative(path, root) for path in result]
    if isinstance(result, str) and result.startswith(PREFIX):
        rest = result[len(PREFIX):]
        return PREFIX + rest[:rest.index(": ") + 2]
    return result


def call_result(writer, call, environ, root, home):
    args = {name: substituted(value, root, home) for name, value in call["args"].items()}
    if call["fn"] in ("append_event", "write_summary"):
        return getattr(writer, call["fn"])(environ=environ, now=moment(call["now"]), **args)
    if call["fn"] == "write_catalogue":
        return writer.write_catalogue(environ=environ, **args)
    if call["fn"] == "prune":
        return writer.prune(**args)
    return writer.run_id(args["name"], moment(args["start"]))


def written_files(root):
    found = {}
    for folder, _, names in os.walk(root):
        for name in names:
            path = os.path.join(folder, name)
            with open(path, "rb") as handle:
                found = {**found, relative(path, root): handle.read().decode("utf-8")}
    return found


def run_case(writer, case, folder):
    root = os.path.join(folder, "root")
    home = os.path.join(folder, "home")
    os.makedirs(root)
    os.makedirs(home)
    environ = {name: substituted(value, root, home) for name, value in case["environ"].items()}
    returns = [reported(call_result(writer, call, environ, root, home), root) for call in case["calls"]]
    return {"files": written_files(root), "returns": returns}


class MetricsConformanceTest(unittest.TestCase):
    def setUp(self):
        self.folder = os.path.realpath(tempfile.mkdtemp(prefix="metrics-conformance-"))
        self.addCleanup(shutil.rmtree, self.folder, True)

    def test_writer_matches_fixtures(self):
        writer = load_writer()
        expected = fixture("expected.json")
        outcome = {
            case["name"]: run_case(writer, case, os.path.join(self.folder, case["name"]))
            for case in fixture("cases.json")
        }
        self.assertEqual(sorted(outcome), sorted(expected))
        for name, written in expected.items():
            with self.subTest(case=name):
                self.assertEqual(outcome[name], written)

    def test_writer_is_self_contained(self):
        home = os.path.join(self.folder, "home")
        store = os.path.join(self.folder, "store")
        outside = os.path.join(self.folder, "outside")
        for folder in (home, store, outside):
            os.mkdir(folder)
        inherited = {key: value for key, value in os.environ.items() if key not in INHERITED_OUT}
        completed = subprocess.run(
            [sys.executable, "-I", "-c", SELF_CONTAINED_LOAD, str(WRITER), str(ROOT), json.dumps(WRITER_CALLABLES)],
            cwd=outside,
            env={**inherited, "HOME": home, "PLUGIN_METRICS_DIR": store},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", "replace"))
        self.assertEqual(
            json.loads(completed.stdout.decode("utf-8")),
            {"inside": [], "callables": ["append_event", "write_summary", "write_catalogue", "run_id", "prune"]},
        )


if __name__ == "__main__":
    unittest.main()
