---
type: regex
target: { source: file, path: docs/specs/reviewbar-dev-button-label.md }
pattern: '## \d+\. Review bar'
match: contains
---

Passes when the spec holds a numbered Review bar section.
