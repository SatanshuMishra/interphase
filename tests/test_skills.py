import pathlib
import unittest

ROUTER = "interphase"
PATHWAYS = ("feature", "bug", "prototype")
DESCRIPTIONS = {
    "feature": "Use when the user wants something that does not exist yet, either a new capability or an extension of an existing one, and its intent, scope and success test are not yet pinned down.",
    "bug": "Use when existing behaviour is wrong and the user wants the cause found or the problem pinned down before anything is changed, such as \"X does Y instead of Z\", \"X stopped working\", \"determine the cause\" or \"why does X\".",
    "prototype": "Use when the user has a design mockup, prototype or exported design, such as HTML, React, Figma frames, a Claude Design export or screenshots, and wants it shipped as a working product.",
}


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def read_skill(name):
    return (repo_root() / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def strip_quotes(value):
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def split_skill(text):
    lines = text.splitlines()
    fences = [index for index, line in enumerate(lines) if line == "---"][:2]
    if len(fences) < 2:
        return {}, text
    pairs = tuple(
        line.split(":", 1)
        for line in lines[fences[0] + 1:fences[1]]
        if ":" in line
    )
    frontmatter = {key.strip(): strip_quotes(value.strip()) for key, value in pairs}
    body = "\n".join(lines[fences[1] + 1:])
    return frontmatter, body


class SkillsTest(unittest.TestCase):
    def test_router_runs_only_when_typed(self):
        frontmatter, body = split_skill(read_skill(ROUTER))
        self.assertEqual(frontmatter.get("name"), "interphase")
        self.assertEqual(frontmatter.get("disable-model-invocation"), "true")
        self.assertTrue(frontmatter.get("argument-hint"))
        for needle in (
            "interphase:feature",
            "interphase:bug",
            "interphase:prototype",
            "${CLAUDE_PLUGIN_ROOT}/core/phases.md",
        ):
            self.assertIn(needle, body)

    def test_pathway_skills_can_start_automatically(self):
        for pathway in PATHWAYS:
            with self.subTest(pathway=pathway):
                frontmatter, _ = split_skill(read_skill(pathway))
                description = frontmatter.get("description", "")
                self.assertEqual(frontmatter.get("name"), pathway)
                self.assertNotIn("disable-model-invocation", frontmatter)
                self.assertEqual(description, DESCRIPTIONS[pathway])
                self.assertTrue(description.startswith("Use when"))
                self.assertLessEqual(len(description), 1024)

    def test_pathway_skills_point_at_their_core_files(self):
        for pathway in PATHWAYS:
            with self.subTest(pathway=pathway):
                _, body = split_skill(read_skill(pathway))
                for needle in (
                    "${CLAUDE_PLUGIN_ROOT}/core/phases.md",
                    "${CLAUDE_PLUGIN_ROOT}/core/pathways/" + pathway + ".md",
                    "${CLAUDE_PLUGIN_ROOT}/core/templates/spec-" + pathway + ".md",
                ):
                    self.assertIn(needle, body)
        for name in (ROUTER,) + PATHWAYS:
            with self.subTest(skill=name):
                text = read_skill(name)
                self.assertLess(len(text.splitlines()), 80)
                self.assertNotIn("mitosis", text.lower())


if __name__ == "__main__":
    unittest.main()
