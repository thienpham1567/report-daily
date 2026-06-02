"""Story 1.3 — Text-to-Speech synthesis.

Supported engines (set via ``REPORTER_TTS_ENGINE``):

1. **edge** (default) — Microsoft Edge neural TTS.
   Free, no API key, high-quality Vietnamese voices.

2. **fpt** — FPT.AI TTS (Vietnamese-optimized).
   Free 100K chars/month, very natural Vietnamese voices.
   Requires ``FPT_API_KEY`` env var (get from https://console.fpt.ai).

3. **fish** — Fish Audio cloud API.
   Very natural voice quality, requires paid API credits.
   Requires ``FISH_API_KEY`` env var.

4. **omnivoice** — OmniVoice zero-shot voice cloning (local GPU).
   Requires GPU ≥18 GB. Set ``REPORTER_TTS_ENGINE=omnivoice``.

AC 1.3.2 / 1.3.3: Produces a clear, high-quality ``report.wav`` in
``_bmad-output/temp/``.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Optional

OUTPUT_SAMPLE_RATE = 24000  # Target sample rate for HyperFrames.

# Available Vietnamese voices in edge-tts.
EDGE_VOICES = {
    "male": "vi-VN-NamMinhNeural",
    "female": "vi-VN-HoaiMyNeural",
}


class TTSError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# edge-tts engine (default)
# ---------------------------------------------------------------------------

async def _edge_tts_generate(text: str, out_mp3: Path, voice: str) -> Path:
    """Generate speech with edge-tts and save as MP3."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_mp3))
    return out_mp3


def _convert_mp3_to_wav(mp3_path: Path, wav_path: Path) -> Path:
    """Convert MP3 → 24 kHz mono WAV using ffmpeg."""
    ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    cmd = [
        ffmpeg, "-y",
        "-i", str(mp3_path),
        "-ar", str(OUTPUT_SAMPLE_RATE),
        "-ac", "1",
        str(wav_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=60)
    except subprocess.CalledProcessError as exc:
        raise TTSError(f"ffmpeg conversion failed: {exc.stderr[:500]}") from exc
    return wav_path


def synthesize_edge(
    text: str,
    out_path: Path,
    voice: str = "male",
) -> Path:
    """Synthesize Vietnamese speech using edge-tts (free, no API key).

    Parameters
    ----------
    text : str
        The Vietnamese narration script.
    out_path : Path
        Output WAV file path.
    voice : str
        ``"male"`` or ``"female"``, or a full edge-tts voice name.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Resolve voice name.
    voice_name = EDGE_VOICES.get(voice, voice)

    # edge-tts outputs MP3; we need WAV for HyperFrames.
    mp3_tmp = out_path.with_suffix(".mp3")

    try:
        asyncio.run(_edge_tts_generate(text, mp3_tmp, voice_name))
    except Exception as exc:
        raise TTSError(f"edge-tts generation failed: {exc}") from exc

    if not mp3_tmp.exists() or mp3_tmp.stat().st_size == 0:
        raise TTSError("edge-tts produced empty output.")

    # Convert MP3 → WAV (24 kHz mono).
    _convert_mp3_to_wav(mp3_tmp, out_path)

    # Clean up temp MP3.
    mp3_tmp.unlink(missing_ok=True)

    return out_path


# ---------------------------------------------------------------------------
# FPT.AI engine (free, Vietnamese-optimized)
# ---------------------------------------------------------------------------

# Available Vietnamese voices in FPT.AI.
FPT_VOICES = {
    "male": "leminh",       # Nam, miền Bắc
    "female": "banmai",     # Nữ, miền Bắc
    "south_female": "lannhi",  # Nữ, miền Nam
    "central_female": "myan",  # Nữ, miền Trung
}


def synthesize_fpt(
    text: str,
    out_path: Path,
    voice: str = "male",
    api_key: str = "",
) -> Path:
    """Synthesize Vietnamese speech using FPT.AI TTS API.

    Parameters
    ----------
    text : str
        Vietnamese narration (max 5000 chars per request).
    out_path : Path
        Output WAV file path.
    voice : str
        ``"male"``, ``"female"``, or an FPT voice name like ``"leminh"``.
    api_key : str
        FPT.AI API key. Falls back to ``FPT_API_KEY`` env var.
    """
    import os
    import time
    import requests

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    key = api_key or os.environ.get("FPT_API_KEY", "")
    if not key:
        raise TTSError(
            "FPT.AI requires an API key. "
            "Get one at https://console.fpt.ai and set FPT_API_KEY in .env"
        )

    # Resolve voice name.
    voice_name = FPT_VOICES.get(voice, voice)

    # Step 1: Submit text for synthesis.
    headers = {
        "api-key": key,
        "voice": voice_name,
        "speed": "0",
    }
    try:
        resp = requests.post(
            "https://api.fpt.ai/hmi/tts/v5",
            headers=headers,
            data=text.encode("utf-8"),
            timeout=30,
        )
        resp.raise_for_status()
    except Exception as exc:
        raise TTSError(f"FPT.AI API request failed: {exc}") from exc

    data = resp.json()
    if data.get("error") or data.get("success") == "false":
        raise TTSError(f"FPT.AI error: {data.get('message', data)}")

    # Get the async download URL.
    audio_url = data.get("async") or data.get("message", "")
    if not audio_url:
        raise TTSError(f"FPT.AI returned no audio URL: {data}")

    # Step 2: Poll until the audio file is ready (max ~60s).
    mp3_tmp = out_path.with_suffix(".mp3")
    for attempt in range(12):
        time.sleep(3 + attempt)  # 3s, 4s, 5s, ...
        try:
            dl = requests.get(audio_url, timeout=30)
            if dl.status_code == 200 and len(dl.content) > 1000:
                mp3_tmp.write_bytes(dl.content)
                break
        except requests.RequestException:
            continue
    else:
        raise TTSError("FPT.AI audio not ready after polling (timeout).")

    # Step 3: Convert to 24 kHz WAV.
    _convert_mp3_to_wav(mp3_tmp, out_path)
    mp3_tmp.unlink(missing_ok=True)

    return out_path


# ---------------------------------------------------------------------------
# Fish Audio engine (cloud API, high quality)
# ---------------------------------------------------------------------------

def synthesize_fish(
    text: str,
    out_path: Path,
    voice: str = "",
    api_key: str = "",
) -> Path:
    """Synthesize Vietnamese speech using Fish Audio cloud API.

    Parameters
    ----------
    text : str
        The Vietnamese narration script.
    out_path : Path
        Output WAV file path.
    voice : str
        Fish Audio voice/model reference ID. Leave empty for default voice.
    api_key : str
        Fish Audio API key. Falls back to ``FISH_API_KEY`` env var.
    """
    import os

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    key = api_key or os.environ.get("FISH_API_KEY", "")
    if not key:
        raise TTSError(
            "Fish Audio requires an API key. "
            "Get one at https://fish.audio/app/api-keys and set FISH_API_KEY in .env"
        )

    try:
        from fishaudio import FishAudio
    except ImportError as exc:
        raise TTSError(
            "fish-audio-sdk not installed. Run: pip install fish-audio-sdk"
        ) from exc

    client = FishAudio(api_key=key)

    # Generate speech — outputs MP3-like bytes.
    mp3_tmp = out_path.with_suffix(".mp3")
    try:
        kwargs = {"text": text}
        if voice:
            kwargs["reference_id"] = voice
        audio = client.tts.convert(**kwargs)

        # Save raw output.
        with open(mp3_tmp, "wb") as f:
            for chunk in audio:
                f.write(chunk)
    except Exception as exc:
        raise TTSError(f"Fish Audio API error: {exc}") from exc

    if not mp3_tmp.exists() or mp3_tmp.stat().st_size == 0:
        raise TTSError("Fish Audio produced empty output.")

    # Convert to 24 kHz WAV for HyperFrames.
    _convert_mp3_to_wav(mp3_tmp, out_path)
    mp3_tmp.unlink(missing_ok=True)

    return out_path


# ---------------------------------------------------------------------------
# OmniVoice engine (optional, requires GPU)
# ---------------------------------------------------------------------------

def _resolve_device(requested: str) -> tuple[str, "object"]:
    """Pick an inference device + dtype. Apple Silicon -> mps, else cpu/cuda.

    AC 1.1.2: PyTorch optimized for Apple Silicon (MPS) or CPU.
    """
    import torch

    req = (requested or "auto").lower()
    if req == "auto":
        if torch.cuda.is_available():
            device = "cuda:0"
        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    else:
        device = req

    # float16 is reliable on CUDA; mps/cpu use float32 for stability.
    dtype = torch.float16 if device.startswith("cuda") else torch.float32
    return device, dtype


class OmniVoiceTTS:
    """Lazy wrapper around the OmniVoice model for voice-cloned synthesis."""

    def __init__(
        self,
        ref_audio: Path,
        ref_text: str,
        model_id: str = "k2-fsa/OmniVoice",
        device: str = "auto",
    ):
        if not ref_audio or not Path(ref_audio).exists():
            raise TTSError(
                "A reference voice file is required for voice cloning (AC 1.3.2).\n"
                "Set REPORTER_REF_AUDIO to a short, clean WAV clip of the target "
                "voice and REPORTER_REF_TEXT to its exact transcription.\n"
                f"Looked for: {ref_audio}"
            )
        if not ref_text.strip():
            raise TTSError(
                "REPORTER_REF_TEXT (transcription of the reference clip) is required "
                "for OmniVoice voice cloning."
            )
        self.ref_audio = str(ref_audio)
        self.ref_text = ref_text
        self.model_id = model_id
        self.device_pref = device
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            import torch  # noqa: F401
            from omnivoice import OmniVoice
        except ImportError as exc:  # pragma: no cover - env dependent
            raise TTSError(
                "OmniVoice/torch not installed. Run scripts/setup.sh (installs "
                "torch and omnivoice into .venv)."
            ) from exc

        device, dtype = _resolve_device(self.device_pref)
        self._device = device
        self._model = OmniVoice.from_pretrained(
            self.model_id, device_map=device, dtype=dtype
        )
        return self._model

    def synthesize(self, text: str, out_path: Path) -> Path:
        """Render ``text`` to a WAV file at ``out_path`` and return the path."""
        import soundfile as sf

        model = self._load()
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        audio = model.generate(
            text=text,
            ref_audio=self.ref_audio,
            ref_text=self.ref_text,
        )
        # OmniVoice returns a list of np.ndarray (T,) at 24 kHz.
        wav = audio[0] if isinstance(audio, (list, tuple)) else audio
        sf.write(str(out_path), wav, OUTPUT_SAMPLE_RATE)
        return out_path


# ---------------------------------------------------------------------------
# Public API — used by the orchestrator
# ---------------------------------------------------------------------------

def synthesize_report(
    text: str,
    out_path: Path,
    ref_audio: Optional[Path] = None,
    ref_text: str = "",
    model_id: str = "k2-fsa/OmniVoice",
    device: str = "auto",
    engine: str = "edge",
    voice: str = "male",
    fish_api_key: str = "",
    fpt_api_key: str = "",
) -> Path:
    """Convenience entry point used by the orchestrator.

    Parameters
    ----------
    engine : str
        ``"edge"`` (default), ``"fpt"``, ``"fish"``, or ``"omnivoice"``.
    voice : str
        For edge-tts: ``"male"`` or ``"female"``.
        For fpt: ``"male"``, ``"female"``, or FPT voice name.
        For fish: a reference_id (or empty for default voice).
    fish_api_key : str
        API key for Fish Audio (falls back to FISH_API_KEY env var).
    fpt_api_key : str
        API key for FPT.AI (falls back to FPT_API_KEY env var).
    """
    if engine == "fpt":
        try:
            return synthesize_fpt(text, out_path, voice=voice, api_key=fpt_api_key)
        except TTSError as exc:
            import sys
            print(
                f"[TTS] FPT.AI failed ({exc}), falling back to edge-tts...",
                file=sys.stderr,
            )
            return synthesize_edge(text, out_path, voice="male")
    elif engine == "fish":
        try:
            return synthesize_fish(text, out_path, voice=voice, api_key=fish_api_key)
        except TTSError as exc:
            import sys
            print(
                f"[TTS] Fish Audio failed ({exc}), falling back to edge-tts...",
                file=sys.stderr,
            )
            return synthesize_edge(text, out_path, voice="male")
    elif engine == "omnivoice":
        tts = OmniVoiceTTS(
            ref_audio=ref_audio, ref_text=ref_text, model_id=model_id, device=device
        )
        return tts.synthesize(text, out_path)
    else:
        return synthesize_edge(text, out_path, voice=voice)
