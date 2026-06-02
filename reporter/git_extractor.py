"""Story 1.2 — Task extraction and parsing logic.

Runs ``git log`` for today's commits by the target author, drops merge commits,
and groups the remaining commits into Features / Fixes / Quality buckets, emitting
a structured JSON payload (AC 1.2.4).
"""

from __future__ import annotations

import re
import subprocess
from datetime import date as _date
from pathlib import Path
from typing import Optional

# Conventional-commit prefix -> category (AC 1.2.3).
_PREFIX_MAP = {
    "feat": "features",
    "feature": "features",
    "fix": "fixes",
    "bug": "fixes",
    "docs": "quality",
    "refactor": "quality",
    "test": "quality",
    "chore": "quality",
    # Common extras routed to "quality" so nothing is silently dropped.
    "style": "quality",
    "perf": "quality",
    "build": "quality",
    "ci": "quality",
}

_PREFIX_RE = re.compile(r"^\s*(\w+)(?:\([^)]*\))?\s*:\s*(.*)$")
_MERGE_RE = re.compile(r"^Merge\b", re.IGNORECASE)


def _run_git_log(repo: Path, author: str, since: str) -> list[str]:
    """Return raw commit subject lines (AC 1.2.1). ``--no-merges`` plus an explicit
    "Merge ..." filter (AC 1.2.2) guards against both real and squashed merges."""
    # Convert "today" to explicit midnight timestamp to avoid git timezone quirks.
    if since.strip().lower() == "today":
        since = _date.today().isoformat() + "T00:00:00"

    cmd = [
        "git",
        "-C",
        str(repo),
        "log",
        f"--since={since}",
        f"--author={author}",
        "--no-merges",
        "-i",  # case-insensitive author match
        "--pretty=format:%s",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=30
        )
    except subprocess.CalledProcessError as exc:  # not a git repo / git error
        raise RuntimeError(f"git log failed: {exc.stderr.strip()}") from exc
    except FileNotFoundError as exc:
        raise RuntimeError("git executable not found on PATH") from exc

    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    return [ln for ln in lines if not _MERGE_RE.match(ln.strip())]


def _classify(subject: str) -> tuple[str, str]:
    """Return (category, cleaned_title) for a commit subject."""
    m = _PREFIX_RE.match(subject)
    if m:
        prefix = m.group(1).lower()
        body = m.group(2).strip() or subject.strip()
        category = _PREFIX_MAP.get(prefix, "quality")
        title = body[:1].upper() + body[1:] if body else body
        return category, title
    # No conventional prefix — keep verbatim, treat as quality work.
    return "quality", subject.strip()


def extract_tasks(
    repo: Path,
    author: str = "Thienpham",
    since: str = "today",
    report_date: Optional[str] = None,
    _raw_subjects: Optional[list[str]] = None,
) -> dict:
    """Build the grouped JSON payload (AC 1.2.4 / 1.2.5).

    ``_raw_subjects`` lets tests inject commit lines without invoking git.
    """
    report_date = report_date or _date.today().isoformat()
    raw = _raw_subjects if _raw_subjects is not None else _run_git_log(
        Path(repo), author, since
    )
    # AC 1.2.2 — always drop merge commits, regardless of source.
    subjects = [s for s in raw if s.strip() and not _MERGE_RE.match(s.strip())]

    categories: dict[str, list[str]] = {"features": [], "fixes": [], "quality": []}
    for subject in subjects:
        category, title = _classify(subject)
        categories[category].append(title)

    payload = {
        "date": report_date,
        "author": author,
        "categories": categories,
        "commits": list(subjects),
        "total": len(subjects),
    }

    # AC 1.2.5 — fallback when no commits were recorded.
    if not subjects:
        payload["empty"] = True
        payload["message"] = "No commits recorded today"

    return payload
