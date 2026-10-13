import json
import threading
import urllib.error
import urllib.request

import pytest

import server


def put(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj) if not isinstance(obj, str) else obj)


@pytest.fixture
def live(tmp_path):
    proj = tmp_path / "proj"
    folder = proj / "docs" / "tasks" / "2026-10-01-0900-build-x"
    folder.mkdir(parents=True)
    (folder / "STATE.md").write_text("---\ngoal: G\nkey_info: building\n---\n\n2026-10-01 09:00: hi\n")
    (folder / "PLAN.md").write_text("# Plan\n")
    (folder / "pic.png").write_bytes(b"\x89PNG")
    (proj / "secret.md").write_text("secret")
    rel = "docs/tasks/2026-10-01-0900-build-x"
    put(proj / ".cairn/export/tasks.json", {"schema": 1, "generated": "t", "tasks": [
        {"folder": rel, "parent": None, "kind": "build", "goal": "G", "key_info": "building", "phase": "building",
         "needs_attention": False, "last_log": "2026-10-01 09:00", "sessions": [{"session_id": "s1"}]},
        {"folder": "docs/tasks/ghost", "phase": "planned"},
    ]})
    put(proj / ".cairn/export/usage.json", {"schema": 1, "sessions": [{"session_id": "s1", "cost_usd": 0.5}]})
    httpd = server.make_server(proj, port=0, active_dir=tmp_path / "active", static_dir=tmp_path / "static")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    yield base, rel, proj
    httpd.shutdown()
    httpd.server_close()


def get(url):
    try:
        with urllib.request.urlopen(url) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers


def test_tasks_route_returns_cards_with_cost(live):
    base, rel, _ = live
    status, body, _ = get(base + "/api/tasks")
    data = json.loads(body)["data"]
    assert status == 200 and data["status"] == "ok"
    assert [c["folder"] for c in data["cards"]] == [rel, "docs/tasks/ghost"]
    assert data["cards"][0]["cost"]["usd"] == 0.5


def test_detail_doc_asset_roundtrip(live):
    base, rel, _ = live
    q = f"project=proj&folder={rel}"
    status, body, _ = get(f"{base}/api/tasks/detail?{q}")
    detail = json.loads(body)["data"]
    assert status == 200 and detail["frontmatter"]["goal"] == "G"
    assert [d["name"] for d in detail["docs"]] == ["PLAN.md"] and detail["cost"]["state"] == "known"
    assert json.loads(get(f"{base}/api/tasks/doc?{q}&file=PLAN.md")[1])["data"]["content"] == "# Plan\n"
    status, body, headers = get(f"{base}/api/tasks/asset?{q}&path=pic.png")
    assert status == 200 and headers["Content-Type"] == "image/png" and body.startswith(b"\x89PNG")


@pytest.mark.parametrize("query", [
    "project=proj&folder=docs/tasks/ghost",                       # listed in export, folder missing on disk
    "project=other&folder={rel}",                                  # wrong project
    "project=proj&folder=docs/tasks/unlisted",                     # not in export
])
def test_drawer_refuses_bad_requests(live, query):
    base, rel, _ = live
    q = query.format(rel=rel)
    assert get(f"{base}/api/tasks/detail?{q}")[0] == 404
    assert get(f"{base}/api/tasks/doc?{q}")[0] == 404


def test_doc_and_asset_refuse_traversal(live):
    base, rel, _ = live
    assert get(f"{base}/api/tasks/doc?project=proj&folder={rel}&file=../../../../secret.md")[0] == 404
    assert get(f"{base}/api/tasks/doc?project=proj&folder=docs/tasks/../..&file=secret.md")[0] == 404
    assert get(f"{base}/api/tasks/asset?project=proj&folder={rel}&path=../../../x.png")[0] == 404


def test_no_write_routes(live):
    base, rel, proj = live
    before = sorted(p.name for p in proj.rglob("*"))
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        req = urllib.request.Request(base + "/api/tasks", data=b"{}", method=method)
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        assert e.value.code == 405
    assert sorted(p.name for p in proj.rglob("*")) == before


def test_empty_state_payload(tmp_path):
    proj = tmp_path / "empty"
    proj.mkdir()
    httpd = server.make_server(proj, port=0, active_dir=tmp_path / "a", static_dir=tmp_path / "s")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        data = json.loads(get(f"http://127.0.0.1:{httpd.server_address[1]}/api/tasks")[1])["data"]
    finally:
        httpd.shutdown()
        httpd.server_close()
    assert data["status"] == "missing" and data["usage"] == "missing" and data["cards"] == []
    assert not (proj / ".cairn").exists()


def raw_get(base, path, host):
    """GET with an explicit Host header (or none when `host` is None)."""
    import http.client
    conn = http.client.HTTPConnection(base.removeprefix("http://"))
    conn.putrequest("GET", path, skip_host=True, skip_accept_encoding=True)
    if host is not None:
        conn.putheader("Host", host)
    conn.endheaders()
    resp = conn.getresponse()
    status = resp.status
    resp.read()
    conn.close()
    return status


@pytest.mark.parametrize("path", ["/api/tasks", "/api/projects", "/", "/index.html"])
def test_host_header_allowlist(live, path):
    base, _, _ = live
    port = base.rsplit(":", 1)[1]
    assert raw_get(base, path, f"127.0.0.1:{port}") == 200
    assert raw_get(base, path, f"localhost:{port}") == 200
    assert raw_get(base, path, f"evil.example:{port}") == 403
    assert raw_get(base, path, "evil.example") == 403
    assert raw_get(base, path, f"127.0.0.1:{int(port) + 1}") == 403
    assert raw_get(base, path, f"[::1]:{port}") == 403  # server binds IPv4 only
    assert raw_get(base, path, None) == 403


def test_host_check_covers_asset_and_write_routes(live):
    base, rel, _ = live
    port = base.rsplit(":", 1)[1]
    assert raw_get(base, f"/api/tasks/asset?project=proj&folder={rel}&path=pic.png", "evil.example") == 403
    assert raw_get(base, f"/api/tasks/asset?project=proj&folder={rel}&path=pic.png", f"localhost:{port}") == 200


def test_task_docs_are_read_as_utf8(live):
    base, rel, proj = live
    (proj / rel / "NOTES.md").write_text("caf\u00e9 \u2014 \u65e5\u672c\n", encoding="utf-8")
    q = f"project=proj&folder={rel}"
    status, body, _ = get(f"{base}/api/tasks/doc?{q}&file=NOTES.md")
    assert status == 200 and json.loads(body)["data"]["content"] == "caf\u00e9 \u2014 \u65e5\u672c\n"


def test_undecodable_doc_is_a_404_not_a_crash(live):
    base, rel, proj = live
    (proj / rel / "BAD.md").write_bytes(b"\xff\xfe not utf-8 \x80")
    q = f"project=proj&folder={rel}"
    assert get(f"{base}/api/tasks/doc?{q}&file=BAD.md")[0] == 404
