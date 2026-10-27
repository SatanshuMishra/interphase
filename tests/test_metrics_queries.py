import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "metrics_hook.py"
SUMMARY = ROOT / "scripts" / "metrics_summary.py"
CATALOGUE = ROOT / "metrics" / "catalogue.json"
SKILL = ROOT / "skills" / "metrics" / "SKILL.md"
INHERITED_OUT = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_PLUGIN_ROOT", "PLUGIN_METRICS_DIR", "PLUGIN_METRICS_PARENT", "AI_AGENT")
SQL_BLOCK = re.compile(r"```sql\n(.*?)\n```", re.DOTALL)
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
QUERY_NAMES = ["runs_overview", "phase_time", "interview", "assumptions_by_intent", "checks_and_review", "spend_by_model", "amendments"]
EXPECTED_COLUMNS = {
    "runs_overview": ("run", "status", "lead_seconds", "usd"),
    "phase_time": ("phase", "seconds"),
    "interview": ("run", "rounds", "questions", "changed"),
    "assumptions_by_intent": ("intent", "count"),
    "checks_and_review": ("run", "review_issues", "check"),
    "spend_by_model": ("model", "usd"),
    "amendments": ("slug", "amendments"),
}
FIRST_RUN = (
    'python3 "{root}/scripts/tree_guard.py" snapshot --repo . --owned "docs/specs/feat-a." --out docs/specs/feat-a.guard.json',
    "python3 {root}/scripts/check_record.py docs/specs/feat-a.record.json",
    "python3 {root}/scripts/check_record.py --complete docs/specs/feat-a.record.json",
    "ASK",
    "python3 {root}/scripts/render_record.py --record docs/specs/feat-a.record.json --spec docs/specs/feat-a.md --items docs/specs/feat-a.items.json",
    "python3 {root}/scripts/check_spec.py --template {root}/core/templates/spec-feature.md docs/specs/feat-a.md",
    "python3 {root}/scripts/check_items.py docs/specs/feat-a.items.json",
    "REVIEW",
    "python3 {root}/scripts/tree_guard.py verify --repo . --snapshot docs/specs/feat-a.guard.json",
)
SECOND_RUN = (
    'python3 "{root}/scripts/tree_guard.py" snapshot --repo . --owned "docs/specs/feat-a." --out docs/specs/feat-a.guard.json',
    "python3 {root}/scripts/render_record.py --record docs/specs/feat-a.record.json --spec docs/specs/feat-a.md --items docs/specs/feat-a.amend-1.items.json --amendment 1",
    "python3 {root}/scripts/check_items.py --amendment docs/specs/feat-a.amend-1.items.json",
    "python3 {root}/scripts/tree_guard.py verify --repo . --snapshot docs/specs/feat-a.guard.json",
)
SPEC = "\n".join((
    "# A feature",
    "",
    "Pathway: feature.",
    "",
    "## 4. Decisions",
    "",
    "### Assumptions",
    "",
    "- The cache is local (relies on I1).",
    "- The owner reads it weekly (relies on I1, I2).",
    "",
    "## 5. Test seams",
    "",
))
DECISIONS = "## Intent\n\n- I1 Goal: a cache\n- I2 Why: the report is slow\n\n## Decisions\n\n- one\n- two\n"


def duckdb_command():
    chosen = os.environ.get("PLUGIN_METRICS_DUCKDB") or shutil.which("duckdb")
    if not chosen:
        raise AssertionError("DuckDB is not installed; install it with brew install duckdb")
    return chosen


def environment(base, session="s-1"):
    inherited = {key: value for key, value in os.environ.items() if key not in INHERITED_OUT}
    return dict(inherited, HOME=str(base / "home"), PLUGIN_METRICS_DIR=str(base / "store"), CLAUDE_CODE_SESSION_ID=session)


def payload(repo, step, session="s-1"):
    common = {
        "hook_event_name": "PostToolUse",
        "session_id": session,
        "transcript_path": str(repo.parent / "home" / ".claude" / "projects" / "-tmp-Sample" / (session + ".jsonl")),
        "cwd": str(repo),
        "tool_use_id": "toolu_1",
    }
    if step == "ASK":
        return dict(common, tool_name="AskUserQuestion", tool_input={"questions": []}, tool_response={"answers": {}})
    if step == "REVIEW":
        return dict(
            common,
            tool_name="Agent",
            tool_input={"subagent_type": "interphase:spec-reviewer", "prompt": "review"},
            tool_response={"content": [{"type": "text", "text": "Status: Issues found\n- Section 4: a\n"}]},
        )
    return dict(
        common,
        tool_name="Bash",
        tool_input={"command": step.format(root=ROOT), "description": "run"},
        tool_response={"stdout": "warning: x" if "check_record" in step else "", "stderr": ""},
    )


def run_hook(base, repo, step):
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload(repo, step)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=str(repo),
        env=environment(base),
        timeout=30,
    )


def event_folder(base):
    return base / "store" / "plugin=interphase" / "kind=event" / "repo=Sample"


def run_ids(base):
    return sorted(path.name[:-len(".jsonl")] for path in event_folder(base).glob("feat-a.*.jsonl"))


def first_ts(base, run):
    first = (event_folder(base) / (run + ".jsonl")).read_text(encoding="utf-8").splitlines()[0]
    return datetime.datetime.strptime(json.loads(first)["ts"], TIMESTAMP_FORMAT)


def next_second():
    time.sleep(1.1 - (time.time() % 1.0))


def settle_detached_builds(base, runs):
    summaries = base / "store" / "plugin=interphase" / "kind=summary" / "repo=Sample"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not all((summaries / (run + ".json")).exists() for run in runs):
        time.sleep(0.2)
    time.sleep(2)


def write_transcript(base, runs):
    path = base / "home" / ".claude" / "projects" / "-tmp-Sample" / "s-1.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "type": "assistant",
            "uuid": "u-" + run,
            "timestamp": first_ts(base, run).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "message": {
                "id": "msg-" + run,
                "model": "claude-opus-5-5",
                "role": "assistant",
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 1000, "output_tokens": 2000, "cache_read_input_tokens": 0},
            },
        }
        for run in runs
    ]
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def build_store(test):
    base = pathlib.Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, str(base), True)
    repo = base / "Sample"
    specs = repo / "docs" / "specs"
    (repo / ".git").mkdir(parents=True)
    specs.mkdir(parents=True)
    (base / "home").mkdir()
    record = {
        "status": "in-progress",
        "seams": [{"name": "a"}],
        "criteria": [{"number": "5.1", "tests": [{"name": "t"}]}],
        "steps": [{"name": "s", "msp": "a", "assumptions": ["x (relies on I1)"]}],
        "rounds": [{"kind": "intent", "questions": 4, "changed": 1}, {"kind": "frontier", "questions": 3, "changed": 0}],
    }
    (specs / "feat-a.record.json").write_text(json.dumps(record), encoding="utf-8")
    (specs / "feat-a.md").write_text(SPEC, encoding="utf-8")
    (specs / "feat-a.decisions.md").write_text(DECISIONS, encoding="utf-8")
    for step in FIRST_RUN:
        test.assertEqual(run_hook(base, repo, step).returncode, 0)
    handed_off = dict(record, status="handed-off", steps=record["steps"] + [{"name": "fix", "amendment": 1}])
    (specs / "feat-a.record.json").write_text(json.dumps(handed_off), encoding="utf-8")
    next_second()
    for step in SECOND_RUN:
        test.assertEqual(run_hook(base, repo, step).returncode, 0)
    runs = run_ids(base)
    test.assertEqual(len(runs), 2)
    settle_detached_builds(base, runs)
    write_transcript(base, runs)
    for run in runs:
        result = subprocess.run(
            [sys.executable, str(SUMMARY), "--repo", str(repo), "--slug", "feat-a", "--run", run],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=environment(base),
            timeout=60,
        )
        test.assertEqual(result.returncode, 0, result.stderr)
    return base / "store"


def views(store):
    block = SQL_BLOCK.search(SKILL.read_text(encoding="utf-8")).group(1)
    return block.replace("<store>", str(store))


def run_query(test, duckdb, store, sql):
    result = subprocess.run(
        [duckdb, "-json"],
        input=views(store) + "\n" + sql.rstrip().rstrip(";") + ";\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env={key: value for key, value in os.environ.items() if key not in INHERITED_OUT},
        timeout=60,
    )
    test.assertEqual(result.returncode, 0, result.stderr)
    return json.loads(result.stdout) if result.stdout.strip() else []


class MetricsQueriesTest(unittest.TestCase):
    def test_named_queries_run(self):
        duckdb = duckdb_command()
        store = build_store(self)
        with open(CATALOGUE, encoding="utf-8") as handle:
            queries = json.load(handle)["queries"]
        for query in queries:
            with self.subTest(query=query["name"]):
                rows = run_query(self, duckdb, store, query["sql"])
                self.assertGreaterEqual(len(rows), 1)
                for column in EXPECTED_COLUMNS[query["name"]]:
                    self.assertIn(column, rows[0])
        amendments = run_query(self, duckdb, store, [query for query in queries if query["name"] == "amendments"][0]["sql"])
        self.assertEqual([(row["slug"], row["amendments"]) for row in amendments], [("feat-a", 1)])

    def test_query_names(self):
        with open(CATALOGUE, encoding="utf-8") as handle:
            queries = json.load(handle)["queries"]
        self.assertEqual([query["name"] for query in queries], QUERY_NAMES)


if __name__ == "__main__":
    unittest.main()
