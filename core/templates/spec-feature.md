# {{title}}

Pathway: feature.

Date: {{date}}.

## 1. Request

{{the user's request, word for word}}

## 2. Problem and why now

{{the real problem, whose problem it is, and why it matters now}}

{{how the benefit will be measured}}

## 3. Users and stories

{{who uses this and who has to behave differently, and how}}

{{user stories: as a <user>, I want <action>, so that <outcome>}}

## 4. Goals and non-goals

{{goals, each one the release would stop without}}

{{non-goals: things that could reasonably be goals but are not, at least one}}

## 5. Boundaries

{{what this feature must not change, touch or depend on}}

## 6. Requirements

{{one line per requirement: the behaviour in a few words and the number of the acceptance criterion that states it, such as 7.1}}

{{non-functional needs: performance, security, privacy, compatibility, migration, each citing the acceptance criterion that states it, such as 7.1}}

## 7. Acceptance criteria

### 7.1 {{short name of the first criterion}}

{{Given, When, Then for one user story, or WHEN <event>, THE SYSTEM SHALL <response> for one rule or error case}}

{{one more numbered heading, 7.2, 7.3 and so on, for each further criterion}}

## 8. Edge cases

{{one line per edge case: the case in a few words and the number of the acceptance criterion whose row covers it, such as 7.1}}

## 9. Code map

{{existing files and symbols the feature extends or sits beside, with paths}}

{{the pattern to follow and the command that runs one test}}

## 10. Approach and alternatives

{{the chosen approach and why}}

{{the other approaches considered and their trade-offs}}

## 11. Assumptions

{{every default chosen without the user's explicit answer, one per line}}

## 12. Open questions

{{at most three open questions, each with why it is safe to leave open, or None}}

## 13. Verification

{{commands and checks that prove the feature works after it is built}}

## 14. Reuse and change

{{Reused as is, Kept separate and Changed, filled as the section Record the result of `${CLAUDE_PLUGIN_ROOT}/core/practices.md` says}}

## 15. Variation

{{each behaviour that varies from run to run: its kind, the ways its input varies, the held-out set and the pass rule, following `${CLAUDE_PLUGIN_ROOT}/core/variation.md`; or Not applicable: <reason>}}

## 16. Review bar

{{the threats the change must withstand and the level of defence for each, each one defended somewhere in this spec; or that it has none beyond its acceptance criteria, and why}}

{{what a reviewer may block on beyond the acceptance criteria: the requirements, the boundaries and the non-goals}}

{{what is out of scope for review: at least weaknesses the code had before the change, and hardening beyond the named threats}}
