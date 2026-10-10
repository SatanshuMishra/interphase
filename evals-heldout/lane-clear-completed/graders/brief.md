---
type: regex
target: { source: file, path: docs/specs/lane-clear-completed.md }
pattern: '^Lane: brief\.$'
flags: m
---

Passes when the spec is headed by the brief lane line.
