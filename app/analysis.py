"""Core, UI-independent analysis functions for AutoAnalyze.

Kept separate from the web layer so they can be unit tested without
spinning up the API or frontend.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

MAX_UPLOAD_MB = 200
MAX_ROWS_FOR_FULL_ANALYSIS = 500_000


class InvalidCSVError(ValueError):
    """Raised when an uploaded file cannot be parsed as a usable CSV."""


def load_csv(file_like: Any) -> pd.DataFrame:
    """Load a CSV from a file-like object or path, with friendly errors."""
    try:
        df = pd.read_csv(file_like)
    except pd.errors.EmptyDataError as exc:
        raise InvalidCSVError("The file is empty.") from exc
    except pd.errors.ParserError as exc:
        raise InvalidCSVError(f"Could not parse this as a CSV: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise InvalidCSVError(
            "Could not read the file's text encoding. Try saving it as UTF-8 CSV."
        ) from exc

    if df.shape[1] == 0:
        raise InvalidCSVError("No columns found in the file.")
    if df.shape[0] == 0:
        raise InvalidCSVError("The file has headers but no data rows.")
    return df


@dataclass
class DatasetOverview:
    n_rows: int
    n_cols: int
    memory_mb: float
    dtypes: dict[str, str]
    numeric_cols: list[str]
    categorical_cols: list[str]
    datetime_cols: list[str]


def get_overview(df: pd.DataFrame) -> DatasetOverview:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
    categorical_cols = [
        c for c in df.columns if c not in numeric_cols and c not in datetime_cols
    ]
    return DatasetOverview(
        n_rows=len(df),
        n_cols=df.shape[1],
        memory_mb=round(df.memory_usage(deep=True).sum() / (1024 * 1024), 3),
        dtypes={c: str(t) for c, t in df.dtypes.items()},
        numeric_cols=numeric_cols,
        categorical_cols=categorical_cols,
        datetime_cols=datetime_cols,
    )


@dataclass
class DataQualityReport:
    missing_by_col: pd.DataFrame
    duplicate_rows: int
    duplicate_pct: float
    outliers_by_col: dict[str, int]
    constant_cols: list[str]
    high_cardinality_cols: list[str]


def get_data_quality(df: pd.DataFrame) -> DataQualityReport:
    n_rows = len(df)

    missing_count = df.isna().sum()
    missing_pct = (missing_count / n_rows * 100).round(2)
    missing_by_col = pd.DataFrame(
        {"missing_count": missing_count, "missing_pct": missing_pct}
    ).sort_values("missing_count", ascending=False)

    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = round(duplicate_rows / n_rows * 100, 2) if n_rows else 0.0

    outliers_by_col: dict[str, int] = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 4:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers_by_col[col] = int(((series < lower) | (series > upper)).sum())

    constant_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    high_cardinality_cols = [
        c
        for c in df.select_dtypes(exclude=[np.number]).columns
        if n_rows > 0 and df[c].nunique(dropna=True) / n_rows > 0.9
    ]

    return DataQualityReport(
        missing_by_col=missing_by_col,
        duplicate_rows=duplicate_rows,
        duplicate_pct=duplicate_pct,
        outliers_by_col=outliers_by_col,
        constant_cols=constant_cols,
        high_cardinality_cols=high_cardinality_cols,
    )


def get_numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        return pd.DataFrame()
    summary = numeric_df.describe().T
    summary["skew"] = numeric_df.skew()
    summary["missing"] = numeric_df.isna().sum()
    return summary.round(3)


def get_categorical_summary(df: pd.DataFrame, max_categories: int = 10) -> dict[str, pd.DataFrame]:
    cat_cols = [
        c
        for c in df.select_dtypes(exclude=[np.number, "datetime64"]).columns
    ]
    result: dict[str, pd.DataFrame] = {}
    for col in cat_cols:
        counts = df[col].value_counts(dropna=False).head(max_categories)
        result[col] = counts.rename_axis(col).reset_index(name="count")
    return result


def get_correlations(df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        return pd.DataFrame()
    return numeric_df.corr(method=method).round(3)


def get_top_correlated_pairs(corr: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if corr.empty:
        return pd.DataFrame(columns=["col_a", "col_b", "correlation"])
    pairs = []
    cols = corr.columns.tolist()
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            pairs.append((a, b, corr.loc[a, b]))
    pairs_df = pd.DataFrame(pairs, columns=["col_a", "col_b", "correlation"])
    pairs_df["abs_corr"] = pairs_df["correlation"].abs()
    return (
        pairs_df.sort_values("abs_corr", ascending=False)
        .drop(columns="abs_corr")
        .head(top_n)
        .reset_index(drop=True)
    )


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    is_numeric: bool
    missing_count: int
    missing_pct: float
    unique_count: int
    stats: dict[str, Any] = field(default_factory=dict)
    top_values: pd.DataFrame | None = None


def profile_column(df: pd.DataFrame, column: str) -> ColumnProfile:
    series = df[column]
    is_numeric = pd.api.types.is_numeric_dtype(series)
    missing_count = int(series.isna().sum())
    n_rows = len(series)
    stats: dict[str, Any] = {}
    top_values = None

    if is_numeric:
        clean = series.dropna()
        if len(clean):
            stats = {
                "mean": round(float(clean.mean()), 4),
                "median": round(float(clean.median()), 4),
                "std": round(float(clean.std()), 4) if len(clean) > 1 else 0.0,
                "min": round(float(clean.min()), 4),
                "max": round(float(clean.max()), 4),
                "skew": round(float(clean.skew()), 4) if len(clean) > 2 else 0.0,
            }
    else:
        top_values = (
            series.value_counts(dropna=False).head(15).rename_axis(column).reset_index(name="count")
        )

    return ColumnProfile(
        name=column,
        dtype=str(series.dtype),
        is_numeric=is_numeric,
        missing_count=missing_count,
        missing_pct=round(missing_count / n_rows * 100, 2) if n_rows else 0.0,
        unique_count=int(series.nunique(dropna=True)),
        stats=stats,
        top_values=top_values,
    )


def get_histogram(df: pd.DataFrame, column: str, bins: int = 20) -> dict[str, list]:
    """Pre-bin a numeric column server-side for lightweight chart payloads."""
    series = df[column].dropna()
    if series.empty:
        return {"counts": [], "bin_edges": []}
    counts, edges = np.histogram(series, bins=bins)
    return {"counts": counts.tolist(), "bin_edges": [round(float(e), 4) for e in edges]}


def clean_dataset(
    df: pd.DataFrame,
    drop_duplicates: bool = False,
    drop_constant_cols: bool = False,
) -> pd.DataFrame:
    """Return a cleaned copy of the dataframe per the requested options."""
    cleaned = df.copy()
    if drop_duplicates:
        cleaned = cleaned.drop_duplicates()
    if drop_constant_cols:
        constant_cols = [c for c in cleaned.columns if cleaned[c].nunique(dropna=False) <= 1]
        cleaned = cleaned.drop(columns=constant_cols)
    return cleaned
