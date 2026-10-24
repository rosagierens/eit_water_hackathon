# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project goal

An application for the energy sector that shows how **droughts and high temperatures affect power plant electricity generation**. Thermal plants, starting with nuclear, lose output when cooling water is scarce or too warm, or when environmental limits on discharge temperature apply.

The application has two tracks:

1. **Short-term forecast (operations).** Forecast generation constraints for the next few days from weather and river forecasts (air temperature, water temperature, river discharge). Verify the forecast skill against past observations, for example by hindcasting past heatwaves or droughts and comparing with observed curtailments.
2. **Climate projections (planning).** Use future climate projections under different scenarios (for example SSP/RCP pathways) to estimate how often and how severely plants will be constrained in coming decades. This supports investment and adaptation planning.

Keep both tracks on a shared core: one plant dataset, one set of environmental-variable loaders, and one model that maps environmental conditions to a generation impact. Only the input data source (forecast or observation vs. projection) and the time horizon differ.

## Repository layout

- `data_in/` holds raw source data **as accessed**, plus notes, citations, and the scripts that do the first cleaning steps. See `README.md`.
  - `data_in/nucler_plants/` contains the Global Nuclear Power Tracker (GEM, Aug 2026, CC BY 4.0) at unit level. `notes.txt` lists the relevant columns (coordinates, capacities, GEM location ID). Filter to `Status == "operating"` and `Region == "Europe"`, excluding `Country/Area == "Russia"`.
  - `data_in/environmental_variables/` is for meteorological and hydrological inputs (temperature, river discharge, water temperature).
    - `river_discharge/` has two download scripts. `download_river_discharge.py` has three subcommands: `forecast` (GloFAS forecast), `historical` (GloFAS reanalysis, used for verification) and `projection` (C3S EURO-CORDEX hydrology projections, used for scenario spread, the period after 2050 and water temperature). `download_hydroland.py` gets the main projection source: DestinE Climate DT HydroLand discharge (`Qrouted`, 1990-2049) from the DestinE Data Lake, which needs a DESP login. `download_samples.sh` fetches a small comparable sample from every source: 2003 historical, the 2022 drought, and 2045 in the HydroLand SSP3-7.0 and C3S RCP2.6/4.5/8.5 scenarios. The project is currently at the sample-data stage, so prefer small downloads. `readme.txt` explains why each dataset was chosen and how to access it. Downloads go to `raw/`, which git ignores.
    - `air_temperature/` has `download_air_temperature.py` with four subcommands: `forecast` (ECMWF open data HRES/ENS, no account needed), `observed` (ERA5-Land daily max/mean), `cordex` (EURO-CORDEX EC-EARTH/RCA4, matching the C3S discharge chain) and `climatedt` (DestinE Climate DT IFS-NEMO, the same runs as HydroLand, extracted at each plant via Polytope). It also has `download_samples.sh` and a `readme.txt`.
- `app/` is the user interface: `core/` (data layer, plain Python), `api/` (FastAPI) and `web/` (static page: MapLibre GL JS on the open-source OpenFreeMap basemap, plus Plotly). Run it with `python -m app --reload` (port 8050; `--port` or `APP_PORT` to change); see `app/README.md`. The API is the contract between backend and frontend, so keep data logic in `core/`, not in `web/`. Track 1 (operations) comes first.
- `data_cleaned/` holds processed outputs that the analysis and the app can use directly. Every file here must be reproducible from `data_in/` by a script.

## Conventions

- Every new dataset in `data_in/` gets a `readme.txt` or `notes.txt` with its source, access date, citation, licence, and processing caveats.
- Never modify raw files in place. Write processed results to `data_cleaned/`.
- Use gridded data formats (NetCDF) through `netCDF4` and `cftime`. Keep `requirements.txt` updated with pinned versions whenever you add a dependency.
- Large data files should not be committed unless they are small reference tables. Document how to download them instead.

## Environment

```bash
source .venv/bin/activate
pip install -r requirements.txt
```
