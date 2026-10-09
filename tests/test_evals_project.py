import importlib.util
import os
import pathlib
import tempfile
import unittest

CASE_PREFIX = "routing-"
DEV_CASE = "new-project-starts-project-pathway"
PROJECT_SKILL = "interphase:project"
ROUTING_FIELDS = {"runs": "3", "max_turns": "3"}
ROUTING_TOOLS = ["Skill", "Read", "Glob", "Grep"]
EMPTY_FIXTURE = "empty-repo"
STARTED = {"min": "1"}
NEVER_STARTED = {"min": "0", "max": "0"}

HELDOUT_CASES = {
    "routing-habit-tracker-from-scratch": (
        "fe22ea6434e6773ed626fa51ed6999720ab558196f42e69ccb4fadd311390458",
        "empty-repo",
        STARTED,
    ),
    "routing-electron-to-tauri": (
        "847c4c5ea6634a5e6d9dd512fccb4eafae8e2c2ce8804b945dae35bc657ac7f7",
        "electron-app",
        STARTED,
    ),
    "routing-notes-backup-cli": (
        "988b1c82184125d2b4b920d82d2e87d03aed86bbc94b3980e86f244e95f13d3c",
        "empty-repo",
        STARTED,
    ),
    "routing-settings-dark-mode": (
        "7d8d946947e2592fd7e98be4b6fca701f215125444b65ab8be84399a9082680b",
        "invoices-app",
        NEVER_STARTED,
    ),
    "routing-invoices-csv-export": (
        "e4d28f9466c75de69c1a49633c72759d5eb7f782e36802b6a57084e897f1ab07",
        "invoices-app",
        NEVER_STARTED,
    ),
}

FIXTURE_FILES = {
    "electron-app": {
        "README.md": ("# Focus Timer", "built with Electron", "python3 -m unittest discover tests"),
        "package.json": ('"electron":', '"electron-builder":'),
        "main.js": ("BrowserWindow",),
        ".github/workflows/release.yml": ("electron-builder",),
    },
    "invoices-app": {
        "README.md": ("# Invoices", "The invoices page", "The settings screen", "python3 -m unittest discover tests"),
        "invoices/views.py": ("def render_invoices", "def render_settings"),
        "invoices/server.py": ('"/invoices"', '"/settings"'),
    },
}


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def load_test_module(name):
    path = pathlib.Path(__file__).resolve().parent / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_helpers():
    return tuple(load_test_module(name) for name in ("test_evals", "test_evals_leak", "test_evals_variation"))


def case_names(suite):
    folder = repo_root() / suite
    return sorted(path.name for path in folder.iterdir() if path.is_dir() and path.name.startswith(CASE_PREFIX))


def fixture_script(fixture):
    return repo_root() / "evals-heldout" / "fixtures" / (fixture + ".sh")


def expected_grader(bounds):
    return dict({"type": "tool_used", "tool": "Skill", "input_match": PROJECT_SKILL, "arm": "both"}, **bounds)


def fixture_env(home):
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "TMPDIR": tempfile.gettempdir(),
        "TERM": "dumb",
    }


class EvalsProjectTest(unittest.TestCase):
    def assert_case(self, helpers, name, digest, fixture, bounds):
        evals, _, variation = helpers
        case = repo_root() / "evals-heldout" / name
        prompt = case / "prompt.md"
        self.assertTrue(prompt.is_file(), str(prompt))
        fields, body = evals.parse_frontmatter(prompt.read_text(encoding="utf-8"))
        self.assertEqual(set(fields), {"name", "description", "runs", "max_turns", "allowed_tools"})
        self.assertEqual(fields.get("name"), name)
        self.assertTrue(fields.get("description"))
        for key, value in ROUTING_FIELDS.items():
            self.assertEqual(fields.get(key), value, key)
        self.assertEqual(evals.parse_list(fields.get("allowed_tools", "")), ROUTING_TOOLS)
        self.assertEqual(variation.request_digest(body.strip()), digest, body.strip())
        settings = variation.parse_yaml_fields((case / "case.yaml").read_text(encoding="utf-8"), evals.strip_quotes)
        self.assertEqual(
            settings,
            {"schema_version": "1.1", "name": name, "context.scaffold_script": "scaffold.sh"},
        )
        self.assertEqual((case / "scaffold.sh").read_bytes(), fixture_script(fixture).read_bytes())
        self.assert_grader(helpers, case / "graders", bounds)

    def assert_grader(self, helpers, folder, bounds):
        evals, _, variation = helpers
        self.assertEqual(sorted(path.name for path in folder.glob("*.md")), ["skill-fired.md"])
        fields, body = evals.parse_frontmatter((folder / "skill-fired.md").read_text(encoding="utf-8"))
        self.assertEqual(fields, expected_grader(bounds))
        self.assertTrue(body.strip().startswith("Passes when"), body)
        self.assertEqual(len(variation.sentences(body)), 1, body)

    def build(self, variation, script, folder):
        workspace = folder / "workspace"
        home = folder / "home"
        workspace.mkdir()
        home.mkdir()
        env = fixture_env(home)
        built = variation.run(["bash", str(script)], workspace, env)
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertTrue((workspace / ".git").is_dir())
        self.assertEqual(variation.run(["git", "rev-list", "--count", "HEAD"], workspace, env).stdout.strip(), "1")
        self.assertEqual(variation.run(["git", "status", "--porcelain"], workspace, env).stdout, "")
        committed = variation.run(["git", "ls-tree", "-r", "--name-only", "HEAD"], workspace, env).stdout
        return workspace, env, committed.splitlines()

    def assert_empty_repo(self, variation, script):
        with tempfile.TemporaryDirectory() as folder:
            workspace, env, committed = self.build(variation, script, pathlib.Path(folder))
            self.assertEqual(committed, ["README.md"])
            self.assertEqual(variation.run(["git", "cat-file", "-s", "HEAD:README.md"], workspace, env).stdout.strip(), "0")
            self.assertEqual(sorted(path.name for path in workspace.iterdir()), [".git", "README.md"])

    def assert_app_fixture(self, variation, script, files):
        variation.EvalsVariationTest.assert_fixture_builds(self, script)
        with tempfile.TemporaryDirectory() as folder:
            workspace, _, committed = self.build(variation, script, pathlib.Path(folder))
            for path, markers in files.items():
                with self.subTest(file=path):
                    self.assertIn(path, committed)
                    text = (workspace / path).read_text(encoding="utf-8")
                    for marker in markers:
                        self.assertIn(marker, text)

    def test_routing_heldout_cases_match_the_spec(self):
        helpers = load_helpers()
        variation = helpers[2]
        self.assertEqual(case_names("evals-heldout"), sorted(HELDOUT_CASES))
        for name, (digest, fixture, bounds) in HELDOUT_CASES.items():
            with self.subTest(case=name):
                self.assert_case(helpers, name, digest, fixture, bounds)
        for fixture in sorted({fixture for _, fixture, _ in HELDOUT_CASES.values()}):
            with self.subTest(fixture=fixture):
                if fixture == EMPTY_FIXTURE:
                    self.assert_empty_repo(variation, fixture_script(fixture))
                else:
                    self.assert_app_fixture(variation, fixture_script(fixture), FIXTURE_FILES[fixture])

    def test_routing_dev_case_shares_no_heldout_sentence(self):
        evals, leak, variation = load_helpers()
        self.assertEqual(evals.CASES[DEV_CASE][1], PROJECT_SKILL)
        requests = leak.heldout_requests(repo_root(), evals.parse_frontmatter)
        heldout = frozenset().union(*(variation.sentences(text) for text in requests))
        self.assertTrue(heldout)
        prompt = repo_root() / "evals" / DEV_CASE / "prompt.md"
        self.assertTrue(prompt.is_file(), str(prompt))
        request = leak.request_text(evals.parse_frontmatter(prompt.read_text(encoding="utf-8"))[1])
        self.assertTrue(request)
        self.assertFalse(variation.sentences(request) & heldout, request)


if __name__ == "__main__":
    unittest.main()
