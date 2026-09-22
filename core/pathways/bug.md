# Bug playbook

Use this playbook when existing behaviour is wrong. It adds bug-specific work to the shared phases in `${CLAUDE_PLUGIN_ROOT}/core/phases.md`. Fill the template at `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-bug.md`.

## Ground

Reproduce the bug before you ask about it.

- Gather the report's facts: steps, expected, actual, environment, version, how often.
- Run the steps. Reproduce as many times as needed. Record every run's command and observed output.
- If it does not reproduce, ask for the missing facts from the question bank before going further. Never invent reproduction steps.
- Find the last known good and first known bad version when history matters. Use `git bisect` only inside a probe worktree.
- Write one to five ranked hypotheses about the cause. Make each one something a single run could disprove.
- Write the draft failing test that reproduces the symptom at `docs/specs/<slug>.repro.<ext>`, in the project's own test framework. Record its failing output in the spec's Evidence section.

## Probes

- A probe is a tiny, temporary code change that tests one hypothesis about the cause.
- Create a throwaway worktree with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/probe.py" create --repo .`. Add `--with-uncommitted` when the bug depends on the user's uncommitted edits. The script prints the worktree path on its last line.
- Change the suspected cause, never the symptom. "If the page is blank, redirect" hides a symptom and proves nothing.
- Rerun the reproduction inside the probe worktree and record the result.
- Remove it with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/probe.py" remove --repo . --path <worktree>`.
- Record the hypothesis, one line describing the change, and the result in the spec. Never record the change itself.
- When the project cannot run, skip probes. Keep the ranked hypotheses and mark them unconfirmed.

## Questions

- The exact steps, including setup.
- Expected result and actual result.
- Version, environment and component.
- How often: always, sometimes, never again.
- Does it happen in a clean environment?
- Last version known to work and first known to fail.
- Logs, stack traces, screenshots.
- What changed recently: deploys, configuration, dependency upgrades.
- Is the expected behaviour actually a new feature?
- Which nearby behaviour must stay exactly as it is?

## Extra step

Confirm the root cause, by probe when possible, before you write the fix boundary.

## Acceptance

- Write a test that fails before the fix and passes after.
- Add checks that the unchanged behaviour still works.
- Write the fix boundary as three EARS blocks:
  - Current: "WHEN <condition> THEN the system <wrong behaviour>".
  - Expected: "WHEN <condition> THE SYSTEM SHALL <right behaviour>".
  - Unchanged: "WHEN <other condition> THE SYSTEM SHALL CONTINUE TO <behaviour that already works>".

## Steps

- Put the full text of the draft test and the path where it belongs in the fix Step's `task`.
- Include that test path in the fix Step's `files`.
- Name that file and test in the fix Step's `acceptance`.
