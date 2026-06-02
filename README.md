# Daily Video Reporter 🎬

Automates a daily work report (Epic 1): extracts the day's completed Git
tasks, narrates them in Vietnamese with **edge-tts** (Microsoft neural voice),
renders a slide-based report video with **HeyGen HyperFrames**, and publishes
the report to the **DevZone** knowledge base — automatically at **17:00** every day.

```
git commits ──▶ JSON payload ──▶ VN narration script ──▶ edge-tts (report.wav)
                                                              │
                          DevZone document  ◀── Markdown ◀────┤
                                                              ▼
                                       HeyGen HyperFrames ──▶ report-YYYY-MM-DD.mp4 (1080p)
```

## Pipeline stages (Epic 1 stories)

| Story | Module | What it does |
|------|--------|--------------|
| 1.2 | [`git_extractor.py`](reporter/git_extractor.py) | `git log` today's commits, drop merges, group into features/fixes/quality JSON |
| 1.3 | [`script_builder.py`](reporter/script_builder.py) + [`tts.py`](reporter/tts.py) | Build VN narration script; **edge-tts** → `report.wav` (24 kHz mono) |
| 1.4 | [`video.py`](reporter/video.py) | Generate HTML composition, render 1080p MP4 via HyperFrames |
| 1.5 | [`devzone.py`](reporter/devzone.py) | POST Markdown report doc to DevZone (`X-API-Key`) |
| 1.6 | [`scripts/`](scripts/) | launchd/cron trigger daily at 17:00, logging + failure notification |

Orchestrated by [`daily_reporter.py`](daily_reporter.py).

## TTS Engines

| Engine | Default? | Requirements | Notes |
|--------|----------|-------------|-------|
| **edge-tts** | ✅ Yes | `pip install edge-tts`, ffmpeg | Free, no API key, Microsoft neural Vietnamese voices (`NamMinhNeural` / `HoaiMyNeural`) |
| **OmniVoice** | No | GPU ≥18 GB, torch, omnivoice | Zero-shot voice cloning. Set `REPORTER_TTS_ENGINE=omnivoice` to use |

## Setup (Story 1.1)

```bash
./scripts/setup.sh          # ffmpeg, Python 3.12 venv, edge-tts, hyperframes
cp .env.example .env        # then edit credentials
```

Requirements: **Node 22+**, **Python 3.10+**, **FFmpeg**, macOS.

## Run

```bash
# Full pipeline
.venv/bin/python daily_reporter.py

# Useful flags
.venv/bin/python daily_reporter.py --dry-run                   # skip DevZone upload
.venv/bin/python daily_reporter.py --skip-tts --skip-video     # extraction only
.venv/bin/python daily_reporter.py --date 2026-06-01 --repo /path/to/repo
```

Intermediate artifacts land in `_bmad-output/temp/` (`payload.json`, `script.txt`,
`report.md`, `report.wav`); videos in `_bmad-output/videos/`; logs in
`_bmad-output/logs/scheduler.log`.

## Schedule (Story 1.6)

```bash
./scripts/install_scheduler.sh      # installs & loads the launchd agent
launchctl start com.vietnix.dailyreporter   # test run now
```

> ⏰ launchd fires at **17:00 local time**. For 17:00 Vietnam time (ICT, UTC+7)
> the Mac must be on `Asia/Ho_Chi_Minh`, or adjust the `Hour` in the plist.

## Configuration

All settings come from environment variables (see [`.env.example`](.env.example)).
DevZone credentials fall back to values parsed from
[`project-context.md`](project-context.md) if not set in the environment.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

Covers the deterministic logic: commit grouping & merge filtering, the narration
script template, and the DevZone Markdown body / document-id parsing.

## Documentation

| File | Audience | Content |
|------|----------|---------|
| **README.md** (this file) | Developers | Quick start, setup, commands |
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | Engineers | System diagrams, data flow, design principles |
| [**HƯỚNG DẪN SỬ DỤNG**](HUONG-DAN-SU-DUNG.md) | End users (VN) | Nguồn dữ liệu, cách cấu hình, ví dụ chi tiết |
