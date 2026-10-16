# interphase

A Claude Code plugin that turns a rough request into a clear spec.

## What it does

interphase grills you about a request until you and it share one understanding of what gets built. It opens with your intent (the goal, why you want it, and what success looks like), then asks every open decision in numbered rounds, each with a recommended answer. It asks only what the code, the docs and your earlier decisions cannot answer, and only when a different answer would change what gets built. Once you approve its read-back, it writes the spec and the Steps on its own and asks nothing more: any gap it finds later is filled with a reasoned guess from your recorded intent, listed as an assumption.

It does not aim for a perfect spec. It aims for a spec that gets the right thing built. A missed intent means major rework; a small inconsistency can be fixed later.

Each request follows one of four pathways:

- **Feature**: something that does not exist yet. interphase researches the code and the libraries involved, then asks what the feature must do.
- **Bug**: existing behaviour is wrong. interphase reproduces the problem, ranks the likely causes and writes a draft failing test.
- **Prototype**: a mockup or design export to ship as a working product. interphase explores the mockup and finds what it fakes or leaves out.
- **Project**: a new repository, or a new stack, build, CI or release for an existing one. interphase settles the stage, platforms, stack, test strategy, CI, release, licence and logging, and the first Step is a walking skeleton that runs end to end.

Every spec has the same six sections: the problem, your intent, user stories (for a bug, the reproduction and cause; for a brief, the evidence), the decisions, the agreed test seams with the acceptance tests at each, and what is out of scope. A test seam is the public interface a test observes behaviour at; interphase agrees the seams with you and aims for one. Only behaviour that is security-sensitive or exists to refuse something gets a full table of input cases.

Every spec follows five programming rules, kept in `core/practices.md`. interphase reuses code that already does the job, asks you only when sharing code and keeping it apart are both real options, and writes a short Reuse and change list (what it reuses as is, what it keeps separate, and what existing code it changes).

interphase keeps your project's domain language in a `GLOSSARY.md` at the repository root and records the few decisions that are hard to reverse, surprising and the result of a real trade-off as decision records in `docs/adr/`. It creates both only when it has something to write. A spec is disposable once its change merges; at hand-off, what must last moves into the glossary and the decision records.

interphase notices behaviour that varies from run to run without being told. That covers open-ended input such as speech or free text, model output, and results measured on a device. It specifies that behaviour as a population: the ways its input varies, a held-out set it drafts for you to approve, outcome grading, repeated runs and a pass rate.

For a small change, interphase writes a short brief instead of a full spec. It takes the brief lane only when all six conditions hold after it reads the code: each item is one behaviour in one sentence that you asked for or that was already observed; the change follows patterns the code already has, with no new module, dependency, interface, stored-data format or build change; there is no design choice between real alternatives and no reuse fork; every acceptance test sits at a seam the builder runs, so nothing is marked unproven; nothing it touches varies from run to run; and, for a bug, the cause is confirmed by reproduction. It says the lane in one sentence, which you may override, and switches to the full pathway if one condition breaks. A brief has one Step per item, one short read-back to approve and no reviewer agent.

Every run ends with a spec package in your repository. It holds the spec, the decisions you made, and a list of Steps. A Step is one piece of build work with its own files and its own test. interphase designs the Steps with you during the interview; it never cuts them out of the finished spec. The spec and the Steps are separate deliverables, and each can be used without the other.

## Install

Add the marketplace:

```
claude plugin marketplace add SatanshuMishra/interphase
```

Install the plugin:

```
claude plugin install interphase@interphase
```

Then restart Claude Code.

## Use

You do not have to type a command. Describe what you want, and Claude starts the matching pathway on its own.

You can also start a pathway yourself:

| Command | When to use it |
|---|---|
| `/interphase` | You are not sure which pathway fits. interphase picks one and tells you, and you can override it. |
| `/interphase:feature` | You want something that does not exist yet. |
| `/interphase:bug` | Something works wrongly and you want the cause found first. |
| `/interphase:prototype` | You have a mockup or design and want it built for real. |
| `/interphase:project` | You are starting a project, or replacing one's stack, build, CI or release. |

Each command takes the request as its argument. For example: `/interphase:bug The export button downloads an empty file.`

interphase asks in numbered plain-text rounds: the intent round first, then every question whose earlier answers are settled. Each question carries a recommended answer, worded so that "yes" accepts it. Answer "yes" to a whole round, or answer by number. There is no cap on the number of questions. The only multiple-choice prompt is the last one: approve the read-back or change something.

If the conversation is compacted or cleared during a run, a hook puts the run's decisions and a summary of its record back into the conversation, and each pathway tells Claude to re-read the record, the decisions and the phases before going on. The hook says nothing when no run is in progress.

When you tell interphase to work autonomously, it holds no interview. It infers the intent from your request and your project's context, marks it as inferred, and resolves each ambiguity from that intent and the usual practice for that context. It records every choice as an assumption that names the intent line it relied on. It never trims what the context calls for: whatever your project lacks today, such as a library, a stored field or a deployment setting, becomes part of the spec instead of a reason to leave the requirement out. At hand-off it lists its own decisions as top risks, first any that override an earlier decision, a decision record or one of your project's written rules or conventions, then the rest.

## What it never does

- It never creates, edits or deletes a file in your repository other than its own output files in `docs/specs/`, the glossary and the decision records in `docs/adr/`. Running your tests can leave caches such as `__pycache__`; interphase removes the ones its run created before it finishes, and never touches caches that were already there.
- It never comments on, asks about or offers to change whether you track its output files in git.
- It never commits, pushes, stashes, resets, checks out or rebases.
- It never implements. The spec states the cause, the boundary and the test. It never contains the patch.
- It never plans a copy of logic that already exists, and never bends existing code to fit a new use.
- It tests bug causes only in throwaway git worktrees. Each worktree is deleted afterwards. The spec keeps the evidence, never the change.

A guard records the state of your repository at the start of a run. At the end it checks that nothing changed, and it tells you exactly what did if something has. It ignores interphase's own output files, the glossary and the decision records, whether you track them in git or not. Before it checks, it removes the caches that running your code created during the run. If the directory is not a git repository, interphase skips the guard and tells you so.

## What it produces

Every file goes in `docs/specs/` at the root of your repository. `<slug>` is a short lowercase name, taken from your request.

A brief is written from `core/templates/spec-brief.md`. Every spec numbers its acceptance criteria 5.x, under the Test seams section.

| File | Contents |
|---|---|
| `<slug>.md` | The spec, written from the pathway's template. |
| `<slug>.decisions.md` | A `# Decisions for <title>` heading, one sentence, an Intent section with one numbered line (`I1`, `I2` and on) for each part of your intent, and a Decisions section with one `- ` line for each question you settled. |
| `<slug>.items.json` | The Steps, as a JSON array. |
| `<slug>.record.json` | The interview record: the agreed test seams, the acceptance criteria and the Steps. interphase keeps it after the run. |
| `<slug>.repro.<ext>` | Bugs only. The draft failing test, kept as evidence. |
| `<slug>.guard.json` | A working file for the guard. It is deleted when the run ends. |

The items file is a JSON array of Step objects. Each Step has these fields:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Lowercase kebab-case. Unique in the file. |
| `task` | yes | Complete instructions for the Step. Whoever builds it gets nothing else about it and never needs the spec. |
| `files` | yes | A non-empty list of repository-relative paths the Step may create or change. It includes the Step's test files. |
| `source` | yes | `{"path": "<absolute path of the spec>", "sha256": "<64 lowercase hex digits>"}`. It is the same on every Step. |
| `acceptance` | yes | A list of `{"file": "<test file>", "test": "<test name>"}`. Each file is also in `files`. Each test fails before the Step and passes after it. The list may be empty only when every criterion the Step claims is marked unproven. |
| `after` | no | Names of Steps that must be finished first. |
| `contract_group` | no | A shared label for Steps that are two halves of one interface. |
| `type` | no | Only the value `contract`. It marks the one Step in a `contract_group` that defines the shared interface. Every other Step in that group reaches it through `after`. |
| `complexity` | no | `simple` or `complex`. |
| `file_notes` | no | An object mapping a path from `files` to what changes there. |
| `msp` | no | A label that makes Steps ship together as one change. |
| `spec_ref` | no, but interphase always sets it | A list of the numbers of the acceptance criteria the Step's tests prove, such as `"5.3"`. It traces each criterion to a Step. |
| `assumptions` | no | Readings chosen without your answer, each naming the intent line it relies on, such as `(relies on I1)`. Each shows in the pull request that builds the Step. |

No other fields are allowed.

The items file has the same shape as the input mitosis reads with --items.

## Check the output yourself

Check a spec against its template:

```
python3 /path/to/interphase/scripts/check_spec.py --template /path/to/interphase/core/templates/spec-feature.md docs/specs/<slug>.md
```

Use `spec-bug.md`, `spec-prototype.md` or `spec-project.md` as the template for the other pathways. The checker reports missing or reordered sections, empty sections, leftover placeholders, vague words, a Test seams section with no numbered criterion heading such as `### 5.1`, an Intent section with no `- I1` line, and an assumption that cites no intent line or one the Intent section does not have.

Check an items file:

```
python3 /path/to/interphase/scripts/check_items.py docs/specs/<slug>.items.json
```

This checker validates every field above. It also confirms that the spec's SHA-256 matches the one recorded in `source`, and that every numbered acceptance criterion is claimed by a Step's `spec_ref`. It warns about a Step that claims no criterion, two Steps that share a file with no order between them, and a package export file that is not ordered after the Steps whose modules it exports.

Check an interview record:

```
python3 /path/to/interphase/scripts/check_record.py [--complete] docs/specs/<slug>.record.json
```

This checker confirms that every name in the record resolves, that every criterion sits at an agreed seam, and that every acceptance criterion has a test at a seam the builder runs, or is marked unproven. Without `--complete`, anything still missing is a warning; with it, an error.

A criterion marked `varies` (input, output or measured) must give each of its tests `cases`, `runs` (at least 2) and `pass_rate`. The render script writes them into the row's Runs cell.

A criterion for security-sensitive behaviour, or for behaviour that exists to refuse something, is a case table: its `case_table` is `security` or `refusal`, its `domains` list the classes of each input the code tells apart, and each of its tests is one row with `given`, `expect` and the classes it `covers`. Any other criterion is a few rows with no domains. The checker reports a class no row covers, domains on a criterion with no `case_table`, and a `case_table` with no domains.

Render the spec's Test seams section and the items file from a record:

```
python3 /path/to/interphase/scripts/render_record.py --record docs/specs/<slug>.record.json --spec docs/specs/<slug>.md --items docs/specs/<slug>.items.json
```

It refuses a record that the checker rejects with `--complete`, and a Step assumption that cites no intent line of the spec, and then writes nothing.

To amend a handed-off spec, ask interphase to add the missed case to it by name. It adds rows and a new Step with `amendment` set, and renders that Step alone with `--amendment <n> --items docs/specs/<slug>.amend-<n>.items.json`. Check that file with `check_items.py --amendment`.

Run every command in this section from the root of the repository that holds `docs/specs/`. Replace `/path/to/interphase` with the folder the plugin is installed in; a marketplace install puts it under `~/.claude/plugins/cache/interphase/interphase/<version>/`. Each checker prints one `error:` or `warning:` line per finding. The exit code is `0` when there are no errors, `1` when there are errors, and `2` for a usage error or a file it cannot read.

## Requirements

- Python 3.9 or later.
- git.

## Tests and evals

Run the tests from the plugin's folder:

```
python3 -m unittest discover tests
```

Run the evals, which check that each pathway starts from the right kind of request:

```
claude plugin eval .
```

## License

Apache-2.0.
