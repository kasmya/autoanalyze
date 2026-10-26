// AutoAnalyze frontend — vanilla JS, no build step.

const state = {
  uploadId: null,
  filename: null,
  columns: [],
  numericCols: [],
  data: null,
};

const el = (id) => document.getElementById(id);

// ---------- Upload screen ----------

const dropzone = el("dropzone");
const fileInput = el("fileInput");
const browseBtn = el("browseBtn");
const uploadError = el("uploadError");
const uploadSpinner = el("uploadSpinner");
const fileInfo = el("fileInfo");

browseBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) handleFile(fileInput.files[0]);
});

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

function showUploadError(message) {
  uploadError.textContent = message;
  uploadError.hidden = false;
}

function clearUploadError() {
  uploadError.hidden = true;
}

async function handleFile(file) {
  clearUploadError();
  if (!file.name.toLowerCase().endsWith(".csv")) {
    showUploadError("Please upload a .csv file.");
    return;
  }

  fileInfo.hidden = false;
  fileInfo.innerHTML = `<strong>${escapeHtml(file.name)}</strong> &middot; ${(file.size / 1024).toFixed(1)} KB`;
  uploadSpinner.hidden = false;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const body = await res.json();
    if (!res.ok) {
      throw new Error(body.detail || "Upload failed.");
    }
    onUploadSuccess(body);
  } catch (err) {
    showUploadError(err.message || "Something went wrong while analyzing this file.");
  } finally {
    uploadSpinner.hidden = true;
  }
}

function onUploadSuccess(data) {
  state.uploadId = data.upload_id;
  state.filename = data.filename;
  state.columns = data.columns;
  state.numericCols = data.overview.numeric_cols;
  state.data = data;

  el("fileLabel").textContent = data.filename;
  el("topbarActions").hidden = false;

  renderOverview(data);
  renderQuality(data);
  renderExplore(data);

  el("screenUpload").hidden = true;
  el("screenDashboard").hidden = false;
}

el("newDatasetBtn").addEventListener("click", () => {
  state.uploadId = null;
  fileInput.value = "";
  fileInfo.hidden = true;
  el("topbarActions").hidden = true;
  el("screenDashboard").hidden = true;
  el("screenUpload").hidden = false;
});

// ---------- Tabs ----------

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => (p.hidden = true));
    btn.classList.add("active");
    el("tab" + capitalize(btn.dataset.tab)).hidden = false;
  });
});

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ---------- Overview tab ----------

function renderOverview(data) {
  const o = data.overview;
  el("overviewMetrics").innerHTML = [
    metricCard("Rows", o.n_rows.toLocaleString()),
    metricCard("Columns", o.n_cols),
    metricCard("Memory", `${o.memory_mb} MB`),
    metricCard("Numeric cols", o.numeric_cols.length),
  ].join("");

  el("summaryList").innerHTML = data.summary_lines.map((l) => `<li>${escapeHtml(l)}</li>`).join("");

  renderTable("previewTable", data.preview);

  const dtypeRows = Object.entries(o.dtypes).map(([column, dtype]) => ({ column, dtype }));
  renderTable("dtypesTable", dtypeRows);

  renderTable("numericSummaryTable", data.numeric_summary, "No numeric columns found.");
}

function metricCard(label, value) {
  return `<div class="metric-card"><div class="label">${label}</div><div class="value">${value}</div></div>`;
}

// ---------- Data Quality tab ----------

function renderQuality(data) {
  const q = data.quality;
  const missingNonZero = q.missing_by_col.filter((r) => r.missing_count > 0);

  if (missingNonZero.length) {
    Plotly.newPlot(
      "missingChart",
      [
        {
          x: missingNonZero.map((r) => r.column),
          y: missingNonZero.map((r) => r.missing_pct),
          type: "bar",
          marker: { color: "#6366f1" },
        },
      ],
      chartLayout("Missing values by column (%)"),
      chartConfig()
    );
  } else {
    el("missingChart").innerHTML = '<p style="padding:16px" class="muted">No missing values detected.</p>';
  }
  renderTable("missingTable", missingNonZero, "No missing values detected.");

  el("duplicatesSummary").textContent = q.duplicate_rows
    ? `${q.duplicate_rows.toLocaleString()} duplicate rows (${q.duplicate_pct}%).`
    : "No duplicate rows detected.";

  const outlierRows = Object.entries(q.outliers_by_col)
    .filter(([, count]) => count > 0)
    .map(([column, outlier_count]) => ({ column, outlier_count }));
  renderTable("outliersTable", outlierRows, "No outliers detected in numeric columns.");

  if (q.constant_cols.length) {
    el("constantColsBlock").hidden = false;
    el("constantColsList").textContent = q.constant_cols.join(", ");
  }
  if (q.high_cardinality_cols.length) {
    el("highCardBlock").hidden = false;
    el("highCardList").textContent = q.high_cardinality_cols.join(", ");
  }
}

el("downloadCleanedBtn").addEventListener("click", () => {
  const dropDup = el("dropDuplicatesCheck").checked;
  const dropConst = el("dropConstantCheck").checked;
  const url = `/api/download/cleaned/${state.uploadId}?drop_duplicates=${dropDup}&drop_constant_cols=${dropConst}`;
  window.location.href = url;
});

el("downloadReportBtn").addEventListener("click", () => {
  window.location.href = `/api/download/report/${state.uploadId}`;
});

// ---------- Explore tab ----------

function renderExplore(data) {
  const select = el("columnSelect");
  select.innerHTML = state.columns.map((c) => `<option value="${escapeAttr(c)}">${escapeHtml(c)}</option>`).join("");
  select.onchange = () => loadColumnProfile(select.value);
  loadColumnProfile(state.columns[0]);

  const corr = data.correlations;
  if (corr.columns.length) {
    el("correlationBlock").hidden = false;
    Plotly.newPlot(
      "correlationChart",
      [
        {
          z: corr.matrix,
          x: corr.columns,
          y: corr.columns,
          type: "heatmap",
          colorscale: "RdBu",
          zmin: -1,
          zmax: 1,
        },
      ],
      chartLayout("Correlation matrix"),
      chartConfig()
    );
    renderTable("topPairsTable", data.top_correlated_pairs, "Not enough numeric columns for correlations.");
  }
}

async function loadColumnProfile(column) {
  const res = await fetch(`/api/column/${state.uploadId}/${encodeURIComponent(column)}`);
  const profile = await res.json();

  el("columnMetrics").innerHTML = [
    metricCard("Missing", `${profile.missing_count} (${profile.missing_pct}%)`),
    metricCard("Unique values", profile.unique_count),
    metricCard("Type", profile.dtype),
  ].join("");

  const chartDiv = el("columnChart");
  const topValuesTable = el("columnTopValuesTable");

  if (profile.is_numeric && profile.histogram) {
    const h = profile.histogram;
    const centers = h.bin_edges.slice(0, -1).map((e, i) => (e + h.bin_edges[i + 1]) / 2);
    Plotly.newPlot(
      chartDiv.id,
      [{ x: centers, y: h.counts, type: "bar", marker: { color: "#6366f1" } }],
      chartLayout(`Distribution of ${column}`),
      chartConfig()
    );
    topValuesTable.innerHTML = "";
  } else if (profile.top_values) {
    Plotly.newPlot(
      chartDiv.id,
      [
        {
          x: profile.top_values.map((r) => r[column]),
          y: profile.top_values.map((r) => r.count),
          type: "bar",
          marker: { color: "#6366f1" },
        },
      ],
      chartLayout(`Top values in ${column}`),
      chartConfig()
    );
    renderTable(topValuesTable.id, profile.top_values);
  }
}

// ---------- helpers ----------

function chartLayout(title) {
  const isDark = !window.matchMedia("(prefers-color-scheme: light)").matches;
  return {
    title: { text: title, font: { size: 14 } },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: isDark ? "#e8e9ed" : "#15171f" },
    margin: { t: 40, l: 50, r: 20, b: 60 },
    height: 360,
  };
}

function chartConfig() {
  return { responsive: true, displayModeBar: false };
}

function renderTable(tableIdOrEl, rows, emptyMessage) {
  const table = typeof tableIdOrEl === "string" ? el(tableIdOrEl) : tableIdOrEl;
  if (!rows || rows.length === 0) {
    table.innerHTML = emptyMessage ? `<tr><td class="muted">${escapeHtml(emptyMessage)}</td></tr>` : "";
    return;
  }
  const columns = Object.keys(rows[0]);
  const thead = `<thead><tr>${columns.map((c) => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${rows
    .map(
      (row) =>
        `<tr>${columns.map((c) => `<td>${row[c] === null || row[c] === undefined ? "" : escapeHtml(String(row[c]))}</td>`).join("")}</tr>`
    )
    .join("")}</tbody>`;
  table.innerHTML = thead + tbody;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(str) {
  return escapeHtml(str).replace(/"/g, "&quot;");
}
