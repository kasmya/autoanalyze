# AutoAnalyze

Automated exploratory data analysis for CSV files — upload a dataset, get an
instant data-quality report, statistics and interactive charts, no code
required.

A standalone web application: a FastAPI + Pandas backend exposes a JSON
analysis API, and a vanilla HTML/CSS/JS frontend renders the dashboard with
Plotly.js charts.

## Features

- **Upload** — drag-and-drop or browse, with validation for empty/malformed/non-CSV files
- **Overview** — row/column counts, dtypes, memory usage, preview, statistical summary, plain-English summary (built only from computed statistics — no invented numbers or causal claims)
- **Data Quality** — missing values by column, duplicate rows, IQR-based outlier detection, constant/high-cardinality columns, cleaned-CSV download
- **Explore** — per-column distribution analysis, correlation heatmap, top correlated pairs, category breakdowns
- **Export** — downloadable self-contained HTML report

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript, Plotly.js |
| Backend | Python, FastAPI |
| Data processing | Pandas, NumPy |
| Testing | Pytest, FastAPI TestClient |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn backend.main:app --reload
```

Then open `http://localhost:8000` and upload a CSV.

## Tests

```bash
pytest -q
```

## Project structure

```
app/              # core, UI-independent analysis logic (pandas)
  analysis.py     # overview, data quality, stats, correlations, column profiling
  insights.py     # plain-English summary built only from computed stats
  report.py       # self-contained HTML report builder
backend/          # FastAPI app
  main.py         # API routes + static file serving
  serialize.py    # pandas -> JSON conversion
  store.py        # in-memory dataset store (single-process prototype, no DB)
static/           # frontend (HTML/CSS/JS, no build step)
tests/            # pytest unit + API tests
```

## Design notes

- Datasets are processed in memory only, with a file-size limit and an
  expiry on the in-memory store — there is no database or persistence layer
  in this prototype.
- Cleaning is always explicit and opt-in from the Data Quality tab; nothing
  is ever silently modified or removed from the original upload.
- The "AI summary" is template-based, generated only from statistics the
  backend actually computed — it never invents numbers or claims causation
  from a correlation.

## Roadmap

Deliberately out of scope for V1 (see `app/analysis.py` for what's already
built): Excel support, database connections, configurable cleaning
pipelines, ML model training, LLM-generated explanations, user accounts.
