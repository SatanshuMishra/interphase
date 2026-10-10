---
name: lane-dev-eligible-feature
description: A per-note button that follows an existing button's pattern writes a spec headed by the brief lane.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Add a 'Duplicate' button beside each note's existing 'Delete' button, working the same way. Work autonomously. Name the spec lane-dev-eligible-feature.
