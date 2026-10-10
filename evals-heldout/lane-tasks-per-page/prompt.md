---
name: lane-tasks-per-page
description: A paging bug with a one-line cause writes a spec headed by the brief lane.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: The task list shows 9 tasks per page instead of 10. Work autonomously. Name the spec lane-tasks-per-page.
