"""Generate the synthetic demo package: fixtures/demo-001/ (bulletin.json + images/).

A made-up issue with drawn pictures and neutral text, so it can live in git (no family
data) and exercise what BC n°17 has no example of: a picture docked in running text,
printed and editorial captions, a gallery and two consecutive figures (both carousels),
an illegible word shown as an inline crop, an inset box (aside). Deterministic: re-running
produces byte-identical files, so it can serve as a test fixture for the real importer.

Usage (from the repo root):
    uv run --no-sync python design/bulletins/prototype/make_demo.py
"""

from __future__ import annotations

import hashlib
import io
import json
import random
import unicodedata
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "fixtures" / "demo-001"
DOC = "demo-001"


def drawable(text: str) -> str:
    """Pillow's built-in font has no accented glyphs: draw 'e' for 'é', a straight apostrophe."""
    text = text.replace("’", "'")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


# Scene palettes: sky top, sky bottom, far ridge, near ridge, ground/water.
SCENES = {
    "dawn": ("#F3D9B1", "#F6C9A8", "#9FB0AE", "#4B5D3F", "#A9C3C8"),
    "noon": ("#8FB3D9", "#D8E6F0", "#9FB0AE", "#4B5D3F", "#6F9AB8"),
    "sunset": ("#6B5B8C", "#E2914E", "#705C48", "#3A2C1E", "#9C4A22"),
    "snow": ("#C9D3DC", "#F2F4F6", "#DDE3E8", "#FBF6EC", "#E8ECEF"),
    "spring": ("#9CC3E0", "#E4F0F6", "#8FA87A", "#4B5D3F", "#7FA35F"),
    "forest": ("#B7CBB0", "#E7EADF", "#6E8A5E", "#28331F", "#4B5D3F"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def gradient(size: tuple[int, int], top: str, bottom: str) -> Image.Image:
    w, h = size
    im = Image.new("RGB", size)
    t, b = ImageColor.getrgb(top), ImageColor.getrgb(bottom)
    draw = ImageDraw.Draw(im)
    for y in range(h):
        f = y / max(1, h - 1)
        draw.line([(0, y), (w, y)], fill=tuple(round(t[i] + (b[i] - t[i]) * f) for i in range(3)))
    return im


def ridge(w: int, base: int, amplitude: int, rng: random.Random, peaks: int) -> list[tuple[int, int]]:
    points = [(0, base)]
    for i in range(1, peaks * 2):
        x = round(w * i / (peaks * 2))
        y = base - (amplitude if i % 2 else amplitude // 3) - rng.randint(0, amplitude // 3)
        points.append((x, y))
    return [*points, (w, base), (w, base + 10_000), (0, base + 10_000)]


def scene(size: tuple[int, int], palette: str, label: str, seed: int, chalet: bool = False) -> Image.Image:
    rng = random.Random(seed)
    sky_top, sky_bottom, far, near, ground = SCENES[palette]
    w, h = size
    im = gradient(size, sky_top, sky_bottom)
    draw = ImageDraw.Draw(im)
    horizon = round(h * 0.62)
    sun = (round(w * rng.uniform(0.6, 0.8)), round(h * rng.uniform(0.18, 0.3)))
    r = round(min(w, h) * 0.07)
    draw.ellipse([sun[0] - r, sun[1] - r, sun[0] + r, sun[1] + r], fill="#FBF6EC")
    draw.polygon(ridge(w, horizon, round(h * 0.28), rng, 4), fill=far)
    draw.polygon(ridge(w, horizon + round(h * 0.06), round(h * 0.22), rng, 3), fill=near)
    draw.rectangle([0, horizon + round(h * 0.12), w, h], fill=ground)
    for i in range(6):  # a few pines on the near slope
        x = round(w * (0.08 + 0.12 * i + rng.uniform(-0.02, 0.02)))
        top = horizon + round(h * 0.02)
        draw.polygon([(x, top), (x - 22, top + 70), (x + 22, top + 70)], fill="#28331F")
    if chalet:
        cx, cy = round(w * 0.55), horizon + round(h * 0.1)
        draw.rectangle([cx - 90, cy - 70, cx + 90, cy + 40], fill="#705C48")
        draw.polygon([(cx - 120, cy - 60), (cx, cy - 150), (cx + 120, cy - 60)], fill="#3A2C1E")
        draw.rectangle([cx - 20, cy - 10, cx + 20, cy + 40], fill="#D9A441")
    font = ImageFont.load_default(size=max(18, h // 30))
    draw.text(
        (24, h - 24), drawable(label), fill="#FFFAF0", font=font, anchor="ls", stroke_width=2, stroke_fill="#3A2C1E"
    )
    return im


def fake_page(number: int) -> Image.Image:
    rng = random.Random(100 + number)
    im = Image.new("L", (1240, 1754), 250)
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle([110, 110, 700, 190], radius=20, outline=40, width=4)
    font = ImageFont.load_default(size=40)
    draw.text((140, 165), drawable(f"Page de démonstration {number}"), fill=40, font=font, anchor="ls")
    y = 260
    while y < 1600:
        width = rng.randint(700, 1020)
        draw.line([(110, y), (110 + width, y)], fill=150, width=6)
        y += rng.choice([34, 34, 34, 70])
    return im


def scribble(seed: int) -> Image.Image:
    rng = random.Random(seed)
    im = Image.new("L", (260, 70), 255)
    draw = ImageDraw.Draw(im)
    x, y = 12, 40
    points = []
    while x < 248:
        points.append((x, y + rng.randint(-18, 18)))
        x += rng.randint(8, 16)
    draw.line(points, fill=40, width=4, joint="curve")
    return im


def encode(im: Image.Image, fmt: str) -> bytes:
    buf = io.BytesIO()
    if fmt == "jpg":
        im.save(buf, "JPEG", quality=85, optimize=True)
    else:
        im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def main() -> None:
    (OUT / "images").mkdir(parents=True, exist_ok=True)
    images: list[dict] = []

    def add(image_id: str, im: Image.Image, fmt: str, kind: str, alt: str, page: int, **extra) -> None:
        data = encode(im, fmt)
        (OUT / "images" / f"{image_id}.{fmt}").write_bytes(data)
        source: dict = {"page": page, "dpi": 200}
        if kind != "page":
            source["bbox"] = [0.1, 0.12, 0.9, 0.55]
        images.append(
            {
                "id": image_id,
                "file": f"images/{image_id}.{fmt}",
                "kind": kind,
                "media_type": "image/jpeg" if fmt == "jpg" else "image/png",
                "width": im.width,
                "height": im.height,
                "sha256": sha256(data),
                "source": source,
                "alt": alt,
                **extra,
            }
        )

    for n in (1, 2):
        add(f"{DOC}-page-{n:02d}", fake_page(n), "jpg", "page", f"Page {n} du bulletin de démonstration", n)
    photos = [
        ("photo-01", (1200, 800), "dawn", "Le lac au petit matin", 1, False),
        ("photo-02", (900, 1200), "forest", "Le sentier", 2, False),
        ("photo-03", (1200, 800), "noon", "Au bord de l’eau", 3, False),
        ("photo-04", (1200, 900), "sunset", "Le retour", 4, False),
        ("photo-05", (1200, 800), "snow", "Le chalet en hiver", 5, True),
        ("photo-06", (1200, 800), "spring", "Le chalet au printemps", 6, True),
    ]
    for suffix, size, palette, label, seed, chalet in photos:
        page = 1 if suffix == "photo-01" else 2
        add(
            f"{DOC}-{suffix}",
            scene(size, palette, label, seed, chalet),
            "jpg",
            "photo",
            f"Image générée : {label}",
            page,
        )
    add(f"{DOC}-scribble-01", scribble(7), "png", "handwriting", "Mot manuscrit illisible", 1, transcript=None)

    filler = (
        "Ce paragraphe tient lieu d’article : il est assez long pour que le texte coule le long de la photo, "
        "puis reprenne toute la largeur de la colonne une fois la photo dépassée. Les bulletins mêlent souvent "
        "une image et un récit ; la photo se range à droite et le texte l’habille, comme sur le papier."
    )
    bulletin = {
        "$schema": "../../../bulletin.schema.json",
        "schema_version": "0.2",
        "id": DOC,
        "title": "Bulletin de démonstration n°1",
        "series": {"code": "DEMO", "title": "Bulletin de démonstration"},
        "issue": {"number": 1},
        "date": {"value": "2026-09", "text": "septembre 2026"},
        "language": "fr",
        "credits": [{"role": "Rédaction", "names": ["Prototype"]}],
        "summary": (
            "Numéro fictif, aux images générées, qui sert à tester le rendu : photo habillée par le texte, "
            "carrousels de photos légendées, mot illisible et encadré."
        ),
        "cover_image": f"{DOC}-page-01",
        "source": {
            "file_name": f"{DOC}.pdf",
            "sha256": sha256(DOC.encode()),
            "page_count": 2,
            "producer": "make_demo.py",
            "scanned_on": "2026-09-27",
            "pages": [{"number": n, "image": f"{DOC}-page-{n:02d}"} for n in (1, 2)],
        },
        "images": images,
        "articles": [
            {
                "id": "photo-habillee",
                "title": "Une photo habillée par le texte",
                "script": "typed",
                "pages": [1],
                "blocks": [
                    {
                        "type": "paragraph",
                        "text": "Ce numéro n’existe pas : il sert à vérifier la mise en page des photos.",
                    },
                    {
                        "type": "figure",
                        "image": f"{DOC}-photo-01",
                        "caption": "Le lac au petit matin (légende imprimée dans le bulletin).",
                    },
                    {"type": "paragraph", "text": filler},
                    {"type": "paragraph", "text": filler},
                    {
                        "type": "paragraph",
                        "text": [
                            "Un mot que personne n’a su lire reste une image, au fil du texte : ",
                            {"kind": "illegible", "image": f"{DOC}-scribble-01"},
                            ". Le lecteur voit l’écriture d’origine.",
                        ],
                    },
                    {"type": "paragraph", "text": filler},
                ],
            },
            {
                "id": "journee-au-lac",
                "rubric": "Album",
                "title": "La journée au lac",
                "script": "typed",
                "pages": [2],
                "blocks": [
                    {
                        "type": "gallery",
                        "caption": "Une page de photos, sans texte",
                        "items": [
                            {"image": f"{DOC}-photo-02", "caption": "Le départ par le sentier."},
                            {"image": f"{DOC}-photo-03", "caption": "Pique-nique au bord de l’eau."},
                            {"image": f"{DOC}-photo-04", "caption": "Le retour, au coucher du soleil."},
                        ],
                    }
                ],
            },
            {
                "id": "deux-photos",
                "title": "Deux photos à la suite",
                "script": "typed",
                "pages": [2],
                "blocks": [
                    {
                        "type": "paragraph",
                        "text": "Deux photos se suivent sans texte entre elles : le site les réunit en carrousel.",
                    },
                    {
                        "type": "figure",
                        "image": f"{DOC}-photo-05",
                        "caption": "Le chalet sous la neige.",
                        "caption_editorial": True,
                    },
                    {
                        "type": "figure",
                        "image": f"{DOC}-photo-06",
                        "caption": "La même vue au printemps.",
                        "caption_editorial": True,
                    },
                ],
            },
            {
                "id": "encadre",
                "title": "Un encadré",
                "script": "typed",
                "pages": [2],
                "blocks": [
                    {"type": "paragraph", "text": "Un encadré isole une information du reste de l’article."},
                    {
                        "type": "aside",
                        "title": "À retenir",
                        "blocks": [
                            {
                                "type": "paragraph",
                                "text": "Les légendes ajoutées à la transcription sont en italique.",
                            },
                            {
                                "type": "list",
                                "style": "bullet",
                                "items": [
                                    "Une photo seule s’aligne à droite.",
                                    "Plusieurs photos forment un carrousel.",
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
        "processing": {
            "agent": "make_demo.py (données fictives)",
            "date": "2026-09-27",
            "conventions": "faithful-v1",
            "review": {"status": "reviewed"},
            "notes": [{"level": "info", "message": "Numéro fictif : textes et images générés pour tester le rendu."}],
        },
    }
    (OUT / "bulletin.json").write_text(json.dumps(bulletin, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(images)} images)")


if __name__ == "__main__":
    main()
