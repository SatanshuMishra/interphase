import datetime
import functools
import importlib.util
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys

PLUGIN = "interphase"
SCRIPTS = pathlib.Path(__file__).resolve().parent
PLUGIN_FOLDER = SCRIPTS.parent
SCRIPT_NAMES = ("tree_guard.py", "check_record.py", "render_record.py", "check_spec.py", "check_items.py")
OWN_SCRIPTS = {os.path.realpath(str(SCRIPTS / name)): name for name in SCRIPT_NAMES}
PUNCTUATION = ";&|()<>\n"
SEPARATOR_CHARACTERS = frozenset(";&|()\n")
ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", re.DOTALL)
VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
RUN_FILE = re.compile(r"(.+)\.([0-9]{8}T[0-9]{6}Z)\.jsonl")
EXIT_LINE = re.compile(r"Exit code (-?[0-9]+)")
SPEC_FOLDER = ("docs", "specs")
REVIEWER = "interphase:spec-reviewer"
AGENT_TOOLS = ("Agent", "Task")
APPROVED = "Status: Approved"
ISSUES_FOUND = "Status: Issues found"
STATUS = "Status:"
ISSUE = "- "
HANDED_OFF = "handed-off"
HANDOFF = "run.handoff"


def load_writer():
    spec = importlib.util.spec_from_file_location("metrics_writer", SCRIPTS / "metrics_writer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def git_root(cwd):
    if not isinstance(cwd, str) or not cwd:
        return None
    start = pathlib.Path(cwd).resolve()
    return next((folder for folder in (start,) + tuple(start.parents) if (folder / ".git").exists()), None)


def tokens(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=PUNCTUATION)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    return tuple(lexer)


def is_separator(token):
    return token != "" and frozenset(token) <= SEPARATOR_CHARACTERS


def split_commands(words):
    def add(commands, word):
        if is_separator(word):
            return commands + ((),)
        return commands[:-1] + (commands[-1] + (word,),)

    return tuple(command for command in functools.reduce(add, words, ((),)) if command)


def expand(token, variables):
    names = tuple(first or second for first, second in VARIABLE.findall(token))
    values = {name: variables[name] if name in variables else os.environ.get(name) for name in names}
    if any(value is None for value in values.values()):
        return None
    return VARIABLE.sub(lambda found: values[found.group(1) or found.group(2)], token)


def resolved(token, folder):
    return os.path.realpath(os.path.join(folder, os.path.expanduser(token)))


def script_name(token, variables, folder):
    if not any(name in token for name in SCRIPT_NAMES) and "$" not in token:
        return None
    expanded = expand(token, variables)
    return None if expanded is None else OWN_SCRIPTS.get(resolved(expanded, folder))


def leading_assignments(words):
    count = next((index for index, word in enumerate(words) if not ASSIGNMENT.fullmatch(word)), len(words))
    return words[:count]


def assign(variables, word):
    name, value = ASSIGNMENT.fullmatch(word).groups()
    return dict(variables, **{name: expand(value, variables)})


def walk(state, indexed):
    variables, folder, found = state
    index, command = indexed
    words = command[1:] if command[0] == "export" else command
    assignments = leading_assignments(words)
    known = functools.reduce(assign, assignments, variables)
    rest = words[len(assignments):]
    if rest[:1] == ("cd",) and len(rest) > 1:
        target = expand(rest[1], known)
        return known, folder if target is None else resolved(target, folder), found
    scripts = tuple(
        (name, tuple(expand(word, known) for word in rest[position + 1:]), index, folder)
        for position, name in ((position, script_name(word, known, folder)) for position, word in enumerate(rest))
        if name is not None
    )
    return known, folder, found + scripts


def recognised(command, cwd):
    commands = split_commands(tokens(command))
    _, _, found = functools.reduce(walk, enumerate(commands), ({}, cwd, ()))
    return found, len(commands)


def option_value(arguments, option):
    pairs = tuple(zip(arguments, arguments[1:]))
    inline = tuple(argument[len(option) + 1:] for argument in arguments if argument and argument.startswith(option + "="))
    return next((value for flag, value in pairs if flag == option), next(iter(inline), None))


def positional(arguments, flags, valued):
    skipped = frozenset(index + 1 for index, argument in enumerate(arguments) if argument in valued)
    return tuple(
        argument
        for index, argument in enumerate(arguments)
        if index not in skipped and argument is not None and argument not in flags and argument not in valued
    )


def spec_path(name, arguments):
    if name == "tree_guard.py":
        return option_value(arguments, "--out") or option_value(arguments, "--snapshot")
    if name == "render_record.py":
        return option_value(arguments, "--record")
    if name == "check_spec.py":
        return next(iter(positional(arguments, (), ("--template",))), None)
    flags = ("--complete",) if name == "check_record.py" else ("--amendment",)
    return next(iter(positional(arguments, flags, ())), None)


def slug_of(path):
    if not path:
        return None
    parts = pathlib.PurePosixPath(path)
    if parts.parent.parts[-2:] != SPEC_FOLDER:
        return None
    slug = parts.name.split(".", 1)[0]
    return slug if slug and "." in parts.name else None


def subcommand(arguments):
    return next((argument for argument in arguments if argument in ("snapshot", "verify")), None)


def output_text(payload):
    if payload.get("hook_event_name") == "PostToolUseFailure":
        error = payload.get("error")
        return "\n".join(error.splitlines()[1:]) if isinstance(error, str) else ""
    response = payload.get("tool_response")
    if isinstance(response, dict):
        return "\n".join(part for part in (response.get("stdout"), response.get("stderr")) if isinstance(part, str))
    return response if isinstance(response, str) else ""


def counted(text, prefix):
    return sum(1 for line in text.splitlines() if line.startswith(prefix))


def exit_code(payload):
    if payload.get("is_interrupt") is True:
        return None
    if payload.get("hook_event_name") == "PostToolUse":
        return 0
    error = payload.get("error")
    first = error.splitlines()[0] if isinstance(error, str) and error.splitlines() else ""
    found = EXIT_LINE.match(first)
    return int(found.group(1)) if found else None


def clean_of(code, errors):
    if code is None and errors is None:
        return None
    return not ((code is not None and code != 0) or (errors is not None and errors > 0))


def list_length(record, key):
    value = record.get(key) if isinstance(record, dict) else None
    return len(value) if isinstance(value, list) else None


def round_counts(path):
    record = read_json(path) if path else None
    return {key: list_length(record, key) for key in ("seams", "criteria", "steps", "rounds")}


def amendment_number(arguments):
    value = option_value(arguments, "--amendment")
    return int(value) if value is not None and re.fullmatch(r"[0-9]+", value) else None


def script_event(name, arguments, folder, outcome):
    code, errors, warnings = outcome
    checked = {"exit": code, "errors": errors, "warnings": warnings}
    if name == "check_record.py" and "--complete" in arguments:
        return "steps.checked", checked
    if name == "check_record.py":
        path = spec_path(name, arguments)
        return "round.recorded", dict(checked, **round_counts(resolved(path, folder) if path else None))
    if name == "render_record.py":
        return "spec.rendered", {"exit": code, "amendment": amendment_number(arguments)}
    if name == "check_spec.py":
        return "spec.checked", checked
    if name == "check_items.py":
        return "items.checked", dict(checked, amendment="--amendment" in arguments)
    if subcommand(arguments) == "verify":
        return HANDOFF, {"exit": code, "errors": errors, "clean": clean_of(code, errors)}
    return None


def event_folder(writer, repo):
    return pathlib.Path(writer.event_path(writer.store_root(os.environ), PLUGIN, repo, "x")).parent


def runs(writer, repo):
    try:
        names = tuple(entry.name for entry in event_folder(writer, repo).iterdir())
    except OSError:
        return ()
    matches = tuple(RUN_FILE.fullmatch(name) for name in names)
    return tuple(sorted(
        ((found.group(2), found.group(1), found.group(0)[:-len(".jsonl")]) for found in matches if found),
        reverse=True,
    ))


def newest_run(writer, repo, slug):
    return next((run for _, run_slug, run in runs(writer, repo) if run_slug == slug), None)


def run_lines(writer, repo, run):
    try:
        text = (event_folder(writer, repo) / (run + ".jsonl")).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ()
    def parsed(line):
        try:
            value = json.loads(line)
        except ValueError:
            return None
        return value if isinstance(value, dict) else None
    return tuple(value for value in map(parsed, text.splitlines()) if value is not None)


def open_run_of_session(writer, repo, session):
    def belongs(lines):
        return bool(lines) and lines[-1].get("session") == session and not any(line.get("event") == HANDOFF for line in lines)
    return next(
        ((slug, run) for _, slug, run in runs(writer, repo) if belongs(run_lines(writer, repo, run))),
        None,
    )


def handed_off(root, slug):
    record = read_json(root / "docs" / "specs" / (slug + ".record.json"))
    return isinstance(record, dict) and record.get("status") == HANDED_OFF


def bash_events(writer, payload, root, repo, moment):
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str) or not any(name in command for name in SCRIPT_NAMES):
        return ()
    try:
        found, total = recognised(command, payload.get("cwd") or str(root))
    except ValueError:
        return ()
    single = len(found) == 1
    output = output_text(payload) if single else ""
    code = exit_code(payload) if single and found[0][2] == total - 1 else None
    outcome = (code, counted(output, "error:") if single else None, counted(output, "warning:") if single else None)

    def event_for(script):
        name, arguments, _, folder = script
        slug = slug_of(spec_path(name, arguments))
        if slug is None:
            return None
        if name == "tree_guard.py" and subcommand(arguments) == "snapshot":
            if payload.get("hook_event_name") != "PostToolUse":
                return None
            amending = handed_off(root, slug)
            fields = {"slug": slug, "amends": newest_run(writer, repo, slug) if amending else None, "amending": amending}
            return slug, writer.run_id(slug, moment), "run.start", fields
        described = script_event(name, arguments, folder, outcome)
        run = newest_run(writer, repo, slug)
        if described is None or run is None:
            return None
        return (slug, run) + described

    return tuple(event for event in map(event_for, found) if event is not None)


def reviewer_reply(payload):
    response = payload.get("tool_response")
    content = response.get("content") if isinstance(response, dict) else response
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(
        part["text"] for part in content
        if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
    )


def review_fields(reply):
    lines = tuple(line.strip() for line in reply.splitlines())
    first = next((line for line in lines if line), "")
    status = next((index for index, line in enumerate(lines) if line.startswith(STATUS)), None)
    return {
        "approved": True if first == APPROVED else False if first == ISSUES_FOUND else None,
        "issues": None if status is None else sum(1 for line in reply.splitlines()[status + 1:] if line.startswith(ISSUE)),
    }


def session_events(writer, payload, repo):
    tool = payload.get("tool_name")
    subagent = (payload.get("tool_input") or {}).get("subagent_type")
    if payload.get("hook_event_name") != "PostToolUse":
        return ()
    if tool == "AskUserQuestion":
        described = ("readback.asked", {})
    elif tool in AGENT_TOOLS and subagent == REVIEWER:
        described = ("review.done", review_fields(reviewer_reply(payload)))
    else:
        return ()
    found = open_run_of_session(writer, repo, payload.get("session_id"))
    return () if found is None else (found + described,)


def plugin_version():
    manifest = read_json(PLUGIN_FOLDER / ".claude-plugin" / "plugin.json")
    return manifest.get("version") if isinstance(manifest, dict) else None


def catalogue():
    return read_json(PLUGIN_FOLDER / "metrics" / "catalogue.json")


def start_summary(root, slug, run):
    try:
        subprocess.Popen(
            [sys.executable, str(SCRIPTS / "metrics_summary.py"), "--repo", str(root), "--slug", slug, "--run", run],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=dict(os.environ),
        )
    except OSError:
        return


def record(writer, root, repo, events, moment):
    version = plugin_version()
    described = catalogue()

    def write(event):
        slug, run, name, fields = event
        warnings = tuple(
            warning
            for warning in (
                writer.append_event(PLUGIN, version, repo, run, name, fields, now=moment),
                writer.write_catalogue(PLUGIN, described) if described is not None else None,
            )
            if warning is not None
        )
        for warning in warnings:
            sys.stderr.write(warning + "\n")
        return None if warnings else (slug, run)

    written = tuple(dict.fromkeys(pair for pair in map(write, events) if pair is not None))
    for slug, run in written:
        start_summary(root, slug, run)


def handle(payload):
    tool = payload.get("tool_name")
    if payload.get("hook_event_name") not in ("PostToolUse", "PostToolUseFailure"):
        return
    if tool == "Bash" and not any(name in str((payload.get("tool_input") or {}).get("command")) for name in SCRIPT_NAMES):
        return
    if tool not in ("Bash", "AskUserQuestion") + AGENT_TOOLS:
        return
    root = git_root(payload.get("cwd"))
    if root is None:
        return
    writer = load_writer()
    moment = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    repo = root.name
    events = bash_events(writer, payload, root, repo, moment) if tool == "Bash" else session_events(writer, payload, repo)
    if events:
        record(writer, root, repo, events, moment)


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        handle(payload)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
