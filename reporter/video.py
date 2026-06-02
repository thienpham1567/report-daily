"""Story 1.4 — HeyGen HyperFrames video generation.

Generates an HTML composition (dark theme, Vietnix green/blue accents, large
Inter/Roboto typography — AC 1.4.1) with three slides (AC 1.4.2), embeds the
``report.wav`` narration as a synced audio track (AC 1.4.3), and renders a 1080p
MP4 via the HyperFrames CLI (AC 1.4.4).
"""

from __future__ import annotations

import html
import json
import shutil
import subprocess
from pathlib import Path

from . import config as _config

HYPERFRAMES_DIR = _config.ROOT / "video"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

# Vietnix-flavoured dark palette.
BG = "#0B1120"
PANEL = "#111c33"
GREEN = "#16C784"
BLUE = "#2D8CFF"
TEXT = "#E7ECF5"
MUTED = "#8A99B5"


def probe_duration(audio_path: Path) -> float:
    """Return audio duration in seconds via ffprobe."""
    cmd = [
        FFPROBE,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
    return float(out.stdout.strip())


def _slide_timings(total: float, n_features: int, n_fixes: int) -> tuple[float, float, float]:
    """Split total duration across (title, features, fixes) slides, roughly
    proportional to how much narration each section carries."""
    d_title = max(2.5, min(6.0, total * 0.18))
    remaining = max(total - d_title, 1.0)
    fw = n_features + 1
    xw = n_fixes + 1
    d_feat = remaining * fw / (fw + xw)
    d_fix = remaining - d_feat
    return round(d_title, 3), round(d_feat, 3), round(d_fix, 3)


def _timings_from_sections(total: float, sections: list[dict]) -> list[float]:
    """Split total audio duration proportionally to character counts per section.

    This ensures each slide stays visible for exactly as long as the TTS engine
    is narrating that section's text — keeping video and voice in sync.
    """
    chars = [max(s.get("chars", 0), 1) for s in sections]  # avoid div-by-zero
    total_chars = sum(chars)
    durations = [round(total * c / total_chars, 3) for c in chars]
    # Fix rounding drift so durations sum exactly to total.
    durations[-1] = round(total - sum(durations[:-1]), 3)
    return durations


def _list_html(items: list[str], accent: str) -> str:
    if not items:
        return f'<li style="color:{MUTED}">— Không có —</li>'
    return "\n".join(
        f'<li><span class="bullet" style="color:{accent}">▸</span> {html.escape(it)}</li>'
        for it in items
    )


def _task_list_html(tasks: list[dict], accent_class: str) -> str:
    """Render DevZone tasks as premium numbered card items with story parent."""
    if not tasks:
        return f'<li class="task-empty">— Không có task nào —</li>'
    items = []
    for i, t in enumerate(tasks, 1):
        title = html.escape(t.get("title", ""))
        story_clean = html.escape(t.get("story_clean", "") or "")
        app_type = t.get("app_type", "")

        # Story parent line
        story_html = ""
        if story_clean and story_clean != title:
            story_html = f'<div style="color:{MUTED};font-weight:400;font-size:26px;margin-top:6px">↳ Story: {story_clean}</div>'

        # App type badge
        app_html = _app_badge_html(app_type)

        items.append(
            f'<li class="task-item">'
            f'<span class="task-num {accent_class}">{i}</span>'
            f'<div style="flex:1"><div>{title}{app_html}</div>{story_html}</div>'
            f'</li>'
        )
    return "\n".join(items)


# Status badge config: (css_color, icon, label)
_STATUS_BADGE = {
    "doing":       (BLUE,  "🔄", "Đang xử lý"),
    "in-progress": (BLUE,  "🔄", "Đang xử lý"),
    "todo":        ("#E8B339", "📋", "Chờ xử lý"),
    "pending":     (MUTED, "⏳", "Hoãn lại"),
    "review":      ("#AB68FF", "👀", "Đang review"),
}


def _task_list_html_with_status(
    doing: list[dict],
    todo: list[dict],
    pending: list[dict],
    review: list[dict],
) -> str:
    """Render tasks grouped by status with status badge, story parent, and app color."""
    all_groups = [
        ("doing", doing),
        ("todo", todo),
        ("pending", pending),
        ("review", review),
    ]
    all_tasks = [(status, t) for status, tasks in all_groups for t in tasks]

    if not all_tasks:
        return '<li class="task-empty">— Không có task nào —</li>'

    items = []
    for i, (status, t) in enumerate(all_tasks, 1):
        title = html.escape(t.get("title", ""))
        story_clean = html.escape(t.get("story_clean", "") or "")
        app_type = t.get("app_type", "")
        badge_color, badge_icon, badge_label = _STATUS_BADGE.get(
            status, (MUTED, "❓", status)
        )

        # Story parent line
        story_html = ""
        if story_clean and story_clean != title:
            story_html = f'<div style="color:{MUTED};font-weight:400;font-size:26px;margin-top:6px">↳ Story: {story_clean}</div>'

        # App type badge
        app_html = _app_badge_html(app_type)

        items.append(
            f'<li class="task-item">'
            f'<span class="task-num blue">{i}</span>'
            f'<div style="flex:1"><div>{title}{app_html}</div>{story_html}</div>'
            f'<span class="status-badge" style="background:rgba({_hex_to_rgb(badge_color)},0.15);'
            f'color:{badge_color};border:1px solid rgba({_hex_to_rgb(badge_color)},0.3)">'
            f'{badge_icon} {badge_label}</span>'
            f'</li>'
        )
    return "\n".join(items)

# App type colors.
APP_CLIENT_COLOR = BLUE       # 🔷 Client app → blue
APP_ADMIN_COLOR = "#FF8C42"   # 🔶 Admin app → orange


def _app_badge_html(app_type: str) -> str:
    """Render a small inline badge for Client or Admin app."""
    if app_type == "client":
        return (
            f' <span class="app-badge" style="background:rgba({_hex_to_rgb(APP_CLIENT_COLOR)},0.15);'
            f'color:{APP_CLIENT_COLOR};border:1px solid rgba({_hex_to_rgb(APP_CLIENT_COLOR)},0.3)">'
            f'Client</span>'
        )
    if app_type == "admin":
        return (
            f' <span class="app-badge" style="background:rgba({_hex_to_rgb(APP_ADMIN_COLOR)},0.15);'
            f'color:{APP_ADMIN_COLOR};border:1px solid rgba({_hex_to_rgb(APP_ADMIN_COLOR)},0.3)">'
            f'Admin</span>'
        )
    return ""


def _hex_to_rgb(hex_color: str) -> str:
    """Convert '#RRGGBB' to 'R,G,B' for use in rgba()."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"
# DevZone Tasks-based video composition (character-proportional timing)
# ---------------------------------------------------------------------------

def build_task_composition_html(
    task_payload: dict,
    sections: list[dict],
    audio_rel: str,
    total: float,
    reporter_name: str = "",
) -> str:
    """Render index.html from DevZone tasks with character-proportional timing.

    Parameters
    ----------
    task_payload : dict
        Output of ``devzone_tasks.get_daily_tasks()``.
    sections : list[dict]
        Output of ``script_builder.build_script_from_tasks()["sections"]``.
    audio_rel : str
        Relative path to the audio file (e.g. ``"assets/report.wav"``).
    total : float
        Total audio duration in seconds.
    reporter_name : str
        Display name for the reporter.
    """
    date = html.escape(task_payload.get("date", ""))
    reporter = html.escape(reporter_name or task_payload.get("user", ""))
    tasks_by_status = task_payload.get("tasks_by_status", {})

    done = tasks_by_status.get("done", [])
    doing = tasks_by_status.get("doing", []) + tasks_by_status.get("in-progress", [])
    todo = tasks_by_status.get("todo", [])
    pending = tasks_by_status.get("pending", [])
    review = tasks_by_status.get("review", [])
    active = doing + todo + pending + review

    n_done = len(done)
    n_doing = len(doing)
    n_todo = len(todo)
    n_pending = len(pending) + len(review)

    # ── Character-proportional timing ──
    durations = _timings_from_sections(total, sections)
    t0 = 0.0
    t1 = round(durations[0], 3)
    t2 = round(durations[0] + durations[1], 3)
    d_title = durations[0]
    d_done = durations[1]
    d_active = durations[2]
    total_r = round(total, 3)

    done_items = _task_list_html(done, "green")
    active_items = _task_list_html_with_status(doing, todo, pending, review)

    return f"""<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{
        width: 1920px; height: 1080px; overflow: hidden;
        background: {BG};
        font-family: 'Inter', system-ui, sans-serif;
        color: {TEXT};
      }}
      body::before {{
        content: '';
        position: absolute;
        top: -200px; right: -200px;
        width: 900px; height: 900px;
        background: radial-gradient(circle, rgba(22,199,132,0.12) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
      }}
      body::after {{
        content: '';
        position: absolute;
        bottom: -300px; left: -100px;
        width: 800px; height: 800px;
        background: radial-gradient(circle, rgba(45,140,255,0.10) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
      }}
      .clip {{
        position: absolute; inset: 0;
        padding: 90px 120px 120px;
        display: flex; flex-direction: column;
      }}
      .slide-badge {{
        display: inline-flex; align-items: center; gap: 10px;
        background: rgba(22,199,132,0.12);
        border: 1px solid rgba(22,199,132,0.25);
        border-radius: 100px;
        padding: 10px 28px;
        font-size: 22px; font-weight: 600;
        color: {GREEN};
        letter-spacing: 3px;
        text-transform: uppercase;
        width: fit-content;
        backdrop-filter: blur(8px);
      }}
      .slide-badge .dot {{
        width: 8px; height: 8px;
        background: {GREEN};
        border-radius: 50%;
        box-shadow: 0 0 8px {GREEN};
      }}
      .hero-title {{
        font-size: 96px; font-weight: 900;
        line-height: 1.08; margin-top: 36px;
        background: linear-gradient(135deg, {TEXT} 0%, rgba(231,236,245,0.75) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }}
      .hero-subtitle {{
        font-size: 36px; font-weight: 400;
        color: {MUTED}; margin-top: 24px;
        letter-spacing: 0.5px;
      }}
      .accent-line {{
        width: 180px; height: 4px;
        background: linear-gradient(90deg, {GREEN}, {BLUE});
        border-radius: 2px;
        margin-top: 48px;
      }}
      .stats {{
        display: flex; gap: 32px;
        margin-top: 64px;
      }}
      .stat {{
        background: rgba(17,28,51,0.65);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 24px;
        padding: 44px 52px;
        min-width: 260px;
        position: relative;
        overflow: hidden;
      }}
      .stat::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 24px 24px 0 0;
      }}
      .stat.green::before {{ background: linear-gradient(90deg, {GREEN}, rgba(22,199,132,0.3)); }}
      .stat.blue::before {{ background: linear-gradient(90deg, {BLUE}, rgba(45,140,255,0.3)); }}
      .stat.muted::before {{ background: linear-gradient(90deg, {MUTED}, rgba(138,153,181,0.3)); }}
      .stat .num {{ font-size: 72px; font-weight: 900; line-height: 1; }}
      .stat .lbl {{
        font-size: 24px; font-weight: 500;
        color: {MUTED}; margin-top: 12px;
        text-transform: uppercase; letter-spacing: 2px;
      }}
      .section-header {{
        display: flex; align-items: center; gap: 20px;
        margin-top: 20px;
      }}
      .section-icon {{
        width: 72px; height: 72px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 20px;
        font-size: 36px;
      }}
      .section-icon.green {{
        background: rgba(22,199,132,0.12);
        border: 1px solid rgba(22,199,132,0.2);
      }}
      .section-icon.blue {{
        background: rgba(45,140,255,0.12);
        border: 1px solid rgba(45,140,255,0.2);
      }}
      .section-title {{
        font-size: 56px; font-weight: 800; line-height: 1.2;
      }}
      .section-title .em {{ color: {GREEN}; }}
      .section-title .em.blue {{ color: {BLUE}; }}
      .task-list {{
        list-style: none;
        margin-top: 48px;
        display: flex; flex-direction: column;
        gap: 20px;
      }}
      .task-item {{
        display: flex; align-items: center; gap: 24px;
        background: rgba(17,28,51,0.5);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.04);
        border-radius: 16px;
        padding: 28px 36px;
        font-size: 36px; font-weight: 600; line-height: 1.4;
      }}
      .task-num {{
        width: 48px; height: 48px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 14px;
        font-size: 22px; font-weight: 800; flex-shrink: 0;
      }}
      .task-num.green {{
        background: rgba(22,199,132,0.15); color: {GREEN};
        border: 1px solid rgba(22,199,132,0.3);
      }}
      .task-num.blue {{
        background: rgba(45,140,255,0.15); color: {BLUE};
        border: 1px solid rgba(45,140,255,0.3);
      }}
      .task-empty {{
        color: {MUTED}; font-weight: 400; font-style: italic;
        padding: 28px 36px; font-size: 36px;
      }}
      .brand-bar {{
        position: absolute;
        bottom: 0; left: 0; right: 0; height: 80px;
        background: rgba(17,28,51,0.6);
        backdrop-filter: blur(12px);
        border-top: 1px solid rgba(255,255,255,0.05);
        display: flex; align-items: center;
        justify-content: space-between;
        padding: 0 120px; font-size: 22px; color: {MUTED};
      }}
      .brand-bar .logo-text {{
        font-weight: 700; color: {TEXT}; letter-spacing: 1px;
      }}
      .brand-bar .separator {{
        width: 4px; height: 4px;
        background: {MUTED}; border-radius: 50%;
        margin: 0 16px; opacity: 0.5;
      }}
      .brand-left, .brand-right {{ display: flex; align-items: center; }}
      .progress-dots {{ display: flex; gap: 8px; }}
      .progress-dots .pdot {{
        width: 10px; height: 10px; border-radius: 50%;
        background: rgba(255,255,255,0.12);
      }}
      .progress-dots .pdot.active {{
        background: {GREEN};
        box-shadow: 0 0 10px rgba(22,199,132,0.5);
      }}
      .status-badge {{
        margin-left: auto;
        padding: 8px 18px;
        border-radius: 10px;
        font-size: 22px;
        font-weight: 600;
        white-space: nowrap;
        flex-shrink: 0;
      }}
      .app-badge {{
        display: inline-block;
        padding: 4px 14px;
        border-radius: 8px;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-left: 12px;
        vertical-align: middle;
      }}
      .stat.amber::before {{ background: linear-gradient(90deg, #E8B339, rgba(232,179,57,0.3)); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main"
         data-start="0" data-duration="{total_r}"
         data-width="1920" data-height="1080">

      <!-- ═══ Slide 1: Title ═══ -->
      <div id="slide-title" class="clip" data-start="{t0}" data-duration="{d_title}" data-track-index="1">
        <div class="slide-badge"><span class="dot"></span> Daily Report</div>
        <div class="hero-title">Báo cáo<br/>công việc</div>
        <div class="hero-subtitle">{date}  ·  {reporter}</div>
        <div class="accent-line"></div>
        <div class="stats">
          <div class="stat green">
            <div class="num" style="color:{GREEN}">{n_done}</div>
            <div class="lbl">Đã xong</div>
          </div>
          <div class="stat blue">
            <div class="num" style="color:{BLUE}">{n_doing}</div>
            <div class="lbl">Đang xử lý</div>
          </div>
          <div class="stat amber">
            <div class="num" style="color:#E8B339">{n_todo}</div>
            <div class="lbl">Chờ xử lý</div>
          </div>
          <div class="stat muted">
            <div class="num" style="color:{MUTED}">{n_pending}</div>
            <div class="lbl">Hoãn lại</div>
          </div>
        </div>
        <div class="brand-bar">
          <div class="brand-left">
            <span class="logo-text">VIETNIX</span>
            <span class="separator"></span>
            <span>Daily Progress Report</span>
          </div>
          <div class="brand-right">
            <div class="progress-dots">
              <div class="pdot active"></div><div class="pdot"></div><div class="pdot"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ Slide 2: Done ═══ -->
      <div id="slide-done" class="clip" data-start="{t1}" data-duration="{d_done}" data-track-index="1">
        <div class="slide-badge"><span class="dot"></span> Completed</div>
        <div class="section-header">
          <div class="section-icon green">✅</div>
          <div class="section-title"><span class="em">Task</span> đã xong</div>
        </div>
        <ul class="task-list">{done_items}</ul>
        <div class="brand-bar">
          <div class="brand-left">
            <span class="logo-text">VIETNIX</span>
            <span class="separator"></span>
            <span>{date}  ·  {reporter}</span>
          </div>
          <div class="brand-right">
            <div class="progress-dots">
              <div class="pdot"></div><div class="pdot active"></div><div class="pdot"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ Slide 3: Active ═══ -->
      <div id="slide-active" class="clip" data-start="{t2}" data-duration="{d_active}" data-track-index="1">
        <div class="slide-badge"><span class="dot"></span> Remaining</div>
        <div class="section-header">
          <div class="section-icon blue">📊</div>
          <div class="section-title"><span class="em blue">Task</span> còn lại</div>
        </div>
        <ul class="task-list">{active_items}</ul>
        <div class="brand-bar">
          <div class="brand-left">
            <span class="logo-text">VIETNIX</span>
            <span class="separator"></span>
            <span>{date}  ·  {reporter}</span>
          </div>
          <div class="brand-right">
            <div class="progress-dots">
              <div class="pdot"></div><div class="pdot"></div><div class="pdot active"></div>
            </div>
          </div>
        </div>
      </div>

      <audio data-start="0" data-duration="{total_r}" data-track-index="0" src="{audio_rel}"></audio>
    </div>

    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});

      tl.from("#slide-title .slide-badge", {{ opacity: 0, y: -20, scale: 0.9, duration: 0.5, ease: "back.out(1.5)" }}, {t0})
        .from("#slide-title .hero-title", {{ opacity: 0, y: 50, duration: 0.8, ease: "power3.out" }}, "<0.15")
        .from("#slide-title .hero-subtitle", {{ opacity: 0, y: 20, duration: 0.5 }}, "<0.2")
        .from("#slide-title .accent-line", {{ scaleX: 0, transformOrigin: "left center", duration: 0.6, ease: "power2.out" }}, "<0.1")
        .from("#slide-title .stat", {{ opacity: 0, y: 40, scale: 0.95, stagger: 0.1, duration: 0.5, ease: "back.out(1.2)" }}, "<0.3")
        .from("#slide-title .brand-bar", {{ opacity: 0, y: 20, duration: 0.4 }}, "<0.2")

        .from("#slide-done .slide-badge", {{ opacity: 0, y: -20, scale: 0.9, duration: 0.4, ease: "back.out(1.5)" }}, {t1})
        .from("#slide-done .section-icon", {{ opacity: 0, scale: 0.5, rotation: -15, duration: 0.5, ease: "back.out(2)" }}, "<0.1")
        .from("#slide-done .section-title", {{ opacity: 0, x: -40, duration: 0.6, ease: "power3.out" }}, "<0.1")
        .from("#slide-done .task-item, #slide-done .task-empty", {{ opacity: 0, x: -30, y: 10, stagger: 0.1, duration: 0.4, ease: "power2.out" }}, "<0.2")

        .from("#slide-active .slide-badge", {{ opacity: 0, y: -20, scale: 0.9, duration: 0.4, ease: "back.out(1.5)" }}, {t2})
        .from("#slide-active .section-icon", {{ opacity: 0, scale: 0.5, rotation: -15, duration: 0.5, ease: "back.out(2)" }}, "<0.1")
        .from("#slide-active .section-title", {{ opacity: 0, x: -40, duration: 0.6, ease: "power3.out" }}, "<0.1")
        .from("#slide-active .task-item, #slide-active .task-empty", {{ opacity: 0, x: -30, y: 10, stagger: 0.1, duration: 0.4, ease: "power2.out" }}, "<0.2");

      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def render_video(payload: dict, audio_path: Path, output_path: Path, *, quality: str = "high") -> Path:
    """Build the composition and render it to ``output_path`` (1080p MP4)."""
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(
            f"Narration audio not found: {audio_path}. Run the TTS step first."
        )

    HYPERFRAMES_DIR.mkdir(parents=True, exist_ok=True)
    assets = HYPERFRAMES_DIR / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    # Copy narration into the project's assets dir (deterministic relative path).
    audio_dest = assets / "report.wav"
    shutil.copyfile(audio_path, audio_dest)

    total = probe_duration(audio_dest)
    composition = build_composition_html(payload, "assets/report.wav", total)
    (HYPERFRAMES_DIR / "index.html").write_text(composition, encoding="utf-8")

    return _run_hyperframes(output_path)


def render_task_video(
    task_payload: dict,
    sections: list[dict],
    audio_path: Path,
    output_path: Path,
    *,
    reporter_name: str = "",
    quality: str = "high",
) -> Path:
    """Render video from DevZone tasks with character-proportional timing.

    Parameters
    ----------
    task_payload : dict
        Output of ``devzone_tasks.get_daily_tasks()``.
    sections : list[dict]
        Output of ``script_builder.build_script_from_tasks()["sections"]``.
    audio_path : Path
        Path to the narration WAV file.
    output_path : Path
        Where to write the final MP4.
    reporter_name : str
        Display name for the reporter in the video.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(
            f"Narration audio not found: {audio_path}. Run the TTS step first."
        )

    HYPERFRAMES_DIR.mkdir(parents=True, exist_ok=True)
    assets = HYPERFRAMES_DIR / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    audio_dest = assets / "report.wav"
    shutil.copyfile(audio_path, audio_dest)

    total = probe_duration(audio_dest)
    composition = build_task_composition_html(
        task_payload, sections, "assets/report.wav", total,
        reporter_name=reporter_name,
    )
    (HYPERFRAMES_DIR / "index.html").write_text(composition, encoding="utf-8")

    return _run_hyperframes(output_path)


def _run_hyperframes(output_path: Path, quality: str = "high") -> Path:
    """Execute HyperFrames CLI render."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "npx",
        "--yes",
        "hyperframes@0.6.65",
        "render",
        str(HYPERFRAMES_DIR),
        "-o",
        str(output_path),
        "--resolution",
        "1080p",
        "--quality",
        quality,
        "--quiet",
    ]
    subprocess.run(cmd, check=True, timeout=1800)
    if not output_path.exists():
        raise RuntimeError("HyperFrames render finished but output file is missing.")
    return output_path

