# {{title}}

Pathway: bug.

Date: {{date}}.

## 1. Problem

{{the user's request, word for word}}

{{what is wrong, where and for whom: the expected result and the actual result}}

## 2. Intent

{{the intent lines of the decisions file, word for word, each with its id, such as - I1 Goal: <goal>}}

## 3. Reproduction and cause

{{the steps to reproduce, every reproduction run's command and observed output, and how often it reproduces}}

{{the draft failing test path, docs/specs/<slug>.repro.<ext>, and its failing output}}

{{the ranked hypotheses, each probe's hypothesis, one line describing the change and its result, and the confirmed cause with path and line, or why it could not be confirmed}}

{{every other place with the same fault, with path and line, or None}}

## 4. Decisions

{{the fix boundary as three statements: Current: WHEN <condition> THEN the system <wrong behaviour>. Expected: WHEN <condition> THE SYSTEM SHALL <right behaviour>. Unchanged: WHEN <other condition> THE SYSTEM SHALL CONTINUE TO <behaviour that already works>.}}

{{any further numbered decision, and each threat the fix must withstand with its defence}}

### Reuse and change

{{Reused as is, Kept separate and Changed, filled as the section Record the result of `${CLAUDE_PLUGIN_ROOT}/core/practices.md` says}}

### Assumptions

{{each reading chosen without the user's answer, ending (relies on I<n>) for the intent line it rests on, or - None}}

### Risks

{{every repeated failure kind outcomes.py wrote to the record, then every other risk, or - None}}

## 5. Test seams

{{written by the render script from the record: the agreed seams, then one numbered heading per acceptance criterion, 5.1 being the reproduction test}}

## 6. Out of scope

{{what could reasonably be in scope but is not, at least one item}}
