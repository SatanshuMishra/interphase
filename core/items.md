# Output files and the items format

Use this guide from phase 3 to phase 10. It says which files to write, how to keep the interview record, how to design the Steps, how to shape the items file, and how to check it.

## Output files

Write every file under `docs/specs/` at the user's repository root.

| File | Contents |
|---|---|
| `<slug>.md` | the spec, from the pathway template |
| `<slug>.decisions.md` | `# Decisions for <title>`, one sentence, then one `- ` line per settled decision |
| `<slug>.record.json` | the interview record: environments, cited facts, acceptance criteria and Step designs, kept after hand-off |
| `<slug>.items.json` | the Steps, a JSON array |
| `<slug>.repro.<ext>` | bugs only: the draft failing test, kept as evidence |
| `<slug>.guard.json` | working file for the tree guard, deleted at hand-off |
| `<slug>.review-copy.md`, `<slug>.review-copy.json` | working copies of the spec and the record as the last review read them, deleted at hand-off |
| `<slug>.review-diff.txt` | working file: the change since the last review, deleted at hand-off |

The spec and the items file are separate deliverables. Each must be usable without the other.

## Interview record

Keep the interview in `<slug>.record.json` from phase 1 to phase 10. Write to it the moment something is found or settled, so that nothing depends on the conversation. It is a JSON object with the four lists `environments`, `facts`, `criteria` and `steps`, a `status`, and from phase 9 the list `reviews`:

| Key | Each entry |
|---|---|
| `environments` | `name` (lowercase kebab-case, unique), `what` (the device, system, runtime or renderer), `builder_runs` (`true` when whoever builds a Step can run tests there) |
| `facts` | `id` (unique), `fact`, and one citation: `path` (repository-relative), `line` (from 1) and `quote` (text that appears in that line); or `url`; or `command` and `output` (what was run and what it showed); a fact about software outside the repository also carries `outside: true` and is cited by `command` and `output`, or, when it cannot be run here, by `assumed` (why it was not run) |
| `criteria` | `number` (such as `7.3`, starting with the number of the spec's Acceptance criteria section), `title`, `text`, `where` (the environments where passing proves it), `tests` (each one row, with `file`, `name`, `given`, `expect`, `env`, `step` and, when the criterion has `domains`, `gives_way` or `keeps`, `covers`), `domains` (each with `name`, `over`, `classes`, `source` (`repo`, `outside`, `person`, `stored` or `sent`), `closed` (`true` or `false`), `fact` (for an outside domain a fact marked outside; for a repo domain a fact cited by path, line and quote or by command and output that shows where the values are defined; for a person domain such a fact that shows where the repository asks for them; for a stored domain such a fact that shows where the repository writes them; for a sent domain such a fact that shows where the repository sends them), `defined_by` (for a repo, person, stored or sent domain whose values a Step of this spec defines, asks for, writes or sends, the name of that Step, which proves the criterion or comes before a Step that does), `open_by` (for a domain the user decided to keep open, the fact that cites that decision's line in a decisions file) and, for an outside, person, stored or sent domain, `invalid` (the classes for input that arrives other than promised)) for the inputs the behaviour reads, `gives_way` (what gives way first to last when a bound is reached), `keeps` (what never gives way when a bound is reached), `facts` (the ids of the facts it rests on), `unproven` (the reason) only when no test the builder runs can prove it where it counts, and `varies` (`input`, `output` or `measured`) only when the behaviour differs from run to run; each test of a varying criterion also carries `cases`, `runs` (at least 2) and `pass_rate` |
| `steps` | `name`, `files`, `criteria` (the numbers its tests prove), `reads` (the names of the domains, from the criteria it proves, of every input its code reads; an empty list when it reads none), `task` once written, `amendment` (the number of the amendment that added it) only when an amendment added it, and any optional field of the items format except `source`, `acceptance` and `spec_ref` |
| `reviews` | `status` (`Approved` or `Issues found`) and `issues` (one object per issue, with `category`, the spec reviewer's category, and `text`), copied unchanged from the `json` block that ends the review, and `reviewed` (what `check_record.py --digest` printed when the review returned, a digest of the record and of the spec beside it), one entry per review in the order the reviews ran, none ever removed |

`status` is `in-progress` from phase 1 and `handed-off` once phase 10 finishes. A record without `status` predates the field: the hook treats it as finished, and `check_record.py` reports it.

The record check refuses a record whose `status` is `handed-off` unless its last review read the record and the spec as they stand, as its `reviewed` digest shows, and no review of the record as it stands reports an issue under Missing input, Missing class, Stand-in, Source, Outside fact, Invalid input, Give-way or Open domain. An issue the record's `open_issues` holds does not count when the last review is a follow-up review that reports it and no fewer issues than the review before it. A brief, whose spec holds the line `Lane: brief.`, with no review hands off only when it holds no domain whose `source` is `outside`, `person`, `stored` or `sent` and no criterion with `gives_way`. `open_issues` holds the issues a review that made no progress left open, each copied unchanged as an object with `category` and `text`, and nothing else; an amendment empties it.

Give every criterion a test the builder runs in one of its `where` environments, or an `unproven` reason. For example, a frame-rate target seen only on the user's phone is unproven when the builder cannot run the phone; a colour check the project's tests can run with the phone's renderer is proven by that test. Never mark a criterion unproven to skip a test the builder could run.

A criterion is a case table. Each domain lists the classes of one input that the code tells apart, drawn from where its values are defined; says with `source` whether the repository defines them, a program, tool, system or service outside the repository produces them, a person enters them, the repository's code reads them back from storage it wrote earlier, or the repository's own code in another process sends them; and says with `closed` whether every value falls in a class. A repo, person, stored or sent domain cites the fact that shows where the repository defines, asks for, writes or sends its values, or names in `defined_by` the Step that will; an outside domain cites a fact marked outside; an outside, person, stored or sent domain lists its `invalid` classes. Each test is one row: `given` says the input, `expect` says the result, and `covers` names what the row covers, as `<domain>: <class>`, `gives-way: <item>` or `keeps: <item>`. The record check reports a class, give-way item or kept item no row covers, a kept item with no row that also covers every give-way item, a criterion that says every, each, any, all, whole, always, never, whatever, however or whenever with no domain, a bound with no `gives_way` or no `keeps`, a domain with no `source` or `closed`, an outside domain with no fact marked outside, an outside, person, stored or sent domain with no `invalid` class, a domain marked `closed: false` with no `open_by` in a criterion with no `varies`, and a Step with no `reads`.

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_record.py" docs/specs/<slug>.record.json` after every question round. It confirms that every quote is in its cited line and every name resolves, and warns about anything still missing. Add `--complete` once the Steps are designed; anything missing is then an error.

In phase 8, run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/render_record.py" --record docs/specs/<slug>.record.json --spec docs/specs/<slug>.md --items docs/specs/<slug>.items.json`. It writes the spec's Acceptance criteria section and the whole items file from the record: every Step's `acceptance`, `spec_ref` and `source`, and its task followed by every criterion it proves, word for word.

## Items format

Write the items file as a JSON array of Step objects. A Step is one unit of build work with its own files and its own test. Use these fields:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | lowercase kebab-case, unique in the file |
| `task` | yes | complete, self-contained instructions; whoever builds the Step receives nothing else about it and never needs the spec |
| `files` | yes | non-empty list of repository-relative paths the Step may create or change, including its test files |
| `source` | yes | `{"path": "<absolute path of the spec>", "sha256": "<64 lowercase hex digits>"}`, identical on every Step |
| `acceptance` | yes | list of `{"file": "<test file>", "test": "<test name>"}`; each file is also in `files`; each test fails before the Step and passes after; an empty list is allowed only when every criterion the Step claims is marked unproven |
| `after` | no | names of Steps that must be finished first |
| `contract_group` | no | a shared label for Steps that are two halves of one interface |
| `type` | no | only the value `contract`: marks the one Step in a `contract_group` that defines the shared interface; every other Step in that group reaches it through `after` |
| `complexity` | no | `simple` or `complex` |
| `file_notes` | no | object mapping a path from `files` to what changes there |
| `msp` | no | a label that makes Steps ship together as one change |
| `spec_ref` | no, but always set it | list of the numbers of the acceptance criteria the Step's tests prove, such as `"7.3"`; it traces each criterion to a Step and never tells a builder to read the spec |
| `assumptions` | no | readings chosen where the spec is silent; aim for none |

Use no other fields. The only value `type` may take is `contract`. The items file's fields do not change for varying behaviour: its population, runs and pass rate live in the record and in the task text.

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
- List in `files` every path the Step creates or changes, including its tests. A write outside `files` is reported as a fault.
- Make every acceptance test fail against today's code. Never name a behaviour the code already has.
- Load the code under test inside the test, never at import time, so a missing implementation fails the named test.
- Set `complexity` to `simple` only for mechanical work with no assumptions. Only simple work may go to a cheaper builder.
- Resolve an assumption by asking, not by writing it down, whenever the user is available.
- Give Steps the user wants shipped together as one change the same `msp`.

## Writing a task

Name the files and the behaviour. The render script adds each acceptance test by file and name with what it is given and what it expects, and every acceptance criterion the Step proves, word for word, after the task you write. Tell the builder to write every row into its test file literally, as the task gives it, and never to compute the rows from the code under test. Restate in the task everything the Step needs from the spec. For a bug, carry the full text of the draft test and the path where it belongs. Never write "see above". Never send the builder to the spec or to anything else outside the task. Carry into the task every Reuse and change line the Step touches: what to reuse as is and never copy, what to keep separate, and which existing code to change.

## Checking the result

The render script refuses a record that `check_record.py --complete` rejects, and then writes nothing. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" docs/specs/<slug>.items.json`. It checks every field, the spec's SHA-256, and that every acceptance criterion is claimed by a Step. It warns about a Step that claims no criterion, two Steps that share a file with no order between them, and an export file that is not ordered after the Steps whose modules it exports. Fix every error before hand-off. Read every warning and fix the ones that are real.

Check an amendment items file with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_items.py" --amendment docs/specs/<slug>.amend-<n>.items.json`; it then does not report the criteria the amendment does not claim.
