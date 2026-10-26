import io

import pandas as pd
import pytest

from app.analysis import (
    InvalidCSVError,
    clean_dataset,
    get_categorical_summary,
    get_correlations,
    get_data_quality,
    get_numeric_summary,
    get_overview,
    get_top_correlated_pairs,
    load_csv,
    profile_column,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "age": [25, 30, 35, 40, None, 200],
            "income": [50000, 60000, 55000, 62000, 58000, 59000],
            "category": ["A", "B", "A", "A", "B", "B"],
            "constant": [1, 1, 1, 1, 1, 1],
        }
    )


def test_load_csv_valid():
    buf = io.StringIO("a,b\n1,2\n3,4\n")
    df = load_csv(buf)
    assert df.shape == (2, 2)


def test_load_csv_empty_raises():
    buf = io.StringIO("")
    with pytest.raises(InvalidCSVError):
        load_csv(buf)


def test_load_csv_headers_only_raises():
    buf = io.StringIO("a,b\n")
    with pytest.raises(InvalidCSVError):
        load_csv(buf)


def test_get_overview(sample_df):
    overview = get_overview(sample_df)
    assert overview.n_rows == 6
    assert overview.n_cols == 4
    assert "age" in overview.numeric_cols
    assert "category" in overview.categorical_cols


def test_get_data_quality_missing(sample_df):
    quality = get_data_quality(sample_df)
    assert quality.missing_by_col.loc["age", "missing_count"] == 1
    assert "constant" in quality.constant_cols


def test_get_data_quality_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2], "b": [1, 1, 2]})
    quality = get_data_quality(df)
    assert quality.duplicate_rows == 1


def test_get_data_quality_outliers(sample_df):
    quality = get_data_quality(sample_df)
    assert quality.outliers_by_col.get("age", 0) >= 1


def test_get_numeric_summary(sample_df):
    summary = get_numeric_summary(sample_df)
    assert "age" in summary.index
    assert "mean" in summary.columns


def test_get_categorical_summary(sample_df):
    cat_summary = get_categorical_summary(sample_df)
    assert "category" in cat_summary
    assert cat_summary["category"]["count"].sum() == 6


def test_get_correlations(sample_df):
    corr = get_correlations(sample_df)
    assert "age" in corr.columns
    assert "income" in corr.columns


def test_get_correlations_single_numeric_col():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    corr = get_correlations(df)
    assert corr.empty


def test_get_top_correlated_pairs(sample_df):
    corr = get_correlations(sample_df)
    pairs = get_top_correlated_pairs(corr, top_n=1)
    assert len(pairs) == 1
    assert {"col_a", "col_b", "correlation"} <= set(pairs.columns)


def test_profile_column_numeric(sample_df):
    profile = profile_column(sample_df, "income")
    assert profile.is_numeric
    assert "mean" in profile.stats


def test_profile_column_categorical(sample_df):
    profile = profile_column(sample_df, "category")
    assert not profile.is_numeric
    assert profile.top_values is not None


def test_clean_dataset_drop_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2]})
    cleaned = clean_dataset(df, drop_duplicates=True)
    assert len(cleaned) == 2


def test_clean_dataset_drop_constant_cols(sample_df):
    cleaned = clean_dataset(sample_df, drop_constant_cols=True)
    assert "constant" not in cleaned.columns
