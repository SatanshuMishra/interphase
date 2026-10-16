import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "core" / "pathways" / "project.md"
TEMPLATE = ROOT / "core" / "templates" / "spec-project.md"
SKILL = ROOT / "skills" / "project" / "SKILL.md"

PLAYBOOK_HEADINGS = (
    "## Ground",
    "## Questions",
    "## Extra step",
    "## Acceptance",
    "## Steps",
)


FOUNDATIONS = (
    ("proof of concept", "product"),
    ("definition of done", "first usable version"),
    ("platforms", "minimum versions", "hardware"),
    ("stack", "alternatives"),
    ("dependencies", "versions", "pinned"),
    ("build tooling",),
    ("each kind of behaviour", "tested", "`${CLAUDE_PLUGIN_ROOT}/core/variation.md`"),
    ("CI",),
    ("packaging", "signing", "distribution", "size"),
    ("configuration", "secrets"),
    ("licence", "third-party attribution"),
    ("log", "diagnostics"),
    ("repository layout",),
)



def load(relative):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_lines(path):
    return tuple(path.read_text(encoding="utf-8").splitlines())


def sections_by_heading(lines):
    starts = tuple(i for i, line in enumerate(lines) if line.startswith("## "))
    ends = starts[1:] + (len(lines),)
    return {lines[s]: tuple(lines[s + 1:e]) for s, e in zip(starts, ends)}


def bullets(section):
    return tuple(line for line in section if line.startswith("- "))




def first_match(lines, words):
    matches = tuple(index for index, line in enumerate(lines) if all(word in line for word in words))
    return matches[0] if matches else None


class PathwayProjectTest(unittest.TestCase):
    def test_project_playbook_has_every_section(self):
        lines = read_lines(PLAYBOOK)
        self.assertEqual(lines[0], "# Project playbook")
        found = tuple(line for line in lines if line.startswith("## "))
        self.assertEqual(found, PLAYBOOK_HEADINGS)

    def test_project_ground_researches_the_domain_and_current_stacks(self):
        ground = "\n".join(sections_by_heading(read_lines(PLAYBOOK))["## Ground"])
        for needle in (
            "domain",
            "users",
            "at stake",
            "For a re-platform, read the existing code, build, CI, release and written rules",
            "`interphase:scout` agent",
            "`${CLAUDE_PLUGIN_ROOT}/core/practices.md`",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, ground)

    def test_project_questions_cover_every_foundation(self):
        questions = bullets(sections_by_heading(read_lines(PLAYBOOK))["## Questions"])
        matched = tuple(first_match(questions, words) for words in FOUNDATIONS)
        for words, index in zip(FOUNDATIONS, matched):
            with self.subTest(foundation=words):
                self.assertIsNotNone(index)
        self.assertEqual(len(frozenset(matched)), len(FOUNDATIONS))

    def test_project_extra_step_lets_the_user_choose_a_stack(self):
        extra = "\n".join(sections_by_heading(read_lines(PLAYBOOK))["## Extra step"])
        for needle in (
            "Propose two or three stacks with their trade-offs as one frontier question, the recommended one first.",
            "decisions file",
            "the spec's Decisions section",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, extra)

    def test_project_acceptance_covers_the_foundations_and_variation(self):
        acceptance = "\n".join(sections_by_heading(read_lines(PLAYBOOK))["## Acceptance"])
        for needle in (
            "Given, When, Then",
            "WHEN <event>, THE SYSTEM SHALL <response>",
            "pass or fail with no judgement call",
            "Number each criterion under the Test seams section, such as `5.1`, and place it at an agreed seam.",
            "the build producing a release artifact and CI running the tests",
            "`${CLAUDE_PLUGIN_ROOT}/core/variation.md`",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, acceptance)

    def test_project_steps_start_with_a_walking_skeleton(self):
        steps = sections_by_heading(read_lines(PLAYBOOK))["## Steps"]
        text = "\n".join(steps)
        self.assertIn("Design the Steps during the interview", text)
        self.assertIn('the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`', text)
        skeleton = "- The first Step builds a walking skeleton: the repository, the build, CI, the test harness and one thin path that runs end to end."
        slices = "- Every later Step comes after the walking skeleton and adds a slice that runs end to end."
        layers = "- Never build a layer that cannot run until a later Step."
        for line in (skeleton, slices, layers):
            with self.subTest(line=line):
                self.assertIn(line, steps)
        self.assertLess(steps.index(skeleton), steps.index(slices))

    def test_project_names_no_consuming_tool(self):
        names = load("tests/test_hooks.py").consumer_names()
        self.assertEqual(len(names), 1, names)
        for path in (PLAYBOOK, TEMPLATE, SKILL):
            with self.subTest(path=path.name):
                self.assertNotIn(names[0], path.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
