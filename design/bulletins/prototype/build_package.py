"""Turn an agent's draft transcription + the source PDF into a bulletin package.

The agent only decides *what* to crop (page + normalized bbox on the displayed page);
this tool does the pixel work deterministically, so every package gets identical image
handling:

    packages/<id>/bulletin.json
    packages/<id>/images/<image-id>.<ext>

Usage (from the repo root):
    uv run --no-sync python design/bulletins/prototype/build_package.py \
        "BC 017 Al 04-1995.pdf" .claude/tmp/bulletins/work/bc-017.draft.json \
        .claude/tmp/bulletins/packages
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

# Rendering policy per image kind: (dpi, output format).
# 200 dpi is the useful ceiling for these MRC scans (foreground mask resolution);
# page previews are lighter because they are only for the "original document" viewer.
RENDER_POLICY: dict[str, tuple[int, str]] = {
    "page": (150, "jpg"),
    "photo": (200, "jpg"),
    "illustration": (200, "jpg"),
    "masthead": (200, "png"),
    "handwriting": (200, "png"),
    "signature": (200, "png"),
    "document": (200, "png"),
}
MEDIA_TYPES = {"jpg": "image/jpeg", "png": "image/png"}
# Ink crops are trimmed to their content so a loose bbox from the agent still gives a tight image.
TRIM_KINDS = {"handwriting", "signature"}
TRIM_THRESHOLD = 180  # grey level under which a pixel counts as ink
TRIM_PADDING = 16  # px kept around the ink
# Scanned paper is light grey, not white: blended onto the page (mix-blend-mode: multiply)
# it shows as a faint box. Pushing near-white to pure white makes the paper vanish while
# keeping pencil strokes (~150-190) and halftone greys intact.
PAPER_KINDS = {"handwriting", "signature", "masthead"}
PAPER_THRESHOLD = 215
# Keys whose string values are identifiers or paths, never prose.
NO_TYPOGRAPHY_KEYS = {"$schema", "file_name", "file"}
SCHEMA = Path(__file__).resolve().parent.parent / "bulletin.schema.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_page(doc: pymupdf.Document, page_number: int, dpi: int) -> Image.Image:
    """Render one page *as displayed* (rotation applied), in greyscale."""
    pix = doc[page_number - 1].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")


def trim_to_ink(im: Image.Image) -> Image.Image:
    mask = im.point(lambda v: 255 if v < TRIM_THRESHOLD else 0)
    box = mask.getbbox()
    if box is None:
        return im
    x0, y0, x1, y1 = box
    return im.crop(
        (
            max(0, x0 - TRIM_PADDING),
            max(0, y0 - TRIM_PADDING),
            min(im.width, x1 + TRIM_PADDING),
            min(im.height, y1 + TRIM_PADDING),
        )
    )


def encode(im: Image.Image, fmt: str, kind: str) -> bytes:
    buf = io.BytesIO()
    if fmt == "jpg":
        quality = 78 if kind == "page" else 88
        im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    else:
        # Line art on paper: 16 grey levels keep strokes crisp at a fraction of the size.
        im.quantize(colors=16, dither=Image.Dither.NONE).save(buf, "PNG", optimize=True)
    return buf.getvalue()


def typography(value, key: str | None = None):
    """Typographic apostrophes in prose; ids, paths and URLs are left alone."""
    if isinstance(value, dict):
        return {k: typography(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [typography(v, key) for v in value]
    if isinstance(value, str) and key not in NO_TYPOGRAPHY_KEYS:
        return value.replace("'", "’")
    return value


def build(pdf_path: Path, draft_path: Path, out_root: Path) -> Path:
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    doc = pymupdf.open(pdf_path)

    package = out_root / draft["id"]
    images_dir = package / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    source = draft["source"]
    source["sha256"] = sha256_bytes(pdf_path.read_bytes())
    if source["page_count"] != doc.page_count:
        raise SystemExit(f"page_count says {source['page_count']}, the PDF has {doc.page_count} pages")

    renders: dict[tuple[int, int], Image.Image] = {}
    for image in draft["images"]:
        kind = image["kind"]
        dpi, fmt = RENDER_POLICY[kind]
        page_number = image["source"]["page"]
        if (page_number, dpi) not in renders:
            renders[(page_number, dpi)] = render_page(doc, page_number, dpi)
        page_im = renders[(page_number, dpi)]

        if kind == "page":
            im = page_im
        else:
            x0, y0, x1, y1 = image["source"]["bbox"]
            w, h = page_im.size
            im = page_im.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
            if kind in TRIM_KINDS:
                im = trim_to_ink(im)
            if kind in PAPER_KINDS:
                im = im.point(lambda v: 255 if v >= PAPER_THRESHOLD else v)
        if kind == "photo":
            im = ImageOps.autocontrast(im, cutoff=0.5)

        data = encode(im, fmt, kind)
        rel = f"images/{image['id']}.{fmt}"
        (package / rel).write_bytes(data)
        image.update(
            {
                "file": rel,
                "media_type": MEDIA_TYPES[fmt],
                "width": im.width,
                "height": im.height,
                "sha256": sha256_bytes(data),
            }
        )
        image["source"]["dpi"] = dpi

    # Stable key order inside each image entry, for readable diffs between runs.
    order = ["id", "file", "kind", "media_type", "width", "height", "sha256", "source", "alt", "caption", "transcript"]
    draft["images"] = [{k: img[k] for k in order if k in img} for img in draft["images"]]
    draft["$schema"] = os.path.relpath(SCHEMA, package.resolve())  # lets editors validate the file in place

    package_json = typography(draft)
    (package / "bulletin.json").write_text(
        json.dumps(package_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return package


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    out = build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    total = sum(f.stat().st_size for f in (out / "images").iterdir())
    print(f"package written to {out} ({len(list((out / 'images').iterdir()))} images, {total / 1024:.0f} KiB)")
