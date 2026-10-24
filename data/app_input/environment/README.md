# Environmental data for the app

Daily river discharge and river water temperature at every plant in `../facilities.csv`, for every downloaded data source. Built by `data_processing/environment/build_all.py`. Do not edit these files by hand.

**Typical use:** load the tables once at startup (about 0.1 s), then filter by `location_id` when a plant is clicked (about 10 ms). A filtered read straight from disk is just as fast: `pd.read_parquet(path, filters=[("location_id", "==", id)])`.

## Files

| File | Content |
| --- | --- |
| `discharge.parquet` | Daily river discharge (m³/s) |
| `water_temperature.parquet` | Daily river water temperature (°C) at the same river cell |
| `plant_statistics.parquet` | Monthly quantiles of the daily values per plant and dataset (climate track) |
| `plant_cells.csv` | Which grid cell was used per plant and model, and how trustworthy it is (`status`) |
| `sources.json` | Description of every `dataset_id`: label, track, scenario, period, units, method |

### `discharge.parquet` and `water_temperature.parquet` (long format, one row per plant, day, dataset, member)

| Column | Meaning |
| --- | --- |
| `location_id` | Plant id, as in `facilities.csv` |
| `date` | Calendar day (UTC) the daily mean describes |
| `dataset_id` | e.g. `glofas_reanalysis`, `c3s_rcp_4_5`, `wt_rcp_4_5` (see `sources.json`) |
| `source` | Model behind the value: `glofas`, `hydroland`, `c3s_hydrology` |
| `scenario` | `forecast`, `reanalysis`, `hist`, `historical`, `SSP3-7.0`, `rcp_2_6`, `rcp_4_5`, `rcp_8_5` |
| `track` | 1 = operations (forecast + past for verification), 2 = planning (climate scenarios) |
| `member` | Ensemble member (0 = control / single run) |
| `forecast_run` | Forecast issue date; empty for non-forecasts |
| `value` | m³/s (discharge) or °C (water temperature) |
| `method`, `calibrated` | Water temperature only: how it was derived; `calibrated = false` for now |

### `plant_statistics.parquet`

`location_id, dataset_id, variable, month, quantile, value, n_days`. These are quantiles (0.01 … 0.99) of the daily values in each calendar month. **Chance of exceeding a limit L** in a month ≈ 1 − (the quantile level at which `value` crosses L), found by interpolating between the quantile rows. `n_days` shows how many days the numbers are based on.

### `plant_cells.csv` — check `status` before showing data

| `status` | Meaning for the app |
| --- | --- |
| `ok` | Main river near the plant |
| `extended_search` | River found only within 20 km (the model's river runs further from the plant) |
| `small_stream` | No river ≥ 10 m³/s nearby in this model. Show with a warning or hide. |
| `sea_cooled` | The plant cools with sea or estuary water (JRC). River values are for reference only. |

The cell is chosen once per model and used for all its scenarios and the forecast, so scenarios are directly comparable. `cooling_water` comes from the JRC plant table (`unknown` = not in JRC).

## Caveats (current sample data)

- **Water temperature is uncalibrated** (`method = air2stream-4p-uncalibrated-v0`): expect peaks a few °C too low. See `methodology_water_temperature.md`.
- **Short periods:** each scenario currently covers only 1 month to 1 year, so the statistics are placeholders. The format stays the same when longer periods are downloaded.
- **HydroLand has discharge only.** Its matching air temperature (Climate DT) has only 00 UTC values so far.
- **Not covered by any model:** Trillo (upper Tagus) and Dukovany (reservoir) are `small_stream` in all models.

For new locations (planning mode), use the gridded data in `data/interim/<source>/europe_daily/` and `.../statistics/` (see `data_processing/environment/README.md`).
