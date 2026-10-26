"""AutoAnalyze FastAPI backend.

Serves the analysis API and the static frontend. Run with:
    uvicorn backend.main:app --reload
"""
from __future__ import annotations

import io

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.analysis import (
    MAX_UPLOAD_MB,
    InvalidCSVError,
    clean_dataset,
    get_categorical_summary,
    get_correlations,
    get_data_quality,
    get_histogram,
    get_numeric_summary,
    get_overview,
    get_top_correlated_pairs,
    load_csv,
    profile_column,
)
from app.insights import build_summary
from app.report import build_html_report
from backend.serialize import (
    categorical_summary_to_dict,
    correlations_to_dict,
    df_to_records,
    numeric_summary_to_dict,
    overview_to_dict,
    quality_to_dict,
)
from backend.store import store

app = FastAPI(title="AutoAnalyze API")


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")

    raw = await file.read()
    size_mb = len(raw) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        raise HTTPException(400, f"File is {size_mb:.1f} MB, which exceeds the {MAX_UPLOAD_MB} MB limit.")

    try:
        df = load_csv(io.BytesIO(raw))
    except InvalidCSVError as exc:
        raise HTTPException(400, str(exc)) from exc

    upload_id = store.put(df, file.filename)

    overview = get_overview(df)
    quality = get_data_quality(df)
    numeric_summary = get_numeric_summary(df)
    categorical_summary = get_categorical_summary(df)
    corr = get_correlations(df)
    top_pairs = get_top_correlated_pairs(corr)
    summary_lines = build_summary(df, overview, quality, numeric_summary, corr)

    return JSONResponse(
        {
            "upload_id": upload_id,
            "filename": file.filename,
            "preview": df_to_records(df, max_rows=50),
            "overview": overview_to_dict(overview),
            "quality": quality_to_dict(quality),
            "numeric_summary": numeric_summary_to_dict(numeric_summary),
            "categorical_summary": categorical_summary_to_dict(categorical_summary),
            "correlations": correlations_to_dict(corr),
            "top_correlated_pairs": df_to_records(top_pairs),
            "summary_lines": summary_lines,
            "columns": df.columns.tolist(),
        }
    )


def _get_df(upload_id: str):
    try:
        return store.get(upload_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found or has expired. Please re-upload.") from None


@app.get("/api/column/{upload_id}/{column}")
async def column_profile(upload_id: str, column: str) -> JSONResponse:
    df = _get_df(upload_id)
    if column not in df.columns:
        raise HTTPException(404, f"Column '{column}' not found.")

    profile = profile_column(df, column)
    payload = {
        "name": profile.name,
        "dtype": profile.dtype,
        "is_numeric": profile.is_numeric,
        "missing_count": profile.missing_count,
        "missing_pct": profile.missing_pct,
        "unique_count": profile.unique_count,
        "stats": profile.stats,
        "top_values": df_to_records(profile.top_values) if profile.top_values is not None else None,
        "histogram": get_histogram(df, column) if profile.is_numeric else None,
    }
    return JSONResponse(payload)


@app.get("/api/download/cleaned/{upload_id}")
async def download_cleaned(
    upload_id: str, drop_duplicates: bool = False, drop_constant_cols: bool = False
) -> Response:
    df = _get_df(upload_id)
    cleaned = clean_dataset(df, drop_duplicates=drop_duplicates, drop_constant_cols=drop_constant_cols)
    filename = f"cleaned_{store.get_filename(upload_id)}"
    return Response(
        content=cleaned.to_csv(index=False),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/download/report/{upload_id}")
async def download_report(upload_id: str) -> HTMLResponse:
    df = _get_df(upload_id)
    filename = store.get_filename(upload_id)

    overview = get_overview(df)
    quality = get_data_quality(df)
    numeric_summary = get_numeric_summary(df)
    corr = get_correlations(df)
    summary_lines = build_summary(df, overview, quality, numeric_summary, corr)

    report_html = build_html_report(filename, overview, quality, numeric_summary, summary_lines)
    report_filename = f"autoanalyze_report_{filename.rsplit('.', 1)[0]}.html"
    return HTMLResponse(
        content=report_html,
        headers={"Content-Disposition": f'attachment; filename="{report_filename}"'},
    )


app.mount("/", StaticFiles(directory="static", html=True), name="static")
