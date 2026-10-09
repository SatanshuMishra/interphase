# {{title}}

Pathway: project.

Date: {{date}}.

## 1. Request

{{the user's request, word for word}}

## 2. Problem and why now

{{the real problem, whose problem it is, and why it matters now}}

{{how the benefit will be measured}}

## 3. Users and stories

{{who uses this, the product's domain and what is at stake for them}}

{{user stories: as a <user>, I want <action>, so that <outcome>}}

## 4. Stage and definition of done

{{proof of concept or product, and what changes if that stage changes}}

{{the definition of done for the first usable version}}

## 5. Goals and non-goals

{{goals, each one the first usable version would stop without}}

{{non-goals: things that could reasonably be goals but are not, at least one}}

## 6. Platforms and environments

{{each platform with its minimum version and the hardware it must run on}}

{{each environment it runs in, such as development, CI and release, and how they differ}}

## 7. Stack and alternatives

{{the chosen stack, each part with its version and why it was chosen}}

{{the rejected stacks and their trade-offs}}

## 8. Repository and tooling

{{the repository layout, with the purpose of each top-level folder}}

{{build tooling, and how dependencies and versions are pinned}}

{{for a re-platform, the existing code, build, CI and release this replaces, with paths}}

## 9. Test strategy

{{each kind of behaviour, how it is tested, the test framework and the command that runs one test}}

## 10. Delivery

{{what CI runs, and on which events}}

{{release: packaging, signing, distribution and size}}

{{licence and third-party attribution}}

## 11. Operations

{{configuration and secrets: where each lives and how it reaches each environment}}

{{logging and diagnostics: what is recorded and where it goes}}

## 12. Requirements

{{numbered requirements, each with the rule and one concrete example}}

{{non-functional needs: performance, security, privacy, compatibility, migration}}

## 13. Acceptance criteria

### 13.1 {{short name of the first criterion}}

{{Given, When, Then for one user story, or WHEN <event>, THE SYSTEM SHALL <response> for one rule, error case or foundation}}

{{one more numbered heading, 13.2, 13.3 and so on, for each further criterion}}

## 14. Edge cases

{{terms, ranges, ordering, output format, units, precision, empty and huge inputs, each with the expected behaviour}}

## 15. Walking skeleton and slices

{{the walking skeleton: the repository, the build, CI, the test harness and the one thin path that runs end to end}}

{{each later slice, in order, and the end-to-end path it adds}}

## 16. Assumptions

{{every default chosen without the user's explicit answer, one per line}}

## 17. Open questions

{{at most three open questions, each with why it is safe to leave open, or None}}

## 18. Verification

{{commands and checks that prove the project works after it is built}}

## 19. Reuse and change

{{Reused as is, Kept separate and Changed, filled as the section Record the result of `${CLAUDE_PLUGIN_ROOT}/core/practices.md` says}}

## 20. Variation

{{each behaviour that varies from run to run: its kind, the ways its input varies, the held-out set and the pass rule, following `${CLAUDE_PLUGIN_ROOT}/core/variation.md`; or Not applicable: <reason>}}
