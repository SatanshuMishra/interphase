# interphase-metrics: Interphase metrics on the shared plugin-metrics store, carried to the first build
Status: parked
Updated: 2026-10-27T00:04:34.191Z
Next ids: c5 D2 R4 S1

## Goal

Interphase records metrics personalised to its purpose (turn a request into an approved, testable spec and buildable Steps) in the shared ~/.plugin-metrics format, standalone, with a catalogue and a small self-query skill; this session carries the full lane up to the point where only the first build is left.

## Done when

- [x] c1 The spec, decisions file, record and items for interphase-metrics are in docs/specs/ of this checkout, with the glossary and decision records interphase wrote left uncommitted evidence: docs/specs/interphase-metrics.{md,decisions.md,record.json,items.json} exist (record status handed-off, check_items passes); git status shows GLOSSARY.md and docs/ (ADRs 0001, 0002) untracked, nothing committed
- [x] c2 The FEATURE branch is pushed and the run home ~/.mitosis/interphase/interphase-metrics/ holds CHARTER.md, worker-rules.txt, dispatch.zsh and run.zsh evidence: git ls-remote shows refs/heads/feat/interphase-metrics at 4b8ad3c8 on origin; run home lists CHARTER.md, worker-rules.txt, dispatch.zsh, run.zsh, feature.json, items.json, graph.json
- [x] c3 run.zsh --plan-only passes with no fatal finding evidence: run.zsh --plan-only exit 0, plan 9ed65354d82c, 8 Steps in 5 Lanes across 2 MSPs, no fatal finding (plan-2.log)
- [x] c4 The thread is parked with a next step gated on the shared reference writers existing on origin/feat/unified-metrics or origin/main evidence: park_thread returned parked [interphase-metrics]; Next step opens with the ls-tree gate on origin/main and origin/feat/unified-metrics and names run.zsh, Needs D1, R1

## Where things stand

Stage 1 is handed off: the spec, decisions, record (status handed-off) and 8-Step items pass every check after the one spec-reviewer round, and GLOSSARY.md plus ADRs 0001 and 0002 sit uncommitted in the checkout. Stage 2 set-up is complete: feat/interphase-metrics is pushed from 4b8ad3c8, the run home holds CHARTER.md, worker-rules.txt, dispatch.zsh, run.zsh, feature.json, items.json and graph.json, and run.zsh --plan-only passes (plan 9ed65354d82c, exit 0, 5 Lanes in 2 MSPs, no fatal finding) after the PR subject was shortened to "record interphase runs as metrics" for the 72-unit title cap. No build has run. The shared writers are on neither origin/feat/unified-metrics nor origin/main as of 2026-10-26.

## Next step

Gate: in /Users/satanshumishra/Documents/DevLabs/pipeline run `git fetch -q origin && git ls-tree --name-only <ref> -- pipeline_tool/metrics_writer.py metrics/metrics-writer.ts docs/metrics-format.md` for origin/main and origin/feat/unified-metrics. Once one prints a path (prefer origin/main), replace the "Pipeline ref:" line in ~/.mitosis/interphase/interphase-metrics/CHARTER.md with that ref, then run ~/.mitosis/interphase/interphase-metrics/run.zsh from the interphase repo root (first build), then the rest of pipeline:run (review, validate, fix pass, ship) to the last pull request.

Needs: D1, R1.

## Decisions in force

- D1 Interphase hand-off boundary: build waits on the shared reference writers: Park at the hand-off. Once the dependency command in the pipeline checkout prints a path on either ref, the build session sets the CHARTER's Pipeline ref line to that ref and runs ~/.mitosis/interphase/interphase-metrics/run.zsh, then the rest of pipeline:run to the last pull request.

## Open risks

- R1 Shared writers absent: as of 2026-10-26 neither origin/feat/unified-metrics nor origin/main in the pipeline repo holds pipeline_tool/metrics_writer.py, metrics/metrics-writer.ts or docs/metrics-format.md; the writer-copy Step cannot build until one does, and its assumed API must be rechecked against the landed writer.
- R2 When the pipeline drives interphase in the same Claude Code session, PLUGIN_METRICS_PARENT is not in that session's environment (run.zsh exports it only for mitosis), so interphase records parent null; out of this spec's scope, a pipeline-side change.
- R3 Criteria 5.4 and 5.20 are live-session checks the builder cannot run; they stay unproven until the owner runs one real interphase session.

## Settled, do not reopen

## Where the details live

- Pipeline spec (format description until the writers land): /Users/satanshumishra/Documents/DevLabs/pipeline/docs/specs/unified-metrics.md
- Pipeline decisions with intent I1 to I6: /Users/satanshumishra/Documents/DevLabs/pipeline/docs/specs/unified-metrics.decisions.md
- Shared notes: /Users/satanshumishra/Library/Application Support/Claude/side-session-notes/local_962684e1-8c70-41bb-98a4-8bcb33f71921
- Interphase package: docs/specs/interphase-metrics.{md,decisions.md,record.json,items.json} and GLOSSARY.md in this checkout
- Decision records: docs/adr/0001-interphase-records-its-runs-through-a-hook.md and 0002-a-run-counts-only-its-own-spend-between-its-first-and-last-event.md in this checkout
- Run home: ~/.mitosis/interphase/interphase-metrics/ (CHARTER.md, worker-rules.txt, dispatch.zsh, run.zsh)
- Record and task generators: /private/tmp/claude-501/-Users-satanshumishra-Documents-DevLabs-interphase/3eafd85b-d0b0-4374-a9f8-454cba4f33f9/scratchpad/build_record.py and build_tasks.py
- Plan-only report: ~/.mitosis/interphase/interphase-metrics/plan-2.log; mitosis run directory ~/.mitosis/runs/interphase/interphase-metrics
