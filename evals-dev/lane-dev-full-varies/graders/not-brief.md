---
type: regex
target: { source: file, path: docs/specs/lane-dev-full-varies.md }
pattern: 'Lane: brief\.'
match: not_contains
---

Passes when the spec does not take the brief lane.
