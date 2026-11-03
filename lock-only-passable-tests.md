# lock-only-passable-tests: interphase locks only acceptance tests that can pass, each into its own MSP; mitosis loses its wall-clock limits
Status: active
Updated: 2026-11-03T20:14:16.827Z
Next ids: c4 D1 R1 S1

## Goal

Spec 3 of the unattended-runs program: interphase checks every locked test for feasibility inside the planned write-sets before locking, renders one check-author per MSP so each MSP locks only its own tests, and mitosis plants, locks and gates per MSP and has no wall-clock limit, with every process non-interactive and git dead-peer detection on.

## Done when

- [ ] c1 interphase pull request open, bound with ccd_pr, Auto-Fix on
- [ ] c2 mitosis pull request open, bound with ccd_pr, Auto-Fix on
- [ ] c3 final report lists each pull request, its unproven criteria and its assumptions

## Where things stand

Not started.

## Next step

Read the Chinook refusal evidence note in the shared notes folder, then invoke interphase:feature with Work autonomously. for the interphase half in this worktree.

## Decisions in force

## Open risks

## Settled, do not reopen

## Where the details live

- Root-cause memory: ~/.claude/projects/-Users-satanshumishra-Documents-DevLabs-pipeline/memory/run-halts-root-causes.md
- Program: ~/.mitosis/harness-redesign/PROGRAM.md section Superseded by the unattended-runs program
- Decisions binding limits: ~/Documents/DevLabs/pipeline/docs/specs/runs-complete-unattended.decisions.md
- Evidence: ~/.mitosis/chinook-project/desktop-reliability-ux/
- Interphase checkout: this session's worktree claude/charming-satoshi-3757e3; mitosis checkout: ~/.mitosis/checkouts/mitosis-<slug>
