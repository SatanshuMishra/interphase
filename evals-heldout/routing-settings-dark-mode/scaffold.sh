#!/usr/bin/env bash
set -euo pipefail

mkdir -p invoices tests

cat > README.md <<'EOF'
# Invoices

Invoices is a small web app a freelance designer uses to keep track of the invoices they send to clients.

The invoices page lists every invoice with its client, amount, due date and whether it is paid. The settings screen holds the business name, the currency and the payment terms in days.

The app keeps invoices in `invoices.json` and settings in `settings.json`. Start it with `python3 -m invoices.server` and open http://localhost:8000/invoices.

The app uses only the Python 3 standard library. Its tests run with `python3 -m unittest discover tests`.
EOF

cat > invoices.json <<'EOF'
[
  {"number": "INV-001", "client": "Harbour Books", "amount": 120000, "due": "2026-09-30", "paid": true},
  {"number": "INV-002", "client": "Green Lane Cafe", "amount": 45000, "due": "2026-10-15", "paid": false},
  {"number": "INV-003", "client": "Northfield Studio", "amount": 98050, "due": "2026-10-31", "paid": false}
]
EOF

cat > settings.json <<'EOF'
{
  "business_name": "Ada Lowe Design",
  "currency": "GBP",
  "payment_terms_days": 30
}
EOF

: > invoices/__init__.py

cat > invoices/store.py <<'EOF'
import json
import pathlib

CURRENCIES = ("GBP", "EUR", "USD")


def load(path, default):
    file = pathlib.Path(path)
    if not file.exists():
        return default
    return json.loads(file.read_text(encoding="utf-8"))


def save(path, data):
    pathlib.Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def outstanding(invoices):
    return [invoice for invoice in invoices if not invoice["paid"]]


def total(invoices):
    return sum(invoice["amount"] for invoice in invoices)


def updated_settings(settings, fields):
    name = fields.get("business_name", "").strip()
    currency = fields.get("currency", "")
    terms = fields.get("payment_terms_days", "").strip()
    if not name:
        raise ValueError("Business name is required")
    if currency not in CURRENCIES:
        raise ValueError("Choose GBP, EUR or USD")
    if not terms.isdigit():
        raise ValueError("Payment terms must be a whole number of days")
    return dict(settings, business_name=name, currency=currency, payment_terms_days=int(terms))
EOF

cat > invoices/views.py <<'EOF'
import html

from invoices import store


def format_amount(amount, currency):
    return "{} {:,}.{:02d}".format(currency, amount // 100, amount % 100)


def page(title, body):
    return (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>{0}</title>"
        "</head><body>"
        '<nav><a href="/invoices">Invoices</a> <a href="/settings">Settings</a></nav>'
        "<h1>{0}</h1>"
        "{1}"
        "</body></html>"
    ).format(html.escape(title), body)


def invoice_row(invoice, currency):
    status = "Paid" if invoice["paid"] else "Unpaid"
    return "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
        html.escape(invoice["number"]),
        html.escape(invoice["client"]),
        format_amount(invoice["amount"], currency),
        html.escape(invoice["due"]),
        status,
    )


def render_invoices(invoices, settings):
    currency = settings["currency"]
    rows = "".join(invoice_row(invoice, currency) for invoice in invoices)
    owed = format_amount(store.total(store.outstanding(invoices)), currency)
    body = (
        "<p>{}</p>"
        "<table>"
        "<tr><th>Number</th><th>Client</th><th>Amount</th><th>Due</th><th>Status</th></tr>"
        "{}"
        "</table>"
        "<p>Outstanding: {}</p>"
    ).format(html.escape(settings["business_name"]), rows, owed)
    return page("Invoices", body)


def currency_option(code, chosen):
    selected = " selected" if code == chosen else ""
    return '<option value="{0}"{1}>{0}</option>'.format(code, selected)


def render_settings(settings, message=""):
    options = "".join(currency_option(code, settings["currency"]) for code in store.CURRENCIES)
    notice = "<p>{}</p>".format(html.escape(message)) if message else ""
    body = (
        "{}"
        '<form method="post" action="/settings">'
        '<label>Business name <input name="business_name" value="{}"></label>'
        '<label>Currency <select name="currency">{}</select></label>'
        '<label>Payment terms in days <input name="payment_terms_days" value="{}"></label>'
        '<button type="submit">Save settings</button>'
        "</form>"
    ).format(notice, html.escape(settings["business_name"]), options, settings["payment_terms_days"])
    return page("Settings", body)
EOF

cat > invoices/server.py <<'EOF'
import http.server
import pathlib
import sys
import urllib.parse

from invoices import store, views

ROOT = pathlib.Path(__file__).resolve().parent.parent
INVOICES_FILE = ROOT / "invoices.json"
SETTINGS_FILE = ROOT / "settings.json"


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
        path = urllib.parse.urlsplit(self.path).path
        settings = store.load(SETTINGS_FILE, {})
        if path in ("/", "/invoices"):
            self.send_page(views.render_invoices(store.load(INVOICES_FILE, []), settings))
            return
        if path == "/settings":
            self.send_page(views.render_settings(settings))
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/settings":
            self.send_error(404)
            return
        settings = store.load(SETTINGS_FILE, {})
        try:
            updated = store.updated_settings(settings, self.read_form())
        except ValueError as error:
            self.send_page(views.render_settings(settings, str(error)), 400)
            return
        store.save(SETTINGS_FILE, updated)
        self.redirect("/settings")


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

from invoices import store


def invoices():
    return [
        {"number": "INV-101", "client": "Moss and Pine", "amount": 30000, "due": "2026-11-01", "paid": True},
        {"number": "INV-102", "client": "Tide Bakery", "amount": 12550, "due": "2026-11-15", "paid": False},
    ]


def settings():
    return {"business_name": "Ada Lowe Design", "currency": "GBP", "payment_terms_days": 30}


class StoreTest(unittest.TestCase):
    def test_saved_invoices_load_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "invoices.json"
            store.save(path, invoices())
            self.assertEqual(store.load(path, []), invoices())

    def test_outstanding_total_counts_only_unpaid_invoices(self):
        self.assertEqual(store.total(store.outstanding(invoices())), 12550)

    def test_settings_update_returns_a_new_copy(self):
        before = settings()
        fields = {"business_name": "Ada Lowe Studio", "currency": "EUR", "payment_terms_days": "14"}
        after = store.updated_settings(before, fields)
        self.assertEqual(after, {"business_name": "Ada Lowe Studio", "currency": "EUR", "payment_terms_days": 14})
        self.assertEqual(before, settings())

    def test_settings_update_refuses_terms_that_are_not_whole_days(self):
        fields = {"business_name": "Ada Lowe Design", "currency": "GBP", "payment_terms_days": "two weeks"}
        with self.assertRaises(ValueError):
            store.updated_settings(settings(), fields)


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_views.py <<'EOF'
import unittest

from invoices import views


def settings():
    return {"business_name": "Ada Lowe Design", "currency": "GBP", "payment_terms_days": 30}


class ViewsTest(unittest.TestCase):
    def test_invoices_page_lists_each_invoice_and_the_amount_outstanding(self):
        invoices = [
            {"number": "INV-201", "client": "Harbour Books", "amount": 120000, "due": "2026-09-30", "paid": True},
            {"number": "INV-202", "client": "Green Lane Cafe", "amount": 45000, "due": "2026-10-15", "paid": False},
        ]
        page = views.render_invoices(invoices, settings())
        self.assertIn("<h1>Invoices</h1>", page)
        self.assertIn("Harbour Books", page)
        self.assertIn("GBP 1,200.00", page)
        self.assertIn("Outstanding: GBP 450.00", page)

    def test_settings_screen_shows_the_current_settings(self):
        page = views.render_settings(settings())
        self.assertIn("<h1>Settings</h1>", page)
        self.assertIn('action="/settings"', page)
        self.assertIn('value="Ada Lowe Design"', page)
        self.assertIn('<option value="GBP" selected>GBP</option>', page)
        self.assertIn('name="payment_terms_days" value="30"', page)


if __name__ == "__main__":
    unittest.main()
EOF

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Invoices app"
