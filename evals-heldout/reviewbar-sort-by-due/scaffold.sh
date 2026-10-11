#!/usr/bin/env bash
set -euo pipefail

mkdir -p tasks tests

cat > README.md <<'EOF'
# Tasks

Tasks is a small to-do web app. Most people open it from the browser on their phone.

Each task has a title, notes, a done flag and a due date. The app keeps every task in `tasks.json`.

Start the app with `python3 -m tasks.server` and open http://localhost:8000.

The app uses only the Python 3 standard library. Its tests run with `python3 -m unittest discover tests`.
EOF

cat > tasks.json <<'EOF'
[
  {
    "title": "Buy groceries",
    "notes": "Milk, eggs, bread and something for Sunday lunch.",
    "done": false,
    "due": "2026-10-12"
  },
  {
    "title": "Book a dentist appointment",
    "notes": "Ask for a morning slot. The last check-up was in March.",
    "done": false,
    "due": null
  },
  {
    "title": "Return library books",
    "notes": "Two novels and the travel guide.",
    "done": true,
    "due": "2026-10-05"
  }
]
EOF

: > tasks/__init__.py

cat > tasks/store.py <<'EOF'
import json
import pathlib

FIELDS = ("title", "notes", "done", "due")


def load(path):
    file = pathlib.Path(path)
    if not file.exists():
        return []
    return json.loads(file.read_text(encoding="utf-8"))


def save(path, tasks):
    pathlib.Path(path).write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8")
    return tasks


def new_task(title, notes="", due=None):
    return {"title": title, "notes": notes, "done": False, "due": due}


def add(tasks, task):
    return tasks + [task]


def mark_all_done(tasks):
    return [dict(task, done=True) for task in tasks]
EOF

cat > tasks/paging.py <<'EOF'
PAGE_SIZE = 10


def page_count(items):
    return max(1, -(-len(items) // PAGE_SIZE))


def page(items, number):
    start = (number - 1) * PAGE_SIZE
    return items[start:start + PAGE_SIZE - 1]
EOF

cat > tasks/views.py <<'EOF'
import html

from tasks import paging


def task_item(task):
    mark = "[x]" if task["done"] else "[ ]"
    due = " (due {})".format(html.escape(task["due"])) if task["due"] else ""
    return "<li>{} {}{}</li>".format(mark, html.escape(task["title"]), due)


def add_form():
    return (
        '<form method="post" action="/add">'
        '<input name="title" placeholder="Title">'
        '<textarea name="notes" placeholder="Notes"></textarea>'
        '<input name="due" type="date">'
        '<button type="submit">Sumbit</button>'
        "</form>"
    )


def mark_all_done_form():
    return (
        '<form method="post" action="/done-all">'
        '<button type="submit">Mark all done</button>'
        "</form>"
    )


def page_links(tasks, number):
    count = paging.page_count(tasks)
    previous = '<a href="/?page={}">Previous</a>'.format(number - 1) if number > 1 else ""
    following = '<a href="/?page={}">Next</a>'.format(number + 1) if number < count else ""
    return "<nav>{} Page {} of {} {}</nav>".format(previous, number, count, following)


def render_list(tasks, number=1):
    items = "".join(task_item(task) for task in paging.page(tasks, number))
    return (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Tasks</title>"
        "</head><body>"
        "<h1>Tasks</h1>"
        + add_form()
        + "<ul>" + items + "</ul>"
        + page_links(tasks, number)
        + mark_all_done_form()
        + "</body></html>"
    )
EOF

cat > tasks/server.py <<'EOF'
import http.server
import pathlib
import sys
import urllib.parse

from tasks import store, views

TASKS_FILE = pathlib.Path(__file__).resolve().parent.parent / "tasks.json"


def page_number(query):
    values = urllib.parse.parse_qs(query).get("page", ["1"])
    return int(values[0]) if values[0].isdigit() and int(values[0]) > 0 else 1


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
        url = urllib.parse.urlsplit(self.path)
        if url.path != "/":
            self.send_error(404)
            return
        self.send_page(views.render_list(store.load(TASKS_FILE), page_number(url.query)))

    def do_POST(self):
        if self.path == "/add":
            fields = self.read_form()
            task = store.new_task(fields.get("title", ""), fields.get("notes", ""), fields.get("due") or None)
            store.save(TASKS_FILE, store.add(store.load(TASKS_FILE), task))
            self.redirect_home()
            return
        if self.path == "/done-all":
            store.save(TASKS_FILE, store.mark_all_done(store.load(TASKS_FILE)))
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

from tasks import store


class StoreTest(unittest.TestCase):
    def test_saved_tasks_load_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "tasks.json"
            tasks = store.add([], store.new_task("Water the plants", "Both balconies", "2026-10-20"))
            store.save(path, tasks)
            self.assertEqual(store.load(path), tasks)

    def test_missing_file_loads_as_no_tasks(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(store.load(pathlib.Path(folder) / "tasks.json"), [])

    def test_new_task_has_every_field_and_starts_open(self):
        task = store.new_task("Call the bank")
        self.assertEqual(tuple(task), store.FIELDS)
        self.assertFalse(task["done"])


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_paging.py <<'EOF'
import unittest

from tasks import paging


class PagingTest(unittest.TestCase):
    def test_a_short_list_fits_on_one_page(self):
        items = ["first", "second", "third"]
        self.assertLess(len(items), paging.PAGE_SIZE)
        self.assertEqual(paging.page(items, 1), items)
        self.assertEqual(paging.page_count(items), 1)


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_mark_all_done.py <<'EOF'
import unittest

from tasks import store, views


class MarkAllDoneTest(unittest.TestCase):
    def test_the_list_shows_a_mark_all_done_button(self):
        page = views.render_list([store.new_task("Pay rent")])
        self.assertIn('action="/done-all"', page)
        self.assertIn(">Mark all done</button>", page)

    def test_mark_all_done_marks_every_task(self):
        tasks = [store.new_task("Pay rent"), store.new_task("Post the parcel")]
        self.assertTrue(all(task["done"] for task in store.mark_all_done(tasks)))
        self.assertFalse(any(task["done"] for task in tasks))


if __name__ == "__main__":
    unittest.main()
EOF

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Tasks app"
