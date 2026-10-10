#!/usr/bin/env bash
set -euo pipefail

mkdir -p northbank tests

cat > README.md <<'EOF'
# Northbank Online

Northbank Online is online banking for Northbank, a regulated retail bank. Customers view their account balances and statements and send transfers to other Northbank accounts.

The app keeps every account and its transactions in `accounts.json`, with amounts in pence. No sign-in exists yet: each page shows the account whose number is in the address.

Start the app with `python3 -m northbank.server` and open http://localhost:8000/account?number=40001234.

The app uses only the Python 3 standard library. Its tests run with `python3 -m unittest discover tests`.
EOF

cat > accounts.json <<'EOF'
[
  {
    "number": "40001234",
    "holder": "Hana Ruiz",
    "balance": 152034,
    "transactions": [
      {"date": "2026-09-30", "description": "Salary", "amount": 210000},
      {"date": "2026-10-01", "description": "Rent", "amount": -95000}
    ]
  },
  {
    "number": "40005678",
    "holder": "Owen Pike",
    "balance": 48210,
    "transactions": [
      {"date": "2026-10-02", "description": "Card payment, grocer", "amount": -4790}
    ]
  }
]
EOF

: > northbank/__init__.py

cat > northbank/ledger.py <<'EOF'
import decimal
import json
import pathlib


def load(path):
    file = pathlib.Path(path)
    if not file.exists():
        return []
    return json.loads(file.read_text(encoding="utf-8"))


def save(path, accounts):
    pathlib.Path(path).write_text(json.dumps(accounts, indent=2) + "\n", encoding="utf-8")
    return accounts


def find(accounts, number):
    return next((account for account in accounts if account["number"] == number), None)


def format_amount(pence):
    sign = "-" if pence < 0 else ""
    return "{}GBP {:,}.{:02d}".format(sign, abs(pence) // 100, abs(pence) % 100)


def parse_amount(text):
    try:
        value = decimal.Decimal(text.strip()) * 100
    except decimal.InvalidOperation:
        raise ValueError("Enter an amount such as 12.50")
    if not value.is_finite() or value != value.to_integral_value():
        raise ValueError("Enter an amount such as 12.50")
    return int(value)


def entry(date, description, amount):
    return {"date": date, "description": description, "amount": amount}


def moved(account, source, target, amount, date):
    if account["number"] == source:
        line = entry(date, "Transfer to " + target, -amount)
        return dict(account, balance=account["balance"] - amount, transactions=account["transactions"] + [line])
    if account["number"] == target:
        line = entry(date, "Transfer from " + source, amount)
        return dict(account, balance=account["balance"] + amount, transactions=account["transactions"] + [line])
    return account


def transfer(accounts, source, target, amount, date):
    sender = find(accounts, source)
    if sender is None or find(accounts, target) is None:
        raise ValueError("Unknown account")
    if source == target:
        raise ValueError("Choose a different account")
    if amount <= 0:
        raise ValueError("The amount must be more than zero")
    if amount > sender["balance"]:
        raise ValueError("Insufficient funds")
    return [moved(account, source, target, amount, date) for account in accounts]
EOF

cat > northbank/views.py <<'EOF'
import html

from northbank import ledger


def statement_row(line):
    return "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
        html.escape(line["date"]),
        html.escape(line["description"]),
        ledger.format_amount(line["amount"]),
    )


def transfer_form(account):
    return (
        '<form method="post" action="/transfer">'
        '<input type="hidden" name="from" value="{}">'
        '<input name="to" placeholder="Account number">'
        '<input name="amount" placeholder="Amount">'
        '<button type="submit">Send transfer</button>'
        "</form>"
    ).format(html.escape(account["number"]))


def render_account(account, message=""):
    rows = "".join(statement_row(line) for line in account["transactions"])
    notice = "<p>{}</p>".format(html.escape(message)) if message else ""
    return (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Northbank Online</title>"
        "</head><body>"
        "<h1>Northbank Online</h1>"
        "<p>{} account {}</p>"
        "<p>Balance: {}</p>"
        "{}"
        "<table>{}</table>"
        "{}"
        "</body></html>"
    ).format(
        html.escape(account["holder"]),
        html.escape(account["number"]),
        ledger.format_amount(account["balance"]),
        notice,
        rows,
        transfer_form(account),
    )
EOF

cat > northbank/server.py <<'EOF'
import datetime
import http.server
import pathlib
import sys
import urllib.parse

from northbank import ledger, views

ACCOUNTS_FILE = pathlib.Path(__file__).resolve().parent.parent / "accounts.json"


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
        account = ledger.find(ledger.load(ACCOUNTS_FILE), query_value(url.query, "number"))
        if url.path != "/account" or account is None:
            self.send_error(404)
            return
        self.send_page(views.render_account(account))

    def do_POST(self):
        if self.path != "/transfer":
            self.send_error(404)
            return
        fields = self.read_form()
        source = fields.get("from", "")
        accounts = ledger.load(ACCOUNTS_FILE)
        account = ledger.find(accounts, source)
        if account is None:
            self.send_error(404)
            return
        today = datetime.date.today().isoformat()
        try:
            amount = ledger.parse_amount(fields.get("amount", ""))
            updated = ledger.transfer(accounts, source, fields.get("to", ""), amount, today)
        except ValueError as error:
            self.send_page(views.render_account(account, str(error)), 400)
            return
        ledger.save(ACCOUNTS_FILE, updated)
        self.redirect("/account?number=" + urllib.parse.quote(source))


def main(argv):
    port = int(argv[0]) if argv else 8000
    server = http.server.HTTPServer(("", port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
EOF

cat > tests/test_ledger.py <<'EOF'
import pathlib
import tempfile
import unittest

from northbank import ledger


def accounts():
    return [
        {"number": "40000001", "holder": "Ivy Moss", "balance": 10000, "transactions": []},
        {"number": "40000002", "holder": "Raj Patel", "balance": 500, "transactions": []},
    ]


class LedgerTest(unittest.TestCase):
    def test_saved_accounts_load_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "accounts.json"
            ledger.save(path, accounts())
            self.assertEqual(ledger.load(path), accounts())

    def test_transfer_moves_money_and_records_both_sides(self):
        before = accounts()
        after = ledger.transfer(before, "40000001", "40000002", 2550, "2026-10-09")
        self.assertEqual([account["balance"] for account in after], [7450, 3050])
        self.assertEqual(after[0]["transactions"][-1]["amount"], -2550)
        self.assertEqual(after[1]["transactions"][-1]["amount"], 2550)
        self.assertEqual(before, accounts())

    def test_transfer_refuses_more_than_the_balance(self):
        with self.assertRaises(ValueError):
            ledger.transfer(accounts(), "40000002", "40000001", 501, "2026-10-09")

    def test_transfer_refuses_an_unknown_account(self):
        with self.assertRaises(ValueError):
            ledger.transfer(accounts(), "40000001", "49999999", 100, "2026-10-09")

    def test_amounts_parse_and_format_in_pence(self):
        self.assertEqual(ledger.parse_amount("12.50"), 1250)
        self.assertEqual(ledger.format_amount(152034), "GBP 1,520.34")
        with self.assertRaises(ValueError):
            ledger.parse_amount("12.505")


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_views.py <<'EOF'
import unittest

from northbank import views


class ViewsTest(unittest.TestCase):
    def test_account_page_shows_balance_statement_and_transfer_form(self):
        account = {
            "number": "40000001",
            "holder": "Ivy Moss",
            "balance": 7450,
            "transactions": [{"date": "2026-10-09", "description": "Transfer to 40000002", "amount": -2550}],
        }
        page = views.render_account(account)
        self.assertIn("Balance: GBP 74.50", page)
        self.assertIn("Transfer to 40000002", page)
        self.assertIn('action="/transfer"', page)


if __name__ == "__main__":
    unittest.main()
EOF

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Northbank Online"
