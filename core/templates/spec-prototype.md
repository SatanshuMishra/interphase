# {{title}}

Pathway: prototype.

Date: {{date}}.

## 1. Problem

{{the user's request, word for word}}

{{every file, URL and screenshot the prototype came from, where each lives and whether it could be run, and the problem the shipped product solves}}

## 2. Intent

{{the intent lines of the decisions file, word for word, each with its id, such as - I1 Goal: <goal>}}

## 3. User stories

{{a long numbered list covering every screen and journey, each as: As a <actor>, I want <feature>, so that <benefit>}}

## 4. Decisions

{{numbered decisions settling each area of the gap analysis the mockup fakes or omits: which screens are final, every screen state, content variation, interactions not shown, data sources and their failure, validation and error wording, permissions, saving and concurrent edits, the UI quality floor (gap analysis item 11), layout at each screen size, analytics, and each threat with its defence}}

### Reuse and change

{{Reused as is, Kept separate and Changed, filled as the section Record the result of `${CLAUDE_PLUGIN_ROOT}/core/practices.md` says}}

### Assumptions

{{each reading chosen without the user's answer, ending (relies on I<n>) for the intent line it rests on, or - None}}

## 5. Test seams

{{written by the render script from the record: the agreed seams, then one numbered heading per acceptance criterion, 5.1, 5.2 and so on}}

## 6. Out of scope

{{what is out of scope, including anything the mockup shows that will not be built}}
