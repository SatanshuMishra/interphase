---
type: regex
target: { source: file, path: docs/specs/lane-dev-eligible-feature.md }
pattern: '^Lane: brief\.$'
flags: m
---

Passes when the spec is headed by the brief lane line.
