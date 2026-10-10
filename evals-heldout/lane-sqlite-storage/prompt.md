---
name: lane-sqlite-storage
description: A request that changes the stored-data format writes a full spec, not a brief.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Store tasks in SQLite instead of the JSON file. Work autonomously. Name the spec lane-sqlite-storage.
