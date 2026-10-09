# {{title}}

Pathway: {{pathway}}.

Lane: brief.

Date: {{date}}.

## 1. Request

{{the user's request, word for word}}

## 2. Change

{{for each item, three statements: Current: WHEN <condition> THEN the system <behaviour today>. Expected: WHEN <condition> THE SYSTEM SHALL <behaviour wanted>. Unchanged: WHEN <other condition> THE SYSTEM SHALL CONTINUE TO <behaviour that stays>.}}

## 3. Evidence

{{for a bug, the reproduction, its output and the confirmed cause with path and line; otherwise the code it extends with path and line, and the pattern it follows}}

## 4. Acceptance criteria

### 4.1 {{short name of the first criterion}}

{{WHEN <condition> THE SYSTEM SHALL <behaviour wanted>, then one more numbered heading, 4.2, 4.3 and so on, for each further criterion}}

## 5. Assumptions

{{every default chosen without the user's explicit answer, one per line}}

## 6. Reuse and change

{{Reused as is, Kept separate and Changed, filled as the section Record the result of `${CLAUDE_PLUGIN_ROOT}/core/practices.md` says}}
