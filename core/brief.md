# Brief lane

A small request can take the brief lane: a short brief in place of a full spec. Any pathway can take it.

## When

A small request takes the brief lane only when all six hold after grounding:

1. Each item is one behaviour in one sentence that the user asked for or that was already observed, such as a reproduced defect or a live-check finding.
2. The change follows patterns the code already has, with no new module, dependency, interface between parts, stored-data or sync format, build or release change.
3. There is no design choice between real alternatives and no reuse fork as `${CLAUDE_PLUGIN_ROOT}/core/practices.md` defines one.
4. Every acceptance test sits at a seam the builder runs, so nothing is marked unproven.
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
- Keep the record and the decisions. Criteria keep their numbers: every template numbers them 5.x.
- Continue with the full phases and the pathway's own template. An attended run goes on with the frontier rounds of the interview; an unattended run stays unattended.

## What changes

In the brief lane, only these phases change. Every other phase and rule applies unchanged.

- Phase 4: ask the intent round, and a frontier round only for a question that passes the hard bar. Agree the one seam the project already tests the change at.
- Phase 5: skip the pre-mortem. The Unchanged statements are the Out of scope section.
- Phase 6: design one Step per item, and run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/surface_probe.py" --record docs/specs/<slug>.record.json --repo .`, with `--unattended` in an unattended run, before the complete check.
- Phase 7: read back only the intent, each item's Current, Expected and Unchanged statements, the Steps and the output of `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/read_back.py" --record docs/specs/<slug>.record.json` word for word, with each failed probe it lists as a question, and ask for the one approval.
- Phase 8: copy `${CLAUDE_PLUGIN_ROOT}/core/templates/spec-brief.md` instead of the pathway template.
- Phase 9: run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_spec.py" --template "${CLAUDE_PLUGIN_ROOT}/core/templates/spec-brief.md" docs/specs/<slug>.md`, `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" --complete docs/specs/<slug>.record.json` and `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" docs/specs/<slug>.items.json`. Do not dispatch the `interphase:spec-reviewer` agent.

An unattended run in the brief lane asks no intent round and holds no read-back, as every unattended run does.
