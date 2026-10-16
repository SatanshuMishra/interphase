---
type: regex
target: { source: file, path: docs/specs/reviewbar-dev-csv-export.md }
pattern: '## \d+\. Decisions'
match: contains
---

Passes when the spec holds a numbered Decisions section.
