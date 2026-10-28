import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

USAGE = "usage: python3 outcomes.py --repo ROOT --record RECORD"
OPTIONS = ("--record", "--repo")
STORE_VARIABLE = "RECEIPTS_TRAJECTORY_STORE"
CONFIG_NAME = "receipts.config.json"
HOME_STORE = (".claude", "mcp-servers", "trajectory-kb", "data", "trajectories.jsonl")
REPO_STORE = (".receipts", "trajectories.jsonl")
K6_KINDS = frozenset(("kind:gate", "kind:verdict"))
FIXED = "fixed"
GIT_TIMEOUT = 10
URL_PARTS_RE = re.compile(r"[/:\\]")


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_items = load_sibling("check_items")
surface_probe = load_sibling("surface_probe")
tree_guard = load_sibling("tree_guard")


def home_store():
    return pathlib.Path(os.path.expanduser("~")).joinpath(*HOME_STORE)


def config_folder(root):
    return next((folder for folder in (root,) + tuple(root.parents) if (folder / CONFIG_NAME).is_file()), None)


def read_config(folder):
    try:
        config = json.loads((folder / CONFIG_NAME).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, RecursionError):
        return None
    return config if isinstance(config, dict) else None


def configured_store(folder, config):
    agent = config.get("agent")
    choice = agent.get("trajectory_store") if isinstance(agent, dict) else None
    if not isinstance(choice, str) or choice == "home":
        return home_store()
    if choice == "repo":
        return folder.joinpath(*REPO_STORE)
    return folder / choice


def find_store(root):
    chosen = os.environ.get(STORE_VARIABLE)
    if chosen:
        return pathlib.Path(chosen)
    folder = config_folder(root)
    config = None if folder is None else read_config(folder)
    return home_store() if config is None else configured_store(folder, config)


def remote_name(root):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=tree_guard.git_environment(),
            timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    url = tree_guard.decode(result.stdout).strip().rstrip("/")
    name = URL_PARTS_RE.split(url)[-1]
    trimmed = name[: -len(".git")] if name.endswith(".git") else name
    return trimmed or None


def repository_names(root):
    return frozenset(name.lower() for name in (remote_name(root), root.name) if name)


def read_entries(store):
    try:
        text = store.read_bytes().decode("utf-8", "replace")
    except FileNotFoundError:
        return ()
    except OSError:
        return None
    return tuple(entry for entry in (parsed(line) for line in text.splitlines() if line.strip()) if entry is not None)


def parsed(line):
    try:
        entry = json.loads(line)
    except (ValueError, RecursionError):
        return None
    return entry if isinstance(entry, dict) else None


def is_k6(entry, names):
    repo = entry.get("repo")
    tags = entry.get("tags")
    return (
        isinstance(repo, str)
        and repo.lower() in names
        and isinstance(tags, list)
        and any(tag in K6_KINDS for tag in tags if isinstance(tag, str))
    )


def failure_kind(entry):
    for key in ("root_cause", "symptom"):
        if check_items.is_text(entry.get(key)):
            return entry[key]
    return "%s at %s" % (entry.get("outcome"), entry.get("surface"))


def repeated_kinds(entries):
    kinds = tuple(failure_kind(entry) for entry in entries if entry.get("outcome") != FIXED)
    counts = {kind: kinds.count(kind) for kind in kinds}
    return [
        {"kind": kind, "count": count}
        for kind, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
        if count >= 2
    ]


def outcomes(root, store, stored):
    names = repository_names(root)
    entries = tuple(entry for entry in stored if is_k6(entry, names))
    return {"store": os.path.abspath(str(store)), "entries": len(entries), "repeated": repeated_kinds(entries)}


def parse_arguments(argv):
    pairs = tuple(zip(argv[0::2], argv[1::2]))
    options = tuple(sorted(option for option, _ in pairs))
    if len(argv) % 2 or options != OPTIONS or any(value.startswith("--") for _, value in pairs):
        return None
    values = dict(pairs)
    return values["--repo"], values["--record"]


def main(argv):
    arguments = parse_arguments(argv)
    if arguments is None:
        print(USAGE, file=sys.stderr)
        return 2
    root, record_path = arguments
    record = surface_probe.read_record(record_path)
    if record is None:
        print("cannot read a JSON object from: " + record_path, file=sys.stderr)
        return 2
    repository = pathlib.Path(os.path.abspath(root))
    store = find_store(repository)
    stored = read_entries(store)
    if stored is None:
        print("cannot read the trajectory store: " + os.path.abspath(str(store)), file=sys.stderr)
        return 2
    found = outcomes(repository, store, stored)
    if not surface_probe.write_record(record_path, {**record, "outcomes": found}):
        print("cannot write: " + record_path, file=sys.stderr)
        return 2
    for entry in found["repeated"]:
        print("repeated: %s (%d times)" % (entry["kind"], entry["count"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
