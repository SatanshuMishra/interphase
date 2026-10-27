# interphase-metrics: Interphase metrics on the shared plugin-metrics store, carried to the first build
Status: parked
Updated: 2026-10-27T11:30:33.187Z
Next ids: c5 D6 R4 S1

## Goal

Interphase records metrics personalised to its purpose (turn a request into an approved, testable spec and buildable Steps) in the shared ~/.plugin-metrics format, standalone, with a catalogue and a small self-query skill; this session carries the full lane up to the point where only the first build is left.

## Done when

- [x] c1 The spec, decisions file, record and items for interphase-metrics are in docs/specs/ of this checkout, with the glossary and decision records interphase wrote left uncommitted evidence: docs/specs/interphase-metrics.{md,decisions.md,record.json,items.json} exist (record status handed-off, check_items passes); git status shows GLOSSARY.md and docs/ (ADRs 0001, 0002) untracked, nothing committed
- [x] c2 The FEATURE branch is pushed and the run home ~/.mitosis/interphase/interphase-metrics/ holds CHARTER.md, worker-rules.txt, dispatch.zsh and run.zsh evidence: git ls-remote shows refs/heads/feat/interphase-metrics at 4b8ad3c8 on origin; run home lists CHARTER.md, worker-rules.txt, dispatch.zsh, run.zsh, feature.json, items.json, graph.json
- [x] c3 run.zsh --plan-only passes with no fatal finding evidence: run.zsh --plan-only exit 0, plan 9ed65354d82c, 8 Steps in 5 Lanes across 2 MSPs, no fatal finding (plan-2.log)
- [x] c4 The thread is parked with a next step gated on the shared reference writers existing on origin/feat/unified-metrics or origin/main evidence: park_thread returned parked [interphase-metrics]; Next step opens with the ls-tree gate on origin/main and origin/feat/unified-metrics and names run.zsh, Needs D1, R1

## Where things stand

Integration is in its first fix round. feat/interphase-metrics (970ae86, including lighthouse's profile commit) holds both MSPs, and the integration worktree is ~/.mitosis/runs/interphase/interphase-metrics/integration. Lighthouse run 1 (lighthouse/run-1) returned verdict failures with no pull request, spending 52.9 dollars over 105 minutes. It found U1: review.done counts every dash line of the spec reviewer's reply, including its Files reviewed list, as an issue (scripts/metrics_hook.py:351). It found U2: shlex fails on a heredoc holding an apostrophe, so the hook drops that command and run.handoff is lost (scripts/metrics_hook.py:51); lighthouse marked it flaky, but it reproduces deterministically. The scout neighbour path was unproven, because no request dispatched scout. Both findings are recorded as integration round 1 with kind failing test; the diagnosis classed them requirement-wrong. Amendment 2 (Step hook-parsing, MSP integration-amend-2: the first-run issue count for 5.8 and a bash-aware command reader for 5.5 to 5.7) is built (gate 6 pass) and merged into feat/interphase-metrics, now pushed at 2e07f10; the suite passes (455 tests, review/round-1/integration.amend-2.suite.txt) and the selecting check finds no instance. Lighthouse run 2 with --previous run-1 is next.

## Next step

Run ~/.mitosis/interphase/interphase-metrics/amend-2.zsh --plan-only, then the build, merge its branch into feat/interphase-metrics in the integration worktree, run the suite and the selecting check, push, then lighthouse run 2 with --previous run-1 until the FEATURE pull request into main opens.

Needs: D5, R2, R3.

## Decisions in force

- D2 Interphase hand-off boundary: run the first build now that the shared writers landed: Build now from origin/feat/unified-metrics at a39ab11: run ~/.mitosis/interphase/interphase-metrics/run.zsh, then Stage 3 review, validate, fix and ship as pipeline:run says.
- D3 Amendment 1 hand-off boundary: build Step summary-write-lock onto mitosis/self-metrics: Build amendment 1 now: run amend-1.zsh --plan-only, then the build with --no-push, merge its branch into mitosis/self-metrics, re-run obligations, then self-metrics review round 2.
- D4 Ship boundary: push interview-rounds and self-metrics and open their stacked pull requests: Ship now: SHIP=1 run.zsh --resume with --proven-head self-metrics=bfb1221; open interview-rounds into feat/interphase-metrics and self-metrics stacked on it, ready for review, assigned to the owner, each with its saved comment.
- D5 Amendment 2 hand-off boundary: build Step hook-parsing onto feat/interphase-metrics: Build amendment 2 now: amend-2.zsh --plan-only, then the build with --no-push, merge its branch into feat/interphase-metrics, run the suite and the selecting check, push, then lighthouse run 2 with --previous run-1.

## Open risks

- R2 When the pipeline drives interphase in the same Claude Code session, PLUGIN_METRICS_PARENT is not in that session's environment (run.zsh exports it only for mitosis), so interphase records parent null; out of this spec's scope, a pipeline-side change.
- R3 Criteria 5.4 and 5.20 are live-session checks the builder cannot run; they stay unproven until the owner runs one real interphase session.

## Settled, do not reopen

## Where the details live

- Pipeline spec: /Users/satanshumishra/Documents/DevLabs/pipeline/docs/specs/unified-metrics.md
- Shared writers, fixtures, schemas and format document: pipeline repo origin/main (42b6145, SatanshuMishra/pipeline#21 merged; shared writer files byte-identical to a39ab11)
- Pipeline decisions with intent I1 to I6: /Users/satanshumishra/Documents/DevLabs/pipeline/docs/specs/unified-metrics.decisions.md
- Shared notes: /Users/satanshumishra/Library/Application Support/Claude/side-session-notes/local_962684e1-8c70-41bb-98a4-8bcb33f71921
- Interphase package: docs/specs/interphase-metrics.{md,decisions.md,record.json,items.json} and GLOSSARY.md in this checkout
- Decision records: docs/adr/0001-interphase-records-its-runs-through-a-hook.md and 0002-a-run-counts-only-its-own-spend-between-its-first-and-last-event.md in this checkout
- Run home: ~/.mitosis/interphase/interphase-metrics/ (CHARTER.md, worker-rules.txt, dispatch.zsh, run.zsh, items.json, graph.json, plan-2.log plan report, build-1.log build output)
- Record and task generators: /private/tmp/claude-501/-Users-satanshumishra-Documents-DevLabs-interphase/3eafd85b-d0b0-4374-a9f8-454cba4f33f9/scratchpad/build_record.py and build_tasks.py
- Mitosis run directories: ~/.mitosis/runs/interphase/interphase-metrics and interphase-metrics-amend-1 (amendment 1)
- Amendment 2 generators: /private/tmp/claude-501/-Users-satanshumishra-Documents-DevLabs-interphase/3eafd85b-d0b0-4374-a9f8-454cba4f33f9/scratchpad/amend2/amend2.py and amend2b.py (review fixes); amendment 2 items: docs/specs/interphase-metrics.amend-2.items.json
- Run home also holds amend-1.zsh and amend-1.items.json (amendment 1 build), amend-2.zsh (amendment 2 build onto feat/interphase-metrics), lighthouse/run-1 (Integration's first lighthouse results), review/ (round records, obligations, proofs, assumptions) and rounds.md; CHARTER.md's Pipeline ref names pipeline origin/main as the source of the shared files
