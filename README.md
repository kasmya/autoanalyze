# AutoAnalyze Lite

Automated Exploratory Data Analysis for CSV files — no code required.

Upload a CSV and instantly get a dataset overview, a data-quality report
(missing values, duplicates, outliers), statistical summaries, interactive
visualizations, and a downloadable HTML report with a plain-English summary
generated from the computed statistics (never invented numbers).

## Features

- **Overview** — row/column counts, dtypes, memory usage, preview, statistical summary
- **Data Quality** — missing values, duplicate rows, IQR-based outlier detection, constant/high-cardinality columns, cleaned-CSV download
- **Explore** — per-column distribution analysis, correlation heatmap, top correlated pairs, category breakdowns
- **Export** — downloadable self-contained HTML report

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run streamlit_app.py
```

Then open the URL Streamlit prints (default `http://localhost:8501`) and upload a CSV.

## Tests

```bash
pytest -q
```

## Project structure

```
app/
  analysis.py   # core, UI-independent analysis functions
  insights.py   # plain-English summary built only from computed stats
  report.py     # self-contained HTML report builder
streamlit_app.py  # Streamlit UI
tests/            # pytest unit tests for app/
```

## Roadmap

- Phase 1 (done): working prototype — upload, overview, quality, charts
- Phase 2 (done): error handling, tests, CI, cleaned-dataset export, report export
- Phase 3: optional LLM-backed narrative summary (current summary is template-based from real statistics, with no causal claims)
