#!/usr/bin/env bash
set -euo pipefail

mkdir -p payroll tests

cat > README.md <<'EOF'
# Brightwater Pay

Brightwater Pay is the payroll portal for Brightwater Staffing, an agency that pays about 1,200 temporary workers every week. Workers read their payslips, which show their pay, their tax and their National Insurance number, and change the bank account their pay goes to.

The app keeps every worker, with their bank details and payslips, in `workers.json`. The workers in it are made up. No sign-in exists yet: each page shows the worker whose number is in the address.

Start the app with `python3 -m payroll.server` and open http://localhost:8000/worker?number=W-2001.

The app uses only the Python 3 standard library. Its tests run with `python3 -m unittest discover tests`.
EOF

cat > workers.json <<'EOF'
[
  {
    "number": "W-2001",
    "name": "Hana Ruiz",
    "insurance_number": "QQ123456C",
    "sort_code": "11-22-33",
    "account_number": "41006781",
    "payslips": [
      {"week_ending": "2026-10-02", "gross": 61250, "tax": 6930, "insurance": 3410, "net": 50910}
    ]
  },
  {
    "number": "W-2002",
    "name": "Owen Pike",
    "insurance_number": "QQ654321A",
    "sort_code": "44-55-66",
    "account_number": "72019934",
    "payslips": [
      {"week_ending": "2026-10-02", "gross": 48000, "tax": 4280, "insurance": 2150, "net": 41570}
    ]
  }
]
EOF

: > payroll/__init__.py

cat > payroll/records.py <<'EOF'
import json
import pathlib
import re

SORT_CODE = re.compile(r"^\d{2}-\d{2}-\d{2}$")
ACCOUNT_NUMBER = re.compile(r"^\d{8}$")


def load(path):
    file = pathlib.Path(path)
    if not file.exists():
        return []
    return json.loads(file.read_text(encoding="utf-8"))


def save(path, workers):
    pathlib.Path(path).write_text(json.dumps(workers, indent=2) + "\n", encoding="utf-8")
    return workers


def find(workers, number):
    return next((worker for worker in workers if worker["number"] == number), None)


def format_pay(pence):
    return "GBP {:,}.{:02d}".format(pence // 100, pence % 100)


def change_bank(workers, number, sort_code, account_number):
    if find(workers, number) is None:
        raise ValueError("Unknown worker")
    if not SORT_CODE.match(sort_code):
        raise ValueError("Enter a sort code such as 12-34-56")
    if not ACCOUNT_NUMBER.match(account_number):
        raise ValueError("Enter an 8-digit account number")
    return [
        dict(worker, sort_code=sort_code, account_number=account_number) if worker["number"] == number else worker
        for worker in workers
    ]
EOF

cat > payroll/views.py <<'EOF'
import html

from payroll import records


def payslip_row(payslip):
    return "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
        html.escape(payslip["week_ending"]),
        records.format_pay(payslip["gross"]),
        records.format_pay(payslip["tax"]),
        records.format_pay(payslip["insurance"]),
        records.format_pay(payslip["net"]),
    )


def bank_form(worker):
    return (
        '<form method="post" action="/bank">'
        '<input type="hidden" name="number" value="{}">'
        '<input name="sort_code" placeholder="Sort code">'
        '<input name="account_number" placeholder="Account number">'
        '<button type="submit">Change bank account</button>'
        "</form>"
    ).format(html.escape(worker["number"]))


def render_worker(worker, message=""):
    rows = "".join(payslip_row(payslip) for payslip in worker["payslips"])
    notice = "<p>{}</p>".format(html.escape(message)) if message else ""
    return (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Brightwater Pay</title>"
        "</head><body>"
        "<h1>Brightwater Pay</h1>"
        "<p>{} ({})</p>"
        "<p>National Insurance number: {}</p>"
        "<p>Pay goes to sort code {}, account {}</p>"
        "{}"
        "<table><tr><th>Week ending</th><th>Gross</th><th>Tax</th><th>National Insurance</th><th>Net</th></tr>{}</table>"
        "{}"
        "</body></html>"
    ).format(
        html.escape(worker["name"]),
        html.escape(worker["number"]),
        html.escape(worker["insurance_number"]),
        html.escape(worker["sort_code"]),
        html.escape(worker["account_number"]),
        notice,
        rows,
        bank_form(worker),
    )
EOF

cat > payroll/server.py <<'EOF'
import http.server
import pathlib
import sys
import urllib.parse

from payroll import records, views

WORKERS_FILE = pathlib.Path(__file__).resolve().parent.parent / "workers.json"


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
        worker = records.find(records.load(WORKERS_FILE), query_value(url.query, "number"))
        if url.path != "/worker" or worker is None:
            self.send_error(404)
            return
        self.send_page(views.render_worker(worker))

    def do_POST(self):
        if self.path != "/bank":
            self.send_error(404)
            return
        fields = self.read_form()
        number = fields.get("number", "")
        workers = records.load(WORKERS_FILE)
        worker = records.find(workers, number)
        if worker is None:
            self.send_error(404)
            return
        try:
            updated = records.change_bank(
                workers, number, fields.get("sort_code", "").strip(), fields.get("account_number", "").strip()
            )
        except ValueError as error:
            self.send_page(views.render_worker(worker, str(error)), 400)
            return
        records.save(WORKERS_FILE, updated)
        self.redirect("/worker?number=" + urllib.parse.quote(number))


def main(argv):
    port = int(argv[0]) if argv else 8000
    server = http.server.HTTPServer(("", port), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
EOF

cat > tests/test_records.py <<'EOF'
import pathlib
import tempfile
import unittest

from payroll import records


def workers():
    return [
        {
            "number": "W-0001",
            "name": "Ivy Moss",
            "insurance_number": "QQ111111A",
            "sort_code": "10-20-30",
            "account_number": "12345678",
            "payslips": [],
        },
        {
            "number": "W-0002",
            "name": "Raj Patel",
            "insurance_number": "QQ222222B",
            "sort_code": "40-50-60",
            "account_number": "87654321",
            "payslips": [],
        },
    ]


class RecordsTest(unittest.TestCase):
    def test_saved_workers_load_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "workers.json"
            records.save(path, workers())
            self.assertEqual(records.load(path), workers())

    def test_change_bank_changes_that_worker_only(self):
        before = workers()
        after = records.change_bank(before, "W-0002", "99-88-77", "11112222")
        self.assertEqual((after[1]["sort_code"], after[1]["account_number"]), ("99-88-77", "11112222"))
        self.assertEqual(after[0], before[0])
        self.assertEqual(before, workers())

    def test_change_bank_refuses_bad_details(self):
        with self.assertRaises(ValueError):
            records.change_bank(workers(), "W-0001", "102030", "12345678")
        with self.assertRaises(ValueError):
            records.change_bank(workers(), "W-0001", "10-20-30", "1234")
        with self.assertRaises(ValueError):
            records.change_bank(workers(), "W-9999", "10-20-30", "12345678")

    def test_pay_formats_in_pence(self):
        self.assertEqual(records.format_pay(50910), "GBP 509.10")


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_views.py <<'EOF'
import unittest

from payroll import views


class ViewsTest(unittest.TestCase):
    def test_worker_page_shows_payslips_and_the_bank_form(self):
        worker = {
            "number": "W-0001",
            "name": "Ivy Moss",
            "insurance_number": "QQ111111A",
            "sort_code": "10-20-30",
            "account_number": "12345678",
            "payslips": [{"week_ending": "2026-10-02", "gross": 61250, "tax": 6930, "insurance": 3410, "net": 50910}],
        }
        page = views.render_worker(worker)
        self.assertIn("National Insurance number: QQ111111A", page)
        self.assertIn("GBP 509.10", page)
        self.assertIn('action="/bank"', page)


if __name__ == "__main__":
    unittest.main()
EOF

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Brightwater Pay"
