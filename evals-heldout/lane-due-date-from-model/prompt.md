---
name: lane-due-date-from-model
description: A request whose output comes from a language model writes a full spec, not a brief.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Suggest a due date for each new task using a language model. Work autonomously. Name the spec lane-due-date-from-model.
