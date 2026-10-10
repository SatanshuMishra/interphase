#!/usr/bin/env bash
set -euo pipefail

mkdir -p portal tests

cat > README.md <<'EOF'
# Riverside Clinic Patient Portal

The Riverside Clinic Patient Portal is a patient portal for a medical clinic. Patients see their upcoming appointments, book or cancel an appointment, and read their test results.

The app keeps every patient, with their appointments and test results, in `patients.json`. The patients in it are made up. No sign-in exists yet: each page shows the patient whose number is in the address.

Start the app with `python3 -m portal.server` and open http://localhost:8000/patient?number=P-1001.

The app uses only the Python 3 standard library. Its tests run with `python3 -m unittest discover tests`.
EOF

cat > patients.json <<'EOF'
[
  {
    "number": "P-1001",
    "name": "Hana Ruiz",
    "born": "1984-03-12",
    "appointments": [
      {"when": "2026-10-14T09:30", "with": "Dr Hale", "reason": "Annual check-up"}
    ],
    "results": [
      {"date": "2026-09-20", "test": "Full blood count", "summary": "Within the normal range."}
    ]
  },
  {
    "number": "P-1002",
    "name": "Owen Pike",
    "born": "1979-11-02",
    "appointments": [],
    "results": [
      {"date": "2026-09-27", "test": "Cholesterol", "summary": "Slightly raised. Discuss at your next visit."}
    ]
  }
]
EOF

: > portal/__init__.py

cat > portal/records.py <<'EOF'
import json
import pathlib


def load(path):
    file = pathlib.Path(path)
    if not file.exists():
        return []
    return json.loads(file.read_text(encoding="utf-8"))


def save(path, patients):
    pathlib.Path(path).write_text(json.dumps(patients, indent=2) + "\n", encoding="utf-8")
    return patients


def find(patients, number):
    return next((patient for patient in patients if patient["number"] == number), None)


def upcoming(patient, now):
    return sorted(
        (appointment for appointment in patient["appointments"] if appointment["when"] >= now),
        key=lambda appointment: appointment["when"],
    )


def appointment(when, clinician, reason):
    return {"when": when, "with": clinician, "reason": reason}


def book(patients, number, booked):
    return [
        dict(patient, appointments=patient["appointments"] + [booked]) if patient["number"] == number else patient
        for patient in patients
    ]


def cancel(patients, number, when):
    return [
        dict(patient, appointments=[item for item in patient["appointments"] if item["when"] != when])
        if patient["number"] == number
        else patient
        for patient in patients
    ]
EOF

cat > portal/views.py <<'EOF'
import html

from portal import records


def appointment_item(number, item):
    return (
        "<li>{} with {}: {}"
        '<form method="post" action="/cancel">'
        '<input type="hidden" name="number" value="{}">'
        '<input type="hidden" name="when" value="{}">'
        '<button type="submit">Cancel</button>'
        "</form>"
        "</li>"
    ).format(
        html.escape(item["when"]),
        html.escape(item["with"]),
        html.escape(item["reason"]),
        html.escape(number),
        html.escape(item["when"]),
    )


def result_item(result):
    return "<li>{} {}: {}</li>".format(
        html.escape(result["date"]), html.escape(result["test"]), html.escape(result["summary"])
    )


def book_form(number):
    return (
        '<form method="post" action="/book">'
        '<input type="hidden" name="number" value="{}">'
        '<input name="when" type="datetime-local">'
        '<input name="reason" placeholder="Reason for the visit">'
        '<button type="submit">Book appointment</button>'
        "</form>"
    ).format(html.escape(number))


def render_patient(patient, now):
    appointments = "".join(appointment_item(patient["number"], item) for item in records.upcoming(patient, now))
    results = "".join(result_item(result) for result in patient["results"])
    return (
        "<!doctype html>"
        "<html><head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Riverside Clinic</title>"
        "</head><body>"
        "<h1>Riverside Clinic</h1>"
        "<p>{}</p>"
        "<h2>Upcoming appointments</h2><ul>{}</ul>"
        "{}"
        "<h2>Test results</h2><ul>{}</ul>"
        "</body></html>"
    ).format(html.escape(patient["name"]), appointments, book_form(patient["number"]), results)
EOF

cat > portal/server.py <<'EOF'
import datetime
import http.server
import pathlib
import sys
import urllib.parse

from portal import records, views

PATIENTS_FILE = pathlib.Path(__file__).resolve().parent.parent / "patients.json"
CLINICIAN = "Dr Hale"


def query_value(query, key):
    return urllib.parse.parse_qs(query).get(key, [""])[0]


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

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def read_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        return form_fields(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        patient = records.find(records.load(PATIENTS_FILE), query_value(url.query, "number"))
        if url.path != "/patient" or patient is None:
            self.send_error(404)
            return
        now = datetime.datetime.now().isoformat(timespec="minutes")
        self.send_page(views.render_patient(patient, now))

    def do_POST(self):
        if self.path not in ("/book", "/cancel"):
            self.send_error(404)
            return
        fields = self.read_form()
        number = fields.get("number", "")
        patients = records.load(PATIENTS_FILE)
        if records.find(patients, number) is None or not fields.get("when"):
            self.send_error(400)
            return
        if self.path == "/book":
            booked = records.appointment(fields["when"], CLINICIAN, fields.get("reason", ""))
            records.save(PATIENTS_FILE, records.book(patients, number, booked))
        else:
            records.save(PATIENTS_FILE, records.cancel(patients, number, fields["when"]))
        self.redirect("/patient?number=" + urllib.parse.quote(number))


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

from portal import records


def patients():
    return [
        {
            "number": "P-2001",
            "name": "Ivy Moss",
            "born": "1990-01-01",
            "appointments": [
                records.appointment("2026-10-01T10:00", "Dr Hale", "Follow-up"),
                records.appointment("2026-10-20T11:00", "Dr Hale", "Vaccination"),
            ],
            "results": [],
        },
        {"number": "P-2002", "name": "Raj Patel", "born": "1975-06-30", "appointments": [], "results": []},
    ]


class RecordsTest(unittest.TestCase):
    def test_saved_patients_load_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "patients.json"
            records.save(path, patients())
            self.assertEqual(records.load(path), patients())

    def test_upcoming_leaves_out_past_appointments(self):
        upcoming = records.upcoming(patients()[0], "2026-10-09T09:00")
        self.assertEqual([item["reason"] for item in upcoming], ["Vaccination"])

    def test_book_adds_the_appointment_to_that_patient_only(self):
        before = patients()
        after = records.book(before, "P-2002", records.appointment("2026-10-30T15:00", "Dr Hale", "Check-up"))
        self.assertEqual(len(after[1]["appointments"]), 1)
        self.assertEqual(len(after[0]["appointments"]), 2)
        self.assertEqual(before, patients())

    def test_cancel_removes_the_appointment(self):
        after = records.cancel(patients(), "P-2001", "2026-10-20T11:00")
        self.assertEqual([item["reason"] for item in after[0]["appointments"]], ["Follow-up"])


if __name__ == "__main__":
    unittest.main()
EOF

cat > tests/test_views.py <<'EOF'
import unittest

from portal import records, views


class ViewsTest(unittest.TestCase):
    def test_patient_page_shows_appointments_and_results(self):
        patient = {
            "number": "P-2001",
            "name": "Ivy Moss",
            "born": "1990-01-01",
            "appointments": [records.appointment("2026-10-20T11:00", "Dr Hale", "Vaccination")],
            "results": [{"date": "2026-09-20", "test": "Full blood count", "summary": "Within the normal range."}],
        }
        page = views.render_patient(patient, "2026-10-09T09:00")
        self.assertIn("Vaccination", page)
        self.assertIn('action="/cancel"', page)
        self.assertIn("Full blood count", page)


if __name__ == "__main__":
    unittest.main()
EOF

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Riverside Clinic patient portal"
