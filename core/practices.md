# Programming practices

These rules apply to every spec on every pathway.

## The five rules

1. One home per piece of logic. Each rule the code enforces lives in one place; never plan a copy of logic that already exists.
2. One reason to change per piece of code. Never bend existing code to fit a new use; code that would change for two unrelated reasons is two pieces.
3. Build only what the request needs. Add no option, hook, layer or abstraction for a use nobody asked for.
4. Follow the project's own written rules and patterns. Keep to the conventions its written rules and existing code follow.
5. Use what the language, libraries or project already provide. Never rebuild what the standard library, a dependency or the project already does.

The project's own written rules win when they conflict with the other four. Note each conflict as a Project rule followed line in the spec's Reuse and change section.

A copy is the same rule written in two places that must always change together. Two pieces of code that look alike but change for different reasons are not a copy.

Bending is adding a mode, flag or branch to existing code that only the new use needs.

## Find what already exists

Before planning any new function, module, component or command, search for code that already does all or part of what is asked. Search three ways:

- By the words of the behaviour.
- By the names of the data it touches.
- Through the callers of the code it extends.

For broad searches, dispatch the `interphase:scout` agent with one self-contained question.

When the request is a bug, the same search finds every other place with the same fault. The fix covers every such place. Raise merging them as a fork only when they are copies.

Read the project's written rules: CLAUDE.md, AGENTS.md, the contributing guide, and the linter and formatter configuration.

## Reuse or ask

Reuse existing code without asking when it already does the job unchanged.

Ask the user only at a fork: when sharing would mean changing existing code for a new use, or keeping apart would mean copying its logic. Ask one question per fork, in the same rounds as the other questions, with a recommendation and a one-line reason.

Recommend sharing the parts that must always change together and keeping apart the parts that differ. A mode, flag or branch that only the new use needs is the sign that the parts differ. Never offer bending as an option.

## Record the result

Write the spec's Reuse and change section as three lists: Reused as is, Kept separate and Changed. Write one line per item: the path or symbol, then what it is used for or why, in a few words. Name only code this change reuses, changes, or kept apart at a fork. Write None for an empty list.

When a project rule overrode one of the other four, add one line after the three lists that starts with Project rule followed: and names the rule and the file it is written in.

Never write a proof for each rule.
