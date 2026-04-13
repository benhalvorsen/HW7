from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF


def rasterize_pdf(pdf_path: Path, out_dir: Path, zoom: float = 2.0) -> list[Path]:
    """Render each PDF page to slide_images/slide_###.png. Returns paths in order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    paths: list[Path] = []
    try:
        mat = fitz.Matrix(zoom, zoom)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            name = f"slide_{i + 1:03d}.png"
            dest = out_dir / name
            pix.save(dest.as_posix())
            paths.append(dest)
    finally:
        doc.close()
    return paths
