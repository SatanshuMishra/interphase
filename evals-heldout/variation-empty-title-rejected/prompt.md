---
name: variation-empty-title-rejected
description: A request to reject an empty task title writes a record with no varying criterion.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Reject a new task whose title is empty, with the message 'Title is required'. Work autonomously. Name the spec variation-empty-title-rejected.
