# App

A minimal web app: a map of Europe's operating nuclear plants. Clicking a plant shows the river discharge at that plant from every data source that has been downloaded.

- **Operations · next days** (track 1, operators and traders): the latest GloFAS forecast (with the ensemble range if downloaded) and the GloFAS reanalysis for the past period used to verify it.
- **Planning · climate scenarios** (track 2, planners and investors): HydroLand and C3S scenarios overlaid on a day-of-year axis, so different years and scenarios can be compared directly.

## Run

```bash
python data_in/nucler_plants/clean_plants.py      # once: builds data_cleaned/nuclear_plants_europe_units.csv
python -m app --reload                            # from the repo root; --port N to change the port
```

Open http://127.0.0.1:8050. The interactive API docs are at http://127.0.0.1:8050/docs.
If port 8050 is busy too, use `python -m app --port 8060` or set `APP_PORT`.
Sources without downloaded data show "No data downloaded for this source yet". See `data_in/environmental_variables/river_discharge/readme.txt` for how to download them.

## Structure

| Folder      | Role                                                                                   |
|-------------|----------------------------------------------------------------------------------------|
| `core/`     | Plain Python data layer: plant table and discharge time series at a plant. No web code, so notebooks or other tools can use it too. |
| `api/`      | FastAPI JSON API (`/api/plants`, `/api/sources`, `/api/plants/{id}/discharge?track=1`); also serves `web/`. |
| `web/`      | Static page with no build step: MapLibre GL JS map on the open-source OpenFreeMap basemap (OpenStreetMap data, no API key), plus Plotly charts. |

To grow this into the full prototype, keep the API as the contract. A richer frontend (for example React) can replace `web/` without touching `core/`. New indicators, such as low-flow thresholds or water temperature, go into `core/` with a new API route.

## How the plant's river cell is chosen

On a 5 km grid the nearest cell is often a small side stream. `core/discharge.py` takes the cell with the **highest mean discharge within 10 km** of the plant (`SEARCH_RADIUS_KM`), which is normally the river the plant takes its cooling water from. Each chart shows the chosen cell and its distance. Check it for coastal plants (seawater cooling), and for plants where two rivers meet.

## Known limits

- The file reader finds variable and coordinate names by trying common options. It was tested on synthetic files shaped like GloFAS, HydroLand and C3S output, not yet on the real downloads. If a real file doesn't load, check the names in `DISCHARGE_VARS`, `LAT_NAMES` and `TIME_NAMES`.
- Balakovo, Beloyarsk and Akademik Lomonosov (Russia) are outside the downloaded Europe box (east of 45°E) and show no data.
- Series are read from the NetCDF files on every request. That's fine for sample data, but for full datasets, pre-extract plant time series into `data_cleaned/`.

## Basemap

[OpenFreeMap](https://openfreemap.org) is open source with OpenStreetMap data (ODbL), and needs no API key and has no usage limits. It is rendered with [MapLibre GL JS](https://maplibre.org) (BSD-3). The style is set in `BASEMAP_STYLE` in `web/app.js`: `positron` (default, muted), `liberty` or `bright`. The whole tile stack can be self-hosted later if the prototype needs to run offline or under its own domain. MapLibre stays on 5.x because 6.x only ships as an ES module, which needs a build step.
