# hr-interphase-acceptance: Run 3 of the harness-redesign program: interphase records K1 acceptance lines, probes surfaces and seeds a check-author Lane
Status: active
Updated: 2026-10-28T11:24:48.966Z
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

interphase handed off; ADR 0003 and five glossary terms are uncommitted in the checkout and ship with the first MSP. FEATURE branch feat/hr-interphase-acceptance holds the ten locked files at ca3b339, receipt-lock 2b84d751de02378b536f8035a52540c51130f36f16fe6157fa1dcad9a2411a2d. MSP pathway-line-kinds (head 0ef62fe) is green in round 1 with no findings and nothing to rerun. MSP acceptance-lines (head df43964) is in review round 2: its round 1 conformance audit judged 5.1 to 5.5 MET, and every round 1 blocker and advisory has a fix commit with a passing receipt test (S1 and C5 at fdf7f1e, C2 at 45e967f, C3 and C6 at 4a7efbf, C1, S3, S4 and C4 at df43964); the suite at df43964 runs 538 tests and fails only the four other-MSP pathway tests. The round 2 code and security reviewers are judging the fix diff from 8f15979 (O6).

## Next step

Collect round 2 findings into review/round-2/acceptance-lines.findings.json, then run pipeline candidates, the validator when needed, pipeline record and pipeline verdict.

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
