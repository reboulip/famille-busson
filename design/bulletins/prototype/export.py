"""Build the copy-anywhere preview folder (+ zip) for reviewing the prototype on another machine.

Usage (from the repo root):
    uv run --no-sync python design/bulletins/prototype/export.py
Output (git-ignored, it contains real family data):
    .claude/tmp/bulletins/export/famille-busson-bulletins-preview/      (folder)
    .claude/tmp/bulletins/export/famille-busson-bulletins-preview.zip   (same, zipped)
"""

from __future__ import annotations

import shutil
from pathlib import Path

from render import DATA, PROTOTYPE, SPEC_DIR, render  # sibling script: run from this folder

NAME = "famille-busson-bulletins-preview"

README = """\
Famille Busson: bulletin import prototype
==========================================

Open index.html in a web browser (double-click it). Everything is in this folder:
it works offline, with no server and no internet connection.

  index.html          list of the bulletins
  bc-017.html         Busson's Connection n°17 (April 1995), rendered from its JSON package
                        - dark theme: "Nightfall" link at the bottom of the left menu
                          (or add ?theme=dark to the address)
                        - mobile layout: make the window narrow, or use the browser's
                          device toolbar (F12, then Ctrl+Shift+M in Chrome/Firefox)
  demo-001.html       a made-up issue (generated pictures) that exercises what BC n°17
                      has no example of: picture carousels, captions on every picture,
                      a picture with a printed caption, an inset box
  bc-017/, demo-001/  the importable packages, exactly what the site would receive:
                      bulletin.json + images/
  schema/             bulletin.schema.json (JSON Schema, draft 2020-12, v0.2)
  SPEC.md             the draft spec (decisions, rendering rules, open questions);
                      its tracked copy is design/bulletins/SPEC.md in the repo
  static/             the site's real CSS/JS/fonts + the prototype's bulletin.css
                      (Caveat font: SIL Open Font License, see static/fonts/)

Private: contains personal family data (names, a 1995 postal address and phone number).
Generated from "BC 017 Al 04-1995.pdf".
"""


def export() -> Path:
    base = DATA / "export"
    folder = base / NAME
    if folder.exists():
        shutil.rmtree(folder)  # regenerated from scratch every time
    render([DATA / "packages", PROTOTYPE / "fixtures"], folder)
    shutil.copy2(SPEC_DIR / "SPEC.md", folder / "SPEC.md")
    (folder / "README.txt").write_text(README, encoding="utf-8")
    archive = shutil.make_archive(str(base / NAME), "zip", root_dir=base, base_dir=NAME)
    return Path(archive)


if __name__ == "__main__":
    archive = export()
    folder = archive.with_suffix("")
    files = [p for p in folder.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(f"folder: {folder} ({len(files)} files, {size / 1024 / 1024:.1f} MiB)")
    print(f"zip:    {archive} ({archive.stat().st_size / 1024 / 1024:.1f} MiB)")
