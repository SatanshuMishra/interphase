# Shared phases

The goal is not a perfect spec. It is that the user's intent is met. A missed intent means major rework; a cosmetic inconsistency can be fixed later. Every rule below serves that trade.

## Rules

1. Never create, edit or delete a tracked file in the user's working tree, except adding the spec folder to .gitignore when the user chooses that in phase 1.
2. Never commit, push, stash, reset, check out or rebase in the user's repository.
3. Never implement: the spec states the cause, the boundary and the acceptance test, never the patch.
4. Look up facts yourself; ask the user only for decisions.
5. Never answer your own decision question; recommend an answer and wait for the user's explicit yes.
6. Write every default you choose into the spec as an assumption.
7. Save each answer to the decisions file the moment it is given.
8. Silence, "just do it", and your own judgement that the spec is fine are not approval.
9. Only the main conversation talks to the user; agents never ask the user anything.
10. Never name, detect or invoke any tool that might consume the spec.

## Phase 1: Intake

- Run every command in these phases from the repository root, the folder `git rev-parse --show-toplevel` prints.
- Record the request word for word. It becomes section 1 of the spec.
- Choose a slug in lowercase kebab-case, at most 40 characters, drawn from the request. State it.
- Use `docs/specs/` at the repository root as the spec folder.
- Check the folder is ignored: `git check-ignore -q docs/specs/<slug>.md`.
- If it is not ignored, ask the user with AskUserQuestion whether to add `docs/specs/` to `.gitignore` (shared with everyone) or to `.git/info/exclude` (this machine only). Do exactly what they choose.
- Create the `docs/specs/` folder if it does not exist.
- Then take the guard snapshot: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tree_guard.py" snapshot --repo . --out docs/specs/<slug>.guard.json`.
- Create `docs/specs/<slug>.decisions.md` with the heading `# Decisions for <title>` and one sentence: `Questions the user settled. These are binding.`
- If the directory is not a git repository, skip the ignore check and the guard. Say so.

## Phase 2: Classify

- Choose the pathway. Use feature for something that does not exist yet. Use bug when existing behaviour is wrong. Use prototype for a mockup or design to ship as a working product.
- Choose the size. Use small for one behaviour in existing code, describable in one sentence. Use standard for most requests. Use large for a new subsystem or several connected behaviours.
- Say both out loud in one sentence, for example "This looks like a small bug, so I'll use the bug pathway." Let the user override.
- Split a request that mixes pathways, such as a bug plus a new feature, into separate specs. Ask which to do first.
- Split a request that spans several independent subsystems into separate specs before asking any detail.
- Let size set depth. Give a small request few questions, and mark template sections `Not applicable: <reason>` where they do not apply. Give a large request the full treatment.

## Phase 3: Ground

- Read before asking. Learn the project's layout, language, test framework, the command that runs one test, its conventions, and the code the request touches.
- Follow the `## Ground` section of `${CLAUDE_PLUGIN_ROOT}/core/pathways/<pathway>.md` for the pathway-specific investigation: feature research, bug reproduction, prototype exploration.
- For broad searches or outside documentation, dispatch the `interphase:scout` agent with one self-contained question. Use its cited answer.
- Treat every fact found here as a question not asked.

## Phase 4: Interrogate

- Follow `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`.
- Use the `## Questions` bank of `${CLAUDE_PLUGIN_ROOT}/core/pathways/<pathway>.md` as the checklist of what must be known.

## Phase 5: Challenge

- Audit assumptions. List what you are assuming. Ask about the ones that matter and have no evidence.
- Run a pre-mortem. Ask: "Imagine this shipped and you are unhappy with it. Why?"
- Push back on scope using the section "Push back on scope" of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`.
- Record at least one non-goal.

## Phase 6: Read back

- Write a short note with four headings: What you told me, What I am assuming, What is out of scope, How we will know it works.
- Ask for approval with AskUserQuestion, with the options "Approve" and "Change something".
- Loop until the user approves.

## Phase 7: Write the spec

- Copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-<pathway>.md` to `docs/specs/<slug>.md`.
- Fill every section. Replace every `{{placeholder}}`.
- Keep every numbered heading exactly as the template has it.
- Give every requirement an acceptance criterion that can pass or fail.
- Put every default into the Assumptions section.
- Leave at most three open questions. Say for each why it is safe to leave open.

## Phase 8: Review

- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_spec.py" --template "${CLAUDE_PLUGIN_ROOT}/core/templates/spec-<pathway>.md" docs/specs/<slug>.md`.
- Fix every error. Read every warning and fix the ones that are real.
- Dispatch the `interphase:spec-reviewer` agent with the spec path. Fix the issues it finds that would cause the wrong thing to be built.
- Show the user what changed in review.
- Ask for approval of the written spec with AskUserQuestion. Loop until approved.

## Phase 9: Split into Steps

- Follow `${CLAUDE_PLUGIN_ROOT}/core/items.md`.
- Write the Work breakdown section of the spec first.
- Then treat the spec as final.
- Then write `docs/specs/<slug>.items.json` with the spec's absolute path and SHA-256 in `source`.
- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" docs/specs/<slug>.items.json` and fix every error.
- After any later edit to the spec, rewrite `source.sha256` and rerun the check.

## Phase 10: Hand off

- Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tree_guard.py" verify --repo . --snapshot docs/specs/<slug>.guard.json`.
- If it reports a difference, stop. Tell the user exactly what changed.
- Delete `docs/specs/<slug>.guard.json` after a clean verify.
- Report the paths of the spec, the decisions file, the items file and, for bugs, the reproduction file.
- Report the counts of Steps, assumptions and open questions.
- Stop. Do not suggest a tool to build it. Do not start building it.
