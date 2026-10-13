#!/usr/bin/env python3
"""Reads cairn's two exports and shapes the board's cards. stdlib only,
read-only: nothing here writes under `.cairn/`, `docs/` or `~/.claude/`.

- `<project>/.cairn/export/tasks.json`, written by cairn core (contract:
  `docs/schemas/tasks-v1.md` in core). Required for any card.
- `<project>/.cairn/export/usage.json`, written by cairn-meter. Optional; it
  only adds cost per task.
- `~/.claude/cairn/active/*.active`, core's subagent markers
  `{project, task, schema?, started?}`, for the "active" badge. Unknown keys
  are ignored.

Each export carries `"schema": <int>`. A higher major than this reader knows
is refused with a status, never half-read.

Cost per task: the sum of `cost_usd` over sessions bound to that task alone.
A session bound to several tasks is `shared` and is never split. A null or
absent figure for a sole session makes the task's cost `unknown`; the board
never shows a partial sum as if it were whole.
"""
import json
import math
import re
import time
from pathlib import Path

SUPPORTED_SCHEMA = 1
MARKER_MAX_AGE_SECONDS = 14400  # a marker older than 4 hours is a crashed subagent's
PHASES = (
    "parent_tasks",
    "scoping",
    "awaiting_approval",
    "planned",
    "building",
    "in_review",
    "blocked",
    "done",
)
KINDS = ("build", "research", "review")

_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?")
_FOLDER_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def default_active_dir() -> Path:
    return Path.home() / ".claude" / "cairn" / "active"


def export_path(project_root: Path, name: str) -> Path:
    return project_root / ".cairn" / "export" / name


def read_export(path: Path) -> dict:
    """`{status, data, detail}`. `status` is `ok`, `missing`, `invalid`
    (unreadable, not JSON, not an object, or no integer `schema`) or
    `unsupported` (a schema major this reader does not know)."""
    if not path.is_file():
        return {"status": "missing", "data": None, "detail": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": "invalid", "data": None, "detail": f"cannot read {path.name}: {exc}"}
    if not isinstance(data, dict):
        return {"status": "invalid", "data": None, "detail": f"{path.name} is not a JSON object"}
    schema = data.get("schema")
    if isinstance(schema, bool) or not isinstance(schema, int) or schema < 1:
        return {"status": "invalid", "data": None, "detail": f"{path.name} has no valid schema number"}
    if schema > SUPPORTED_SCHEMA:
        return {
            "status": "unsupported",
            "data": None,
            "detail": f"{path.name} uses schema {schema}; this board reads schema {SUPPORTED_SCHEMA}",
        }
    return {"status": "ok", "data": data, "detail": ""}


def live_markers(active_dir: Path, project_root: Path, now: float | None = None) -> set[str]:
    """Task folders (project-relative) with a fresh marker for this project.
    A marker that is unreadable, not an object, stale, from another project,
    or from a schema major newer than 1 contributes nothing."""
    live: set[str] = set()
    if not active_dir.is_dir():
        return live
    now = time.time() if now is None else now
    try:
        root = str(project_root.resolve())
    except OSError:
        return live
    for path in active_dir.glob("*.active"):
        try:
            if now - path.stat().st_mtime > MARKER_MAX_AGE_SECONDS:
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        schema = payload.get("schema")
        if isinstance(schema, int) and not isinstance(schema, bool) and schema > 1:
            continue
        project, task = payload.get("project"), payload.get("task")
        if not isinstance(project, str) or not isinstance(task, str):
            continue
        try:
            if str(Path(project).resolve()) != root:
                continue
        except (OSError, RuntimeError):
            continue
        live.add(task.strip("/"))
    return live


def _usable_cost(value) -> float | None:
    """A finite, non-negative number, else None (unknown). NaN, Infinity and
    negative figures never reach the API JSON."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def session_costs(usage: dict | None) -> dict[str, float | None]:
    """session_id -> cost_usd (None when null, malformed, or duplicated)."""
    costs: dict[str, float | None] = {}
    if not usage:
        return costs
    seen: set[str] = set()
    for entry in usage.get("sessions") or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("session_id"), str):
            continue
        sid = entry["session_id"]
        if sid in seen:
            costs[sid] = None  # two rows for one session: not safe to pick one
            continue
        seen.add(sid)
        costs[sid] = _usable_cost(entry.get("cost_usd"))
    return costs


def _task_session_ids(task: dict) -> list[str]:
    ids: list[str] = []
    for s in task.get("sessions") or []:
        sid = s.get("session_id") if isinstance(s, dict) else None
        if isinstance(sid, str) and sid not in ids:
            ids.append(sid)
    return ids


def cost_for(session_ids: list[str], owners: dict[str, int], costs: dict[str, float | None]) -> dict:
    """`{state, usd, sessions, shared_sessions}`; state is `none` (nothing to
    show), `known`, `unknown` or `shared` (every session is shared)."""
    sole = [s for s in session_ids if owners.get(s, 0) == 1]
    shared = [s for s in session_ids if owners.get(s, 0) > 1]
    base = {"usd": None, "sessions": len(sole), "shared_sessions": len(shared)}
    if sole:
        figures = [costs.get(s) for s in sole]
        if any(f is None for f in figures):
            return {"state": "unknown", **base}
        total = sum(figures)
        if not math.isfinite(total):
            return {"state": "unknown", **base}
        return {"state": "known", **base, "usd": round(total, 6)}
    if shared:
        return {"state": "shared", **base}
    return {"state": "none", **base}


def _last_log(raw, folder: str) -> tuple[str, str]:
    if isinstance(raw, str):
        m = _DATE_RE.match(raw)
        if m:
            return m.group(1), m.group(2) or ""
    m = _FOLDER_DATE_RE.search(folder)
    return (m.group(1) if m else ""), ""


def build_board(project_root: Path, active_dir: Path | None = None, now: float | None = None) -> dict:
    """The `/api/tasks` payload: `{status, detail, generated, usage,
    usage_detail, skipped, cards}`. `cards` is empty unless `status` is `ok`."""
    label = project_root.name
    tasks_export = read_export(export_path(project_root, "tasks.json"))
    usage_export = read_export(export_path(project_root, "usage.json"))
    payload = {
        "status": tasks_export["status"],
        "detail": tasks_export["detail"],
        "generated": None,
        "usage": usage_export["status"],
        "usage_detail": usage_export["detail"],
        "skipped": 0,
        "cards": [],
    }
    if tasks_export["status"] != "ok":
        return payload
    data = tasks_export["data"]
    raw_tasks = data.get("tasks")
    if not isinstance(raw_tasks, list):
        payload["status"], payload["detail"] = "invalid", "tasks.json has no tasks list"
        return payload
    payload["generated"] = data.get("generated") if isinstance(data.get("generated"), str) else None

    tasks: list[dict] = []
    seen_folders: set[str] = set()
    for t in raw_tasks:
        if isinstance(t, dict) and isinstance(t.get("folder"), str) and t.get("phase") in PHASES:
            if t["folder"] in seen_folders:
                continue  # a repeated folder: the first entry wins
            seen_folders.add(t["folder"])
            tasks.append(t)
        else:
            payload["skipped"] += 1

    costs = session_costs(usage_export["data"]) if usage_export["status"] == "ok" else {}
    owners: dict[str, int] = {}
    for t in tasks:
        for sid in _task_session_ids(t):
            owners[sid] = owners.get(sid, 0) + 1
    live = live_markers(active_dir if active_dir is not None else default_active_dir(), project_root, now)

    by_parent: dict[str, list[dict]] = {}
    for t in tasks:
        parent = t.get("parent")
        if isinstance(parent, str):
            by_parent.setdefault(parent, []).append(t)

    cards = []
    for t in tasks:
        folder = t["folder"]
        date, time_ = _last_log(t.get("last_log"), folder)
        kids = by_parent.get(folder)
        parent = t.get("parent")
        kind = t.get("kind")
        cards.append(
            {
                "project": label,
                "folder": folder,
                "parent": parent if isinstance(parent, str) else None,
                "kind": kind if kind in KINDS else "build",
                "goal": t.get("goal") if isinstance(t.get("goal"), str) else "",
                "key_info": t.get("key_info") if isinstance(t.get("key_info"), str) else "",
                "last_log_date": date,
                "last_log_time": time_,
                "column": t["phase"],
                "active": folder in live,
                "needs_attention": t.get("needs_attention") is True,
                "done": t["phase"] == "done",
                "sub_tasks": (
                    {"done": sum(1 for k in kids if k["phase"] == "done"), "total": len(kids)} if kids else None
                ),
                "cost": (
                    cost_for(_task_session_ids(t), owners, costs)
                    if usage_export["status"] == "ok"
                    else cost_for([], owners, costs)
                ),
            }
        )
    cards.sort(key=lambda c: f"{c['last_log_date']} {c['last_log_time'] or '00:00'}", reverse=True)
    payload["cards"] = cards
    return payload
