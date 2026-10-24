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
  - `data_in/nucler_plants/` contains the Global Nuclear Power Tracker (GEM, Aug 2026, CC BY 4.0) at unit level. `notes.txt` lists the relevant columns (coordinates, capacities, GEM location ID). Filter to `Status == "operating"` and `Region == "Europe"`.
  - `data_in/environmental_variables/` is for meteorological and hydrological inputs (temperature, river discharge, water temperature). It is empty so far.
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
