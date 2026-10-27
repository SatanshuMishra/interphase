# interphase-metrics: Interphase metrics on the shared plugin-metrics store, carried to the first build
Status: parked
Updated: 2026-10-27T08:14:04.145Z
Next ids: c5 D4 R4 S1

## Goal

Interphase records metrics personalised to its purpose (turn a request into an approved, testable spec and buildable Steps) in the shared ~/.plugin-metrics format, standalone, with a catalogue and a small self-query skill; this session carries the full lane up to the point where only the first build is left.

## Done when

- [x] c1 The spec, decisions file, record and items for interphase-metrics are in docs/specs/ of this checkout, with the glossary and decision records interphase wrote left uncommitted evidence: docs/specs/interphase-metrics.{md,decisions.md,record.json,items.json} exist (record status handed-off, check_items passes); git status shows GLOSSARY.md and docs/ (ADRs 0001, 0002) untracked, nothing committed
- [x] c2 The FEATURE branch is pushed and the run home ~/.mitosis/interphase/interphase-metrics/ holds CHARTER.md, worker-rules.txt, dispatch.zsh and run.zsh evidence: git ls-remote shows refs/heads/feat/interphase-metrics at 4b8ad3c8 on origin; run home lists CHARTER.md, worker-rules.txt, dispatch.zsh, run.zsh, feature.json, items.json, graph.json
- [x] c3 run.zsh --plan-only passes with no fatal finding evidence: run.zsh --plan-only exit 0, plan 9ed65354d82c, 8 Steps in 5 Lanes across 2 MSPs, no fatal finding (plan-2.log)
- [x] c4 The thread is parked with a next step gated on the shared reference writers existing on origin/feat/unified-metrics or origin/main evidence: park_thread returned parked [interphase-metrics]; Next step opens with the ls-tree gate on origin/main and origin/feat/unified-metrics and names run.zsh, Needs D1, R1

## Where things stand

interview-rounds is green after round 1, its advisory C1 fixed at 529d53a on mitosis/interview-rounds (base feat/interphase-metrics 4b8ad3c); gate 5 pass, 2 inert, which are not findings. self-metrics is in review round 2, its code-reviewer and security-reviewer running, on mitosis/self-metrics at 46beae0 (base mitosis/interview-rounds; round 1 reviewed 09bcee9): round 1 blocker C2 (non-typed text counted as typed) is fixed with receipt a2d4714 and fix 700dca7, advisories C4, C5 and S2 are fixed in 501d906 (new scripts/metrics_files.py, outside the write-set), and the stale summary overwrite race (C1, S1) is answered by amendment 1, merged from mitosis/self-metrics-amend-1 (700624a): 5.10 now writes the summary under the event file's append lock only when that file is unchanged. The amendment's gate passed test_build_skips_when_events_changed and found test_overlapping_builds_leave_the_newer_summary inert, because on the old code the newer build always finishes last. The round-2 suite at 46beae0 passes 448 tests (review/round-2/self-metrics.suite.txt). Nothing is pushed. GLOSSARY.md and ADRs 0001 and 0002 sit uncommitted in the checkout until Ship copies them.

## Next step

When the self-metrics round-2 code-reviewer and security-reviewer report (obligations already refreshed to 53 with Threats T1 to T19 kept), collect their last JSON arrays into review/round-2/self-metrics.findings.json, then run pipeline candidates, the validator, pipeline record and pipeline verdict.

Needs: D2, D3.

## Decisions in force

- D2 Interphase hand-off boundary: run the first build now that the shared writers landed: Build now from origin/feat/unified-metrics at a39ab11: run ~/.mitosis/interphase/interphase-metrics/run.zsh, then Stage 3 review, validate, fix and ship as pipeline:run says.
- D3 Amendment 1 hand-off boundary: build Step summary-write-lock onto mitosis/self-metrics: Build amendment 1 now: run amend-1.zsh --plan-only, then the build with --no-push, merge its branch into mitosis/self-metrics, re-run obligations, then self-metrics review round 2.

## Open risks

- R2 When the pipeline drives interphase in the same Claude Code session, PLUGIN_METRICS_PARENT is not in that session's environment (run.zsh exports it only for mitosis), so interphase records parent null; out of this spec's scope, a pipeline-side change.
- R3 Criteria 5.4 and 5.20 are live-session checks the builder cannot run; they stay unproven until the owner runs one real interphase session.

## Settled, do not reopen

## Where the details live

- Pipeline spec: /Users/satanshumishra/Documents/DevLabs/pipeline/docs/specs/unified-metrics.md
- Shared writers, fixtures, schemas and format document: pipeline repo origin/feat/unified-metrics at a39ab11 (SatanshuMishra/pipeline#21)
- Pipeline decisions with intent I1 to I6: /Users/satanshumishra/Documents/DevLabs/pipeline/docs/specs/unified-metrics.decisions.md
- Shared notes: /Users/satanshumishra/Library/Application Support/Claude/side-session-notes/local_962684e1-8c70-41bb-98a4-8bcb33f71921
- Interphase package: docs/specs/interphase-metrics.{md,decisions.md,record.json,items.json} and GLOSSARY.md in this checkout
- Decision records: docs/adr/0001-interphase-records-its-runs-through-a-hook.md and 0002-a-run-counts-only-its-own-spend-between-its-first-and-last-event.md in this checkout
- Run home: ~/.mitosis/interphase/interphase-metrics/ (CHARTER.md, worker-rules.txt, dispatch.zsh, run.zsh, items.json, graph.json, plan-2.log plan report, build-1.log build output)
- Record and task generators: /private/tmp/claude-501/-Users-satanshumishra-Documents-DevLabs-interphase/3eafd85b-d0b0-4374-a9f8-454cba4f33f9/scratchpad/build_record.py and build_tasks.py
- Mitosis run directories: ~/.mitosis/runs/interphase/interphase-metrics and interphase-metrics-amend-1 (amendment 1)
- Run home also holds amend-1.zsh and amend-1.items.json (amendment 1 build), review/ (round records, obligations, proofs, assumptions) and rounds.md
