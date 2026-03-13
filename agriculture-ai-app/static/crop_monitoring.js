/* ==========================================================================
   Crop Monitoring – Chart & Data Rendering
   Uses Chart.js 4.x  +  /api/crop-monitoring/* endpoints
   ========================================================================== */

// Chart instances (for destroy-before-recreate)
let chartProduction   = null;
let chartPrices       = null;
let chartSeasons      = null;
let chartCompare      = null;
let chartProductivity = null;

// ── helpers ──────────────────────────────────────────────────────────────────
function _fmt(n) {
  if (n == null) return "—";
  return Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function _isDark() {
  return document.body.classList.contains("dark-mode");
}

function _gridColor() {
  return _isDark() ? "rgba(148,163,184,0.18)" : "rgba(15,23,42,0.08)";
}

function _textColor() {
  return _isDark() ? "#e2e8f0" : "#1e293b";
}

function _chartDefaults() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: _textColor(), font: { weight: 600 } } },
    },
    scales: {
      x: { ticks: { color: _textColor() }, grid: { color: _gridColor() } },
      y: { ticks: { color: _textColor() }, grid: { color: _gridColor() } },
    },
  };
}

async function _post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Request failed with status ${res.status}`);
  }
  return data;
}

function setStatus(message, type = "warning") {
  const el = document.getElementById("monitor-status");
  if (!el) return;
  el.className = `alert alert-${type} mb-3`;
  el.textContent = message;
  el.classList.remove("d-none");
}

function clearStatus() {
  const el = document.getElementById("monitor-status");
  if (!el) return;
  el.textContent = "";
  el.classList.add("d-none");
}

// ── main loaders ─────────────────────────────────────────────────────────────

async function loadDashboard() {
  const crop      = document.getElementById("filter-crop").value;
  const state     = document.getElementById("filter-state").value || null;
  const commodity = document.getElementById("filter-commodity").value || null;

  clearStatus();

  if (!crop) {
    setStatus("Select a crop to analyze.");
    return;
  }

  // spinner
  document.getElementById("monitor-btn-text").classList.add("d-none");
  document.getElementById("monitor-btn-spinner").classList.remove("d-none");
  document.getElementById("monitor-btn").disabled = true;

  try {
    const data = await _post("/api/crop-monitoring/dashboard", { crop, state, commodity });
    renderSummary(data);
    renderProductionChart(data.production);
    renderProductionForecast(data.production);
    renderPriceChart(data.market_price);
    renderPriceForecast(data.market_price);
    renderSeasonsChart(data.seasons);
    renderStateRanking(data.state_ranking);
    renderProductivityChart(data.production);
    renderSoilProfile(data.soil_profile);
  } catch (e) {
    console.error("Dashboard load error:", e);
    setStatus(e.message || "Unable to load the crop monitoring dashboard right now.", "danger");
  } finally {
    document.getElementById("monitor-btn-text").classList.remove("d-none");
    document.getElementById("monitor-btn-spinner").classList.add("d-none");
    document.getElementById("monitor-btn").disabled = false;
  }
}

async function loadComparison() {
  const raw   = document.getElementById("compare-crops").value;
  const crops = raw.split(",").map(s => s.trim()).filter(Boolean);
  const state = document.getElementById("filter-state").value || null;
  if (crops.length === 0) {
    setStatus("Enter at least one crop name to compare.");
    return;
  }

  try {
    const data = await _post("/api/crop-monitoring/compare", { crops, state });
    renderCompareChart(data);
  } catch (e) {
    console.error("Compare error:", e);
    setStatus(e.message || "Unable to compare crops right now.", "danger");
  }
}

async function hydrateFilters() {
  const cropSelect = document.getElementById("filter-crop");
  const stateSelect = document.getElementById("filter-state");
  const commoditySelect = document.getElementById("filter-commodity");

  if (!cropSelect || cropSelect.options.length > 0) {
    return;
  }

  const res = await fetch("/api/crop-monitoring/filters");
  const filters = await res.json();

  cropSelect.innerHTML = (filters.production_crops || [])
    .map(crop => `<option value="${crop}" ${crop === "Rice" ? "selected" : ""}>${crop}</option>`)
    .join("");

  stateSelect.innerHTML = [`<option value="">All States</option>`]
    .concat((filters.states || []).map(state => `<option value="${state}">${state}</option>`))
    .join("");

  commoditySelect.innerHTML = [`<option value="">All Commodities</option>`]
    .concat((filters.price_crops || []).map(commodity => `<option value="${commodity}">${commodity}</option>`))
    .join("");
}

// ── summary cards ────────────────────────────────────────────────────────────

function renderSummary(data) {
  const row = document.getElementById("summary-cards");
  row.classList.remove("d-none");

  const ps = data.production?.summary || {};
  const ms = data.market_price?.summary || {};

  document.getElementById("sum-trend").textContent      = ps.trend_direction || "—";
  document.getElementById("sum-avg-prod").textContent    = _fmt(ps.avg_production);
  document.getElementById("sum-price-trend").textContent = ms.price_trend || "—";
  document.getElementById("sum-avg-price").textContent   = ms.avg_modal_price ? `₹${_fmt(ms.avg_modal_price)}` : "—";
}

// ── Production chart ─────────────────────────────────────────────────────────

function renderProductionChart(prod) {
  const yearly  = prod?.yearly || [];
  const forecast = prod?.forecast || [];

  const labels     = yearly.map(y => y.year);
  const production = yearly.map(y => y.total_production);
  const area       = yearly.map(y => y.total_area);

  // Append forecast
  const fLabels = forecast.map(f => f.year);
  const fProd   = forecast.map(f => f.predicted_production);

  const allLabels = [...labels, ...fLabels];
  const prodData  = [...production, ...new Array(fLabels.length).fill(null)];
  const foreData  = [...new Array(labels.length).fill(null), ...fProd];
  const areaData  = [...area, ...forecast.map(f => f.predicted_area)];

  if (chartProduction) chartProduction.destroy();

  const ctx = document.getElementById("chart-production").getContext("2d");
  chartProduction = new Chart(ctx, {
    type: "line",
    data: {
      labels: allLabels,
      datasets: [
        {
          label: "Total Production",
          data: prodData,
          borderColor: "#22c55e",
          backgroundColor: "rgba(34,197,94,0.15)",
          borderWidth: 3,
          fill: true,
          tension: 0.3,
          pointRadius: 4,
        },
        {
          label: "Forecast Production",
          data: foreData,
          borderColor: "#fbbf24",
          borderDash: [8, 4],
          borderWidth: 2,
          pointRadius: 5,
          pointStyle: "triangle",
          fill: false,
          tension: 0.3,
        },
        {
          label: "Total Area (ha)",
          data: areaData,
          borderColor: "#3b82f6",
          backgroundColor: "rgba(59,130,246,0.08)",
          borderWidth: 2,
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      ..._chartDefaults(),
      scales: {
        x: { ticks: { color: _textColor() }, grid: { color: _gridColor() } },
        y: {
          position: "left",
          title: { display: true, text: "Production", color: _textColor() },
          ticks: { color: _textColor() },
          grid: { color: _gridColor() },
        },
        y1: {
          position: "right",
          title: { display: true, text: "Area (ha)", color: _textColor() },
          ticks: { color: _textColor() },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

// ── Production forecast text ─────────────────────────────────────────────────

function renderProductionForecast(prod) {
  const forecast = prod?.forecast || [];
  const summary  = prod?.summary || {};
  const div = document.getElementById("forecast-production");

  let html = "";
  if (forecast.length) {
    forecast.forEach(f => {
      html += `<div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid rgba(148,163,184,0.15);">
        <span style="font-weight:700; color:#fbbf24;">${f.year}</span>
        <span style="font-weight:600;">${_fmt(f.predicted_production)}</span>
        <span style="font-size:0.8rem; color:#60a5fa;">~${_fmt(f.predicted_productivity)} prod/ha</span>
      </div>`;
    });
    html += `<div class="mt-3 p-3" style="background:rgba(34,197,94,0.12); border-radius:10px; border-left:4px solid #22c55e;">
      <strong>Growth Rate:</strong> ${summary.growth_rate_pct || 0}% per year<br>
      <strong>Avg Production:</strong> ${_fmt(summary.avg_production)}<br>
      <strong>Peak Production:</strong> ${_fmt(summary.max_production)}
    </div>`;
  } else {
    html = `<p style="color:#94a3b8;">No production data available for this selection.</p>`;
  }
  div.innerHTML = html;
}

// ── Price chart ──────────────────────────────────────────────────────────────

function renderPriceChart(price) {
  const daily = price?.daily || [];
  if (chartPrices) chartPrices.destroy();

  if (!daily.length) {
    const ctx = document.getElementById("chart-prices").getContext("2d");
    chartPrices = new Chart(ctx, {
      type: "bar",
      data: { labels: ["No data"], datasets: [{ label: "No price data", data: [0] }] },
      options: _chartDefaults(),
    });
    return;
  }

  const labels   = daily.map(d => d.date);
  const minP     = daily.map(d => d.min_price);
  const maxP     = daily.map(d => d.max_price);
  const modalP   = daily.map(d => d.modal_price);

  const ctx = document.getElementById("chart-prices").getContext("2d");
  chartPrices = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Modal Price",
          data: modalP,
          borderColor: "#fbbf24",
          backgroundColor: "rgba(251,191,36,0.15)",
          borderWidth: 3,
          fill: true,
          tension: 0.3,
          pointRadius: 5,
        },
        {
          label: "Max Price",
          data: maxP,
          borderColor: "#ef4444",
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 3,
          fill: false,
        },
        {
          label: "Min Price",
          data: minP,
          borderColor: "#22c55e",
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 3,
          fill: false,
        },
      ],
    },
    options: {
      ..._chartDefaults(),
      scales: {
        x: { ticks: { color: _textColor(), maxRotation: 45 }, grid: { color: _gridColor() } },
        y: {
          title: { display: true, text: "Price (Rs./Quintal)", color: _textColor() },
          ticks: { color: _textColor() },
          grid: { color: _gridColor() },
        },
      },
    },
  });
}

// ── Price forecast + monthly ─────────────────────────────────────────────────

function renderPriceForecast(price) {
  const forecast = price?.forecast || [];
  const monthly  = price?.monthly || [];
  const summary  = price?.summary || {};

  // Forecast
  const fDiv = document.getElementById("forecast-price");
  let fhtml = "";
  if (forecast.length) {
    forecast.forEach(f => {
      fhtml += `<div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid rgba(148,163,184,0.15);">
        <span style="font-weight:600;">+${f.days_ahead} days</span>
        <span style="font-weight:700; color:#fbbf24;">₹${_fmt(f.predicted_modal_price)}</span>
        <span style="font-size:0.8rem; color:#60a5fa;">${f.trend_per_day > 0 ? "↑" : "↓"} ₹${Math.abs(f.trend_per_day)}/day</span>
      </div>`;
    });
    fhtml += `<div class="mt-2 p-2" style="background:rgba(251,191,36,0.12); border-radius:8px; font-size:0.85rem;">
      <strong>Volatility:</strong> ₹${_fmt(summary.price_volatility)} | 
      <strong>Range:</strong> ₹${_fmt(summary.min_modal_price)} – ₹${_fmt(summary.max_modal_price)}
    </div>`;
  } else {
    fhtml = `<p style="color:#94a3b8; font-size:0.9rem;">No price forecast available.</p>`;
  }
  fDiv.innerHTML = fhtml;

  // Monthly
  const mDiv = document.getElementById("monthly-prices");
  let mhtml = "";
  if (monthly.length) {
    monthly.forEach(m => {
      mhtml += `<div style="display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid rgba(148,163,184,0.1);">
        <span style="font-weight:600;">${m.month}</span>
        <span>₹${_fmt(m.avg_modal_price)}</span>
        <span style="font-size:0.8rem; color:#94a3b8;">(${m.data_points} pts)</span>
      </div>`;
    });
  } else {
    mhtml = `<span style="color:#94a3b8; font-size:0.9rem;">No monthly data.</span>`;
  }
  mDiv.innerHTML = mhtml;
}

// ── Seasons chart ────────────────────────────────────────────────────────────

function renderSeasonsChart(seasons) {
  const list = seasons?.seasons || [];
  if (chartSeasons) chartSeasons.destroy();

  const labels = list.map(s => s.season);
  const prods  = list.map(s => s.total_production);
  const areas  = list.map(s => s.total_area);

  const palette = ["#22c55e", "#3b82f6", "#fbbf24", "#ef4444", "#8b5cf6", "#06b6d4"];

  const ctx = document.getElementById("chart-seasons").getContext("2d");
  chartSeasons = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: prods,
        backgroundColor: palette.slice(0, labels.length),
        borderWidth: 2,
        borderColor: _isDark() ? "#0f172a" : "#ffffff",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { color: _textColor(), font: { weight: 600, size: 13 } } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.label}: ${_fmt(ctx.parsed)} (Area: ${_fmt(areas[ctx.dataIndex])})`,
          },
        },
      },
    },
  });
}

// ── State ranking ────────────────────────────────────────────────────────────

function renderStateRanking(ranking) {
  const states = ranking?.states || [];
  const div = document.getElementById("state-ranking");

  if (!states.length) {
    div.innerHTML = `<p style="color:#94a3b8;">No state data available.</p>`;
    return;
  }

  let html = `<table style="width:100%; border-collapse:collapse;">
    <thead>
      <tr style="border-bottom:2px solid rgba(148,163,184,0.3);">
        <th style="padding:8px; text-align:left; font-size:0.85rem;">Rank</th>
        <th style="padding:8px; text-align:left; font-size:0.85rem;">State</th>
        <th style="padding:8px; text-align:right; font-size:0.85rem;">Total Prod.</th>
        <th style="padding:8px; text-align:right; font-size:0.85rem;">Prod./Ha</th>
      </tr>
    </thead><tbody>`;

  states.forEach((s, i) => {
    const bgColor = i === 0 ? "rgba(34,197,94,0.12)" : (i % 2 === 0 ? "rgba(255,255,255,0.02)" : "transparent");
    const medal   = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `#${s.rank}`;
    html += `<tr style="background:${bgColor}; border-bottom:1px solid rgba(148,163,184,0.1);">
      <td style="padding:8px; font-weight:700;">${medal}</td>
      <td style="padding:8px;">${s.state}</td>
      <td style="padding:8px; text-align:right; font-weight:600; color:#3b82f6;">${_fmt(s.total_production)}</td>
      <td style="padding:8px; text-align:right; color:#22c55e;">${_fmt(s.productivity)}</td>
    </tr>`;
  });

  html += `</tbody></table>`;
  div.innerHTML = html;
}

// ── Comparison chart ─────────────────────────────────────────────────────────

function renderCompareChart(data) {
  const crops = data?.crops || [];
  if (chartCompare) chartCompare.destroy();

  const labels  = crops.map(c => c.crop);
  const avgProd = crops.map(c => c.avg_production);
  const latest  = crops.map(c => c.latest_production);
  const fcast   = crops.map(c => c.forecast_next_year);

  const ctx = document.getElementById("chart-compare").getContext("2d");
  chartCompare = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Avg Production",
          data: avgProd,
          backgroundColor: "rgba(59,130,246,0.7)",
          borderRadius: 6,
        },
        {
          label: "Latest Year",
          data: latest,
          backgroundColor: "rgba(34,197,94,0.7)",
          borderRadius: 6,
        },
        {
          label: "Forecast (Next Year)",
          data: fcast,
          backgroundColor: "rgba(251,191,36,0.7)",
          borderRadius: 6,
        },
      ],
    },
    options: {
      ..._chartDefaults(),
      plugins: {
        legend: { labels: { color: _textColor(), font: { weight: 600 } } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${_fmt(ctx.parsed.y)}`,
          },
        },
      },
    },
  });
}

function renderSoilProfile(profile) {
  const soilTypesEl = document.getElementById("soil-top-types");
  document.getElementById("soil-avg-ph").textContent = profile?.avg_ph ? _fmt(profile.avg_ph) : "—";
  document.getElementById("soil-avg-n").textContent = profile?.avg_n ? _fmt(profile.avg_n) : "—";
  document.getElementById("soil-avg-p").textContent = profile?.avg_p ? _fmt(profile.avg_p) : "—";
  document.getElementById("soil-avg-k").textContent = profile?.avg_k ? _fmt(profile.avg_k) : "—";

  if (!soilTypesEl) return;

  const topSoils = profile?.top_soils || [];
  if (!topSoils.length) {
    soilTypesEl.innerHTML = `<span style="color:#94a3b8;">No soil records available for this selection.</span>`;
    return;
  }

  soilTypesEl.innerHTML = topSoils.map(item => `
    <span style="padding:8px 12px; border-radius:999px; background:rgba(139,92,246,0.1); color:#6d28d9; font-weight:700;">
      ${item.soil_type} (${item.count})
    </span>
  `).join("");
}

// ── Productivity chart ───────────────────────────────────────────────────────

function renderProductivityChart(prod) {
  const yearly = prod?.yearly || [];
  if (chartProductivity) chartProductivity.destroy();

  const labels  = yearly.map(y => y.year);
  const prodv   = yearly.map(y => y.productivity);
  const temps   = yearly.map(y => y.avg_temp);
  const hums    = yearly.map(y => y.avg_humidity);

  const ctx = document.getElementById("chart-productivity").getContext("2d");
  chartProductivity = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Productivity (prod/ha)",
          data: prodv,
          borderColor: "#ef4444",
          backgroundColor: "rgba(239,68,68,0.1)",
          borderWidth: 3,
          fill: true,
          tension: 0.3,
          yAxisID: "y",
        },
        {
          label: "Avg Temp (°C)",
          data: temps,
          borderColor: "#fbbf24",
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 3,
          yAxisID: "y1",
        },
        {
          label: "Avg Humidity (%)",
          data: hums,
          borderColor: "#3b82f6",
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 3,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      ..._chartDefaults(),
      scales: {
        x: { ticks: { color: _textColor() }, grid: { color: _gridColor() } },
        y: {
          position: "left",
          title: { display: true, text: "Productivity", color: _textColor() },
          ticks: { color: _textColor() },
          grid: { color: _gridColor() },
        },
        y1: {
          position: "right",
          title: { display: true, text: "Temp / Humidity", color: _textColor() },
          ticks: { color: _textColor() },
          grid: { drawOnChartArea: false },
        },
      },
    },
  });
}

// ── Auto-load on page ────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Only auto-load if we're on the monitoring page
  if (document.getElementById("chart-production")) {
    document.getElementById("monitor-btn")?.addEventListener("click", loadDashboard);
    document.getElementById("compare-btn")?.addEventListener("click", loadComparison);
    hydrateFilters()
      .catch(err => {
        console.error("Filter hydration error:", err);
        setStatus("The monitoring filters could not be loaded from the datasets.", "danger");
      })
      .finally(() => {
        loadDashboard();
        loadComparison();
      });
  }
});
