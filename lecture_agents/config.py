from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def env_str(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    return v


def gemini_api_key() -> str | None:
    return env_str("GEMINI_API_KEY") or env_str("GOOGLE_API_KEY")


def gemini_model() -> str:
    return env_str("GEMINI_MODEL", "gemini-2.0-flash") or "gemini-2.0-flash"


def gemini_tts_model() -> str:
    return (
        env_str("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
        or "gemini-2.5-flash-preview-tts"
    )


def gemini_tts_voice() -> str:
    return env_str("GEMINI_TTS_VOICE", "Kore") or "Kore"
