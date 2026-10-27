import pathlib
import unittest

ROUTER = "interphase"
PATHWAYS = ("feature", "bug", "prototype", "project")
DESCRIPTIONS = {
    "feature": "Use when the user wants something that does not exist yet, either a new capability or an extension of an existing one, and its intent, scope and success test are not yet pinned down.",
    "bug": "Use when existing behaviour is wrong and the user wants the cause found or the problem pinned down before anything is changed, such as \"X does Y instead of Z\", \"X stopped working\", \"determine the cause\" or \"why does X\".",
    "prototype": "Use when the user has a design mockup, prototype or exported design, such as HTML, React, Figma frames, a Claude Design export or screenshots, and wants it shipped as a working product.",
    "project": "Use when the user wants to start a new project or repository, or to replace an existing project's stack, build, CI or release, and its foundations, scope and success test are not yet pinned down.",
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


def generic_steps(body, pathway):
    return (
        body.replace("Pathway: " + pathway + ".", "Pathway: <pathway>.")
        .replace("/core/pathways/" + pathway + ".md", "/core/pathways/<pathway>.md")
        .replace("/core/templates/spec-" + pathway + ".md", "/core/templates/spec-<pathway>.md")
    )


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

    def test_pathway_skills_reread_after_a_summary(self):
        step = "6. If this conversation was summarized or cleared during this run, re-read `docs/specs/<slug>.record.json`, `docs/specs/<slug>.decisions.md` and `${CLAUDE_PLUGIN_ROOT}/core/phases.md` before acting."
        for pathway in PATHWAYS:
            with self.subTest(pathway=pathway):
                _, body = split_skill(read_skill(pathway))
                lines = body.splitlines()
                self.assertIn(step, lines)
                fifth = [
                    index for index, line in enumerate(lines)
                    if line.startswith("5. If phase 2 classifies")
                ]
                self.assertEqual(len(fifth), 1)
                self.assertGreater(lines.index(step), fifth[0])

    def test_project_skill_points_to_its_playbook_and_template(self):
        frontmatter, body = split_skill(read_skill("project"))
        self.assertEqual(frontmatter.get("name"), "project")
        self.assertEqual(frontmatter.get("description"), DESCRIPTIONS["project"])
        self.assertEqual(frontmatter.get("argument-hint"), "[what to start or re-platform]")
        lines = body.splitlines()
        for line in (
            "Pathway: project.",
            "3. The playbook is `${CLAUDE_PLUGIN_ROOT}/core/pathways/project.md`.",
            "4. The spec template is `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-project.md`.",
        ):
            self.assertIn(line, lines)
        for relative in ("core/pathways/project.md", "core/templates/spec-project.md"):
            self.assertTrue((repo_root() / relative).is_file(), relative)
        expected = generic_steps(body, "project")
        for pathway in ("feature", "bug", "prototype"):
            with self.subTest(pathway=pathway):
                _, other = split_skill(read_skill(pathway))
                self.assertEqual(expected, generic_steps(other, pathway))

    def test_router_classifies_four_pathways(self):
        _, body = split_skill(read_skill(ROUTER))
        lines = body.splitlines()
        self.assertIn(
            "2. Read `${CLAUDE_PLUGIN_ROOT}/core/phases.md` section \"Phase 2: Classify\". Classify the request as feature, bug, prototype or project.",
            lines,
        )
        self.assertIn(
            "4. Invoke the Skill tool with `interphase:feature`, `interphase:bug`, `interphase:prototype` or `interphase:project`. Pass the request as the arguments. If the Skill tool is unavailable, read `${CLAUDE_PLUGIN_ROOT}/skills/<pathway>/SKILL.md` and follow it.",
            lines,
        )

    def test_metrics_skill_answers_from_the_store(self):
        text = read_skill("metrics")
        frontmatter, body = split_skill(text)
        self.assertEqual(frontmatter.get("name"), "metrics")
        self.assertTrue(frontmatter.get("description"))
        self.assertIn("interphase", frontmatter.get("description", ""))
        self.assertNotIn("disable-model-invocation", frontmatter)
        for needle in (
            "PLUGIN_METRICS_DIR",
            "~/.plugin-metrics",
            "plugin=interphase/catalogue.json",
            "read_json",
            "union_by_name",
            "hive_partitioning",
            "TimeZone",
            "<store>",
            "missing",
            "transcripts",
            "brew install duckdb",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, body)
        self.assertEqual(body.count("```sql"), 1)
        self.assertFalse("mitosis" in text.lower())


if __name__ == "__main__":
    unittest.main()
