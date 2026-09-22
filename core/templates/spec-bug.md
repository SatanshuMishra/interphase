# {{title}}

Pathway: bug.

Date: {{date}}.

## 1. Request

{{The user's request, word for word.}}

## 2. Summary

{{One or two sentences: what is wrong, where, and for whom.}}

## 3. Environment

{{Version, operating system, runtime, configuration and component where the bug occurs.}}

## 4. Steps to reproduce

{{Numbered steps, including setup, that reproduce the bug every time or as often as it occurs.}}

{{How often it reproduces: always, sometimes, or never again.}}

## 5. Expected and actual

{{Expected: what should happen.}}

{{Actual: what happens instead.}}

## 6. Evidence

{{Every reproduction run: the command and its observed output.}}

{{The draft failing test path, docs/specs/<slug>.repro.<ext>, and its failing output.}}

{{Logs, stack traces and screenshots, if any.}}

## 7. Severity and workaround

{{Who is affected, how badly, and any known workaround.}}

## 8. Root cause

{{Ranked hypotheses. For each probe: the hypothesis, one line describing the change, and the result. Mark unconfirmed hypotheses as unconfirmed.}}

{{The confirmed root cause, or why it could not be confirmed.}}

## 9. Fix boundary

### Current

{{WHEN <condition> THEN the system <wrong behaviour>}}

### Expected

{{WHEN <condition> THE SYSTEM SHALL <right behaviour>}}

### Unchanged

{{WHEN <other condition> THE SYSTEM SHALL CONTINUE TO <behaviour that already works>}}

## 10. Acceptance criteria

{{The test that fails before the fix and passes after, named by file and test.}}

{{Checks that the unchanged behaviour still works.}}

## 11. Assumptions

{{Every default chosen without the user's explicit answer, one per line.}}

## 12. Open questions

{{At most three open questions, each with why it is safe to leave open.}}

## 13. Work breakdown

{{The Steps. The fix Step carries the full draft test text and the path where it belongs.}}

## 14. Prevention

{{What would have caught this earlier, such as a test, a check or a monitor.}}
