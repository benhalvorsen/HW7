from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config
from . import gemini_utils


ARC_SYSTEM = """You design a coherent spoken arc for narrating a slide deck."""


def build_arc(premise: dict[str, Any], slide_doc: dict[str, Any], *, mock: bool) -> dict[str, Any]:
    if mock:
        return {
            "flow": "Introduce topic, develop core ideas slide by slide, synthesize and close.",
            "acts": [
                {"name": "Opening", "goal": "Orient the listener to goals and context."},
                {"name": "Development", "goal": "Explain each slide in order with connective tissue."},
                {"name": "Closing", "goal": "Reinforce takeaways and how pieces fit together."},
            ],
            "idea_build": "Each narration bridges from prior slide to the next claim or example.",
            "transitions": "Use light recap + forward pointer between slides.",
        }

    schema_hint = """Return JSON with keys:
- flow (string): one paragraph on overall progression
- acts (array of objects with name, goal)
- idea_build (string): how concepts accumulate across slides
- transitions (string): how to move between slides orally"""

    data = gemini_utils.generate_json_object(
        model=config.gemini_model(),
        system_instruction=ARC_SYSTEM,
        user_parts=[
            schema_hint,
            "\n--- premise.json ---\n",
            json.dumps(premise, ensure_ascii=False, indent=2),
            "\n--- slide_description.json ---\n",
            json.dumps(slide_doc, ensure_ascii=False, indent=2)[:200_000],
        ],
    )
    if not isinstance(data, dict):
        raise TypeError("arc agent: expected JSON object")
    return data


def write_arc(
    project_dir: Path,
    premise: dict[str, Any],
    slide_doc: dict[str, Any],
    *,
    mock: bool,
) -> Path:
    arc = build_arc(premise, slide_doc, mock=mock)
    out = project_dir / "arc.json"
    out.write_text(json.dumps(arc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
