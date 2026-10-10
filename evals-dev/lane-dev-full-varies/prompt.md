---
name: lane-dev-full-varies
description: A request whose tags come from a language model writes a full spec, not a brief.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Tag each note automatically with topics picked by a language model. Work autonomously. Name the spec lane-dev-full-varies.
