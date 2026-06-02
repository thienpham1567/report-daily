"""Daily Video Reporter — pipeline package.

Modules:
    config          Configuration loading (env + project-context.md).
    git_extractor   Story 1.2 — extract & group today's git commits.
    script_builder  Story 1.3 — build the Vietnamese narration script.
    tts             Story 1.3 — OmniVoice voice-clone TTS -> report.wav.
    video           Story 1.4 — HeyGen HyperFrames HTML -> 1080p mp4.
    devzone         Story 1.5 — REST client to publish the report document.
"""

__all__ = [
    "config",
    "git_extractor",
    "script_builder",
    "tts",
    "video",
    "devzone",
]
