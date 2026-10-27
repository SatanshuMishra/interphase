# interphase

interphase turns a request into an approved, testable spec and the Steps that build it, and records how each of its runs went.

## Language

**Run**:
One pass of interphase over one spec, from its guard snapshot to its hand-off; an amendment of a handed-off spec is a run of its own.
_Avoid_: session, job

**Round**:
One numbered set of questions put to the user during the interview, either the intent round or a frontier round.
_Avoid_: batch, turn

**Read-back**:
The short note of what the interview settled that the user approves or changes before interphase writes the spec.
_Avoid_: summary, confirmation

**Hand-off**:
The end of a run: the guard has verified the tree and the record says handed-off.
_Avoid_: delivery, completion

**Metrics store**:
The folder tree, at ~/.plugin-metrics unless PLUGIN_METRICS_DIR names another, where interphase and other plugins keep their events, run summaries and catalogues in one shared format.
_Avoid_: metrics database, telemetry folder

**Event**:
One line interphase appends to the metrics store at a boundary of a run's work, such as a round recorded or the spec rendered.

**Run summary**:
The one line of figures for a run, replaced whole each time it is rebuilt.
_Avoid_: report

**Catalogue**:
Interphase's description of everything it records: its purpose and objectives, and for every event and field what it records, how it is measured, its unit and how to read it.

**Parent run**:
The run of whatever started this run, named as <plugin>/<run id>; a run started on its own has none.
