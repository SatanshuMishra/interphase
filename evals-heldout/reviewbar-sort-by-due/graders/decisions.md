---
type: regex
target: { source: file, path: docs/specs/reviewbar-sort-by-due.md }
pattern: '## \d+\. Decisions'
match: contains
---

Passes when the spec holds a numbered Decisions section.
