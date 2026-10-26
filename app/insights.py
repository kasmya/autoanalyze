"""Plain-English narrative built only from computed statistics.

No numbers are invented here: every sentence is templated from values
already produced by app.analysis. This keeps the "AI summary" honest and
cheap (no LLM call required for the core app to work).
"""
from __future__ import annotations

import pandas as pd

from app.analysis import (
    DataQualityReport,
    DatasetOverview,
    get_top_correlated_pairs,
)


def build_summary(
    df: pd.DataFrame,
    overview: DatasetOverview,
    quality: DataQualityReport,
    numeric_summary: pd.DataFrame,
    corr: pd.DataFrame,
) -> list[str]:
    lines: list[str] = []

    lines.append(
        f"The dataset has {overview.n_rows:,} rows and {overview.n_cols} columns "
        f"({len(overview.numeric_cols)} numeric, {len(overview.categorical_cols)} categorical)."
    )

    missing_cols = quality.missing_by_col[quality.missing_by_col["missing_count"] > 0]
    if not missing_cols.empty:
        worst = missing_cols.iloc[0]
        lines.append(
            f"The dataset contains {worst['missing_pct']}% missing values in the "
            f"{missing_cols.index[0]} column"
            + (
                f", and {len(missing_cols) - 1} other column(s) also have missing data."
                if len(missing_cols) > 1
                else "."
            )
        )
    else:
        lines.append("No missing values were found in any column.")

    if quality.duplicate_rows > 0:
        lines.append(
            f"{quality.duplicate_rows:,} duplicate rows were detected "
            f"({quality.duplicate_pct}% of all rows)."
        )

    if not numeric_summary.empty:
        skewed = numeric_summary[numeric_summary["skew"].abs() > 1]
        for col in skewed.index[:3]:
            direction = "right-skewed" if numeric_summary.loc[col, "skew"] > 0 else "left-skewed"
            lines.append(
                f"{col} is {direction}, meaning a small number of unusually "
                f"{'high' if direction == 'right-skewed' else 'low'} values pull the average up."
            )

    outlier_cols = {k: v for k, v in quality.outliers_by_col.items() if v > 0}
    if outlier_cols:
        top_outlier_col = max(outlier_cols, key=outlier_cols.get)
        lines.append(
            f"{top_outlier_col} has {outlier_cols[top_outlier_col]} potential outlier value(s) "
            "based on the IQR rule."
        )

    if not corr.empty:
        top_pairs = get_top_correlated_pairs(corr, top_n=1)
        if not top_pairs.empty and abs(top_pairs.iloc[0]["correlation"]) > 0.5:
            row = top_pairs.iloc[0]
            strength = "strong" if abs(row["correlation"]) > 0.75 else "moderate"
            direction = "positive" if row["correlation"] > 0 else "negative"
            lines.append(
                f"There is a {strength} {direction} correlation ({row['correlation']}) "
                f"between {row['col_a']} and {row['col_b']}. This is a statistical "
                "association, not evidence that one causes the other."
            )

    if quality.constant_cols:
        lines.append(
            f"{len(quality.constant_cols)} column(s) have only a single distinct value "
            "and carry no information: " + ", ".join(quality.constant_cols[:5]) + "."
        )

    return lines
