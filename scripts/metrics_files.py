import json
import os
import pathlib
import stat

REPOSITORY_FILE_LIMIT = 4 * 1024 * 1024


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


def parsed_object(line):
    try:
        value = json.loads(line)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def json_objects(lines):
    return tuple(value for value in map(parsed_object, lines) if value is not None)


def json_lines(path):
    return json_objects(read_lines(path) or ())


def json_text(text):
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def plugin_version(plugin_folder):
    manifest = read_json(pathlib.Path(plugin_folder) / ".claude-plugin" / "plugin.json")
    return manifest.get("version") if isinstance(manifest, dict) else None


def regular_text(path, limit=REPOSITORY_FILE_LIMIT):
    try:
        if not stat.S_ISREG(os.stat(path).st_mode):
            return None
        with open(path, "rb") as handle:
            data = handle.read(limit + 1)
    except (OSError, TypeError, ValueError):
        return None
    if len(data) > limit:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def repository_text(root, path):
    folder = os.path.realpath(str(root))
    target = os.path.realpath(str(path))
    return regular_text(target) if os.path.commonpath((folder, target)) == folder else None
