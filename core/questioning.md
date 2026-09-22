# Questioning

## Sort every unknown

| Class | Examples | What to do |
|---|---|---|
| Intent | who it is for, the outcome, the core behaviour, what is in or out of scope, how the user will know it works | Ask until it is settled. |
| Structure | where it plugs in, interfaces, where data is stored, which files change | Look it up in the code; ask only when the code is silent. |
| Cosmetic | colour, spacing, exact wording, icons | Default to the mockup or the existing style and record the default as an assumption. |

Test every unknown before you ask it. If a different answer would not change a file, a test or an acceptance criterion, do not ask it.

## Choose the next question

- Never ask what the code, the docs or a quick run can answer.
- Drop any question whose answer would not change what gets built.
- Rank the rest by how much the answer matters times how unsure you are. Ask the top ones first.
- Give every question a recommended answer, so "yes" is a complete reply.
- Ask about one concept per question.
- Match effort to the request. Ask more questions for thin or risky requests and few for clear ones. A long, detailed request can still hide ambiguity.

## Ask

- Ask the first question, about purpose or the outcome the user wants, open-ended in plain text.
- Ask every later question through the AskUserQuestion tool.
- Put up to 4 questions in one call, and only questions that do not depend on each other. A question that depends on an unanswered one waits for the next round.
- Give each question 2 to 4 options. Put the recommended option first, with "(Recommended)" at the end of its label. Keep the header to at most 12 characters. The tool always adds a free-text option.
- Use an open question whenever the options cannot be listed honestly.
- Never set a question to continue on its own after a timeout.

## Spot ambiguity

| Kind | Example | How to spot it |
|---|---|---|
| Word meaning | "archive": hide it, delete it, or export it? | domain words, and everyday words used as jargon |
| Sentence structure | "non-friendly and unknown mission or restricted airspace" | "and" and "or" mixed in one sentence |
| Quantity | "every light has their switch": one switch each, or one shared? | "all", "each", "every", "only" |
| Reference | "treat the roads before they freeze": the roads, or the trucks? | "it", "they", "this" |
| Vagueness | "fast response time" | no way to measure it |
| Missing information | "protect a small group from the elements": an igloo or a space station? | walking the playbook's question bank |
| Conflicting goals | two Musts that cannot both hold | forcing a Must, Should, Could, Won't ranking |

Imagine two different builders reading the request. Ask about every place they would build different things.

## Push back on scope

- When a request names a solution, ask for the problem first.
- When a request spans several independent subsystems, split it before refining.
- Split work vertically, so each piece works end to end. Prefer the split that lets one piece be thrown away. The word "manage" usually hides create, read, update and delete.
- For each proposed item, ask: would you stop the release without it? Keep Musts to no more than about 60 percent of the effort.
- Record what is cut as a non-goal or a Won't, so it does not creep back.
- Surface hidden scope with the pre-mortem.

## Record each answer

- Append each settled answer to `docs/specs/<slug>.decisions.md` immediately. Write it as one line starting with `- `, as a rule in the user's terms. Example: `- Expired sessions redirect to the login screen; they never render an empty page.`
- Never reword or delete an earlier line. Give a reversed decision a new line that says it replaces the earlier one.
- Update the affected part of the working notes or spec at the same time.

## Know when to stop

Stop asking when all three hold:

1. Every Must requirement has a way to tell pass from fail.
2. No open question would change a file, a test or an acceptance criterion. Everything else is written down as an assumption or deferred with a reason.
3. The user confirmed the read-back in phase 6.

There is no fixed question count. When you defer questions, list them in the spec's Open questions section with why each is safe to leave.
