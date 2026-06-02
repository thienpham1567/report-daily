"""Configuration for the daily video reporter.

Values resolve in this order (highest priority first):
    1. Environment variables (optionally loaded from a local ``.env`` file).
    2. Values parsed from ``project-context.md`` (DevZone credentials only).
    3. Built-in defaults.

Story 1.5 / AC 1.5.1: API Key and Project ID are read from ``project-context.md``
or environment variables.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date as _date
from pathlib import Path

# Project root = parent of this package directory.
ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = ROOT / "_bmad-output"
TEMP_DIR = OUTPUT_DIR / "temp"
VIDEO_DIR = OUTPUT_DIR / "videos"
LOG_DIR = OUTPUT_DIR / "logs"
REF_DIR = ROOT / "ref"

PROJECT_CONTEXT = ROOT / "project-context.md"


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no external dependency). Does not overwrite real env vars."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _parse_project_context() -> dict[str, str]:
    """Extract DevZone credentials from project-context.md if present."""
    out: dict[str, str] = {}
    if not PROJECT_CONTEXT.exists():
        return out
    text = PROJECT_CONTEXT.read_text(encoding="utf-8")
    patterns = {
        "project_id": r"\*\*Project ID\*\*:\s*(\S+)",
        "api_key": r"\*\*API Key\*\*:\s*(\S+)",
        "base_url": r"\*\*Base URL\*\*:\s*(\S+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            out[key] = m.group(1).strip()
    return out


@dataclass
class Config:
    # --- Git extraction (Story 1.2) ---
    target_repo: Path = ROOT
    git_author: str = "Thienpham"
    since: str = "today"

    # --- DevZone (Story 1.5) ---
    devzone_base_url: str = "https://api.devzone.vietnix.dev"
    devzone_project_id: str = ""
    devzone_api_key: str = ""

    # --- TTS (Story 1.3) ---
    tts_engine: str = "edge"  # edge | fpt | fish | omnivoice
    tts_voice: str = "male"  # edge: male|female; fpt: male|female|leminh; fish: ref_id
    fpt_api_key: str = ""  # FPT.AI API key (FPT_API_KEY)
    fish_api_key: str = ""  # Fish Audio API key (FISH_API_KEY)
    omnivoice_model: str = "k2-fsa/OmniVoice"
    ref_audio: Path | None = None
    ref_text: str = ""
    tts_device: str = "auto"  # auto | mps | cpu | cuda

    # --- Reporter identity / locale ---
    reporter_name: str = "Thienpham"

    # --- Paths (Story 1.3 / 1.4 outputs) ---
    output_dir: Path = OUTPUT_DIR
    temp_dir: Path = TEMP_DIR
    video_dir: Path = VIDEO_DIR
    log_dir: Path = LOG_DIR

    report_date: str = field(default_factory=lambda: _date.today().isoformat())

    @property
    def audio_path(self) -> Path:
        return self.temp_dir / "report.wav"

    @property
    def video_path(self) -> Path:
        return self.video_dir / f"report-{self.report_date}.mp4"

    @property
    def documents_endpoint(self) -> str:
        return (
            f"{self.devzone_base_url}/workspace/projects/"
            f"{self.devzone_project_id}/documents"
        )

    def ensure_dirs(self) -> None:
        for d in (self.output_dir, self.temp_dir, self.video_dir, self.log_dir, REF_DIR):
            d.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    """Build a Config from .env, environment, and project-context.md."""
    _load_dotenv(ROOT / ".env")
    ctx = _parse_project_context()

    ref_audio_env = os.environ.get("REPORTER_REF_AUDIO", "").strip()
    ref_audio = Path(ref_audio_env) if ref_audio_env else None

    target = os.environ.get("REPORTER_TARGET_REPO", "").strip()
    target_repo = Path(target).expanduser().resolve() if target else ROOT

    cfg = Config(
        target_repo=target_repo,
        git_author=os.environ.get("REPORTER_GIT_AUTHOR", "Thienpham"),
        since=os.environ.get("REPORTER_SINCE", "today"),
        devzone_base_url=os.environ.get(
            "DEVZONE_BASE_URL", ctx.get("base_url", "https://api.devzone.vietnix.dev")
        ),
        devzone_project_id=os.environ.get(
            "DEVZONE_PROJECT_ID", ctx.get("project_id", "")
        ),
        devzone_api_key=os.environ.get("DEVZONE_API_KEY", ctx.get("api_key", "")),
        tts_engine=os.environ.get("REPORTER_TTS_ENGINE", "edge"),
        tts_voice=os.environ.get("REPORTER_TTS_VOICE", "male"),
        fpt_api_key=os.environ.get("FPT_API_KEY", ""),
        fish_api_key=os.environ.get("FISH_API_KEY", ""),
        omnivoice_model=os.environ.get("OMNIVOICE_MODEL", "k2-fsa/OmniVoice"),
        ref_audio=ref_audio,
        ref_text=os.environ.get("REPORTER_REF_TEXT", ""),
        tts_device=os.environ.get("REPORTER_TTS_DEVICE", "auto"),
        reporter_name=os.environ.get("REPORTER_NAME", "Thienpham"),
    )
    return cfg
