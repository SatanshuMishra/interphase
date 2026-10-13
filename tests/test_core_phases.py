import importlib.util
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

OUTSIDE_FACT_RULE = "- Run every fact about software outside the repository, such as a tool's flags, an interface's reply or what a version accepts, and record it with `outside: true`, the command and what it showed. Run it far enough to see every class the code will tell apart, not only the names of the fields it returns. Documentation and memory are never the evidence for such a fact. When it cannot be run here, because it needs the user's device, a live service or a paid account, record it with `outside: true` and `assumed` set to why it could not be run, never only as an assumption in the spec."
STAND_IN_RULE = "- When the code would read one value to learn another, such as a file's extension to learn its format, a country code to learn a time zone or a screen width to learn the device, find where the two can differ. Read the value the behaviour depends on, or give the domain a class where the two differ."
BOUNDARY_RULE = "- Draw the change's boundary from the request, before any domain, and keep it: settling a review issue never moves it. Inside it is the behaviour the request asks to add or alter, and existing code that behaviour newly calls or newly routes input into. Outside it is existing behaviour the change neither alters nor newly reaches: state it as Unchanged, give it no domain, and never redesign it. The values that reach the changed code from unchanged code in front of it are what that code lets through: read that code and cite it by path, line and quote. A value that reached the same existing code with the same result before the change, and still does, keeps that result when it breaks nothing the request asks for: give it a class whose result is that existing behaviour, cite the code that gives it by path, line and quote, and add no behaviour for it. A defect found outside the boundary, such as unchanged code that fails on some input before the changed code sees it, is never a criterion or a Step: record it as a fact and report it in phase 10."
CASE_TABLE_RULE = "- Write each criterion as a case table. For every input that behaviour inside the boundary reads, add a domain: what varies, its `source`, and every class of it the code tells apart, drawn from where its values are defined, never from a description of them. A domain's `source` is `outside` when a program, tool, system or service outside the repository produces its values, even when the repository's code parses them; its `fact` is then a fact marked outside. It is `person` when a person types, picks or says its values; its `fact` then cites, by path, line and quote or by command and output, where the repository asks for them, or `defined_by` names the Step that will. It is `stored` when the repository's own code wrote its values earlier, to a file, a database or another store, and reads them back; its `fact` then cites where the repository writes them, or `defined_by` names the Step that will. It is `sent` when the repository's own code in another process, such as its client, a producer or another deployed version, sends its values over a network, a queue, a pipe or another channel the code reads from; its `fact` then cites where the repository sends them, or `defined_by` names the Step that will. Anything else that can reach that channel can send it values too. Otherwise its `source` is `repo`, and its `fact` cites, by path, line and quote or by command and output, where the repository defines the values, or `defined_by` names the Step that will define them. A Step named in `defined_by` proves the domain's criterion or comes before a Step that does. When nothing where the values are defined bounds a value's size or count, give the domain a class beyond every bound the behaviour sets. Give every class a row: one named test with what is given, what is expected and the classes it covers. A criterion that says every, each, any, all, whole, always, never, whatever, however or whenever needs a domain over each kind of thing the word ranges over."
INVALID_RULE = "- Give every outside, person, stored or sent domain `invalid`: the classes for input that arrives other than promised, such as missing, empty, malformed, of another type, cut short or written by an older version. A behaviour that exists to refuse something refuses on every invalid class, unless the user decides otherwise and the decision is recorded. An autonomous run never lets an invalid class through such a behaviour, whatever the request's wording."
CLOSED_RULE = "- Mark every domain `closed`: `true` when every value the input can take falls in one of its classes and every value in a class gets the same result, otherwise `false`. Phase 5 settles every domain marked `false`."
READS_RULE = "- Give every Step `reads`: the names of the domains, from the criteria it proves, of every input its code reads, or an empty list when it reads none. When its code reads an input no domain covers, add the domain first."
BOUND_RULE = "- When a criterion sets a bound, such as at most, no more than, up to, a maximum, a budget, a limit, a cap or exceeding something, list in `gives_way` what gives way first to last when the bound is reached, and in `keeps` what never gives way, including everything the criterion promises. Give every give-way item a row, and every kept item a row in which every give-way item gives way and the kept item still holds."
CLOSED_DESIGN_RULE = "- Check that every domain is closed. A class for every other value does not close a domain when some of those values need a different result. When the classes of an input cannot all be listed, because it is free text, a shell command, arbitrary configuration or anything else open-ended, recommend a design that makes the decision where every input can be listed, such as one entry point that receives them already parsed, and settle it as any other decision. A mechanism the request names does not settle an open domain: in an autonomous run, choose the design that closes it and record the choice as a decision that overrides the request's wording. Keep `closed: false` only on a criterion that varies from run to run, or when the user decides to keep the domain open: record that decision and name in `open_by` the fact that cites its line in the decisions file. A behaviour that exists to refuse something never keeps its domain open, and an autonomous run never keeps a domain open by `open_by`."
DISPATCH_RULE = "- Dispatch the `interphase:spec-reviewer` agent with the spec path, the items path, the record path, the decisions path and the path of `${CLAUDE_PLUGIN_ROOT}/core/practices.md`, and say whether the run is autonomous. This first review reads the whole spec. Fix the issues it finds that would cause the wrong thing to be built."
RECORD_REVIEW_RULE = "- As soon as a review returns, before changing anything, copy the `json` block that ends it, unchanged, to the end of the record's `reviews`, and add to it `reviewed`, set to what `python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py\" --digest docs/specs/<slug>.record.json` prints. Then copy the spec and the record to `docs/specs/<slug>.review-copy.md` and `docs/specs/<slug>.review-copy.json`, replacing any earlier copies. Never remove a review. When the reply has no `json` block holding one JSON object, record nothing and dispatch a fresh reviewer for the same review. When the record check refuses a review of the record as it stands, write in the decisions file what it refused and why, add to the record a fact that cites that line, fix what the review reports, and dispatch a follow-up review. When it reports a review with no `reviewed` or one that is not a digest, set `reviewed` to what `--digest` printed when that review returned, or, when that is not known, to 64 zeros, which marks it as a review of an earlier version, and dispatch a follow-up review. When it reports an entry that is not an object, which holds no review, remove that entry and dispatch a fresh reviewer for the same review."
FIX_INPUT_RULE = "- Settle every issue it reports under Missing input, Missing class, Stand-in, Source, Outside fact, Invalid input, Give-way or Open domain: change the record to cover it, or, when the issue concerns behaviour outside the change's boundary or a class that cannot reach the changed code, add a fact that shows so by path, line and quote or by command and output. Settle each issue with the least the record needs: a class that keeps the existing result, as phase 4 describes, when the value reached it before the change; otherwise a refusal with a fixed answer that reads no further input; and new behaviour only where the request needs it. Removing behaviour an earlier settlement added that the request does not need also settles the issues in it. New behaviour a settlement adds reads no input that no domain covers: write its domains, classes and rows in the same change, before the follow-up review. Then rerun the record check with `--complete` and every render, spec check and items check this run has run, with the same arguments, which in an amendment includes those with `--amendment`. After any change that follows a review, write the change since that review with `diff -u docs/specs/<slug>.review-copy.md docs/specs/<slug>.md > docs/specs/<slug>.review-diff.txt` and `diff -u docs/specs/<slug>.review-copy.json docs/specs/<slug>.record.json >> docs/specs/<slug>.review-diff.txt`, running the second whatever the first exits with, since `diff` exits 1 when the files differ, and dispatch a fresh reviewer for a follow-up review, giving it the same paths, the path of that file and the issues of the last review. Stop when a review leads to no change; the record check hands off only when that review reports none of those eight categories. Any change to the record or the spec after the last review needs a follow-up review too: the record check refuses to hand off a record whose record or spec changed after its last review, and one that any review of them as they stand found an input issue in."
NO_PROGRESS_RULE = "- A follow-up review that reports at least one issue, and no fewer issues than the review before it, makes no progress: change nothing more for it. When none of its issues falls under those eight categories, go on to phase 10 and list them as top risks. Otherwise, in an attended run, show the user those issues and ask how to settle each; in an autonomous run, copy each of those issues, unchanged, to the record's `open_issues`, go on to phase 10 and list them first among the top risks. An autonomous run always ends with a handed-off spec."
WRONG_ISSUE_RULE = "- When the user decides that an issue reported under one of those eight categories is wrong, record the decision with its reason, add to the record a fact that cites its line in the decisions file, and dispatch a follow-up review, which reads the decisions file. An autonomous run never settles such an issue by its own judgement: it changes the record, or adds a fact showing that the issue lies outside the change or concerns a class that cannot reach the changed code, until a follow-up review no longer reports it."
HAND_OFF_CHECK_RULE = "- Run `python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py\" --complete docs/specs/<slug>.record.json`. When it reports an error, set the `status` back to `in-progress`, take the guard snapshot as in phase 1 and reopen phase 9."
DELETE_WORKING_FILES_RULE = "- When that check reports no error, delete `docs/specs/<slug>.review-copy.md`, `docs/specs/<slug>.review-copy.json` and `docs/specs/<slug>.review-diff.txt`."
ASSUMED_RISK_RULE = "- List next every fact marked `assumed`, with its reason, as top risks."
DECISION_RISK_RULE = "- In an autonomous run, list next every decision that overrides a line of an earlier decisions file, a written rule or convention of the project or the request's own wording, then every other decision made on the user's behalf, as top risks."
AMEND_ASSERTS_RULE = "- When the record's tests carry `asserts`, rewrite each as `given` and `expect`. Add the domains, give-way orders, `source`, `closed`, `invalid`, `keeps` and `reads` the record check asks for."
AMEND_DISPATCH_RULE = "- Dispatch the `interphase:spec-reviewer` agent as in phase 9, passing the amendment items file beside the items file and naming the criteria and the Step that changed, and record each review as in phase 9. Fix every input issue a review reports, in any criterion, as in phase 9, giving each new row's test to a new Step of this amendment, and get approval as in phase 9."
INPUT_RULES = (
    OUTSIDE_FACT_RULE,
    STAND_IN_RULE,
    CASE_TABLE_RULE,
    INVALID_RULE,
    CLOSED_RULE,
    READS_RULE,
    BOUND_RULE,
    CLOSED_DESIGN_RULE,
    DISPATCH_RULE,
    RECORD_REVIEW_RULE,
    FIX_INPUT_RULE,
    NO_PROGRESS_RULE,
    WRONG_ISSUE_RULE,
    HAND_OFF_CHECK_RULE,
    DELETE_WORKING_FILES_RULE,
    ASSUMED_RISK_RULE,
    DECISION_RISK_RULE,
    AMEND_ASSERTS_RULE,
    AMEND_DISPATCH_RULE,
)


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
        check = lines[guard + 2]
        self.assertTrue(check.startswith("- Run `python3"), check)
        self.assertTrue(check.endswith("reopen phase 9."), check)
        self.assertEqual(lines[guard + 3], DELETE_WORKING_FILES_RULE)

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
            "List every issue in the record's `open_issues` first",
            "List next every criterion marked unproven",
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
            if line.startswith("- List next every criterion marked unproven")
        )
        self.assertEqual(len(unproven), 1)
        assumed = hand_off[unproven[0] + 1]
        self.assertTrue(assumed.startswith("- List next every fact marked `assumed`"), assumed)
        risks = hand_off[unproven[0] + 2]
        self.assertTrue(risks.startswith("- In an autonomous run, list next"), risks)
        overriding = risks.find(
            "every decision that overrides a line of an earlier decisions file, a written rule or convention of the project or the request's own wording"
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
                OUTSIDE_FACT_RULE,
                STAND_IN_RULE,
            ],
        )

    def test_interrogate_writes_case_tables(self):
        self.assert_directly_after(
            "## Phase 4: Interrogate",
            "- Design the Steps as the interview goes",
            [
                BOUNDARY_RULE,
                CASE_TABLE_RULE,
                INVALID_RULE,
                CLOSED_RULE,
                READS_RULE,
                BOUND_RULE,
            ],
        )

    def test_challenge_closes_every_domain(self):
        self.assert_directly_after(
            "## Phase 5: Challenge",
            "- Record at least one non-goal.",
            [
                CLOSED_DESIGN_RULE,
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
                AMEND_ASSERTS_RULE,
                "- Number the amendment one more than the highest `amendment` of any Step in the record, or 1 when no Step has one.",
                "- Add the missing classes, give-way items, facts and rows to the criteria they belong to. Add a criterion only for a behaviour no criterion states.",
                "- Give every new row's test to a new Step with `amendment` set to that number, the files it changes, `after` naming the Steps whose code it changes, and a task written as in phase 8.",
                "- Save each decision to the decisions file, follow phases 5 and 6 for what changed, and run `python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py\" --complete docs/specs/<slug>.record.json`.",
                "- Run the render script as in phase 8, then again with `--amendment <n>` and `--items docs/specs/<slug>.amend-<n>.items.json`.",
                "- Run the spec check as in phase 9, and the items check with `--amendment` on the amendment items file.",
                AMEND_DISPATCH_RULE,
                "- Hand off as in phase 10, and report the amendment items file in place of the items file.",
            ),
        )


    def test_phases_state_the_input_rules(self):
        text = read_phases()
        lines = text.splitlines()
        self.assertEqual(tuple(rule for rule in INPUT_RULES if rule not in lines), ())
        for replaced in (
            "write it into the spec as an assumption instead.",
            "and, when existing code reads it, the fact that cites where.",
        ):
            self.assertNotIn(replaced, text)
        self.assert_directly_after(
            "## Phase 9: Review",
            "- Dispatch the `interphase:spec-reviewer` agent with",
            [RECORD_REVIEW_RULE, FIX_INPUT_RULE, NO_PROGRESS_RULE, WRONG_ISSUE_RULE],
        )
        hand_off = bullets(phase_body("## Phase 10: Hand off"))
        order = tuple(
            hand_off.index(line)
            for line in (
                "- List every issue in the record's `open_issues` first, as the top risks.",
                "- List next every criterion marked unproven, with its reason, as top risks.",
                ASSUMED_RISK_RULE,
                DECISION_RISK_RULE,
            )
        )
        self.assertEqual(order, (order[0], order[0] + 1, order[0] + 2, order[0] + 3))

    def test_input_category_lists_agree_with_the_record_check(self):
        spec = importlib.util.spec_from_file_location("check_record", str(repo_root() / "scripts" / "check_record.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        places = (
            ("agents/spec-reviewer.md", "When an issue fits one of ", " and another category too"),
            ("core/phases.md", "Settle every issue it reports under ", ": change the record"),
            ("core/items.md", "reports an issue under ", "."),
        )
        for relative, opening, closing in places:
            with self.subTest(relative=relative):
                text = (repo_root() / relative).read_text(encoding="utf-8")
                self.assertEqual(text.count(opening), 1, opening)
                start = text.index(opening) + len(opening)
                listed = text[start : text.index(closing, start)]
                head, separator, last = listed.rpartition(" or ")
                self.assertEqual(separator, " or ", listed)
                self.assertEqual(tuple(head.split(", ")) + (last,), tuple(module.INPUT_CATEGORIES))


if __name__ == "__main__":
    unittest.main()
