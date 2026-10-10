# Brief lane

A small request can take the brief lane: a short brief in place of a full spec. Any pathway can take it.

## When

A small request takes the brief lane only when all six hold after grounding:

1. Each item is one behaviour in one sentence that the user asked for or that was already observed, such as a reproduced defect or a live-check finding.
2. The change follows patterns the code already has, with no new module, dependency, interface between parts, stored-data or sync format, build or release change.
3. There is no design choice between real alternatives and no reuse fork as `${CLAUDE_PLUGIN_ROOT}/core/practices.md` defines one.
4. Every acceptance test runs where the builder runs, so nothing is marked unproven.
5. Nothing it touches varies from run to run as `${CLAUDE_PLUGIN_ROOT}/core/variation.md` defines.
6. For a bug, the cause is confirmed by reproduction.

Every item must meet all six. When one item fails a condition, the whole request takes the full pathway.

## Choose and record

- Check the six conditions at the end of Phase 3.
- Say the lane in one sentence, which the user may override. For example: "This change meets the six conditions, so I'll write a brief."
- Write `- Lane: brief.` to the decisions file.

## Switch

When any condition breaks later, switch to the full pathway.

- Say so in one sentence that names the condition that broke.
- Write `- Lane: full, replacing the brief lane.` to the decisions file.
- Keep the record and the decisions.
- Renumber each criterion in the record, and in its Steps, to the Acceptance criteria section of the pathway's own template.
- Continue with the full phases and the pathway's own template.

## What changes

In the brief lane, only these phases change. Every other phase and rule applies unchanged.

- Phase 5: skip the pre-mortem. The Unchanged statements are the non-goals.
- Phase 6: design one Step per item.
- Phase 7: skip the read-back.
- Phase 8: copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-brief.md` instead of the pathway template.
- Phase 9: run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_spec.py" --template "${CLAUDE_PLUGIN_ROOT}/core/templates/spec-brief.md" docs/specs/<slug>.md`, `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" --complete docs/specs/<slug>.record.json` and `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" docs/specs/<slug>.items.json`. Do not dispatch the `interphase:spec-reviewer` agent. Ask for one approval of the written brief and its Steps.

## Numbering

Number every criterion in a brief 4.1, 4.2 and so on, whatever number the pathway playbook gives. The bug playbook's draft failing test, criterion 10.1, becomes 4.1. A prototype's 16.x checks become 4.x.
