# interphase

A Claude Code plugin that turns a rough request into a clear spec.

## What it does

interphase asks questions, challenges assumptions and pushes back on scope until your intent is clear. It does not aim for a perfect spec. It aims for a spec that gets the right thing built. A missed intent means major rework; a small inconsistency can be fixed later.

Each request follows one of three pathways:

- **Feature**: something that does not exist yet. interphase researches the code and the libraries involved, then asks what the feature must do.
- **Bug**: existing behaviour is wrong. interphase reproduces the problem, ranks the likely causes and writes a draft failing test.
- **Prototype**: a mockup or design export to ship as a working product. interphase explores the mockup and finds what it fakes or leaves out.

Every run ends with a spec package in your repository. It holds the spec, the decisions you made, and a list of Steps. A Step is one piece of build work with its own files and its own test.

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

Each command takes the request as its argument. For example: `/interphase:bug The export button downloads an empty file.`

interphase asks its first question in plain text. Later questions come as short multiple-choice sets, with the recommended answer first. Answer "yes" to accept a recommendation.

## What it never does

- It never creates, edits or deletes a tracked file in your repository. The one exception is adding the spec folder to `.gitignore` when you choose that.
- It never commits, pushes, stashes, resets, checks out or rebases.
- It never implements. The spec states the cause, the boundary and the test. It never contains the patch.
- It tests bug causes only in throwaway git worktrees. Each worktree is deleted afterwards. The spec keeps the evidence, never the change.

A guard records the state of your repository at the start of a run. At the end it checks that nothing changed, and it tells you exactly what did if something has.

## What it produces

Every file goes in `docs/specs/` at the root of your repository. `<slug>` is a short lowercase name, taken from your request.

| File | Contents |
|---|---|
| `<slug>.md` | The spec, written from the pathway's template. |
| `<slug>.decisions.md` | A `# Decisions for <title>` heading, one sentence, then one `- ` line for each question you settled. |
| `<slug>.items.json` | The Steps, as a JSON array. |
| `<slug>.repro.<ext>` | Bugs only. The draft failing test, kept as evidence. |
| `<slug>.guard.json` | A working file for the guard. It is deleted when the run ends. |

The items file is a JSON array of Step objects. Each Step has these fields:

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Lowercase kebab-case. Unique in the file. |
| `task` | yes | Complete instructions for the Step. Whoever builds it gets nothing else about it. |
| `files` | yes | A non-empty list of repository-relative paths the Step may create or change. It includes the Step's test files. |
| `source` | yes | `{"path": "<absolute path of the spec>", "sha256": "<64 lowercase hex digits>"}`. It is the same on every Step. |
| `acceptance` | yes | A list of `{"file": "<test file>", "test": "<test name>"}`. Each file is also in `files`. Each test fails before the Step and passes after it. The list may be empty only when nothing can be tested, and the spec says why. |
| `after` | no | Names of Steps that must be finished first. |
| `contract_group` | no | A shared label for Steps that are two halves of one interface. |
| `type` | no | Only the value `contract`. It marks the one Step in a `contract_group` that defines the shared interface. Every other Step in that group reaches it through `after`. |
| `complexity` | no | `simple` or `complex`. |
| `file_notes` | no | An object mapping a path from `files` to what changes there. |
| `msp` | no | A label that makes Steps ship together as one change. |
| `spec_ref` | no, but interphase always sets it | A list of spec section numbers, such as `"7"` or `"9.2"`, or exact section titles. These are the sections the Step builds. |
| `assumptions` | no | Readings chosen where the spec is silent. interphase aims for none. |

No other fields are allowed.

The items file has the same shape as the input mitosis reads with --items.

## Keep specs out of git

Specs are working documents. Keep them out of your repository's history. Add this line to `.gitignore`:

```
docs/specs/
```

If the folder is not ignored, interphase asks you where to ignore it. You can add it to `.gitignore`, which applies to everyone. Or you can add it to `.git/info/exclude`, which applies only to your machine. interphase does exactly what you choose.

If the directory is not a git repository, interphase skips this check and the guard, and tells you so.

## Check the output yourself

Check a spec against its template:

```
python3 /path/to/interphase/scripts/check_spec.py --template /path/to/interphase/core/templates/spec-feature.md docs/specs/<slug>.md
```

Use `spec-bug.md` or `spec-prototype.md` as the template for the other pathways. The checker reports missing or reordered sections, empty sections, leftover placeholders and vague words.

Check an items file:

```
python3 /path/to/interphase/scripts/check_items.py docs/specs/<slug>.items.json
```

This checker validates every field above. It also confirms that the spec's SHA-256 matches the one recorded in `source`.

Run both commands from the root of the repository that holds `docs/specs/`. Replace `/path/to/interphase` with the folder the plugin is installed in; a marketplace install puts it under `~/.claude/plugins/cache/interphase/interphase/<version>/`. Each prints one `error:` or `warning:` line per finding. The exit code is `0` when there are no errors, `1` when there are errors, and `2` for a usage error or a file it cannot read.

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
