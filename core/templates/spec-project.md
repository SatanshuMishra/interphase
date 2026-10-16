# {{title}}

Pathway: project.

Date: {{date}}.

## 1. Problem

{{the user's request, word for word}}

{{the problem the project solves, whose problem it is, the product's domain and what is at stake}}

## 2. Intent

{{the intent lines of the decisions file, word for word, each with its id, such as - I1 Goal: <goal>}}

## 3. User stories

{{a long numbered list covering the first usable version, each as: As a <actor>, I want <feature>, so that <benefit>}}

## 4. Decisions

{{numbered decisions: the stage and the definition of done for the first usable version, platforms and minimum versions, the stack with each part's version and the stacks rejected, the repository layout and build tooling, how dependencies are pinned, what CI runs and on which events, packaging, signing and distribution, licence and attribution, where configuration and secrets live, logging and diagnostics, each threat with its defence, and the walking skeleton followed by each later slice in order}}

### Reuse and change

{{Reused as is, Kept separate and Changed, filled as the section Record the result of `${CLAUDE_PLUGIN_ROOT}/core/practices.md` says}}

### Assumptions

{{each reading chosen without the user's answer, ending (relies on I<n>) for the intent line it rests on, or - None}}

## 5. Test seams

{{written by the render script from the record: the agreed seams, then one numbered heading per acceptance criterion, 5.1, 5.2 and so on}}

## 6. Out of scope

{{what could reasonably be in scope but is not, at least one item}}
