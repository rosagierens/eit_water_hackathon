// Map of plants + time-series charts per data source, fed by the JSON API in app/api/main.py.

const state = { track: 1, plant: null, compare: null, picking: false, request: 0 };
const dark = window.matchMedia("(prefers-color-scheme: dark)");

// Open-source basemap: OpenFreeMap (OpenStreetMap data, no API key) rendered with MapLibre GL JS.
// Other OpenFreeMap styles: "liberty", "bright". The style carries its own attribution.
const BASEMAP_STYLE = "https://tiles.openfreemap.org/styles/positron";

// What a series measures, picked from its units. Colors are CSS tokens (style.css) so dark mode swaps them.
const QUANTITIES = {
  discharge: { key: "discharge", name: "River discharge", unit: "m³/s", color: "--series-1", format: ",.0f", zero: true },
  temperature: { key: "temperature", name: "Water temperature", unit: "°C", color: "--series-2", format: ".1f", zero: false },
  curtailment: { key: "curtailment", name: "Curtailment", unit: "MW", color: "--series-4", format: ",.0f", zero: true, shape: "linear" },
  other: { key: "other", name: "Value", unit: "", color: "--series-3", format: ",.2f", zero: false },
};

// Track 2: colour follows the scenario, never its position in the list. Historical runs are grey
// references (told apart by dash); C3S RCPs are one blue ramp, light to dark with rising forcing.
const SCENARIO_STYLE = {
  hydroland_hist: { color: "--reference", dash: "solid" },
  c3s_historical: { color: "--reference", dash: "dash" },
  hydroland_ssp370: { color: "--series-2", dash: "solid" },
  c3s_rcp26: { color: "--ramp-low", dash: "solid" },
  c3s_rcp45: { color: "--ramp-mid", dash: "solid" },
  c3s_rcp85: { color: "--ramp-high", dash: "solid" },
};

const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

function quantityOf(source) {
  if (source.variable === "curtailment") return QUANTITIES.curtailment;
  const u = (source.units || "").toLowerCase();
  if (u.includes("degc") || u.includes("°c") || /temperature/i.test(source.label)) return QUANTITIES.temperature;
  if (u.includes("m3") || u.includes("m³") || /discharge/i.test(source.label)) return QUANTITIES.discharge;
  return { ...QUANTITIES.other, unit: source.units || "" };
}

const map = new maplibregl.Map({
  container: "map",
  style: BASEMAP_STYLE,
  center: [10, 50],
  zoom: 3.3,
  maxZoom: 14,
});
map.addControl(new maplibregl.NavigationControl({ showCompass: false }));
map.addControl(new maplibregl.ScaleControl());

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

// Marker colour = net capacity on one orange ramp, light (small) to dark (large). Literal hex,
// because MapLibre rejects an empty colour and then drops the whole layer.
const CAPACITY_RAMP = ["#fdba74", "#ea580c", "#7c2d12"];
let plantList = [];

function rampColor(t) {
  const [a, b] = t < 0.5 ? [CAPACITY_RAMP[0], CAPACITY_RAMP[1]] : [CAPACITY_RAMP[1], CAPACITY_RAMP[2]];
  const f = t < 0.5 ? t * 2 : (t - 0.5) * 2;
  const ca = parseInt(a.slice(1), 16), cb = parseInt(b.slice(1), 16);
  const mix = (shift) => Math.round(((ca >> shift) & 255) * (1 - f) + ((cb >> shift) & 255) * f);
  return `rgb(${mix(16)},${mix(8)},${mix(0)})`;
}

async function loadPlants() {
  plantList = await getJSON("/api/plants");
  const byId = Object.fromEntries(plantList.map((p) => [p.id, p]));
  const caps = plantList.map((p) => p.capacity_mw);
  const minCap = Math.min(...caps), maxCap = Math.max(...caps, minCap + 1);
  plantList.forEach((p) => { p.capacityShare = (p.capacity_mw - minCap) / (maxCap - minCap); });

  map.addSource("plants", {
    type: "geojson",
    data: {
      type: "FeatureCollection",
      features: plantList.map((p) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [p.lon, p.lat] },
        properties: { id: p.id, name: p.name, capacity_mw: p.capacity_mw },
      })),
    },
  });
  const radius = ["+", 4, ["/", ["sqrt", ["get", "capacity_mw"]], 12]];
  const color = ["interpolate", ["linear"], ["get", "capacity_mw"],
    minCap, CAPACITY_RAMP[0], (minCap + maxCap) / 2, CAPACITY_RAMP[1], maxCap, CAPACITY_RAMP[2]];
  map.addLayer({
    id: "plants", type: "circle", source: "plants",
    paint: { "circle-radius": radius, "circle-color": color, "circle-opacity": 0.9,
             "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5 },
  });
  map.addLayer({
    id: "plant-hover", type: "circle", source: "plants", filter: ["==", ["get", "id"], ""],
    paint: { "circle-radius": ["+", radius, 3], "circle-color": "rgba(0,0,0,0)",
             "circle-stroke-color": "#2a78d6", "circle-stroke-width": 2 },
  });
  map.addLayer({
    id: "plant-compare", type: "circle", source: "plants", filter: ["==", ["get", "id"], ""],
    paint: { "circle-radius": ["+", radius, 4], "circle-color": "rgba(0,0,0,0)",
             "circle-stroke-color": "#1baf7a", "circle-stroke-width": 2.5 },
  });
  map.addLayer({
    id: "plant-selected", type: "circle", source: "plants", filter: ["==", ["get", "id"], ""],
    paint: { "circle-radius": ["+", radius, 4], "circle-color": "rgba(0,0,0,0)",
             "circle-stroke-color": "#1d1d1b", "circle-stroke-width": 2.5 },
  });

  const tooltip = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
  map.on("mousemove", "plants", (e) => {
    map.getCanvas().style.cursor = "pointer";
    const p = e.features[0].properties;
    highlight(p.id);
    tooltip.setLngLat(e.lngLat).setText(`${p.name} (${Math.round(p.capacity_mw).toLocaleString()} MW)`).addTo(map);
  });
  map.on("mouseleave", "plants", () => {
    map.getCanvas().style.cursor = "";
    highlight(null);
    tooltip.remove();
  });
  map.on("click", "plants", (e) => selectPlant(byId[e.features[0].properties.id]));

  document.getElementById("legend-min").textContent = `${Math.round(minCap).toLocaleString()} MW`;
  document.getElementById("legend-max").textContent = `${Math.round(maxCap).toLocaleString()} MW`;
  document.querySelector(".legend-ramp").style.background = `linear-gradient(90deg, ${CAPACITY_RAMP.join(", ")})`;
  document.getElementById("legend").hidden = false;
  showOverview();
}

function setMapFilter(layer, id) {
  if (map.getLayer(layer)) map.setFilter(layer, ["==", ["get", "id"], id ?? ""]);
}

function highlight(id) {
  if (map.getLayer("plant-hover")) map.setFilter("plant-hover", ["==", ["get", "id"], id ?? ""]);
}

function plantRow(p) {
  return `<li><button class="plant-row" data-id="${esc(p.id)}">
      <span class="dot" style="background:${rampColor(p.capacityShare)}"></span>
      <span class="row-name">${esc(p.name)}<small>${esc(p.country)}</small></span>
      <span class="row-cap">${Math.round(p.capacity_mw).toLocaleString()} MW</span>
      <span class="bar"><span style="width:${(8 + 92 * p.capacityShare).toFixed(0)}%;background:${rampColor(p.capacityShare)}"></span></span>
    </button></li>`;
}

// The start view: every plant, largest first. Hover a row to find it on the map, click to open it.
function showOverview() {
  state.plant = null;
  state.compare = null;
  state.picking = false;
  state.request++;
  setMapFilter("plant-selected", null);
  setMapFilter("plant-compare", null);
  const countries = new Set(plantList.map((p) => p.country).filter(Boolean)).size;
  const total = plantList.reduce((sum, p) => sum + p.capacity_mw, 0);
  document.getElementById("plant-info").innerHTML = `
    <div class="kpis">
      <div class="kpi kpi-a"><span>${plantList.length}</span>plants</div>
      <div class="kpi kpi-b"><span>${countries}</span>countries</div>
      <div class="kpi kpi-c"><span>${Math.round(total / 1000).toLocaleString()}</span>GW capacity</div>
    </div>
    <p class="hint">Pick a plant on the map or in the list to see its river conditions.</p>`;
  const sorted = [...plantList].sort((a, b) => b.capacity_mw - a.capacity_mw);
  document.getElementById("charts").innerHTML = `<ul class="plant-list">${sorted.map(plantRow).join("")}</ul>`;
}

document.getElementById("panel").addEventListener("click", (e) => {
  const row = e.target.closest(".plant-row");
  if (row) selectPlant(plantList.find((p) => p.id === row.dataset.id));
  if (e.target.closest(".back")) showOverview();
  if (e.target.closest(".compare-btn")) { state.picking = true; renderPlantInfo(); searchInput.focus(); }
  if (e.target.closest(".cancel-compare")) { state.picking = false; renderPlantInfo(); }
  const legalToggle = e.target.closest(".legal-toggle");
  if (legalToggle) {
    const open = legalToggle.parentElement.classList.toggle("open");
    legalToggle.setAttribute("aria-expanded", open);
    legalToggle.textContent = open ? "Show less" : "Show more";
  }
  if (e.target.closest(".clear-compare")) { state.compare = null; setMapFilter("plant-compare", null); renderPlantInfo(); loadCharts(); }
});
document.getElementById("panel").addEventListener("mouseover", (e) => {
  const row = e.target.closest(".plant-row");
  highlight(row ? row.dataset.id : null);
});
document.getElementById("panel").addEventListener("mouseleave", () => highlight(null));

// While "Compare with…" is active, the next plant picked becomes the comparison plant.
function selectPlant(plant) {
  if (!plant) return;
  closeSearch();
  if (state.picking && state.plant && plant.id !== state.plant.id) {
    state.compare = plant;
    state.picking = false;
    setMapFilter("plant-compare", plant.id);
    const bounds = new maplibregl.LngLatBounds([state.plant.lon, state.plant.lat], [plant.lon, plant.lat]);
    map.fitBounds(bounds, { padding: 80, maxZoom: 7, duration: 1200 });
  } else {
    state.plant = plant;
    state.picking = false;
    if (state.compare?.id === plant.id) state.compare = null;
    setMapFilter("plant-selected", plant.id);
    setMapFilter("plant-compare", state.compare?.id);
    map.flyTo({ center: [plant.lon, plant.lat], zoom: Math.max(map.getZoom(), 6), speed: 1.4 });
  }
  renderPlantInfo();
  loadCharts();
}

function renderPlantInfo() {
  const plant = state.plant;
  const facts = [
    plant.country,
    plant.units ? `${plant.units} unit${plant.units > 1 ? "s" : ""}` : "",
    `${Math.round(plant.capacity_mw).toLocaleString()} MW`,
    plant.operator,
  ].filter(Boolean);
  let compare = `<button class="compare-btn">⇄ Compare with another plant</button>`;
  if (state.picking) {
    compare = `<p class="picking">Click a second plant on the map, or search for it above.
      <button class="cancel-compare">Cancel</button></p>`;
  } else if (state.compare) {
    compare = `<p class="vs"><span class="swatch main"></span>${esc(plant.name)} <span class="muted">vs</span>
      <span class="swatch other"></span>${esc(state.compare.name)}
      <button class="clear-compare" aria-label="Stop comparing">✕</button></p>`;
  }
  document.getElementById("plant-info").innerHTML = `
    <button class="back">← All plants</button>
    <h2 class="plant-name"><span class="dot big" style="background:${rampColor(plant.capacityShare ?? 0.5)}"></span>${esc(plant.name)}</h2>
    <ul class="facts">${facts.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
    ${coolingCard(plant)}
    ${compare}`;
  // Offer "Show more" only when the legal reference does not fit on one line.
  const legal = document.querySelector("#plant-info .legal-text");
  if (legal && legal.scrollHeight > legal.clientHeight + 1) legal.nextElementSibling.hidden = false;
}

// Cooling set-up and the river temperature limits the plant must respect.
function coolingCard(plant) {
  const missing = plant.cooling_data_flag === "missing";
  const num = (v, digits = 0) => (v == null ? null : Number(v).toLocaleString(undefined, { maximumFractionDigits: digits }));
  const item = (icon, label, value, hint = "") => `
    <div class="cool-item"><span class="cool-icon" aria-hidden="true">${icon}</span>
      <div><dt>${label}</dt><dd>${value ?? `<span class="muted">Unknown</span>`}${hint ? `<small>${hint}</small>` : ""}</dd></div></div>`;
  const heat = plant.heat_to_river_mw_th == null ? null
    : `${num(plant.heat_to_river_mw_th)} MW<sub>th</sub>`;
  const share = plant.alpha == null ? "" : `${num(plant.alpha * 100)}% of condenser heat`;
  return `
    <section class="cooling">
      <h3>Cooling &amp; river limits</h3>
      <dl class="cool-grid">
        ${item("❄", "Cooling type", plant.cooling_type ? esc(plant.cooling_type) : null, missing ? "no JRC cooling data" : "")}
        ${item("≈", "Cooling water", plant.water_type ? esc(plant.water_type) : null)}
        ${item("♨", "Heat to the river", heat, share)}
        ${item("🌡", "Max temperature downstream", plant.temp_limit_c == null ? null : `${num(plant.temp_limit_c, 1)} °C`)}
        ${item("↑", "Max warming of the river", plant.temp_change_limit_c == null ? null : `+${num(plant.temp_change_limit_c, 1)} °C`)}
        ${item("§", "Regulation level", plant.regulation_level ? esc(plant.regulation_level) : null,
          !plant.regulation_level || plant.regulation_level === "No limit found" ? "no regulation level data" : "")}
      </dl>
      ${plant.temp_limit_sources ? `
      <div class="legal">
        <p class="provisional legal-text">Legal reference: ${esc(plant.temp_limit_sources)}</p>
        <button class="legal-toggle" aria-expanded="false" hidden>Show more</button>
      </div>` : ""}
    </section>`;
}

// Search box: type to filter, arrow keys to move, Enter to open, Escape to close.
const searchInput = document.getElementById("search");
const searchResults = document.getElementById("search-results");
let searchIndex = 0;

function closeSearch() {
  searchResults.hidden = true;
  searchInput.value = "";
}

function renderSearch() {
  const q = searchInput.value.trim().toLowerCase();
  const hits = q ? plantList.filter((p) => `${p.name} ${p.country}`.toLowerCase().includes(q)).slice(0, 8) : [];
  searchIndex = Math.min(searchIndex, Math.max(hits.length - 1, 0));
  searchResults.innerHTML = hits.length
    ? hits.map((p, i) => `<li role="option" data-id="${esc(p.id)}" aria-selected="${i === searchIndex}">
        <span class="dot" style="background:${rampColor(p.capacityShare)}"></span>${esc(p.name)}<small>${esc(p.country)}</small></li>`).join("")
    : q ? `<li class="empty">No plant matches “${esc(q)}”</li>` : "";
  searchResults.hidden = !q;
  return hits;
}

searchInput.addEventListener("input", () => { searchIndex = 0; renderSearch(); });
searchInput.addEventListener("keydown", (e) => {
  const hits = renderSearch();
  if (e.key === "ArrowDown") { searchIndex = Math.min(searchIndex + 1, hits.length - 1); renderSearch(); e.preventDefault(); }
  if (e.key === "ArrowUp") { searchIndex = Math.max(searchIndex - 1, 0); renderSearch(); e.preventDefault(); }
  if (e.key === "Enter" && hits[searchIndex]) selectPlant(hits[searchIndex]);
  if (e.key === "Escape") closeSearch();
});
searchResults.addEventListener("mousedown", (e) => {
  const li = e.target.closest("[data-id]");
  if (li) selectPlant(plantList.find((p) => p.id === li.dataset.id));
});
searchInput.addEventListener("blur", () => setTimeout(() => { searchResults.hidden = true; }, 150));

const fetchPlant = (plant) =>
  getJSON(`/api/plants/${encodeURIComponent(plant.id)}/discharge?track=${state.track}`);

async function loadCharts() {
  const charts = document.getElementById("charts");
  if (!state.plant) return;
  const request = ++state.request; // ignore responses for a plant or tab that is no longer selected
  charts.innerHTML = `<div class="card skeleton"></div><div class="card skeleton"></div>`;
  let data, other;
  try {
    [data, other] = await Promise.all([fetchPlant(state.plant), state.compare ? fetchPlant(state.compare) : null]);
  } catch (err) {
    if (request === state.request) charts.innerHTML = `<p class="message error">Could not load data: ${esc(err.message)}</p>`;
    return;
  }
  if (request !== state.request) return;
  charts.innerHTML = "";
  linked.length = 0;

  const withData = data.sources.filter((s) => s.series.length);
  const missing = data.sources.filter((s) => !s.series.length);
  const otherSource = (key) => other?.sources.find((o) => o.source === key && o.series.length);
  if (state.track === 1) {
    for (const s of withData) {
      const q = quantityOf(s);
      const o = otherSource(s.source);
      const curtail = q.key === "curtailment";
      const traces = curtail ? curtailmentTraces(s, q, state.plant, o ? state.plant.name : null) : timeTraces(s, q, o ? state.plant.name : null);
      if (o) traces.push(curtail ? curtailmentTraces(o, q, state.compare, state.compare.name, true)[0] : compareTrace(o, q));
      // An invisible point on the % axis so Plotly draws that axis.
      if (curtail && !o) traces.push({ x: [s.series[0].time], y: [0], yaxis: "y2", mode: "markers", opacity: 0, hoverinfo: "skip", showlegend: false });
      addChart(charts, {
        title: q.name, badge: badgeOf(s), source: s, quantity: q, traces,
        ...(curtail && !o ? capacityAxes(state.plant.capacity_mw) : {}),
        subtitle: s.forecast_run ? `${s.label} · run of ${new Date(s.forecast_run).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}` : s.label,
        xaxis: { type: "date", tickformat: "%d %b", hoverformat: "%a %d %b %Y", ...rangeButtons(s) },
        shapes: [...todayMarker(s), ...limitLine(q)], stats: [[s, o ? state.plant.name : null], ...(o ? [[o, state.compare.name]] : [])],
      });
    }
    if (other && withData.length && !withData.some((s) => otherSource(s.source))) {
      charts.insertAdjacentHTML("beforeend", `<p class="message">${esc(state.compare.name)} has no data in these sources.</p>`);
    }
  } else if (withData.length) {
    // Overlay all scenarios on one calendar-year axis so years like 2003 and 2045 compare directly.
    // When comparing, each plant gets its own chart on the same y range.
    const q = quantityOf(withData[0]);
    const plants = [[state.plant, withData], ...(other ? [[state.compare, other.sources.filter((s) => s.series.length)]] : [])]
      .filter(([, sources]) => sources.length);
    const values = plants.flatMap(([, sources]) => sources.flatMap((s) => s.series.map((p) => p.value)));
    const yrange = other ? [q.zero ? 0 : Math.min(...values), Math.max(...values) * 1.05] : undefined;
    for (const [plant, sources] of plants) {
      addChart(charts, {
        title: other ? `${q.name} · ${plant.name}` : `${q.name} by scenario`,
        subtitle: "Each year drawn over the same January–December axis. Click a legend entry to hide it, double-click to show only that one.",
        source: sources[0], quantity: q, traces: sources.map(dayOfYearTrace), yrange,
        xaxis: { type: "date", tickformat: "%b", hoverformat: "%d %b", dtick: "M1", range: ["2000-01-01", "2000-12-31"] },
      });
    }
  }
  if (missing.length) {
    charts.insertAdjacentHTML("beforeend", `<p class="message">No data for this plant yet: ${missing.map((s) => esc(s.label)).join(", ")}.</p>`);
  }
  if (!data.sources.length) charts.innerHTML = `<p class="message">No data sources for this track yet.</p>`;
}

// Charts of the current plant share a crosshair and zoom. `syncing` stops the
// programmatic hover/relayout on one chart from echoing back to the others.
const linked = [];
let syncing = false;

function linkChart(div, extent) {
  const entry = { div, extent };
  linked.push(entry);
  const others = () => linked.filter((l) => l !== entry && document.body.contains(l.div));
  const toMs = (gd, x) => gd._fullLayout.xaxis.d2c(x);

  div.on("plotly_hover", (ev) => {
    if (ev.event?.synthetic) return;
    for (const l of others()) {
      try { Plotly.Fx.hover(l.div, { xval: toMs(l.div, ev.points[0].x), synthetic: true }); } catch { /* point outside this chart */ }
    }
  });
  div.on("plotly_unhover", (ev) => {
    if (ev?.event?.synthetic) return;
    for (const l of others()) Plotly.Fx.unhover(l.div);
  });
  div.on("plotly_relayout", (ev) => {
    if (syncing) return;
    let update;
    if (ev["xaxis.autorange"]) update = { "xaxis.autorange": true };
    const r = ev["xaxis.range"] || (ev["xaxis.range[0]"] !== undefined && [ev["xaxis.range[0]"], ev["xaxis.range[1]"]]);
    if (r) update = { "xaxis.range": r };
    if (!update) return;
    // Only zoom charts whose data overlaps the new window (forecast and 2022 reanalysis do not).
    const targets = others().filter((l) => !r ||
      (toMs(div, r[0]) <= l.extent[1] && toMs(div, r[1]) >= l.extent[0]));
    syncing = true;
    Promise.all(targets.map((l) => Plotly.relayout(l.div, update))).finally(() => { syncing = false; });
  });
}

// Quick zoom buttons for series longer than two weeks.
function rangeButtons(s) {
  const days = (new Date(s.series[s.series.length - 1].time) - new Date(s.series[0].time)) / 86400000;
  if (days <= 14) return {};
  return {
    rangeselector: {
      x: 1, xanchor: "right", y: 1.02, yanchor: "bottom",
      bgcolor: token("--bg"), activecolor: token("--accent-soft"), bordercolor: token("--border"), borderwidth: 1,
      font: { size: 11, color: token("--text-secondary") },
      buttons: [
        { count: 7, label: "7 d", step: "day", stepmode: "backward" },
        { count: 14, label: "14 d", step: "day", stepmode: "backward" },
        { count: 1, label: "1 m", step: "month", stepmode: "backward" },
        { step: "all", label: "All" },
      ],
    },
  };
}

function badgeOf(s) {
  if (s.forecast_run || /forecast/.test(s.source)) return "Forecast";
  if (/reanalysis|hist/.test(s.source)) return "Past";
  return "";
}

function addChart(parent, { title, badge, subtitle, source, quantity, traces, xaxis, yaxis = {}, yaxis2, yrange, shapes = [], stats = [] }) {
  const block = document.createElement("section");
  block.className = `card accent-${quantity.key}`;
  const cell = source.cell
    ? `River cell ${source.cell.lat.toFixed(2)}° N, ${source.cell.lon.toFixed(2)}° E · ${source.cell.distance_km.toFixed(1)} km from plant`
    : "";
  block.innerHTML = `
    <header class="card-head">
      <h3>${esc(title)}</h3>${badge ? `<span class="badge">${esc(badge)}</span>` : ""}
    </header>
    <p class="sub">${esc(subtitle)}</p>
    ${source.warning ? `<p class="warning">${esc(source.warning)}</p>` : ""}
    ${stats.map(([src, label], i) => statsRow(src, quantity, label, i)).join("")}
    <div class="chart" role="img" aria-label="${esc(`${title}: ${subtitle}`)}"></div>
    ${cell ? `<p class="cell">${esc(cell)}</p>` : ""}`;
  parent.appendChild(block);

  const unit = quantity.unit ? ` (${quantity.unit})` : "";
  const showLegend = traces.filter((t) => t.showlegend !== false).length > 1;
  const chartDiv = block.querySelector(".chart");
  if (showLegend) chartDiv.classList.add("tall");
  const axisCommon = {
    gridcolor: token("--grid"), linecolor: token("--axis"), zeroline: false,
    tickfont: { color: token("--muted") }, ticks: "", showline: true,
  };
  Plotly.newPlot(chartDiv, traces, {
    font: { family: token("--font"), size: 12, color: token("--text-secondary") },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 56, r: yaxis2 ? 56 : 12, t: xaxis.rangeselector || showLegend ? 40 : 8, b: 24 },
    hovermode: "x unified",
    hoverlabel: { bgcolor: token("--surface"), bordercolor: token("--border-strong"), font: { color: token("--text") } },
    xaxis: { ...axisCommon, ...xaxis, showspikes: true, spikemode: "across", spikethickness: 1,
             spikecolor: token("--axis"), spikedash: "solid",
             // Drag the handles under the chart to pick a time window.
             rangeslider: { visible: true, thickness: 0.1, bgcolor: token("--bg"), bordercolor: token("--border"), borderwidth: 1 } },
    yaxis: { ...axisCommon, title: { text: `${quantity.name}${unit}`, font: { color: token("--muted") } },
             rangemode: quantity.zero ? "tozero" : "normal", tickformat: quantity.format.replace(/\.\d+f/, ".0f"),
             ...(yrange ? { range: yrange } : {}), ...yaxis },
    ...(yaxis2 ? { yaxis2: { ...axisCommon, ...yaxis2, title: { ...yaxis2.title, font: { color: token("--muted") } } } } : {}),
    legend: { orientation: "h", x: 0, y: 1.02, yanchor: "bottom", font: { color: token("--text-secondary") } },
    showlegend: showLegend,
    shapes: shapes.filter((s) => s.type),
    annotations: shapes.filter((s) => s.text),
  }, {
    responsive: true, displaylogo: false,
    modeBarButtons: [["toImage", "resetScale2d"]],
    toImageButtonOptions: { filename: `${state.plant.name}_${source.source}`.replace(/\W+/g, "_") },
  });
  const xs = traces.flatMap((t) => t.x).filter(Boolean).map((x) => chartDiv._fullLayout.xaxis.d2c(x));
  linkChart(chartDiv, [Math.min(...xs), Math.max(...xs)]);
}

function fmt(value, quantity) {
  const decimals = Number(quantity.format.match(/\.(\d+)f/)?.[1] ?? 0);
  return value.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function statsRow(source, quantity, label, index) {
  const s = source.series;
  const last = s[s.length - 1];
  const min = s.reduce((a, b) => (b.value < a.value ? b : a));
  const max = s.reduce((a, b) => (b.value > a.value ? b : a));
  const day = (p) => new Date(p.time).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  const tile = (label, p) => `<div><dt>${label}</dt><dd>${fmt(p.value, quantity)}<small> ${esc(quantity.unit)}</small></dd><dd class="when">${day(p)}</dd></div>`;
  const head = label ? `<p class="stats-label"><span class="swatch ${index ? "other" : "main"}"></span>${esc(label)}</p>` : "";
  return `${head}<dl class="stats">${tile(source.forecast_run ? "Last forecast day" : "Last day", last)}${tile("Lowest", min)}${tile("Highest", max)}</dl>`;
}

// The selected plant's maximum downstream temperature, drawn on water temperature charts.
function limitLine(q) {
  const limit = state.plant?.temp_limit_c;
  if (q.key !== "temperature" || limit == null) return [];
  return [
    { type: "line", xref: "paper", yref: "y", x0: 0, x1: 1, y0: limit, y1: limit,
      line: { color: token("--limit"), width: 1.5, dash: "dash" } },
    { text: `Max downstream ${limit} °C`, xref: "paper", yref: "y", x: 0, y: limit, xanchor: "left", yanchor: "bottom",
      showarrow: false, font: { size: 11, color: token("--limit") } },
  ];
}

function todayMarker(s) {
  const today = new Date().toISOString().slice(0, 10);
  const first = s.series[0].time.slice(0, 10), last = s.series[s.series.length - 1].time.slice(0, 10);
  if (today < first || today > last) return [];
  return [
    { type: "line", xref: "x", yref: "paper", x0: today, x1: today, y0: 0, y1: 1,
      line: { color: token("--muted"), width: 1, dash: "dot" } },
    { text: "Today", xref: "x", yref: "paper", x: today, y: 1, yanchor: "bottom", xanchor: "left",
      showarrow: false, font: { size: 11, color: token("--muted") } },
  ];
}

function timeTraces(s, q, plantName = null) {
  const x = s.series.map((p) => p.time);
  const color = token(q.color);
  const hasRange = s.series[0].p10 !== undefined;
  const unit = q.unit ? ` ${q.unit}` : "";
  const traces = [];
  if (hasRange) {
    traces.push(
      { x, y: s.series.map((p) => p.p90), mode: "lines", line: { width: 0 }, showlegend: false, hoverinfo: "skip" },
      { x, y: s.series.map((p) => p.p10), mode: "lines", line: { width: 0 }, fill: "tonexty",
        fillcolor: withAlpha(color, 0.18), name: "Likely range (10–90%)", hoverinfo: "skip", showlegend: !plantName },
    );
  }
  traces.push({
    x, y: s.series.map((p) => p.value), mode: "lines", line: { color, width: 2, shape: q.shape ?? "spline", smoothing: 0.4 },
    name: plantName ?? (hasRange ? "Ensemble median" : s.label),
    customdata: hasRange ? s.series.map((p) => [p.p10, p.p90]) : undefined,
    hovertemplate: hasRange
      ? `Median <b>%{y:${q.format}}</b>${unit}<br>Range %{customdata[0]:${q.format}}–%{customdata[1]:${q.format}}${unit}<extra></extra>`
      : `<b>%{y:${q.format}}</b>${unit}<extra></extra>`,
  });
  return traces;
}

// Curtailment as MW to cut, with the share of the plant's capacity in the hover. The comparison
// plant is a single dashed line, like compareTrace.
function curtailmentTraces(s, q, plant, plantName = null, compare = false) {
  const x = s.series.map((p) => p.time);
  const capacity = plant.capacity_mw;
  const color = token(compare ? "--series-compare" : q.color);
  return [{
    x, y: s.series.map((p) => p.value), mode: "lines+markers", name: plantName ?? s.label,
    line: { color, width: 2, dash: compare ? "dash" : "solid" },
    marker: { color, size: 7, line: { color: token("--surface"), width: 1.5 } },
    ...(compare ? {} : { fill: "tozeroy", fillcolor: withAlpha(color, 0.15) }),
    customdata: s.series.map((p) => (capacity ? (100 * p.value) / capacity : null)),
    hovertemplate: `<b>%{y:${q.format}} ${q.unit}</b>${capacity ? " · %{customdata:.0f}% of capacity" : ""}<extra></extra>`,
  }];
}

// Left axis in MW to cut, right axis in % of capacity, both from 0 to the plant's full capacity.
function capacityAxes(capacity) {
  if (!capacity) return {};
  const steps = [0, 0.25, 0.5, 0.75, 1];
  return {
    yaxis: { title: { text: "MW to cut" }, range: [0, capacity], tickvals: steps.map((f) => f * capacity),
             ticktext: steps.map((f) => Math.round(f * capacity).toLocaleString()) },
    yaxis2: { title: { text: "% of capacity" }, overlaying: "y", side: "right", range: [0, 100], tickvals: steps.map((f) => f * 100),
              ticksuffix: "%", showgrid: false, fixedrange: true },
  };
}

// The comparison plant: one dashed line in its own colour, no ensemble band.
function compareTrace(s, q) {
  const x = s.series.map((p) => p.time);
  const unit = q.unit ? ` ${q.unit}` : "";
  return {
    x, y: s.series.map((p) => p.value), mode: "lines", name: state.compare.name,
    line: { color: token("--series-compare"), width: 2, dash: "dash", shape: q.shape ?? "spline", smoothing: 0.4 },
    hovertemplate: `<b>%{y:${q.format}}</b>${unit}<extra></extra>`,
  };
}

function dayOfYearTrace(s) {
  const style = SCENARIO_STYLE[s.source] || { color: "--series-3", dash: "solid" };
  const q = quantityOf(s);
  const years = [...new Set(s.series.map((p) => p.time.slice(0, 4)))];
  // Put every point on the leap year 2000 and break the line between years, so December
  // does not join up with the next January.
  const x = [], y = [];
  let prev = null;
  for (const p of s.series) {
    const md = p.time.slice(5, 10);
    if (prev !== null && md < prev) { x.push(null); y.push(null); }
    x.push(`2000-${md}`); y.push(p.value);
    prev = md;
  }
  const yearText = years.length > 3 ? `${years[0]}–${years[years.length - 1]}` : years.join(", ");
  return {
    x, y, mode: "lines", connectgaps: false,
    name: `${s.label} (${yearText})`,
    line: { color: token(style.color), width: 2, dash: style.dash },
    hovertemplate: `%{y:${q.format}} ${q.unit}<extra>${esc(s.label)}</extra>`,
  };
}

function withAlpha(hex, alpha) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${alpha})`;
}

for (const button of document.querySelectorAll(".tabs button")) {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b === button));
    state.track = Number(button.dataset.track);
    loadCharts();
  });
}

dark.addEventListener("change", loadCharts); // re-read the colour tokens
map.on("load", loadPlants);
