#!/usr/bin/env bash
set -euo pipefail

mkdir -p notes tests

cat > README.md <<'EOF'
# Notes

Notes is a small notes web app. Each note has a title, a body and the time it was created. The app keeps every note in `notes.json`.

The list shows notes newest first. Each note has a Delete button.

Start the app with `python3 -m notes.server` and open http://localhost:8000.

The app uses only the Python 3 standard library. Its tests run with `python3 -m unittest discover tests`.
EOF

cat > notes.json <<'EOF'
[
  {
    "title": "Packing list",
    "body": "Charger, passport, rain jacket.",
    "created": "2026-09-02T08:15:00"
  },
  {
    "title": "Gift ideas",
    "body": "A board game for Sam, a scarf for Priya.",
    "created": "2026-09-14T19:40:00"
  },
  {
    "title": "Garden",
    "body": "Plant the bulbs before the first frost.",
    "created": "2026-09-28T07:05:00"
  }
]
EOF

: > notes/__init__.py

cat > notes/store.py <<'EOF'
import datetime
import json
import pathlib

FIELDS = ("title", "body", "created")


def load(path):
    file = pathlib.Path(path)
    if not file.exists():
        return []
    return json.loads(file.read_text(encoding="utf-8"))


def save(path, notes):
    pathlib.Path(path).write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")
    return notes


def new_note(title, body, created=None):
    stamp = created or datetime.datetime.now().isoformat(timespec="seconds")
    return {"title": title, "body": body, "created": stamp}


def add(notes, note):
    return notes + [note]


def delete(notes, index):
    return notes[:index] + notes[index + 1:]
EOF

cat > notes/views.py <<'EOF'
import html


def ordered(notes):
    return sorted(enumerate(notes), key=lambda pair: pair[1]["created"])


def note_item(index, note):
    return (
        "<li>"
        "<h2>{}</h2>"
        "<p>{}</p>"
        '<form method="post" action="/delete">'
        '<input type="hidden" name="index" value="{}">'
        '<button type="submit">Delete</button>'
        "</form>"
        "</li>"
    ).format(html.escape(note["title"]), html.escape(note["body"]), index)


def add_form():
    return (
        '<form method="post" action="/add">'
        '<input name="title" placeholder="Title">'
        '<textarea name="body" placeholder="Write a note"></textarea>'
        '<button type="submit">Save</button>'
        "</form>"
    )


def render_list(notes):
    items = "".join(note_item(index, note) for index, note in ordered(notes))
    return (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Notes</title>"
        "</head><body>"
        "<h1>Notes</h1>"
        + add_form()
        + "<ul>" + items + "</ul>"
        + "</body></html>"
    )
EOF

cat > notes/server.py <<'EOF'
import http.server
import pathlib
import sys
import urllib.parse

from notes import store, views

NOTES_FILE = pathlib.Path(__file__).resolve().parent.parent / "notes.json"


def form_fields(body):
    fields = urllib.parse.parse_qs(body, keep_blank_values=True)
    return {key: values[0] for key, values in fields.items()}


class Handler(http.server.BaseHTTPRequestHandler):
    def send_page(self, text):
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect_home(self):
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def read_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        return form_fields(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        if urllib.parse.urlsplit(self.path).path != "/":
            self.send_error(404)
            return
        self.send_page(views.render_list(store.load(NOTES_FILE)))

    def do_POST(self):
        if self.path == "/add":
            fields = self.read_form()
            note = store.new_note(fields.get("title", ""), fields.get("body", ""))
            store.save(NOTES_FILE, store.add(store.load(NOTES_FILE), note))
            self.redirect_home()
            return
        if self.path == "/delete":
            index = self.read_form().get("index", "")
            notes = store.load(NOTES_FILE)
            if index.isdigit() and int(index) < len(notes):
                store.save(NOTES_FILE, store.delete(notes, int(index)))
            self.redirect_home()
            return
        self.send_error(404)


def main(argv):
    port = int(argv[0]) if argv else 8000
    server = http.server.HTTPServer(("", port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
EOF

cat > tests/test_store.py <<'EOF'
import pathlib
import tempfile
import unittest

from notes import store


class StoreTest(unittest.TestCase):
    def test_saved_notes_load_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "notes.json"
            notes = store.add([], store.new_note("Recipes", "Soup on Monday", "2026-09-01T10:00:00"))
            store.save(path, notes)
            self.assertEqual(store.load(path), notes)

    def test_missing_file_loads_as_no_notes(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(store.load(pathlib.Path(folder) / "notes.json"), [])

    def test_new_note_has_every_field(self):
        self.assertEqual(tuple(store.new_note("Ideas", "Paint the shed")), store.FIELDS)


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_delete.py <<'EOF'
import unittest

from notes import store, views


class DeleteTest(unittest.TestCase):
    def test_each_note_has_a_delete_button(self):
        notes = [
            store.new_note("Ideas", "Paint the shed", "2026-09-01T10:00:00"),
            store.new_note("Errands", "Post office", "2026-09-02T10:00:00"),
        ]
        page = views.render_list(notes)
        self.assertEqual(page.count('action="/delete"'), 2)
        self.assertEqual(page.count(">Delete</button>"), 2)

    def test_delete_removes_only_that_note(self):
        notes = [
            store.new_note("Ideas", "Paint the shed", "2026-09-01T10:00:00"),
            store.new_note("Errands", "Post office", "2026-09-02T10:00:00"),
        ]
        self.assertEqual(store.delete(notes, 0), notes[1:])
        self.assertEqual(len(notes), 2)


if __name__ == "__main__":
    unittest.main()
EOF

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Notes app"
