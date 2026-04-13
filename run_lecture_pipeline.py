#!/usr/bin/env python3
"""
Entrypoint: lecture transcript → style.json; PDF → slide images → agent JSON artifacts;
TTS → per-slide MP3; ffmpeg → one final MP4 named like the PDF.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from lecture_agents import arc_agent
from lecture_agents import narration_agent
from lecture_agents import pdf_render
from lecture_agents import premise_agent
from lecture_agents import slide_description_agent
from lecture_agents import style_agent
from lecture_agents import tts_gemini
from lecture_agents import video_assembly
from lecture_agents.config import REPO_ROOT


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Lecture PDF → narrated video pipeline.")
    p.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root (default: directory containing this script).",
    )
    p.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Path to Lecture 17 PDF (default: <repo>/Lecture_17_AI_screenplays.pdf).",
    )
    p.add_argument(
        "--transcript",
        type=Path,
        default=None,
        help="Lecture transcript text file (default: <repo>/lecture_transcript.txt).",
    )
    p.add_argument(
        "--mock-ai",
        action="store_true",
        help="Do not call remote models; emit stub JSON and silent MP3s for wiring tests.",
    )
    p.add_argument(
        "--skip-style",
        action="store_true",
        help="Do not regenerate style.json (must already exist).",
    )
    p.add_argument(
        "--skip-video",
        action="store_true",
        help="Stop after audio; skip ffmpeg assembly.",
    )
    p.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Use an existing project directory instead of creating project_YYYYMMDD_HHMMSS.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo = args.repo_root.resolve()
    pdf = (args.pdf or (repo / "Lecture_17_AI_screenplays.pdf")).resolve()
    transcript = (args.transcript or (repo / "lecture_transcript.txt")).resolve()

    if not pdf.is_file():
        print(f"ERROR: PDF not found: {pdf}", file=sys.stderr)
        return 2
    if not transcript.is_file():
        print(f"ERROR: Transcript not found: {transcript}", file=sys.stderr)
        return 2

    mock = bool(args.mock_ai)

    # 1) Style profile at repo root
    style_path = repo / "style.json"
    if args.skip_style:
        if not style_path.is_file():
            print(f"ERROR: --skip-style but missing {style_path}", file=sys.stderr)
            return 2
    else:
        print("Writing style.json from transcript...")
        style_path = style_agent.write_style_json(repo, transcript, mock=mock)
        print(f"  -> {style_path}")

    style = style_agent.load_style_json(repo)

    # 2) Project directory
    if args.project_dir is not None:
        project_dir = args.project_dir.resolve()
        project_dir.mkdir(parents=True, exist_ok=True)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = (repo / "projects" / f"project_{stamp}").resolve()
        project_dir.mkdir(parents=True, exist_ok=True)
    print(f"Project: {project_dir}")

    slide_img_dir = project_dir / "slide_images"
    audio_dir = project_dir / "audio"
    slide_img_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    # 3) Rasterize
    print("Rasterizing PDF...")
    image_paths = pdf_render.rasterize_pdf(pdf, slide_img_dir)
    print(f"  -> {len(image_paths)} PNGs in {slide_img_dir}")

    pdf_basename = pdf.name

    # 4) Slide descriptions
    print("Slide description agent...")
    slide_description_agent.write_slide_descriptions(
        project_dir,
        image_paths,
        pdf_basename=pdf_basename,
        mock=mock,
    )
    slide_doc = json.loads((project_dir / "slide_description.json").read_text(encoding="utf-8"))

    # 5) Premise
    print("Premise agent...")
    premise_agent.write_premise(project_dir, slide_doc, mock=mock)
    premise = json.loads((project_dir / "premise.json").read_text(encoding="utf-8"))

    # 6) Arc
    print("Arc agent...")
    arc_agent.write_arc(project_dir, premise, slide_doc, mock=mock)
    arc = json.loads((project_dir / "arc.json").read_text(encoding="utf-8"))

    # 7) Narration
    print("Narration agent...")
    narration_agent.write_slide_description_narration(
        project_dir,
        image_paths,
        style,
        premise,
        arc,
        slide_doc,
        pdf_basename=pdf_basename,
        mock=mock,
    )
    narr_doc = json.loads(
        (project_dir / "slide_description_narration.json").read_text(encoding="utf-8")
    )

    # 8) TTS
    print("TTS (Gemini)...")
    slides = narr_doc.get("slides", [])
    slides = sorted(slides, key=lambda s: int(s["slide_index"]))
    for row in slides:
        idx = int(row["slide_index"])
        out_mp3 = audio_dir / f"slide_{idx:03d}.mp3"
        narration = str(row.get("narration", "")).strip()
        if mock:
            tts_gemini.write_placeholder_mp3(out_mp3)
        else:
            if not narration:
                raise RuntimeError(f"Missing narration for slide {idx}")
            tts_gemini.synthesize_slide_mp3(narration, out_mp3)
        print(f"  -> {out_mp3.name}")

    if args.skip_video:
        print("Done (--skip-video).")
        return 0

    # 9) Video assembly
    print("Assembling video with ffmpeg...")
    ffmpeg = video_assembly.require_ffmpeg()
    segments_dir = project_dir / "segments_tmp"
    segments_dir.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    for row in slides:
        idx = int(row["slide_index"])
        png = project_dir / row.get("image", f"slide_images/slide_{idx:03d}.png")
        mp3 = audio_dir / f"slide_{idx:03d}.mp3"
        seg = segments_dir / f"seg_{idx:03d}.mp4"
        if not png.is_file():
            raise FileNotFoundError(png)
        if not mp3.is_file():
            raise FileNotFoundError(mp3)
        video_assembly.mux_slide_segment(ffmpeg, png=png, mp3=mp3, segment_mp4=seg)
        segments.append(seg)

    stem = Path(pdf_basename).stem
    out_mp4 = project_dir / f"{stem}.mp4"
    video_assembly.concat_segments(ffmpeg, segments, out_mp4)
    print(f"  -> {out_mp4}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
