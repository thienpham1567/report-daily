"""Story 1.5 — DevZone knowledge-base upload integration.

Posts the daily report as a ``doc`` document to the DevZone ERP workspace using
``X-API-Key`` authentication (AC 1.5.2 / 1.5.3 / 1.5.4) and returns the created
document ID on ``201 Created`` (AC 1.5.5).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def build_markdown(payload: dict, video_path: Path, reporter_name: str = "Thienpham") -> str:
    """Build the Markdown document body (AC 1.5.4).

    Contains the structured tasks, the raw git commit list, and a link to the
    generated local video file.
    """
    date = payload.get("date", "")
    categories = payload.get("categories", {})
    features = categories.get("features", [])
    fixes = categories.get("fixes", [])
    quality = categories.get("quality", [])

    lines = [
        f"# Báo cáo công việc ngày {date}",
        "",
        f"**Người báo cáo:** {reporter_name}  ",
        f"**Tổng số commit:** {payload.get('total', 0)}",
        "",
        "## 📊 Tổng quan",
        f"- ✅ {len(features)} tính năng mới",
        f"- 🐛 {len(fixes)} lỗi đã sửa",
        f"- 🧹 {len(quality)} tác vụ nâng cao chất lượng",
        "",
    ]

    def section(emoji: str, title: str, items: list[str]) -> None:
        lines.append(f"## {emoji} {title}")
        if items:
            lines.extend(f"- {it}" for it in items)
        else:
            lines.append("_Không có_")
        lines.append("")

    section("🚀", "Tính năng (Features)", features)
    section("🐛", "Sửa lỗi (Fixes)", fixes)
    section("🧹", "Chất lượng (Quality)", quality)

    lines.append("## 📝 Danh sách commit (Git log)")
    commits = payload.get("commits", [])
    if commits:
        lines.extend(f"- `{c}`" for c in commits)
    else:
        lines.append("_Không có commit nào hôm nay._")
    lines.append("")

    lines.append("## 🎬 Video báo cáo")
    lines.append(f"`{video_path}`")
    lines.append("")
    lines.append("---")
    lines.append("_Báo cáo được tạo tự động bởi Daily Video Reporter._")

    return "\n".join(lines)


def upload_document(
    *,
    base_url: str,
    project_id: str,
    api_key: str,
    title: str,
    content: str,
    doc_type: str = "doc",
    parent_id: Optional[str] = None,
    timeout: int = 30,
) -> dict:
    """POST a document to DevZone. Returns the parsed JSON response.

    Raises ``RuntimeError`` on non-201 responses.
    """
    import requests

    if not api_key:
        raise RuntimeError("DEVZONE_API_KEY is not configured.")
    if not project_id:
        raise RuntimeError("DEVZONE_PROJECT_ID is not configured.")

    endpoint = f"{base_url}/workspace/projects/{project_id}/documents"
    body: dict = {"title": title, "type": doc_type, "content": content}
    if parent_id:
        body["parentId"] = parent_id

    resp = requests.post(
        endpoint,
        json=body,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        timeout=timeout,
    )

    if resp.status_code != 201:
        raise RuntimeError(
            f"DevZone upload failed: HTTP {resp.status_code} — {resp.text[:500]}"
        )

    data = resp.json() if resp.content else {}
    return data


def extract_document_id(response: dict) -> Optional[str]:
    """Pull the document id from a variety of plausible response shapes."""
    if not isinstance(response, dict):
        return None
    for key in ("id", "_id", "documentId"):
        if response.get(key):
            return str(response[key])
    data = response.get("data")
    if isinstance(data, dict):
        return extract_document_id(data)
    return None
