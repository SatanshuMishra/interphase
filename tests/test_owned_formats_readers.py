import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

H11_FILE = "h11-interphase-record.schema.json"
READ_BACK_HEADING = "How we will know it works"
RESUME_HEADING = "interphase run in progress: "
UNREADABLE = "The record could not be read:"
DECISION = "- Totals are kept in cents."
PARTIAL_RECORD = {
    "status": "in-progress",
    "seams": [],
    "steps": [],
    "criteria": [{"number": 5.1, "title": "No seam"}, "junk"],
}
WHOLE_RECORD = {"status": "in-progress", "seams": [], "criteria": [], "steps": []}
DONE_RECORD = {"status": "handed-off", "criteria": ["junk"]}


def repository_root():
    return pathlib.Path(__file__).resolve().parents[1]


def load_path(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixtures():
    tests = repository_root() / "tests"
    lane = load_path("owned_formats_readers_lane", tests / "test_check_author_lane.py")
    kinds = load_path("owned_formats_readers_kinds", tests / "test_outcome_kinds.py")
    return lane.complete_record(), kinds.SPEC_WITHOUT_KIND


def environment(home):
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "RECEIPTS_", "XDG_"))
    }
    return {**kept, "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1"}


def script_path(name):
    return repository_root() / "scripts" / name


def run(arguments, cwd, home, stdin_text=None):
    closed = {"stdin": subprocess.DEVNULL} if stdin_text is None else {"input": stdin_text}
    return subprocess.run(
        [sys.executable] + [str(argument) for argument in arguments],
        cwd=str(cwd),
        env=environment(home),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **closed,
    )


def output_of(result):
    return result.stdout + result.stderr


def without_seam_interface(record):
    seams = record["seams"]
    first = {key: value for key, value in seams[0].items() if key != "interface"}
    return {**record, "seams": [first] + list(seams[1:])}


def with_numeric_second_number(record):
    criteria = record["criteria"]
    return {**record, "criteria": [criteria[0], {**criteria[1], "number": 5.2}] + list(criteria[2:])}


def with_first_line_kind(record, kind):
    criteria = record["criteria"]
    first = criteria[0]
    line = {**first["acceptance"][0], "kind": kind}
    return {
        **record,
        "criteria": [{**first, "acceptance": [line] + list(first["acceptance"][1:])}] + list(criteria[1:]),
    }


def resume_blocks(text):
    starts = tuple(
        position for position, line in enumerate(text.splitlines()) if line.startswith(RESUME_HEADING)
    )
    lines = text.splitlines()
    ends = starts[1:] + (len(lines),)
    return {lines[start][len(RESUME_HEADING) :]: lines[start:end] for start, end in zip(starts, ends)}


def first_index(lines, predicate):
    return next((position for position, line in enumerate(lines) if predicate(line)), None)


class ReadBackRefusalTest(unittest.TestCase):
    def test_read_back_refuses_a_record_that_fails_h11(self):
        record, spec_text = fixtures()
        copies = (
            ("seam.record.json", without_seam_interface(record), "#/seams/0"),
            ("number.record.json", with_numeric_second_number(record), "#/criteria/1/number"),
            ("kind.record.json", with_first_line_kind(record, "fuzzy"), "#/criteria/0/acceptance/0/kind"),
        )
        with tempfile.TemporaryDirectory() as base:
            folder = pathlib.Path(base).resolve()
            home = folder / "home"
            home.mkdir()
            (folder / "demo.md").write_text(spec_text, encoding="utf-8")
            record_path = folder / "demo.record.json"
            record_path.write_text(json.dumps(record), encoding="utf-8")
            result = run([script_path("read_back.py"), "--record", record_path], folder, home)
            self.assertEqual(result.returncode, 0, output_of(result))
            self.assertIn(READ_BACK_HEADING, result.stdout.splitlines(), output_of(result))
            for name, copy, pointer in copies:
                with self.subTest(copy=name):
                    path = folder / name
                    path.write_text(json.dumps(copy), encoding="utf-8")
                    result = run([script_path("read_back.py"), "--record", path], folder, home)
                    self.assertEqual(result.returncode, 1, output_of(result))
                    self.assertEqual(result.stdout, "", output_of(result))
                    naming = [
                        line
                        for line in result.stderr.splitlines()
                        if str(path) in line and H11_FILE in line and pointer in line
                    ]
                    self.assertNotEqual(naming, [], output_of(result))


class ResumeContextRefusalTest(unittest.TestCase):
    def test_an_in_progress_record_that_fails_h11_is_refused_not_digested(self):
        with tempfile.TemporaryDirectory() as base:
            root = pathlib.Path(base).resolve()
            home = root / "home"
            home.mkdir()
            specs = root / "docs" / "specs"
            specs.mkdir(parents=True)
            (specs / "partial.record.json").write_text(json.dumps(PARTIAL_RECORD), encoding="utf-8")
            (specs / "partial.decisions.md").write_text(DECISION + "\n", encoding="utf-8")
            (specs / "whole.record.json").write_text(json.dumps(WHOLE_RECORD), encoding="utf-8")
            (specs / "done.record.json").write_text(json.dumps(DONE_RECORD), encoding="utf-8")
            (specs / "broken.record.json").write_text("{not json", encoding="utf-8")
            (specs / "listed.record.json").write_text("[]", encoding="utf-8")
            result = run(
                [script_path("resume_context.py")], root, home, stdin_text=json.dumps({"cwd": str(root)})
            )
            partial_path = str(specs / "partial.record.json")
        output = output_of(result)
        self.assertEqual(result.returncode, 0, output)
        blocks = resume_blocks(result.stdout)
        self.assertNotIn("done", blocks, output)
        self.assertEqual(sorted(blocks), ["broken", "listed", "partial", "whole"], output)
        partial = blocks["partial"]
        self.assertEqual(partial[0], RESUME_HEADING + "partial", output)
        reread = first_index(partial, lambda line: "re-read" in line and partial_path in line)
        decision = first_index(partial, lambda line: line == DECISION)
        refusal = first_index(partial, lambda line: "partial.record.json" in line and H11_FILE in line)
        required = first_index(partial, lambda line: "#/criteria/0 required" in line)
        typed = first_index(partial, lambda line: "#/criteria/1 type" in line)
        positions = (reread, decision, refusal, required, typed)
        self.assertNotIn(None, positions, output)
        self.assertLess(reread, decision, output)
        self.assertLess(decision, refusal, output)
        self.assertLess(refusal, required, output)
        self.assertLess(refusal, typed, output)
        self.assertEqual([line for line in partial if line.strip() in ("Criteria:", "Steps:")], [], output)
        whole = [line.strip() for line in blocks["whole"]]
        self.assertIn("Criteria:", whole, output)
        self.assertIn("Steps:", whole, output)
        for slug in ("broken", "listed"):
            with self.subTest(block=slug):
                lines = blocks[slug]
                self.assertNotEqual([line for line in lines if line.startswith(UNREADABLE)], [], output)
                self.assertEqual([line for line in lines if H11_FILE in line], [], output)


if __name__ == "__main__":
    unittest.main()
