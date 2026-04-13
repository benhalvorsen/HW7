from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config
from . import gemini_utils


PREMISE_SYSTEM = """You infer the lecture's teaching premise from slide descriptions."""


def build_premise(slide_doc: dict[str, Any], *, mock: bool) -> dict[str, Any]:
    if mock:
        return {
            "thesis": "Structured overview of the topic implied by the slide deck.",
            "scope": "Covers definitions, examples, and takeaways visible on slides.",
            "learning_objectives": [
                "Understand the main concepts introduced on the slides.",
                "Follow how ideas build from introduction to conclusion.",
            ],
            "audience": "Students in a lecture course.",
            "assumed_background": "Basic familiarity with the subject area.",
        }

    schema_hint = """Return JSON with keys:
- thesis (string)
- scope (string)
- learning_objectives (array of strings)
- audience (string)
- assumed_background (string)"""

    data = gemini_utils.generate_json_object(
        model=config.gemini_model(),
        system_instruction=PREMISE_SYSTEM,
        user_parts=[
            schema_hint,
            "\n--- slide_description.json ---\n",
            json.dumps(slide_doc, ensure_ascii=False, indent=2)[:200_000],
        ],
    )
    if not isinstance(data, dict):
        raise TypeError("premise agent: expected JSON object")
    return data


def write_premise(project_dir: Path, slide_doc: dict[str, Any], *, mock: bool) -> Path:
    premise = build_premise(slide_doc, mock=mock)
    out = project_dir / "premise.json"
    out.write_text(json.dumps(premise, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
