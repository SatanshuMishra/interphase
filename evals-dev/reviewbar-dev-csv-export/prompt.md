---
name: reviewbar-dev-csv-export
description: A request to download every task as a CSV file writes a spec whose Review bar names the threats to the file and their defence.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Add a button that downloads every task as a CSV file. Work autonomously. Name the spec reviewbar-dev-csv-export.
