import hashlib
import importlib.util
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

FULL_RUN_PROMPT = (
    "Use interphase to write a spec for this request, and stop at hand-off: "
    "{}. Work autonomously. Name the spec {}."
)
FULL_RUN_SETTINGS = {"runs": "3", "max_turns": "200", "timeout_seconds": "3600"}
FULL_RUN_TOOLS = ["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "Agent", "WebSearch", "WebFetch"]
KINDS = {"input", "output", "measured", None}

HELDOUT_CASES = {
    "variation-language-model-summary": (
        "130ac9f85181840b31ffe98463eaf90f9b4d6412e6587377737e46da105e335f",
        "output",
    ),
    "variation-plain-english-dates": (
        "ec3804785dded6617b7c456334ec92dbe3c2852c3c3ef9a726172c81dc969072",
        "input",
    ),
    "variation-slow-start-on-phone": (
        "db2749a0c2fae26e841502eebe271e8b9a364cd0d2752a7e641ed33056d6900d",
        "measured",
    ),
    "variation-empty-title-rejected": (
        "1ad28cc4e6ea668df4253feebafd7910010e2647e3c4538a653d23be7801a906",
        None,
    ),
}

DEV_CASES = {
    "variation-dev-output": ("Translate each note into Spanish with a language model", "output"),
    "variation-dev-input": (
        "Let people search their notes by describing what they remember, "
        "like 'that recipe with lemons from last spring'",
        "input",
    ),
    "variation-dev-measured": ("The note list takes three seconds to appear on my phone", "measured"),
    "variation-dev-negative": (
        "Refuse to save a note longer than 10,000 characters, with the message 'Note is too long'",
        None,
    ),
}


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def load_test_module(name):
    path = pathlib.Path(__file__).resolve().parent / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def yaml_scalar(value):
    if len(value) >= 2 and value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def parse_flow_map(value):
    inner = value.strip()
    if not (inner.startswith("{") and inner.endswith("}")):
        return {}
    pairs = [item.split(":", 1) for item in inner[1:-1].split(",") if ":" in item]
    return {key.strip(): yaml_scalar(text.strip()) for key, text in pairs}


def parse_yaml_fields(text, strip_quotes):
    rows = tuple(
        (len(line) - len(line.lstrip(" ")), key.strip(), value.strip())
        for line in text.splitlines()
        if ":" in line
        for key, value in (line.split(":", 1),)
    )
    parents = tuple(
        next((key for indent, key, _ in reversed(rows[:index]) if indent == 0), "")
        for index in range(len(rows))
    )
    return {
        (parent + "." + key if indent else key): strip_quotes(value)
        for (indent, key, value), parent in zip(rows, parents)
        if value
    }


def request_digest(request):
    return hashlib.sha256(request.encode("utf-8")).hexdigest()


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text)
    return frozenset(" ".join(part.split()).rstrip(".!?").casefold() for part in parts if part.strip())


def record_path(name):
    return "docs/specs/" + name + ".record.json"


def varies_pattern(kind):
    return '"varies"\\s*:\\s*"' + kind + '"'


def run(command, cwd, env):
    return subprocess.run(command, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=120)


class EvalsVariationTest(unittest.TestCase):
    def assert_case(self, suite, name, kind, fixture):
        evals = load_test_module("test_evals")
        leak = load_test_module("test_evals_leak")
        case = repo_root() / suite / name
        prompt = case / "prompt.md"
        self.assertTrue(prompt.is_file(), str(prompt))
        fields, body = evals.parse_frontmatter(prompt.read_text(encoding="utf-8"))
        self.assertEqual(fields.get("name"), name)
        self.assertTrue(fields.get("description"))
        for key, value in FULL_RUN_SETTINGS.items():
            self.assertEqual(fields.get(key), value, key)
        self.assertEqual(evals.parse_list(fields.get("allowed_tools", "")), FULL_RUN_TOOLS)
        request = leak.request_text(body)
        self.assertEqual(body.strip(), FULL_RUN_PROMPT.format(request, name))
        settings = parse_yaml_fields((case / "case.yaml").read_text(encoding="utf-8"), evals.strip_quotes)
        self.assertEqual(
            settings,
            {"schema_version": "1.1", "name": name, "context.scaffold_script": "scaffold.sh"},
        )
        canonical = repo_root() / suite / "fixtures" / (fixture + ".sh")
        self.assertEqual((case / "scaffold.sh").read_bytes(), canonical.read_bytes())
        self.assert_graders(case / "graders", name, kind, evals.parse_frontmatter)
        return request

    def assert_graders(self, folder, name, kind, parse_frontmatter):
        expected = ["varies.md"] if kind else ["no-varies.md", "spec-written.md"]
        self.assertEqual(sorted(path.name for path in folder.glob("*.md")), expected)
        graders = {
            path.name: parse_frontmatter(path.read_text(encoding="utf-8")) for path in folder.glob("*.md")
        }
        for _, body in graders.values():
            self.assertTrue(body.strip())
        if kind:
            fields, _ = graders["varies.md"]
            self.assertEqual(set(fields), {"type", "target", "pattern"})
            self.assertEqual(fields["type"], "regex")
            self.assertEqual(parse_flow_map(fields["target"]), {"source": "file", "path": record_path(name)})
            self.assertEqual(yaml_scalar(fields["pattern"]), varies_pattern(kind))
            return
        fields, _ = graders["no-varies.md"]
        self.assertEqual(set(fields), {"type", "target", "pattern", "match"})
        self.assertEqual(fields["type"], "regex")
        self.assertEqual(parse_flow_map(fields["target"]), {"source": "file", "path": record_path(name)})
        self.assertEqual(yaml_scalar(fields["pattern"]), '"varies"')
        self.assertEqual(fields["match"], "not_contains")
        fields, _ = graders["spec-written.md"]
        self.assertEqual(fields, {"type": "file_exists", "path": record_path(name), "exists": "true"})

    def assert_fixture_builds(self, script):
        with tempfile.TemporaryDirectory() as folder:
            workspace = pathlib.Path(folder) / "workspace"
            home = pathlib.Path(folder) / "home"
            workspace.mkdir()
            home.mkdir()
            env = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": str(home),
                "TMPDIR": tempfile.gettempdir(),
                "TERM": "dumb",
            }
            built = run(["bash", str(script)], workspace, env)
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue((workspace / ".git").is_dir())
            self.assertEqual(run(["git", "rev-list", "--count", "HEAD"], workspace, env).stdout.strip(), "1")
            author = run(["git", "log", "-1", "--format=%an %ae"], workspace, env).stdout.strip()
            self.assertEqual(author, "fixture fixture@example.com")
            self.assertEqual(run(["git", "status", "--porcelain"], workspace, env).stdout, "")
            readme = (workspace / "README.md").read_text(encoding="utf-8")
            self.assertIn("python3 -m unittest discover tests", readme)
            tests = run([sys.executable, "-m", "unittest", "discover", "tests"], workspace, env)
            self.assertEqual(tests.returncode, 0, tests.stderr)
            ran = re.search(r"Ran (\d+) tests?", tests.stderr)
            self.assertTrue(ran and int(ran.group(1)) > 0, tests.stderr)

    def test_variation_heldout_cases_match_the_spec(self):
        for name, (digest, kind) in HELDOUT_CASES.items():
            with self.subTest(case=name):
                request = self.assert_case("evals-heldout", name, kind, "tasks-app")
                self.assertEqual(request_digest(request), digest, request)
        self.assert_fixture_builds(repo_root() / "evals-heldout" / "fixtures" / "tasks-app.sh")

    def test_variation_dev_cases_cover_every_kind(self):
        self.assertEqual({kind for _, kind in DEV_CASES.values()}, KINDS)
        leak = load_test_module("test_evals_leak")
        evals = load_test_module("test_evals")
        requests = leak.heldout_requests(repo_root(), evals.parse_frontmatter)
        heldout = frozenset().union(*(sentences(text) for text in requests))
        self.assertTrue(heldout)
        for name, (expected, kind) in DEV_CASES.items():
            with self.subTest(case=name):
                request = self.assert_case("evals-dev", name, kind, "notes-app")
                self.assertEqual(request, expected)
                self.assertFalse(sentences(request) & heldout, request)
        self.assert_fixture_builds(repo_root() / "evals-dev" / "fixtures" / "notes-app.sh")


if __name__ == "__main__":
    unittest.main()
