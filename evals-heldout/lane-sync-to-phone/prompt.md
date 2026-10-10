---
name: lane-sync-to-phone
description: A request that adds a server and a sync format writes a full spec, not a brief.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Sync tasks to a server so they appear on my phone too. Work autonomously. Name the spec lane-sync-to-phone.
