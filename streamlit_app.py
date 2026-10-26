"""AutoAnalyze Lite — Automated Exploratory Data Analysis.

Run with: streamlit run streamlit_app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.analysis import (
    MAX_UPLOAD_MB,
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
from app.insights import build_summary
from app.report import build_html_report

st.set_page_config(page_title="AutoAnalyze Lite", layout="wide")

st.title("📊 AutoAnalyze Lite")
st.caption("Automated Exploratory Data Analysis — upload a CSV, get instant insights.")

uploaded = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV to get started. Max file size ~{} MB.".format(MAX_UPLOAD_MB))
    st.stop()

size_mb = uploaded.size / (1024 * 1024)
if size_mb > MAX_UPLOAD_MB:
    st.error(f"File is {size_mb:.1f} MB, which exceeds the {MAX_UPLOAD_MB} MB limit.")
    st.stop()

try:
    df = load_csv(uploaded)
except InvalidCSVError as exc:
    st.error(f"Couldn't read this file: {exc}")
    st.stop()

overview = get_overview(df)
quality = get_data_quality(df)
numeric_summary = get_numeric_summary(df)
corr = get_correlations(df)

tab_overview, tab_quality, tab_explore, tab_export = st.tabs(
    ["Overview", "Data Quality", "Explore", "Export"]
)

with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{overview.n_rows:,}")
    c2.metric("Columns", overview.n_cols)
    c3.metric("Memory", f"{overview.memory_mb} MB")
    c4.metric("Numeric cols", len(overview.numeric_cols))

    st.subheader("Preview")
    st.dataframe(df.head(50), use_container_width=True)

    st.subheader("Column types")
    dtype_df = pd.DataFrame(
        {"column": list(overview.dtypes.keys()), "dtype": list(overview.dtypes.values())}
    )
    st.dataframe(dtype_df, use_container_width=True, hide_index=True)

    st.subheader("Statistical summary (numeric columns)")
    if numeric_summary.empty:
        st.write("No numeric columns found.")
    else:
        st.dataframe(numeric_summary, use_container_width=True)

    st.subheader("AI-generated summary")
    summary_lines = build_summary(df, overview, quality, numeric_summary, corr)
    for line in summary_lines:
        st.markdown(f"- {line}")

with tab_quality:
    st.subheader("Missing values")
    missing_nonzero = quality.missing_by_col[quality.missing_by_col["missing_count"] > 0]
    if missing_nonzero.empty:
        st.success("No missing values detected.")
    else:
        st.dataframe(missing_nonzero, use_container_width=True)
        fig = px.bar(
            missing_nonzero.reset_index().rename(columns={"index": "column"}),
            x="column",
            y="missing_pct",
            title="Missing values by column (%)",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Duplicates")
    if quality.duplicate_rows:
        st.warning(f"{quality.duplicate_rows:,} duplicate rows ({quality.duplicate_pct}%).")
    else:
        st.success("No duplicate rows detected.")

    st.subheader("Potential outliers (IQR method)")
    if quality.outliers_by_col:
        outlier_df = pd.DataFrame(
            [{"column": k, "outlier_count": v} for k, v in quality.outliers_by_col.items() if v > 0]
        )
        if outlier_df.empty:
            st.success("No outliers detected in numeric columns.")
        else:
            st.dataframe(outlier_df, use_container_width=True, hide_index=True)
    else:
        st.write("No numeric columns to check for outliers.")

    if quality.constant_cols:
        st.subheader("Constant columns (no information)")
        st.write(quality.constant_cols)

    if quality.high_cardinality_cols:
        st.subheader("High-cardinality columns (likely IDs)")
        st.write(quality.high_cardinality_cols)

    st.subheader("Clean this dataset")
    drop_dupes = st.checkbox("Drop duplicate rows", value=False)
    drop_const = st.checkbox("Drop constant columns", value=False)
    cleaned = clean_dataset(df, drop_duplicates=drop_dupes, drop_constant_cols=drop_const)
    st.download_button(
        "Download cleaned CSV",
        data=cleaned.to_csv(index=False).encode("utf-8"),
        file_name=f"cleaned_{uploaded.name}",
        mime="text/csv",
    )

with tab_explore:
    st.subheader("Column analysis")
    selected_col = st.selectbox("Select a column", df.columns.tolist())
    profile = profile_column(df, selected_col)

    c1, c2, c3 = st.columns(3)
    c1.metric("Missing", f"{profile.missing_count} ({profile.missing_pct}%)")
    c2.metric("Unique values", profile.unique_count)
    c3.metric("Type", profile.dtype)

    if profile.is_numeric:
        if profile.stats:
            st.json(profile.stats)
        fig = px.histogram(df, x=selected_col, title=f"Distribution of {selected_col}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        if profile.top_values is not None:
            st.dataframe(profile.top_values, use_container_width=True, hide_index=True)
            fig = px.bar(
                profile.top_values, x=selected_col, y="count", title=f"Top values in {selected_col}"
            )
            st.plotly_chart(fig, use_container_width=True)

    if not corr.empty:
        st.subheader("Correlation heatmap")
        fig = px.imshow(corr, text_auto=True, title="Correlation matrix", color_continuous_scale="RdBu_r")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Strongest relationships")
        st.dataframe(get_top_correlated_pairs(corr), use_container_width=True, hide_index=True)

    cat_summaries = get_categorical_summary(df)
    if cat_summaries:
        st.subheader("Category breakdowns")
        for col, counts in cat_summaries.items():
            with st.expander(col):
                st.dataframe(counts, use_container_width=True, hide_index=True)

with tab_export:
    st.subheader("Export analysis report")
    summary_lines = build_summary(df, overview, quality, numeric_summary, corr)
    report_html = build_html_report(uploaded.name, overview, quality, numeric_summary, summary_lines)
    st.download_button(
        "Download HTML report",
        data=report_html.encode("utf-8"),
        file_name=f"autoanalyze_report_{uploaded.name.rsplit('.', 1)[0]}.html",
        mime="text/html",
    )
    st.components.v1.html(report_html, height=500, scrolling=True)
