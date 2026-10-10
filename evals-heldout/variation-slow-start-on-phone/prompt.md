---
name: variation-slow-start-on-phone
description: A request to make the app open faster on a phone is marked as measured on a device.
runs: 3
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Skill, Read, Write, Edit, Bash, Glob, Grep, Agent, WebSearch, WebFetch]
---

Use interphase to write a spec for this request, and stop at hand-off: Opening the app takes over two seconds on my Android phone; make it open faster. Work autonomously. Name the spec variation-slow-start-on-phone.
