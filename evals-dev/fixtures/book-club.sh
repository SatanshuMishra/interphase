#!/usr/bin/env bash
set -euo pipefail

mkdir -p club tests

cat > README.md <<'EOF'
# Page Turners

Page Turners is a sign-up sheet for a neighbourhood book club of about 20 people. Members put their name down for the next meeting, take it off again, and suggest the book to read after it.

The app keeps every meeting and its sign-ups in `meetings.json`. No sign-in exists yet: anyone who opens the sheet can add or remove any name.

Start the app with `python3 -m club.server` and open http://localhost:8000.

The app uses only the Python 3 standard library. Its tests run with `python3 -m unittest discover tests`.
EOF

cat > meetings.json <<'EOF'
[
  {
    "date": "2026-10-21",
    "book": "The Lighthouse Keeper's Year",
    "place": "The back room of the community library",
    "attendees": ["Hana", "Owen", "Lola"],
    "suggestions": ["A Map of Small Rivers"]
  },
  {
    "date": "2026-11-18",
    "book": "To be chosen at the October meeting",
    "place": "The back room of the community library",
    "attendees": [],
    "suggestions": []
  }
]
EOF

: > club/__init__.py

cat > club/sheet.py <<'EOF'
import json
import pathlib


def load(path):
    file = pathlib.Path(path)
    if not file.exists():
        return []
    return json.loads(file.read_text(encoding="utf-8"))


def save(path, meetings):
    pathlib.Path(path).write_text(json.dumps(meetings, indent=2) + "\n", encoding="utf-8")
    return meetings


def next_meeting(meetings, today):
    upcoming = sorted((meeting for meeting in meetings if meeting["date"] >= today), key=lambda meeting: meeting["date"])
    return upcoming[0] if upcoming else None


def changed(meetings, date, change):
    return [change(meeting) if meeting["date"] == date else meeting for meeting in meetings]


def sign_up(meetings, date, name):
    def add(meeting):
        if not name or name in meeting["attendees"]:
            return meeting
        return dict(meeting, attendees=meeting["attendees"] + [name])

    return changed(meetings, date, add)


def withdraw(meetings, date, name):
    def remove(meeting):
        return dict(meeting, attendees=[person for person in meeting["attendees"] if person != name])

    return changed(meetings, date, remove)


def suggest(meetings, date, book):
    def add(meeting):
        if not book or book in meeting["suggestions"]:
            return meeting
        return dict(meeting, suggestions=meeting["suggestions"] + [book])

    return changed(meetings, date, add)
EOF

cat > club/views.py <<'EOF'
import html


def attendee_item(date, name):
    return (
        "<li>{}"
        '<form method="post" action="/withdraw">'
        '<input type="hidden" name="date" value="{}">'
        '<input type="hidden" name="name" value="{}">'
        '<button type="submit">Remove</button>'
        "</form>"
        "</li>"
    ).format(html.escape(name), html.escape(date), html.escape(name))


def date_form(action, field, placeholder, label, date):
    return (
        '<form method="post" action="{}">'
        '<input type="hidden" name="date" value="{}">'
        '<input name="{}" placeholder="{}">'
        '<button type="submit">{}</button>'
        "</form>"
    ).format(action, html.escape(date), field, placeholder, label)


def render_sheet(meeting):
    if meeting is None:
        body = "<p>No meeting is planned yet.</p>"
    else:
        attendees = "".join(attendee_item(meeting["date"], name) for name in meeting["attendees"])
        suggestions = "".join("<li>{}</li>".format(html.escape(book)) for book in meeting["suggestions"])
        body = (
            "<h2>{} at {}</h2>"
            "<p>Reading: {}</p>"
            "<h3>Coming ({})</h3><ul>{}</ul>"
            "{}"
            "<h3>Suggested next</h3><ul>{}</ul>"
            "{}"
        ).format(
            html.escape(meeting["date"]),
            html.escape(meeting["place"]),
            html.escape(meeting["book"]),
            len(meeting["attendees"]),
            attendees,
            date_form("/sign-up", "name", "Your name", "Sign up", meeting["date"]),
            suggestions,
            date_form("/suggest", "book", "Book title", "Suggest", meeting["date"]),
        )
    return (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Page Turners</title>"
        "</head><body>"
        "<h1>Page Turners</h1>"
        + body
        + "</body></html>"
    )
EOF

cat > club/server.py <<'EOF'
import datetime
import http.server
import pathlib
import sys
import urllib.parse

from club import sheet, views

MEETINGS_FILE = pathlib.Path(__file__).resolve().parent.parent / "meetings.json"
CHANGES = {"/sign-up": ("name", sheet.sign_up), "/withdraw": ("name", sheet.withdraw), "/suggest": ("book", sheet.suggest)}


def form_fields(body):
    fields = urllib.parse.parse_qs(body, keep_blank_values=True)
    return {key: values[0].strip() for key, values in fields.items()}


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
        today = datetime.date.today().isoformat()
        self.send_page(views.render_sheet(sheet.next_meeting(sheet.load(MEETINGS_FILE), today)))

    def do_POST(self):
        if self.path not in CHANGES:
            self.send_error(404)
            return
        field, change = CHANGES[self.path]
        fields = self.read_form()
        meetings = sheet.load(MEETINGS_FILE)
        sheet.save(MEETINGS_FILE, change(meetings, fields.get("date", ""), fields.get(field, "")))
        self.redirect_home()


def main(argv):
    port = int(argv[0]) if argv else 8000
    server = http.server.HTTPServer(("", port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
EOF

cat > tests/test_sheet.py <<'EOF'
import pathlib
import tempfile
import unittest

from club import sheet


def meetings():
    return [
        {"date": "2026-10-21", "book": "Book one", "place": "Library", "attendees": ["Ivy"], "suggestions": []},
        {"date": "2026-11-18", "book": "Book two", "place": "Library", "attendees": [], "suggestions": []},
    ]


class SheetTest(unittest.TestCase):
    def test_saved_meetings_load_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "meetings.json"
            sheet.save(path, meetings())
            self.assertEqual(sheet.load(path), meetings())

    def test_next_meeting_is_the_first_from_today(self):
        self.assertEqual(sheet.next_meeting(meetings(), "2026-10-22")["date"], "2026-11-18")
        self.assertIsNone(sheet.next_meeting(meetings(), "2026-12-01"))

    def test_sign_up_adds_a_name_once_to_that_meeting(self):
        before = meetings()
        after = sheet.sign_up(sheet.sign_up(before, "2026-10-21", "Raj"), "2026-10-21", "Raj")
        self.assertEqual(after[0]["attendees"], ["Ivy", "Raj"])
        self.assertEqual(after[1]["attendees"], [])
        self.assertEqual(before, meetings())

    def test_withdraw_removes_the_name(self):
        self.assertEqual(sheet.withdraw(meetings(), "2026-10-21", "Ivy")[0]["attendees"], [])

    def test_suggest_adds_a_book(self):
        self.assertEqual(sheet.suggest(meetings(), "2026-10-21", "Book three")[0]["suggestions"], ["Book three"])


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_views.py <<'EOF'
import unittest

from club import views


class ViewsTest(unittest.TestCase):
    def test_sheet_lists_attendees_with_sign_up_and_remove(self):
        meeting = {"date": "2026-10-21", "book": "Book one", "place": "Library", "attendees": ["Ivy", "Raj"], "suggestions": []}
        page = views.render_sheet(meeting)
        self.assertIn("Coming (2)", page)
        self.assertEqual(page.count('action="/withdraw"'), 2)
        self.assertIn('action="/sign-up"', page)

    def test_sheet_without_a_meeting_says_so(self):
        self.assertIn("No meeting is planned yet.", views.render_sheet(None))


if __name__ == "__main__":
    unittest.main()
EOF

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Page Turners sign-up sheet"
