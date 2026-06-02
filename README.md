# Daily Video Reporter 🎬

Automates a daily work report (Epic 1): it extracts the day's completed Git
tasks, narrates them in Vietnamese with a **cloned voice (OmniVoice)**, renders a
slide-based report video with **HeyGen HyperFrames**, and publishes the report to
the **DevZone** knowledge base — automatically at **17:00** every day.

```
git commits ──▶ JSON payload ──▶ VN narration script ──▶ OmniVoice TTS (report.wav)
                                                              │
                          DevZone document  ◀── Markdown ◀────┤
                                                              ▼
                                       HeyGen HyperFrames ──▶ report-YYYY-MM-DD.mp4 (1080p)
```

## Pipeline stages (Epic 1 stories)

| Story | Module | What it does |
|------|--------|--------------|
| 1.2 | [`reporter/git_extractor.py`](reporter/git_extractor.py) | `git log` today's commits, drop merges, group into features/fixes/quality JSON |
| 1.3 | [`reporter/script_builder.py`](reporter/script_builder.py) + [`reporter/tts.py`](reporter/tts.py) | Build VN narration; OmniVoice voice-clone → `report.wav` (24 kHz) |
| 1.4 | [`reporter/video.py`](reporter/video.py) | Generate HTML composition, render 1080p MP4 via HyperFrames |
| 1.5 | [`reporter/devzone.py`](reporter/devzone.py) | POST Markdown report doc to DevZone (`X-API-Key`) |
| 1.6 | [`scripts/`](scripts/) | launchd/cron trigger daily at 17:00, logging + failure notification |

Orchestrated by [`daily_reporter.py`](daily_reporter.py).

## Setup (Story 1.1)

```bash
./scripts/setup.sh          # ffmpeg, Python 3.12 venv, torch+omnivoice, hyperframes
cp .env.example .env        # then edit credentials + reference voice
```

Requirements: **Node 22+**, **Python 3.10+**, **FFmpeg**, macOS (for the launchd
schedule + the placeholder-voice helper).

### Reference voice (required for cloning)

OmniVoice clones a **target voice** from a short reference clip + its transcript:

- Put a clean WAV at `ref/reference.wav` and its exact transcript at `ref/reference.txt`.
- Or generate a synthetic placeholder for testing: `./scripts/make_reference.sh`
  (uses the macOS Vietnamese voice "Linh" — **replace with a real recording** for
  production-quality cloning).

## Run

```bash
# Full pipeline
.venv/bin/python daily_reporter.py

# Useful flags
.venv/bin/python daily_reporter.py --dry-run        # everything except the upload
.venv/bin/python daily_reporter.py --skip-tts --skip-video   # extraction + upload only
.venv/bin/python daily_reporter.py --date 2026-06-01 --repo /path/to/repo
```

Intermediate artifacts land in `_bmad-output/temp/` (`payload.json`, `script.txt`,
`report.md`, `report.wav`); the video in `_bmad-output/videos/`; logs in
`_bmad-output/logs/scheduler.log`.

## Schedule (Story 1.6)

```bash
./scripts/install_scheduler.sh      # installs & loads the launchd agent
launchctl start com.vietnix.dailyreporter   # test run now
```

> ⏰ launchd fires at **17:00 local time**. For 17:00 Vietnam time (ICT, UTC+7)
> the Mac must be on `Asia/Ho_Chi_Minh`, or adjust the `Hour` in the plist.
> A cron one-liner alternative is printed by the installer.

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
