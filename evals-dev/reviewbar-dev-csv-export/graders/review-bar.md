---
type: regex
target: { source: file, path: docs/specs/reviewbar-dev-csv-export.md }
pattern: '## \d+\. Review bar'
match: contains
---

Passes when the spec holds a numbered Review bar section.
