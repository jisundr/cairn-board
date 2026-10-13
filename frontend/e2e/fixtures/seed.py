#!/usr/bin/env python3
"""Seeds one e2e scenario under <scratch>/<scenario>/: a project directory
(`board-demo`) plus a HOME for the server to read markers from. The server
under test is started with HOME=<scratch>/<scenario>, so it can never pick
up this machine's real ~/.claude.

Usage: seed.py <scratch> <populated|tasks-only|empty|shared|null-cost>
"""
import json
import shutil
import sys
from pathlib import Path

PARENT = "docs/tasks/2026-10-01-0900-build-epic"
CHILD_DONE = f"{PARENT}/01-build-schema"
CHILD_LIVE = f"{PARENT}/02-build-board"
PLANNED = "docs/tasks/2026-10-02-1000-build-planned-thing"
SCOPING = "docs/tasks/2026-10-03-1100-research-open-question"
STALLED = "docs/tasks/2026-10-04-1200-build-stalled-work"


def task(folder, phase, goal, parent=None, kind="build", key_info="", attention=False, sessions=(), last="2026-10-05 09:00"):
    return {
        "folder": folder, "parent": parent, "kind": kind, "goal": goal, "key_info": key_info, "phase": phase,
        "needs_attention": attention, "last_log": last,
        "sessions": [{"session_id": s, "started": "2026-10-05T08:00:00Z", "ended": "2026-10-05T09:00:00Z"} for s in sessions],
    }


def write_folder(project: Path, folder: str, goal: str, key_info: str):
    d = project / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "STATE.md").write_text(f"---\ngoal: {goal}\nkey_info: {key_info}\n---\n\n2026-10-05 09:00: seeded for e2e\n")
    (d / "REQUIREMENTS.md").write_text(f"# Requirements\n\nSeeded requirements for {goal}.\n")


def tasks_for(scenario: str):
    if scenario == "shared":
        return [
            task("docs/tasks/2026-10-01-0900-build-first", "building", "First task", sessions=["s-own", "s-both"]),
            task("docs/tasks/2026-10-02-0900-build-second", "building", "Second task", sessions=["s-both"]),
        ]
    if scenario == "null-cost":
        return [
            task("docs/tasks/2026-10-01-0900-build-metered", "building", "Metered task", sessions=["s-ok", "s-null"]),
            task("docs/tasks/2026-10-02-0900-build-fine", "building", "Fine task", sessions=["s-fine"]),
        ]
    return [
        task(PARENT, "parent_tasks", "Epic parent", sessions=[]),
        task(CHILD_DONE, "done", "Schema child", parent=PARENT, sessions=["s-1"]),
        task(CHILD_LIVE, "building", "Board child", parent=PARENT, sessions=["s-2", "s-3"], key_info="building"),
        task(PLANNED, "planned", "Planned thing", key_info="approved; next step build"),
        task(SCOPING, "scoping", "Open question", kind="research"),
        task(STALLED, "building", "Stalled work", key_info="stalled: waiting on input", attention=True),
    ]


def usage_for(scenario: str):
    rows = {
        "populated": [("s-1", 0.5), ("s-2", 1.25), ("s-3", 0.75)],
        "shared": [("s-own", 1.0), ("s-both", 9.0)],
        "null-cost": [("s-ok", 2.0), ("s-null", None), ("s-fine", 0.4)],
    }[scenario]
    return [{"session_id": s, "started": "2026-10-05T08:00:00Z", "ended": "2026-10-05T09:00:00Z", "models": ["m"],
             "input_tokens": 1, "output_tokens": 1, "cache_read_tokens": 0, "cache_write_tokens": 0,
             "cost_usd": c, "unpriced_models": [] if c is not None else ["m"]} for s, c in rows]


def main():
    scratch, scenario = Path(sys.argv[1]), sys.argv[2]
    home = scratch / scenario
    shutil.rmtree(home, ignore_errors=True)
    project = home / "board-demo"
    project.mkdir(parents=True)
    if scenario == "empty":
        return
    tasks = tasks_for(scenario)
    for t in tasks:
        write_folder(project, t["folder"], t["goal"], t["key_info"] or "")
    export = project / ".cairn" / "export"
    export.mkdir(parents=True)
    (export / "tasks.json").write_text(json.dumps(
        {"schema": 1, "generated": "2026-10-05T09:30:00Z", "project": str(project.resolve()), "tasks": tasks}))
    if scenario != "tasks-only":
        (export / "usage.json").write_text(json.dumps(
            {"schema": 1, "generated": "2026-10-05T09:30:00Z", "project": str(project.resolve()), "currency": "USD",
             "prices_as_of": "2026-10-01", "sessions": usage_for(scenario)}))
    if scenario in ("populated", "tasks-only"):
        active = home / ".claude" / "cairn" / "active"
        active.mkdir(parents=True)
        (active / "sess--agent.active").write_text(json.dumps(
            {"project": str(project.resolve()), "task": CHILD_LIVE, "schema": 1, "started": "2026-10-05T09:00:00Z", "future_key": 1}))


if __name__ == "__main__":
    main()
