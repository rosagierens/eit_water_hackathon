# Environmental data for the app

Daily river discharge, river water temperature and curtailment at every plant in `../facilities.csv` (35 freshwater-cooled plants). Built by `data_processing/environment/build_all.py`. Do not edit these files by hand.

**Current scope: track 1 (operations).** The tables hold the latest **forecast**, plus the **reanalysis**, the recent past used to verify the forecast. Climate scenarios (track 2) are left out for now. Their Europe-wide grids are kept in `data/interim/` and can be added with `build_app_input.py --tracks 1 2`, which also writes `plant_statistics.parquet`.

**Typical use:** load the tables once (well under a second), then filter by `location_id` when a plant is clicked (about 10 ms). A filtered read straight from disk is just as fast: `pd.read_parquet(path, filters=[("location_id", "==", id)])`.

## Files

| File | Content |
| --- | --- |
| `discharge.parquet` | Daily river discharge (m³/s) |
| `water_temperature.parquet` | Daily river water temperature (°C) at the same river cell |
| `curtailment.parquet` | Daily curtailment (MW) from that discharge and water temperature (see `methodology_cooling_constrain.md`) |
| `plant_cells.csv` | The river grid cell used per plant, and how trustworthy it is (`status`) |
| `sources.json` | Description of every `dataset_id`: label, period, units, method, `status_values` |

Datasets at the moment:

| `dataset_id` | Variable | What it is |
| --- | --- | --- |
| `glofas_forecast` | discharge | GloFAS forecast, next ~10 days (`forecast_run` = issue date) |
| `wt_forecast` | water temperature | From GloFAS forecast + ECMWF HRES air temperature |
| `glofas_reanalysis` | discharge | GloFAS reanalysis (ERA5-driven), past period |
| `wt_reanalysis` | water temperature | From GloFAS reanalysis + ERA5-Land air temperature |
| `curtailment_forecast` | curtailment | From `glofas_forecast` + `wt_forecast` (days where both exist) |
| `curtailment_reanalysis` | curtailment | From `glofas_reanalysis` + `wt_reanalysis` |

### `discharge.parquet` and `water_temperature.parquet` (long format, one row per plant, day, dataset, member)

| Column | Meaning |
| --- | --- |
| `location_id` | Plant id, as in `facilities.csv` (`Location_ID`) |
| `date` | Calendar day (UTC) the daily mean describes |
| `dataset_id` | See the table above |
| `source`, `scenario`, `track` | `glofas`; `forecast` or `reanalysis`; `1` |
| `member` | Ensemble member (0 = control / single run) |
| `forecast_run` | Forecast issue date; empty for the reanalysis |
| `value` | m³/s (discharge) or °C (water temperature) |
| `method`, `calibrated` | Water temperature only: how it was derived; `calibrated = false` for now |

### `curtailment.parquet`

Same columns as the two tables above, with `value` = **curtailed output in MW** (0 = full output possible). Extra columns:

| Column | Meaning |
| --- | --- |
| `available_fraction` | Share of capacity the river allows (`f`, 0–1) |
| `available_mw` | Output still possible (MW) |
| `q_heat_max_mw` | Heat the river can take before reaching the limit (MW thermal; negative = river already above `T_limit`) |
| `limiting_limit` | Which permit limit binds: `T_limit` (absolute downstream temperature) or `dT_limit` (warming by the plant) |
| `river_cell_status` | Status of the river cell behind the inputs (see `plant_cells.csv`). **`small_stream` makes the curtailment meaningless**: the model has no real river there, so it shows near-full curtailment. |
| `method`, `calibrated` | `cooling-constraint-v1`; `calibrated = false` because the water temperature input is uncalibrated |

Plants without curtailment rows lack an input in `facilities.csv`: no temperature limit (`Temp_limit` and `Temp_change_limit` empty: Doel, Almaraz, Cofrentes) or no cooling data (`Cooling_data_flag = missing`: Astravets, Ukraine). The parameters used per plant are recorded in `data/interim/curtailment/curtailment_inputs.csv`.

### `plant_cells.csv`: check `status` before showing data

One row per plant: the GloFAS grid cell (`row`, `col`, `cell_lat`, `cell_lon`), its `distance_km` from the plant, its `mean_discharge`, `cooling_water` (from `Water_type` in `facilities.csv`; `unknown` where that is empty) and `status`:

| `status` | Meaning for the app |
| --- | --- |
| `ok` | Main river near the plant |
| `extended_search` | River found only within 20 km (the model's river runs further from the plant), e.g. Cernavodă |
| `small_stream` | No river ≥ 10 m³/s nearby in this model. Show with a warning or hide. Currently Dukovany, Mochovce, Cofrentes, Trillo, Khmelnitski. |
| `sea_cooled` | Not used now (`facilities.csv` excludes sea-cooled plants) |

The same cell is used for the forecast and the reanalysis, so they are directly comparable.

## Caveats (current sample data)

- **Water temperature is uncalibrated** (`method = air2stream-4p-uncalibrated-v0`): expect peaks a few °C too low. See `methodology_water_temperature.md`.
- **The water temperature forecast starts in equilibrium** with the first forecast week, because no observed water temperature is used yet. It covers the days where the GloFAS and ECMWF forecasts overlap (9 days now).
- **Curtailment follows its inputs.** Low model discharge at small or regulated rivers drives most of it, through the `dT_limit` (e.g. Temelín, Cattenom in the October forecast), and the uncalibrated water temperature affects the `T_limit` cases. Treat the values as indicative until discharge and water temperature are checked against measurements.
- **The reanalysis is a sample:** July–August 2022 only. Rerun the pipeline after downloading more months.
