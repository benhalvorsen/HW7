from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config
from . import gemini_utils


NARR_SYSTEM = """You write spoken lecture narration that will be read aloud by TTS.
Match the instructor style profile: tone, pacing, fillers (use sparingly but naturally),
framing, and how ideas are introduced. Keep language clear for listening (not slide-reading).
Do not mention that you are an AI. Output spoken script only in JSON."""


def narrate_slides_sequential(
    image_paths: list[Path],
    style: dict[str, Any],
    premise: dict[str, Any],
    arc: dict[str, Any],
    slide_doc: dict[str, Any],
    *,
    pdf_basename: str,
    mock: bool,
) -> dict[str, Any]:
    slides_out: list[dict[str, Any]] = []
    by_index = {s["slide_index"]: s for s in slide_doc.get("slides", [])}
    model = config.gemini_model()

    for idx, img in enumerate(image_paths, start=1):
        slide_row = by_index.get(idx)
        if not slide_row:
            raise KeyError(f"Missing slide_description for slide_index={idx}")
        desc = slide_row["description"]
        rel = slide_row.get("image", f"slide_images/{img.name}")

        prior = [
            {"slide_index": s["slide_index"], "narration": s["narration"]}
            for s in slides_out
        ]

        if mock:
            slides_out.append(
                {
                    "slide_index": idx,
                    "image": rel,
                    "description": desc,
                    "narration": (
                        f"(Mock narration for slide {idx}.) "
                        f"This connects to the premise: {premise.get('thesis', '')[:120]}"
                    ),
                }
            )
            continue

        title_extra = ""
        if idx == 1:
            title_extra = """
This is the TITLE slide (slide 1). The speaker must introduce themselves by name and role
(e.g., course instructor) and give a short summary of the lecture topic and why it matters.
Keep it natural and brief (roughly 20–40 seconds spoken). Then transition into the slide content.
"""

        prompt = f"""PDF: {pdf_basename}
Current slide index: {idx} (1-based).
{title_extra}

--- style.json ---
{json.dumps(style, ensure_ascii=False, indent=2)}

--- premise.json ---
{json.dumps(premise, ensure_ascii=False, indent=2)}

--- arc.json ---
{json.dumps(arc, ensure_ascii=False, indent=2)}

--- this slide's description (from slide_description.json) ---
{desc}

--- prior slide narrations (JSON; may be empty) ---
{json.dumps(prior, ensure_ascii=False, indent=2)}

Task: Write the narration for THIS slide only. It should follow the arc, reflect the style profile,
and connect smoothly from prior narrations.

Return JSON: {{"narration": "<string>"}}"""

        data = gemini_utils.generate_json_object(
            model=model,
            system_instruction=NARR_SYSTEM,
            user_parts=[gemini_utils.image_part(img), prompt],
            temperature=0.55,
        )
        if not isinstance(data, dict) or "narration" not in data:
            raise RuntimeError(f"Slide {idx}: expected {{'narration': ...}} JSON")
        narration = str(data["narration"]).strip()
        if not narration:
            raise RuntimeError(f"Slide {idx}: empty narration")
        slides_out.append(
            {
                "slide_index": idx,
                "image": rel,
                "description": desc,
                "narration": narration,
            }
        )

    return {"pdf_basename": pdf_basename, "slides": slides_out}


def write_slide_description_narration(
    project_dir: Path,
    image_paths: list[Path],
    style: dict[str, Any],
    premise: dict[str, Any],
    arc: dict[str, Any],
    slide_doc: dict[str, Any],
    *,
    pdf_basename: str,
    mock: bool,
) -> Path:
    doc = narrate_slides_sequential(
        image_paths,
        style,
        premise,
        arc,
        slide_doc,
        pdf_basename=pdf_basename,
        mock=mock,
    )
    out = project_dir / "slide_description_narration.json"
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
