"""Validate a bulletin package: JSON Schema (structure) + semantic checks (integrity).

JSON Schema cannot express cross-references, so the second pass checks what an importer
must be able to trust before touching the database:

- ids: images and articles unique; image ids prefixed by the document id;
- every image reference resolves; every image file exists, matches its sha256,
  dimensions, media type and the images/<id>.<ext> naming rule;
- page previews: exactly one per PDF page, in order; bbox present iff kind != page;
- articles: pages within the PDF, ascending; tables: every row as wide as the header;
- events: start <= end.

Usage (from the repo root):
    uv run --no-sync --with jsonschema python design/bulletins/prototype/validate.py \
        .claude/tmp/bulletins/packages/bc-017
Exit code 0 = valid, 1 = invalid.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

# Not a project dependency yet (the real feature will `uv add jsonschema`): run with `uv run --with jsonschema`.
from jsonschema import Draft202012Validator  # ty: ignore[unresolved-import]
from PIL import Image

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "bulletin.schema.json"
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def iter_blocks(blocks):
    for block in blocks:
        yield block
        if block["type"] in ("news_item", "aside"):
            yield from iter_blocks(block["blocks"])


def iter_inline(value):
    """Yield every inline run of an inline_text value."""
    if isinstance(value, list):
        for run in value:
            if isinstance(run, dict):
                yield run


def inline_fields(block):
    """All inline_text values carried by one block."""
    t = block["type"]
    if t == "paragraph":
        yield block["text"]
    elif t == "list":
        yield from block["items"]
    elif t == "quote":
        yield from block["paragraphs"]
    elif t in ("figure", "gallery"):
        if "caption" in block:
            yield block["caption"]
        for item in block.get("items", []):
            if "caption" in item:
                yield item["caption"]
    elif t == "table":
        for group in block["row_groups"]:
            for row in group["rows"]:
                yield from (cell for cell in row if cell is not None)
    elif t == "signature":
        yield from (block[k] for k in ("closing", "name") if k in block)
    elif t == "news_item":
        yield block["subject"]
        if "headline" in block:
            yield block["headline"]


def semantic_checks(data: dict, package: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    stats: Counter = Counter()

    doc_id = data["id"]
    page_count = data["source"]["page_count"]
    images = {}
    for img in data["images"]:
        if img["id"] in images:
            errors.append(f"image id {img['id']!r} is duplicated")
        images[img["id"]] = img
        if not img["id"].startswith(f"{doc_id}-"):
            errors.append(f"image id {img['id']!r} must start with the document id '{doc_id}-'")
        expected_file = f"images/{img['id']}.{EXTENSIONS[img['media_type']]}"
        if img["file"] != expected_file:
            errors.append(f"image {img['id']!r}: file must be {expected_file!r}, got {img['file']!r}")
        path = package / img["file"]
        if not path.is_file():
            errors.append(f"image {img['id']!r}: missing file {img['file']}")
        else:
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != img["sha256"]:
                errors.append(f"image {img['id']!r}: sha256 mismatch")
            with Image.open(path) as im:
                if im.size != (img["width"], img["height"]):
                    actual = f"{im.size[0]}x{im.size[1]}"
                    errors.append(f"image {img['id']!r}: file is {actual}, JSON says {img['width']}x{img['height']}")
                if Image.MIME.get(im.format) != img["media_type"]:
                    errors.append(
                        f"image {img['id']!r}: file is {Image.MIME.get(im.format)}, JSON says {img['media_type']}"
                    )
        src = img["source"]
        if not 1 <= src["page"] <= page_count:
            errors.append(f"image {img['id']!r}: page {src['page']} outside 1..{page_count}")
        has_bbox = "bbox" in src
        if img["kind"] == "page" and has_bbox:
            errors.append(f"image {img['id']!r}: a page preview must not have a bbox")
        if img["kind"] != "page":
            if not has_bbox:
                errors.append(f"image {img['id']!r}: bbox required for kind {img['kind']!r}")
            else:
                x0, y0, x1, y1 = src["bbox"]
                if not (x0 < x1 and y0 < y1):
                    errors.append(f"image {img['id']!r}: bbox must satisfy x0 < x1 and y0 < y1")

    referenced: Counter = Counter()

    def ref(image_id: str, where: str) -> None:
        referenced[image_id] += 1
        if image_id not in images:
            errors.append(f"{where}: unknown image {image_id!r}")

    for key in ("masthead_image", "cover_image"):
        if key in data:
            ref(data[key], key)

    pages = data["source"]["pages"]
    if [p["number"] for p in pages] != list(range(1, page_count + 1)):
        errors.append(f"source.pages must list pages 1..{page_count} in order")
    for p in pages:
        ref(p["image"], f"source.pages[{p['number']}]")
        if images.get(p["image"], {}).get("kind") not in (None, "page"):
            errors.append(f"source.pages[{p['number']}]: image {p['image']!r} is not a page preview")

    for m in data.get("marginalia", []):
        ref(m["image"], "marginalia")

    article_ids: set[str] = set()
    for art in data["articles"]:
        aid = art["id"]
        if aid in article_ids:
            errors.append(f"article id {aid!r} is duplicated")
        article_ids.add(aid)
        if any(not 1 <= p <= page_count for p in art["pages"]):
            errors.append(f"article {aid!r}: pages outside 1..{page_count}")
        if art["pages"] != sorted(art["pages"]):
            errors.append(f"article {aid!r}: pages must be ascending")
        stats[f"script:{art['script']}"] += 1
        for block in iter_blocks(art["blocks"]):
            stats[f"block:{block['type']}"] += 1
            where = f"article {aid!r} {block['type']}"
            if block["type"] in ("figure", "gallery"):
                # Caption coverage, so a reviewer sees which pictures still have none.
                for placed in block.get("items", [block]):
                    stats["pictures"] += 1
                    if "caption" in placed:
                        kind = "editorial" if placed.get("caption_editorial") else "printed"
                        stats[f"captions:{kind}"] += 1
            if block["type"] == "figure":
                ref(block["image"], where)
            elif block["type"] == "gallery":
                image_ids = [item["image"] for item in block["items"]]
                if len(set(image_ids)) != len(image_ids):
                    errors.append(f"{where}: the same picture appears twice")
                for image_id in image_ids:
                    ref(image_id, where)
            elif block["type"] == "signature" and "image" in block:
                ref(block["image"], where)
            elif block["type"] == "table":
                width = len(block["columns"])
                for g, group in enumerate(block["row_groups"]):
                    for r, row in enumerate(group["rows"]):
                        if len(row) != width:
                            errors.append(
                                f"{where}: row_groups[{g}].rows[{r}] has {len(row)} cells, header has {width}"
                            )
            elif block["type"] == "event":
                for d in block["dates"]:
                    if "start" in d and "end" in d and d["end"] < d["start"]:
                        errors.append(f"{where}: date {d['text']!r} ends before it starts")
            for value in inline_fields(block):
                for run in iter_inline(value):
                    kind = run.get("kind")
                    if kind == "illegible":
                        ref(run["image"], f"{where} (illegible span)")
                        stats["inline:illegible"] += 1
                    elif kind == "uncertain":
                        stats["inline:uncertain"] += 1
        if "byline" in art:
            for run in iter_inline(art["byline"]):
                if run.get("kind") == "uncertain":
                    stats["inline:uncertain"] += 1

    for note in data["processing"].get("notes", []):
        if "article" in note and note["article"] not in article_ids:
            errors.append(f"processing note refers to unknown article {note['article']!r}")
        if "page" in note and not 1 <= note["page"] <= page_count:
            errors.append(f"processing note refers to page {note['page']} outside 1..{page_count}")

    for image_id in images:
        if referenced[image_id] == 0:
            warnings.append(f"image {image_id!r} is never referenced")

    return errors, warnings, dict(sorted(stats.items()))


def main(package: Path) -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    data = json.loads((package / "bulletin.json").read_text(encoding="utf-8"))

    schema_errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.absolute_path))
    for err in schema_errors:
        path = "/".join(str(p) for p in err.absolute_path) or "(root)"
        print(f"SCHEMA  {path}: {err.message[:300]}")
    if schema_errors:
        print(f"\n{len(schema_errors)} schema error(s); semantic checks skipped.")
        return 1

    errors, warnings, stats = semantic_checks(data, package)
    for e in errors:
        print(f"ERROR   {e}")
    for w in warnings:
        print(f"WARNING {w}")
    print(f"\n{data['id']}: {len(data['articles'])} articles, {len(data['images'])} images")
    print("stats:", ", ".join(f"{k}={v}" for k, v in stats.items()))
    print("VALID" if not errors else f"INVALID ({len(errors)} error(s))")
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    sys.exit(main(Path(sys.argv[1])))
