# Output files and the items format

Use this guide from phase 3 to phase 10. It says which files to write, how to keep the interview record, how to design the Steps, how to shape the items file, and how to check it.

## Output files

Write every file under `docs/specs/` at the user's repository root.

| File | Contents |
|---|---|
| `<slug>.md` | the spec, from the pathway template |
| `<slug>.decisions.md` | `# Decisions for <title>`, one sentence, then `## Intent` with one `- I<n>` line per intent line and `## Decisions` with one `- ` line per settled decision |
| `<slug>.record.json` | the interview record: seams, acceptance criteria and Step designs, kept after hand-off |
| `<slug>.items.json` | the Steps, a JSON array |
| `<slug>.repro.<ext>` | bugs only: the draft failing test, kept as evidence |
| `<slug>.guard.json` | working file for the tree guard, deleted at hand-off |

The glossary and the ADRs live outside the spec folder, as `${CLAUDE_PLUGIN_ROOT}/core/domain.md` says. The spec and the items file are separate deliverables. Each must be usable without the other. The spec is disposable once its change merges; the glossary and the ADRs carry what must last.

## Interview record

Keep the interview in `<slug>.record.json` from phase 1 to phase 10. Write to it the moment something is settled, so that nothing depends on the conversation. It is a JSON object with exactly these three lists, `seams`, `criteria` and `steps`, an optional `rounds` list, a `locked` list once a criterion has acceptance lines, a `probes` list once `surface_probe.py` has run, an `outcomes` object once `outcomes.py` has run, a `stop` object (`phase` and `reason`) with the status `stopped` once a failed probe stops an unattended run, and a `status`:

| Key | Each entry |
|---|---|
| `seams` | `name` (lowercase kebab-case, unique), `interface` (the public interface tests observe behaviour at), `catches` (what tests there catch), `misses` (what they miss), `builder_runs` (`true` when whoever builds a Step can run tests there) |
| `criteria` | `number` (such as `5.3`, starting with the number of the spec's Test seams section), `title`, `text`, `seam` (the name of the agreed seam its tests sit at), `acceptance` (its acceptance lines, each as `${CLAUDE_PLUGIN_ROOT}/contracts/k1-acceptance.schema.json` states it) for every criterion at a seam the builder runs, `tests` (each one row, with `file`, `name`, `given`, `expect`, `step`, `check` (the id of the acceptance line it implements) when the criterion has acceptance lines and, when the criterion has a case table, `covers`), `unproven` (the reason) only when no test the builder runs can prove it, `varies` (`input`, `output` or `measured`) only when the behaviour differs from run to run, and, only for security-sensitive or refusal behaviour, `case_table` (`security` or `refusal`) with `domains` (each with `name`, `over` and `classes`) for the inputs it reads; each test of a varying criterion also carries `cases`, `runs` (at least 2) and `pass_rate` |
| `steps` | `name` (never `check-author`, which the render script reserves), `files`, `criteria` (the numbers its tests prove), `task` once written, `amendment` (the number of the amendment that added it) only when an amendment added it, and any optional field of the items format except `source`, `acceptance`, `spec_ref` and `role` |
| `rounds` | `kind` (`intent` or `frontier`), `questions` (the number of questions the round asked) and `changed` (the answers that differ from the recommended one) |
| `locked` | the repository-relative path of every test file a row of a criterion with acceptance lines names, as `${CLAUDE_PLUGIN_ROOT}/contracts/k2-locked.schema.json` states it; no Step lists a locked path in its `files` |

A record without rounds stays valid, because an unattended run holds no interview and a record from an earlier release has none.

`status` is `in-progress` from phase 1 and `handed-off` once phase 10 finishes. A record without `status` predates the field: the hook treats it as finished, and `check_record.py` reports it.

Give every criterion a test at a seam the builder runs, or an `unproven` reason. For example, a frame-rate target seen only on the user's phone sits at a seam the builder cannot run and is unproven; a colour check the project's tests can run with the phone's renderer is proven by that test. Never mark a criterion unproven to skip a test the builder could run.

In a case table, each domain lists the classes of one input that the code tells apart, and each test covers some of them, named `<domain>: <class>`. The record check reports a class no row covers, domains on a criterion with no `case_table`, and a `case_table` with no domains.

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" docs/specs/<slug>.record.json` after every question round. It confirms that every name resolves, and warns about anything still missing. Add `--complete` once the Steps are designed; anything missing is then an error.

In phase 8, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_record.py" --record docs/specs/<slug>.record.json --spec docs/specs/<slug>.md --items docs/specs/<slug>.items.json`. It writes the spec's Test seams section and the whole items file from the record: every Step's `acceptance`, `spec_ref` and `source`, and its task followed by every criterion it proves, word for word, with the seam it sits at. When the record has a `locked` list, it writes one more Step first: the check-author Step, with name and role `check-author`, which writes the locked tests before anything is built. Its `files` are the locked paths, its `acceptance` is empty, its `spec_ref` names every criterion with acceptance lines, and its task holds each such criterion with every acceptance line and test row. Every other Step comes after it.

## Items format

Write the items file as a JSON array of Step objects. A Step is one unit of build work with its own files and its own test. Use these fields:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | lowercase kebab-case, unique in the file |
| `task` | yes | complete, self-contained instructions; whoever builds the Step receives nothing else about it and never needs the spec |
| `files` | yes | non-empty list of repository-relative paths the Step may create or change, including its own test files, except locked paths, which the check-author Step writes |
| `source` | yes | `{"path": "<absolute path of the spec>", "sha256": "<64 lowercase hex digits>"}`, identical on every Step |
| `acceptance` | yes | list of `{"file": "<test file>", "test": "<test name>"}`; each file is also in `files`, or in the `files` of a check-author Step it comes after; each test fails before the Step and passes after; an empty list is allowed only when every criterion the Step claims is marked unproven, and is required on the check-author Step |
| `after` | no | names of Steps that must be finished first |
| `contract_group` | no | a shared label for Steps that are two halves of one interface |
| `type` | no | only the value `contract`: marks the one Step in a `contract_group` that defines the shared interface; every other Step in that group reaches it through `after` |
| `complexity` | no | `simple` or `complex` |
| `file_notes` | no | object mapping a path from `files` to what changes there |
| `msp` | no | a label that makes Steps ship together as one change |
| `spec_ref` | no, but always set it | list of the numbers of the acceptance criteria the Step's tests prove, such as `"5.3"`; it traces each criterion to a Step and never tells a builder to read the spec |
| `assumptions` | no | readings chosen without the user's answer, each ending `(relies on I<n>)` for the intent line it rests on, the same line as in the spec's Assumptions |
| `role` | no | only the value `check-author`: marks the Step the render script writes to author the locked tests; it comes before every Step without the role, every other Step names it in `after`, and no other Step lists one of its `files` |

Use no other fields. The only value `type` may take is `contract`, and the only value `role` may take is `check-author`. The items file's fields do not change for varying behaviour: its population, runs and pass rate live in the record and in the task text.

## Designing Steps

- Design the Steps during the interview, from the settled decisions and the facts found in the code. Never derive them by reading the finished spec.
- Write each Step to the record as you design it: its name, its files, the criteria its tests prove, and later its task.
- Make one Step one independently testable behaviour with its own files.
- Give a small request one Step per item.
- Give every Step the acceptance criteria its tests prove, and every acceptance criterion at least one Step.
- Ask the user about the shape of the work: what ships together, what order matters and what could be thrown away. Look up the files, tests and export files each Step needs; ask only when the code is silent.
- Keep the Steps' `files` apart wherever you can. Steps that share a file cannot be built at the same time. When two Steps must share a file, order them with `after`.
- Give logic that two Steps need to one Step, and make the others come after it.
- Never keep Steps' files apart by copying logic.
- Give a Step `after` naming every Step whose output it uses. Importing another Step's module does not order the two Steps by itself.
- Give a package's export file, such as `__init__.py`, `index.ts` or `mod.rs`, to a Step that comes after every Step whose modules it exports.
- Give two halves of one interface a shared `contract_group`. To let them be built at the same time, add a Step with `type: contract` that only defines the interface, and make the other halves come after it.
- List in `files` every path the Step creates or changes, including its tests, except a locked path. A write outside `files` is reported as a fault.
- Write each criterion's acceptance lines to the record, and each test row that implements one with its `check`, and add the row's test file to the record's `locked` list.
- Never design the check-author Step and never name a Step `check-author`. The render script writes it first from the record's `locked` list and puts it in every other Step's `after`, so the locked tests ship before anything is built and no later Step changes them.
- Make every acceptance test fail against today's code. Never name a behaviour the code already has.
- Load the code under test inside the test, never at import time, so a missing implementation fails the named test.
- Set `complexity` to `simple` only for mechanical work with no assumptions. Only simple work may go to a cheaper builder.
- During the interview, settle an assumption by asking it when it passes the hard bar. After the interview, fill it from the intent and add it to the Step's `assumptions`.
- Give Steps the user wants shipped together as one change the same `msp`.

## Writing a task

Name the files and the behaviour, in the glossary's terms. The render script adds each acceptance test by file and name with what it is given and what it expects, and every acceptance criterion the Step proves, word for word, after the task you write. Tell the builder to write every row into its test file literally, as the task gives it, and never to compute the rows from the code under test. Restate in the task everything the Step needs from the spec. For a bug, carry the full text of the draft test and the path where it belongs. Never write "see above". Never send the builder to the spec or to anything else outside the task. Carry into the task every Reuse and change line the Step touches: what to reuse as is and never copy, what to keep separate, and which existing code to change. Carry every assumption the Step rests on in its `assumptions`, never only in the task.

## Checking the result

The render script refuses a record that `check_record.py --complete` rejects, and then writes nothing. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" docs/specs/<slug>.items.json`. It checks every field, the spec's SHA-256, and that every acceptance criterion is claimed by a Step. It warns about a Step that claims no criterion, two Steps that share a file with no order between them, and an export file that is not ordered after the Steps whose modules it exports. Fix every error before hand-off. Read every warning and fix the ones that are real.

Check an amendment items file with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" --amendment docs/specs/<slug>.amend-<n>.items.json`; it then does not report the criteria the amendment does not claim.
