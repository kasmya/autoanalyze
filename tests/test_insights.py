import pandas as pd

from app.analysis import get_correlations, get_data_quality, get_numeric_summary, get_overview
from app.insights import build_summary


def test_build_summary_no_numbers_missing():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    overview = get_overview(df)
    quality = get_data_quality(df)
    numeric_summary = get_numeric_summary(df)
    corr = get_correlations(df)
    lines = build_summary(df, overview, quality, numeric_summary, corr)
    assert any("No missing values" in line for line in lines)


def test_build_summary_reports_missing_pct():
    df = pd.DataFrame({"a": [1, None, 3, 4], "b": [1, 2, 3, 4]})
    overview = get_overview(df)
    quality = get_data_quality(df)
    numeric_summary = get_numeric_summary(df)
    corr = get_correlations(df)
    lines = build_summary(df, overview, quality, numeric_summary, corr)
    assert any("missing values in the a column" in line for line in lines)
