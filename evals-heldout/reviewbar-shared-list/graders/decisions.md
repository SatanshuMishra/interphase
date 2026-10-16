---
type: regex
target: { source: file, path: docs/specs/reviewbar-shared-list.md }
pattern: '## \d+\. Decisions'
match: contains
---

Passes when the spec holds a numbered Decisions section.
