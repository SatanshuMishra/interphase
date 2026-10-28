# hr-interphase-acceptance: Run 3 of the harness-redesign program: interphase records K1 acceptance lines, probes surfaces and seeds a check-author Lane
Status: active
Updated: 2026-10-28T09:38:26.016Z
Next ids: c7 D2 R3 S1

## Goal

Run 3 of the harness-redesign program (~/.mitosis/harness-redesign/PROGRAM.md): interphase stores K1 acceptance lines in its record, probes each surface before the read-back, renders a check-author first Lane over the locked paths, reads K6 outcomes before planning, and each pathway names the acceptance-line kinds it requires; shipped as ready pull requests through the full lane under overrides O1 to O10.

## Done when

- [ ] c1 P1 The record holds K1 acceptance lines: check_record.py validates them, and --complete refuses a criterion at a builder-runnable seam with no acceptance line.
- [ ] c2 P2 Before the read-back, each acceptance line's surface is probed (command on PATH, Playwright present, vmlab capabilities, claude on PATH) and the result is stored in the record's probes; a failed probe becomes a read-back question in attended runs and an Assumption plus a stopped run in unattended ones.
- [ ] c3 P3 The read-back lists each acceptance line in plain words.
- [ ] c4 P4 The items file carries a first Lane with role: check-author whose Steps write each acceptance line's test, and every other Lane depends on it; its write-set is the locked paths, which the record lists as locked.
- [ ] c5 P5 Before planning, interphase reads this repository's K6 outcome entries and lists repeated failure kinds under the spec's risks.
- [ ] c6 P6 Each pathway playbook names the acceptance-line kinds it requires: feature (error, empty and permission states), bug (reproduction on the old code and a sweep of the same class), project (build and CI), prototype (judged lines with a rubric).

## Where things stand

interphase handed off (record status handed-off; ADR 0003 and five glossary terms are uncommitted in the checkout and ship with the first MSP). FEATURE branch feat/hr-interphase-acceptance is cut at 57ee015. The O2 check author committed ten locked files at ca3b339 on FEATURE (30 tests, each failing for the absent behaviour; the 458 old tests pass); receipt-lock 2b84d751de02378b536f8035a52540c51130f36f16fe6157fa1dcad9a2411a2d is in receipts-lock.txt and CHARTER.md lists the ten files under - Locked:. The base suite passes, 458 tests. Six Steps in two MSPs: acceptance-lines (five chained Steps, P1 to P5) and pathway-line-kinds (P6). run.zsh is written and its --plan-only exits 0 with six Lanes and no finding; items.json is copied to the run home.

## Next step

Run the first build: ~/.mitosis/interphase/hr-interphase-acceptance/run.zsh in the background (no SHIP), then read mitosis's JSON result and run the locked checks at each MSP head (O4).

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
