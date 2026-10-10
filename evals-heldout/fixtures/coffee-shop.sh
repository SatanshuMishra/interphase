#!/usr/bin/env bash
set -euo pipefail

mkdir -p loyalty tests

cat > README.md <<'EOF'
# Bean There

Bean There is a loyalty app for one independent coffee shop with a single location and about 300 regular customers. Customers open it on their phones to see their stamp count, and staff add stamps at the counter. Every tenth stamp earns a free coffee.

The app keeps every customer and their stamps in `customers.json`. No sign-in exists yet: a customer's card opens from its card number in the address, and the counter page is open to anyone.

Start the app with `python3 -m loyalty.server` and open http://localhost:8000/counter.

The app uses only the Python 3 standard library. Its tests run with `python3 -m unittest discover tests`.
EOF

cat > customers.json <<'EOF'
[
  {
    "card": "1001",
    "name": "Hana Ruiz",
    "email": "hana@example.com",
    "stamps": 7
  },
  {
    "card": "1002",
    "name": "Owen Pike",
    "email": "owen@example.com",
    "stamps": 2
  },
  {
    "card": "1003",
    "name": "Lola Mendes",
    "email": "lola@example.com",
    "stamps": 19
  }
]
EOF

: > loyalty/__init__.py

cat > loyalty/store.py <<'EOF'
import json
import pathlib

FIELDS = ("card", "name", "email", "stamps")
STAMPS_PER_FREE_COFFEE = 10


def load(path):
    file = pathlib.Path(path)
    if not file.exists():
        return []
    return json.loads(file.read_text(encoding="utf-8"))


def save(path, customers):
    pathlib.Path(path).write_text(json.dumps(customers, indent=2) + "\n", encoding="utf-8")
    return customers


def new_customer(card, name, email):
    return {"card": card, "name": name, "email": email, "stamps": 0}


def find(customers, card):
    return next((customer for customer in customers if customer["card"] == card), None)


def add_stamp(customers, card):
    return [
        dict(customer, stamps=customer["stamps"] + 1) if customer["card"] == card else customer
        for customer in customers
    ]


def stamps_to_free_coffee(customer):
    return STAMPS_PER_FREE_COFFEE - customer["stamps"] % STAMPS_PER_FREE_COFFEE
EOF

cat > loyalty/views.py <<'EOF'
import html

from loyalty import store


def page(title, body):
    return (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>{}</title>"
        "</head><body>{}</body></html>"
    ).format(html.escape(title), body)


def render_card(customer):
    return page(
        "Bean There",
        "<h1>Bean There</h1>"
        "<p>Hello, {}.</p>"
        "<p>You have {} stamps.</p>"
        "<p>{} more until your next free coffee.</p>".format(
            html.escape(customer["name"]),
            customer["stamps"],
            store.stamps_to_free_coffee(customer),
        ),
    )


def counter_row(customer):
    return (
        "<li>{} {}: {} stamps"
        '<form method="post" action="/stamp">'
        '<input type="hidden" name="card" value="{}">'
        '<button type="submit">Add stamp</button>'
        "</form>"
        "</li>"
    ).format(
        html.escape(customer["card"]),
        html.escape(customer["name"]),
        customer["stamps"],
        html.escape(customer["card"]),
    )


def render_counter(customers):
    rows = "".join(counter_row(customer) for customer in customers)
    return page("Bean There counter", "<h1>Counter</h1><ul>" + rows + "</ul>")
EOF

cat > loyalty/server.py <<'EOF'
import http.server
import pathlib
import sys
import urllib.parse

from loyalty import store, views

CUSTOMERS_FILE = pathlib.Path(__file__).resolve().parent.parent / "customers.json"


def query_value(query, key):
    return urllib.parse.parse_qs(query).get(key, [""])[0]


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

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def read_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        return form_fields(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        customers = store.load(CUSTOMERS_FILE)
        if url.path == "/counter":
            self.send_page(views.render_counter(customers))
            return
        if url.path == "/card":
            customer = store.find(customers, query_value(url.query, "number"))
            if customer:
                self.send_page(views.render_card(customer))
                return
        self.send_error(404)

    def do_POST(self):
        if self.path == "/stamp":
            card = self.read_form().get("card", "")
            store.save(CUSTOMERS_FILE, store.add_stamp(store.load(CUSTOMERS_FILE), card))
            self.redirect("/counter")
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

from loyalty import store


class StoreTest(unittest.TestCase):
    def test_saved_customers_load_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "customers.json"
            customers = [store.new_customer("2001", "Ivy Moss", "ivy@example.com")]
            store.save(path, customers)
            self.assertEqual(store.load(path), customers)

    def test_new_customer_has_every_field_and_no_stamps(self):
        customer = store.new_customer("2001", "Ivy Moss", "ivy@example.com")
        self.assertEqual(tuple(customer), store.FIELDS)
        self.assertEqual(customer["stamps"], 0)

    def test_add_stamp_adds_one_to_that_card_only(self):
        customers = [
            store.new_customer("2001", "Ivy Moss", "ivy@example.com"),
            store.new_customer("2002", "Raj Patel", "raj@example.com"),
        ]
        stamped = store.add_stamp(customers, "2002")
        self.assertEqual([customer["stamps"] for customer in stamped], [0, 1])
        self.assertEqual([customer["stamps"] for customer in customers], [0, 0])

    def test_every_tenth_stamp_earns_a_free_coffee(self):
        customer = dict(store.new_customer("2001", "Ivy Moss", "ivy@example.com"), stamps=13)
        self.assertEqual(store.stamps_to_free_coffee(customer), 7)


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_views.py <<'EOF'
import unittest

from loyalty import store, views


class ViewsTest(unittest.TestCase):
    def test_card_shows_the_stamp_count(self):
        customer = dict(store.new_customer("2001", "Ivy Moss", "ivy@example.com"), stamps=4)
        page = views.render_card(customer)
        self.assertIn("You have 4 stamps.", page)
        self.assertIn("6 more until your next free coffee.", page)

    def test_counter_has_an_add_stamp_button_per_customer(self):
        customers = [
            store.new_customer("2001", "Ivy Moss", "ivy@example.com"),
            store.new_customer("2002", "Raj Patel", "raj@example.com"),
        ]
        page = views.render_counter(customers)
        self.assertEqual(page.count('action="/stamp"'), 2)
        self.assertEqual(page.count(">Add stamp</button>"), 2)


if __name__ == "__main__":
    unittest.main()
EOF

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Bean There loyalty app"
