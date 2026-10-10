---
name: lane-dev-full-subsystem
description: A request for shared notebooks with live edits writes a full spec, not a brief.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Let two people share a notebook and see each other's edits. Work autonomously. Name the spec lane-dev-full-subsystem.
