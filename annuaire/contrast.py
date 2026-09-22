"""WCAG 2.1 contrast-ratio helpers, used both by FormSiteConfig's brand-colour
validation and by the contrast-sweep regression test (annuaire/tests/test_contrast.py).
No external dependency -- the formula is small and stays source-text testable like
everything else here (see CLAUDE.md's coding standards)."""

from __future__ import annotations

# WCAG 2.1 minimum ratios (Success Criteria 1.4.3 and 1.4.11).
AA_TEXT = 4.5
AA_NON_TEXT = 3.0


def _linearise(channel: float) -> float:
    if channel <= 0.03928:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance for a `#RRGGBB` hex colour, in [0, 1]."""
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))
    r, g, b = _linearise(r), _linearise(g), _linearise(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    """WCAG 2.1 contrast ratio between two `#RRGGBB` colours, in [1, 21]."""
    l1 = relative_luminance(hex_a)
    l2 = relative_luminance(hex_b)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
