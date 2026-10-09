---
type: regex
target: { source: file, path: docs/specs/variation-dev-negative.record.json }
pattern: '"varies"'
match: not_contains
---

Passes when no criterion in the record is marked as varying.
