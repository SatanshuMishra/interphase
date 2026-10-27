# interphase-metrics: Interphase metrics on the shared plugin-metrics store, carried to the first build
Status: parked
Updated: 2026-10-27T08:07:20.252Z
Next ids: c5 D4 R4 S1

## Goal

Interphase records metrics personalised to its purpose (turn a request into an approved, testable spec and buildable Steps) in the shared ~/.plugin-metrics format, standalone, with a catalogue and a small self-query skill; this session carries the full lane up to the point where only the first build is left.

## Done when

- [x] c1 The spec, decisions file, record and items for interphase-metrics are in docs/specs/ of this checkout, with the glossary and decision records interphase wrote left uncommitted evidence: docs/specs/interphase-metrics.{md,decisions.md,record.json,items.json} exist (record status handed-off, check_items passes); git status shows GLOSSARY.md and docs/ (ADRs 0001, 0002) untracked, nothing committed
- [x] c2 The FEATURE branch is pushed and the run home ~/.mitosis/interphase/interphase-metrics/ holds CHARTER.md, worker-rules.txt, dispatch.zsh and run.zsh evidence: git ls-remote shows refs/heads/feat/interphase-metrics at 4b8ad3c8 on origin; run home lists CHARTER.md, worker-rules.txt, dispatch.zsh, run.zsh, feature.json, items.json, graph.json
- [x] c3 run.zsh --plan-only passes with no fatal finding evidence: run.zsh --plan-only exit 0, plan 9ed65354d82c, 8 Steps in 5 Lanes across 2 MSPs, no fatal finding (plan-2.log)
- [x] c4 The thread is parked with a next step gated on the shared reference writers existing on origin/feat/unified-metrics or origin/main evidence: park_thread returned parked [interphase-metrics]; Next step opens with the ls-tree gate on origin/main and origin/feat/unified-metrics and names run.zsh, Needs D1, R1

## Where things stand

interview-rounds is green after round 1; its one advisory, C1 (core/items.md called rounds required), is fixed at 529d53a on mitosis/interview-rounds, which still needs merging into mitosis/self-metrics. Self-metrics round 1 verdict is diagnose: blockers C1 and S1 (kind stale summary overwrite race) and C2 (kind non-typed text counted as typed), advisories C4, C5 and S2; C3, S3 and S4 rejected. Self-metrics round 1 verdict is loop. On mitosis/self-metrics: C2 fixed (receipt a2d4714 red, fix 700dca7, selecting check empty), advisories C4, C5, S2 fixed in 501d906 (new scripts/metrics_files.py, outside the write-set), interview-rounds merged in (aa4160f); full suite 446 OK. The stale summary overwrite race (C1, S1) is requirement-wrong: 5.10's write-unless-stored-ts-is-later rule cannot leave the newer summary; the right rule writes under an exclusive flock on the run's event file only when it still holds the lines the build read. Amendment 1 is written (record in-progress, guard snapshot taken in the checkout): 5.10 now writes under the append lock only when the event file is unchanged, with rows test_build_skips_when_events_changed and test_overlapping_builds_leave_the_newer_summary for Step summary-write-lock (MSP self-metrics-amend-1, docs/specs/interphase-metrics.amend-1.items.json); checks pass and the one spec-reviewer pass is running. 5.4 and 5.20 are not applicable as live-session checks. Both MSPs are committed and held unpushed: interview-rounds at f20d9a8 on mitosis/interview-rounds (base feat/interphase-metrics 4b8ad3c), self-metrics at 09bcee9 on mitosis/self-metrics (base mitosis/interview-rounds). Gate: self-metrics 70 pass; interview-rounds 5 pass, 2 inert (test_record_without_rounds_is_valid, test_rounds_not_a_list_refused), which are not findings. Round-1 suites pass (374 and 443 tests); the 77 gated tests are recorded as proofs. GLOSSARY.md and ADRs 0001 and 0002 sit uncommitted in the checkout until Ship copies them.

## Next step

Run ~/.mitosis/interphase/interphase-metrics/amend-1.zsh --plan-only, then the build in the background. Merge its branch into mitosis/self-metrics, re-run pipeline obligations for self-metrics, then self-metrics review round 2.

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
- Mitosis run directory: ~/.mitosis/runs/interphase/interphase-metrics
