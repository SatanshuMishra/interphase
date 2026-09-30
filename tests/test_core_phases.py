import pathlib
import unittest

HEADINGS = (
    "## Phase 1: Intake",
    "## Phase 2: Classify",
    "## Phase 3: Ground",
    "## Phase 4: Interrogate",
    "## Phase 5: Challenge",
    "## Phase 6: Design the Steps",
    "## Phase 7: Read back",
    "## Phase 8: Write the spec and the Steps",
    "## Phase 9: Review",
    "## Phase 10: Hand off",
)

RULES = (
    "Never create, edit or delete a file in the user's working tree, except interphase's own output files in the spec folder.",
    "Never commit, push, stash, reset, check out or rebase in the user's repository.",
    "Never implement: the spec states the cause, the boundary and the acceptance test, never the patch.",
    "Look up facts yourself; ask the user only for decisions.",
    "Never answer your own decision question; recommend an answer and wait for the user's explicit yes.",
    "Write every default you choose into the spec as an assumption.",
    "Save each answer to the decisions file the moment it is given.",
    "Silence, \"just do it\", and your own judgement that the spec is fine are not approval.",
    "Only the main conversation talks to the user; agents never ask the user anything.",
    "Never name, detect or invoke any tool that might consume the spec.",
    "After the user approves the spec and the Steps, change neither without asking for approval again.",
    "Never comment on, ask about or offer to change whether git tracks interphase's own output files, in anything you say or ask, or in the spec, decisions or items files.",
    "Never plan a copy of logic that already exists, and never bend existing code to fit a new use; follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md`.",
    "Keep the interview in the record: write each environment, fact, criterion and Step to `docs/specs/<slug>.record.json` the moment it is found or settled, and after any summary of the conversation, re-read the record and the decisions file before acting.",
)

STEP_FILES = ("core/phases.md",)


def repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def read_phases():
    return (repo_root() / "core" / "phases.md").read_text(encoding="utf-8")


def phase_body(heading):
    lines = read_phases().splitlines()
    start = lines.index(heading) + 1
    end = start
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    return "\n".join(lines[start:end])


class CorePhasesTest(unittest.TestCase):
    def test_phases_lists_all_ten_phases_in_order(self):
        lines = read_phases().splitlines()
        positions = tuple(
            lines.index(heading) if heading in lines else -1 for heading in HEADINGS
        )
        self.assertNotIn(-1, positions)
        self.assertEqual(list(positions), sorted(positions))

    def test_phases_states_every_rule_verbatim(self):
        text = read_phases()
        lines = text.splitlines()
        self.assertIn("## Rules", lines)
        self.assertIn(HEADINGS[0], lines)
        rules_line = lines.index("## Rules")
        self.assertLess(rules_line, lines.index(HEADINGS[0]))
        rules_block = "\n".join(lines[rules_line:lines.index(HEADINGS[0])])
        positions = tuple(
            rules_block.find(f"{number}. {rule}")
            for number, rule in enumerate(RULES, start=1)
        )
        self.assertNotIn(-1, positions)
        self.assertEqual(list(positions), sorted(positions))
        for relative in STEP_FILES:
            content = (repo_root() / relative).read_text(encoding="utf-8")
            self.assertNotIn("mitosis", content.lower(), relative)

    def test_phases_never_mention_ignoring_the_spec_folder(self):
        text = read_phases().lower()
        for phrase in ("gitignore", "info/exclude", "check-ignore", "ignored"):
            self.assertNotIn(phrase, text)

    def test_phases_design_steps_before_the_read_back(self):
        self.assertIn(
            "every acceptance criterion has a Step whose test proves it",
            phase_body("## Phase 6: Design the Steps"),
        )
        self.assertIn("How the work is cut", phase_body("## Phase 7: Read back"))
        self.assertIn(
            "Never derive the Steps by reading them back out of the spec.",
            phase_body("## Phase 8: Write the spec and the Steps"),
        )

    def test_phases_pass_the_owned_prefix_to_the_guard(self):
        text = read_phases()
        self.assertIn(
            'snapshot --repo . --owned "docs/specs/<slug>." --out docs/specs/<slug>.guard.json',
            text,
        )

    def test_phases_go_straight_from_approval_to_hand_off(self):
        review_body = phase_body("## Phase 9: Review")
        self.assertIn(
            "Once the user approves, change neither the spec nor the items file.",
            review_body,
        )
        self.assertIn(
            "then go straight to Phase 10 in the same turn.",
            review_body,
        )
        self.assertIn("reopen this phase", review_body)
        write_body = phase_body("## Phase 8: Write the spec and the Steps")
        self.assertIn(
            "After any edit to the spec, rewrite `source.sha256`.",
            write_body,
        )
        self.assertNotIn("After any later edit", read_phases())

    def test_phases_say_the_guard_removes_new_caches(self):
        self.assertIn(
            "The guard first removes the caches that running the project's code created since the snapshot.",
            phase_body("## Phase 10: Hand off"),
        )

    def test_phases_apply_the_practices(self):
        self.assertIn(
            "Follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md` to find what already exists and the project's own written rules.",
            phase_body("## Phase 3: Ground"),
        )
        review_body = phase_body("## Phase 9: Review")
        self.assertIn("the decisions path", review_body)
        self.assertIn("the path of `${CLAUDE_PLUGIN_ROOT}/core/practices.md`", review_body)

    def test_phases_keep_the_interview_in_the_record(self):
        self.assertIn(
            "Create `docs/specs/<slug>.record.json`",
            phase_body("## Phase 1: Intake"),
        )
        interrogate = phase_body("## Phase 4: Interrogate")
        for phrase in (
            "After every question round, run",
            "scripts/check_record.py",
            "Fix every error before the next round.",
        ):
            self.assertIn(phrase, interrogate)
        self.assertIn(
            "--complete docs/specs/<slug>.record.json",
            phase_body("## Phase 6: Design the Steps"),
        )
        write_body = phase_body("## Phase 8: Write the spec and the Steps")
        for phrase in (
            "Fill every section except Acceptance criteria.",
            "scripts/render_record.py",
        ):
            self.assertIn(phrase, write_body)
        hand_off = phase_body("## Phase 10: Hand off")
        for phrase in (
            "the record, the items file",
            "List every criterion marked unproven first",
        ):
            self.assertIn(phrase, hand_off)

    def test_phase_2_asks_only_when_it_matters(self):
        body = phase_body("## Phase 2: Classify")
        for phrase in (
            "ask the pathway, the size and how to split it with AskUserQuestion before phase 3",
            "Otherwise say both out loud in one sentence",
        ):
            self.assertIn(phrase, body)

    def test_phase_3_records_where_the_user_sees_the_result(self):
        body = phase_body("## Phase 3: Ground")
        for phrase in (
            "Learn where the user sees the result",
            "marking whether the builder can run it",
        ):
            self.assertIn(phrase, body)

    def test_phase_3_never_waits_on_the_user(self):
        body = phase_body("## Phase 3: Ground")
        for phrase in ("Never end a turn only to wait for it.", "mark it unconfirmed"):
            self.assertIn(phrase, body)

    def test_phase_3_delegates_only_checkable_answers(self):
        body = phase_body("## Phase 3: Ground")
        for phrase in (
            "Read the code you need to understand yourself.",
            "only for outside documentation, or for a question whose answer is where something is in the code",
        ):
            self.assertIn(phrase, body)
        self.assertNotIn("For broad searches", read_phases())


if __name__ == "__main__":
    unittest.main()
