# A run counts only its own spend, between its first and last event

Status: accepted

An interphase run's spend is the main session's messages and its own scout and spec-reviewer agents' messages timed from its first event, the guard snapshot, to its last, priced from interphase's own price table with that table's date. The few messages before the snapshot, such as reading the playbook, are left to whatever started the run, because a parent run leaves out exactly the span between a child's first and last event; counting them here would count them twice. A model the price table lacks makes the run's cost unknown rather than lower. We chose this over counting from the moment the pathway skill starts, which is closer to the true cost but double-counts under any parent, and over reading another plugin's prices, which would make interphase depend on it.
