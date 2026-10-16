---
name: reviewbar-shared-list
description: A request to share the task list through a link writes a spec whose Decisions name the threats to the link and their defence.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Let people share their task list with a friend through a link the friend can open without an account. Work autonomously. Name the spec reviewbar-shared-list.
