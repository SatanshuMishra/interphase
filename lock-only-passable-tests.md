# lock-only-passable-tests: interphase locks only acceptance tests that can pass, each into its own MSP; mitosis loses its wall-clock limits
Status: parked
Updated: 2026-11-04T20:18:26.891Z
Next ids: c4 D5 R5 S1

## Goal

Spec 3 of the unattended-runs program: interphase checks every locked test for feasibility inside the planned write-sets before locking, renders one check-author per MSP so each MSP locks only its own tests, and mitosis plants, locks and gates per MSP and has no wall-clock limit, with every process non-interactive and git dead-peer detection on.

## Done when

- [~] c1 interphase pull request open, bound with ccd_pr, Auto-Fix on struck: interphase #64 merged into main as 3900590 with Auto-Fix never on, which the app refuses for a pull request opened through GitHub MCP
- [~] c2 mitosis pull request open, bound with ccd_pr, Auto-Fix on struck: mitosis #35 merged into main as 5023475 with Auto-Fix never on, which the app refuses for a pull request opened through GitHub MCP
- [x] c3 final report lists each pull request, its unproven criteria and its assumptions evidence: the reports to the coordinator session name interphase #64 and mitosis #35, every acceptance line proven by a check result, and #35's four assumptions in its review comment

## Where things stand

Both FEATURE pull requests are merged and Clean-up is done for both runs: pipeline clean kept nothing, and each run's archive sits under ~/.mitosis/interphase/archive/lock-only-passable-tests and ~/.mitosis/mitosis/archive/per-msp-locks-no-limits. Plugin installs are left to the coordinator session while spec 4's builds run.

## Next step

None: Clean-up is the last stage, so the thread closes.

## Decisions in force

## Open risks

- R4 This session's interphase worktree cannot fast-forward to main because its GLOSSARY.md lacks spec 4's terms and it holds an untracked copy of spec 3's ADR under the old number 0004; it is left as it is.

## Settled, do not reopen

## Where the details live

- Program: ~/.mitosis/harness-redesign/PROGRAM.md section Superseded by the unattended-runs program
- Root-cause memory: ~/.claude/projects/-Users-satanshumishra-Documents-DevLabs-pipeline/memory/run-halts-root-causes.md
- Interphase run archive: ~/.mitosis/interphase/archive/lock-only-passable-tests (charter, review rounds, Integration and main-merge outputs, spec files, the stale feature record)
- Mitosis run archive: ~/.mitosis/mitosis/archive/per-msp-locks-no-limits (charter, review rounds, Integration outputs, code-reviewer rerun, spec files)
- Mitosis 0.11 held-Lane replay bug and the state repair: mitosis-0.11-held-lane-replay.md in the shared notes folder
