# {{title}}

Pathway: feature.

Date: {{date}}.

## 1. Problem

{{the user's request, word for word}}

{{the problem the user faces, from their perspective: whose problem it is and why it matters now}}

## 2. Intent

{{the intent lines of the decisions file, word for word, each with its id, such as - I1 Goal: <goal>}}

## 3. User stories

{{a long numbered list covering every aspect of the feature, each as: As a <actor>, I want <feature>, so that <benefit>}}

## 4. Decisions

{{numbered implementation decisions: the modules built or changed and their interfaces, the approach chosen and the alternatives rejected, schema and interface contracts, and each threat the change must withstand with its defence; no file paths or code}}

### Reuse and change

{{Reused as is, Kept separate and Changed, filled as the section Record the result of `${CLAUDE_PLUGIN_ROOT}/core/practices.md` says}}

### Assumptions

{{each reading chosen without the user's answer, ending (relies on I<n>) for the intent line it rests on, or - None}}

## 5. Test seams

{{written by the render script from the record: the agreed seams, then one numbered heading per acceptance criterion, 5.1, 5.2 and so on}}

## 6. Out of scope

{{what could reasonably be in scope but is not, at least one item}}
