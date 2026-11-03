# lock-only-passable-tests: interphase locks only acceptance tests that can pass, each into its own MSP; mitosis loses its wall-clock limits
Status: active
Updated: 2026-11-03T23:03:29.863Z
Next ids: c4 D3 R2 S1

## Goal

Spec 3 of the unattended-runs program: interphase checks every locked test for feasibility inside the planned write-sets before locking, renders one check-author per MSP so each MSP locks only its own tests, and mitosis plants, locks and gates per MSP and has no wall-clock limit, with every process non-interactive and git dead-peer detection on.

## Done when

- [ ] c1 interphase pull request open, bound with ccd_pr, Auto-Fix on
- [ ] c2 mitosis pull request open, bound with ccd_pr, Auto-Fix on
- [ ] c3 final report lists each pull request, its unproven criteria and its assumptions

## Where things stand

Interphase build: MSP lock-feasibility is green at round 2 with its advisories C8 and C9 fixed at 27a56bc, plus a fix with receipt for the list-valued Step name crash the validator rejected only as predating round 2. MSP feasibility-instructions is committed on that head at 4d4c795 with its gate 6 of 6, its six proofs recorded; its round 1 diff, obligations, standard checks (none) and code-reviewer and conformance-auditor briefs are written, and its suite is running. The mitosis build per-msp-locks-no-limits is on its one resume: Lane 0 per-msp-lock is ok at c750737; Lane 1 no-limits-nothing-waits failed with four test-only fixes left, because a hook refuses edits to a test file once a session has seen it fail; its charter now holds those four fixes and the first attempt's diff, and Lane 2 release-0-12 waits on it. The mitosis checkout holds the uncommitted GLOSSARY.md change and ADR 0016 for pipeline commit-records. H11 and H12 carry this spec's new fields, H12 allowing msp check-author on the plain check-author.

## Next step

When feasibility-instructions' suite finishes, dispatch its round 1 reviewers; when the mitosis resume ends, read its JSON result, commit-records, then review the mitosis MSP.

Needs: D1, D2, R1.

## Decisions in force

- D1 Hand-off boundary: build the interphase spec lock-only-passable-tests with mitosis 0.11.0 from feat/lock-only-passable-tests, running plan, build, review and ship in this session.
- D2 Hand-off boundary: build the mitosis spec per-msp-locks-no-limits as one MSP from feat/per-msp-locks-no-limits: Build now with mitosis 0.11.0 from feat/per-msp-locks-no-limits, with run home ~/.mitosis/mitosis/per-msp-locks-no-limits, running plan, build, review and ship in this session.

## Open risks

- R1 The standards text appended to worker rules says to give every wait a time limit, against both specs' no-caps intent; the interphase Workers received it, so review checks lock_feasibility.py for any limit, and the mitosis run's worker-rules.txt overrides that line. Bears on c1.

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
