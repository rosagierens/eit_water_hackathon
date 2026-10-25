# Environmental data pipeline

Turns the downloads from `../river_discharge/` and `../air_temperature/` into one standard format: daily river discharge and water temperature, Europe-wide and at every plant. Plant data is only *read* (locations and `Water_type` from `data/app_input/facilities.csv`).

```bash
python data_processing/environment/build_all.py      # after new downloads; ~5 min for the current samples
```

| Step | Output | Used for |
| --- | --- | --- |
| `build_grids.py` | `data/interim/<source>/europe_daily/<scenario>.zarr` (forecasts: `forecast_<run>.zarr`) | Standard grids of `discharge` (m³/s) and `air_temperature` (°C) |
| `water_temperature.py` | `data/interim/water_temperature/europe_daily/<scenario>.zarr` | `water_temperature` (°C) on each discharge grid |
| `build_statistics.py` | `data/interim/<source>/statistics/<scenario>.zarr` | Monthly quantiles per grid cell (climate track, planning mode) |
| `build_app_input.py` | `data/app_input/environment/` | Per-plant tables for the app (see the README there). Track 1 only by default; `--tracks 1 2` adds the climate scenarios and `plant_statistics.parquet` |
| `build_curtailment.py` | `data/app_input/environment/curtailment.parquet` | Daily curtailment per plant (`methodology_cooling_constrain.md`), from the per-plant tables + `facilities.csv` |

## Grid conventions (all Zarr stores)

- Dimension `time` = the UTC calendar day the daily mean describes. GloFAS time stamps are shifted back one day to match.
- Grids are kept as delivered (regridding discharge breaks river networks):
  - Regular grids use `lat`/`lon` dimensions: GloFAS and HydroLand (0.05°), ERA5-Land (0.1°), ECMWF (0.25°).
  - Curvilinear grids use `y`/`x` with 2-D `lat`/`lon`: C3S E-HYPEgrid (5 km), EURO-CORDEX (0.11°).
- Optional `member` dimension (0 = control). Chunks are up to 10 years × 32 × 32 cells, so a point's full series reads in < 0.1 s on regular grids and ~1 s on curvilinear ones.

## Pairings for water temperature

| Water temperature | Discharge | Air temperature |
| --- | --- | --- |
| `forecast` | GloFAS forecast | ECMWF HRES |
| `reanalysis` | GloFAS reanalysis | ERA5-Land |
| `historical`, `rcp_*` | C3S E-HYPEgrid | EURO-CORDEX EC-EARTH/RCA4 (same model chain) |
| — | HydroLand | Not yet: Climate DT temperature has only 00 UTC values |

The air temperature is mapped to the nearest air temperature cell for each discharge cell. The model is air2stream reduced to 4 parameters and **uncalibrated** (see the docstring of `water_temperature.py` and `methodology_water_temperature.md`). After calibration, change `DEFAULT_PARAMS` (or make them per cell) and `METHOD`; the output format stays the same.

## Planning mode: a new location

```python
import xarray as xr
ds = xr.open_zarr("data/interim/c3s_hydrology/europe_daily/rcp_4_5.zarr")
# find the main-river cell near (lat, lon) with build_app_input.find_cell(...), then:
series = ds["discharge"].isel(y=row, x=col).load()
stats = xr.open_zarr("data/interim/water_temperature/statistics/rcp_4_5.zarr")["water_temperature_quantile"]
```

## Scaling to full periods

All steps rebuild from every file present, so downloading more years and rerunning `build_all.py` is enough. For decades of daily data, `build_grids.py` rechunks through dask. If memory becomes a limit, use the `rechunker` package for that step.
