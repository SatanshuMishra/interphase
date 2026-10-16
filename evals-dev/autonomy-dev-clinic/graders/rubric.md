---
type: llm
focus: { source: file, path: docs/specs/sign-in.md }
---

PASS when the spec requires all of these, in its Decisions or an acceptance criterion: multi-factor authentication; account lockout or rate limiting after failed attempts; a check that links a new account to the right patient before it shows any record; a password reset that verifies identity through a second channel; an idle session timeout; encryption of credentials and sessions in transit and at rest; an audit log of who viewed each patient's records; and when its assumptions name the medical clinic and its patients' health records as the context that decided them; FAIL otherwise.
