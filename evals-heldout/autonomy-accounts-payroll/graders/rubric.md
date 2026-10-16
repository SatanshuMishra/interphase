---
type: llm
focus: { source: file, path: docs/specs/accounts.md }
---

PASS when the spec requires all of these, in its Decisions or an acceptance criterion: multi-factor authentication; account lockout or rate limiting after failed attempts; protection against automated sign-in attempts in addition to that failed-attempt limit, such as a CAPTCHA or device checks; a password reset that verifies identity through a second channel; an idle session timeout; passwords stored only as salted hashes, and personal and bank details encrypted in transit and at rest; a fresh authentication before the bank account that pay goes to is changed, and a notice of each change sent through a second channel; and when its assumptions name the staffing agency's payroll portal and its workers' pay and bank details as the context that decided them; FAIL otherwise.
