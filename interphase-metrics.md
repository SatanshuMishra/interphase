# interphase-metrics: Interphase metrics on the shared plugin-metrics store, carried to the first build
Status: active
Updated: 2026-10-26T23:49:15.652Z
Next ids: c5 D1 R1 S1

## Goal

Interphase records metrics personalised to its purpose (turn a request into an approved, testable spec and buildable Steps) in the shared ~/.plugin-metrics format, standalone, with a catalogue and a small self-query skill; this session carries the full lane up to the point where only the first build is left.

## Done when

- [ ] c1 The spec, decisions file, record and items for interphase-metrics are in docs/specs/ of this checkout, with the glossary and decision records interphase wrote left uncommitted
- [ ] c2 The FEATURE branch is pushed and the run home ~/.mitosis/interphase/interphase-metrics/ holds CHARTER.md, worker-rules.txt, dispatch.zsh and run.zsh
- [ ] c3 run.zsh --plan-only passes with no fatal finding
- [ ] c4 The thread is parked with a next step gated on the shared reference writers existing on origin/feat/unified-metrics or origin/main

## Where things stand

Stage 1 is in interphase's Phase 9: the spec, decisions, record and 8-Step items are written and pass every check; the one spec-reviewer pass is running. ADRs 0001 and 0002 are drafted. The run home holds CHARTER.md, worker-rules.txt, dispatch.zsh and a run.zsh whose --feature-branch is still the placeholder FEATURE_BRANCH. Lighthouse readiness is clear (claude cli fact saved); receipts.config.json is already committed, so no receipts setup.

## Next step

When the spec reviewer reports, fix each issue that would build the wrong thing, re-render and recheck, then run interphase's Phase 10 hand-off (ADRs, tree guard verify, status handed-off).

## Decisions in force

## Open risks

## Settled, do not reopen

## Where the details live

- Pipeline spec (format description until the writers land): /Users/satanshumishra/Documents/DevLabs/pipeline/docs/specs/unified-metrics.md
- Pipeline decisions with intent I1 to I6: /Users/satanshumishra/Documents/DevLabs/pipeline/docs/specs/unified-metrics.decisions.md
- Shared notes: /Users/satanshumishra/Library/Application Support/Claude/side-session-notes/local_962684e1-8c70-41bb-98a4-8bcb33f71921
- Interphase package: docs/specs/interphase-metrics.{md,decisions.md,record.json,items.json} and GLOSSARY.md in this checkout
- Record and task generators: /private/tmp/claude-501/-Users-satanshumishra-Documents-DevLabs-interphase/3eafd85b-d0b0-4374-a9f8-454cba4f33f9/scratchpad/build_record.py and build_tasks.py
