# Prototype playbook

Use this playbook when the request starts from a mockup, a clickable prototype or screenshots.

## Ground

Explore the prototype before asking anything.

- Accept the prototype as files, a URL or screenshots. Use a connected design tool only when one is present; never require one.
- Open or run the prototype when it can run, and click through it.
- Inventory every screen, every state shown, every interaction, every piece of data displayed and every component.
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
11. Accessibility floor: keyboard use, visible focus, contrast, touch targets at least 24 by 24 pixels.
12. Layout at every screen size the product supports.
13. Analytics events, if any.
14. Performance expectations for slow data.
15. What is out of scope.

## Questions

Draw from this bank. Ask only what the prototype and the code cannot answer.

- Which parts of the mockup are deliberate and which are placeholders?
- Which screens are final?
- For each screen, what does it show when empty, loading, failed or partly filled?
- What are the input limits and the exact error wording?
- Which layout behaviours are must-haves at each screen size?
- Which accessibility level is the target?
- What is the real data source for each piece of data, who may see it, how is it saved, and what happens when saving fails?

## Extra step

Sort every gap into one of three kinds before writing the spec:

- Intent: only the user knows. Ask.
- Structure: the code or documentation knows. Look it up.
- Cosmetic: default to the mockup and record the assumption.

## Acceptance

Write one check per screen state. Add a screenshot of the built screen compared with the mockup.

## Steps

Cut one Step per screen or per data flow. Give a shared interface between screen and server its own `contract` Step.
