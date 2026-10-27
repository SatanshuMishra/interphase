import argparse
import datetime
import functools
import importlib.util
import json
import os
import pathlib
import re
import sys

PLUGIN = "interphase"
SCRIPTS = pathlib.Path(__file__).resolve().parent
PLUGIN_FOLDER = SCRIPTS.parent
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
PATHWAY = re.compile(r"Pathway: ([a-z]+)\.")
PATHWAYS = ("feature", "bug", "prototype", "project")
BRIEF_LINE = "Lane: brief."
INTENT_LINE = re.compile(r"- I[0-9]+\b")
INFERRED = "(inferred)"
RELIES_ON = re.compile(r"\(relies on([^)]*)\)")
INTENT_ID = re.compile(r"\bI([0-9]+)\b")
CHECKS = (("record", "round.recorded"), ("steps", "steps.checked"), ("spec", "spec.checked"), ("items", "items.checked"))
CLOSING_CHECKS = ("spec.checked", "items.checked", "review.done")
HANDOFF = "run.handoff"
STATUSES = {True: "handed-off", False: "guard-difference"}
OWN_AGENTS = ("interphase:scout", "interphase:spec-reviewer")
MAIN_SESSION = "main session"
SYNTHETIC = "<synthetic>"
TOKEN_KINDS = ("input", "cache_write_5m", "cache_write_1h", "cache_read", "output")
ASK = "AskUserQuestion"
PERSON = "human"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def read_lines(path):
    try:
        return pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None


def json_lines(path):
    def parsed(line):
        try:
            value = json.loads(line)
        except ValueError:
            return None
        return value if isinstance(value, dict) else None
    return tuple(value for value in map(parsed, read_lines(path) or ()) if value is not None)


def moment(text):
    try:
        return datetime.datetime.strptime(text, TIMESTAMP_FORMAT).replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return None


def transcript_moment(text):
    if not isinstance(text, str):
        return None
    try:
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(datetime.timezone.utc)
    except ValueError:
        return None


def named(events, name):
    return tuple(event for event in events if event.get("event") == name)


def last_of(events, name):
    found = named(events, name)
    return found[-1] if found else None


def section(lines, heading):
    starts = tuple(index for index, line in enumerate(lines) if line.rstrip() == heading)
    if not starts:
        return ()
    rest = lines[starts[0] + 1:]
    end = next((index for index, line in enumerate(rest) if line.startswith("## ")), len(rest))
    return tuple(rest[:end])


def spec_figures(lines, check_spec):
    if lines is None:
        return {"pathway": None, "lane": None, "assumptions": None, "assumptions_by_intent": None}
    pathway = next((found.group(1) for found in map(PATHWAY.fullmatch, (line.rstrip() for line in lines)) if found), None)
    assumptions = tuple(line for _, line in check_spec.assumption_lines(lines))
    cited = tuple(
        frozenset(int(number) for inside in RELIES_ON.findall(line) for number in INTENT_ID.findall(inside))
        for line in assumptions
    )
    numbers = sorted(frozenset().union(*cited)) if cited else []
    return {
        "pathway": pathway if pathway in PATHWAYS else None,
        "lane": "brief" if BRIEF_LINE in (line.rstrip() for line in lines) else "full",
        "assumptions": len(assumptions),
        "assumptions_by_intent": [
            {"intent": "I" + str(number), "count": sum(1 for line in cited if number in line)} for number in numbers
        ],
    }


def decisions_figures(lines):
    if lines is None:
        return {"attended": None, "intent_lines": None, "decisions": None}
    intent = tuple(line.rstrip() for line in section(lines, "## Intent") if INTENT_LINE.match(line))
    return {
        "attended": None if not intent else not all(line.endswith(INFERRED) for line in intent),
        "intent_lines": len(intent),
        "decisions": sum(1 for line in section(lines, "## Decisions") if line.startswith("- ")),
    }


def entries(record, key):
    value = record.get(key) if isinstance(record, dict) else None
    return tuple(entry for entry in value if isinstance(entry, dict)) if isinstance(value, list) else None


def count_of(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def round_figures(record):
    rounds = entries(record, "rounds")
    if rounds is None:
        return {"rounds": None, "questions": None, "recommended": None, "changed": None}
    questions = sum(count_of(entry.get("questions")) for entry in rounds)
    changed = sum(count_of(entry.get("changed")) for entry in rounds)
    return {"rounds": len(rounds), "questions": questions, "recommended": questions - changed, "changed": changed}


def size(items):
    return None if items is None else len(items)


def having(items, key):
    return None if items is None else sum(1 for item in items if item.get(key))


def record_figures(record, amends):
    seams = entries(record, "seams")
    criteria = entries(record, "criteria")
    steps = entries(record, "steps")
    amendments = tuple(
        step.get("amendment") for step in steps or ()
        if isinstance(step.get("amendment"), int) and not isinstance(step.get("amendment"), bool)
    )
    return {
        "amendment": max(amendments) if amends is not None and amendments else None,
        "seams": size(seams),
        "criteria": size(criteria),
        "tests": None if criteria is None else sum(len(entries(criterion, "tests") or ()) for criterion in criteria),
        "unproven": having(criteria, "unproven"),
        "varying": having(criteria, "varies"),
        "case_tables": having(criteria, "case_table"),
        "steps": size(steps),
        "msps": None if steps is None else len(frozenset(step.get("msp") for step in steps if isinstance(step.get("msp"), str) and step.get("msp"))),
        "steps_with_assumptions": None if steps is None else sum(
            1 for step in steps if isinstance(step.get("assumptions"), list) and step.get("assumptions")
        ),
    }


def status_of(events):
    if not events:
        return None
    handoff = last_of(events, HANDOFF)
    return "in-progress" if handoff is None else STATUSES.get(handoff.get("clean"))


def readback_figures(events):
    if not events:
        return {"readbacks": None, "approved": None}
    indexes = tuple(index for index, event in enumerate(events) if event.get("event") == "readback.asked")
    if not indexes:
        return {"readbacks": 0, "approved": None}
    rendered = any(event.get("event") == "spec.rendered" for event in events[indexes[-1] + 1:])
    return {"readbacks": len(indexes), "approved": rendered}


def check_figures(events):
    if not events:
        return None
    return [
        {
            "check": check,
            "runs": len(found),
            "first_errors": found[0].get("errors"),
            "first_warnings": found[0].get("warnings"),
            "last_errors": found[-1].get("errors"),
        }
        for check, found in ((check, named(events, name)) for check, name in CHECKS)
        if found
    ]


def seconds_between(start, end):
    return (end - start).total_seconds()


def landmarks(events):
    timed = tuple((event.get("event"), moment(event.get("ts"))) for event in events)
    timed = tuple(pair for pair in timed if pair[1] is not None)

    def first(name):
        return next(((name, at) for event, at in timed if event == name), None)

    def last(name):
        found = tuple((name, at) for event, at in timed if event == name)
        return found[-1] if found else None

    rendered_index = next((index for index, (event, _) in enumerate(timed) if event == "spec.rendered"), None)
    closing = tuple(
        ("closing", at) for event, at in timed[rendered_index + 1:] if event in CLOSING_CHECKS
    ) if rendered_index is not None else ()
    return (
        first("run.start"),
        first("round.recorded"),
        first("steps.checked"),
        last("readback.asked"),
        first("spec.rendered"),
        closing[-1] if closing else None,
        last(HANDOFF),
    )


PHASE_NAMES = {
    "round.recorded": "interview",
    "steps.checked": "interview",
    "readback.asked": "read-back",
    "spec.rendered": "write",
    "closing": "review",
    HANDOFF: "hand-off",
}


def phase_figures(events):
    def keep(kept, landmark):
        if landmark is None or (kept and landmark[1] < kept[-1][1]):
            return kept
        return kept + (landmark,)

    kept = functools.reduce(keep, landmarks(events), ())
    spans = tuple(zip(kept, kept[1:]))
    return [
        {"phase": "ground" if index == 0 else PHASE_NAMES[end[0]], "seconds": seconds_between(start[1], end[1])}
        for index, (start, end) in enumerate(spans)
    ]


def time_figures(events):
    times = tuple(at for at in (moment(event.get("ts")) for event in events) if at is not None)
    if not times:
        return {"lead_seconds": None, "phases": None}
    return {"lead_seconds": seconds_between(times[0], times[-1]), "phases": phase_figures(events)}


def projects(home):
    return pathlib.Path(home) / ".claude" / "projects"


def main_transcripts(home, sessions):
    folder = projects(home)
    return tuple(path for session in sessions for path in sorted(folder.glob("*/" + session + ".jsonl")))


def own_agent_transcripts(home, sessions):
    folder = projects(home)
    found = tuple(
        (path, read_json(path.with_name(path.name[:-len(".jsonl")] + ".meta.json")))
        for session in sessions
        for path in sorted(folder.glob("*/" + session + "/subagents/agent-*.jsonl"))
    )
    return tuple(
        (path, meta.get("agentType")) for path, meta in found
        if isinstance(meta, dict) and meta.get("agentType") in OWN_AGENTS
    )


def parts(record):
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    return tuple(part for part in content if isinstance(part, dict)) if isinstance(content, list) else ()


def typed_by_person(record):
    origin = record.get("origin")
    return isinstance(origin, dict) and origin.get("kind") == PERSON and not record.get("isMeta")


def typed_text(record):
    if not typed_by_person(record):
        return False
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return bool(content.strip())
    pieces = parts(record)
    return any(part.get("type") == "text" for part in pieces) and not any(part.get("type") == "tool_result" for part in pieces)


def answers_question(record, asked):
    return any(part.get("type") == "tool_result" and part.get("tool_use_id") in asked for part in parts(record))


def transcript_wait(path, start, end):
    def step(state, record):
        total, latest, asked = state
        kind = record.get("type")
        at = transcript_moment(record.get("timestamp"))
        if kind == "assistant":
            questions = frozenset(
                part.get("id") for part in parts(record) if part.get("type") == "tool_use" and part.get("name") == ASK
            )
            return total, at or latest, asked | questions
        waited = (
            kind == "user" and at is not None and latest is not None and start <= at <= end
            and (typed_text(record) or answers_question(record, asked))
        )
        return (total + seconds_between(latest, at) if waited else total), latest, asked

    return functools.reduce(step, json_lines(path), (0.0, None, frozenset()))[0]


def wait_figure(home, sessions, span):
    paths = main_transcripts(home, sessions)
    if not paths or span is None:
        return None
    return sum(transcript_wait(path, span[0], span[1]) for path in paths)


def positive(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def message_tokens(usage):
    usage = usage if isinstance(usage, dict) else {}
    creation = usage.get("cache_creation")
    return {
        "input": positive(usage.get("input_tokens")),
        "cache_write_5m": positive(creation.get("ephemeral_5m_input_tokens") if isinstance(creation, dict) else usage.get("cache_creation_input_tokens")),
        "cache_write_1h": positive(creation.get("ephemeral_1h_input_tokens")) if isinstance(creation, dict) else 0,
        "cache_read": positive(usage.get("cache_read_input_tokens")),
        "output": positive(usage.get("output_tokens")),
    }


def counted_messages(sources, span):
    start, end = span

    def counted(record):
        message = record.get("message") if isinstance(record.get("message"), dict) else {}
        at = transcript_moment(record.get("timestamp"))
        return (
            record.get("type") == "assistant"
            and at is not None
            and start <= at <= end
            and (message.get("id") or record.get("uuid")) is not None
            and message.get("model") != SYNTHETIC
        )

    def described(record, agent):
        message = record["message"] if isinstance(record.get("message"), dict) else {}
        return message.get("id") or record.get("uuid"), (agent, message.get("model"), message_tokens(message.get("usage")))

    pairs = tuple(
        described(record, agent) for path, agent in sources for record in json_lines(path) if counted(record)
    )
    return tuple(dict(reversed(pairs)).values())


def added(first, second):
    return {kind: first[kind] + second[kind] for kind in TOKEN_KINDS}


def cost(tokens, price):
    if not isinstance(price, dict):
        return None
    return sum(tokens[kind] * float(price.get(kind, 0)) for kind in TOKEN_KINDS) / 1000000


def spend_figures(home, sessions, span, prices):
    table = prices.get("per_million", {}) if isinstance(prices, dict) else {}
    date = prices.get("date") if isinstance(prices, dict) else None
    sources = tuple((path, MAIN_SESSION) for path in main_transcripts(home, sessions)) + own_agent_transcripts(home, sessions)
    if not sources or span is None:
        return {"usd": None, "prices_date": date, "tokens": None, "models": None, "unpriced": None}
    messages = counted_messages(sources, span)
    empty = {kind: 0 for kind in TOKEN_KINDS}

    def grouped(totals, message):
        agent, model, tokens = message
        count, summed = totals.get((agent, model), (0, empty))
        return {**totals, (agent, model): (count + 1, added(summed, tokens))}

    summed = tuple((agent, model, count, tokens) for (agent, model), (count, tokens) in functools.reduce(grouped, messages, {}).items())
    exact = tuple((agent, model, count, tokens, cost(tokens, table.get(model))) for agent, model, count, tokens in summed)
    unpriced = sorted(frozenset(str(model) for _, model, _, _, usd in exact if usd is None))
    models = sorted(
        (
            {"agent": agent, "model": model, "messages": count, "tokens": tokens, "usd": None if usd is None else round(usd, 6)}
            for agent, model, count, tokens, usd in exact
        ),
        key=lambda row: (row["usd"] is None, -(row["usd"] or 0), row["agent"], str(row["model"])),
    )
    return {
        "usd": None if unpriced else round(sum(usd for _, _, _, _, usd in exact), 6),
        "prices_date": date,
        "tokens": functools.reduce(added, (tokens for _, _, tokens in messages), empty),
        "models": models,
        "unpriced": unpriced,
    }


def run_span(events):
    times = tuple(at for at in (moment(event.get("ts")) for event in events) if at is not None)
    return (times[0], times[-1]) if times else None


def summary(repo, slug, events, home, prices):
    specs = pathlib.Path(repo) / "docs" / "specs"
    record = read_json(specs / (slug + ".record.json"))
    start = next(iter(named(events, "run.start")), None)
    amends = start.get("amends") if start else None
    sessions = tuple(sorted(frozenset(event.get("session") for event in events if isinstance(event.get("session"), str))))
    review = last_of(events, "review.done")
    span = run_span(events)
    spec = spec_figures(read_lines(specs / (slug + ".md")), load_script("check_spec"))
    decided = decisions_figures(read_lines(specs / (slug + ".decisions.md")))
    counts = record_figures(record, amends)
    timed = time_figures(events)
    readback = readback_figures(events)
    spend = spend_figures(home, sessions, span, prices)
    interview = round_figures(record)
    return {
        "slug": slug,
        "status": status_of(events),
        "pathway": spec["pathway"],
        "lane": spec["lane"],
        "attended": decided["attended"],
        "amends": amends,
        "amendment": counts["amendment"],
        "lead_seconds": timed["lead_seconds"],
        "wait_seconds": wait_figure(home, sessions, span),
        "phases": timed["phases"],
        "sessions": len(sessions) if events else None,
        "intent_lines": decided["intent_lines"],
        "rounds": interview["rounds"],
        "questions": interview["questions"],
        "recommended": interview["recommended"],
        "changed": interview["changed"],
        "readbacks": readback["readbacks"],
        "approved": readback["approved"],
        "decisions": decided["decisions"],
        "seams": counts["seams"],
        "criteria": counts["criteria"],
        "tests": counts["tests"],
        "unproven": counts["unproven"],
        "varying": counts["varying"],
        "case_tables": counts["case_tables"],
        "steps": counts["steps"],
        "msps": counts["msps"],
        "steps_with_assumptions": counts["steps_with_assumptions"],
        "assumptions": spec["assumptions"],
        "assumptions_by_intent": spec["assumptions_by_intent"],
        "checks": check_figures(events),
        "review_approved": review.get("approved") if review else None,
        "review_issues": review.get("issues") if review else None,
        "usd": spend["usd"],
        "prices_date": spend["prices_date"],
        "tokens": spend["tokens"],
        "models": spend["models"],
        "unpriced": spend["unpriced"],
        "spend_scope": "own",
    }


def plugin_version():
    manifest = read_json(PLUGIN_FOLDER / ".claude-plugin" / "plugin.json")
    return manifest.get("version") if isinstance(manifest, dict) else None


def newer_summary_exists(path, started):
    written = json_lines(path)
    stamp = moment(written[0].get("ts")) if written else None
    return stamp is not None and stamp > started


def parse_arguments(argv):
    parser = argparse.ArgumentParser(prog="metrics_summary.py")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--run", required=True)
    return parser.parse_args(argv)


def main(argv):
    started = datetime.datetime.now(datetime.timezone.utc)
    arguments = parse_arguments(argv)
    writer = load_script("metrics_writer")
    root = writer.store_root(os.environ)
    repo = pathlib.Path(arguments.repo).resolve()
    events = json_lines(writer.event_path(root, PLUGIN, repo.name, arguments.run))
    if newer_summary_exists(writer.summary_path(root, PLUGIN, repo.name, arguments.run), started):
        return 0
    home = os.environ.get("HOME") or str(pathlib.Path.home())
    fields = summary(repo, arguments.slug, events, home, read_json(SCRIPTS / "metrics_prices.json"))
    warning = writer.write_summary(PLUGIN, plugin_version(), repo.name, arguments.run, fields)
    if warning is not None:
        sys.stderr.write(warning + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
