#!/usr/bin/env python3
"""Daily Video Reporter — pipeline orchestrator (Epic 1).

Runs the full daily pipeline:
    1.2  Extract today's git commits and group them into a JSON payload.
    1.3  Build the Vietnamese narration script and synthesize report.wav (OmniVoice).
    1.4  Render a 1080p MP4 from an HTML composition (HeyGen HyperFrames).
    1.5  Publish a Markdown report document to DevZone.

Usage:
    python3 daily_reporter.py [--dry-run] [--skip-tts] [--skip-video]
                              [--skip-upload] [--date YYYY-MM-DD] [--repo PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

from reporter import config as config_mod
from reporter import devzone, git_extractor, script_builder, video


def _log(cfg, message: str) -> None:
    """Append a timestamped line to scheduler.log and echo to stdout (AC 1.6.3)."""
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {message}"
    with (cfg.log_dir / "scheduler.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def _notify_failure(message: str) -> None:
    """Surface a failure to the user (AC 1.6.4). Best-effort macOS notification."""
    import subprocess

    safe = message.replace('"', "'")[:200]
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{safe}" with title "Daily Reporter FAILED"',
            ],
            check=False,
            timeout=10,
        )
    except Exception:
        pass


def run(cfg, args) -> int:
    start = time.time()
    cfg.ensure_dirs()
    _log(cfg, f"=== Daily report run started (date={cfg.report_date}) ===")

    # --- Story 1.2: extract & group commits ---
    payload = git_extractor.extract_tasks(
        cfg.target_repo, author=cfg.git_author, since=cfg.since,
        report_date=cfg.report_date,
    )
    (cfg.temp_dir / "payload.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    cats = payload["categories"]
    _log(
        cfg,
        f"Extracted {payload['total']} commit(s): "
        f"{len(cats['features'])} feat / {len(cats['fixes'])} fix / "
        f"{len(cats['quality'])} quality",
    )

    # --- Story 1.3: narration script ---
    script = script_builder.build_script(payload, reporter_name=cfg.reporter_name)
    (cfg.temp_dir / "script.txt").write_text(script, encoding="utf-8")
    _log(cfg, f"Built narration script ({len(script)} chars)")

    # --- Story 1.3: TTS synthesis ---
    audio_ready = False
    if args.skip_tts:
        _log(cfg, "TTS skipped (--skip-tts)")
    else:
        from reporter import tts

        tts.synthesize_report(
            script, cfg.audio_path,
            ref_audio=cfg.ref_audio, ref_text=cfg.ref_text,
            model_id=cfg.omnivoice_model, device=cfg.tts_device,
            engine=cfg.tts_engine, voice=cfg.tts_voice,
            fish_api_key=cfg.fish_api_key,
            fpt_api_key=cfg.fpt_api_key,
        )
        audio_ready = cfg.audio_path.exists()
        _log(cfg, f"Synthesized narration -> {cfg.audio_path} (engine={cfg.tts_engine})")

    # --- Story 1.4: video render ---
    if args.skip_video:
        _log(cfg, "Video render skipped (--skip-video)")
    elif not audio_ready:
        _log(cfg, "Video render skipped (no narration audio available)")
    else:
        video.render_video(payload, cfg.audio_path, cfg.video_path)
        _log(cfg, f"Rendered video -> {cfg.video_path}")

    # --- Story 1.5: DevZone upload ---
    markdown = devzone.build_markdown(payload, cfg.video_path, reporter_name=cfg.reporter_name)
    (cfg.temp_dir / "report.md").write_text(markdown, encoding="utf-8")

    if args.skip_upload or args.dry_run:
        _log(cfg, "DevZone upload skipped (--skip-upload/--dry-run)")
    else:
        title = f"Báo cáo ngày {cfg.report_date}"
        response = devzone.upload_document(
            base_url=cfg.devzone_base_url,
            project_id=cfg.devzone_project_id,
            api_key=cfg.devzone_api_key,
            title=title,
            content=markdown,
        )
        doc_id = devzone.extract_document_id(response)
        _log(cfg, f"DevZone upload OK (201) — document id: {doc_id}")

    elapsed = time.time() - start
    _log(cfg, f"=== Run completed in {elapsed:.1f}s ===")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Daily Video Reporter pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline but do not upload")
    parser.add_argument("--skip-tts", action="store_true", help="Skip OmniVoice synthesis")
    parser.add_argument("--skip-video", action="store_true", help="Skip HyperFrames render")
    parser.add_argument("--skip-upload", action="store_true", help="Skip DevZone upload")
    parser.add_argument("--date", help="Override report date (YYYY-MM-DD)")
    parser.add_argument("--repo", help="Override target git repository path")
    args = parser.parse_args(argv)

    cfg = config_mod.load_config()
    if args.date:
        cfg.report_date = args.date
    if args.repo:
        cfg.target_repo = Path(args.repo).expanduser().resolve()

    try:
        return run(cfg, args)
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        _log(cfg, f"FAILED: {exc}\n{tb}")
        _notify_failure(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
