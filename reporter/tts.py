"""Story 1.3 — Text-to-Speech synthesis via OmniVoice (k2-fsa/OmniVoice).

Performs zero-shot voice cloning: given a short reference voice clip + its
transcription, OmniVoice renders the narration script in that cloned voice and
writes a 24 kHz ``report.wav`` into ``_bmad-output/temp/`` (AC 1.3.2 / 1.3.3).

Heavy ML imports (torch, omnivoice, soundfile) are deferred to call time so the
rest of the pipeline (and the unit tests) can import this module without them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

OUTPUT_SAMPLE_RATE = 24000  # OmniVoice emits 24 kHz mono audio.


class TTSError(RuntimeError):
    pass


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
                "torch==2.8.0 and omnivoice into .venv)."
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


def synthesize_report(
    text: str,
    out_path: Path,
    ref_audio: Path,
    ref_text: str,
    model_id: str = "k2-fsa/OmniVoice",
    device: str = "auto",
) -> Path:
    """Convenience entry point used by the orchestrator."""
    tts = OmniVoiceTTS(
        ref_audio=ref_audio, ref_text=ref_text, model_id=model_id, device=device
    )
    return tts.synthesize(text, out_path)
