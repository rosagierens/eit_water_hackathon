// Map of plants + discharge charts per data source, fed by the JSON API in app/api/main.py.

const state = { track: 1, plant: null };
const SCENARIO_COLORS = {
  hydroland_hist: "#6b6b66", hydroland_ssp370: "#7c3aed",
  c3s_historical: "#9ca3af", c3s_rcp26: "#2563eb", c3s_rcp45: "#d97706", c3s_rcp85: "#dc2626",
};

// Open-source basemap: OpenFreeMap (OpenStreetMap data, no API key) rendered with MapLibre GL JS.
// Other OpenFreeMap styles: "liberty", "bright". The style carries its own attribution.
const BASEMAP_STYLE = "https://tiles.openfreemap.org/styles/positron";

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

async function loadPlants() {
  const plants = await getJSON("/api/plants");
  const byId = Object.fromEntries(plants.map((p) => [p.id, p]));
  map.addSource("plants", {
    type: "geojson",
    data: {
      type: "FeatureCollection",
      features: plants.map((p) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [p.lon, p.lat] },
        properties: { id: p.id, name: p.name, capacity_mw: p.capacity_mw },
      })),
    },
  });
  const radius = ["+", 4, ["/", ["sqrt", ["get", "capacity_mw"]], 12]];
  map.addLayer({
    id: "plants", type: "circle", source: "plants",
    paint: { "circle-radius": radius, "circle-color": "#c2410c", "circle-opacity": 0.85,
             "circle-stroke-color": "#ffffff", "circle-stroke-width": 1 },
  });
  map.addLayer({
    id: "plant-selected", type: "circle", source: "plants", filter: ["==", ["get", "id"], ""],
    paint: { "circle-radius": ["+", radius, 3], "circle-color": "rgba(0,0,0,0)",
             "circle-stroke-color": "#1d1d1b", "circle-stroke-width": 2 },
  });

  const tooltip = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
  map.on("mousemove", "plants", (e) => {
    map.getCanvas().style.cursor = "pointer";
    const p = e.features[0].properties;
    tooltip.setLngLat(e.lngLat).setText(`${p.name} (${Math.round(p.capacity_mw)} MW)`).addTo(map);
  });
  map.on("mouseleave", "plants", () => {
    map.getCanvas().style.cursor = "";
    tooltip.remove();
  });
  map.on("click", "plants", (e) => selectPlant(byId[e.features[0].properties.id]));
}

function selectPlant(plant) {
  state.plant = plant;
  map.setFilter("plant-selected", ["==", ["get", "id"], plant.id]);
  document.getElementById("plant-info").innerHTML = `
    <h2 class="plant-name">${plant.name}</h2>
    <p class="plant-meta">${plant.country} · ${plant.units} unit(s) · ${Math.round(plant.capacity_mw)} MW
      ${plant.operator ? "· " + plant.operator : ""}</p>`;
  loadCharts();
}

async function loadCharts() {
  const charts = document.getElementById("charts");
  if (!state.plant) return;
  charts.innerHTML = `<p class="hint">Loading…</p>`;
  const data = await getJSON(`/api/plants/${state.plant.id}/discharge?track=${state.track}`);
  charts.innerHTML = "";
  if (state.track === 1) {
    data.sources.forEach((s) => addChart(charts, s.label, s, [timeTraces(s)], "Date"));
  } else {
    // Overlay all scenarios on a shared day-of-year axis so years like 2003 and 2045 compare directly.
    const withData = data.sources.filter((s) => s.series.length);
    const missing = data.sources.filter((s) => !s.series.length);
    if (withData.length) {
      addChart(charts, "River discharge by scenario", withData[0],
        withData.map(dayOfYearTrace), "Day of year");
    }
    for (const s of missing) addChart(charts, s.label, s, [], "");
  }
}

function addChart(parent, title, source, traces, xTitle) {
  const block = document.createElement("section");
  block.className = "chart-block";
  const cell = source.cell
    ? `River cell ${source.cell.lat.toFixed(2)}, ${source.cell.lon.toFixed(2)} (${source.cell.distance_km.toFixed(1)} km from plant)`
    : "";
  block.innerHTML = `<h3>${title}</h3><p class="cell">${cell}</p>`;
  parent.appendChild(block);
  if (!traces.length || !traces.flat().length) {
    block.insertAdjacentHTML("beforeend", `<p class="message">${source.message || "No data"}</p>`);
    return;
  }
  const div = document.createElement("div");
  div.className = "chart";
  block.appendChild(div);
  Plotly.newPlot(div, traces.flat(), {
    margin: { l: 56, r: 8, t: 8, b: 40 },
    xaxis: { title: { text: xTitle } },
    yaxis: { title: { text: `Discharge (${source.units || "m³/s"})` }, rangemode: "tozero" },
    legend: { orientation: "h", y: -0.25 },
    showlegend: traces.flat().length > 1,
  }, { displayModeBar: false, responsive: true });
}

function timeTraces(s) {
  if (!s.series.length) return [];
  const x = s.series.map((p) => p.time);
  const traces = [];
  if (s.series[0].p10 !== undefined) {
    traces.push(
      { x, y: s.series.map((p) => p.p90), mode: "lines", line: { width: 0 }, showlegend: false, hoverinfo: "skip" },
      { x, y: s.series.map((p) => p.p10), mode: "lines", line: { width: 0 }, fill: "tonexty",
        fillcolor: "rgba(31,111,178,0.18)", name: "10–90% ensemble range" },
    );
  }
  traces.push({ x, y: s.series.map((p) => p.value), mode: "lines", line: { color: "#1f6fb2", width: 2 },
    name: s.series[0].p10 !== undefined ? "Ensemble median" : s.label });
  return traces;
}

function dayOfYearTrace(s) {
  const doy = (iso) => {
    const d = new Date(iso);
    return Math.floor((d - Date.UTC(d.getUTCFullYear(), 0, 0)) / 86400000);
  };
  const years = [...new Set(s.series.map((p) => p.time.slice(0, 4)))];
  return {
    x: s.series.map((p) => doy(p.time)),
    y: s.series.map((p) => p.value),
    mode: "lines",
    name: `${s.label} (${years.join(", ")})`,
    line: { color: SCENARIO_COLORS[s.source], width: 2 },
  };
}

for (const button of document.querySelectorAll(".tabs button")) {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b === button));
    state.track = Number(button.dataset.track);
    loadCharts();
  });
}

map.on("load", loadPlants);
