import pathlib
import unittest

HEADINGS = (
    "## Phase 1: Intake",
    "## Phase 2: Classify",
    "## Phase 3: Ground",
    "## Phase 4: Interview",
    "## Phase 5: Challenge",
    "## Phase 6: Design the Steps",
    "## Phase 7: Read back",
    "## Phase 8: Write the spec and the Steps",
    "## Phase 9: Review",
    "## Phase 10: Hand off",
)

RULES = (
    "Never create, edit or delete a file in the user's working tree, except interphase's own output files: this run's files in the spec folder, the glossary files and the ADRs `${CLAUDE_PLUGIN_ROOT}/core/domain.md` describes.",
    "Never commit, push, stash, reset, check out or rebase in the user's repository.",
    "Never implement: the spec states the cause, the decisions and the acceptance tests, never the patch.",
    "Look up facts yourself; ask the user only for decisions that pass the hard bar of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`.",
    "During the interview, never answer your own decision question; recommend an answer and wait for the user's reply.",
    "Silence, \"just do it\", and your own judgement that the spec is fine do not approve the read-back.",
    "After the user approves the read-back, ask nothing more: fill every gap as the section After the interview of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` says, and never stop for an answer.",
    "Save each answer to the decisions file the moment it is given.",
    "Only the main conversation talks to the user; agents never ask the user anything.",
    "Never name, detect or invoke any tool that might consume the spec.",
    "Never comment on, ask about or offer to change whether git tracks interphase's own output files, in anything you say or ask, or in the spec, decisions or items files.",
    "Never plan a copy of logic that already exists, and never bend existing code to fit a new use; follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md`.",
    "Keep the interview in the record: write each seam, criterion and Step to `docs/specs/<slug>.record.json` the moment it is settled, and after any summary of the conversation, re-read the record and the decisions file before acting.",
    "When the user's instructions say to work autonomously, the run is unattended: follow the section Unattended runs of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` in place of every question and approval.",
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


def bullets(body):
    return tuple(line for line in body.splitlines() if line.startswith("- "))


class CorePhasesTest(unittest.TestCase):
    def test_phases_lists_all_ten_phases_in_order(self):
        lines = read_phases().splitlines()
        positions = tuple(lines.index(heading) if heading in lines else -1 for heading in HEADINGS)
        self.assertNotIn(-1, positions)
        self.assertEqual(list(positions), sorted(positions))

    def test_phases_states_every_rule_verbatim(self):
        lines = read_phases().splitlines()
        rules_line = lines.index("## Rules")
        self.assertLess(rules_line, lines.index(HEADINGS[0]))
        rules_block = "\n".join(lines[rules_line:lines.index(HEADINGS[0])])
        positions = tuple(rules_block.find(f"{number}. {rule}") for number, rule in enumerate(RULES, start=1))
        self.assertNotIn(-1, positions)
        self.assertEqual(list(positions), sorted(positions))
        self.assertEqual(len([line for line in rules_block.splitlines() if line[:1].isdigit()]), len(RULES))
        for relative in STEP_FILES:
            content = (repo_root() / relative).read_text(encoding="utf-8")
            self.assertNotIn("mitosis", content.lower(), relative)

    def test_the_run_is_attended_up_front_then_autonomous_to_the_end(self):
        lead = read_phases().split("## Rules")[0]
        for phrase in (
            "The interview, phases 3 to 7, is attended",
            "From then on the run is autonomous to the end: it asks nothing and stops for nothing, and fills every gap from the recorded intent.",
            "An unattended run skips the interview altogether.",
        ):
            self.assertIn(phrase, lead)

    def test_the_read_back_is_the_only_ask_user_question_and_the_last_question(self):
        read_back = phase_body("## Phase 7: Read back")
        self.assertIn("This is the only question the tool asks in a run.", read_back)
        self.assertIn("From here the run is autonomous to the end.", read_back)
        uses = [line for line in read_phases().splitlines() if "AskUserQuestion" in line]
        self.assertEqual(len(uses), 1)
        for heading in ("## Phase 8: Write the spec and the Steps", "## Phase 9: Review", "## Phase 10: Hand off"):
            self.assertNotIn("approval", phase_body(heading).lower(), heading)

    def test_phases_review_each_spec_once_and_fix_real_findings_once(self):
        review = bullets(phase_body("## Phase 9: Review"))
        dispatch = tuple(line for line in review if line.startswith("- Dispatch the `interphase:spec-reviewer` agent once"))
        self.assertEqual(len(dispatch), 1)
        for phrase in (
            "Fix once each issue it finds that would cause the wrong thing to be built",
            "Fill any gap a fix opens as the section After the interview says.",
            "Never dispatch the reviewer again.",
            "say whether the run is unattended",
        ):
            self.assertIn(phrase, dispatch[0])
        self.assertIn("- Ask nothing. Go straight to Phase 10 in the same turn.", review)

    def test_phases_never_mention_ignoring_the_spec_folder(self):
        text = read_phases().lower()
        for phrase in ("gitignore", "info/exclude", "check-ignore", "ignored"):
            self.assertNotIn(phrase, text)

    def test_phases_design_steps_before_the_read_back(self):
        self.assertIn(
            "every acceptance criterion has a Step whose test proves it at an agreed seam the builder runs",
            phase_body("## Phase 6: Design the Steps"),
        )
        self.assertIn("How the work is cut", phase_body("## Phase 7: Read back"))
        self.assertIn(
            "Never derive the Steps by reading them back out of the spec.",
            phase_body("## Phase 8: Write the spec and the Steps"),
        )

    def test_intake_owns_the_spec_files_the_glossary_and_the_adrs(self):
        intake = phase_body("## Phase 1: Intake")
        self.assertIn(
            'snapshot --repo . --owned "docs/specs/<slug>." --owned GLOSSARY --owned docs/adr/ --out docs/specs/<slug>.guard.json',
            intake,
        )
        self.assertIn("When a `GLOSSARY-MAP.md` exists, add one `--owned` for each glossary and each ADR folder it names.", intake)
        self.assertIn("then an empty `## Intent` section and an empty `## Decisions` section.", intake)
        self.assertIn('{"seams": [], "criteria": [], "steps": [], "status": "in-progress"}', intake)

    def test_phases_say_the_guard_removes_new_caches(self):
        self.assertIn(
            "The guard first removes the caches that running the project's code created since the snapshot.",
            phase_body("## Phase 10: Hand off"),
        )

    def test_phases_apply_the_practices_glossary_and_adrs(self):
        ground = phase_body("## Phase 3: Ground")
        self.assertIn(
            "Follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md` to find what already exists and the project's own written rules.",
            ground,
        )
        self.assertIn("Read the glossary and the ADRs in the area the request touches", ground)
        review_body = phase_body("## Phase 9: Review")
        self.assertIn("the decisions path", review_body)
        self.assertIn("the path of `${CLAUDE_PLUGIN_ROOT}/core/practices.md`", review_body)

    def test_phases_mark_the_run_in_the_record(self):
        lines = phase_body("## Phase 10: Hand off").splitlines()
        guard = lines.index("- Delete `docs/specs/<slug>.guard.json` after a clean verify.")
        self.assertEqual(lines[guard + 1], "- Set the record's `status` to `handed-off`.")

    def test_phases_keep_the_interview_in_the_record(self):
        interview = phase_body("## Phase 4: Interview")
        for phrase in (
            "After every round, run",
            "scripts/check_record.py",
            "Fix every error before the next round.",
            "When the user agrees a seam, write it to the record.",
        ):
            self.assertIn(phrase, interview)
        self.assertIn("--complete docs/specs/<slug>.record.json", phase_body("## Phase 6: Design the Steps"))
        write_body = phase_body("## Phase 8: Write the spec and the Steps")
        for phrase in ("Fill every section except Test seams.", "scripts/render_record.py", "Copy the intent lines of the decisions file into the Intent section word for word."):
            self.assertIn(phrase, write_body)

    def test_phase_2_puts_a_hard_classification_in_the_intent_round(self):
        body = phase_body("## Phase 2: Classify")
        self.assertIn("put the pathway, the size and the split in the intent round instead.", body)
        self.assertIn("Let size set depth.", body)

    def test_classify_knows_the_project_pathway(self):
        body = phase_body("## Phase 2: Classify")
        for phrase in (
            "use project for a new repository, or for replacing an existing repository's stack, build, CI or release",
            "use feature for anything else that does not exist yet",
            "A new product built from a design mixes project and prototype; recommend a project spec first and a prototype spec second",
        ):
            self.assertIn(phrase, body)

    def test_phase_3_finds_seams_and_never_waits_on_the_user(self):
        body = phase_body("## Phase 3: Ground")
        for phrase in (
            "Find the seams the project already tests at",
            "whether the builder can run tests there",
            "Never end a turn only to wait for it.",
            "mark it unconfirmed",
            "Read the code you need to understand yourself.",
            "only for outside documentation, or for a question whose answer is where something is in the code",
            "write the command and what it showed into the decision that rests on it",
            "- Mark every behaviour the request touches that varies from run to run, following `${CLAUDE_PLUGIN_ROOT}/core/variation.md`.",
        ):
            self.assertIn(phrase, body)

    def test_interview_writes_case_tables_only_for_security_and_refusal(self):
        body = phase_body("## Phase 4: Interview")
        self.assertIn(
            "Write a case table only for behaviour that is security-sensitive, such as an input a person or outside software controls at a trust boundary or a result that could expose data, and for behaviour that exists to refuse something.",
            body,
        )
        self.assertIn("Mark the criterion's `case_table` as `security` or `refusal`", body)
        self.assertIn(
            "- Write each criterion for a varying behaviour with its kind and its population, following `${CLAUDE_PLUGIN_ROOT}/core/variation.md`.",
            body,
        )
        self.assertNotIn("gives_way", read_phases().replace("remove its `where`, `facts` and `gives_way`", ""))

    def test_challenge_closes_every_case_table(self):
        body = phase_body("## Phase 5: Challenge")
        self.assertIn("- Record at least one item for the spec's Out of scope section.", body)
        self.assertIn("Check that every case table's domains are closed.", body)

    def test_phases_route_small_requests_to_the_brief_lane(self):
        brief = "`${CLAUDE_PLUGIN_ROOT}/core/brief.md`"
        self.assertEqual(
            bullets(phase_body("## Phase 3: Ground"))[-1],
            "- When the request is small, end the phase by checking the conditions in " + brief + " and choosing the lane.",
        )
        for heading in ("## Phase 5: Challenge", "## Phase 7: Read back", "## Phase 9: Review"):
            self.assertEqual(bullets(phase_body(heading))[0], "- In the brief lane, follow " + brief + ".", heading)
        copy = tuple(line for line in bullets(phase_body("## Phase 8: Write the spec and the Steps")) if line.startswith("- Copy `"))
        self.assertEqual(len(copy), 1)
        self.assertIn("In the brief lane, copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-brief.md` instead of the pathway template.", copy[0])

    def test_hand_off_promotes_lasting_decisions_and_lists_assumptions_as_risks(self):
        hand_off = bullets(phase_body("## Phase 10: Hand off"))
        self.assertTrue(hand_off[0].startswith("- Promote what must outlast the spec into the glossary and the ADRs"), hand_off[0])
        risks = tuple(line for line in hand_off if line.startswith("- List as top risks"))
        self.assertEqual(len(risks), 1)
        for phrase in (
            "every criterion marked unproven first",
            "then every assumption with the intent line it relied on",
            "an ADR or a written rule or convention of the project first",
        ):
            self.assertIn(phrase, risks[0])
        self.assertTrue(any("every glossary file and ADR written" in line for line in hand_off))

    def test_intake_routes_an_amendment(self):
        lines = bullets(phase_body("## Phase 1: Intake"))
        self.assertEqual(
            lines[0],
            "- When the request names a spec in the spec folder whose record says `handed-off` and asks to add a case to it or fix a gap in it, follow the section Amend a handed-off spec instead of the phases below.",
        )

    def test_amend_section_follows_hand_off_and_migrates_earlier_records(self):
        lines = read_phases().splitlines()
        level_two = tuple(line for line in lines if line.startswith("## "))
        position = level_two.index("## Phase 10: Hand off")
        self.assertEqual(level_two[position + 1], "## Amend a handed-off spec")
        amend = phase_body("## Amend a handed-off spec")
        for phrase in (
            "turn each entry of `environments` into a seam",
            "remove `facts`, `environments`, `reviews` and `open_issues` from the record",
            "rename its `Acceptance criteria` heading to `Test seams`, keeping its number",
            "Fill every gap from the intent as the section After the interview says",
            "--amendment <n>",
            "report the amendment items file in place of the items file",
        ):
            self.assertIn(phrase, amend)
        self.assertNotIn("approval", amend)


if __name__ == "__main__":
    unittest.main()
