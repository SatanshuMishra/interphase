---
name: project
description: Use when the user wants to start a new project or repository, or to replace an existing project's stack, build, CI or release, and its foundations, scope and success test are not yet pinned down.
argument-hint: "[what to start or re-platform]"
---

Pathway: project.

1. The request is `$ARGUMENTS`, or the user's latest request when this skill started automatically.
2. Read `${CLAUDE_PLUGIN_ROOT}/core/phases.md` in full before any other action. Follow it with this pathway.
3. The playbook is `${CLAUDE_PLUGIN_ROOT}/core/pathways/project.md`.
4. The spec template is `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-project.md`.
5. If phase 2 classifies the request as a different pathway, say so. Then invoke the Skill tool with that pathway's skill instead.
6. If this conversation was summarized or cleared during this run, re-read `docs/specs/<slug>.record.json`, `docs/specs/<slug>.decisions.md` and `${CLAUDE_PLUGIN_ROOT}/core/phases.md` before acting.
