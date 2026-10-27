import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "metrics" / "catalogue.json"
SCHEMA = ROOT / "metrics" / "schema" / "catalogue.schema.json"
EVENTS = (
    "run.start",
    "round.recorded",
    "steps.checked",
    "readback.asked",
    "spec.rendered",
    "spec.checked",
    "items.checked",
    "review.done",
    "run.handoff",
)
SUMMARY_FIELDS = (
    "slug",
    "status",
    "pathway",
    "lane",
    "attended",
    "amends",
    "amendment",
    "lead_seconds",
    "wait_seconds",
    "phases",
    "sessions",
    "intent_lines",
    "rounds",
    "questions",
    "recommended",
    "changed",
    "readbacks",
    "approved",
    "decisions",
    "seams",
    "criteria",
    "tests",
    "unproven",
    "varying",
    "case_tables",
    "steps",
    "msps",
    "steps_with_assumptions",
    "assumptions",
    "assumptions_by_intent",
    "checks",
    "review_approved",
    "review_issues",
    "usd",
    "prices_date",
    "tokens",
    "models",
    "unpriced",
    "spend_scope",
)
OTHER_PLUGINS = ("mitosis", "lighthouse", "logbook", "pipeline")


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def filled(value):
    return value is not None and value != "" and value != [] and value != {}


def field_entries(name, entry):
    nested = tuple(
        pair
        for child, child_entry in entry.get("fields", {}).items()
        for pair in field_entries(name + "." + child, child_entry)
    )
    items = field_entries(name + "[]", entry["items"]) if "items" in entry else ()
    return ((name, entry),) + nested + items


def every_field(catalogue):
    from_events = tuple(
        pair
        for event, description in catalogue["events"].items()
        for name, entry in description.get("fields", {}).items()
        for pair in field_entries("event." + event + "." + name, entry)
    )
    from_summary = tuple(
        pair
        for name, entry in catalogue["summary"]["fields"].items()
        for pair in field_entries("summary." + name, entry)
    )
    return from_events + from_summary


def described(catalogue, reference):
    if reference.startswith("summary."):
        return reference[len("summary."):] in catalogue["summary"]["fields"]
    if reference.startswith("event."):
        event, _, name = reference[len("event."):].rpartition(".")
        return name in catalogue["events"].get(event, {}).get("fields", {})
    return False


class MetricsCatalogueTest(unittest.TestCase):
    def test_catalogue_has_schema_keys(self):
        catalogue = read_json(CATALOGUE)
        schema = read_json(SCHEMA)
        for key in schema["required"]:
            with self.subTest(key=key):
                self.assertIn(key, catalogue)
                self.assertTrue(filled(catalogue[key]), key)
        self.assertEqual(catalogue["format"], 1)
        self.assertEqual(catalogue["plugin"], "interphase")
        required = schema["$defs"]["field"]["required"]
        kinds = schema["$defs"]["field"]["properties"]["type"]["enum"]
        units = schema["$defs"]["field"]["properties"]["unit"]["enum"]
        fields = every_field(catalogue)
        self.assertGreater(len(fields), len(SUMMARY_FIELDS))
        for name, entry in fields:
            with self.subTest(field=name):
                for key in required:
                    self.assertIn(key, entry)
                    self.assertTrue(filled(entry[key]), key)
                self.assertIn(entry["type"], kinds)
                self.assertIn(entry["unit"], units)
                if entry["type"] == "enum":
                    self.assertTrue(filled(entry.get("values")))

    def test_objectives_name_described_fields(self):
        catalogue = read_json(CATALOGUE)
        objectives = catalogue["objectives"]
        self.assertGreaterEqual(len(objectives), 7)
        for objective in objectives:
            with self.subTest(objective=objective.get("id")):
                self.assertTrue(filled(objective.get("id")))
                self.assertTrue(filled(objective.get("text")))
                self.assertTrue(filled(objective.get("measured_by")))
                for reference in objective["measured_by"]:
                    self.assertTrue(described(catalogue, reference), reference)

    def test_every_event_and_summary_field_listed(self):
        catalogue = read_json(CATALOGUE)
        self.assertEqual(tuple(catalogue["events"]), EVENTS)
        self.assertEqual(tuple(catalogue["summary"]["fields"]), SUMMARY_FIELDS)

    def test_catalogue_names_no_other_plugin(self):
        text = CATALOGUE.read_text(encoding="utf-8").lower()
        for name in OTHER_PLUGINS:
            with self.subTest(name=name):
                self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
