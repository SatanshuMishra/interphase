# {{title}}

Pathway: {{pathway}}.

Lane: brief.

Date: {{date}}.

## 1. Problem

{{the user's request, word for word}}

{{for each item, three statements: Current: WHEN <condition> THEN the system <behaviour today>. Expected: WHEN <condition> THE SYSTEM SHALL <behaviour wanted>. Unchanged: WHEN <other condition> THE SYSTEM SHALL CONTINUE TO <behaviour that stays>.}}

## 2. Intent

{{the intent lines of the decisions file, word for word, each with its id, such as - I1 Goal: <goal>}}

## 3. Evidence

{{for a bug, the reproduction, its output and the confirmed cause with path and line; otherwise the code it extends with path and line, and the pattern it follows}}

## 4. Decisions

### Reuse and change

{{Reused as is, Kept separate and Changed, filled as the section Record the result of `${CLAUDE_PLUGIN_ROOT}/core/practices.md` says}}

### Assumptions

{{each reading chosen without the user's answer, ending (relies on I<n>) for the intent line it rests on, or - None}}

## 5. Test seams

{{written by the render script from the record: the agreed seams, then one numbered heading per acceptance criterion, 5.1, 5.2 and so on}}

## 6. Out of scope

{{the Unchanged statements, and anything else the request could reasonably be read to include}}
