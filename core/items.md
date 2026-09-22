# Output files and the items format

Use this guide in phases 7, 9 and 10. It says which files to write, how to shape the items file, and how to check it.

## Output files

Write every file under `docs/specs/` at the user's repository root. Keep all of them gitignored.

| File | Contents |
|---|---|
| `<slug>.md` | the spec, from the pathway template |
| `<slug>.decisions.md` | `# Decisions for <title>`, one sentence, then one `- ` line per settled decision |
| `<slug>.items.json` | the Steps, a JSON array |
| `<slug>.repro.<ext>` | bugs only: the draft failing test, kept as evidence |
| `<slug>.guard.json` | working file for the tree guard, deleted at hand-off |

## Items format

Write the items file as a JSON array of Step objects. A Step is one unit of build work with its own files and its own test. Use these fields:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | lowercase kebab-case, unique in the file |
| `task` | yes | complete, self-contained instructions; whoever builds the Step receives nothing else about it |
| `files` | yes | non-empty list of repository-relative paths the Step may create or change, including its test files |
| `source` | yes | `{"path": "<absolute path of the spec>", "sha256": "<64 lowercase hex digits>"}`, identical on every Step |
| `acceptance` | yes | list of `{"file": "<test file>", "test": "<test name>"}`; each file is also in `files`; each test fails before the Step and passes after; an empty list is allowed only when nothing can be tested, and the spec says why |
| `after` | no | names of Steps that must be finished first |
| `contract_group` | no | a shared label for Steps that are two halves of one interface |
| `type` | no | only the value `contract`: marks the one Step in a `contract_group` that defines the shared interface; every other Step in that group reaches it through `after` |
| `complexity` | no | `simple` or `complex` |
| `file_notes` | no | object mapping a path from `files` to what changes there |
| `msp` | no | a label that makes Steps ship together as one change |
| `spec_ref` | no, but always set it | list of spec section numbers such as `"7"` or `"9.2"`, or exact section titles, that the Step implements |
| `assumptions` | no | readings chosen where the spec is silent; aim for none |

Use no other fields. The only value `type` may take is `contract`.

## Cutting Steps

- Make one Step one independently testable behaviour with its own files.
- Prefer Steps whose `files` do not overlap. Steps that share a file are built one after another.
- Give a package's export file, such as `__init__.py`, `index.ts` or `mod.rs`, to a Step that comes after every Step whose modules it exports.
- Give two halves of one interface a shared `contract_group`. To let them be built at the same time, add a Step with `type: contract` that only defines the interface, and make the other halves come after it.
- Make every acceptance test fail against today's code. Never name a behaviour the code already has.
- Load the code under test inside the test, never at import time, so a missing implementation fails the named test.
- Set `complexity` to `simple` only for mechanical work with no assumptions.
- Keep each Step's change reviewable: about 400 changed lines at most.
- Resolve an assumption by asking, not by writing it down, whenever the user is available.
- List the same Steps in plain language in the spec's Work breakdown section.

## Writing a task

Name the files, the behaviour, each acceptance test by file and name with what it asserts, and the spec sections the Step implements. For a bug, carry the full text of the draft test and the path where it belongs. Never write "see above". Never depend on anything outside the task itself and the spec.

## Checking the result

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" docs/specs/<slug>.items.json` and fix every error before hand-off.
