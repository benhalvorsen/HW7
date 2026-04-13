from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Sequence

from google import genai
from google.genai import types

from . import config


def client() -> genai.Client:
    key = config.gemini_api_key()
    if not key:
        raise RuntimeError(
            "Set GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment, or pass --mock-ai."
        )
    return genai.Client(api_key=key)


def generate_text(
    *,
    model: str,
    user_parts: Sequence[str | types.Part],
    system_instruction: str | None = None,
    temperature: float = 0.5,
) -> str:
    c = client()
    cfg = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
    )
    resp = c.models.generate_content(model=model, contents=list(user_parts), config=cfg)
    t = (resp.text or "").strip()
    if not t:
        raise RuntimeError("Empty model response (text).")
    return t


def generate_json_object(
    *,
    model: str,
    user_parts: Sequence[str | types.Part],
    system_instruction: str | None = None,
    temperature: float = 0.35,
) -> Any:
    c = client()
    cfg = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        response_mime_type="application/json",
    )
    resp = c.models.generate_content(model=model, contents=list(user_parts), config=cfg)
    t = (resp.text or "").strip()
    if not t:
        raise RuntimeError("Empty model response (JSON).")
    return json.loads(t)


def image_part(path: Path) -> types.Part:
    data = path.read_bytes()
    return types.Part.from_bytes(data=data, mime_type="image/png")


def pcm_to_wav_bytes(pcm: bytes, *, rate: int = 24000, channels: int = 1) -> bytes:
    import wave
    from io import BytesIO

    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def synthesize_speech_wav_bytes(text: str) -> bytes:
    """Single Gemini TTS call; returns WAV bytes (PCM wrapped)."""
    c = client()
    prompt = text.strip()
    if not prompt:
        raise ValueError("TTS text is empty.")
    resp = c.models.generate_content(
        model=config.gemini_tts_model(),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=config.gemini_tts_voice(),
                    )
                )
            ),
        ),
    )
    cand = resp.candidates
    if not cand:
        raise RuntimeError("TTS: no candidates returned.")
    parts = cand[0].content.parts if cand[0].content else []
    if not parts or not parts[0].inline_data or not parts[0].inline_data.data:
        raise RuntimeError("TTS: missing inline audio data.")
    raw = parts[0].inline_data.data
    pcm = base64.b64decode(raw) if isinstance(raw, str) else raw
    if not isinstance(pcm, (bytes, bytearray)):
        raise TypeError("TTS inline audio payload must be bytes or base64 string")
    return pcm_to_wav_bytes(bytes(pcm))
