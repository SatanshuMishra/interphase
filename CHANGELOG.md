# Changelog

## 0.16.1

- lock_feasibility.py passes a locked row an earlier Step already built when an amendment adds a Step, without running its absent check again. A row counts as built when its Step carries a lower amendment number than the newest in the record and its test's name is in its locked file at HEAD. 0.16.0 judged every row against HEAD on every run, so after a build an amendment's run refused each built row, as no absent though every load exists at HEAD or as already passing on today's code, and the only way through was a false absent entry. A row the amendment adds, and a row no build has delivered, are judged as before.
- The feasibility digest covers each Step's amendment number, so a number changed after the run makes the stored results stale.
- lock_feasibility.py reads a relative --repo path from the folder it was started in. It named the folder to git twice, as the working folder and as -C, so any relative path but . was looked up under itself and refused as unreadable with exit 2.

## 0.16.0

- lock_feasibility.py checks each test before it is locked: every file it loads exists or is written by its Step or an earlier one, the files it needs are in those write-sets, it fails on today's code, and every existing test that refers to a changed file is owned by a Step or named unaffected. The record stores the results with a digest of the parts they judge.
- render_record.py refuses a record whose feasibility results are missing, stale or failed.
- render_record.py writes one check-author per MSP, so an MSP's tree holds only its own locked tests and those of the MSPs it builds on; a locked helper goes to the check-author of the tests that load it.
- check_items.py refuses a Step whose acceptance file another MSP's check-author writes, and reads a check-author named check-author as the unlabelled one whatever its msp.
- The check-author's task requires a passing probe implementation inside the row's write-sets and a failure by assertion, never by a harness crash.

## 0.15.0

- interphase now vendors the harness program's validator and its H11 (interview record), H12 (items file), K1, K2 and K6 schemas in contracts/, as byte-identical copies, and drops scripts/schema_check.py.
- render_record.py checks the record against H11 and check_record, and the items against H12 and check_items, before writing either, and writes nothing when a check fails. This also refuses an amendment whose check-author Step would have no files.
- surface_probe.py and outcomes.py check the record before they rewrite it.
- Each acceptance entry in the items file carries its test's acceptance line id as check.
- outcomes.py reads the trajectory store through K6 and reports each line that fails.
- read_back.py and the resume hook refuse a record that fails H11.
