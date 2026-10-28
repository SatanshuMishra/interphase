# Questioning

The interview is a grilling: question the user relentlessly, in rounds, until you share one understanding of what gets built. Map it as a design tree, where every decision branches into the decisions that hang off it.

## The hard bar

Ask a question only when both hold:

1. Nothing you can read answers it: not the request, the code, the docs, the project's written rules, `GLOSSARY.md`, the ADRs in `docs/adr/`, the decisions files of earlier specs, an answer already given, or a quick run.
2. A different answer would change what gets built: a file, a test, an acceptance criterion or a Step.

Facts are yours to find and decisions are the user's. When a question needs a fact, look it up, or dispatch the `interphase:scout` agent for outside documentation, and ask only the decision the fact leaves open. Never ask the user to confirm something you read. A question that fails the bar is neither asked nor recorded as an assumption.

Wording that states how the product behaves is a fact, not a cosmetic choice. For example, a mockup's "the N days in a row you kept writing" says what the count measures; look it up in the code before using it. Cosmetic choices, such as colour, spacing, icons and wording that states nothing about how the product behaves, are never asked: take the mockup's or the existing style's. Such a choice is read, not guessed, so it is not an assumption either. The one exception is a choice that breaks the impeccable skill's UI standard: the spec states the corrected behaviour as an assumption, never as a question.

## Intent round

Open the interview with one round, in plain text, that asks three things:

- Goal: what the change must achieve.
- Why: why it is wanted now, and for whom.
- Success: how the user will know it worked.

Draft a recommended answer for each from the request and what grounding found, so that "yes" accepts all three. When the request mixes pathways, spans independent subsystems or is large, put the pathway, the size and the split in this round too.

Write the answers to the `## Intent` section of the decisions file as numbered lines, `- I1 Goal: <goal>`, `- I2 Why: <why>`, `- I3 Success: <success>`, adding `I4` and on for each further success test or constraint the user states. Every guess made after the interview cites one of these lines.

## Frontier rounds

After the intent round, work the design tree in rounds. The frontier is every decision whose prerequisites are settled: the questions you can ask now without guessing at answers you have not heard yet.

- Ask the whole frontier in one round. There is no cap on how many questions a round holds or how many rounds the interview takes.
- A question whose answer depends on another question still open in the same round belongs to a later round.
- When a lookup is still running, it is an unsettled prerequisite: ask the rest of the frontier now, and hold back only the questions downstream of it.
- After each round, recompute the frontier from the answers and ask the next round.

Write each round as numbered plain text, never through the AskUserQuestion tool:

```
Q1. <short title>: <the question, with the options when there are some>
Recommended: <your answer>

Q2. <short title>: <the question>
Recommended: <your answer>
```

Word each question so that "yes" accepts the recommended answer. The user may answer "yes" to the whole round or answer by number.

The tree covers what the pathway's `## Questions` bank lists, and always these branches:

- The scope: what is in, what is out, and the rules, with one concrete example of each.
- The shape of the work: what ships together, what order matters and what could be thrown away.
- Each fork between sharing code and keeping it apart, as `${CLAUDE_PLUGIN_ROOT}/core/practices.md` defines one.
- The test seams, as the section Test seams below says.
- The pre-mortem: "Imagine this shipped and you are unhappy with it. Why?", recommending the likeliest failure.

## Domain language

Follow `${CLAUDE_PLUGIN_ROOT}/core/domain.md` throughout the interview.

- When the request or an answer uses a term that conflicts with the glossary, put it in the next round: "The glossary defines X as A, but you seem to mean B. Which is it?"
- When a term is vague or overloaded, propose one precise term as the recommended answer.
- When a relationship between domain concepts is unsettled, invent the concrete scenario that forces the boundary and ask it.
- When the user states how something works and the code disagrees, ask which is right.
- When a term is settled, write it to the glossary at once.

## Test seams

A seam is the public interface a test observes behaviour at, without reaching inside. Agree the seams before any acceptance criterion is written against them.

- Prefer a seam the project already tests at to a new one, and the highest seam that observes the behaviour.
- Use as few seams as the change allows; the ideal number is one.
- Propose each seam with one line on what it catches and one on what it misses, and whether the builder can run tests there.
- Put the seams to the user as a frontier question. Write no acceptance test at a seam the user has not agreed.

## Push back on scope

- When a request names a solution, ask for the problem first; the intent round usually settles it.
- When a request spans several independent subsystems, split it before refining.
- Split work vertically, so each piece works end to end. Prefer the split that lets one piece be thrown away. The word "manage" usually hides create, read, update and delete.
- Record what is cut in the spec's Out of scope section, so it does not creep back.

## Record each answer

- Append each settled decision to the `## Decisions` section of the decisions file at once, as one `- ` line stating a rule in the user's terms. Example: `- Expired sessions redirect to the login screen; they never render an empty page.`
- Never reword or delete an earlier line. Give a reversed decision a new line that says it replaces the earlier one.
- Update the record at the same time: the seams, the criteria and the owning Steps.
- When a round is settled, append one entry to the record's rounds list at once: kind is `intent` for the intent round or `frontier` for a frontier round, questions is the number of questions the round asked (the intent round counts one for each of goal, why and success, and one for each further intent question it asked), and changed is the number of answers that differ from the recommended one, an answer of yes to a whole round changing none.

## Know when to stop

The interview ends when the frontier is empty: every branch of the tree visited and nothing left silently assumed. Then hold the read-back of phase 7, the one place the AskUserQuestion tool is used, to approve or change what you understood. Never act on the interview before the user approves it.

## After the interview

Once the user approves the read-back, ask nothing more and never stop for an answer. Every gap a later phase finds, in writing the spec, designing a Step or fixing a review finding, is filled with a well-reasoned guess:

- Take the reading the intent best supports, together with the project's context: who the product serves, what is at stake and the domain.
- Write it to the spec's Assumptions as one line ending `(relies on I<n>)`, naming the intent line it relied on, such as `- Exports include archived tasks, because the user wants a full backup (relies on I1).`
- Add the same line to the `assumptions` of every Step it shapes, so the pull request that builds the Step shows it.

## Unattended runs

When the user's instructions, in the conversation or in the project's written instructions, say to work autonomously, hold no interview: ask no question and seek no approval.

- Write the `## Intent` section from the request and the project's context, ending each line `(inferred)`.
- Settle every decision the way the section After the interview fills a gap, from the intent and the project's context.
- Never fall back to the lightest option. Research the established practice for that context: the standards for the capability itself, the laws and standards that govern the domain and the data the requested work touches, and what comparable products in that domain ship. Dispatch the `interphase:scout` agent for outside documentation.
- List the threats that practice expects for what is at stake in the requested work, and require a defence for each in the layers that practice uses at those stakes: the established minimum where little is at stake, and never only that minimum where much is.
- Write the concrete, specific requirements that context calls for, without avoiding complexity or added services, so there is something specific to test. Never put one the context calls for in Out of scope.
- Treat what the project depends on, the data it holds and where it runs as the starting point, not a limit. When the context calls for something the project cannot do yet, require what it takes, such as a new dependency, a new stored field, an added service or a change to how it is deployed.
- When only something outside the code can meet a requirement, such as the server in front of the app, still write its acceptance criterion, marked unproven with the reason when the builder cannot check it, and keep in the code every part the code can enforce and test.
- When a written rule or a convention of the project forbids what the context calls for, meet the requirement within the rule only when that meets it as fully as the established practice at those stakes does. Otherwise keep the requirement at full strength and record the override as `${CLAUDE_PLUGIN_ROOT}/core/practices.md` says.

When a surface probe of Phase 6 fails for a line at a seam the builder runs, the run cannot prove that criterion here, so it stops instead of guessing: write `Assumption: <surface> cannot be driven here because <detail>; the run stops (relies on I<n>)` to the decisions file, verify the guard as Phase 10 of `${CLAUDE_PLUGIN_ROOT}/core/phases.md` says, report the stop and the record's stop reason, and stop.

Example: `Add file uploads` for a hobby photo blog calls for a size limit and a file-type check; for a hospital's imaging records it calls for virus scanning, encryption at rest, an access audit log and a retention rule. If the hospital project cannot encrypt files yet, the spec requires what lets it.

A run that starts unattended stays unattended, even when it switches from the brief lane to the full pathway.
