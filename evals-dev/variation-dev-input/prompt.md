---
name: variation-dev-input
description: A request to find notes from a remembered description is marked as open-ended input.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Let people search their notes by describing what they remember, like 'that recipe with lemons from last spring'. Work autonomously. Name the spec variation-dev-input.
