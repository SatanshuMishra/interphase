---
name: metrics
description: Use when someone asks how interphase is performing, how its runs went, or what its interviews, checks, reviews, time or spend look like, answered from interphase's own records in the metrics store.
---

# interphase metrics

1. The store root is the folder `PLUGIN_METRICS_DIR` names when it is set and non-empty, otherwise `~/.plugin-metrics`.
2. Read `<root>/plugin=interphase/catalogue.json` first. Start from its purpose and objectives, and choose the fields that answer the question from each field's description and reading.
3. List `<root>/plugin=interphase/kind=event/` and `<root>/plugin=interphase/kind=summary/`. When a folder holds no file, say no runs are recorded there and do not query it, because DuckDB refuses a pattern that matches no file.
4. Find the DuckDB command-line tool with `command -v duckdb`. When it is not found, say so, give the install command `brew install duckdb`, and stop.
5. Run DuckDB with this block first, replacing every `<store>` with the store root, then the query:

```sql
SET TimeZone = 'UTC';
CREATE OR REPLACE VIEW events AS
SELECT * FROM read_json('<store>/plugin=interphase/kind=event/*/*.jsonl',
    format = 'newline_delimited', union_by_name = true, hive_partitioning = true);
CREATE OR REPLACE VIEW summaries AS
SELECT * FROM read_json('<store>/plugin=interphase/kind=summary/*/*.json',
    format = 'newline_delimited', union_by_name = true, hive_partitioning = true);
```

6. Use the catalogue's named queries where one fits the question, and write a new query over the same views only when none does.
7. Answer with the figures, the runs in scope, the period they cover and the fields you used.
8. Count only interphase's own spend. Never add another plugin's spend to it; a run's spend fields hold its own messages only.
9. Show a null figure as missing, never as zero. Null means the value is unknown or its source was absent.
10. Never read transcripts. Answer from the store alone.
11. Point out weak figures in the answer, such as few runs or many missing values, and store no verdict anywhere.
