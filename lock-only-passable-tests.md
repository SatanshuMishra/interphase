# lock-only-passable-tests: interphase locks only acceptance tests that can pass, each into its own MSP; mitosis loses its wall-clock limits
Status: parked
Updated: 2026-11-04T20:01:15.304Z
Next ids: c4 D5 R5 S1

## Goal

Spec 3 of the unattended-runs program: interphase checks every locked test for feasibility inside the planned write-sets before locking, renders one check-author per MSP so each MSP locks only its own tests, and mitosis plants, locks and gates per MSP and has no wall-clock limit, with every process non-interactive and git dead-peer detection on.

## Done when

- [ ] c1 interphase pull request open, bound with ccd_pr, Auto-Fix on
- [ ] c2 mitosis pull request open, bound with ccd_pr, Auto-Fix on
- [ ] c3 final report lists each pull request, its unproven criteria and its assumptions

## Where things stand

Mitosis #35 is merged into mitosis main. Interphase's FEATURE pull request https://github.com/SatanshuMishra/interphase/pull/64 conflicted with main 67cefd6 (spec 4, interphase#63); main is merged into feat/lock-only-passable-tests in the integration worktree, released as 0.16.0 because main took 0.15.0, spec 3's ADR renumbered 0005, and the merge review's three advisories fixed. Head 2e666f8 is pushed: 8 of 8 acceptance lines and 626 tests pass, and #64 reports MERGEABLE and CLEAN with no CI checks configured in the repository. H11 and H12 carry this spec's new fields.

## Next step

The owner merges interphase #64, then starts Clean-up by saying the FEATURE pull request merged.

Needs: R3, R4.

## Decisions in force

- D1 Hand-off boundary: build the interphase spec lock-only-passable-tests with mitosis 0.11.0 from feat/lock-only-passable-tests, running plan, build, review and ship in this session.
- D2 Hand-off boundary: build the mitosis spec per-msp-locks-no-limits as one MSP from feat/per-msp-locks-no-limits: Build now with mitosis 0.11.0 from feat/per-msp-locks-no-limits, with run home ~/.mitosis/mitosis/per-msp-locks-no-limits, running plan, build, review and ship in this session.
- D3 Ship boundary: push interphase lock-feasibility and feasibility-instructions as ready pull requests: Ship both now, with --proven-head lock-feasibility=c8a20df and feasibility-instructions=7e994b5, then open each pull request through GitHub MCP create_pull_request, assign it, bind it with ccd_pr and turn Auto-Fix on.
- D4 Ship boundary: push mitosis per-msp-lock as a ready pull request: Ship now: SHIP=1 run.zsh --resume --proven-head per-msp-lock=7f7f597, then open the pull request through GitHub MCP create_pull_request with the title and body mitosis renders, assign it to the owner, post the review comment, bind it with ccd_pr and try Auto-Fix.

## Open risks

- R3 The app refuses Auto-Fix for a PR opened through GitHub MCP create_pull_request, and a session binds one PR, so the owner binds the FEATURE pull requests and turns Auto-Fix on. Bears on c1 and c2.
- R4 This interphase checkout cannot fast-forward to main because its local GLOSSARY.md differs from main's; it is left as it is, and Integration reads only the FEATURE branch.

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
- Mitosis run folder alias: ~/.mitosis/runs/mitosis-per-msp-locks-no-limits/per-msp-locks-no-limits links to ~/.mitosis/runs/mitosis/per-msp-locks-no-limits, because pipeline names runs after the checkout folder
- Mitosis Integration outputs: ~/.mitosis/mitosis/per-msp-locks-no-limits/integration.checks.out and integration.suite.json (suite passes on 3.9 and 3.14 at eb1b25e)
- Mitosis code-reviewer rerun: ~/.mitosis/mitosis/per-msp-locks-no-limits/review/round-3/per-msp-lock.code-reviewer.rerun.agent.json
- Interphase Integration outputs: ~/.mitosis/interphase/lock-only-passable-tests/integration.checks.out and integration.suite.json (suite passes at 121ec43)
- Interphase main-merge outputs: ~/.mitosis/interphase/lock-only-passable-tests/integration-main-merge.checks.out and integration-main-merge.suite.json; the merge, release and review-fix commits are 701253b, b6a3dd4 and 2e666f8 on feat/lock-only-passable-tests
- Interphase run folder aliases: ~/.mitosis/charming-satoshi-3757e3/lock-only-passable-tests and ~/.mitosis/runs/charming-satoshi-3757e3/lock-only-passable-tests link to the interphase run home and run folder, because pipeline names runs after this worktree's folder; the stale record that stood there is kept beside it as lock-only-passable-tests.stale-feature-record
