import importlib.util
import pathlib
import tempfile
import unittest

REPLAY_WORDS = (
    "next_step_records",
    "run.zsh",
    "claude_project_dir",
    "installed_plugins",
    "option_reasons",
    "compaction",
    "logbook",
    "selectmanifestentry",
    "rename detection",
    "step record",
    "compact briefing",
    "sessionstart",
    "precompact",
)


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def load_leak_module():
    path = pathlib.Path(__file__).resolve().parent / "test_evals_leak.py"
    spec = importlib.util.spec_from_file_location("test_evals_leak", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def files_to_scan(root):
    leak = load_leak_module()
    scripts = root / "scripts"
    script_files = (
        tuple(
            path
            for path in sorted(scripts.rglob("*"))
            if path.is_file() and "__pycache__" not in path.relative_to(root).parts
        )
        if scripts.is_dir()
        else ()
    )
    return tuple(leak.scanned_files(root)) + script_files


def scan(root):
    leak = load_leak_module()
    read = files_to_scan(root)
    found = {}
    for path in read:
        text = leak.normalized(path.read_text(encoding="utf-8", errors="replace"))
        words = tuple(word for word in REPLAY_WORDS if word.casefold() in text)
        if words:
            found[path.relative_to(root).as_posix()] = words
    return found, tuple(path.relative_to(root).as_posix() for path in read)


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class ReplayLeakTest(unittest.TestCase):
    def test_rules_name_no_replay_case(self):
        found, read = scan(repo_root())
        report = "; ".join(path + ": " + ", ".join(words) for path, words in sorted(found.items()))
        self.assertEqual(found, {}, report)
        for folder in ("core/", "skills/", "agents/", "scripts/"):
            self.assertTrue(any(name.startswith(folder) for name in read), folder)
        self.assertIn("README.md", read)

    def test_scan_reads_undecodable_bytes_and_skips_bytecode(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            write_bytes(root / "scripts" / "blob.bin", b"\xff\xfe" + b"compaction")
            write_bytes(root / "scripts" / "__pycache__" / "tool.cpython-39.pyc", b"compaction")
            found, read = scan(root)
        self.assertEqual(found, {"scripts/blob.bin": ("compaction",)})
        self.assertIn("scripts/blob.bin", read)
        self.assertEqual(tuple(name for name in read if "__pycache__" in name), ())

    def test_scan_finds_a_planted_word(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            write_bytes(root / "core" / "rules.md", b"Keep the Compaction notes short.")
            write_bytes(root / "scripts" / "tool.py", b"print(1)")
            found, read = scan(root)
        self.assertEqual(found, {"core/rules.md": ("compaction",)})
        self.assertIn("scripts/tool.py", read)


if __name__ == "__main__":
    unittest.main()
