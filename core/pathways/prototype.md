# Prototype playbook

Use this playbook when the request starts from a mockup, a clickable prototype or screenshots.

## Ground

Explore the prototype before asking anything.

- Accept the prototype as files, a URL or screenshots. Use a connected design tool only when one is present; never require one.
- Open or run the prototype when it can run, and click through it.
- Inventory every screen, every state shown, every interaction, every piece of data displayed and every component.
- Map every component and data flow in the prototype to existing code that already provides it, following `${CLAUDE_PLUGIN_ROOT}/core/practices.md`.
- The rule: the spec wins over the mockup. The mockup illustrates the idea; it is not the contract.

## Gap analysis

Walk these fifteen areas for every screen. Record what the mockup shows, what it fakes and what it omits.

1. Which screens are final and which are still exploratory.
2. What is deliberate and what is accidental.
3. Screens mapped to the user journeys they serve.
4. Every state: ideal, empty, loading, partial, error.
5. Content variation: long text, missing images, half-filled records.
6. Interactions the mockup does not show.
7. Where each piece of data really comes from, and how that source fails.
8. Input validation and error messages.
9. Login and permissions: deny by default, checked on the server.
10. Saving data, and two people editing at once.
11. UI quality floor: each component's role, surface, states, form factors and input methods. Run the impeccable skill's standard with the key of each platform the product ships (`impeccable standard <apple|android|windows|web>`) and judge every mockup choice against it; where that command is not available, judge against WCAG 2.2 AA.
12. Layout at every screen size the product supports.
13. Analytics events, if any.
14. Performance expectations for slow data.
15. What is out of scope.

## Questions

Draw from this bank. Ask only what passes the hard bar of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md`: what the prototype and the code cannot answer.

- Which parts of the mockup are deliberate and which are placeholders?
- Which screens are final?
- For each screen, what does it show when empty, loading, failed or partly filled?
- What are the input limits and the exact error wording?
- Which layout behaviours are must-haves at each screen size?
- What is the real data source for each piece of data, who may see it, how is it saved, and what happens when saving fails?

## Extra step

Sort every gap before writing the spec: a gap that passes the hard bar of `${CLAUDE_PLUGIN_ROOT}/core/questioning.md` is a frontier question, a fact the code answers is looked up, and a cosmetic gap takes the mockup's choice as an assumption. A mockup choice that breaks the UI standard of item 11, cosmetic or behavioural, and whether or not it was called deliberate, is never kept and never asked: the spec states the corrected behaviour as an assumption. Write each settled area into the spec's Decisions section.

## Acceptance

- Give every screen state a judged acceptance line with a rubric and three trials.

Write one check per screen state. Add a screenshot of the built screen compared with the mockup; it expects the corrected behaviour where the build corrects a standard violation. Number each check under the Test seams section, such as `5.1`, and place it at an agreed seam.

- Follow `${CLAUDE_PLUGIN_ROOT}/core/variation.md` for every behaviour that varies from run to run.

## Steps

Design the Steps during the interview, following the section "Designing Steps" of `${CLAUDE_PLUGIN_ROOT}/core/items.md`. Cut one Step per screen or per data flow. Give a shared interface between screen and server its own `contract` Step.
