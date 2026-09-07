from annuaire.search.text import MAX_SEARCH_TEXT_LENGTH, normalize, terms

# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------


def test_normalize_none_and_empty():
    assert normalize(None) == ""
    assert normalize("") == ""


def test_normalize_strips_accents():
    assert normalize("Büsson") == "busson"
    assert normalize("Été") == "ete"


def test_normalize_casefolds():
    assert normalize("BUSSON") == "busson"


def test_normalize_collapses_whitespace():
    assert normalize("  Famille   Busson  ") == "famille busson"


def test_normalize_truncates_to_max_length():
    long_text = "a" * (MAX_SEARCH_TEXT_LENGTH + 500)
    assert len(normalize(long_text)) == MAX_SEARCH_TEXT_LENGTH


# ---------------------------------------------------------------------------
# terms
# ---------------------------------------------------------------------------


def test_terms_none_and_empty():
    assert terms(None) == []
    assert terms("") == []


def test_terms_splits_on_whitespace():
    assert terms("famille busson") == ["famille", "busson"]


def test_terms_folds_accents_before_splitting():
    assert terms("Büsson") == ["busson"]


def test_terms_drops_punctuation():
    assert terms("a & b | (c'") == ["a", "b", "c"]


def test_terms_only_punctuation_yields_empty_list():
    assert terms("!!!") == []
