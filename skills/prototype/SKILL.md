---
name: prototype
description: Use when the user has a design mockup, prototype or exported design, such as HTML, React, Figma frames, a Claude Design export or screenshots, and wants it shipped as a working product.
argument-hint: "[mockup path or URL]"
---

Pathway: prototype.

1. The request is `$ARGUMENTS`, or the user's latest request when this skill started automatically.
2. Read `${CLAUDE_PLUGIN_ROOT}/core/phases.md` in full before any other action. Follow it with this pathway.
3. The playbook is `${CLAUDE_PLUGIN_ROOT}/core/pathways/prototype.md`.
4. The spec template is `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-prototype.md`.
5. If phase 2 classifies the request as a different pathway, say so. Then invoke the Skill tool with that pathway's skill instead.
