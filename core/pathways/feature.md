# Feature playbook

Use this playbook when the request is for something that does not exist yet. Follow it alongside `${CLAUDE_PLUGIN_ROOT}/core/phases.md`. Write the spec from `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-feature.md`.

## Ground

Research before you ask.

- Find the existing code the feature extends or sits beside, and the patterns it must follow.
- Find code that already does all or part of what is asked, following `${CLAUDE_PLUGIN_ROOT}/core/practices.md`.
- Find how the project tests similar behaviour and the command that runs one test.
- For libraries or outside services involved, get current documentation through the `interphase:scout` agent.

## Questions

Use this bank as the checklist of branches the design tree must reach. Ask only what passes the hard bar of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`; skip any question the Ground phase or the intent round already answered.

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

Propose two or three approaches with their trade-offs as one frontier question, the recommended one first. Record the choice in the decisions file, and the choice with the rejected approaches in the spec's Decisions section.

## Acceptance

- Give every behaviour acceptance lines for its error state, its empty state and its permission state.
- Write Given, When, Then for each user story.
- Write rules and error handling as "WHEN <event>, THE SYSTEM SHALL <response>" sentences.
- Make every criterion pass or fail with no judgement call.
- Number each criterion under the Test seams section, such as `5.1`, and place it at an agreed seam.
- A text criterion is a criterion about the repository's own authored text: a document, a README, a changelog, a version file, or the wording of a skill, a prompt or a brief.
- To tell a text criterion from a behaviour criterion, ask whether a change to shipped code alone can make it fail; when it cannot, it is a text criterion.
- Place a text criterion at the seam `authored-text`, which interphase reserves for text criteria and declares with `builder_runs` true, and give it acceptance lines and no test row: each line's command is a lint check the repository's lint stage runs, an existing one or one a Step adds beside the repository's other lint checks, and it exits 0 when the text is right and 1 when it is not.
- The Step that claims a text criterion lists the file of every lint check it adds and, when the lint stage names its checks one by one, the file that names them, so the check is registered there; it has an empty acceptance list when it claims only text criteria, and adds no locked path.
- When the repository has no lint stage, place a criterion about authored text at an ordinary seam and give it a test row like any other criterion, never at the seam `authored-text`.
- Start the command of a lint check a Step adds with a program already installed, such as `python3 scripts/check_changelog.py` or `sh scripts/check_changelog.sh`, because the surface probe runs before the Step adds the file.
- Follow `${CLAUDE_PLUGIN_ROOT}/core/variation.md` for every behaviour that varies from run to run.

## Steps

Design the Steps during the interview, one per independently testable behaviour, following the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`. Give each Step the acceptance criteria its tests prove. Split Steps along file boundaries where you can.
