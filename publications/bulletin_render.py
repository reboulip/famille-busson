"""Build the template context for one bulletin's articles: deterministic layout
rules (docked pictures, carousels) applied at render time, ported from
design/bulletins/prototype/render.py's bulletin_context()/prepare_blocks().

Kept separate from the templates so the exact same logic renders a staged
BulletinImport preview and a published Bulletin detail page -- only the
image-id -> URL mapping differs between the two.
"""

from __future__ import annotations

import copy
from typing import Any

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
    """Package blocks -> render blocks. Deterministic layout rules, so every issue looks the same:

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


def build_bulletin_context(data: dict, image_urls: dict[str, str]) -> dict:
    """Template context for one bulletin. `image_urls` maps image id -> URL
    (a BulletinImage.file.url or a BulletinImportImage.file.url, depending on
    whether this is a published bulletin or a staged import preview)."""
    data = copy.deepcopy(data)
    for img in data["images"]:
        img["file"] = image_urls.get(img["id"], "")
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
