import pytest

from annuaire.contrast import AA_NON_TEXT, AA_TEXT, contrast_ratio, relative_luminance


def test_relative_luminance_white_is_one():
    assert relative_luminance("#FFFFFF") == pytest.approx(1.0, abs=1e-6)


def test_relative_luminance_black_is_zero():
    assert relative_luminance("#000000") == pytest.approx(0.0, abs=1e-6)


def test_contrast_ratio_black_on_white_is_maximal():
    assert contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0, abs=1e-2)


def test_contrast_ratio_is_symmetric():
    assert contrast_ratio("#9C4A22", "#FFFAF0") == contrast_ratio("#FFFAF0", "#9C4A22")


def test_contrast_ratio_identical_colours_is_one():
    assert contrast_ratio("#9C4A22", "#9C4A22") == pytest.approx(1.0, abs=1e-6)


# Baseline regression guard: recomputes design/web/SPEC.md §3.2's documented pairs.
# If these drift, either tokens.css changed or the formula broke -- both worth knowing.


def test_ember_on_card_light_clears_aa_text():
    assert contrast_ratio("#9C4A22", "#FFFAF0") == pytest.approx(5.90, abs=0.01)
    assert contrast_ratio("#9C4A22", "#FFFAF0") >= AA_TEXT


def test_ember_on_card_dark_clears_aa_text():
    assert contrast_ratio("#E2914E", "#2C2119") == pytest.approx(6.28, abs=0.01)
    assert contrast_ratio("#E2914E", "#2C2119") >= AA_TEXT


def test_alpenglow_on_card_light_is_non_text_only():
    """Documented in SPEC.md §3.2 as decorative/non-text only -- this is why
    --fb-alpenglow never carries link/button text in the Alpenglow palette."""
    ratio = contrast_ratio("#D9793F", "#FFFAF0")
    assert ratio == pytest.approx(2.99, abs=0.02)
    assert ratio < AA_TEXT


def test_alpenglow_on_card_dark_clears_aa_non_text():
    assert contrast_ratio("#E2914E", "#2C2119") >= AA_NON_TEXT
