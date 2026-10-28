# hr-interphase-acceptance: Run 3 of the harness-redesign program: interphase records K1 acceptance lines, probes surfaces and seeds a check-author Lane
Status: parked
Updated: 2026-10-28T19:10:41.981Z
Next ids: c7 D3 R3 S1

## Goal

Run 3 of the harness-redesign program (~/.mitosis/harness-redesign/PROGRAM.md): interphase stores K1 acceptance lines in its record, probes each surface before the read-back, renders a check-author first Lane over the locked paths, reads K6 outcomes before planning, and each pathway names the acceptance-line kinds it requires; shipped as ready pull requests through the full lane under overrides O1 to O10.

## Done when

- [x] c1 P1 The record holds K1 acceptance lines: check_record.py validates them, and --complete refuses a criterion at a builder-runnable seam with no acceptance line. evidence: its locked tests pass alone at mitosis/acceptance-lines 294301f (review/acceptance-lines.proofs.jsonl), the suite there fails only the four other-MSP pathway tests, and the round 1 conformance audit judged 5.1 MET
- [x] c2 P2 Before the read-back, each acceptance line's surface is probed (command on PATH, Playwright present, vmlab capabilities, claude on PATH) and the result is stored in the record's probes; a failed probe becomes a read-back question in attended runs and an Assumption plus a stopped run in unattended ones. evidence: its locked tests pass alone at mitosis/acceptance-lines 294301f (review/acceptance-lines.proofs.jsonl), the suite there fails only the four other-MSP pathway tests, and the round 1 conformance audit judged 5.2 MET
- [x] c3 P3 The read-back lists each acceptance line in plain words. evidence: its locked tests pass alone at mitosis/acceptance-lines 294301f (review/acceptance-lines.proofs.jsonl), the suite there fails only the four other-MSP pathway tests, and the round 1 conformance audit judged 5.3 MET
- [x] c4 P4 The items file carries a first Lane with role: check-author whose Steps write each acceptance line's test, and every other Lane depends on it; its write-set is the locked paths, which the record lists as locked. evidence: its locked tests pass alone at mitosis/acceptance-lines 294301f (review/acceptance-lines.proofs.jsonl), the suite there fails only the four other-MSP pathway tests, and the round 1 conformance audit judged 5.4 MET
- [x] c5 P5 Before planning, interphase reads this repository's K6 outcome entries and lists repeated failure kinds under the spec's risks. evidence: its locked tests pass alone at mitosis/acceptance-lines 294301f (review/acceptance-lines.proofs.jsonl), the suite there fails only the four other-MSP pathway tests, and the round 1 conformance audit judged 5.5 MET
- [x] c6 P6 Each pathway playbook names the acceptance-line kinds it requires: feature (error, empty and permission states), bug (reproduction on the old code and a sweep of the same class), project (build and CI), prototype (judged lines with a rubric). evidence: the four locked tests in tests/test_pathway_line_kinds.py pass at mitosis/pathway-line-kinds 0ef62fe and the round 1 conformance audit judged 5.6 MET

## Where things stand

Integration: MSP pull requests 55 and 56 merged into feat/hr-interphase-acceptance (da50a0f, 71678de) and pipeline integration-ready reports ready. lighthouse:test run 1 is starting against core main with results in the run home's lighthouse/run-1.

## Next step

Read lighthouse run 1's last JSON line; on failures or blocked, record findings, verdict and diagnosis and send each fixable kind to a fresh fix agent with a receipt test; on green, bind the FEATURE pull request lighthouse opens with Auto-Fix on, park for Clean-up and update run 3's PROGRAM.md row.

Needs: D2.

## Decisions in force

- D1 interphase hand-off: build the handed-off spec with an O2 check author first: Dispatch the check author first; the build starts only after its tests are committed, pushed, locked with receipts lock and listed under - Locked: in CHARTER.md.
- D2 ship boundary: ship both MSPs as ready pull requests: Ship both MSPs as ready pull requests: SHIP=1 run.zsh --resume with --proven-head acceptance-lines=27b3c97c5777215d16adde0a4cfeab33ac8765d8 and --proven-head pathway-line-kinds=0ef62fe0eb3494f27ce5d0060a34bbd700ffd058.

## Open risks

- R1 The installed vmlab 0.4.0 has no capabilities verb, so a desktop or mobile probe fails until VMLab's release with it is installed.
- R2 receipts.config.json in this repository names agent.repo_name receipts-tree; the pipeline writes that value in every repository, so receipts' own session memory may mix repositories.

## Settled, do not reopen

## Where the details live

- Program: ~/.mitosis/harness-redesign/PROGRAM.md (run 3 of the harness-redesign program; intent I1 to I6, contracts K1 to K7, overrides O1 to O10)
- Contracts: ~/.mitosis/harness-redesign/contracts/ (k1-acceptance, k2-locked, k3-check-result, k6-outcome, frozen JSON Schema 2020-12)
- Audit: ~/.mitosis/harness-redesign/audit/interphase.md
- Run home: ~/.mitosis/interphase/hr-interphase-acceptance/
- Program thread: harness-redesign in the pipeline repository
- Spec, decisions, record, items: docs/specs/hr-interphase-acceptance.* in the interphase checkout
- Run home files: CHARTER.md, worker-rules.txt, dispatch.zsh, feature.json, graph.json, check-tree (temporary check-author worktree)
- Review record: run home review/ (obligations, assumptions, proofs per MSP; round-<n>/ findings, verdicts, diagnoses) and rounds.md (one line per round)
- MSP worktrees: ~/.mitosis/runs/interphase/hr-interphase-acceptance/trees/<msp>
- Pull requests: https://github.com/SatanshuMishra/interphase/pull/55 (acceptance-lines) and https://github.com/SatanshuMishra/interphase/pull/56 (pathway-line-kinds)
- Lighthouse results: run home lighthouse/run-<k>
