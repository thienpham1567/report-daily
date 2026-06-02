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


def _list_html(items: list[str], accent: str) -> str:
    if not items:
        return f'<li style="color:{MUTED}">— Không có —</li>'
    return "\n".join(
        f'<li><span class="bullet" style="color:{accent}">▸</span> {html.escape(it)}</li>'
        for it in items
    )


def build_composition_html(payload: dict, audio_rel: str, total: float) -> str:
    """Render the full index.html composition string."""
    cats = payload.get("categories", {})
    features = cats.get("features", [])
    fixes = cats.get("fixes", []) + cats.get("quality", [])
    date = html.escape(payload.get("date", ""))
    reporter = html.escape(payload.get("author", "Thienpham"))

    d_title, d_feat, d_fix = _slide_timings(total, len(features), len(fixes))
    t0 = 0.0
    t1 = round(d_title, 3)
    t2 = round(d_title + d_feat, 3)
    total_r = round(total, 3)

    n_feat, n_fix = len(features), len(cats.get("fixes", []))
    n_qual = len(cats.get("quality", []))

    feat_items = _list_html(features, GREEN)
    fix_items = _list_html(fixes, BLUE)

    return f"""<!doctype html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap" rel="stylesheet" />
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{
        width: 1920px; height: 1080px; overflow: hidden;
        background: {BG};
        font-family: 'Inter', 'Roboto', system-ui, sans-serif;
        color: {TEXT};
      }}
      .clip {{ position: absolute; inset: 0; padding: 120px 140px; }}
      .kicker {{ font-size: 34px; font-weight: 600; letter-spacing: 6px;
                 text-transform: uppercase; color: {GREEN}; }}
      .title {{ font-size: 110px; font-weight: 900; line-height: 1.05; margin-top: 24px; }}
      .date {{ font-size: 52px; font-weight: 600; color: {MUTED}; margin-top: 40px; }}
      .accent-bar {{ width: 220px; height: 12px; border-radius: 6px;
                     background: linear-gradient(90deg, {GREEN}, {BLUE}); margin-top: 56px; }}
      .stats {{ display: flex; gap: 48px; margin-top: 80px; }}
      .stat {{ background: {PANEL}; border-radius: 24px; padding: 40px 56px; }}
      .stat .num {{ font-size: 84px; font-weight: 900; }}
      .stat .lbl {{ font-size: 30px; color: {MUTED}; margin-top: 8px; }}
      .section-title {{ font-size: 72px; font-weight: 800; }}
      .section-title .em {{ color: {GREEN}; }}
      .section-title .em.blue {{ color: {BLUE}; }}
      ul {{ list-style: none; margin-top: 60px; }}
      li {{ font-size: 46px; font-weight: 600; line-height: 1.55;
            display: flex; gap: 24px; align-items: baseline; }}
      .bullet {{ font-size: 40px; }}
      .footer {{ position: absolute; bottom: 70px; left: 140px;
                 font-size: 30px; color: {MUTED}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main"
         data-start="0" data-duration="{total_r}"
         data-width="1920" data-height="1080">

      <!-- Slide 1: Title + Date -->
      <div id="slide-title" class="clip" data-start="{t0}" data-duration="{t1}" data-track-index="1">
        <div class="kicker">Daily Progress Report</div>
        <div class="title">Báo cáo<br/>công việc</div>
        <div class="date">{date} · {reporter}</div>
        <div class="accent-bar"></div>
        <div class="stats">
          <div class="stat"><div class="num" style="color:{GREEN}">{n_feat}</div><div class="lbl">Tính năng</div></div>
          <div class="stat"><div class="num" style="color:{BLUE}">{n_fix}</div><div class="lbl">Sửa lỗi</div></div>
          <div class="stat"><div class="num" style="color:{MUTED}">{n_qual}</div><div class="lbl">Chất lượng</div></div>
        </div>
      </div>

      <!-- Slide 2: Completed Features -->
      <div id="slide-features" class="clip" data-start="{t1}" data-duration="{round(d_feat,3)}" data-track-index="1">
        <div class="section-title">🚀 <span class="em">Tính năng</span> đã hoàn thành</div>
        <ul>{feat_items}</ul>
        <div class="footer">{date} · {reporter}</div>
      </div>

      <!-- Slide 3: Bug Fixes & Refactoring -->
      <div id="slide-fixes" class="clip" data-start="{t2}" data-duration="{round(d_fix,3)}" data-track-index="1">
        <div class="section-title">🛠️ <span class="em blue">Sửa lỗi</span> & Tái cấu trúc</div>
        <ul>{fix_items}</ul>
        <div class="footer">{date} · {reporter}</div>
      </div>

      <!-- Narration audio track -->
      <audio data-start="0" data-duration="{total_r}" data-track-index="0" src="{audio_rel}"></audio>
    </div>

    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      tl.from("#slide-title .kicker", {{ opacity: 0, y: -30, duration: 0.6 }}, {t0})
        .from("#slide-title .title", {{ opacity: 0, y: 40, duration: 0.7 }}, "<0.1")
        .from("#slide-title .stat", {{ opacity: 0, y: 30, stagger: 0.12, duration: 0.5 }}, "<0.2")
        .from("#slide-features .section-title", {{ opacity: 0, x: -40, duration: 0.6 }}, {t1})
        .from("#slide-features li", {{ opacity: 0, x: -30, stagger: 0.12, duration: 0.4 }}, "<0.2")
        .from("#slide-fixes .section-title", {{ opacity: 0, x: -40, duration: 0.6 }}, {t2})
        .from("#slide-fixes li", {{ opacity: 0, x: -30, stagger: 0.12, duration: 0.4 }}, "<0.2");
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
