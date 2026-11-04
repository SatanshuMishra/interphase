# Changelog

## 0.15.0

- interphase now vendors the harness program's validator and its H11 (interview record), H12 (items file), K1, K2 and K6 schemas in contracts/, as byte-identical copies, and drops scripts/schema_check.py.
- render_record.py checks the record against H11 and check_record, and the items against H12 and check_items, before writing either, and writes nothing when a check fails. This also refuses an amendment whose check-author Step would have no files.
- surface_probe.py and outcomes.py check the record before they rewrite it.
- Each acceptance entry in the items file carries its test's acceptance line id as check.
- outcomes.py reads the trajectory store through K6 and reports each line that fails.
- read_back.py and the resume hook refuse a record that fails H11.
