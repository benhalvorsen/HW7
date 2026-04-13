from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def require_ffmpeg() -> str:
    override = os.environ.get("FFMPEG_PATH", "").strip()
    if override:
        p = Path(override)
        if p.is_file():
            return p.as_posix()
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install ffmpeg, add it to PATH, "
            "or set FFMPEG_PATH to the full path of ffmpeg.exe."
        )
    return exe


def mux_slide_segment(
    ffmpeg: str,
    *,
    png: Path,
    mp3: Path,
    segment_mp4: Path,
) -> None:
    segment_mp4.parent.mkdir(parents=True, exist_ok=True)
    # -shortest: video length follows audio (still image loops); avoids silent tail beyond audio.
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-loop",
        "1",
        "-i",
        png.as_posix(),
        "-i",
        mp3.as_posix(),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        "-movflags",
        "+faststart",
        segment_mp4.as_posix(),
    ]
    subprocess.run(cmd, check=True)


def concat_segments(ffmpeg: str, segments: list[Path], out_mp4: Path) -> None:
    if not segments:
        raise ValueError("No segments to concatenate.")
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    list_path = out_mp4.with_name("concat_list.txt")
    lines = []
    for p in segments:
        # concat demuxer: escape single quotes per ffmpeg docs
        s = p.resolve().as_posix().replace("'", r"'\''")
        lines.append(f"file '{s}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path.as_posix(),
        "-c",
        "copy",
        out_mp4.as_posix(),
    ]
    subprocess.run(cmd, check=True)
