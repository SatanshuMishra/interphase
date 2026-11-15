---
name: feature
description: Use when the user wants something that does not exist yet, either a new capability or an extension of an existing one, and its intent, scope and success test are not yet pinned down.
argument-hint: "[what should exist]"
---

Pathway: feature.

1. The request is `$ARGUMENTS`, or the user's latest request when this skill started automatically.
2. Read `${CLAUDE_PLUGIN_ROOT}/core/phases.md` in full before any other action. Follow it with this pathway.
3. The playbook is `${CLAUDE_PLUGIN_ROOT}/core/pathways/feature.md`.
4. The spec template is `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-feature.md`.
5. If phase 2 classifies the request as a different pathway, say so. Then invoke the Skill tool with that pathway's skill instead.
