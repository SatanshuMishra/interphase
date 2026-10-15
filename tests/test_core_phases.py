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
    "Rules 5 and 8 give way only to explicit instructions to work autonomously; then follow the section Work autonomously of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` in place of every question and approval.",
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

    def test_phases_review_each_spec_once_with_judgement(self):
        review = bullets(phase_body("## Phase 9: Review"))
        dispatch = tuple(line for line in review if line.startswith("- Dispatch the `interphase:spec-reviewer` agent once"))
        self.assertEqual(len(dispatch), 1)
        self.assertIn("use your judgement on each", dispatch[0])
        self.assertIn("Do not dispatch it again for the fixes.", dispatch[0])

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

    def test_phases_mark_the_run_in_the_record(self):
        self.assertIn(
            '"status": "in-progress"', phase_body("## Phase 1: Intake")
        )
        lines = phase_body("## Phase 10: Hand off").splitlines()
        guard = lines.index(
            "- Delete `docs/specs/<slug>.guard.json` after a clean verify."
        )
        self.assertEqual(
            lines[guard + 1],
            "- Set the record's `status` to `handed-off`.",
        )

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

    def test_classify_knows_the_project_pathway(self):
        body = phase_body("## Phase 2: Classify")
        for phrase in (
            "use project for a new repository, or for replacing an existing repository's stack, build, CI or release",
            "use feature for anything else that does not exist yet",
            "A new product built from a design mixes project and prototype; recommend a project spec first and a prototype spec second",
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

    def test_ground_marks_varying_behaviour(self):
        self.assertIn(
            "- Mark every behaviour the request touches that varies from run to run, following `${CLAUDE_PLUGIN_ROOT}/core/variation.md`.",
            phase_body("## Phase 3: Ground"),
        )

    def test_interrogate_specifies_each_varying_criterion_as_a_population(self):
        self.assertIn(
            "- Write each criterion for a varying behaviour with its kind and its population, following `${CLAUDE_PLUGIN_ROOT}/core/variation.md`.",
            phase_body("## Phase 4: Interrogate"),
        )

    def test_phases_route_small_requests_to_the_brief_lane(self):
        brief = "`${CLAUDE_PLUGIN_ROOT}/core/brief.md`"
        classify = phase_body("## Phase 2: Classify")
        for phrase in (
            "Use small for one or more items, each one behaviour in existing code describable in one sentence; whether a small request takes the brief lane is confirmed at the end of Phase 3, following "
            + brief
            + ".",
            "Use standard for most requests.",
            "Use large for a new subsystem or several connected behaviours.",
        ):
            self.assertIn(phrase, classify)
        depth = tuple(line for line in bullets(classify) if line.startswith("- Let size set depth"))
        self.assertEqual(len(depth), 1)
        self.assertIn("A small request takes the brief lane when the conditions in " + brief + " hold.", depth[0])
        self.assertIn("one Step per item", depth[0])
        self.assertEqual(
            bullets(phase_body("## Phase 3: Ground"))[-1],
            "- When the request is small, end the phase by checking the conditions in "
            + brief
            + " and choosing the lane.",
        )
        for heading in ("## Phase 5: Challenge", "## Phase 7: Read back", "## Phase 9: Review"):
            self.assertEqual(
                bullets(phase_body(heading))[0],
                "- In the brief lane, follow " + brief + ".",
                heading,
            )
        copy = tuple(
            line
            for line in bullets(phase_body("## Phase 8: Write the spec and the Steps"))
            if line.startswith("- Copy ")
        )
        self.assertEqual(len(copy), 1)
        self.assertIn(
            "In the brief lane, copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-brief.md` instead of the pathway template.",
            copy[0],
        )

    def test_phase_8_says_how_to_fill_the_review_bar(self):
        lines = bullets(phase_body("## Phase 8: Write the spec and the Steps"))
        fill = "- Fill every section except Acceptance criteria."
        positions = tuple(index for index, line in enumerate(lines) if line.startswith(fill))
        self.assertEqual(len(positions), 1)
        following = lines[positions[0] + 1]
        self.assertTrue(following.startswith("- Fill the Review bar section"), following)
        for phrase in (
            "threat",
            "level of defence",
            "interview",
            "Work autonomously",
            "core/questioning.md",
            "defended",
            "block",
            "out of scope",
            "before the change",
            "brief lane",
        ):
            self.assertIn(phrase, following)
        self.assertNotIn("mitosis", read_phases())

    def test_autonomous_runs_skip_approval_and_list_their_decisions_as_risks(self):
        rules = tuple(line for line in phase_body("## Rules").splitlines() if line[:1].isdigit())
        self.assertEqual(len(rules), 15)
        self.assertEqual(
            rules[-1],
            "15. Rules 5 and 8 give way only to explicit instructions to work autonomously; then follow the section Work autonomously of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` in place of every question and approval.",
        )
        ground = bullets(phase_body("## Phase 3: Ground"))
        self.assertTrue(
            ground[-2].startswith(
                "- Read the decisions files of earlier specs in the spec folder that touch the same code"
            ),
            ground[-2],
        )
        self.assertTrue(ground[-1].startswith("- When the request is small"), ground[-1])
        hand_off = bullets(phase_body("## Phase 10: Hand off"))
        unproven = tuple(
            index
            for index, line in enumerate(hand_off)
            if line.startswith("- List every criterion marked unproven first")
        )
        self.assertEqual(len(unproven), 1)
        risks = hand_off[unproven[0] + 1]
        self.assertTrue(risks.startswith("- In an autonomous run, list next"), risks)
        overriding = risks.find(
            "every decision that overrides a line of an earlier decisions file or a written rule or convention of the project"
        )
        others = risks.find("then every other decision made on the user's behalf")
        self.assertNotIn(-1, (overriding, others))
        self.assertLess(overriding, others)
        self.assertIn("as top risks", risks)
        review = phase_body("## Phase 9: Review")
        self.assertIn(
            "the path of `${CLAUDE_PLUGIN_ROOT}/core/practices.md`, and say whether the run is autonomous.",
            review,
        )


    def assert_directly_after(self, heading, prefix, expected):
        lines = bullets(phase_body(heading))
        positions = tuple(i for i, line in enumerate(lines) if line.startswith(prefix))
        self.assertEqual(len(positions), 1, prefix)
        following = lines[positions[0] + 1:positions[0] + 1 + len(expected)]
        self.assertEqual(following, tuple(expected))

    def test_intake_routes_an_amendment(self):
        lines = bullets(phase_body("## Phase 1: Intake"))
        self.assertEqual(
            lines[0],
            "- When the request names a spec in the spec folder whose record says `handed-off` and asks to add a case to it or fix a gap in it, follow the section Amend a handed-off spec instead of the phases below.",
        )

    def test_ground_runs_outside_facts(self):
        self.assert_directly_after(
            "## Phase 3: Ground",
            "- Read the code you need to understand yourself",
            [
                "- Run every fact about software outside the repository, such as a tool's flags, an interface's reply or what a version accepts, and record it with `outside: true`, the command and what it showed. Documentation and memory are never the evidence for such a fact. When it cannot be run here, because it needs the user's device, a live service or a paid account, write it into the spec as an assumption instead.",
            ],
        )

    def test_interrogate_writes_case_tables(self):
        self.assert_directly_after(
            "## Phase 4: Interrogate",
            "- Design the Steps as the interview goes",
            [
                "- Write a case table only for an input that carries real risk: one a person types, picks or says; one that comes from software outside the repository, a file, a network or a store the code reads back; or one where a wrong result loses, corrupts or exposes data. For such an input, add a domain: what varies, every class of it the code tells apart that a real path can deliver and, when existing code reads it, the fact that cites where. Give every class a row: one named test with what is given, what is expected and the classes it covers. Any other criterion needs no domain: give it the rows that prove it, each with what is given and what is expected.",
                "- When a criterion sets a bound, such as at most, no more than, up to, a maximum, a budget, a limit, a cap or exceeding something, list in `gives_way` what gives way first to last when the bound is reached, and give every item a row.",
            ],
        )

    def test_challenge_closes_every_domain(self):
        self.assert_directly_after(
            "## Phase 5: Challenge",
            "- Record at least one non-goal.",
            [
                "- Check that every domain is closed. When the classes of an input cannot all be listed, because it is free text, a shell command, arbitrary configuration or anything else open-ended, recommend a design that makes the decision where every input can be listed, such as one entry point that receives them already parsed, and settle it as any other decision.",
            ],
        )

    def test_write_states_each_requirement_once(self):
        self.assert_directly_after(
            "## Phase 8: Write the spec and the Steps",
            "- Give every requirement an acceptance criterion that can pass or fail.",
            [
                "- Write each requirement once, in its acceptance criterion. Every line of Requirements, Edge cases, Expected and Unchanged cites the number of the criterion that states it, such as 7.3, and says no more than that criterion does.",
            ],
        )

    def test_amend_section_follows_hand_off(self):
        lines = read_phases().splitlines()
        level_two = tuple(line for line in lines if line.startswith("## "))
        position = level_two.index("## Phase 10: Hand off")
        self.assertEqual(level_two[position + 1], "## Amend a handed-off spec")
        self.assertEqual(
            bullets(phase_body("## Amend a handed-off spec")),
            (
                "- Keep the slug, the spec, the decisions file and the record. Never start a new spec for a case a handed-off spec missed.",
                "- Take the guard snapshot as in phase 1, and set the record's `status` to `in-progress`.",
                "- When the record's tests carry `asserts`, rewrite each as `given` and `expect`, and add the domains and give-way orders the record check asks for.",
                "- Number the amendment one more than the highest `amendment` of any Step in the record, or 1 when no Step has one.",
                "- Add the missing classes, give-way items, facts and rows to the criteria they belong to. Add a criterion only for a behaviour no criterion states.",
                "- Give every new row's test to a new Step with `amendment` set to that number, the files it changes, `after` naming the Steps whose code it changes, and a task written as in phase 8.",
                "- Save each decision to the decisions file, follow phases 5 and 6 for what changed, and run `python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py\" --complete docs/specs/<slug>.record.json`.",
                "- Run the render script as in phase 8, then again with `--amendment <n>` and `--items docs/specs/<slug>.amend-<n>.items.json`.",
                "- Run the spec check as in phase 9, and the items check with `--amendment` on the amendment items file.",
                "- Dispatch the `interphase:spec-reviewer` agent as in phase 9, naming the criteria and the Step that changed, and get approval as in phase 9.",
                "- Hand off as in phase 10, and report the amendment items file in place of the items file.",
            ),
        )


if __name__ == "__main__":
    unittest.main()
