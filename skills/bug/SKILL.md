---
name: bug
description: Use when existing behaviour is wrong and the user wants the cause found or the problem pinned down before anything is changed, such as "X does Y instead of Z", "X stopped working", "determine the cause" or "why does X".
argument-hint: "[what is wrong]"
---

Pathway: bug.

1. The request is `$ARGUMENTS`, or the user's latest request when this skill started automatically.
2. Read `${CLAUDE_PLUGIN_ROOT}/core/phases.md` in full before any other action. Follow it with this pathway.
3. The playbook is `${CLAUDE_PLUGIN_ROOT}/core/pathways/bug.md`.
4. The spec template is `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-bug.md`.
5. If phase 2 classifies the request as a different pathway, say so. Then invoke the Skill tool with that pathway's skill instead.
