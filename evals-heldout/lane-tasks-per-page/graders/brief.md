---
type: regex
target: { source: file, path: docs/specs/lane-tasks-per-page.md }
pattern: '^Lane: brief\.$'
flags: m
---

Passes when the spec is headed by the brief lane line.
