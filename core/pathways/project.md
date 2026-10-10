# Project playbook

Use this playbook when the request is to create a new repository, or to replace an existing repository's stack, build, CI or release. Follow it alongside `${CLAUDE_PLUGIN_ROOT}/core/phases.md`. Write the spec from `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-project.md`.

## Ground

Research before you ask.

- Research the product's domain, who its users are and what is at stake for them.
- For a re-platform, read the existing code, build, CI, release and written rules before proposing any change.
- For candidate stacks, libraries and services, get current documentation through the `interphase:scout` agent.
- Follow `${CLAUDE_PLUGIN_ROOT}/core/practices.md`.

## Questions

Use this bank as the checklist of what must be known. Skip any question the Ground phase already answered.

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

Propose two or three stacks with their trade-offs. Put the recommended one first. Let the user choose before you write the spec. Record the choice in the decisions file and the rejected stacks in the Stack and alternatives section of the spec.

## Acceptance

- Write Given, When, Then for each user story.
- Write rules and error handling as "WHEN <event>, THE SYSTEM SHALL <response>" sentences.
- Make every criterion pass or fail with no judgement call.
- Give each criterion its own numbered heading under the Acceptance criteria section, such as `### 13.1 <short name>`.
- Write criteria for the foundations themselves, such as the build producing a release artifact and CI running the tests.
- Follow `${CLAUDE_PLUGIN_ROOT}/core/variation.md` for every behaviour that varies from run to run.

## Steps

Design the Steps during the interview, following the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`. Give each Step the acceptance criteria its tests prove.

- The first Step builds a walking skeleton: the repository, the build, CI, the test harness and one thin path that runs end to end.
- Every later Step comes after the walking skeleton and adds a slice that runs end to end.
- Never build a layer that cannot run until a later Step.
