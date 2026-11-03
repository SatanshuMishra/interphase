# lock-only-passable-tests: interphase locks only acceptance tests that can pass, each into its own MSP; mitosis loses its wall-clock limits
Status: active
Updated: 2026-11-03T23:14:16.248Z
Next ids: c4 D4 R2 S1

## Goal

Spec 3 of the unattended-runs program: interphase checks every locked test for feasibility inside the planned write-sets before locking, renders one check-author per MSP so each MSP locks only its own tests, and mitosis plants, locks and gates per MSP and has no wall-clock limit, with every process non-interactive and git dead-peer detection on.

## Done when

- [ ] c1 interphase pull request open, bound with ccd_pr, Auto-Fix on
- [ ] c2 mitosis pull request open, bound with ccd_pr, Auto-Fix on
- [ ] c3 final report lists each pull request, its unproven criteria and its assumptions

## Where things stand

Interphase build: MSP lock-feasibility is green at round 2 with its advisories C8 and C9 fixed at 27a56bc, plus a fix with receipt for the list-valued Step name crash the validator rejected only as predating round 2. MSP feasibility-instructions is committed on that head at 4d4c795 with its gate 6 of 6, its six proofs recorded; its round 1 diff, obligations, standard checks (none) and its suite passes, the conformance-auditor finds 5.8 met, the code-reviewer reports F1 (MEDIUM, README still describes one check-author for the run) and F2 and F3 (LOW, instruction wording), and its validator is running. The mitosis build per-msp-locks-no-limits is on its one resume: Lane 0 per-msp-lock is ok at c750737; Lane 1 no-limits-nothing-waits failed with four test-only fixes left, because a hook refuses edits to a test file once a session has seen it fail; its charter now holds those four fixes and the first attempt's diff, and Lane 2 release-0-12 waits on it. The mitosis checkout holds the uncommitted GLOSSARY.md change and ADR 0016 for pipeline commit-records. H11 and H12 carry this spec's new fields, H12 allowing msp check-author on the plain check-author.

## Next step

Run SHIP=1 ~/.mitosis/interphase/lock-only-passable-tests/run.zsh --resume --proven-head lock-feasibility=c8a20df --proven-head feasibility-instructions=7e994b5, then open, assign, comment, bind and Auto-Fix each pull request in stack order.

Needs: D1, D3.

## Decisions in force

- D1 Hand-off boundary: build the interphase spec lock-only-passable-tests with mitosis 0.11.0 from feat/lock-only-passable-tests, running plan, build, review and ship in this session.
- D2 Hand-off boundary: build the mitosis spec per-msp-locks-no-limits as one MSP from feat/per-msp-locks-no-limits: Build now with mitosis 0.11.0 from feat/per-msp-locks-no-limits, with run home ~/.mitosis/mitosis/per-msp-locks-no-limits, running plan, build, review and ship in this session.
- D3 Ship boundary: push interphase lock-feasibility and feasibility-instructions as ready pull requests: Ship both now, with --proven-head lock-feasibility=c8a20df and feasibility-instructions=7e994b5, then open each pull request through GitHub MCP create_pull_request, assign it, bind it with ccd_pr and turn Auto-Fix on.

## Open risks


## Settled, do not reopen

## Where the details live

- Root-cause memory: ~/.claude/projects/-Users-satanshumishra-Documents-DevLabs-pipeline/memory/run-halts-root-causes.md
- Program: ~/.mitosis/harness-redesign/PROGRAM.md section Superseded by the unattended-runs program
- Decisions binding limits: ~/Documents/DevLabs/pipeline/docs/specs/runs-complete-unattended.decisions.md
- Evidence: ~/.mitosis/chinook-project/desktop-reliability-ux/
- Interphase checkout: this session's worktree claude/charming-satoshi-3757e3; spec files docs/specs/lock-only-passable-tests.*
- Mitosis checkout: ~/.mitosis/checkouts/mitosis-per-msp-locks-no-limits, branch spec/per-msp-locks-no-limits
- Refusal evidence pinned per class: side-session-notes/local_66da20f4-53bb-4093-baf3-210dfad1fed7/spec3-chinook-refusals.md
- Mitosis run home: ~/.mitosis/mitosis/per-msp-locks-no-limits, also reached as ~/.mitosis/mitosis-per-msp-locks-no-limits/per-msp-locks-no-limits (charter, worker rules, dispatch, run.zsh, feature.json, graph copy); its acceptance script ~/.mitosis/mitosis/accept.zsh has no alarm
- Shared contracts holding this spec's fields: ~/.mitosis/harness-redesign/contracts/h11-interphase-record.schema.json and h12-interphase-items.schema.json; the note for spec 4 is spec3-overlap-with-spec4.md in the shared notes folder
- Interphase review records: ~/.mitosis/interphase/lock-only-passable-tests/review/ (round folders, obligations, assumptions); base worktree for suites at its base-tree folder
- Failed Lanes' first attempts: ~/.mitosis/mitosis/per-msp-locks-no-limits/lane-1-attempt-1.diff and ~/.mitosis/interphase/lock-only-passable-tests/lane-3-attempt-1.diff
