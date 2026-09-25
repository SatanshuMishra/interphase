# Output files and the items format

Use this guide from phase 3 to phase 10. It says which files to write, how to design the Steps, how to shape the items file, and how to check it.

## Output files

Write every file under `docs/specs/` at the user's repository root.

| File | Contents |
|---|---|
| `<slug>.md` | the spec, from the pathway template |
| `<slug>.decisions.md` | `# Decisions for <title>`, one sentence, then one `- ` line per settled decision |
| `<slug>.items.json` | the Steps, a JSON array |
| `<slug>.repro.<ext>` | bugs only: the draft failing test, kept as evidence |
| `<slug>.guard.json` | working file for the tree guard, deleted at hand-off |

The spec and the items file are separate deliverables. Each must be usable without the other.

## Items format

Write the items file as a JSON array of Step objects. A Step is one unit of build work with its own files and its own test. Use these fields:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | lowercase kebab-case, unique in the file |
| `task` | yes | complete, self-contained instructions; whoever builds the Step receives nothing else about it and never needs the spec |
| `files` | yes | non-empty list of repository-relative paths the Step may create or change, including its test files |
| `source` | yes | `{"path": "<absolute path of the spec>", "sha256": "<64 lowercase hex digits>"}`, identical on every Step |
| `acceptance` | yes | list of `{"file": "<test file>", "test": "<test name>"}`; each file is also in `files`; each test fails before the Step and passes after; an empty list is allowed only when nothing can be tested, and the spec says why |
| `after` | no | names of Steps that must be finished first |
| `contract_group` | no | a shared label for Steps that are two halves of one interface |
| `type` | no | only the value `contract`: marks the one Step in a `contract_group` that defines the shared interface; every other Step in that group reaches it through `after` |
| `complexity` | no | `simple` or `complex` |
| `file_notes` | no | object mapping a path from `files` to what changes there |
| `msp` | no | a label that makes Steps ship together as one change |
| `spec_ref` | no, but always set it | list of the numbers of the acceptance criteria the Step's tests prove, such as `"7.3"`; it traces each criterion to a Step and never tells a builder to read the spec |
| `assumptions` | no | readings chosen where the spec is silent; aim for none |

Use no other fields. The only value `type` may take is `contract`.

## Designing Steps

- Design the Steps during the interview, from the settled decisions and the facts found in the code. Never derive them by reading the finished spec.
- Make one Step one independently testable behaviour with its own files.
- Give a small request one Step.
- Give every Step the acceptance criteria its tests prove, and every acceptance criterion at least one Step.
- Ask the user about the shape of the work: what ships together, what order matters and what could be thrown away. Look up the files, tests and export files each Step needs; ask only when the code is silent.
- Keep the Steps' `files` apart wherever you can. Steps that share a file cannot be built at the same time. When two Steps must share a file, order them with `after`.
- Give a Step `after` naming every Step whose output it uses. Importing another Step's module does not order the two Steps by itself.
- Give a package's export file, such as `__init__.py`, `index.ts` or `mod.rs`, to a Step that comes after every Step whose modules it exports.
- Give two halves of one interface a shared `contract_group`. To let them be built at the same time, add a Step with `type: contract` that only defines the interface, and make the other halves come after it.
- List in `files` every path the Step creates or changes, including its tests. A write outside `files` is reported as a fault.
- Make every acceptance test fail against today's code. Never name a behaviour the code already has.
- Load the code under test inside the test, never at import time, so a missing implementation fails the named test.
- Set `complexity` to `simple` only for mechanical work with no assumptions. Only simple work may go to a cheaper builder.
- Resolve an assumption by asking, not by writing it down, whenever the user is available.
- Give Steps the user wants shipped together as one change the same `msp`.

## Writing a task

Name the files, the behaviour, each acceptance test by file and name with what it asserts, and the acceptance criteria the Step proves. Restate in the task everything the Step needs from the spec. For a bug, carry the full text of the draft test and the path where it belongs. Never write "see above". Never send the builder to the spec or to anything else outside the task.

## Checking the result

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" docs/specs/<slug>.items.json`. It checks every field, the spec's SHA-256, and that every acceptance criterion is claimed by a Step. It warns about a Step that claims no criterion, two Steps that share a file with no order between them, and an export file that is not ordered after the Steps whose modules it exports. Fix every error before hand-off. Read every warning and fix the ones that are real.
