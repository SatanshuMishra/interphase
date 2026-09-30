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

## Phase 1: Intake

- Run every command in these phases from the repository root, the folder `git rev-parse --show-toplevel` prints.
- Record the request word for word. It becomes section 1 of the spec.
- Choose a slug in lowercase kebab-case, at most 40 characters, drawn from the request. State it.
- Use `docs/specs/` at the repository root as the spec folder. Create it if it does not exist.
- Take the guard snapshot: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tree_guard.py" snapshot --repo . --owned "docs/specs/<slug>." --out docs/specs/<slug>.guard.json`.
- Create `docs/specs/<slug>.decisions.md` with the heading `# Decisions for <title>` and one sentence: `Questions the user settled. These are binding.`
- Create `docs/specs/<slug>.record.json` holding `{"environments": [], "facts": [], "criteria": [], "steps": []}`. Its format is in the section "Interview record" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`.
- If the directory is not a git repository, skip the guard. Say so.

## Phase 2: Classify

- Choose the pathway. Use feature for something that does not exist yet. Use bug when existing behaviour is wrong. Use prototype for a mockup or design to ship as a working product.
- Choose the size. Use small for one behaviour in existing code, describable in one sentence. Use standard for most requests. Use large for a new subsystem or several connected behaviours.
- When the request is large, mixes pathways or spans independent subsystems, ask the pathway, the size and how to split it with AskUserQuestion before phase 3, with your recommendation first. Otherwise say both out loud in one sentence, for example "This looks like a small bug, so I'll use the bug pathway." Let the user override.
- Recommend splitting a request that mixes pathways, such as a bug plus a new feature, or that spans several independent subsystems, into separate specs. Split it when the user agrees, and ask which to do first.
- Let size set depth. Give a small request few questions, one Step and no question about how the work is cut, and mark template sections `Not applicable: <reason>` where they do not apply. Give a large request the full treatment.

## Phase 3: Ground

- Read before asking. Learn the project's layout, language, test framework, the command that runs one test, its conventions, and the code the request touches.
- Follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md` to find what already exists and the project's own written rules.
- Learn what the Steps will need: the files each behaviour touches, where its tests live, the package export files beside them, and any interface two parts will share.
- Learn where the user sees the result: the device, operating system, runtime, renderer, screen size and window chrome, and where the project's tests run. Record each as an environment in the record, marking whether the builder can run it.
- Follow the `## Ground` section of `${CLAUDE_PLUGIN_ROOT}/core/pathways/<pathway>.md` for the pathway-specific investigation: feature research, bug reproduction, prototype exploration.
- Read the code you need to understand yourself. Dispatch the `interphase:scout` agent only for outside documentation, or for a question whose answer is where something is in the code, with one self-contained question. Record each fact you keep in the record with its citation: the path, the line and the quoted text; the URL; or the command and what it showed.
- When a finding needs something only the user can provide, such as their device, their presence or repeated measurement, ask for it once and carry on with every other phase. Never end a turn only to wait for it. If it is still unavailable when you write the spec, keep the finding and mark it unconfirmed.
- Treat every fact found here as a question not asked.

## Phase 4: Interrogate

- Follow `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`.
- Use the `## Questions` bank of `${CLAUDE_PLUGIN_ROOT}/core/pathways/<pathway>.md` as the checklist of what must be known.
- Design the Steps as the interview goes. When a requirement is settled, write its acceptance criterion to the record, with the environments where passing proves it and the tests that prove it or the reason it is unproven, and give it an owning Step in the record: what the Step builds, the files it changes and the test that proves it. Follow the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`.
- Ask about the shape of the work in the same rounds as the other questions: what must ship together, what order matters and what could be thrown away. Look up the files, tests and export files each Step needs; ask only when the code is silent.
- After every question round, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" docs/specs/<slug>.record.json`. Fix every error before the next round.

## Phase 5: Challenge

- Audit assumptions. List what you are assuming. Ask about the ones that matter and have no evidence.
- Run a pre-mortem. Ask: "Imagine this shipped and you are unhappy with it. Why?"
- Push back on scope using the section "Push back on scope" of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`.
- Record at least one non-goal.

## Phase 6: Design the Steps

- Check the whole set of Steps against the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`.
- Settle what needs the whole picture: files two Steps share, package export files, interfaces two Steps share, and the order the Steps are built in.
- Make sure every acceptance criterion has a Step whose test proves it where passing counts, or is marked unproven with the reason, and that every Step proves at least one criterion.
- Ask the user any Step question only they can answer. Save each answer to the decisions file.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" --complete docs/specs/<slug>.record.json`. Fix every error.

## Phase 7: Read back

- Write a short note with five headings: What you told me, What I am assuming, What is out of scope, How we will know it works, How the work is cut.
- Under How the work is cut, list each Step in plain language: what it builds, the criteria it proves and the Steps it comes after.
- Ask for approval with AskUserQuestion, with the options "Approve" and "Change something".
- Loop until the user approves.

## Phase 8: Write the spec and the Steps

- Copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-<pathway>.md` to `docs/specs/<slug>.md`.
- Fill every section except Acceptance criteria. Replace every `{{placeholder}}` outside it.
- Keep every numbered heading exactly as the template has it.
- Give every requirement an acceptance criterion that can pass or fail.
- Put every default into the Assumptions section.
- Leave at most three open questions. Say for each why it is safe to leave open.
- Write each Step's task into its entry in the record, following the section "Writing a task" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`. Never derive the Steps by reading them back out of the spec.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_record.py" --record docs/specs/<slug>.record.json --spec docs/specs/<slug>.md --items docs/specs/<slug>.items.json`. It writes the Acceptance criteria section, one numbered heading per criterion such as `### 7.1 <short name>`, and the items file, with the spec's absolute path and SHA-256 in every Step's `source`.
- After any edit to the spec, rewrite `source.sha256`. Rerun the render script after any edit to the record or the spec; it rewrites both.

## Phase 9: Review

- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_spec.py" --template "${CLAUDE_PLUGIN_ROOT}/core/templates/spec-<pathway>.md" docs/specs/<slug>.md`.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" docs/specs/<slug>.items.json`.
- Fix every error. Read every warning and fix the ones that are real.
- Dispatch the `interphase:spec-reviewer` agent with the spec path, the items path, the decisions path and the path of `${CLAUDE_PLUGIN_ROOT}/core/practices.md`. Fix the issues it finds that would cause the wrong thing to be built.
- Show the user what changed in review.
- Ask for approval of the written spec and the Steps with AskUserQuestion. Loop until approved.
- Once the user approves, change neither the spec nor the items file. Save the approval to the decisions file, then go straight to Phase 10 in the same turn. If you find something to change, reopen this phase: edit, rewrite `source.sha256`, rerun both checks and ask for approval again.

## Phase 10: Hand off

- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tree_guard.py" verify --repo . --snapshot docs/specs/<slug>.guard.json`. The guard first removes the caches that running the project's code created since the snapshot.
- If it reports a difference, stop. Tell the user exactly what changed.
- Delete `docs/specs/<slug>.guard.json` after a clean verify.
- Report the paths of the spec, the decisions file, the record, the items file and, for bugs, the reproduction file.
- List every criterion marked unproven first, with its reason, as the top risks.
- Report the counts of Steps, unproven criteria, assumptions and open questions.
- Stop. Do not suggest a tool to build it. Do not start building it.
