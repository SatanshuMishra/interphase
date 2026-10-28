# Acceptance lines are checked against the frozen program schemas, loaded at run time

Status: accepted

interphase ships verbatim copies of the harness program's frozen K1, K2 and K6 JSON Schema files in contracts/ and validates the record's acceptance lines and locked list by loading them through a small standard-library validator that knows only the keywords those files use and refuses any other. We chose this over restating the rules in Python, which drifts from the contract mitosis and lighthouse read, and over a third-party validator, which interphase cannot assume on any Python 3.9. A change to a schema is a program decision: the copies are pinned by digest in the tests, so updating one means updating the program's file, the copy and the pin together.
