# Lecture PDF → narrated video pipeline

This repository implements a multi-stage, agent-style pipeline that turns **Lecture 17** (`Lecture_17_AI_screenplays.pdf`) into a single **narrated MP4**: one still per slide, audio aligned to slide length, concatenated with **ffmpeg**.

## What you need

- **Python 3.10+**
- **`ffmpeg`** on your `PATH` (required for MP3 encoding, audio concatenation, and video mux/concat).
- **`GEMINI_API_KEY`** (or `GOOGLE_API_KEY`) for Gemini vision/text and Gemini TTS, unless you use `--mock-ai` for wiring tests only.

Place these files at the repository root before running:

- `Lecture_17_AI_screenplays.pdf` (lecture slide deck at repo root)
- `lecture_transcript.txt` (instructor transcript used to build `style.json`)

## Install

```bash
python -m pip install -r requirements.txt
```

## Run

From the repository root:

```bash
python run_lecture_pipeline.py
```

Options:

- `--transcript PATH` — override transcript file (default: `./lecture_transcript.txt`)
- `--pdf PATH` — override PDF path (default: `./Lecture_17_AI_screenplays.pdf`)
- `--skip-style` — reuse existing `style.json` without calling the model
- `--skip-video` — stop after generating `audio/slide_XXX.mp3`
- `--project-dir PATH` — write into an existing folder instead of `projects/project_YYYYMMDD_HHMMSS`
- `--mock-ai` — no API calls; stub JSON and tiny silent MP3s (for pipeline smoke tests)

### Environment

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Gemini API key |
| `GEMINI_MODEL` | Vision/text model (default: `gemini-2.0-flash`) |
| `GEMINI_TTS_MODEL` | TTS model (default: `gemini-2.5-flash-preview-tts`) |
| `GEMINI_TTS_VOICE` | Prebuilt voice name (default: `Kore`) |
| `FFMPEG_PATH` | Full path to `ffmpeg` / `ffmpeg.exe` if it is not on `PATH` |

## Pipeline stages

1. **Style** — reads the transcript → writes `style.json` (tone, pacing, fillers, framing, …).
2. **Project** — creates `projects/project_YYYYMMDD_HHMMSS/` with empty `slide_images/` and `audio/`.
3. **Rasterize** — renders each PDF page to `slide_images/slide_###.png` (PyMuPDF).
4. **Slide descriptions** — for each slide, Gemini sees the image plus prior descriptions → `slide_description.json`.
5. **Premise** — from slide descriptions → `premise.json`.
6. **Arc** — from premise + slide descriptions → `arc.json`.
7. **Narration** — per slide: image + `style.json` + premise + arc + full slide descriptions + prior narrations → `slide_description_narration.json`. Slide 1 includes self-introduction and a short topic summary.
8. **TTS** — Gemini TTS per narration (chunked for long text), merged to `audio/slide_001.mp3`, …
9. **Video** — per slide: PNG + MP3 → segment MP4 (`-shortest`), then concat → `<pdf_stem>.mp4` in the project folder.

## Repository layout

```text
your-repo/
├── README.md
├── style.json                 (generated on run; not required in git)
├── Lecture_17_AI_screenplays.pdf   (you add this)
├── lecture_transcript.txt     (sample provided; replace with real transcript)
├── requirements.txt
├── run_lecture_pipeline.py
├── lecture_agents/
└── projects/
    └── project_YYYYMMDD_HHMMSS/
        ├── slide_images/       (PNGs generated; gitignored)
        ├── audio/              (MP3s generated; gitignored)
        ├── premise.json
        ├── arc.json
        ├── slide_description.json
        └── slide_description_narration.json
```

Large artifacts (`*.png`, `*.mp3`, `*.mp4`) are listed in `.gitignore` per submission instructions.

### Grading / what to commit

After a **full successful run** (with a real API key, not `--mock-ai`), **commit the generated JSON** so the grader can review outputs without re-running:

- `style.json` (repo root)
- Under `projects/project_YYYYMMDD_HHMMSS/`: `premise.json`, `arc.json`, `slide_description.json`, and `slide_description_narration.json`

Do **not** commit `slide_images/`, `audio/`, `*.mp4`, or `segments_tmp/` — they stay ignored.

## Creating a tiny PDF for local tests

If you do not have the real deck yet:

```bash
python -c "import fitz; d=fitz.open(); d.new_page(); d.new_page(); d.save('Lecture_17_AI_screenplays.pdf'); d.close()"
```

Then run with `--mock-ai` or with a real API key.
