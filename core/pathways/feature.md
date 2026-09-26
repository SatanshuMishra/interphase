# Feature playbook

Use this playbook when the request is for something that does not exist yet. Follow it alongside `${CLAUDE_PLUGIN_ROOT}/core/phases.md`. Write the spec from `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-feature.md`.

## Ground

Research before you ask.

- Find the existing code the feature extends or sits beside, the patterns it must follow, and a good existing example to copy.
- Find how the project tests similar behaviour and the command that runs one test.
- For libraries or outside services involved, get current documentation through the `interphase:scout` agent.

## Questions

Use this bank as the checklist of what must be known. Skip any question the Ground phase already answered.

- When does this come up, what is the user trying to do, and what should that let them achieve?
- What is the problem really, and whose problem is it?
- How will the benefit be measured?
- Who has to behave differently, and how?
- What are the rules? Give one concrete example of each.
- For each item: would you stop the release without it?
- What could reasonably be a goal but is not?
- Which assumption, if wrong, sinks this?
- Imagine it shipped and failed. Why?
- Edge cases: terms, ranges, ordering, output format, units, precision, empty and huge inputs.
- Non-functional needs: performance, security, privacy, compatibility, migration.

## Extra step

Propose two or three approaches with their trade-offs. Put the recommended one first. Let the user choose before you write the spec. Record the choice in the decisions file and the rejected approaches in section 10 of the spec.

## Acceptance

- Write Given, When, Then for each user story.
- Write rules and error handling as "WHEN <event>, THE SYSTEM SHALL <response>" sentences.
- Make every criterion pass or fail with no judgement call.
- Give each criterion its own numbered heading under the Acceptance criteria section, such as `### 7.1 <short name>`.

## Steps

Design the Steps during the interview, one per independently testable behaviour, following the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`. Give each Step the acceptance criteria its tests prove. Split Steps along file boundaries where you can.
