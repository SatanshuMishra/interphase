---
name: variation-plain-english-dates
description: A request to read due dates from typed task text is marked as open-ended input.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Let people type tasks in plain English, like 'call mum tomorrow at 5pm', and set the due date from it. Work autonomously. Name the spec variation-plain-english-dates.
