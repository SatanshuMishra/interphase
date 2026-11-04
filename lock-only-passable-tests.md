# lock-only-passable-tests: interphase locks only acceptance tests that can pass, each into its own MSP; mitosis loses its wall-clock limits
Status: active
Updated: 2026-11-04T00:14:14.375Z
Next ids: c4 D4 R3 S1

## Goal

Spec 3 of the unattended-runs program: interphase checks every locked test for feasibility inside the planned write-sets before locking, renders one check-author per MSP so each MSP locks only its own tests, and mitosis plants, locks and gates per MSP and has no wall-clock limit, with every process non-interactive and git dead-peer detection on.

## Done when

- [ ] c1 interphase pull request open, bound with ccd_pr, Auto-Fix on
- [ ] c2 mitosis pull request open, bound with ccd_pr, Auto-Fix on
- [ ] c3 final report lists each pull request, its unproven criteria and its assumptions

## Where things stand

Interphase is shipped as ready pull requests, both assigned to the owner: https://github.com/SatanshuMishra/interphase/pull/59 (lock-feasibility, into feat/lock-only-passable-tests, review comment posted, bound to this session) and https://github.com/SatanshuMishra/interphase/pull/60 (feasibility-instructions, stacked on mitosis/lock-feasibility, so it merges into that branch before #59 merges). The mitosis MSP per-msp-lock is gated at 3831e1a (37 of 37 acceptance tests pass) and its branch mitosis/per-msp-lock holds dfc8a92 with GLOSSARY.md and ADR 0016 on top, nothing pushed. Its state.json was hand-repaired after mitosis 0.11 replayed a held Lane from a cleaned clone. Review round 1 holds 12 findings, the blocking candidates being S1 (CRITICAL: a consumer's referee misses deletion of a producer's merged locked test), S2 (HIGH: the referee restore drops that test), C1 (HIGH: interphase 0.14's check-author carrying msp check-author is refused) and U1/U2 (the version_is_0_11_0 pins in test_docs and test_referee_docs); the validator is judging the 10 candidates. H11 and H12 carry this spec's new fields, H12 allowing msp check-author on the plain check-author.

## Next step

When the round 1 reviewers return, gather their findings with the suite and standards findings into candidates, validate them, record and verdict, then fix the confirmed ones and the version pins on mitosis/per-msp-lock.

Needs: D2.

## Decisions in force

- D1 Hand-off boundary: build the interphase spec lock-only-passable-tests with mitosis 0.11.0 from feat/lock-only-passable-tests, running plan, build, review and ship in this session.
- D2 Hand-off boundary: build the mitosis spec per-msp-locks-no-limits as one MSP from feat/per-msp-locks-no-limits: Build now with mitosis 0.11.0 from feat/per-msp-locks-no-limits, with run home ~/.mitosis/mitosis/per-msp-locks-no-limits, running plan, build, review and ship in this session.
- D3 Ship boundary: push interphase lock-feasibility and feasibility-instructions as ready pull requests: Ship both now, with --proven-head lock-feasibility=c8a20df and feasibility-instructions=7e994b5, then open each pull request through GitHub MCP create_pull_request, assign it, bind it with ccd_pr and turn Auto-Fix on.

## Open risks

- R2 The app refuses to turn on Auto-Fix for a PR opened through GitHub MCP create_pull_request, and a session binds one PR at a time: interphase #59 is bound with Auto-Fix off, and #60 is unbound, so the owner turns Auto-Fix on and binds #60 themselves. Bears on c1.

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
- Mitosis review records: ~/.mitosis/mitosis/per-msp-locks-no-limits/review/ (round folders, obligations, assumptions); base worktree for suites at its base-tree folder
- Mitosis 0.11 held-Lane replay bug and the state repair: mitosis-0.11-held-lane-replay.md in the shared notes folder
