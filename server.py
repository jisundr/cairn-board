#!/usr/bin/env python3
"""cairn-board's local server: a read-only kanban over cairn's exports.
stdlib only.

Binds 127.0.0.1, serves the built frontend from `static/` and a small JSON
API. Every route is GET; any other method is refused with 405. Nothing here
writes to the project, the harness or `~/.claude/`.

Usage:
    python3 server.py [project_root] [port]
"""
import http.server
import json
import mimetypes
import socket
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exports  # noqa: E402
import taskfiles  # noqa: E402

DEFAULT_PORT = 4319
DEFAULT_HOST = "127.0.0.1"
STATIC_DIR = Path(__file__).resolve().parent / "static"

_PLACEHOLDER_HTML = (
    "<!doctype html><html><body>"
    "<p>cairn-board: the frontend is not built yet. Run <code>npm run build</code> in frontend/.</p>"
    "</body></html>"
).encode("utf-8")


class BoardApp:
    """Query layer, independent of HTTP."""

    def __init__(self, project_root: Path, *, active_dir: Path | None = None, static_dir: Path | None = None):
        self.project_root = Path(project_root).resolve()
        self.label = self.project_root.name
        self.active_dir = Path(active_dir) if active_dir else None
        self.static_dir = Path(static_dir) if static_dir else STATIC_DIR

    def board(self) -> dict:
        return exports.build_board(self.project_root, self.active_dir)

    def _card(self, folder: str | None) -> dict | None:
        """The exported card for `folder`; a folder tasks.json does not list
        is not served."""
        if not folder:
            return None
        board = self.board()
        return next((c for c in board["cards"] if c["folder"] == folder), None)

    def _folder_dir(self, project: str | None, folder: str | None):
        if project != self.label:
            return None, None
        card = self._card(folder)
        if card is None:
            return None, None
        return card, taskfiles.resolve_task_folder(self.project_root, folder or "")

    def detail(self, project: str | None, folder: str | None) -> dict | None:
        card, folder_dir = self._folder_dir(project, folder)
        if card is None or folder_dir is None:
            return None
        state, draft = folder_dir / "STATE.md", folder_dir / "DRAFT.md"
        source = state if state.is_file() else draft if draft.is_file() else None
        if source is None:
            return None
        try:
            text = source.read_text()
        except OSError:
            return None
        if source.name == "DRAFT.md":
            goal, key_info = taskfiles.draft_summary(text)
            frontmatter, activity, draft_content = {"goal": goal, "key_info": key_info}, None, text
        else:
            frontmatter, activity, draft_content = taskfiles.parse_frontmatter(text), taskfiles.parse_activity(text), None
        board = self.board()
        children = [c for c in board["cards"] if c["parent"] == card["folder"]]
        return {
            "project": card["project"],
            "folder": card["folder"],
            "parent": card["parent"],
            "kind": card["kind"],
            "column": card["column"],
            "needs_attention": card["needs_attention"],
            "active": card["active"],
            "cost": card["cost"],
            "frontmatter": frontmatter,
            "activity": activity,
            "draft_content": draft_content,
            "sub_tasks": [
                {
                    "folder": c["folder"],
                    "column": c["column"],
                    "needs_attention": c["needs_attention"],
                    "active": c["active"],
                    "goal": c["goal"],
                }
                for c in children
            ]
            or None,
            "docs": taskfiles.list_docs(folder_dir),
        }

    def doc(self, project: str | None, folder: str | None, file_name: str | None) -> dict | None:
        _, folder_dir = self._folder_dir(project, folder)
        if folder_dir is None:
            return None
        path = taskfiles.safe_task_doc_path(folder_dir, file_name or "")
        if path is None or not path.is_file():
            return None
        try:
            return {"content": path.read_text()}
        except OSError:
            return None

    def asset(self, project: str | None, folder: str | None, rel: str | None):
        _, folder_dir = self._folder_dir(project, folder)
        if folder_dir is None:
            return None
        path = taskfiles.safe_task_asset_path(folder_dir, rel or "")
        if path is None:
            return None
        return path, taskfiles.TASK_ASSET_TYPES[path.suffix.lower()]

    def handle_api(self, path: str, query: dict) -> tuple[int, dict]:
        def first(key):
            values = query.get(key)
            return values[0] if values else None

        meta = {"generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
        if path == "/api/projects":
            data = {"hostname": socket.gethostname(), "projects": [{"label": self.label, "parent": None}]}
            return 200, {"data": data, "meta": meta}
        if path == "/api/tasks":
            return 200, {"data": self.board(), "meta": meta}
        if path == "/api/tasks/detail":
            data = self.detail(first("project"), first("folder"))
            return (200, {"data": data, "meta": meta}) if data else (404, {"error": "task folder not found"})
        if path == "/api/tasks/doc":
            data = self.doc(first("project"), first("folder"), first("file"))
            return (200, {"data": data, "meta": meta}) if data else (404, {"error": "document not found"})
        return 404, {"error": "unknown route"}


def _safe_static_path(static_dir: Path, request_path: str) -> Path | None:
    rel = request_path.lstrip("/")
    if not rel:
        return None
    try:
        candidate = (static_dir / rel).resolve()
        candidate.relative_to(static_dir.resolve())
    except (OSError, RuntimeError, ValueError):
        return None
    return candidate


class Handler(http.server.BaseHTTPRequestHandler):
    app: "BoardApp" = None
    # Host header values this server answers to (set by make_server once the
    # port is known). Anything else is a DNS-rebinding attempt.
    allowed_hosts: frozenset = frozenset()

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").strip().lower()
        if host in self.allowed_hosts:
            return True
        self._write(403, "application/json", b'{"error": "forbidden host"}')
        return False

    def do_GET(self):
        if not self._host_ok():
            return
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == "/api/tasks/asset":
            self._serve_asset(params)
        elif parsed.path.startswith("/api/"):
            status, body = self.app.handle_api(parsed.path, params)
            self._write(status, "application/json", json.dumps(body).encode("utf-8"))
        else:
            self._serve_static(parsed.path)

    def _refuse(self):
        if not self._host_ok():
            return
        self._write(405, "application/json", b'{"error": "read-only: this board has no write routes"}', allow="GET")

    do_POST = do_PUT = do_PATCH = do_DELETE = _refuse

    def _serve_asset(self, params: dict):
        def first(key):
            values = params.get(key)
            return values[0] if values else None

        found = self.app.asset(first("project"), first("folder"), first("path"))
        content = None
        if found is not None:
            try:
                content = found[0].read_bytes()
            except OSError:
                content = None
        if content is None:
            self._write(404, "application/json", b'{"error": "asset not found"}')
            return
        self._write(
            200,
            found[1],
            content,
            extra={"X-Content-Type-Options": "nosniff", "Cross-Origin-Resource-Policy": "same-origin"},
        )

    def _serve_static(self, path: str):
        static_dir = self.app.static_dir
        candidate = _safe_static_path(static_dir, path) if static_dir.is_dir() else None
        if candidate is not None and candidate.is_file():
            ctype, _ = mimetypes.guess_type(str(candidate))
            self._write(200, ctype or "application/octet-stream", candidate.read_bytes())
            return
        index = static_dir / "index.html"
        if index.is_file():
            self._write(200, "text/html", index.read_bytes())
            return
        self._write(200, "text/html", _PLACEHOLDER_HTML)

    def _write(self, status: int, ctype: str, payload: bytes, *, allow: str | None = None, extra: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache")
        if allow:
            self.send_header("Allow", allow)
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


def make_server(project_root: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, **kwargs):
    app = BoardApp(project_root, **kwargs)
    handler = type("BoundHandler", (Handler,), {"app": app})
    httpd = http.server.ThreadingHTTPServer((host, port), handler)
    handler.allowed_hosts = allowed_hosts(httpd)
    return httpd


def allowed_hosts(httpd) -> frozenset:
    """`127.0.0.1:<port>` and `localhost:<port>`, plus `[::1]:<port>` only
    when the socket really is IPv6."""
    bound = httpd.server_address[1]
    names = ["127.0.0.1", "localhost"]
    if httpd.address_family == socket.AF_INET6:
        names.append("[::1]")
    return frozenset(f"{n}:{bound}" for n in names)


def main(argv: list[str] | None = None):
    argv = sys.argv[1:] if argv is None else argv
    project_root = Path(argv[0]) if argv else Path.cwd()
    port = int(argv[1]) if len(argv) > 1 else DEFAULT_PORT
    httpd = make_server(project_root, port=port)
    host, bound = httpd.server_address[:2]
    print(f"cairn-board: http://{host}:{bound}", flush=True)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
