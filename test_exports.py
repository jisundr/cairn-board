import json
import os
import time

import pytest

import exports


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(obj if isinstance(obj, str) else json.dumps(obj))


def task(folder, phase="building", sessions=(), **kw):
    return {
        "folder": folder, "parent": None, "kind": "build", "goal": f"goal {folder}", "key_info": "",
        "phase": phase, "needs_attention": False, "last_log": "2026-10-01 09:00",
        "sessions": [{"session_id": s, "started": "2026-10-01T09:00:00Z", "ended": None} for s in sessions],
        **kw,
    }


def tasks_json(project, tasks, schema=1):
    write(project / ".cairn/export/tasks.json",
          {"schema": schema, "generated": "2026-10-01T10:00:00Z", "project": str(project), "tasks": tasks})


def usage_json(project, sessions, schema=1):
    write(project / ".cairn/export/usage.json",
          {"schema": schema, "generated": "2026-10-01T10:00:00Z", "project": str(project), "currency": "USD",
           "sessions": [{"session_id": s, "cost_usd": c} for s, c in sessions]})


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return p


def card(payload, folder):
    return next(c for c in payload["cards"] if c["folder"] == folder)


def test_missing_tasks_json(project, tmp_path):
    out = exports.build_board(project, tmp_path / "none")
    assert out["status"] == "missing" and out["cards"] == []


def test_unsupported_and_invalid_schema(project, tmp_path):
    tasks_json(project, [task("a")], schema=2)
    out = exports.build_board(project, tmp_path)
    assert out["status"] == "unsupported" and "schema 2" in out["detail"] and out["cards"] == []
    write(project / ".cairn/export/tasks.json", "{not json")
    assert exports.build_board(project, tmp_path)["status"] == "invalid"
    write(project / ".cairn/export/tasks.json", {"tasks": []})
    assert exports.build_board(project, tmp_path)["status"] == "invalid"
    write(project / ".cairn/export/tasks.json", {"schema": 1, "tasks": "x"})
    assert exports.build_board(project, tmp_path)["status"] == "invalid"


def test_cards_and_subtask_summary(project, tmp_path):
    tasks_json(project, [
        task("docs/tasks/p", "parent_tasks"),
        task("docs/tasks/p/01-x", "done", parent="docs/tasks/p"),
        task("docs/tasks/p/02-y", "building", parent="docs/tasks/p", needs_attention=True),
        task("docs/tasks/bad", "mystery"),
    ])
    out = exports.build_board(project, tmp_path)
    assert out["status"] == "ok" and out["skipped"] == 1 and len(out["cards"]) == 3
    assert card(out, "docs/tasks/p")["sub_tasks"] == {"done": 1, "total": 2}
    assert card(out, "docs/tasks/p/02-y")["needs_attention"] is True
    assert card(out, "docs/tasks/p/01-x")["done"] is True
    assert card(out, "docs/tasks/p/01-x")["last_log_date"] == "2026-10-01"


def test_cost_absent_without_usage_json(project, tmp_path):
    tasks_json(project, [task("a", sessions=["s1"])])
    out = exports.build_board(project, tmp_path)
    assert out["usage"] == "missing"
    assert card(out, "a")["cost"]["state"] == "none"


def test_cost_sums_sole_sessions_only(project, tmp_path):
    tasks_json(project, [task("a", sessions=["s1", "s2"]), task("b", sessions=["s3"])])
    usage_json(project, [("s1", 1.25), ("s2", 0.5), ("s3", 2)])
    out = exports.build_board(project, tmp_path)
    assert card(out, "a")["cost"] == {"state": "known", "usd": 1.75, "sessions": 2, "shared_sessions": 0}
    assert card(out, "b")["cost"]["usd"] == 2.0


def test_shared_session_is_not_split(project, tmp_path):
    tasks_json(project, [task("a", sessions=["s1", "sx"]), task("b", sessions=["sx"])])
    usage_json(project, [("s1", 1.0), ("sx", 9.0)])
    out = exports.build_board(project, tmp_path)
    assert card(out, "a")["cost"] == {"state": "known", "usd": 1.0, "sessions": 1, "shared_sessions": 1}
    assert card(out, "b")["cost"] == {"state": "shared", "usd": None, "sessions": 0, "shared_sessions": 1}


def test_null_or_unmetered_cost_makes_unknown(project, tmp_path):
    tasks_json(project, [task("a", sessions=["s1", "s2"]), task("b", sessions=["s3", "gone"])])
    usage_json(project, [("s1", 1.0), ("s2", None), ("s3", 1.0)])
    out = exports.build_board(project, tmp_path)
    assert card(out, "a")["cost"]["state"] == "unknown" and card(out, "a")["cost"]["usd"] is None
    assert card(out, "b")["cost"]["state"] == "unknown"


def test_duplicate_usage_rows_make_unknown(project, tmp_path):
    tasks_json(project, [task("a", sessions=["s1"])])
    usage_json(project, [("s1", 1.0), ("s1", 2.0)])
    assert card(exports.build_board(project, tmp_path), "a")["cost"]["state"] == "unknown"


def test_unsupported_usage_schema_shows_no_cost(project, tmp_path):
    tasks_json(project, [task("a", sessions=["s1"])])
    usage_json(project, [("s1", 1.0)], schema=3)
    out = exports.build_board(project, tmp_path)
    assert out["status"] == "ok" and out["usage"] == "unsupported"
    assert card(out, "a")["cost"]["state"] == "none"


def marker(dirpath, name, payload, age=0):
    dirpath.mkdir(parents=True, exist_ok=True)
    p = dirpath / name
    p.write_text(json.dumps(payload))
    t = time.time() - age
    os.utime(p, (t, t))


def test_active_markers(project, tmp_path):
    tasks_json(project, [task("a"), task("b"), task("c"), task("d")])
    d = tmp_path / "active"
    marker(d, "1.active", {"project": str(project), "task": "a", "schema": 1, "started": "x", "extra": [1]})
    marker(d, "2.active", {"project": "/elsewhere", "task": "b"})
    marker(d, "3.active", {"project": str(project), "task": "c"}, age=exports.MARKER_MAX_AGE_SECONDS + 60)
    marker(d, "4.active", {"project": str(project), "task": "d", "schema": 2})
    (d / "5.active").write_text("not json")
    (d / "sess.json").write_text(json.dumps({"project": str(project), "task": "b"}))
    out = exports.build_board(project, d)
    assert [c["folder"] for c in out["cards"] if c["active"]] == ["a"]
