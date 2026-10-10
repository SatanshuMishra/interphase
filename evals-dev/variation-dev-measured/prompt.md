---
name: variation-dev-measured
description: A request about a slow note list on a phone is marked as measured on a device.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: The note list takes three seconds to appear on my phone. Work autonomously. Name the spec variation-dev-measured.
