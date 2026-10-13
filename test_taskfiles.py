import os
from pathlib import Path

import pytest

import taskfiles

STATE = """---
goal: Ship the thing
paths: [a/, b/]
key_info: building, next is review
flags:
  - first flag
  - "second, flag"
---

2026-10-01 09:00: started
2026-10-02: halfway
stray prose line
"""


def test_frontmatter_scalars_lists_and_block_lists():
    fm = taskfiles.parse_frontmatter(STATE)
    assert fm["goal"] == "Ship the thing"
    assert fm["paths"] == ["a/", "b/"]
    assert fm["flags"] == ["first flag", "second, flag"]


def test_frontmatter_missing_or_unclosed_is_empty():
    assert taskfiles.parse_frontmatter("no fm here") == {}
    assert taskfiles.parse_frontmatter("---\ngoal: x\n") == {}


def test_activity_keeps_dated_lines_only():
    entries = taskfiles.parse_activity(STATE)
    assert [(e["date"], e["time"], e["text"]) for e in entries] == [
        ("2026-10-01", "09:00", "started"),
        ("2026-10-02", None, "halfway"),
    ]


def test_draft_summary_uses_first_and_last_lines():
    assert taskfiles.draft_summary("# Title\n\nbody\n\nverdict line\n") == ("Title", "verdict line")
    assert taskfiles.draft_summary("\n\n") == ("", "")


def test_list_docs_skips_state_and_nested(tmp_path):
    (tmp_path / "STATE.md").write_text("x")
    (tmp_path / "PLAN.md").write_text("plan")
    (tmp_path / "notes.txt").write_text("n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.md").write_text("d")
    assert [d["name"] for d in taskfiles.list_docs(tmp_path)] == ["PLAN.md"]


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / "docs" / "tasks" / "t1"
    folder.mkdir(parents=True)
    (folder / "STATE.md").write_text(STATE)
    (folder / "mockup.png").write_bytes(b"png")
    (folder / "icon.svg").write_text("<svg/>")
    (tmp_path / "secret.md").write_text("secret")
    return tmp_path


def test_resolve_folder_guards(project):
    assert taskfiles.resolve_task_folder(project, "docs/tasks/t1") == (project / "docs/tasks/t1").resolve()
    for bad in ["", "docs/tasks/../..", "..", "/etc", "docs/tasks/missing", "docs"]:
        assert taskfiles.resolve_task_folder(project, bad) is None


def test_resolve_folder_refuses_symlink_escape(project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    os.symlink(outside, project / "docs" / "tasks" / "link")
    assert taskfiles.resolve_task_folder(project, "docs/tasks/link") is None


def test_doc_guard_allows_direct_md_only(project):
    folder = (project / "docs/tasks/t1").resolve()
    assert taskfiles.safe_task_doc_path(folder, "STATE.md") == folder / "STATE.md"
    for bad in ["", "../../../secret.md", "sub/x.md", "STATE.txt", "/etc/passwd.md"]:
        assert taskfiles.safe_task_doc_path(folder, bad) is None


def test_asset_guard_allows_images_only(project):
    folder = (project / "docs/tasks/t1").resolve()
    assert taskfiles.safe_task_asset_path(folder, "mockup.png") == folder / "mockup.png"
    for bad in ["icon.svg", "../x.png", "/x.png", "a\\b.png", "STATE.md", "missing.png"]:
        assert taskfiles.safe_task_asset_path(folder, bad) is None
