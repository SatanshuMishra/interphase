# hr-interphase-acceptance: Run 3 of the harness-redesign program: interphase records K1 acceptance lines, probes surfaces and seeds a check-author Lane
Status: active
Updated: 2026-10-28T09:11:50.440Z
Next ids: c7 D1 R1 S1

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

interphase Phase 9: the spec, record and items are written and pass check_spec, check_record --complete and check_items; the one spec review is running. The run home holds CHARTER.md (locked list still a placeholder; carries the O10 line verbatim), worker-rules.txt (carries the O3 line verbatim), dispatch.zsh and graph.json; run 1's home is cleaned, so its shape is rebuilt from pipeline:run and PROGRAM.md. The base suite passes, 458 tests. Six Steps in two MSPs: acceptance-lines (five chained Steps, P1 to P5) and pathway-line-kinds (P6).

## Next step

Fix the spec review's real issues once, rerender, hand off (Phase 10), then dispatch the O2 check author on the FEATURE branch.

## Decisions in force

## Open risks

## Settled, do not reopen

## Where the details live

- Program: ~/.mitosis/harness-redesign/PROGRAM.md (run 3 of the harness-redesign program; intent I1 to I6, contracts K1 to K7, overrides O1 to O10)
- Contracts: ~/.mitosis/harness-redesign/contracts/ (k1-acceptance, k2-locked, k3-check-result, k6-outcome, frozen JSON Schema 2020-12)
- Audit: ~/.mitosis/harness-redesign/audit/interphase.md
- Run home: ~/.mitosis/interphase/hr-interphase-acceptance/
- Program thread: harness-redesign in the pipeline repository
- Spec, decisions, record, items: docs/specs/hr-interphase-acceptance.* in the interphase checkout
