# Data processing

Keep all data download, extraction, cleaning, and preparation code here. Run
scripts from the repository root with `python data_processing/<group>/<script>.py`.

| Group | Scripts | Data sources |
| --- | --- | --- |
| `plants/` | `process_gem_units.py`, `process_jrc_units.py`, `merge_units.py`, `build_facilities.py` | Global Nuclear Power Tracker, JRC Open Power Plants Database, project parameters |
| `river_discharge/` | `download_river_discharge.py`, `download_hydroland.py`, `download_samples.sh` | GloFAS, C3S hydrology, HydroLand |
| `air_temperature/` | `download_air_temperature.py`, `download_samples.sh` | ECMWF, ERA5-Land, EURO-CORDEX, Climate DT |

Source downloads go to `data/raw/<source>/`. Filtered, extracted, cropped, or
converted data goes to `data/interim/<source>/`. Data that combines sources goes
to its own folder under `data/interim/` (for example `nuclear_units/`).
`plants/build_facilities.py` publishes `data/app_input/facilities.csv`; see
`plants/readme.txt` for the run order.
