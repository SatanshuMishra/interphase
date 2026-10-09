---
name: variation-dev-negative
description: A request to refuse an overlong note writes a record with no varying criterion.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Refuse to save a note longer than 10,000 characters, with the message 'Note is too long'. Work autonomously. Name the spec variation-dev-negative.
