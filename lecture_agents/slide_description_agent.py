from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config
from . import gemini_utils


DESC_SYSTEM = """You describe lecture slides for downstream narration planning.
Be accurate to the visible slide: titles, bullets, diagrams, and emphasis.
Do not invent content that is not reasonably visible."""


def describe_slides_sequential(
    image_paths: list[Path],
    *,
    pdf_basename: str,
    mock: bool,
) -> dict[str, Any]:
    slides: list[dict[str, Any]] = []
    model = config.gemini_model()

    for idx, img in enumerate(image_paths, start=1):
        rel = f"slide_images/{img.name}"
        prev = [
            {"slide_index": s["slide_index"], "description": s["description"]}
            for s in slides
        ]
        if mock:
            slides.append(
                {
                    "slide_index": idx,
                    "image": rel,
                    "description": f"(Mock) Slide {idx} summary based on filename {img.name}.",
                }
            )
            continue

        prompt = f"""PDF: {pdf_basename}
Current slide index: {idx} (1-based).
You are given the slide image.

Previous slide descriptions (JSON, may be empty):
{json.dumps(prev, ensure_ascii=False, indent=2)}

Task: Describe ONLY this slide's visible content and pedagogical role given prior context.
Return JSON: {{"description": "<string>"}}"""

        data = gemini_utils.generate_json_object(
            model=model,
            system_instruction=DESC_SYSTEM,
            user_parts=[gemini_utils.image_part(img), prompt],
        )
        if not isinstance(data, dict) or "description" not in data:
            raise RuntimeError(f"Slide {idx}: expected {{'description': ...}} JSON")
        slides.append(
            {
                "slide_index": idx,
                "image": rel,
                "description": str(data["description"]).strip(),
            }
        )

    return {"pdf_basename": pdf_basename, "slides": slides}


def write_slide_descriptions(
    project_dir: Path,
    image_paths: list[Path],
    *,
    pdf_basename: str,
    mock: bool,
) -> Path:
    doc = describe_slides_sequential(image_paths, pdf_basename=pdf_basename, mock=mock)
    out = project_dir / "slide_description.json"
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
