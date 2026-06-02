"""Story 1.3 — Build the Vietnamese narration script (AC 1.3.1).

Produces the spoken report text from the grouped task payload. The opening
sentence follows the exact template required by AC 1.3.1, followed by a readout
of each task title, grouped by category.
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
    date = payload.get("date", "")
    categories = payload.get("categories", {})
    features = categories.get("features", [])
    fixes = categories.get("fixes", [])
    quality = categories.get("quality", [])

    x, y, z = len(features), len(fixes), len(quality)

    intro = (
        f"Chào mọi người, đây là báo cáo công việc ngày {date} của {reporter_name}. "
        f"Hôm nay tôi đã hoàn thành {x} tính năng, sửa {y} lỗi "
        f"và cập nhật {z} tác vụ nâng cao chất lượng code."
    )

    if payload.get("empty") or (x + y + z) == 0:
        return (
            intro
            + " Hôm nay không có commit nào được ghi nhận. Cảm ơn mọi người đã lắng nghe."
        )

    sections = [intro]
    for key in ("features", "fixes", "quality"):
        titles = categories.get(key, [])
        if titles:
            sections.append(f"{_SECTION_TITLES[key]}: {_readout(titles)}")

    sections.append("Đó là toàn bộ báo cáo hôm nay. Cảm ơn mọi người đã lắng nghe.")
    return " ".join(sections)
