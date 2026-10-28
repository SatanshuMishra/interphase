import importlib.util
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys

USAGE = "usage: python3 surface_probe.py --record RECORD --repo ROOT [--unattended] [--timeout SECONDS]"
VALUED = ("--record", "--repo", "--timeout")
UNATTENDED = "--unattended"
DEFAULT_TIMEOUT = 60.0
ASSIGNMENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
NO_EXECUTABLE = "command names no executable"
EXTRA_PROBES = {
    "browser": lambda target: (("playwright", "playwright"),),
    "desktop": lambda target: (("vmlab", target),),
    "mobile": lambda target: (("vmlab", target),),
    "agent": lambda target: (("claude", "claude"),),
}
TOLERATED_VMLAB_EXITS = (0, 2)


def load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_items = load_sibling("check_items")
atomic_file = load_sibling("atomic_file")


class TimedOut(Exception):
    pass


def command_words(command):
    if not check_items.is_text(command):
        return ()
    try:
        return tuple(shlex.split(command))
    except ValueError:
        return ()


def executable(command):
    return next((word for word in command_words(command) if not ASSIGNMENT_RE.match(word)), None)


def command_target(line):
    found = executable(line.get("command"))
    if found is not None:
        return found
    command = line.get("command")
    return command.strip() if check_items.is_text(command) and command.strip() else "command"


def line_surface(line):
    surface = line.get("surface")
    return surface if isinstance(surface, dict) else {}


def expected_probes(line):
    surface = line_surface(line)
    family = surface.get("family")
    target = surface.get("target")
    extra = EXTRA_PROBES.get(family) if isinstance(family, str) else None
    return (("command", command_target(line)),) + (extra(target) if extra and check_items.is_text(target) else ())


def run_quietly(arguments, cwd, timeout):
    try:
        return subprocess.run(
            arguments,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise TimedOut()


def timed_out(timeout):
    return ("fail", "timed out after %g seconds" % timeout)


def probe_command(line, target, root, timeout):
    found = executable(line.get("command"))
    if found is None:
        return ("fail", NO_EXECUTABLE)
    if "/" in found:
        path = pathlib.Path(root) / found
        if path.is_file() and os.access(str(path), os.X_OK):
            return ("pass", str(path))
        return ("fail", "%s is not an executable file in the repository" % found)
    resolved = shutil.which(found)
    return ("pass", resolved) if resolved else ("fail", "%s is not on PATH" % found)


def probe_playwright(line, target, root, timeout):
    installed = shutil.which("playwright")
    if installed:
        result = run_quietly([installed, "--version"], root, timeout)
        if result.returncode == 0:
            return ("pass", "%s --version exited 0" % installed)
        return ("fail", "playwright --version exited %d" % result.returncode)
    npx = shutil.which("npx")
    if not npx:
        return ("fail", "Playwright is not installed: neither playwright nor npx is on PATH")
    result = run_quietly([npx, "--no-install", "playwright", "--version"], root, timeout)
    if result.returncode == 0:
        return ("pass", "npx --no-install playwright --version exited 0")
    return ("fail", "Playwright is not installed: npx --no-install playwright --version exited %d" % result.returncode)


def machines(stdout):
    try:
        listing = json.loads(stdout)
    except (ValueError, RecursionError):
        return None
    if not isinstance(listing, list):
        return None
    return tuple(machine for machine in listing if isinstance(machine, dict))


def names_target(machine, target):
    return any(
        isinstance(machine.get(key), str) and machine[key].lower() == target.lower() for key in ("name", "platform")
    )


def probe_vmlab(line, target, root, timeout):
    installed = shutil.which("vmlab")
    if not installed:
        return ("fail", "vmlab is not on PATH")
    result = run_quietly([installed, "capabilities", "--json"], root, timeout)
    if result.returncode not in TOLERATED_VMLAB_EXITS:
        return ("fail", "vmlab capabilities --json exited %d" % result.returncode)
    listed = machines(result.stdout)
    if listed is None:
        return ("fail", "vmlab capabilities --json printed unreadable output")
    matching = tuple(machine for machine in listed if names_target(machine, target))
    if not matching:
        return ("fail", "no machine named or running %s" % target)
    machine = matching[0]
    return ("pass", "machine %s runs %s" % (machine.get("name"), machine.get("platform")))


def probe_claude(line, target, root, timeout):
    resolved = shutil.which("claude")
    return ("pass", resolved) if resolved else ("fail", "claude is not on PATH")


PROBES = {"command": probe_command, "playwright": probe_playwright, "vmlab": probe_vmlab, "claude": probe_claude}


def run_probe(line, name, target, root, timeout):
    try:
        return PROBES[name](line, target, root, timeout)
    except TimedOut:
        return timed_out(timeout)
    except OSError as exc:
        return ("fail", "cannot run the %s probe: %s" % (name, exc))


def builder_seams(record):
    seams = record.get("seams")
    return frozenset(
        seam["name"]
        for seam in (seams if isinstance(seams, list) else ())
        if isinstance(seam, dict) and check_items.is_text(seam.get("name")) and seam.get("builder_runs") is True
    )


def acceptance_lines(record):
    criteria = record.get("criteria")
    return tuple(
        (criterion, line)
        for criterion in (criteria if isinstance(criteria, list) else ())
        if isinstance(criterion, dict) and isinstance(criterion.get("acceptance"), list)
        for line in criterion["acceptance"]
        if isinstance(line, dict) and check_items.is_text(line.get("id"))
    )


def planned(record):
    candidates = tuple(
        (criterion, line, name, target)
        for criterion, line in acceptance_lines(record)
        for name, target in expected_probes(line)
    )
    keys = tuple((line["id"], name, target) for _, line, name, target in candidates)
    return tuple(candidate for position, candidate in enumerate(candidates) if keys[position] not in keys[:position])


def probe_all(record, root, timeout):
    builders = builder_seams(record)
    return tuple(
        (
            {"check": line["id"], "probe": name, "target": target, "status": status, "detail": detail},
            criterion.get("seam") in builders and status == "fail",
        )
        for criterion, line, name, target in planned(record)
        for status, detail in (run_probe(line, name, target, root, timeout),)
    )


def failure_text(entry):
    return "%s %s %s: %s" % (entry["check"], entry["probe"], entry["target"], entry["detail"])


def updated(record, results, unattended):
    probed = {**record, "probes": [entry for entry, _ in results]}
    blocking = tuple(entry for entry, blocks in results if blocks)
    if not unattended or not blocking:
        return probed
    reason = "surface probe failed: " + "; ".join(failure_text(entry) for entry in blocking)
    return {**probed, "status": "stopped", "stop": {"phase": "probe", "reason": reason}}


def parse_timeout(text):
    try:
        value = float(text)
    except ValueError:
        return None
    return value if 0 < value < float("inf") else None


def parse_arguments(argv):
    flags = tuple(argument for argument in argv if argument == UNATTENDED)
    rest = tuple(argument for argument in argv if argument != UNATTENDED)
    pairs = tuple(zip(rest[0::2], rest[1::2]))
    options = tuple(option for option, _ in pairs)
    if len(flags) > 1 or len(rest) % 2 or len(set(options)) != len(options):
        return None
    if not set(options) <= set(VALUED) or not {"--record", "--repo"} <= set(options):
        return None
    if any(value.startswith("--") for _, value in pairs):
        return None
    values = dict(pairs)
    timeout = parse_timeout(values["--timeout"]) if "--timeout" in values else DEFAULT_TIMEOUT
    if timeout is None:
        return None
    return values["--record"], values["--repo"], bool(flags), timeout


def read_record(path):
    try:
        record = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, RecursionError):
        return None
    return record if isinstance(record, dict) else None


def write_record(path, record):
    try:
        atomic_file.replace(path, (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    except (OSError, UnicodeEncodeError):
        return False
    return True


def main(argv):
    arguments = parse_arguments(argv)
    if arguments is None:
        print(USAGE, file=sys.stderr)
        return 2
    record_path, root, unattended, timeout = arguments
    if not pathlib.Path(root).is_dir():
        print("cannot read: " + root, file=sys.stderr)
        return 2
    record = read_record(record_path)
    if record is None:
        print("cannot read a JSON object from: " + record_path, file=sys.stderr)
        return 2
    results = probe_all(record, root, timeout)
    if not write_record(record_path, updated(record, results, unattended)):
        print("cannot write: " + record_path, file=sys.stderr)
        return 2
    for entry, _ in results:
        print("%s: %s" % (entry["status"], failure_text(entry)))
    return 1 if any(blocks for _, blocks in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
