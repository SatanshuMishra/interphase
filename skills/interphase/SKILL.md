---
name: interphase
description: Use when the user types /interphase to turn a request into a spec and the kind of request is not yet known.
disable-model-invocation: true
argument-hint: "[request]"
---

# interphase

1. The request is `$ARGUMENTS`. When that is empty, ask the user for the request in plain text.
2. Read `${CLAUDE_PLUGIN_ROOT}/core/phases.md` section "Phase 2: Classify". Classify the request as feature, bug or prototype.
3. Say the classification out loud in one sentence. Let the user override it.
4. Invoke the Skill tool with `interphase:feature`, `interphase:bug` or `interphase:prototype`. Pass the request as the arguments. If the Skill tool is unavailable, read `${CLAUDE_PLUGIN_ROOT}/skills/<pathway>/SKILL.md` and follow it.
