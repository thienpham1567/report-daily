"""Unit tests for the deterministic pipeline logic (Stories 1.2, 1.3, 1.5)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reporter import git_extractor, script_builder, devzone  # noqa: E402


SAMPLE = [
    "feat: Add login validation",
    "feature: support OAuth",
    "fix: Fix button alignment",
    "bug: crash on empty input",
    "docs: Update README.md",
    "refactor: extract helper",
    "test: add coverage",
    "chore: bump deps",
    "Merge branch 'main' into dev",  # must be filtered (AC 1.2.2)
    "style: reformat",  # routed to quality
    "random commit without prefix",  # quality fallback
]


# --- Story 1.2 ---------------------------------------------------------------

def test_extract_groups_and_filters_merges():
    payload = git_extractor.extract_tasks(
        Path("."), report_date="2026-06-01", _raw_subjects=SAMPLE
    )
    cats = payload["categories"]
    assert "Add login validation" in cats["features"]
    assert "Support OAuth" in cats["features"]
    assert "Fix button alignment" in cats["fixes"]
    assert "Crash on empty input" in cats["fixes"]
    assert "Update README.md" in cats["quality"]
    # merge commit filtered out
    assert not any("Merge branch" in c for c in payload["commits"])
    assert payload["total"] == len(SAMPLE) - 1
    assert payload["date"] == "2026-06-01"


def test_extract_payload_shape():
    payload = git_extractor.extract_tasks(
        Path("."), report_date="2026-06-01", _raw_subjects=SAMPLE
    )
    assert set(payload["categories"].keys()) == {"features", "fixes", "quality"}


def test_extract_empty_fallback():
    payload = git_extractor.extract_tasks(
        Path("."), report_date="2026-06-01", _raw_subjects=[]
    )
    assert payload.get("empty") is True
    assert payload["message"] == "No commits recorded today"
    assert payload["total"] == 0


# --- Story 1.3 (script) ------------------------------------------------------

def test_script_intro_template():
    payload = git_extractor.extract_tasks(
        Path("."), report_date="2026-06-01", _raw_subjects=SAMPLE
    )
    script = script_builder.build_script(payload, reporter_name="Thienpham")
    assert "Chào mọi người, đây là báo cáo công việc ngày 2026-06-01 của Thienpham" in script
    # counts: 2 features, 2 fixes, rest quality
    assert "hoàn thành 2 tính năng, sửa 2 lỗi" in script


def test_script_empty():
    payload = git_extractor.extract_tasks(
        Path("."), report_date="2026-06-01", _raw_subjects=[]
    )
    script = script_builder.build_script(payload)
    assert "không có commit nào được ghi nhận" in script.lower()


# --- Story 1.5 (markdown body) ----------------------------------------------

def test_markdown_contains_sections_and_video_link():
    payload = git_extractor.extract_tasks(
        Path("."), report_date="2026-06-01", _raw_subjects=SAMPLE
    )
    md = devzone.build_markdown(payload, Path("_bmad-output/videos/report-2026-06-01.mp4"))
    assert "# Báo cáo công việc ngày 2026-06-01" in md
    assert "Tính năng (Features)" in md
    assert "report-2026-06-01.mp4" in md
    assert "`feat: Add login validation`" in md  # raw commit list


def test_extract_document_id_variants():
    assert devzone.extract_document_id({"id": "abc"}) == "abc"
    assert devzone.extract_document_id({"data": {"_id": "xyz"}}) == "xyz"
    assert devzone.extract_document_id({"documentId": 99}) == "99"
    assert devzone.extract_document_id({}) is None
