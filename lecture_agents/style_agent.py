from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config
from . import gemini_utils


STYLE_SYSTEM = """You analyze lecture transcripts and output a compact JSON object
describing how the instructor speaks. Be concrete and evidence-based."""


def build_style_from_transcript(transcript_text: str, *, mock: bool) -> dict[str, Any]:
    if mock:
        return {
            "tone": "Conversational, approachable, lightly enthusiastic.",
            "pacing": "Moderate with pauses after key claims; speeds up on examples.",
            "fillers": ["um", "you know", "right?", "so"],
            "framing": "Uses signposting ('first', 'next', 'the key idea is') and rhetorical questions.",
            "sentence_shape": "Mix of short punchy sentences and longer explanatory ones with em dashes.",
            "emphasis": "Repeats technical terms once slowly, then uses them fluently.",
            "audience_address": "Speaks directly to students as 'you' and 'we'.",
        }

    schema_hint = """Return JSON with keys:
- tone (string)
- pacing (string)
- fillers (array of strings)
- framing (string): how they introduce, connect, and conclude ideas
- sentence_shape (string)
- emphasis (string)
- audience_address (string)
Optional: register (string), hedging (string)."""

    data = gemini_utils.generate_json_object(
        model=config.gemini_model(),
        system_instruction=STYLE_SYSTEM,
        user_parts=[
            schema_hint,
            "\n--- TRANSCRIPT ---\n",
            transcript_text[:120_000],
        ],
    )
    if not isinstance(data, dict):
        raise TypeError("style agent: expected JSON object")
    return data


def write_style_json(repo_root: Path, transcript_path: Path, *, mock: bool) -> Path:
    text = transcript_path.read_text(encoding="utf-8", errors="replace")
    style = build_style_from_transcript(text, mock=mock)
    out = repo_root / "style.json"
    out.write_text(json.dumps(style, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def load_style_json(repo_root: Path) -> dict[str, Any]:
    p = repo_root / "style.json"
    if not p.is_file():
        raise FileNotFoundError(f"Missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))
