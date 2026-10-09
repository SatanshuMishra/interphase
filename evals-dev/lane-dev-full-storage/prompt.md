---
name: lane-dev-full-storage
description: A request that changes what each note stores writes a full spec, not a brief.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Keep every past version of a note so an earlier one can be restored. Work autonomously. Name the spec lane-dev-full-storage.
