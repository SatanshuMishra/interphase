# Glossary and decision records

Every repository interphase works in keeps two lasting records beside its code: a glossary of the project's domain language and a few architecture decision records, ADRs. They outlive every spec. A spec is disposable once its change merges; what must last moves into these two records at hand-off.

## Where they live

- Most repositories have one context: one `GLOSSARY.md` at the repository root and ADRs in `docs/adr/`.
- When a `GLOSSARY-MAP.md` exists at the root, the repository has several contexts. The map lists each context's glossary and how the contexts relate; a context may keep its own `docs/adr/` beside its glossary. Use the context the request touches, and ask which when the request touches more than one and the map does not settle it.
- Create each file and folder lazily, only when there is something to write.

## Reading them

Read the glossary and the ADRs in the area the request touches during grounding. Use the glossary's terms in every question, in the spec and in every Step's task. Respect every ADR in force; a decision that reverses one supersedes it, and the interview asks that reversal like any other decision.

## The glossary

Write a term to the glossary the moment the interview settles it, not in a batch at the end.

```md
# {Context name}

{One or two sentences: what this context is and why it exists.}

## Language

**Order**:
A request from a customer for one or more products.
_Avoid_: Purchase, transaction
```

- Be opinionated. When several words exist for one concept, pick the best and list the others under `_Avoid_`.
- Keep each definition to one or two sentences. Define what the term is, not what it does.
- Include only terms specific to this project's domain. A general programming concept, such as a timeout or an error type, never belongs.
- Group terms under subheadings when natural clusters emerge.
- Keep the glossary free of implementation detail. It is not a spec, a scratch pad or a home for decisions.

## Decision records

Write an ADR only when all three hold:

1. Hard to reverse: changing your mind later costs something real.
2. Surprising without context: a future reader of the code would ask why it was done this way.
3. The result of a real trade-off: there were genuine alternatives and one was picked for specific reasons.

What qualifies: architectural shape, integration patterns between contexts, technology choices that carry lock-in, boundary and scope decisions including the explicit refusals, deliberate departures from the obvious path, constraints the code does not show, and rejected alternatives whose rejection is not obvious.

Number ADRs in sequence, `0001-<slug>.md`, `0002-<slug>.md` and on, one past the highest number in the folder.

```md
# {Short title of the decision}

{One to three sentences: the context, what was decided and why.}
```

Add a `Status:` line (`proposed`, `accepted`, `deprecated` or `superseded by ADR-NNNN`), a Considered options section or a Consequences section only when it adds something a reader needs. Write each ADR so it stands alone: it never cites the spec, which is deleted after merge.

## At hand-off

Promote what must outlast the spec:

- Check that every term the interview settled is in the glossary.
- Write an ADR for each decision in the decisions file that passes all three tests, and mark any ADR it reverses as superseded.
- List each glossary term and ADR you wrote in the hand-off report.
