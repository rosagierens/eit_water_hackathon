# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project goal

An application for the energy sector that shows how **droughts and high temperatures affect power plant electricity generation**. Thermal plants, starting with nuclear, lose output when cooling water is scarce or too warm, or when environmental limits on discharge temperature apply.

The application has two tracks:

1. **Short-term forecast (operations).** Forecast generation constraints for the next few days from weather and river forecasts (air temperature, water temperature, river discharge). Verify the forecast skill against past observations, for example by hindcasting past heatwaves or droughts and comparing with observed curtailments.
2. **Climate projections (planning).** Use future climate projections under different scenarios (for example SSP/RCP pathways) to estimate how often and how severely plants will be constrained in coming decades. This supports investment and adaptation planning.

Keep both tracks on a shared core: one plant dataset, one set of environmental-variable loaders, and one model that maps environmental conditions to a generation impact. Only the input data source (forecast or observation vs. projection) and the time horizon differ.

## Repository layout

- `app/` is the user interface: `core/` (data layer, plain Python), `api/` (FastAPI), and `web/` (static MapLibre/Plotly page). Run `python -m app --reload` from the repository root; see `app/README.md`. Keep the API as the contract between backend and frontend. Track 1 (operations) comes first.
- `data/raw/<source>/` holds source files as obtained, including the GEM August 2026 workbook under `global_nuclear_power_tracker/` and JRC Open Power Plants Database files under `jrc_open_power_plants/`. Source notes and citations belong beside the source files.
- `data/interim/<source>/` holds reproducible filtered and converted outputs. GEM's `Operating_Europe.csv` and JRC's `Nuclear_commissioned.csv` are examples. Data that combines sources gets its own folder: `data/interim/nuclear_units/` holds the GEM-JRC reactor table and the unfiltered facility table.
- `data/raw/project_parameters/` holds hand-made parameter tables, such as `cooling_type_alpha.csv` (share of cooling heat reaching the river per JRC cooling type). Keep it identical to Table 1 in `methodology_cooling_constrain.md`.
- `data/app_input/` holds application-ready data. The plant loader reads `facilities.csv` here: one row per GEM location, with capacities summed over operating units and a heat-weighted `Alpha`. Seawater facilities are left out in the last step (`EXCLUDED_WATER_TYPES`). Ukraine and Belarus have no cooling data (`Cooling_data_flag` = `missing`).
- `data_processing/plants/` contains the plant pipeline, run in this order: `process_gem_units.py`, `process_jrc_units.py`, `merge_units.py`, `build_facilities.py`. Status comes from GEM; JRC supplies only cooling and water type. `data_processing/river_discharge/` contains GloFAS, C3S hydrology, and HydroLand downloaders. `data_processing/air_temperature/` contains ECMWF, ERA5-Land, EURO-CORDEX, and Climate DT downloaders. Sample runners and dataset notes are beside their scripts. Prefer small downloads while the project is at the sample-data stage.

The discharge reader in `app/core/discharge.py` still points to the former download location. New downloads under `data/raw/<source>/` will not appear in its charts until that reader is migrated separately.

## Conventions

- Every new source dataset gets notes with its source, access date, citation, licence, and processing caveats.
- Never modify files in `data/raw/` in place. Write source-specific processed results to `data/interim/<source>/` and application-ready outputs to `data/app_input/`.
- Use gridded data formats (NetCDF) through `netCDF4` and `cftime`. Keep `requirements.txt` updated with pinned versions whenever you add a dependency.
- Large data files should not be committed unless they are small reference tables. Document how to download them instead.

## Environment

```bash
source .venv/bin/activate
pip install -r requirements.txt
```
