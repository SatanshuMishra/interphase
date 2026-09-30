import contextlib
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PHASES = str(ROOT / "core" / "phases.md")
HEADING = "interphase run in progress: "
DECISIONS_TEXT = "# Decisions\n\n- Totals are kept in cents.\n- The report runs nightly.\n"
SECRETS = ("SECRET-ENV", "SECRET-FACT", "SECRET-TEXT", "SECRET-TEST", "SECRET-TASK")


def record(**fields):
    return {"environments": [], "facts": [], "criteria": [], "steps": [], "status": "in-progress", **fields}


def full_record():
    return record(
        environments=[
            {"name": "unit-tests", "what": "SECRET-ENV", "builder_runs": True},
            {"name": "phone", "what": "Galaxy Note10+, Android 12", "builder_runs": False},
        ],
        facts=[{"id": "f1", "fact": "The app returns the total", "path": "src/app.py", "line": 2, "quote": "SECRET-FACT"}],
        criteria=[
            {
                "number": "7.1",
                "title": "Totals add up",
                "text": "SECRET-TEXT",
                "where": ["unit-tests"],
                "tests": [{"file": "tests/test_app.py", "name": "SECRET-TEST", "asserts": "the total", "env": "unit-tests", "step": "build-app"}],
            },
            {
                "number": "7.2",
                "title": "Fast on the phone",
                "text": "The total shows within a second.",
                "where": ["phone"],
                "tests": [],
                "unproven": "needs the phone",
            },
        ],
        steps=[
            {
                "name": "build-app",
                "files": ["src/app.py", "tests/test_app.py"],
                "criteria": ["7.1", "7.2"],
                "task": "SECRET-TASK",
            }
        ],
    )


class ResumeContextTest(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location("resume_context", str(ROOT / "scripts" / "resume_context.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def run_main(self, module, stdin_text):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module.main(stdin_text)
        return code, out.getvalue()

    def session(self, module, folder):
        return self.run_main(module, json.dumps({"cwd": str(folder)}))

    def specs(self, root):
        folder = root / "docs" / "specs"
        folder.mkdir(parents=True)
        return folder

    def write(self, folder, name, content):
        path = folder / name
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
        return path

    def ignore_line(self, folder, slug):
        return (
            "Ignore this unless this conversation is continuing that interphase run. If it is, re-read "
            + str(folder / (slug + ".record.json"))
            + " and "
            + str(folder / (slug + ".decisions.md"))
            + " and "
            + PHASES
            + " before acting."
        )

    def block_for(self, output, slug):
        start = output.index(HEADING + slug + "\n")
        following = output.find("\n" + HEADING, start)
        return output[start:] if following == -1 else output[start:following]

    def test_runs_marked_in_progress_are_reported(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            folder = self.specs(root)
            self.write(folder, "beta.record.json", record())
            self.write(folder, "alpha.record.json", record(
                criteria=[{"number": "7.1", "title": "Totals add up", "text": "The total adds up.", "where": ["unit-tests"], "tests": []}],
                steps=[{"name": "build-app", "files": ["src/app.py"], "criteria": ["7.1"]}],
            ))
            self.write(folder, "alpha.decisions.md", DECISIONS_TEXT)
            code, output = self.session(module, root)
        self.assertEqual(code, 0)
        self.assertIn(HEADING + "alpha", output)
        self.assertLess(output.index(HEADING + "alpha"), output.index(HEADING + "beta"))
        self.assertIn("\n\n" + HEADING + "beta", output)
        self.assertNotIn("\n\n\n" + HEADING + "beta", output)
        self.assertIn(DECISIONS_TEXT, self.block_for(output, "alpha"))
        self.assertIn("No decisions file yet.", self.block_for(output, "beta").splitlines())

    def test_only_the_record_status_decides(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            folder = self.specs(root)
            self.write(folder, "done.record.json", record(status="handed-off"))
            self.write(folder, "old.record.json", {"environments": [], "facts": [], "criteria": [], "steps": []})
            self.write(folder, "guarded.guard.json", {"head": "abc"})
            self.write(folder, "guarded.decisions.md", DECISIONS_TEXT)
            self.write(folder, "lone.items.json", [])
            self.write(folder, "lone.md", "# Lone spec\n")
            self.assertEqual(self.session(module, root), (0, ""))

            done_record = (folder / "done.record.json").stat().st_mtime
            os.utime(self.write(folder, "done.items.json", []), (done_record - 3600, done_record - 3600))
            self.assertEqual(self.session(module, root), (0, ""))

            live_record = self.write(folder, "live.record.json", record()).stat().st_mtime
            os.utime(self.write(folder, "live.items.json", []), (live_record + 3600, live_record + 3600))
            code, output = self.session(module, root)
            self.assertEqual(code, 0)
            self.assertEqual(
                tuple(line for line in output.splitlines() if line.startswith(HEADING)),
                (HEADING + "live",),
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            self.write(self.specs(root), "root-run.record.json", record())
            package = root / "pkg"
            self.write(self.specs(package), "package-run.record.json", record(status="handed-off"))
            code, output = self.session(module, package)
        self.assertEqual(code, 0)
        self.assertEqual(
            tuple(line for line in output.splitlines() if line.startswith(HEADING)),
            (HEADING + "root-run",),
        )

    def test_the_block_carries_decisions_and_the_digest_only(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            folder = self.specs(root)
            self.write(folder, "app.record.json", full_record())
            self.write(folder, "app.decisions.md", DECISIONS_TEXT)
            code, output = self.session(module, root)
        expected = "".join((
            HEADING + "app\n",
            self.ignore_line(folder, "app") + "\n",
            "\n",
            "Decisions (" + str(folder / "app.decisions.md") + "):\n",
            DECISIONS_TEXT,
            "\n",
            "Record digest (" + str(folder / "app.record.json") + "):\n",
            "Criteria:\n",
            "- 7.1 Totals add up (where: unit-tests)\n",
            "- 7.2 Fast on the phone (where: phone) Unproven: needs the phone\n",
            "Steps:\n",
            "- build-app: files src/app.py, tests/test_app.py; criteria 7.1, 7.2\n",
        ))
        self.assertEqual(code, 0)
        self.assertEqual(output, expected)
        for secret in SECRETS:
            self.assertNotIn(secret, output)

    def test_the_run_is_found_from_the_session_folder(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            self.write(self.specs(root), "app.record.json", record())
            nested = root / "app" / "src"
            nested.mkdir(parents=True)
            code, output = self.session(module, nested)
            self.assertEqual(code, 0)
            self.assertIn(HEADING + "app\n", output)

            working = os.getcwd()
            try:
                os.chdir(str(root))
                for stdin_text in ("not json", "{}", "", "[]", json.dumps({"cwd": ""})):
                    with self.subTest(stdin_text=stdin_text):
                        code, output = self.run_main(module, stdin_text)
                        self.assertEqual(code, 0)
                        self.assertIn(HEADING + "app\n", output)
            finally:
                os.chdir(working)

    def test_the_hook_never_disrupts_a_session(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            start = pathlib.Path(tmp).resolve()
            ambient = "\n\n".join(
                text_block
                for folder in module.spec_folders(start)
                for text_block in module.blocks(folder, PHASES)
            )
            self.assertEqual(self.session(module, start), (0, ambient + "\n" if ambient else ""))

        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            folder = self.specs(root)
            self.write(folder, "first.record.json", record(status="handed-off"))
            self.write(folder, "second.record.json", record(status="handed-off"))
            self.assertEqual(self.session(module, root), (0, ""))

            self.write(folder, "broken.record.json", "{not json")
            self.write(folder, "listed.record.json", "[]")
            (folder / "unreadable.decisions.md").write_bytes(b"\xff\xfe- not UTF-8\n")
            self.write(folder, "unreadable.record.json", record())
            code, output = self.session(module, root)
            self.assertEqual(code, 0)
            for slug in ("broken", "listed"):
                with self.subTest(slug=slug):
                    lines = self.block_for(output, slug).splitlines()
                    self.assertEqual(lines[:2], [HEADING + slug, self.ignore_line(folder, slug)])
                    self.assertTrue(any(line.startswith("The record could not be read:") for line in lines), lines)
            self.assertTrue(any(
                line.startswith("The decisions file could not be read:")
                for line in self.block_for(output, "unreadable").splitlines()
            ))

            self.assertEqual(self.session(module, root / "missing"), (0, ""))

            working = os.getcwd()
            stdin = sys.stdin

            class Unreadable:
                def read(self):
                    raise OSError("standard input is closed")

            try:
                os.chdir(str(root))
                sys.stdin = Unreadable()
                code, output = self.run_main(module, None)
            finally:
                sys.stdin = stdin
                os.chdir(working)
            self.assertEqual(code, 0)
            self.assertIn(HEADING + "broken\n", output)

    def test_a_partly_written_record_still_prints(self):
        module = self.load()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            folder = self.specs(root)
            self.write(folder, "partial.record.json", {
                "status": "in-progress",
                "criteria": [
                    {"number": "7.1", "title": "No where"},
                    {"number": 7.2, "title": "Numeric", "where": ["unit-tests"]},
                    {"number": "7.3", "title": None, "where": [], "unproven": None},
                    "junk",
                ],
            })
            code, output = self.session(module, root)
        self.assertEqual(code, 0)
        lines = output.splitlines()
        self.assertEqual(
            lines[lines.index("Record digest (" + str(folder / "partial.record.json") + "):") + 1:],
            [
                "Criteria:",
                "- 7.1 No where (where: )",
                "- 7.2 Numeric (where: unit-tests)",
                "- 7.3  (where: )",
                "Steps:",
            ],
        )


if __name__ == "__main__":
    unittest.main()
