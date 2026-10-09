import importlib.util
import pathlib
import tempfile
import unittest

FULL_RUN_PREFIX = "Use interphase to write a spec for this request, and stop at hand-off: "
FULL_RUN_SUFFIX = " Work autonomously."
SCANNED_FOLDERS = ("core", "skills", "agents", "evals", "evals-dev")
SCANNED_FILES = ("README.md",)


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def load_test_module(name):
    path = pathlib.Path(__file__).resolve().parent / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def without_prefix(text, prefix):
    return text[len(prefix):] if text.startswith(prefix) else text


def request_text(body):
    request = without_prefix(body.strip(), FULL_RUN_PREFIX).split(FULL_RUN_SUFFIX, 1)[0].strip()
    return request[:-1].rstrip() if request.endswith(".") else request


def heldout_requests(root, parse_frontmatter):
    prompts = sorted((root / "evals-heldout").glob("*/prompt.md"))
    requests = (request_text(parse_frontmatter(path.read_text(encoding="utf-8"))[1]) for path in prompts)
    return tuple(request for request in requests if request)


def normalized(text):
    return " ".join(text.split()).casefold()


def scanned_files(root):
    folders = tuple(root / name for name in SCANNED_FOLDERS)
    nested = tuple(path for folder in folders if folder.is_dir() for path in sorted(folder.rglob("*")))
    singles = tuple(root / name for name in SCANNED_FILES)
    return tuple(path for path in nested + singles if path.is_file())


def leaked_files(root):
    parse_frontmatter = load_test_module("test_evals").parse_frontmatter
    needles = tuple(normalized(request) for request in heldout_requests(root, parse_frontmatter))
    return tuple(
        path.relative_to(root).as_posix()
        for path in scanned_files(root)
        if any(needle in normalized(path.read_text(encoding="utf-8", errors="replace")) for needle in needles)
    )


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class EvalsLeakTest(unittest.TestCase):
    def build_tree(self, root):
        write(
            root / "evals-heldout" / "chores-archive" / "prompt.md",
            "---\nname: chores-archive\nruns: 3\n---\n\n"
            + FULL_RUN_PREFIX
            + "Archive every finished chore a week after it is done. Work autonomously. Name the spec chores-archive.\n",
        )
        write(root / "evals-heldout" / "chores-by-room" / "prompt.md", "Sort the chore list by room, then by due date.\n")
        write(root / "evals-heldout" / "fixtures" / "chores.sh", "Archive every finished chore a week after it is done.\n")
        write(root / "core" / "rules.md", "Treat `ARCHIVE EVERY FINISHED CHORE A WEEK AFTER IT IS DONE` as one change.\n")
        write(root / "core" / "phases.md", "Archive finished chores when the user asks.\n")
        write(root / "evals-dev" / "chores-dev" / "prompt.md", "Please sort the chore\nlist by room, then by due date, today.\n")
        write(root / "skills" / "chores" / "SKILL.md", "Use when the user wants chores sorted.\n")
        write(root / "tests" / "test_chores.py", "Archive every finished chore a week after it is done.\n")
        write(root / "README.md", "# Chores\n")
        return root

    def test_no_heldout_request_appears_outside_the_heldout_suite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.build_tree(pathlib.Path(folder))
            self.assertEqual(leaked_files(root), ("core/rules.md", "evals-dev/chores-dev/prompt.md"))
        root = repo_root()
        parse_frontmatter = load_test_module("test_evals").parse_frontmatter
        self.assertTrue(heldout_requests(root, parse_frontmatter))
        self.assertEqual(leaked_files(root), ())

    def test_request_text_drops_frontmatter_prefix_suffix_and_full_stop(self):
        parse_frontmatter = load_test_module("test_evals").parse_frontmatter
        full_run = "---\nname: case\n---\n\n" + FULL_RUN_PREFIX + "Do the thing. Work autonomously. Name the spec case.\n"
        self.assertEqual(request_text(parse_frontmatter(full_run)[1]), "Do the thing")
        self.assertEqual(request_text(parse_frontmatter("  Do the other thing.  \n")[1]), "Do the other thing")


if __name__ == "__main__":
    unittest.main()
