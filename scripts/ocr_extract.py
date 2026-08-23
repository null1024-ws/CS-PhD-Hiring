"""OCR note images. EasyOCR is used when available; tests may inject a reader."""

from __future__ import annotations

import json
from pathlib import Path

from _paths import RAW_IMAGES, RAW_OCR, ensure_dirs


def ocr_image(reader, path: Path) -> tuple[str, float]:
    results = reader.readtext(str(path))
    lines = []
    confidences = []
    for _bbox, text, conf in results:
        lines.append(text)
        confidences.append(float(conf))
    avg = sum(confidences) / len(confidences) if confidences else 0.0
    return "\n".join(lines), avg


def ocr_note_images(
    note_id: str,
    image_dir: Path | None = None,
    out_dir: Path | None = None,
    reader=None,
) -> dict:
    ensure_dirs()
    note_dir = image_dir or (RAW_IMAGES / note_id)
    dest = out_dir or RAW_OCR
    dest.mkdir(parents=True, exist_ok=True)
    images = []
    if note_dir.is_dir():
        images = sorted(
            p for p in note_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )
    if not images:
        payload = {"note_id": note_id, "pages": [], "full_text": "", "confidence": 0.0}
        (dest / f"{note_id}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return payload

    if reader is None:
        import easyocr

        reader = easyocr.Reader(["ch_sim", "en"], gpu=False)

    pages = []
    for img in images:
        text, conf = ocr_image(reader, img)
        pages.append({"file": img.name, "text": text, "confidence": round(conf, 3)})
    payload = {
        "note_id": note_id,
        "pages": pages,
        "full_text": "\n\n".join(p["text"] for p in pages if p["text"]),
        "confidence": round(
            sum(p["confidence"] for p in pages) / len(pages),
            3,
        ),
    }
    (dest / f"{note_id}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload
