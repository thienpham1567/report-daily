"""Story 1.3 — Build the Vietnamese narration script (AC 1.3.1).

Produces the spoken report text from the grouped task payload. The opening
sentence follows the exact template required by AC 1.3.1, followed by a readout
of each task title, grouped by category.

``build_script_with_sections`` additionally returns per-section character counts
so that ``video.py`` can synchronise slide timings proportionally to narration
length (chars ∝ speech duration at constant TTS speed).
"""

from __future__ import annotations

_SECTION_TITLES = {
    "features": "Các tính năng đã hoàn thành",
    "fixes": "Các lỗi đã được sửa",
    "quality": "Các tác vụ nâng cao chất lượng code",
}


def _readout(titles: list[str]) -> str:
    """Join task titles into spoken, numbered sentences."""
    parts = []
    for i, title in enumerate(titles, start=1):
        clean = title.rstrip(". ")
        parts.append(f"{i}. {clean}.")
    return " ".join(parts)


def build_script(payload: dict, reporter_name: str = "Thienpham") -> str:
    """Return the full narration text for the given task payload."""
    result = build_script_with_sections(payload, reporter_name)
    return result["script"]


def build_script_with_sections(
    payload: dict, reporter_name: str = "Thienpham"
) -> dict:
    """Return the full narration script **and** per-section metadata.

    Returns
    -------
    dict with keys:
        ``script`` : str — full narration text (unchanged from ``build_script``).
        ``sections`` : list[dict] — one entry per slide, each with:
            ``name``  : ``"title"`` | ``"features"`` | ``"fixes"``
            ``text``  : the narration text spoken during this slide
            ``chars`` : len(text) — used to compute proportional timing
    """
    date = payload.get("date", "")
    categories = payload.get("categories", {})
    features = categories.get("features", [])
    fixes = categories.get("fixes", [])
    quality = categories.get("quality", [])

    x, y, z = len(features), len(fixes), len(quality)

    # ── Section 1: Intro (maps to Slide 1 — title slide) ──
    intro = (
        f"Chào mọi người, đây là báo cáo công việc ngày {date} của {reporter_name}. "
        f"Hôm nay tôi đã hoàn thành {x} tính năng, sửa {y} lỗi "
        f"và cập nhật {z} tác vụ nâng cao chất lượng code."
    )

    if payload.get("empty") or (x + y + z) == 0:
        empty_text = (
            intro
            + " Hôm nay không có commit nào được ghi nhận. Cảm ơn mọi người đã lắng nghe."
        )
        return {
            "script": empty_text,
            "sections": [
                {"name": "title", "text": empty_text, "chars": len(empty_text)},
                {"name": "features", "text": "", "chars": 0},
                {"name": "fixes", "text": "", "chars": 0},
            ],
        }

    # ── Section 2: Features (maps to Slide 2) ──
    feat_text = ""
    if features:
        feat_text = f"{_SECTION_TITLES['features']}: {_readout(features)}"

    # ── Section 3: Fixes + Quality (maps to Slide 3) ──
    fix_parts = []
    if fixes:
        fix_parts.append(f"{_SECTION_TITLES['fixes']}: {_readout(fixes)}")
    if quality:
        fix_parts.append(f"{_SECTION_TITLES['quality']}: {_readout(quality)}")
    fix_text = " ".join(fix_parts)

    # Closing sentence — appended to the last non-empty section.
    closing = "Đó là toàn bộ báo cáo hôm nay. Cảm ơn mọi người đã lắng nghe."

    # Attach closing to whichever section is last (fixes if present, else features).
    if fix_text:
        fix_text = f"{fix_text} {closing}"
    elif feat_text:
        feat_text = f"{feat_text} {closing}"
    else:
        intro = f"{intro} {closing}"

    # Assemble full script (space-joined, just like the old build_script).
    all_parts = [intro]
    if feat_text:
        all_parts.append(feat_text)
    if fix_text:
        all_parts.append(fix_text)
    full_script = " ".join(all_parts)

    return {
        "script": full_script,
        "sections": [
            {"name": "title", "text": intro, "chars": len(intro)},
            {"name": "features", "text": feat_text, "chars": len(feat_text)},
            {"name": "fixes", "text": fix_text, "chars": len(fix_text)},
        ],
    }


# ---------------------------------------------------------------------------
# DevZone Tasks-based narration script
# ---------------------------------------------------------------------------

def _task_readout(tasks: list[dict]) -> str:
    """Build spoken list from DevZone task entries."""
    parts = []
    for i, t in enumerate(tasks, start=1):
        title = t.get("title", "").rstrip(". ")
        story = t.get("story_clean", "") or t.get("story", "").lstrip("🔷🔶 ").rstrip(". ")
        story = story.rstrip(". ")
        app = t.get("app_type", "")
        app_label = " bên Client app" if app == "client" else " bên Admin app" if app == "admin" else ""

        if story and story != title:
            parts.append(f"{i}. {title}, thuộc story {story}{app_label}.")
        else:
            parts.append(f"{i}. {title}{app_label}.")
    return " ".join(parts)


def build_script_from_tasks(
    task_payload: dict, reporter_name: str = "Thienpham"
) -> dict:
    """Build narration script from DevZone task payload (from ``devzone_tasks.py``).

    Returns the same shape as ``build_script_with_sections`` — dict with
    ``script`` and ``sections`` keys — so it's a drop-in data source for
    ``video.py`` character-proportional timing.

    Slide mapping:
        - Slide 1 (title): Intro + summary counts
        - Slide 2 (done): List of completed tasks
        - Slide 3 (active): Doing + Todo + Pending tasks
    """
    date = task_payload.get("date", "")
    tasks_by_status = task_payload.get("tasks_by_status", {})
    summary = task_payload.get("summary", {})

    done = tasks_by_status.get("done", [])
    doing = tasks_by_status.get("doing", []) + tasks_by_status.get("in-progress", [])
    todo = tasks_by_status.get("todo", [])
    pending = tasks_by_status.get("pending", [])
    review = tasks_by_status.get("review", [])

    n_done = len(done)
    n_doing = len(doing)
    n_remaining = len(todo) + len(pending) + len(review)

    # ── Section 1: Intro (Slide 1 — title) ──
    intro = (
        f"Chào mọi người, đây là báo cáo công việc ngày {date} của {reporter_name}. "
        f"Hôm nay tôi đã xong {n_done} task"
    )
    if n_doing:
        intro += f", đang xử lý {n_doing} task"
    if n_remaining:
        intro += f" và còn {n_remaining} task chờ xử lý"
    intro += "."

    total = n_done + n_doing + n_remaining
    if total == 0:
        empty_text = intro + " Hôm nay không có task nào được cập nhật. Cảm ơn mọi người đã lắng nghe."
        return {
            "script": empty_text,
            "sections": [
                {"name": "title", "text": empty_text, "chars": len(empty_text)},
                {"name": "done", "text": "", "chars": 0},
                {"name": "active", "text": "", "chars": 0},
            ],
        }

    # ── Section 2: Done tasks (Slide 2) ──
    done_text = ""
    if done:
        done_text = f"Các task đã xong: {_task_readout(done)}"

    # ── Section 3: Active tasks — doing + todo + pending (Slide 3) ──
    active_parts = []
    if doing:
        active_parts.append(f"Các task đang xử lý: {_task_readout(doing)}")
    if todo:
        active_parts.append(f"Các task chờ xử lý: {_task_readout(todo)}")
    if pending:
        active_parts.append(f"Các task hoãn lại: {_task_readout(pending)}")
    if review:
        active_parts.append(f"Các task đang review: {_task_readout(review)}")
    active_text = " ".join(active_parts)

    # Closing — attach to last non-empty section.
    closing = "Đó là toàn bộ báo cáo hôm nay. Cảm ơn mọi người đã lắng nghe."
    if active_text:
        active_text = f"{active_text} {closing}"
    elif done_text:
        done_text = f"{done_text} {closing}"
    else:
        intro = f"{intro} {closing}"

    # Full script.
    all_parts = [intro]
    if done_text:
        all_parts.append(done_text)
    if active_text:
        all_parts.append(active_text)
    full_script = " ".join(all_parts)

    return {
        "script": full_script,
        "sections": [
            {"name": "title", "text": intro, "chars": len(intro)},
            {"name": "done", "text": done_text, "chars": len(done_text)},
            {"name": "active", "text": active_text, "chars": len(active_text)},
        ],
    }

