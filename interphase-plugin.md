# interphase-plugin: Build the interphase plugin: rough request to clear spec
Status: active
Updated: 2026-10-16T01:04:17.003Z
Next ids: c9 D13 R8 S4

## Goal

Create interphase, a standalone Claude Code plugin that interrogates a rough request (feature, bug, or prototype pathway) until intent is unambiguous and emits a traditional spec plus the resources mitosis's items entry pathway consumes. This session: research spec design per pathway, questioning technique, comparable skills, mitosis's input contract, and plugin mechanics, then break down interphase's core architecture in an in-line report.

## Done when

- [ ] c1 Report covers spec design for each pathway: feature, bug, prototype
- [ ] c2 Report covers what questions to ask to pin down user intent and objectives
- [ ] c3 Report covers how similar industry-standard skills work
- [ ] c4 Report covers what mitosis needs from interphase
- [ ] c5 Report covers how Claude Code plugins and skills work, as relevant to building interphase
- [ ] c6 Report breaks down interphase's core architecture
- [ ] c7 Report is in-line, plain English, small organized text, no large paragraphs, assumes no domain knowledge
- [ ] c8 interphase plugin is built, installable, and runs all three pathways end to end

## Where things stand

interphase 0.1.0 is built and merged to main at 48c6a83 (15 PRs), installed from its marketplace at user scope, and loads in a fresh session. Verified: 74 tests pass on Python 3.14 and 3.9 on main; claude plugin validate --strict passes; trigger evals pass 4/4 cases and 12/12 runs in isolation; one live trace shows interphase:bug firing and reading its core files. Not verified: a full interview run of any pathway to hand-off, the tree guard in real use, the checkers on real output, or precedence against receipts:gates. Completion criterion c8 stays open; c1 to c7 await the user's agreement with the research report.

## Next step

Start a new Claude Code session in a real project repository (so superpowers stays unloaded) and send one bug report in the form "X does Y instead of Z. Determine the cause."; confirm interphase:bug starts rather than receipts:gates, run the interview through phase 10, then run the plugin's scripts/check_spec.py with core/templates/spec-bug.md on docs/specs/U+003Cslug>.md and scripts/check_items.py on docs/specs/U+003Cslug>.items.json, and file anything that breaks with /interphase:bug.

## Decisions in force

- D1 Question format: open purpose question, then batched independent questions: User chose the recommendation on 2026-09-22: open purpose question first, then AskUserQuestion batches of up to 4 independent questions, one concept each, recommended option first.
- D2 Outputs flat under docs/specs, and specs and dev docs are always gitignored: User chose flat docs/specs/U+003Cslug>.md, U+003Cslug>.decisions.md, U+003Cslug>.items.json, and marked CRITICAL that specs and all development documentation are gitignored; only usage docs such as README.md are tracked. interphase never commits a spec.
- D3 Always write the items file, even without mitosis installed: User chose always write it; it doubles as a task list and costs nothing.
- D4 Prototype input: files, URLs and screenshots by default; design tools only when connected: User chose the baseline of files, URLs and screenshots, using Figma or Claude Design connectors only when present.
- D5 mitosis type is set only to contract, on the Step that pins a shared interface: User chose on 2026-09-22 to use type only as mitosis intends: "type": "contract" on the one Step that pins a contract_group interface, and no type field anywhere else. The spec and the Step task already say what the work is.
- D6 Pathways trigger automatically from the request; interphase and mitosis stay mutually unaware: Pathway skills are model-invocable, reversing the earlier user-typed-only recommendation. interphase never detects, names, invokes or suggests mitosis at runtime; mitosis never knows interphase. Chaining a spec into a build is the user's harness's job. interphase's items output is its own documented format that happens to match mitosis --items.
- D7 Bug reproduction test is kept as evidence and its text travels inside the Step task: User chose (b) on 2026-09-22. interphase saves the draft test next to the spec, records the observed failure in the spec's Evidence section, and puts the test text plus its target path in the Step task; the Step's files and acceptance name the target test. The builder creates it.
- D8 Items source.path is the spec's absolute path: User chose absolute source.path with the spec's sha256 on 2026-09-22. Justified on interphase's own terms: the items file never leaves the machine, and an absolute path lets any reader open the spec from anywhere.
- D9 README documents exactly what interphase produces, on its own terms: User chose on 2026-09-22: the README specifies each file interphase writes (spec, decisions log, items file) and every items field precisely, as interphase's own format. What a consumer does with it is not the README's concern; a single compatibility line is the most it says about any other tool.
- D10 Probe fixes allowed in the bug pathway, in a throwaway worktree only: User chose allow on 2026-09-22, under three rules: probes run only in a throwaway git worktree that is deleted afterwards; the spec keeps the evidence (hypothesis, one-line description of the change, result), never the change; interphase records git status at start and confirms it unchanged at the end. A probe must alter the suspected cause, not mask the symptom.
- D11 Build with mitosis --no-push; open pull requests afterwards through pr.mjs: Chose --no-push. mitosis builds, gates and reconciles every MSP on local branches cut from feat/interphase; nothing is published. Pull requests are opened afterwards through pr.mjs, with each MSP's gate verdict restated as --verified or --not-verified lines.
- D12 One pull request per part into feat/interphase, then one into main: User chose the first on 2026-09-22, after the conformance audit returns and any fixes land. Each pull request restates its gate verdicts as --verified lines. The user also updated the Homebrew claude CLI.

## Open risks

- R1 One-question-at-a-time versus batched questioning is contested: Tessl and superpowers brainstorming mandate one per message, Matt Pocock's grilling moved to whole-frontier batches on 2026-07-31, and the only direct comparison used a simulated user in a CAD task.
- R2 Whether AskUserQuestion can be driven inside claude plugin eval runs is unverified, so interviewer evals may need a pre-seeded history_file rather than live answers.
- R3 Gitignored specs never reach mitosis worktrees (verified: git worktree add omits ignored files; mitosis builds in git worktrees, run.py:166-175). A relative source.path leaves each builder brief pointing at a missing file. An absolute source.path kept drift and coverage working and put an openable path in the brief in a plan-only probe, but mitosis does not document absolute paths and the brief still says 'open it from your worktree'.
- R4 Auto-triggered pathway skills compete in the user's harness with superpowers:brainstorming (all creative work), superpowers:systematic-debugging (any bug, before proposing fixes) and receipts:gates (fixing a bug). Which skill Claude starts depends on description wording; precedence must be set in the harness and measured with claude plugin eval tool_used graders.
- R5 If mitosis changes its items format, interphase's items file stops matching. The spec document stays usable regardless: mitosis --spec reads any document and embeds its text in its structure and brief prompts (decompose.py:477, briefs.py:145), and it picks up U+003Cspec>.decisions.md by default. A harness can check items with mitosis --plan-only and fall back to --spec.
- R6 claude plugin eval runs each case in a sandbox with its own HOME, so the user's other plugins never load; the 4/4 trigger pass proves the descriptions fire in isolation, not that they win against superpowers:brainstorming, superpowers:systematic-debugging or receipts:gates in the user's real harness. Only real-session use can measure that. Bears on c8.
- R7 superpowers@claude-plugins-official is disabled at user scope for testing, and ~/.claude resolves into .windful-ocean/.claude, so brainstorming, systematic-debugging and the rest stay off in every project until someone runs claude plugin enable superpowers@claude-plugins-official --scope user.

## Settled, do not reopen

- S1 Out of scope: Implementing any change, including committing a bug's regression test; implementation belongs to mitosis or the user's own method (user, 2026-09-22)
- S2 Out of scope: Committing specs or development docs; they are gitignored and only usage docs are tracked (user, 2026-09-22)
- S3 Out of scope: Detecting, naming, invoking or suggesting mitosis at runtime; chaining interphase into mitosis belongs to the user's personal harness (user, 2026-09-22)

## Where the details live

- interphase design spec (gitignored): docs/specs/interphase.md
- interphase decisions log (gitignored): docs/specs/interphase.decisions.md
- interphase items file, 14 Steps (gitignored): docs/specs/interphase.items.json
- worker charter (gitignored): docs/specs/interphase.charter.md
- mitosis run directory: /Users/satanshumishra/.mitosis/runs/interphase/items-b69284b63402
- integration pull request into main: https://github.com/SatanshuMishra/interphase/pull/15
- part pull requests into feat/interphase: https://github.com/SatanshuMishra/interphase/pulls
- Old ledger record: thread 01M35AQ225TJBKP566K5G42ZG8 in refs/logbook/archive/ledger
