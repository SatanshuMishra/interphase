---
name: reviewbar-sort-by-due
description: A request to change the order of the task list writes a spec whose Review bar names no security threat.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Sort the task list by due date, soonest first, with tasks that have no due date last. Work autonomously. Name the spec reviewbar-sort-by-due.
