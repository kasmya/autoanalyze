"""Builds a self-contained HTML report (no external deps) for download."""
from __future__ import annotations

import html
from datetime import datetime

import pandas as pd

from app.analysis import DataQualityReport, DatasetOverview


def _df_to_html(df: pd.DataFrame, max_rows: int = 50) -> str:
    if df is None or df.empty:
        return "<p><em>None</em></p>"
    return df.head(max_rows).to_html(classes="tbl", border=0)


def build_html_report(
    filename: str,
    overview: DatasetOverview,
    quality: DataQualityReport,
    numeric_summary: pd.DataFrame,
    summary_lines: list[str],
) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary_html = "".join(f"<li>{html.escape(line)}</li>" for line in summary_lines)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AutoAnalyze Report — {html.escape(filename)}</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; margin: 40px; color: #1a1a1a; }}
h1 {{ font-size: 22px; }}
h2 {{ font-size: 17px; margin-top: 32px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
.meta {{ color: #666; font-size: 13px; margin-bottom: 24px; }}
.tbl {{ border-collapse: collapse; font-size: 13px; width: 100%; margin-top: 8px; }}
.tbl th, .tbl td {{ padding: 6px 10px; border-bottom: 1px solid #eee; text-align: left; }}
.tbl th {{ background: #fafafa; }}
ul {{ line-height: 1.6; }}
.badge {{ display: inline-block; background: #eef2ff; color: #3730a3; padding: 2px 8px;
  border-radius: 10px; font-size: 12px; margin-right: 6px; }}
</style>
</head>
<body>
<h1>AutoAnalyze — Automated Analysis Report</h1>
<div class="meta">File: {html.escape(filename)} &middot; Generated: {generated}</div>

<h2>Overview</h2>
<span class="badge">{overview.n_rows:,} rows</span>
<span class="badge">{overview.n_cols} columns</span>
<span class="badge">{overview.memory_mb} MB</span>
<span class="badge">{len(overview.numeric_cols)} numeric</span>
<span class="badge">{len(overview.categorical_cols)} categorical</span>

<h2>Plain-English Summary</h2>
<ul>{summary_html}</ul>

<h2>Data Quality</h2>
<p>Duplicate rows: {quality.duplicate_rows:,} ({quality.duplicate_pct}%)</p>
{_df_to_html(quality.missing_by_col)}

<h2>Statistical Summary</h2>
{_df_to_html(numeric_summary)}

</body>
</html>
"""
