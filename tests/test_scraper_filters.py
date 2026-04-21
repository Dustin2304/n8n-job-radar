import pandas as pd

from api.scraper import (
    EXCLUDE_TITLE_KEYWORDS,
    _clean_str,
    _compile_exclude_pattern,
    infer_level,
)


def test_clean_str_handles_nan_variants():
    assert _clean_str("nan") == ""
    assert _clean_str("None") == ""
    assert _clean_str(None) == ""
    assert _clean_str(float("nan")) == ""
    assert _clean_str(" Hello   World ") == "Hello World"


def test_exclude_pattern_word_boundaries():
    pattern = _compile_exclude_pattern(EXCLUDE_TITLE_KEYWORDS)

    assert pattern.search("Senior Engineer")
    assert pattern.search("Sr. Developer")
    assert pattern.search("Praktikum Backend")
    assert not pattern.search("Leadership Platform Engineer")
    assert pattern.search("Experienced Python Developer")


def test_infer_level_from_title():
    assert infer_level(None, "Junior Python Developer") == "Entry"
    assert infer_level(None, "Senior Data Engineer") == "Senior"
    assert infer_level("associate", "Principal Engineer") == "Entry"


def test_clean_str_strips_pandas_nan():
    assert _clean_str(pd.NA) == ""
