"""DevZone daily task tracker — fetch & filter tasks for today's report.

Connects to the DevZone ERP API, pulls all tasks assigned to the configured
user, and groups them by status for the daily report.

Authentication:
    - **Bearer token** (preferred): Set ``DEVZONE_BEARER_TOKEN`` in ``.env``.
      This is the JWT from the DevZone web app (inspect any API request in
      Network tab → copy the ``authorization: Bearer …`` value).
    - **X-API-Key** fallback: Uses the existing ``DEVZONE_API_KEY``.

Usage (standalone):
    python -m reporter.devzone_tasks [--date YYYY-MM-DD] [--json]
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date as _date, datetime
from pathlib import Path
from typing import Optional


# Status display order and Vietnamese labels.
STATUS_ORDER = ["done", "doing", "in-progress", "todo", "pending", "review"]
STATUS_LABELS = {
    "done": ("✅", "Đã xong"),
    "doing": ("🔄", "Đang xử lý"),
    "in-progress": ("🔄", "Đang xử lý"),
    "todo": ("📋", "Chờ xử lý"),
    "pending": ("⏳", "Hoãn lại"),
    "review": ("👀", "Đang review"),
}


class DevZoneTaskError(RuntimeError):
    pass


def _clean_story(story_title: str) -> str:
    """Strip emoji prefix (🔷/🔶) from a story title."""
    return story_title.lstrip("🔷🔶 ").strip()


def _detect_app_type(story_title: str) -> str:
    """Detect app type from story title emoji prefix.

    - ``🔷`` → ``"client"`` (Client app — blue)
    - ``🔶`` → ``"admin"``  (Admin app — orange)
    - Otherwise → ``""``
    """
    s = story_title.strip()
    if s.startswith("🔷"):
        return "client"
    if s.startswith("🔶"):
        return "admin"
    return ""


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _build_headers(bearer_token: str = "", api_key: str = "") -> dict[str, str]:
    """Build request headers, preferring Bearer token over X-API-Key."""
    headers = {
        "accept": "application/json",
        "origin": "https://devzone.vietnix.dev",
        "referer": "https://devzone.vietnix.dev/",
    }
    if bearer_token:
        headers["authorization"] = (
            bearer_token if bearer_token.startswith("Bearer ")
            else f"Bearer {bearer_token}"
        )
    elif api_key:
        headers["X-API-Key"] = api_key
    else:
        raise DevZoneTaskError(
            "No authentication configured. "
            "Set DEVZONE_BEARER_TOKEN or DEVZONE_API_KEY in .env"
        )
    return headers


def fetch_all_tasks(
    base_url: str,
    project_id: str,
    bearer_token: str = "",
    api_key: str = "",
    timeout: int = 30,
) -> list[dict]:
    """Fetch all tasks from a DevZone project (single request, limit=9999)."""
    import requests

    url = f"{base_url}/workspace/projects/{project_id}/tasks"
    params = {"limit": "9999", "sorts": "position"}
    headers = _build_headers(bearer_token, api_key)

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        raise DevZoneTaskError(f"Failed to fetch tasks: {exc}") from exc

    data = resp.json()
    return data.get("items", [])


# ---------------------------------------------------------------------------
# Filtering & grouping
# ---------------------------------------------------------------------------

def filter_user_tasks(
    tasks: list[dict],
    user_id: str,
) -> list[dict]:
    """Return only tasks **assigned to** ``user_id``.

    Checks multiple fields because the DevZone API shape can vary:
    - ``assigneeId`` — single assignee (most common)
    - ``assignees``  — array of assignee objects (multi-assign)
    - ``members``    — array of member objects (alternative schema)

    Does NOT match ``userId`` (task creator) — a task you created but
    isn't assigned to you should not appear in your daily report.
    """
    result = []
    for t in tasks:
        # Direct assigneeId match (most common).
        if t.get("assigneeId") == user_id:
            result.append(t)
            continue

        # Check assignees array: [{id: "...", ...}, ...]
        assignees = t.get("assignees") or []
        if any(
            (a.get("id") == user_id or a.get("userId") == user_id)
            for a in assignees
            if isinstance(a, dict)
        ):
            result.append(t)
            continue

        # Check members array (alternative schema).
        members = t.get("members") or []
        if any(
            (m.get("id") == user_id or m.get("userId") == user_id)
            for m in members
            if isinstance(m, dict)
        ):
            result.append(t)
            continue

    return result


def filter_today_tasks(
    tasks: list[dict],
    report_date: str | None = None,
) -> list[dict]:
    """Return tasks that were updated, completed, or created on ``report_date``.

    ``report_date`` defaults to today (``YYYY-MM-DD``).
    """
    target = report_date or _date.today().isoformat()

    result = []
    for t in tasks:
        # Check multiple date fields — a task is "today" if ANY of them match.
        for field in ("updatedAt", "completedAt", "createdAt"):
            val = t.get(field)
            if val and val[:10] == target:
                result.append(t)
                break
    return result


def group_by_status(tasks: list[dict]) -> dict[str, list[dict]]:
    """Group tasks into buckets keyed by status string."""
    groups: dict[str, list[dict]] = {}
    for t in tasks:
        status = t.get("status", "unknown")
        groups.setdefault(status, []).append(t)
    return groups


# ---------------------------------------------------------------------------
# Structured payload (mirrors git_extractor output shape)
# ---------------------------------------------------------------------------

def build_task_payload(
    tasks: list[dict],
    report_date: str | None = None,
    user_name: str = "",
) -> dict:
    """Build a structured payload summarising today's tasks.

    Returns a dict with:
        - ``date``, ``user``
        - ``tasks_by_status``: {status: [{title, story, completedAt, ...}, …]}
        - ``summary``: {done: N, doing: N, todo: N, pending: N, total: N}
    """
    target = report_date or _date.today().isoformat()

    tasks_by_status: dict[str, list[dict]] = {}
    for t in tasks:
        status = t.get("status", "unknown")
        doc = t.get("document") or {}
        entry = {
            "id": t.get("id", ""),
            "title": t.get("title", ""),
            "status": status,
            "story": doc.get("title", ""),
            "story_type": doc.get("type", ""),
            "story_clean": _clean_story(doc.get("title", "")),
            "app_type": _detect_app_type(doc.get("title", "")),
            "createdAt": t.get("createdAt", ""),
            "updatedAt": t.get("updatedAt", ""),
            "completedAt": t.get("completedAt"),
            "tags": [
                tag.get("name", "") for tag in t.get("tags", [])
                if isinstance(tag, dict)
            ],
        }
        tasks_by_status.setdefault(status, []).append(entry)

    summary = {s: len(tasks_by_status.get(s, [])) for s in STATUS_ORDER}
    summary["total"] = len(tasks)

    return {
        "date": target,
        "user": user_name,
        "tasks_by_status": tasks_by_status,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Pretty-print for terminal / daily report
# ---------------------------------------------------------------------------

def format_report(payload: dict) -> str:
    """Render a human-readable Vietnamese daily task report."""
    lines: list[str] = []
    date = payload.get("date", "")
    user = payload.get("user", "")
    summary = payload.get("summary", {})
    tasks_by_status = payload.get("tasks_by_status", {})

    lines.append(f"{'='*60}")
    lines.append(f"📋 BÁO CÁO TASKS NGÀY {date} — {user}")
    lines.append(f"{'='*60}")
    lines.append("")

    # Summary bar.
    parts = []
    for status in STATUS_ORDER:
        count = summary.get(status, 0)
        if count > 0:
            icon, label = STATUS_LABELS.get(status, ("❓", status))
            parts.append(f"{icon} {label}: {count}")
    lines.append(" | ".join(parts))
    lines.append(f"📊 Tổng cộng: {summary.get('total', 0)} tasks")
    lines.append("")

    # Detail sections.
    for status in STATUS_ORDER:
        tasks = tasks_by_status.get(status, [])
        if not tasks:
            continue
        icon, label = STATUS_LABELS.get(status, ("❓", status))
        lines.append(f"--- {icon} {label.upper()} ({len(tasks)}) ---")
        for i, t in enumerate(tasks, 1):
            title = t.get("title", "(không có tiêu đề)")
            story = t.get("story", "")
            completed = t.get("completedAt")
            tags = t.get("tags", [])

            lines.append(f"  {i}. {title}")
            if story:
                lines.append(f"     └─ Story: {story}")
            if completed:
                # Show time in UTC+7.
                try:
                    dt = datetime.fromisoformat(completed.replace("Z", "+00:00"))
                    from datetime import timezone, timedelta
                    vn = timezone(timedelta(hours=7))
                    local = dt.astimezone(vn)
                    lines.append(f"     └─ Hoàn thành lúc: {local.strftime('%H:%M %d/%m')}")
                except Exception:
                    lines.append(f"     └─ Hoàn thành: {completed[:16]}")
            if tags:
                lines.append(f"     └─ Tags: {', '.join(tags)}")
        lines.append("")

    # Handle unknown statuses.
    for status, tasks in tasks_by_status.items():
        if status not in STATUS_ORDER and tasks:
            lines.append(f"--- ❓ {status.upper()} ({len(tasks)}) ---")
            for i, t in enumerate(tasks, 1):
                lines.append(f"  {i}. {t.get('title', '')}")
                story = t.get("story", "")
                if story:
                    lines.append(f"     └─ Story: {story}")
            lines.append("")

    lines.append(f"{'='*60}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# High-level convenience — one-call daily task report
# ---------------------------------------------------------------------------

def get_daily_tasks(
    base_url: str = "",
    project_id: str = "",
    bearer_token: str = "",
    api_key: str = "",
    user_id: str = "",
    user_name: str = "",
    report_date: str | None = None,
) -> dict:
    """All-in-one: fetch → filter → build payload for today's tasks.

    Falls back to environment variables / .env for any empty parameter.
    """
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    base_url = base_url or os.environ.get("DEVZONE_BASE_URL", "https://api.devzone.vietnix.dev")
    project_id = project_id or os.environ.get("DEVZONE_PROJECT_ID", "")
    bearer_token = bearer_token or os.environ.get("DEVZONE_BEARER_TOKEN", "")
    api_key = api_key or os.environ.get("DEVZONE_API_KEY", "")
    user_id = user_id or os.environ.get("DEVZONE_USER_ID", "")
    user_name = user_name or os.environ.get("REPORTER_NAME", "")

    if not project_id:
        raise DevZoneTaskError("DEVZONE_PROJECT_ID is not configured.")
    if not user_id:
        raise DevZoneTaskError(
            "DEVZONE_USER_ID is not configured. "
            "Find your user ID on DevZone and set it in .env"
        )

    # Step 1: Fetch all tasks.
    all_tasks = fetch_all_tasks(
        base_url, project_id,
        bearer_token=bearer_token, api_key=api_key,
    )

    # Step 2: Filter by user.
    my_tasks = filter_user_tasks(all_tasks, user_id)

    # Step 3: Filter by date.
    today_tasks = filter_today_tasks(my_tasks, report_date)

    # Step 4: Build payload.
    return build_task_payload(today_tasks, report_date, user_name)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch & display today's DevZone tasks for the configured user."
    )
    parser.add_argument("--date", help="Report date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--json", action="store_true", help="Output raw JSON payload")
    parser.add_argument("--all-statuses", action="store_true",
                        help="Show all user tasks, not just today's")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    except ImportError:
        pass

    base_url = os.environ.get("DEVZONE_BASE_URL", "https://api.devzone.vietnix.dev")
    project_id = os.environ.get("DEVZONE_PROJECT_ID", "")
    bearer_token = os.environ.get("DEVZONE_BEARER_TOKEN", "")
    api_key = os.environ.get("DEVZONE_API_KEY", "")
    user_id = os.environ.get("DEVZONE_USER_ID", "")
    user_name = os.environ.get("REPORTER_NAME", "")

    try:
        all_tasks = fetch_all_tasks(
            base_url, project_id,
            bearer_token=bearer_token, api_key=api_key,
        )
        my_tasks = filter_user_tasks(all_tasks, user_id)

        if args.all_statuses:
            target_tasks = my_tasks
        else:
            target_tasks = filter_today_tasks(my_tasks, args.date)

        payload = build_task_payload(target_tasks, args.date, user_name)

        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(format_report(payload))

        return 0
    except DevZoneTaskError as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"❌ Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
