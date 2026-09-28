"""Validate and extract an uploaded bulletin package (zip of bulletin.json + images/).

Two layers, same as design/bulletins/prototype/validate.py:
- JSON Schema (structure): bulletin.schema.json (copied alongside this module --
  design/bulletins/ is scratch/spec material, not a production dependency).
- Semantic checks (integrity) JSON Schema cannot express: ids unique, every image
  reference resolves, every image file exists/matches its sha256/dimensions/media
  type, page previews exactly one per PDF page in order, articles' pages ascending,
  table rows as wide as the header, events' start <= end.

A schema error is fatal (the package is fundamentally malformed): semantic checks
are skipped and the whole upload is rejected. A semantic error is recorded in the
validation report but the package is still staged for review -- a human decides
whether to fix it and re-upload, or discard it.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator
from PIL import Image, UnidentifiedImageError

SCHEMA_PATH = Path(__file__).resolve().parent / "bulletin.schema.json"
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PACKAGE_SIZE = 50 * 1024 * 1024  # 50 Mo, matches documents.validators.MAX_DOCUMENT_SIZE
MAX_PACKAGE_FILES = 500


class PackageValidationError(Exception):
    """The package is fundamentally malformed -- reject the upload outright."""


@dataclass
class PackageValidationResult:
    data: dict
    images: dict[str, bytes]  # image_id -> raw bytes
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def _safe_member_path(name: str) -> None:
    if name.startswith("/") or name.startswith("\\"):
        raise PackageValidationError(f"chemin absolu interdit dans le paquet : {name!r}")
    if ".." in Path(name).parts:
        raise PackageValidationError(f"chemin remontant interdit dans le paquet : {name!r}")


def _open_zip_safely(zip_file) -> dict[str, bytes]:
    """Returns {name: bytes} for every member, after rejecting anything but
    bulletin.json and images/*.{jpg,jpeg,png,webp}, symlinks, path traversal,
    and packages that are too large or contain too many files."""
    try:
        zf = zipfile.ZipFile(zip_file)
    except zipfile.BadZipFile as exc:
        raise PackageValidationError("le fichier n'est pas une archive zip valide") from exc

    infos = zf.infolist()
    if len(infos) > MAX_PACKAGE_FILES:
        raise PackageValidationError(f"le paquet contient plus de {MAX_PACKAGE_FILES} fichiers")

    total_size = 0
    members: dict[str, bytes] = {}
    for info in infos:
        name = info.filename
        if name.endswith("/"):
            continue  # directory entry
        _safe_member_path(name)
        # A symlink's Unix mode bits live in the high 16 bits of external_attr.
        is_symlink = ((info.external_attr >> 16) & 0o170000) == 0o120000
        if is_symlink:
            raise PackageValidationError(f"lien symbolique interdit dans le paquet : {name!r}")
        if name != "bulletin.json" and not (
            name.startswith("images/") and Path(name).suffix.lower() in ALLOWED_IMAGE_SUFFIXES
        ):
            raise PackageValidationError(f"fichier inattendu dans le paquet : {name!r}")
        total_size += info.file_size
        if total_size > MAX_PACKAGE_SIZE:
            raise PackageValidationError(
                f"le paquet dépasse la taille maximale de {MAX_PACKAGE_SIZE // (1024 * 1024)} Mo"
            )
        members[name] = zf.read(info)

    if "bulletin.json" not in members:
        raise PackageValidationError("le paquet ne contient pas de bulletin.json")
    return members


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


def semantic_checks(data: dict, images_bytes: dict[str, bytes]) -> tuple[list[str], list[str], dict]:
    """Port of design/bulletins/prototype/validate.py's semantic_checks(), reading
    image bytes from the extracted zip members instead of a package directory."""
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
        payload = images_bytes.get(img["file"])
        if payload is None:
            errors.append(f"image {img['id']!r}: missing file {img['file']}")
        else:
            if hashlib.sha256(payload).hexdigest() != img["sha256"]:
                errors.append(f"image {img['id']!r}: sha256 mismatch")
            try:
                with Image.open(io.BytesIO(payload)) as im:
                    if im.size != (img["width"], img["height"]):
                        actual = f"{im.size[0]}x{im.size[1]}"
                        errors.append(
                            f"image {img['id']!r}: file is {actual}, JSON says {img['width']}x{img['height']}"
                        )
                    if Image.MIME.get(im.format) != img["media_type"]:
                        errors.append(
                            f"image {img['id']!r}: file is {Image.MIME.get(im.format)}, JSON says {img['media_type']}"
                        )
            except UnidentifiedImageError:
                errors.append(f"image {img['id']!r}: file is not a readable image")
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


def validate_package(zip_file) -> PackageValidationResult:
    """Validates an uploaded zip (a Django UploadedFile or any file-like object
    zipfile.ZipFile accepts). Raises PackageValidationError for anything that
    makes the package fundamentally unusable (bad zip, unsafe paths, missing
    bulletin.json, schema errors). Semantic-check errors are returned in the
    result instead of raised -- the package is still staged for review."""
    members = _open_zip_safely(zip_file)

    try:
        data = json.loads(members["bulletin.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageValidationError(f"bulletin.json n'est pas du JSON valide : {exc}") from exc

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema_errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.absolute_path))
    if schema_errors:
        messages = []
        for err in schema_errors:
            path = "/".join(str(p) for p in err.absolute_path) or "(root)"
            messages.append(f"{path}: {err.message[:300]}")
        raise PackageValidationError("erreurs de schéma :\n" + "\n".join(messages))

    images_bytes = {name: payload for name, payload in members.items() if name.startswith("images/")}
    errors, warnings, stats = semantic_checks(data, images_bytes)
    image_id_bytes = {img["id"]: images_bytes[img["file"]] for img in data["images"] if img["file"] in images_bytes}
    return PackageValidationResult(data=data, images=image_id_bytes, errors=errors, warnings=warnings, stats=stats)


def flatten_bulletin_text(data: dict) -> str:
    """All user-visible prose in one string, for full-text search -- the
    summary plus every article's flattened inline text."""
    parts = [data.get("summary", "")]
    for art in data.get("articles", []):
        if art.get("title"):
            parts.append(art["title"])
        if art.get("subtitle"):
            parts.append(art["subtitle"])
        for block in iter_blocks(art.get("blocks", [])):
            for value in inline_fields(block):
                parts.append(_plain_inline(value))
    return " ".join(p for p in parts if p)


def _plain_inline(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return "".join(run if isinstance(run, str) else run.get("text", "") for run in value)
