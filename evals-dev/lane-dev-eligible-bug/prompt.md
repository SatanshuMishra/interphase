---
name: lane-dev-eligible-bug
description: A sort-order bug that contradicts the README writes a spec headed by the brief lane.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Notes are listed oldest first, but the README says newest first. Work autonomously. Name the spec lane-dev-eligible-bug.
