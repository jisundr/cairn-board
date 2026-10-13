#!/usr/bin/env python3
"""Reads one task folder's own files for the drawer: frontmatter, the
activity log, the doc list, and the path guards that keep every read inside
`<project>/docs/tasks/`. stdlib only, read-only.

Frontmatter, activity and doc-list logic is adapted from cairn core's
mission-control `tasks.py` (core at 0d4e7a3); the guards from its `server.py`.
The card list itself never comes from here: it comes from `tasks.json`
(`exports.py`).
"""
import re
from datetime import datetime
from pathlib import Path

def _frontmatter_bounds(lines: list[str]) -> tuple[int, int] | None:
    """`(start, end)` such that `lines[start:end]` is the frontmatter
    block's own lines, excluding both `---` delimiters - or `None` if the
    file doesn't open with `---`, or never closes it (degrade, not crash:
    callers treat `None` as "no frontmatter found")."""
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return (1, i)
    return None


_KEY_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*):(.*)$")


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _split_flow_list(inner: str) -> list[str]:
    """Splits a `[a, b, c]` flow list's inner text on top-level commas only
    - a comma inside a quoted item (`["a, b", "c"]`) doesn't split it."""
    items: list[str] = []
    current: list[str] = []
    in_quotes = False
    quote_char = ""
    for ch in inner:
        if in_quotes:
            current.append(ch)
            if ch == quote_char:
                in_quotes = False
            continue
        if ch in "\"'":
            in_quotes = True
            quote_char = ch
            current.append(ch)
            continue
        if ch == ",":
            items.append("".join(current))
            current = []
            continue
        current.append(ch)
    items.append("".join(current))
    return items


def _parse_frontmatter_lines(lines: list[str]) -> dict[str, str | list[str]]:
    result: dict[str, str | list[str]] = {}
    current_key: str | None = None
    current_list: list[str] | None = None

    for line in lines:
        if current_list is not None:
            stripped = line.strip()
            if stripped.startswith("- "):
                current_list.append(_strip_quotes(stripped[2:]))
                continue
            result[current_key] = current_list
            current_key, current_list = None, None
            # fall through: this line may itself be the next key

        match = _KEY_LINE_RE.match(line)
        if not match:
            continue  # unparseable line: dropped, not fatal (degrade)
        key, raw_value = match.group(1), match.group(2).strip()

        if raw_value == "":
            # Either a block list follows (`flags:\n  - a`) or the scalar
            # is genuinely empty - resolved once the next line is seen.
            current_key, current_list = key, []
            continue
        if raw_value.startswith("[") and raw_value.endswith("]"):
            inner = raw_value[1:-1].strip()
            result[key] = [] if inner == "" else [_strip_quotes(item) for item in _split_flow_list(inner)]
        else:
            result[key] = _strip_quotes(raw_value)

    if current_list is not None:
        result[current_key] = current_list
    return result


def parse_frontmatter(text: str) -> dict[str, str | list[str]]:
    """A `STATE.md`'s frontmatter block (flat scalars + string lists,
    `goal`/`paths`/`done_when`/`out_of_scope`/`source`/`path`/`key_info`/
    `flags`) as a dict. `text` is the whole file's content. `{}` if there's
    no well-formed opening+closing `---` pair - never raises on malformed
    content."""
    bounds = _frontmatter_bounds(text.splitlines())
    if bounds is None:
        return {}
    lines = text.splitlines()
    return _parse_frontmatter_lines(lines[bounds[0] : bounds[1]])


def draft_summary(text: str) -> tuple[str, str]:
    """A `review` folder's `DRAFT.md` has no frontmatter - `/cairn-triage`
    step 1's own treatment ("one trailing line") is mirrored here for both
    ends: the first non-empty line (the draft's own title) stands in for
    `goal`, the last non-empty line stands in for `key_info`."""
    non_empty = [line.strip() for line in text.splitlines() if line.strip()]
    if not non_empty:
        return "", ""
    goal = non_empty[0].lstrip("#").strip()
    return goal, non_empty[-1]


_ACTIVITY_DATE = r"\d{4}-\d{2}-\d{2}(?:/\d{2})?"
_ACTIVITY_START_RE = re.compile(
    rf"^(?:- (?P<date>{_ACTIVITY_DATE})(?: (?P<time>\d{{2}}:\d{{2}}))?:?"
    rf"|(?P<bare_date>{_ACTIVITY_DATE})(?: (?P<bare_time>\d{{2}}:\d{{2}}))?:)\s*"
)


def parse_activity(text: str) -> list[dict]:
    """`STATE.md`'s append-only log, after its frontmatter, split into one
    timeline entry per dated line, in either of the two forms real task
    folders use: dashed (`- YYYY-MM-DD[ HH:MM][:]`) or bare
    (`YYYY-MM-DD[ HH:MM]:`, where the trailing colon is required so a prose
    line that merely starts with a date is not taken for an entry). A
    `YYYY-MM-DD/DD` date-range prefix is also recognized. Each entry
    is `{date, time, text}`, `time` being the line's `HH:MM` or None when it
    has none. Every real entry in this repo is written as one dense line,
    never soft-wrapped, so an entry's text is exactly that line's own
    content after its dated prefix; a line in neither form - the `cairn:shared`-template blockquote that precedes
    the first entry, a blank separator line, or hand-edited stray content -
    is dropped outright rather than folded into whichever entry precedes
    it, and never errors the whole parse (degrade, not crash)."""
    lines = text.splitlines()
    bounds = _frontmatter_bounds(lines)
    body_lines = lines[bounds[1] + 1 :] if bounds is not None else lines

    entries: list[dict] = []
    for line in body_lines:
        match = _ACTIVITY_START_RE.match(line)
        if match:
            entries.append(
                {
                    "date": match.group("date") or match.group("bare_date"),
                    "time": match.group("time") or match.group("bare_time"),
                    "text": line[match.end() :].strip(),
                }
            )
        # else: dropped - either precedes the first entry (blockquote/blank)
        # or is unparseable stray content.
    return entries


def list_docs(folder_dir: Path) -> list[dict]:
    """Every `*.md` file directly under `folder_dir` except whichever of
    `STATE.md`/`DRAFT.md` the Details tab already shows (`DRAFT.md` only
    when there is no `STATE.md`, as in an older `review` folder), as name/byte-size/
    mtime metadata only - never content. Not recursive: a subfolder
    of loose assets (`wireframes/`, `mockups/`) is never a "doc" and isn't
    listed. Filesystem mtime is the "last touched" signal."""
    docs: list[dict] = []
    shown = {"STATE.md"} if (folder_dir / "STATE.md").is_file() else {"DRAFT.md"}
    for path in sorted(folder_dir.glob("*.md")):
        if path.name in shown or not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        docs.append(
            {
                "name": path.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
            }
        )
    return docs


def resolve_task_folder(project_root: Path, folder: str) -> Path | None:
    """The client-supplied, project-root-relative `folder` path, resolved
    and guarded to stay under that project's own `docs/tasks/` - refuses
    (returns `None`) a `folder` that resolves outside it, or that isn't a
    real directory, rather than degrading to a partial or wrong read."""
    if not folder:
        return None
    try:
        tasks_root = (project_root / "docs" / "tasks").resolve()
        candidate = (project_root / folder).resolve()
    except (OSError, RuntimeError, ValueError):  # a symlink loop or NUL refuses, not crashes
        return None
    try:
        candidate.relative_to(tasks_root)
    except ValueError:
        return None
    return candidate if candidate.is_dir() else None


def safe_task_doc_path(folder_dir: Path, file_name: str) -> Path | None:
    """`file_name` resolved as a direct child of the already-resolved
    `folder_dir` - `.md` extension only, no escaping via `..`/`/` in the
    name itself . Refuses, rather than degrades, anything else."""
    if not file_name or not file_name.endswith(".md"):
        return None
    try:
        candidate = (folder_dir / file_name).resolve()
    except (OSError, RuntimeError, ValueError):  # a symlink loop or NUL refuses, not crashes
        return None
    try:
        candidate.relative_to(folder_dir.resolve())
    except ValueError:
        return None
    if candidate.parent != folder_dir.resolve():
        return None
    return candidate


# Image types `/api/tasks/asset` serves, keyed on lowercased suffix. A fixed
# table rather than `mimetypes`, whose answers vary with the host's own
# registry; SVG is absent on purpose (an SVG opened directly can run script
# in the dashboard's origin).
TASK_ASSET_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def safe_task_asset_path(folder_dir: Path, rel: str) -> Path | None:
    """`rel` (subfolders allowed, e.g. `mockups/y.webp`) resolved inside the
    already-resolved `folder_dir` - an allow-listed image type both as
    requested and after symlink resolution, still inside the folder once
    resolved, and a real file. Refuses (returns `None`) anything else:
    `..` segments, absolute paths, backslashes, NULs, symlink escapes."""
    if not rel or "\x00" in rel or "\\" in rel or rel.startswith("/"):
        return None
    if any(segment == ".." for segment in rel.split("/")):
        return None
    if Path(rel).suffix.lower() not in TASK_ASSET_TYPES:
        return None
    try:
        root = folder_dir.resolve()
        candidate = (folder_dir / rel).resolve()
    except (OSError, RuntimeError, ValueError):  # a symlink loop or NUL refuses, not crashes
        return None
    if not candidate.is_relative_to(root):
        return None
    if candidate.suffix.lower() not in TASK_ASSET_TYPES:
        return None
    return candidate if candidate.is_file() else None
