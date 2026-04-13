from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from . import gemini_utils
from . import video_assembly


def _split_text_chunks(text: str, max_chars: int = 2400) -> list[str]:
    t = text.strip()
    if len(t) <= max_chars:
        return [t]
    parts: list[str] = []
    sentences = re.split(r"(?<=[.!?])\s+", t)
    buf: list[str] = []
    size = 0
    for s in sentences:
        if not s:
            continue
        if size + len(s) + 1 > max_chars and buf:
            parts.append(" ".join(buf).strip())
            buf = [s]
            size = len(s)
        else:
            buf.append(s)
            size += len(s) + 1
    if buf:
        parts.append(" ".join(buf).strip())
    return [p for p in parts if p]


def _wav_to_mp3(ffmpeg: str, wav_path: Path, mp3_path: Path) -> None:
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            wav_path.as_posix(),
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            mp3_path.as_posix(),
        ],
        check=True,
    )


def _concat_wavs_to_mp3(ffmpeg: str, wav_paths: list[Path], out_mp3: Path) -> None:
    if not wav_paths:
        raise ValueError("No WAV chunks to concatenate.")
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    if len(wav_paths) == 1:
        _wav_to_mp3(ffmpeg, wav_paths[0], out_mp3)
        return
    inputs: list[str] = []
    for w in wav_paths:
        inputs.extend(["-i", w.as_posix()])
    n = len(wav_paths)
    labeled = "".join(f"[{i}:a]" for i in range(n))
    filt = f"{labeled}concat=n={n}:v=0:a=1[aout]"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            *inputs,
            "-filter_complex",
            filt,
            "-map",
            "[aout]",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            out_mp3.as_posix(),
        ],
        check=True,
    )


def write_placeholder_mp3(out_mp3: Path, duration_sec: float = 0.5) -> None:
    """Short silent MP3 for --mock-ai smoke tests (no API)."""
    ffmpeg = video_assembly.require_ffmpeg()
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r=24000:cl=mono",
            "-t",
            str(duration_sec),
            "-c:a",
            "libmp3lame",
            "-q:a",
            "9",
            out_mp3.as_posix(),
        ],
        check=True,
    )


def synthesize_slide_mp3(narration: str, out_mp3: Path) -> None:
    """Gemini TTS per chunk, merge to one MP3 via ffmpeg."""
    ffmpeg = video_assembly.require_ffmpeg()
    chunks = _split_text_chunks(narration)
    if not chunks:
        raise ValueError("Empty narration for TTS.")

    tmp_paths: list[Path] = []
    try:
        for ch in chunks:
            payload = f"Speak the following lecture narration naturally and clearly:\n\n{ch}"
            wav_bytes = gemini_utils.synthesize_speech_wav_bytes(payload)
            fd, name = tempfile.mkstemp(suffix=".wav")
            try:
                os.write(fd, wav_bytes)
            finally:
                os.close(fd)
            tmp_paths.append(Path(name))
        _concat_wavs_to_mp3(ffmpeg, tmp_paths, out_mp3)
    finally:
        for p in tmp_paths:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
