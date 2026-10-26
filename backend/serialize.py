"""Converts pandas-based analysis results into JSON-serializable dicts."""
from __future__ import annotations

import math

import pandas as pd

from app.analysis import DataQualityReport, DatasetOverview


def _clean_float(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def df_to_records(df: pd.DataFrame, max_rows: int | None = None) -> list[dict]:
    frame = df.head(max_rows) if max_rows else df
    records = frame.to_dict(orient="records")
    return [{k: _clean_float(v) for k, v in row.items()} for row in records]


def overview_to_dict(overview: DatasetOverview) -> dict:
    return {
        "n_rows": overview.n_rows,
        "n_cols": overview.n_cols,
        "memory_mb": overview.memory_mb,
        "dtypes": overview.dtypes,
        "numeric_cols": overview.numeric_cols,
        "categorical_cols": overview.categorical_cols,
        "datetime_cols": overview.datetime_cols,
    }


def quality_to_dict(quality: DataQualityReport) -> dict:
    missing = quality.missing_by_col.reset_index().rename(columns={"index": "column"})
    return {
        "missing_by_col": df_to_records(missing),
        "duplicate_rows": quality.duplicate_rows,
        "duplicate_pct": quality.duplicate_pct,
        "outliers_by_col": quality.outliers_by_col,
        "constant_cols": quality.constant_cols,
        "high_cardinality_cols": quality.high_cardinality_cols,
    }


def numeric_summary_to_dict(summary: pd.DataFrame) -> list[dict]:
    if summary.empty:
        return []
    out = summary.reset_index().rename(columns={"index": "column"})
    return df_to_records(out)


def categorical_summary_to_dict(summaries: dict[str, pd.DataFrame]) -> dict[str, list[dict]]:
    return {col: df_to_records(counts) for col, counts in summaries.items()}


def correlations_to_dict(corr: pd.DataFrame) -> dict:
    if corr.empty:
        return {"columns": [], "matrix": []}
    return {"columns": corr.columns.tolist(), "matrix": corr.values.tolist()}
