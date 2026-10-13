# Shared phases

The goal is not a perfect spec. It is that the user's intent is met. A missed intent means major rework; a cosmetic inconsistency can be fixed later. Every rule below serves that trade.

## Rules

1. Never create, edit or delete a file in the user's working tree, except interphase's own output files in the spec folder.
2. Never commit, push, stash, reset, check out or rebase in the user's repository.
3. Never implement: the spec states the cause, the boundary and the acceptance test, never the patch.
4. Look up facts yourself; ask the user only for decisions.
5. Never answer your own decision question; recommend an answer and wait for the user's explicit yes.
6. Write every default you choose into the spec as an assumption.
7. Save each answer to the decisions file the moment it is given.
8. Silence, "just do it", and your own judgement that the spec is fine are not approval.
9. Only the main conversation talks to the user; agents never ask the user anything.
10. Never name, detect or invoke any tool that might consume the spec.
11. After the user approves the spec and the Steps, change neither without asking for approval again.
12. Never comment on, ask about or offer to change whether git tracks interphase's own output files, in anything you say or ask, or in the spec, decisions or items files.
13. Never plan a copy of logic that already exists, and never bend existing code to fit a new use; follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md`.
14. Keep the interview in the record: write each environment, fact, criterion and Step to `docs/specs/<slug>.record.json` the moment it is found or settled, and after any summary of the conversation, re-read the record and the decisions file before acting.
15. Rules 5 and 8 give way only to explicit instructions to work autonomously; then follow the section Work autonomously of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` in place of every question and approval.

## Phase 1: Intake

- When the request names a spec in the spec folder whose record says `handed-off` and asks to add a case to it or fix a gap in it, follow the section Amend a handed-off spec instead of the phases below.
- Run every command in these phases from the repository root, the folder `git rev-parse --show-toplevel` prints.
- Record the request word for word. It becomes section 1 of the spec.
- Choose a slug in lowercase kebab-case, at most 40 characters, drawn from the request. State it.
- Use `docs/specs/` at the repository root as the spec folder. Create it if it does not exist.
- Take the guard snapshot: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tree_guard.py" snapshot --repo . --owned "docs/specs/<slug>." --out docs/specs/<slug>.guard.json`.
- Create `docs/specs/<slug>.decisions.md` with the heading `# Decisions for <title>` and one sentence: `Questions the user settled. These are binding.`
- Create `docs/specs/<slug>.record.json` holding `{"environments": [], "facts": [], "criteria": [], "steps": [], "status": "in-progress"}`. Its format is in the section "Interview record" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`.
- If the directory is not a git repository, skip the guard. Say so.

## Phase 2: Classify

- Choose the pathway: use project for a new repository, or for replacing an existing repository's stack, build, CI or release; use feature for anything else that does not exist yet; use bug when existing behaviour is wrong; use prototype for a mockup or design to ship as a working product.
- A new product built from a design mixes project and prototype; recommend a project spec first and a prototype spec second.
- Choose the size. Use small for one or more items, each one behaviour in existing code describable in one sentence; whether a small request takes the brief lane is confirmed at the end of Phase 3, following `${CLAUDE_PLUGIN_ROOT}/core/brief.md`. Use standard for most requests. Use large for a new subsystem or several connected behaviours.
- When the request is large, mixes pathways or spans independent subsystems, ask the pathway, the size and how to split it with AskUserQuestion before phase 3, with your recommendation first. Otherwise say both out loud in one sentence, for example "This looks like a small bug, so I'll use the bug pathway." Let the user override.
- Recommend splitting a request that mixes pathways, such as a bug plus a new feature, or that spans several independent subsystems, into separate specs. Split it when the user agrees, and ask which to do first.
- Let size set depth. A small request takes the brief lane when the conditions in `${CLAUDE_PLUGIN_ROOT}/core/brief.md` hold. Give a small request few questions, one Step per item and no question about how the work is cut, and mark template sections `Not applicable: <reason>` where they do not apply. Give a large request the full treatment.

## Phase 3: Ground

- Read before asking. Learn the project's layout, language, test framework, the command that runs one test, its conventions, and the code the request touches.
- Follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md` to find what already exists and the project's own written rules.
- Learn what the Steps will need: the files each behaviour touches, where its tests live, the package export files beside them, and any interface two parts will share.
- Learn where the user sees the result: the device, operating system, runtime, renderer, screen size and window chrome, and where the project's tests run. Record each as an environment in the record, marking whether the builder can run it.
- Follow the `## Ground` section of `${CLAUDE_PLUGIN_ROOT}/core/pathways/<pathway>.md` for the pathway-specific investigation: feature research, bug reproduction, prototype exploration.
- Read the code you need to understand yourself. Dispatch the `interphase:scout` agent only for outside documentation, or for a question whose answer is where something is in the code, with one self-contained question. Record each fact you keep in the record with its citation: the path, the line and the quoted text; the URL; or the command and what it showed.
- Run every fact about software outside the repository, such as a tool's flags, an interface's reply or what a version accepts, and record it with `outside: true`, the command and what it showed. Run it far enough to see every class the code will tell apart, not only the names of the fields it returns. Documentation and memory are never the evidence for such a fact. When it cannot be run here, because it needs the user's device, a live service or a paid account, record it with `outside: true` and `assumed` set to why it could not be run, never only as an assumption in the spec.
- When the code would read one value to learn another, such as a file's extension to learn its format, a country code to learn a time zone or a screen width to learn the device, find where the two can differ. Read the value the behaviour depends on, or give the domain a class where the two differ.
- When a finding needs something only the user can provide, such as their device, their presence or repeated measurement, ask for it once and carry on with every other phase. Never end a turn only to wait for it. If it is still unavailable when you write the spec, keep the finding and mark it unconfirmed.
- Mark every behaviour the request touches that varies from run to run, following `${CLAUDE_PLUGIN_ROOT}/core/variation.md`.
- Treat every fact found here as a question not asked.
- Read the decisions files of earlier specs in the spec folder that touch the same code, to spot any decision this request would override.
- When the request is small, end the phase by checking the conditions in `${CLAUDE_PLUGIN_ROOT}/core/brief.md` and choosing the lane.

## Phase 4: Interrogate

- Follow `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`.
- Use the `## Questions` bank of `${CLAUDE_PLUGIN_ROOT}/core/pathways/<pathway>.md` as the checklist of what must be known.
- Design the Steps as the interview goes. When a requirement is settled, write its acceptance criterion to the record, with the environments where passing proves it and the tests that prove it or the reason it is unproven, and give it an owning Step in the record: what the Step builds, the files it changes and the test that proves it. Follow the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`.
- Draw the change's boundary from the request, before any domain, and keep it: settling a review issue never moves it. Inside it is the behaviour the request asks to add or alter, and existing code that behaviour newly calls or newly routes input into. Outside it is existing behaviour the change neither alters nor newly reaches: state it as Unchanged, give it no domain, and never redesign it. The values that reach the changed code from unchanged code in front of it are what that code lets through: read that code and cite it by path, line and quote. A value that reached the same existing code with the same result before the change, and still does, keeps that result when it breaks nothing the request asks for: give it a class whose result is that existing behaviour, cite the code that gives it by path, line and quote, and add no behaviour for it. A defect found outside the boundary, such as unchanged code that fails on some input before the changed code sees it, is never a criterion or a Step: record it as a fact and report it in phase 10.
- Write each criterion as a case table. For every input that behaviour inside the boundary reads, add a domain: what varies, its `source`, and every class of it the code tells apart, drawn from where its values are defined, never from a description of them. A domain's `source` is `outside` when a program, tool, system or service outside the repository produces its values, even when the repository's code parses them; its `fact` is then a fact marked outside. It is `person` when a person types, picks or says its values; its `fact` then cites, by path, line and quote or by command and output, where the repository asks for them, or `defined_by` names the Step that will. It is `stored` when the repository's own code wrote its values earlier, to a file, a database or another store, and reads them back; its `fact` then cites where the repository writes them, or `defined_by` names the Step that will. It is `sent` when the repository's own code in another process, such as its client, a producer or another deployed version, sends its values over a network, a queue, a pipe or another channel the code reads from; its `fact` then cites where the repository sends them, or `defined_by` names the Step that will. Anything else that can reach that channel can send it values too. Otherwise its `source` is `repo`, and its `fact` cites, by path, line and quote or by command and output, where the repository defines the values, or `defined_by` names the Step that will define them. A Step named in `defined_by` proves the domain's criterion or comes before a Step that does. When nothing where the values are defined bounds a value's size or count, give the domain a class beyond every bound the behaviour sets. Give every class a row: one named test with what is given, what is expected and the classes it covers. A criterion that says every, each, any, all, whole, always, never, whatever, however or whenever needs a domain over each kind of thing the word ranges over.
- Give every outside, person, stored or sent domain `invalid`: the classes for input that arrives other than promised, such as missing, empty, malformed, of another type, cut short or written by an older version. A behaviour that exists to refuse something refuses on every invalid class, unless the user decides otherwise and the decision is recorded. An autonomous run never lets an invalid class through such a behaviour, whatever the request's wording.
- Mark every domain `closed`: `true` when every value the input can take falls in one of its classes and every value in a class gets the same result, otherwise `false`. Phase 5 settles every domain marked `false`.
- Give every Step `reads`: the names of the domains, from the criteria it proves, of every input its code reads, or an empty list when it reads none. When its code reads an input no domain covers, add the domain first.
- When a criterion sets a bound, such as at most, no more than, up to, a maximum, a budget, a limit, a cap or exceeding something, list in `gives_way` what gives way first to last when the bound is reached, and in `keeps` what never gives way, including everything the criterion promises. Give every give-way item a row, and every kept item a row in which every give-way item gives way and the kept item still holds.
- Ask about the shape of the work in the same rounds as the other questions: what must ship together, what order matters and what could be thrown away. Look up the files, tests and export files each Step needs; ask only when the code is silent.
- Write each criterion for a varying behaviour with its kind and its population, following `${CLAUDE_PLUGIN_ROOT}/core/variation.md`.
- After every question round, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" docs/specs/<slug>.record.json`. Fix every error before the next round.

## Phase 5: Challenge

- In the brief lane, follow `${CLAUDE_PLUGIN_ROOT}/core/brief.md`.
- Audit assumptions. List what you are assuming. Ask about the ones that matter and have no evidence.
- Run a pre-mortem. Ask: "Imagine this shipped and you are unhappy with it. Why?"
- Push back on scope using the section "Push back on scope" of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`.
- Record at least one non-goal.
- Check that every domain is closed. A class for every other value does not close a domain when some of those values need a different result. When the classes of an input cannot all be listed, because it is free text, a shell command, arbitrary configuration or anything else open-ended, recommend a design that makes the decision where every input can be listed, such as one entry point that receives them already parsed, and settle it as any other decision. A mechanism the request names does not settle an open domain: in an autonomous run, choose the design that closes it and record the choice as a decision that overrides the request's wording. Keep `closed: false` only on a criterion that varies from run to run, or when the user decides to keep the domain open: record that decision and name in `open_by` the fact that cites its line in the decisions file. A behaviour that exists to refuse something never keeps its domain open, and an autonomous run never keeps a domain open by `open_by`.

## Phase 6: Design the Steps

- Check the whole set of Steps against the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`.
- Settle what needs the whole picture: files two Steps share, package export files, interfaces two Steps share, and the order the Steps are built in.
- Make sure every acceptance criterion has a Step whose test proves it where passing counts, or is marked unproven with the reason, and that every Step proves at least one criterion.
- Ask the user any Step question only they can answer. Save each answer to the decisions file.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" --complete docs/specs/<slug>.record.json`. Fix every error.

## Phase 7: Read back

- In the brief lane, follow `${CLAUDE_PLUGIN_ROOT}/core/brief.md`.
- Write a short note with five headings: What you told me, What I am assuming, What is out of scope, How we will know it works, How the work is cut.
- Under How the work is cut, list each Step in plain language: what it builds, the criteria it proves and the Steps it comes after.
- Ask for approval with AskUserQuestion, with the options "Approve" and "Change something".
- Loop until the user approves.

## Phase 8: Write the spec and the Steps

- Copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-<pathway>.md` to `docs/specs/<slug>.md`. In the brief lane, copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-brief.md` instead of the pathway template.
- Fill every section except Acceptance criteria. Replace every `{{placeholder}}` outside it.
- Fill the Review bar section: name each threat the change must withstand and its level of defence, taking them from the security needs settled in the interview and stated in the spec and, in an autonomous run, from the threats the section Work autonomously of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` lists, or say it has none beyond its acceptance criteria and why. Keep every threat it names defended somewhere in the spec, name the sections of the spec a reviewer may block on beyond the acceptance criteria, and name what is out of scope for review, at least weaknesses the code had before the change and hardening beyond the named threats. In the brief lane, write all of it in one or two lines.
- Keep every numbered heading exactly as the template has it.
- Give every requirement an acceptance criterion that can pass or fail.
- Write each requirement once, in its acceptance criterion. Every line of Requirements, Edge cases, Expected and Unchanged cites the number of the criterion that states it, such as 7.3, and says no more than that criterion does.
- Put every default into the Assumptions section.
- Leave at most three open questions. Say for each why it is safe to leave open.
- Write each Step's task into its entry in the record, following the section "Writing a task" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`. Never derive the Steps by reading them back out of the spec.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_record.py" --record docs/specs/<slug>.record.json --spec docs/specs/<slug>.md --items docs/specs/<slug>.items.json`. It writes the Acceptance criteria section, one numbered heading per criterion such as `### 7.1 <short name>`, and the items file, with the spec's absolute path and SHA-256 in every Step's `source`.
- After any edit to the spec, rewrite `source.sha256`. Rerun the render script after any edit to the record or the spec; it rewrites both.

## Phase 9: Review

- In the brief lane, follow `${CLAUDE_PLUGIN_ROOT}/core/brief.md`.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_spec.py" --template "${CLAUDE_PLUGIN_ROOT}/core/templates/spec-<pathway>.md" docs/specs/<slug>.md`.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" docs/specs/<slug>.items.json`.
- Fix every error. Read every warning and fix the ones that are real.
- Dispatch the `interphase:spec-reviewer` agent with the spec path, the items path, the record path, the decisions path and the path of `${CLAUDE_PLUGIN_ROOT}/core/practices.md`, and say whether the run is autonomous. This first review reads the whole spec. Fix the issues it finds that would cause the wrong thing to be built.
- As soon as a review returns, before changing anything, copy the `json` block that ends it, unchanged, to the end of the record's `reviews`, and add to it `reviewed`, set to what `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" --digest docs/specs/<slug>.record.json` prints. Then copy the spec and the record to `docs/specs/<slug>.review-copy.md` and `docs/specs/<slug>.review-copy.json`, replacing any earlier copies. Never remove a review. When the reply has no `json` block holding one JSON object, record nothing and dispatch a fresh reviewer for the same review. When the record check refuses a review of the record as it stands, write in the decisions file what it refused and why, add to the record a fact that cites that line, fix what the review reports, and dispatch a follow-up review. When it reports a review with no `reviewed` or one that is not a digest, set `reviewed` to what `--digest` printed when that review returned, or, when that is not known, to 64 zeros, which marks it as a review of an earlier version, and dispatch a follow-up review. When it reports an entry that is not an object, which holds no review, remove that entry and dispatch a fresh reviewer for the same review.
- Settle every issue it reports under Missing input, Missing class, Stand-in, Source, Outside fact, Invalid input, Give-way or Open domain: change the record to cover it, or, when the issue concerns behaviour outside the change's boundary or a class that cannot reach the changed code, add a fact that shows so by path, line and quote or by command and output. Settle each issue with the least the record needs: a class that keeps the existing result, as phase 4 describes, when the value reached it before the change; otherwise a refusal with a fixed answer that reads no further input; and new behaviour only where the request needs it. Removing behaviour an earlier settlement added that the request does not need also settles the issues in it. New behaviour a settlement adds reads no input that no domain covers: write its domains, classes and rows in the same change, before the follow-up review. Then rerun the record check with `--complete` and every render, spec check and items check this run has run, with the same arguments, which in an amendment includes those with `--amendment`. After any change that follows a review, write the change since that review with `diff -u docs/specs/<slug>.review-copy.md docs/specs/<slug>.md > docs/specs/<slug>.review-diff.txt` and `diff -u docs/specs/<slug>.review-copy.json docs/specs/<slug>.record.json >> docs/specs/<slug>.review-diff.txt`, running the second whatever the first exits with, since `diff` exits 1 when the files differ, and dispatch a fresh reviewer for a follow-up review, giving it the same paths, the path of that file and the issues of the last review. Stop when a review leads to no change; the record check hands off only when that review reports none of those eight categories. Any change to the record or the spec after the last review needs a follow-up review too: the record check refuses to hand off a record whose record or spec changed after its last review, and one that any review of them as they stand found an input issue in.
- A follow-up review that reports at least one issue, and no fewer issues than the review before it, makes no progress: change nothing more for it. When none of its issues falls under those eight categories, go on to phase 10 and list them as top risks. Otherwise, in an attended run, show the user those issues and ask how to settle each; in an autonomous run, copy each of those issues, unchanged, to the record's `open_issues`, go on to phase 10 and list them first among the top risks. An autonomous run always ends with a handed-off spec.
- When the user decides that an issue reported under one of those eight categories is wrong, record the decision with its reason, add to the record a fact that cites its line in the decisions file, and dispatch a follow-up review, which reads the decisions file. An autonomous run never settles such an issue by its own judgement: it changes the record, or adds a fact showing that the issue lies outside the change or concerns a class that cannot reach the changed code, until a follow-up review no longer reports it.
- Show the user what changed in review.
- Ask for approval of the written spec and the Steps with AskUserQuestion. Loop until approved.
- Once the user approves, change neither the spec nor the items file. Save the approval to the decisions file, then go straight to Phase 10 in the same turn. If you find something to change, reopen this phase: edit, rewrite `source.sha256`, rerun both checks and ask for approval again.

## Phase 10: Hand off

- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tree_guard.py" verify --repo . --snapshot docs/specs/<slug>.guard.json`. The guard first removes the caches that running the project's code created since the snapshot.
- If it reports a difference, stop. Tell the user exactly what changed.
- Delete `docs/specs/<slug>.guard.json` after a clean verify.
- Set the record's `status` to `handed-off`.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" --complete docs/specs/<slug>.record.json`. When it reports an error, set the `status` back to `in-progress`, take the guard snapshot as in phase 1 and reopen phase 9.
- When that check reports no error, delete `docs/specs/<slug>.review-copy.md`, `docs/specs/<slug>.review-copy.json` and `docs/specs/<slug>.review-diff.txt`.
- Report the paths of the spec, the decisions file, the record, the items file and, for bugs, the reproduction file.
- List every issue in the record's `open_issues` first, as the top risks.
- List next every criterion marked unproven, with its reason, as top risks.
- List next every fact marked `assumed`, with its reason, as top risks.
- In an autonomous run, list next every decision that overrides a line of an earlier decisions file, a written rule or convention of the project or the request's own wording, then every other decision made on the user's behalf, as top risks.
- Report every fact that records a defect found outside the change, under the heading Found outside the change.
- Report the counts of Steps, unproven criteria, assumptions and open questions.
- Stop. Do not suggest a tool to build it. Do not start building it.

## Amend a handed-off spec

- Keep the slug, the spec, the decisions file and the record. Never start a new spec for a case a handed-off spec missed.
- Take the guard snapshot as in phase 1, and set the record's `status` to `in-progress`.
- When the record's tests carry `asserts`, rewrite each as `given` and `expect`. Add the domains, give-way orders, `source`, `closed`, `invalid`, `keeps` and `reads` the record check asks for.
- Number the amendment one more than the highest `amendment` of any Step in the record, or 1 when no Step has one.
- Add the missing classes, give-way items, facts and rows to the criteria they belong to. Add a criterion only for a behaviour no criterion states.
- Give every new row's test to a new Step with `amendment` set to that number, the files it changes, `after` naming the Steps whose code it changes, and a task written as in phase 8.
- Save each decision to the decisions file, follow phases 5 and 6 for what changed, and run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" --complete docs/specs/<slug>.record.json`.
- Run the render script as in phase 8, then again with `--amendment <n>` and `--items docs/specs/<slug>.amend-<n>.items.json`.
- Run the spec check as in phase 9, and the items check with `--amendment` on the amendment items file.
- Dispatch the `interphase:spec-reviewer` agent as in phase 9, passing the amendment items file beside the items file and naming the criteria and the Step that changed, and record each review as in phase 9. Fix every input issue a review reports, in any criterion, as in phase 9, giving each new row's test to a new Step of this amendment, and get approval as in phase 9.
- Hand off as in phase 10, and report the amendment items file in place of the items file.
