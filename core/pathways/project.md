# Project playbook

Use this playbook when the request is to create a new repository, or to replace an existing repository's stack, build, CI or release. Follow it alongside `${CLAUDE_PLUGIN_ROOT}/core/phases.md`. Write the spec from `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-project.md`.

## Ground

Research before you ask.

- Research the product's domain, who its users are and what is at stake for them.
- For a re-platform, read the existing code, build, CI, release and written rules before proposing any change.
- For candidate stacks, libraries and services, get current documentation through the `interphase:scout` agent.
- Follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md`.

## Questions

Use this bank as the checklist of branches the design tree must reach. Ask only what passes the hard bar of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`; skip any question the Ground phase or the intent round already answered.

- Is this a proof of concept or a product?
- What is the definition of done for the first usable version?
- Which platforms, minimum versions and hardware must it run on?
- Which stack, and which alternatives were considered?
- How are dependencies and versions pinned?
- Which build tooling builds it?
- How is each kind of behaviour tested? Follow `${CLAUDE_PLUGIN_ROOT}/core/variation.md` for behaviour that varies from run to run.
- What does CI run, and on which events?
- How is it released: packaging, signing, distribution and size?
- Where do configuration and secrets live, and how do they reach each environment?
- Which licence does it carry, and how is third-party attribution kept?
- What does it log, and which diagnostics help when it fails?
- What is the repository layout?

## Extra step

Propose two or three stacks with their trade-offs as one frontier question, the recommended one first. Record the choice in the decisions file, and the choice with the rejected stacks in the spec's Decisions section.

## Acceptance

- Give the foundations acceptance lines for the build and for CI.
- Write Given, When, Then for each user story.
- Write rules and error handling as "WHEN <event>, THE SYSTEM SHALL <response>" sentences.
- Make every criterion pass or fail with no judgement call.
- Number each criterion under the Test seams section, such as `5.1`, and place it at an agreed seam.
- Write criteria for the foundations themselves, such as the build producing a release artifact and CI running the tests.
- A text criterion is a criterion about the repository's own authored text: a document, a README, a changelog, a version file, or the wording of a skill, a prompt or a brief.
- To tell a text criterion from a behaviour criterion, ask whether a change to shipped code alone can make it fail; when it cannot, it is a text criterion.
- Place a text criterion at the seam `authored-text`, which interphase reserves for text criteria and declares with `builder_runs` true, and give it acceptance lines and no test row: each line's command is a lint check the repository's lint stage runs, an existing one or one a Step adds beside the repository's other lint checks, and it exits 0 when the text is right and 1 when it is not.
- The Step that claims a text criterion lists the file of every lint check it adds and, when the lint stage names its checks one by one, the file that names them, so the check is registered there; it has an empty acceptance list when it claims only text criteria, and adds no locked path.
- When the repository has no lint stage, place a criterion about authored text at an ordinary seam and give it a test row like any other criterion, never at the seam `authored-text`.
- Start the command of a lint check a Step adds with a program already installed, such as `python3 scripts/check_changelog.py` or `sh scripts/check_changelog.sh`, because the surface probe runs before the Step adds the file.
- Follow `${CLAUDE_PLUGIN_ROOT}/core/variation.md` for every behaviour that varies from run to run.

## Steps

Design the Steps during the interview, following the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`. Give each Step the acceptance criteria its tests prove.

- The first Step builds a walking skeleton: the repository, the build, CI, the test harness and one thin path that runs end to end.
- Every later Step comes after the walking skeleton and adds a slice that runs end to end.
- Never build a layer that cannot run until a later Step.
