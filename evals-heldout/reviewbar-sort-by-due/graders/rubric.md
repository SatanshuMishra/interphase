---
type: llm
focus: { source: file, path: docs/specs/reviewbar-sort-by-due.md }
---

PASS when the spec's Review bar says the change has no threats beyond its acceptance criteria and puts weaknesses the app had before the change out of scope for review; FAIL otherwise, and always FAIL when it names a security threat the change must withstand.
