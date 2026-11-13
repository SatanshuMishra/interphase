# Changelog

## 0.17.0

- A spec places each behaviour at the seam of the part that owns it: the smallest unit whose public interface promises the behaviour, called with values inside the test runner's own process. A seam at the product's front door is kept for what the way in itself owns and for crossings: a way in the request adds on its success and one failure path, a failure kind or a guard it adds, each role a guard must deny, and a way in to a changed behaviour that no test crosses yet. Every other meeting point the request changes, such as an instruction file and the tool it names, gets its crossing too. Earlier releases asked for the seams the project already tests at and the highest seam that observes the behaviour, with one seam as the ideal, so every case of a decision was specified as a test that starts the whole product; such a suite can only be run whole, and its acceptance tests are locked, so no later stage could move them.
- A test row keeps the part's real collaborators. It replaces only what cannot run locally with the same result every time, at the edge where it leaves the process, and never a function inside the code under test.
- A line whose test runs inside the test runner's own process has the surface family `library`, a call of the dispatcher or the root screen there included. A way-in family means the test starts a separate process, a browser or a device.
- A written rule of the project on where its tests go that disagrees is reported in the spec as an overridden project rule and not followed, except in a repository the request says belongs to someone else.
- A bug's draft failing test is written against the part that produces the symptom, as a crossing of the way in when the fault is in the way in, and against the component that renders it when what the reporter saw is rendered, falling back to the part at fault where the two cannot run together inside the test runner.
- The spec reviewer reports a criterion about a decision placed at the front door when a part promises that behaviour, and two tests that cross the same path of one way in. It no longer reports a spec for having more than one seam. The prototype pathway compares each screen with its mockup rendered on its own, and a function a small change is moved into does not take it out of the brief lane.
- A check the seam rule leaves to the product test or the build job, such as a real start that needs a device or a browser, gets no criterion; the spec's Risks section lists it and the hand-off reports it.
- The record format is unchanged.

## 0.16.2

- The scout agent names its model and effort, opus at high, where it inherited both from the session that dispatched it. Every recorded dispatch ran on Opus at high because the opening sessions did; a session opened on another model would have run its fact finding there, and the spec reviewer already named its own.

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
