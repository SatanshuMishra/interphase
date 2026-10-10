#!/usr/bin/env bash
set -euo pipefail

mkdir -p rota tests

cat > README.md <<'EOF'
# Plot Rota

Plot Rota is the watering rota for the Harbour Lane Allotment Society, about 40 gardeners who share one water tank. Members see the evenings they water the shared beds and swap an evening with another member.

The app keeps every member and their evenings in `members.json`. No sign-in exists yet: each page shows the member whose number is in the address.

Start the app with `python3 -m rota.server` and open http://localhost:8000/member?number=M-01.

The app uses only the Python 3 standard library. Its tests run with `python3 -m unittest discover tests`.
EOF

cat > members.json <<'EOF'
[
  {"number": "M-01", "name": "Hana Ruiz", "email": "hana@example.com", "plot": 4, "evenings": ["2026-10-13", "2026-10-27"]},
  {"number": "M-02", "name": "Owen Pike", "email": "owen@example.com", "plot": 11, "evenings": ["2026-10-14"]},
  {"number": "M-03", "name": "Lola Mendes", "email": "lola@example.com", "plot": 17, "evenings": ["2026-10-20"]}
]
EOF

: > rota/__init__.py

cat > rota/store.py <<'EOF'
import json
import pathlib


def load(path):
    file = pathlib.Path(path)
    if not file.exists():
        return []
    return json.loads(file.read_text(encoding="utf-8"))


def save(path, members):
    pathlib.Path(path).write_text(json.dumps(members, indent=2) + "\n", encoding="utf-8")
    return members


def find(members, number):
    return next((member for member in members if member["number"] == number), None)


def swapped(member, giver, taker, evening):
    if member["number"] == giver:
        return dict(member, evenings=[day for day in member["evenings"] if day != evening])
    if member["number"] == taker:
        return dict(member, evenings=sorted(member["evenings"] + [evening]))
    return member


def swap(members, giver, taker, evening):
    owner = find(members, giver)
    if owner is None or find(members, taker) is None:
        raise ValueError("Unknown member")
    if giver == taker:
        raise ValueError("Choose another member")
    if evening not in owner["evenings"]:
        raise ValueError("That evening is not yours to swap")
    return [swapped(member, giver, taker, evening) for member in members]
EOF

cat > rota/views.py <<'EOF'
import html


def evening_item(member, evening):
    return (
        "<li>{}"
        '<form method="post" action="/swap">'
        '<input type="hidden" name="from" value="{}">'
        '<input type="hidden" name="evening" value="{}">'
        '<input name="to" placeholder="Member number">'
        '<button type="submit">Swap</button>'
        "</form>"
        "</li>"
    ).format(html.escape(evening), html.escape(member["number"]), html.escape(evening))


def render_member(member, message=""):
    items = "".join(evening_item(member, evening) for evening in member["evenings"])
    notice = "<p>{}</p>".format(html.escape(message)) if message else ""
    return (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Plot Rota</title>"
        "</head><body>"
        "<h1>Plot Rota</h1>"
        "<p>{}, plot {}</p>"
        "{}"
        "<h2>Your watering evenings</h2>"
        "<ul>{}</ul>"
        "</body></html>"
    ).format(html.escape(member["name"]), member["plot"], notice, items)
EOF

cat > rota/server.py <<'EOF'
import http.server
import pathlib
import sys
import urllib.parse

from rota import store, views

MEMBERS_FILE = pathlib.Path(__file__).resolve().parent.parent / "members.json"


def query_value(query, key):
    return urllib.parse.parse_qs(query).get(key, [""])[0]


def form_fields(body):
    fields = urllib.parse.parse_qs(body, keep_blank_values=True)
    return {key: values[0] for key, values in fields.items()}


class Handler(http.server.BaseHTTPRequestHandler):
    def send_page(self, text, status=200):
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def read_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        return form_fields(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        member = store.find(store.load(MEMBERS_FILE), query_value(url.query, "number"))
        if url.path != "/member" or member is None:
            self.send_error(404)
            return
        self.send_page(views.render_member(member))

    def do_POST(self):
        if self.path != "/swap":
            self.send_error(404)
            return
        fields = self.read_form()
        giver = fields.get("from", "")
        members = store.load(MEMBERS_FILE)
        member = store.find(members, giver)
        if member is None:
            self.send_error(404)
            return
        try:
            updated = store.swap(members, giver, fields.get("to", "").strip(), fields.get("evening", ""))
        except ValueError as error:
            self.send_page(views.render_member(member, str(error)), 400)
            return
        store.save(MEMBERS_FILE, updated)
        self.redirect("/member?number=" + urllib.parse.quote(giver))


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

from rota import store


def members():
    return [
        {"number": "M-91", "name": "Ivy Moss", "email": "ivy@example.com", "plot": 2, "evenings": ["2026-10-13"]},
        {"number": "M-92", "name": "Raj Patel", "email": "raj@example.com", "plot": 9, "evenings": []},
    ]


class StoreTest(unittest.TestCase):
    def test_saved_members_load_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "members.json"
            store.save(path, members())
            self.assertEqual(store.load(path), members())

    def test_swap_moves_the_evening_to_the_other_member(self):
        before = members()
        after = store.swap(before, "M-91", "M-92", "2026-10-13")
        self.assertEqual([member["evenings"] for member in after], [[], ["2026-10-13"]])
        self.assertEqual(before, members())

    def test_swap_refuses_an_evening_that_is_not_theirs(self):
        with self.assertRaises(ValueError):
            store.swap(members(), "M-92", "M-91", "2026-10-13")


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_views.py <<'EOF'
import unittest

from rota import views


class ViewsTest(unittest.TestCase):
    def test_member_page_lists_each_evening_with_a_swap_form(self):
        member = {"number": "M-91", "name": "Ivy Moss", "email": "ivy@example.com", "plot": 2, "evenings": ["2026-10-13", "2026-10-27"]}
        page = views.render_member(member)
        self.assertIn("Ivy Moss, plot 2", page)
        self.assertEqual(page.count('action="/swap"'), 2)


if __name__ == "__main__":
    unittest.main()
EOF

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Plot Rota"
