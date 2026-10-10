---
name: variation-language-model-summary
description: A request to summarise task notes with a language model is marked as varying output.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Write a one-line summary of each task's notes using a language model. Work autonomously. Name the spec variation-language-model-summary.
