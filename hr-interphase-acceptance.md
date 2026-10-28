# hr-interphase-acceptance: Run 3 of the harness-redesign program: interphase records K1 acceptance lines, probes surfaces and seeds a check-author Lane
Status: active
Updated: 2026-10-28T13:16:09.171Z
Next ids: c7 D2 R3 S1

## Goal

Run 3 of the harness-redesign program (~/.mitosis/harness-redesign/PROGRAM.md): interphase stores K1 acceptance lines in its record, probes each surface before the read-back, renders a check-author first Lane over the locked paths, reads K6 outcomes before planning, and each pathway names the acceptance-line kinds it requires; shipped as ready pull requests through the full lane under overrides O1 to O10.

## Done when

- [ ] c1 P1 The record holds K1 acceptance lines: check_record.py validates them, and --complete refuses a criterion at a builder-runnable seam with no acceptance line.
- [ ] c2 P2 Before the read-back, each acceptance line's surface is probed (command on PATH, Playwright present, vmlab capabilities, claude on PATH) and the result is stored in the record's probes; a failed probe becomes a read-back question in attended runs and an Assumption plus a stopped run in unattended ones.
- [ ] c3 P3 The read-back lists each acceptance line in plain words.
- [ ] c4 P4 The items file carries a first Lane with role: check-author whose Steps write each acceptance line's test, and every other Lane depends on it; its write-set is the locked paths, which the record lists as locked.
- [ ] c5 P5 Before planning, interphase reads this repository's K6 outcome entries and lists repeated failure kinds under the spec's risks.
- [x] c6 P6 Each pathway playbook names the acceptance-line kinds it requires: feature (error, empty and permission states), bug (reproduction on the old code and a sweep of the same class), project (build and CI), prototype (judged lines with a rubric). evidence: the four locked tests in tests/test_pathway_line_kinds.py pass at mitosis/pathway-line-kinds 0ef62fe and the round 1 conformance audit judged 5.6 MET

## Where things stand

interphase handed off; ADR 0003 and five glossary terms are uncommitted in the checkout and ship with the first MSP. FEATURE branch feat/hr-interphase-acceptance holds the ten locked files at ca3b339, receipt-lock 2b84d751de02378b536f8035a52540c51130f36f16fe6157fa1dcad9a2411a2d. MSP pathway-line-kinds (head 0ef62fe) is green in round 1 with no findings and nothing to rerun. MSP acceptance-lines (head 39bc600) is in review round 3: round 1's conformance audit judged 5.1 to 5.5 MET; round 1's blockers are fixed; round 2's confirmed blocker (malformed record crashes script) is fixed at 8a38af9 after O6 reverted the faulty advisory fix; the second and last attempt at advisories C1, S2, S3, S4 and C4 is at 35ac082 and 39bc600. The suite at 39bc600 runs 545 tests and fails only the four other-MSP pathway tests. Round 3 reviews the fix diff from df43964 (O6): neither reviewer marked a blocker; the candidates file holds carried P1, new MEDIUM C1 to C3 (prefix-option argument, quoted operator and trailing comment each probed as a command) and LOW advisories C4 to C6, S1 and S2. The validator is judging them.

## Next step

When both reviewers return, collect round 3 findings, then run candidates, the validator, record and verdict; an advisory that fails again is blocked and ships in a draft.

Needs: D1.

## Decisions in force

- D1 interphase hand-off: build the handed-off spec with an O2 check author first: Dispatch the check author first; the build starts only after its tests are committed, pushed, locked with receipts lock and listed under - Locked: in CHARTER.md.

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
