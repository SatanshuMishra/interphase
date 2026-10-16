# Shared phases

The goal is not a perfect spec. It is that the user's intent is met. A missed intent means major rework; a cosmetic inconsistency can be fixed later. Every rule below serves that trade.

A run has two parts. The interview, phases 3 to 7, is attended: the user answers rounds of questions and approves the read-back. From then on the run is autonomous to the end: it asks nothing and stops for nothing, and fills every gap from the recorded intent. An unattended run skips the interview altogether.

## Rules

1. Never create, edit or delete a file in the user's working tree, except interphase's own output files: this run's files in the spec folder, the glossary files and the ADRs `${CLAUDE_PLUGIN_ROOT}/core/domain.md` describes.
2. Never commit, push, stash, reset, check out or rebase in the user's repository.
3. Never implement: the spec states the cause, the decisions and the acceptance tests, never the patch.
4. Look up facts yourself; ask the user only for decisions that pass the hard bar of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`.
5. During the interview, never answer your own decision question; recommend an answer and wait for the user's reply.
6. Silence, "just do it", and your own judgement that the spec is fine do not approve the read-back.
7. After the user approves the read-back, ask nothing more: fill every gap as the section After the interview of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` says, and never stop for an answer.
8. Save each answer to the decisions file the moment it is given.
9. Only the main conversation talks to the user; agents never ask the user anything.
10. Never name, detect or invoke any tool that might consume the spec.
11. Never comment on, ask about or offer to change whether git tracks interphase's own output files, in anything you say or ask, or in the spec, decisions or items files.
12. Never plan a copy of logic that already exists, and never bend existing code to fit a new use; follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md`.
13. Keep the interview in the record: write each seam, criterion and Step to `docs/specs/<slug>.record.json` the moment it is settled, and after any summary of the conversation, re-read the record and the decisions file before acting.
14. When the user's instructions say to work autonomously, the run is unattended: follow the section Unattended runs of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` in place of every question and approval.

## Phase 1: Intake

- When the request names a spec in the spec folder whose record says `handed-off` and asks to add a case to it or fix a gap in it, follow the section Amend a handed-off spec instead of the phases below.
- Run every command in these phases from the repository root, the folder `git rev-parse --show-toplevel` prints.
- Record the request word for word. It opens section 1 of the spec.
- Choose a slug in lowercase kebab-case, at most 40 characters, drawn from the request. State it.
- Use `docs/specs/` at the repository root as the spec folder. Create it if it does not exist.
- Take the guard snapshot: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tree_guard.py" snapshot --repo . --owned "docs/specs/<slug>." --owned GLOSSARY --owned docs/adr/ --out docs/specs/<slug>.guard.json`. When a `GLOSSARY-MAP.md` exists, add one `--owned` for each glossary and each ADR folder it names.
- Create `docs/specs/<slug>.decisions.md` with the heading `# Decisions for <title>`, the sentence `Questions the user settled. These are binding.`, then an empty `## Intent` section and an empty `## Decisions` section.
- Create `docs/specs/<slug>.record.json` holding `{"seams": [], "criteria": [], "steps": [], "status": "in-progress"}`. Its format is in the section "Interview record" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`.
- If the directory is not a git repository, skip the guard. Say so.

## Phase 2: Classify

- Choose the pathway: use project for a new repository, or for replacing an existing repository's stack, build, CI or release; use feature for anything else that does not exist yet; use bug when existing behaviour is wrong; use prototype for a mockup or design to ship as a working product.
- A new product built from a design mixes project and prototype; recommend a project spec first and a prototype spec second.
- Choose the size. Use small for one or more items, each one behaviour in existing code describable in one sentence; whether a small request takes the brief lane is confirmed at the end of Phase 3, following `${CLAUDE_PLUGIN_ROOT}/core/brief.md`. Use standard for most requests. Use large for a new subsystem or several connected behaviours.
- Say the pathway and the size in one sentence, for example "This looks like a small bug, so I'll use the bug pathway." Let the user override. When the request is large, mixes pathways or spans independent subsystems, put the pathway, the size and the split in the intent round instead.
- Recommend splitting a request that mixes pathways, such as a bug plus a new feature, or that spans several independent subsystems, into separate specs.
- Let size set depth. A small request takes the brief lane when the conditions in `${CLAUDE_PLUGIN_ROOT}/core/brief.md` hold. Give a small request few questions, one Step per item and no question about how the work is cut. Give a large request the full treatment.

## Phase 3: Ground

- Read before asking. Learn the project's layout, language, test framework, the command that runs one test, its conventions, and the code the request touches.
- Read the glossary and the ADRs in the area the request touches, following `${CLAUDE_PLUGIN_ROOT}/core/domain.md`, and the decisions files of earlier specs in the spec folder that touch the same code, to spot any decision this request would override.
- Follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md` to find what already exists and the project's own written rules.
- Learn what the Steps will need: the files each behaviour touches, where its tests live, the package export files beside them, and any interface two parts will share.
- Find the seams the project already tests at, and where the user sees the result: the device, runtime or renderer, and whether the builder can run tests there.
- Follow the `## Ground` section of `${CLAUDE_PLUGIN_ROOT}/core/pathways/<pathway>.md` for the pathway-specific investigation: feature research, bug reproduction, prototype exploration.
- Read the code you need to understand yourself. Dispatch the `interphase:scout` agent only for outside documentation, or for a question whose answer is where something is in the code, with one self-contained question.
- Run every fact about software outside the repository, such as a tool's flags, an interface's reply or what a version accepts, and write the command and what it showed into the decision that rests on it. Documentation and memory are never the evidence for such a fact. When it cannot be run here, because it needs the user's device, a live service or a paid account, write it into the spec as an assumption instead.
- When a finding needs something only the user can provide, such as their device, their presence or repeated measurement, put it in the next round and carry on with every other phase. Never end a turn only to wait for it. If it is still unavailable when you write the spec, or the run is unattended, keep the finding and mark it unconfirmed.
- Mark every behaviour the request touches that varies from run to run, following `${CLAUDE_PLUGIN_ROOT}/core/variation.md`.
- Treat every fact found here as a question not asked.
- When the request is small, end the phase by checking the conditions in `${CLAUDE_PLUGIN_ROOT}/core/brief.md` and choosing the lane.

## Phase 4: Interview

- Follow `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`: the intent round first, then frontier rounds until the frontier is empty.
- Use the `## Questions` bank of `${CLAUDE_PLUGIN_ROOT}/core/pathways/<pathway>.md` as a checklist of branches the tree must reach; skip every question grounding already answered.
- Design the seams and the Steps as the interview goes. When the user agrees a seam, write it to the record. When a requirement is settled, write its acceptance criterion to the record with its seam, the tests that prove it or the reason it is unproven, and an owning Step: what the Step builds, the files it changes and the test that proves it. Follow the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`.
- Give a criterion a few rows, each a named test with what it is given and what it expects.
- Write a case table only for behaviour that is security-sensitive, such as an input a person or outside software controls at a trust boundary or a result that could expose data, and for behaviour that exists to refuse something. Mark the criterion's `case_table` as `security` or `refusal`, add a domain for each input it reads, listing every class of that input the code tells apart that a real path can deliver, and give every class a row that covers it.
- Write each criterion for a varying behaviour with its kind and its population, following `${CLAUDE_PLUGIN_ROOT}/core/variation.md`.
- After every round, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" docs/specs/<slug>.record.json`. Fix every error before the next round.

## Phase 5: Challenge

- In the brief lane, follow `${CLAUDE_PLUGIN_ROOT}/core/brief.md`.
- Before the frontier empties, make sure the pre-mortem and the scope branches of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` were asked.
- List what you are still assuming. Put each assumption that passes the hard bar to the user as a question.
- Record at least one item for the spec's Out of scope section.
- Check that every case table's domains are closed. When the classes of an input cannot all be listed, because it is free text, a shell command, arbitrary configuration or anything else open-ended, recommend a design that makes the decision where every input can be listed, such as one entry point that receives them already parsed, and ask it like any other decision.

## Phase 6: Design the Steps

- Check the whole set of Steps against the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`.
- Settle what needs the whole picture: files two Steps share, package export files, interfaces two Steps share, and the order the Steps are built in.
- Make sure every acceptance criterion has a Step whose test proves it at an agreed seam the builder runs, or is marked unproven with the reason, and that every Step proves at least one criterion.
- Ask any Step question only the user can answer in the same rounds as the rest.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" --complete docs/specs/<slug>.record.json`. Fix every error.

## Phase 7: Read back

- In the brief lane, follow `${CLAUDE_PLUGIN_ROOT}/core/brief.md`.
- Write a short note with five headings: Intent, What we decided, What is out of scope, How we will know it works, How the work is cut.
- Under How we will know it works, name each seam and the criteria at it. Under How the work is cut, list each Step in plain language: what it builds, the criteria it proves and the Steps it comes after.
- Ask for approval with the AskUserQuestion tool, with the options "Approve" and "Change something". This is the only question the tool asks in a run.
- When the user changes something, settle it in a frontier round and read back again. Loop until the user approves.
- Save the approval to the decisions file. From here the run is autonomous to the end.

## Phase 8: Write the spec and the Steps

- Copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-<pathway>.md` to `docs/specs/<slug>.md`. In the brief lane, copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-brief.md` instead of the pathway template.
- Fill every section except Test seams. Replace every `{{placeholder}}` outside it.
- Copy the intent lines of the decisions file into the Intent section word for word.
- Write each decision once. Keep every numbered heading exactly as the template has it.
- Write every reading you chose without the user's answer into Assumptions, as the section After the interview of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` says.
- Write each Step's task into its entry in the record, following the section "Writing a task" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`. Never derive the Steps by reading them back out of the spec.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_record.py" --record docs/specs/<slug>.record.json --spec docs/specs/<slug>.md --items docs/specs/<slug>.items.json`. It writes the Test seams section, the agreed seams followed by one numbered heading per criterion such as `### 5.1 <short name>`, and the items file, with the spec's absolute path and SHA-256 in every Step's `source`.
- Rerun the render script after any edit to the record or the spec; it rewrites both.

## Phase 9: Review

- In the brief lane, follow `${CLAUDE_PLUGIN_ROOT}/core/brief.md`.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_spec.py" --template "${CLAUDE_PLUGIN_ROOT}/core/templates/spec-<pathway>.md" docs/specs/<slug>.md`.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" docs/specs/<slug>.items.json`.
- Fix every error. Read every warning and fix the ones that are real.
- Dispatch the `interphase:spec-reviewer` agent once, with the spec path, the items path, the decisions path and the path of `${CLAUDE_PLUGIN_ROOT}/core/practices.md`, and say whether the run is unattended. Fix once each issue it finds that would cause the wrong thing to be built, using your judgement: an issue that needs an input no real path delivers, or that the intent or a recorded decision already settles, is not one to fix. Fill any gap a fix opens as the section After the interview says. Never dispatch the reviewer again.
- Rerun the render script and both checks after the fixes.
- Ask nothing. Go straight to Phase 10 in the same turn.

## Phase 10: Hand off

- Promote what must outlast the spec into the glossary and the ADRs, following the section At hand-off of `${CLAUDE_PLUGIN_ROOT}/core/domain.md`.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tree_guard.py" verify --repo . --snapshot docs/specs/<slug>.guard.json`. The guard first removes the caches that running the project's code created since the snapshot.
- If it reports a difference, stop. Tell the user exactly what changed.
- Delete `docs/specs/<slug>.guard.json` after a clean verify.
- Set the record's `status` to `handed-off`.
- Report the paths of the spec, the decisions file, the record, the items file, every glossary file and ADR written and, for bugs, the reproduction file.
- List as top risks every criterion marked unproven first, with its reason, then every assumption with the intent line it relied on, those that override a line of an earlier decisions file, an ADR or a written rule or convention of the project first.
- Report what the review changed, and the counts of Steps, unproven criteria and assumptions.
- Stop. Do not suggest a tool to build it. Do not start building it.

## Amend a handed-off spec

- Keep the slug, the spec, the decisions file and the record. Never start a new spec for a case a handed-off spec missed.
- Take the guard snapshot as in phase 1, and set the record's `status` to `in-progress`.
- When the record was written by an earlier release, rewrite it to this release's shape: turn each entry of `environments` into a seam with `name`, `interface` set to its `what`, `catches`, `misses` and `builder_runs`; give each criterion the `seam` its tests ran at and remove its `where`, `facts` and `gives_way`; remove each test's `env` and every `gives-way:` entry from its `covers`; remove `facts`, `environments`, `reviews` and `open_issues` from the record; keep a criterion's `domains` only when it is security-sensitive or exists to refuse something, setting `case_table`, and otherwise remove its domains and every test's `covers`.
- When the spec was written by an earlier release, rename its `Acceptance criteria` heading to `Test seams`, keeping its number, and skip the spec check below, which knows only this release's templates.
- Number the amendment one more than the highest `amendment` of any Step in the record, or 1 when no Step has one.
- Add the missing classes and rows to the criteria they belong to. Add a criterion only for a behaviour no criterion states.
- Give every new row's test to a new Step with `amendment` set to that number, the files it changes, `after` naming the Steps whose code it changes, and a task written as in phase 8.
- Fill every gap from the intent as the section After the interview says, and run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" --complete docs/specs/<slug>.record.json`.
- Run the render script as in phase 8, then again with `--amendment <n>` and `--items docs/specs/<slug>.amend-<n>.items.json`.
- Run the spec check as in phase 9, and the items check with `--amendment` on the amendment items file.
- Dispatch the `interphase:spec-reviewer` agent as in phase 9, naming the criteria and the Step that changed.
- Hand off as in phase 10, and report the amendment items file in place of the items file.
