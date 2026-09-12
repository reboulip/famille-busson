"""Named-theme registry for the configurable brand colours (Phase 15.3).

`SiteConfig.theme` names an entry here; `brand_css_overrides()` emits only the CSS
custom-property declarations that actually differ from that theme's own defaults,
so an unconfigured SiteConfig renders byte-identically to the shipped palette.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Default hex values for the two overridable roles, per palette, plus the
    two surfaces those roles are validated against.

    `--fb-ember` (link text, primary button fill) is the "primary" role;
    `--fb-alpenglow` (rules, focus ring, hover -- non-text) is "accent".
    `--fb-card`/`--fb-parchment` (raised surface / page ground) are never
    overridable -- they're here only so FormSiteConfig can check a submitted
    primary/accent colour clears its contrast threshold against both. See
    annuaire/static/css/tokens.css for the full token set.
    """

    primary_light: str
    primary_dark: str
    accent_light: str
    accent_dark: str
    card_light: str
    card_dark: str
    parchment_light: str
    parchment_dark: str


THEMES: dict[str, Theme] = {
    "alpenglow": Theme(
        primary_light="#9C4A22",
        primary_dark="#E2914E",
        accent_light="#D9793F",
        # Nightfall inverts roles: the bright ember reads well enough (6.28:1 on
        # --fb-card) to take over both the primary and accent role, and the deep
        # ember drops out entirely -- see tokens.css's dark-mode block.
        accent_dark="#E2914E",
        card_light="#FFFAF0",
        card_dark="#2C2119",
        parchment_light="#F6EEE0",
        parchment_dark="#221810",
    ),
}

DEFAULT_THEME = "alpenglow"


def brand_css_overrides(config) -> str:
    """Inline CSS overriding `--fb-ember`/`--fb-alpenglow` with the configured
    brand colours, restricted to whichever ones actually differ from the active
    theme's defaults. Emits an empty string when nothing is overridden."""
    theme = THEMES.get(config.theme, THEMES[DEFAULT_THEME])

    light_declarations = []
    if config.brand_primary_light and config.brand_primary_light != theme.primary_light:
        light_declarations.append(f"--fb-ember:{config.brand_primary_light};")
    if config.brand_accent_light and config.brand_accent_light != theme.accent_light:
        light_declarations.append(f"--fb-alpenglow:{config.brand_accent_light};")

    dark_declarations = []
    if config.brand_primary_dark and config.brand_primary_dark != theme.primary_dark:
        dark_declarations.append(f"--fb-ember:{config.brand_primary_dark};")
    if config.brand_accent_dark and config.brand_accent_dark != theme.accent_dark:
        dark_declarations.append(f"--fb-alpenglow:{config.brand_accent_dark};")

    css = ""
    if light_declarations:
        css += ":root{" + "".join(light_declarations) + "}"
    if dark_declarations:
        block = "".join(dark_declarations)
        # Same two selectors tokens.css itself uses for the dark palette (OS
        # preference, and the explicit data-bs-theme="dark" toggle) -- matching
        # specificity so this override wins purely on being later in the
        # cascade (this <style> is emitted after tokens.css's <link>).
        css += f'@media (prefers-color-scheme: dark){{:root:not([data-bs-theme="light"]){{{block}}}}}'
        css += f'[data-bs-theme="dark"]{{{block}}}'
    return css
