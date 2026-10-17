"""Render bulletin packages to a static, self-contained preview of famille-busson.

Uses Django's own template engine (standalone, no project settings) and the site's real
CSS, so the templates under ../templates/publications/ can move into the app almost
as-is. The output opens straight from disk (file://, no server, no network): every page
sits at the root and only references files *below* it, which browsers require for
file:// pages (Firefox refuses fonts from a parent folder).

    <out>/index.html                 bulletin list
    <out>/<id>.html                  one page per bulletin
    <out>/<id>/bulletin.json         the importable package (JSON + images/), as-is
    <out>/<id>/images/...
    <out>/schema/bulletin.schema.json
    <out>/static/...                 site CSS/JS/fonts + bulletin.css + Caveat

Usage (from the repo root), with one or more folders of packages:
    uv run --no-sync python design/bulletins/prototype/render.py <out-dir> \
        .claude/tmp/bulletins/packages design/bulletins/prototype/fixtures
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Any

PROTOTYPE = Path(__file__).resolve().parent  # design/bulletins/prototype: code, templates, CSS, fonts
SPEC_DIR = PROTOTYPE.parent  # design/bulletins: SPEC.md + bulletin.schema.json
REPO = SPEC_DIR.parent.parent
# Real family data (drafts, packages, exports) never goes into git: it lives in the ignored scratch area.
DATA = REPO / ".claude" / "tmp" / "bulletins"
sys.path[:0] = [str(REPO), str(PROTOTYPE)]

import django  # noqa: E402
from django.conf import settings  # noqa: E402

settings.configure(
    DEBUG=False,
    USE_I18N=False,
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [str(PROTOTYPE / "templates")],
            "OPTIONS": {"libraries": {"bulletin": "bulletin_tags"}, "string_if_invalid": ""},
        }
    ],
)
django.setup()

from django.template.loader import render_to_string  # noqa: E402

SITE_STATIC = REPO / "annuaire" / "static"
SCHEMA = SPEC_DIR / "bulletin.schema.json"
INK_KINDS = ("handwriting", "signature", "masthead")
# Pictures, as opposed to ink crops: the blocks that dock right or group into carousels.
PICTURE_KINDS = ("photo", "illustration", "document")
# Blocks a docked picture can sit beside: their text, or their own box, flows around it.
FLOWING_TYPES = {"paragraph", "heading", "list", "quote", "news_item", "event", "address", "aside"}


def prepare_table(block: dict) -> None:
    """Column roles: the key column, and the column right after it that names the row."""
    cols = block["columns"]
    render_cols = []
    for i, col in enumerate(cols):
        if col.get("key"):
            cls = "is-key"
        elif i > 0 and cols[i - 1].get("key"):
            cls = "is-label"
        else:
            cls = ""
        render_cols.append({"label": col["label"], "cls": cls})
    block["render_cols"] = render_cols
    block["render_groups"] = [
        {
            "label": group.get("label"),
            "rows": [[{"value": cell, "col": render_cols[i]} for i, cell in enumerate(row)] for row in group["rows"]],
        }
        for group in block["row_groups"]
    ]


def is_picture(block: dict, images: dict[str, dict]) -> bool:
    if block["type"] == "gallery":
        return True
    return block["type"] == "figure" and images[block["image"]]["kind"] in PICTURE_KINDS


def carousel_from(run: list[dict], carousel_id: str) -> dict:
    """One carousel out of consecutive picture blocks; every slide keeps its own caption."""
    slides: list[dict] = []
    for block in run:
        if block["type"] == "gallery":
            slides.extend(block["items"])
        else:
            slides.append({k: block[k] for k in ("image", "caption", "caption_editorial") if k in block})
    carousel: dict[str, Any] = {"type": "carousel", "id": carousel_id, "slides": slides}
    if len(run) == 1:  # a lone gallery keeps its group caption
        carousel.update({k: run[0][k] for k in ("caption", "caption_editorial") if k in run[0]})
    return carousel


def prepare_blocks(blocks: list[dict], images: dict[str, dict], id_prefix: str) -> list[dict]:
    """Package blocks → render blocks. Deterministic layout rules, so every issue looks the same:

    - consecutive pictures (picture figures, galleries) with no text between them become one
      carousel; a gallery on its own is a carousel too;
    - a single picture docks right when text follows it (the text wraps around it), and is
      centred otherwise, since a float with nothing beside it would leave a hole;
    - ink crops (handwriting, signatures) stay small, in the flow.
    """
    out: list[dict] = []
    run: list[dict] = []
    carousels = 0

    def flush() -> None:
        nonlocal carousels
        if not run:
            return
        slide_count = sum(len(b["items"]) if b["type"] == "gallery" else 1 for b in run)
        if slide_count >= 2:
            carousels += 1
            out.append(carousel_from(run, f"{id_prefix}-carousel-{carousels}"))
        else:
            out.append(run[0])
        run.clear()

    for block in blocks:
        if is_picture(block, images):
            run.append(block)
            continue
        flush()
        if block["type"] == "table":
            prepare_table(block)
        elif block["type"] in ("news_item", "aside"):
            block["blocks"] = prepare_blocks(block["blocks"], images, f"{id_prefix}-{len(out)}")
        out.append(block)
    flush()

    for i, block in enumerate(out):
        if block["type"] != "figure":
            continue
        if images[block["image"]]["kind"] not in PICTURE_KINDS:
            block["layout"] = "ink"
            continue
        block["layout"] = "center"
        for following in out[i + 1 :]:
            if following["type"] in FLOWING_TYPES:
                block["layout"] = "dock"
                break
            if following["type"] in ("table", "carousel", "separator", "signature", "figure"):
                break
    return out


def bulletin_context(data: dict, media_prefix: str) -> dict:
    """Template context for one bulletin; image paths are rewritten relative to the page."""
    data = copy.deepcopy(data)
    for img in data["images"]:
        img["file"] = media_prefix + img["file"]
    images = {img["id"]: img for img in data["images"]}
    sections: list[dict] = []
    toc = []
    for article in data["articles"]:
        rubric = article.get("rubric")
        article["level"] = 3 if rubric else 2
        article["htag"] = f"h{article['level']}"
        article["blocks"] = prepare_blocks(article["blocks"], images, article["id"])
        if rubric and sections and sections[-1]["rubric"] == rubric:
            sections[-1]["articles"].append(article)
        else:
            sections.append({"rubric": rubric, "articles": [article]})
        toc.append({"id": article["id"], "rubric": rubric, "title": article.get("title"), "pages": article["pages"]})
    return {
        "bulletin": data,
        "images": images,
        "ink_kinds": INK_KINDS,
        "masthead": images.get(data.get("masthead_image")),
        "sections": sections,
        "toc": toc,
        "pages": [{"number": p["number"], "img": images[p["image"]]} for p in data["source"]["pages"]],
        "marginalia": [dict(m, img=images[m["image"]]) for m in data.get("marginalia", [])],
        "page_title": f"{data['title']} — {data['date']['text']}",
        "schema_version": data["schema_version"],
    }


def copy_static(out: Path) -> None:
    static = out / "static"
    (static / "css").mkdir(parents=True, exist_ok=True)
    (static / "js").mkdir(parents=True, exist_ok=True)
    for name in ("bootstrap.css", "tokens.css", "components.css", "main.css"):
        shutil.copy2(SITE_STATIC / "css" / name, static / "css" / name)
    shutil.copy2(PROTOTYPE / "bulletin.css", static / "css" / "bulletin.css")
    shutil.copy2(SITE_STATIC / "js" / "bootstrap.bundle.min.js", static / "js" / "bootstrap.bundle.min.js")
    shutil.copy2(PROTOTYPE / "bulletin.js", static / "js" / "bulletin.js")
    shutil.copytree(SITE_STATIC / "fonts", static / "fonts", dirs_exist_ok=True)
    shutil.copytree(PROTOTYPE / "fonts", static / "fonts", dirs_exist_ok=True)  # Caveat + its OFL licence


def copy_package(package: Path, target: Path) -> None:
    """Ship the package itself next to the page, so the folder shows exactly what gets imported."""
    shutil.copytree(package / "images", target / "images", dirs_exist_ok=True)
    data = json.loads((package / "bulletin.json").read_text(encoding="utf-8"))
    data["$schema"] = "../schema/bulletin.schema.json"
    (target / "bulletin.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render(package_roots: list[Path], out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    copy_static(out)
    (out / "schema").mkdir(exist_ok=True)
    shutil.copy2(SCHEMA, out / "schema" / SCHEMA.name)

    written = []
    listing: list[dict[str, Any]] = []
    packages = sorted(p for root in package_roots for p in root.iterdir() if (p / "bulletin.json").is_file())
    for package in packages:
        data = json.loads((package / "bulletin.json").read_text(encoding="utf-8"))
        doc_id = data["id"]
        copy_package(package, out / doc_id)
        context = bulletin_context(data, media_prefix=f"{doc_id}/")
        context.update(static="static/", home="index.html", content_template="publications/bulletin_detail.html")
        page = out / f"{doc_id}.html"
        page.write_text(render_to_string("preview_shell.html", context), encoding="utf-8")
        written.append(page)

        cover = next(
            img
            for img in data["images"]
            if img["id"] == (data.get("cover_image") or data["source"]["pages"][0]["image"])
        )
        listing.append(
            {
                "data": data,
                "href": f"{doc_id}.html",
                "cover": f"{doc_id}/{cover['file']}",
                "cover_w": cover["width"],
                "cover_h": cover["height"],
            }
        )

    listing.sort(key=lambda e: (e["data"]["date"]["value"], e["data"]["issue"].get("number") or 0))
    html = render_to_string(
        "preview_shell.html",
        {
            "bulletins": listing,
            "static": "static/",
            "home": "index.html",
            "content_template": "publications/bulletin_list.html",
            "page_title": "Bulletins familiaux",
            "schema_version": listing[0]["data"]["schema_version"] if listing else "",
        },
    )
    (out / "index.html").write_text(html, encoding="utf-8")
    written.append(out / "index.html")
    return written


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    for path in render([Path(arg) for arg in sys.argv[2:]], Path(sys.argv[1])):
        print("wrote", path)
