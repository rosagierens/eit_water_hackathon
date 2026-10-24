# Data processing

Keep all data download, extraction, cleaning, and preparation code here. Run
scripts from the repository root with `python data_processing/<group>/<script>.py`.

| Group | Scripts | Data sources |
| --- | --- | --- |
| `plants/` | `process_gem_units.py`, `process_jrc_units.py` | Global Nuclear Power Tracker, JRC Open Power Plants Database |
| `river_discharge/` | `download_river_discharge.py`, `download_hydroland.py`, `download_samples.sh` | GloFAS, C3S hydrology, HydroLand |
| `air_temperature/` | `download_air_temperature.py`, `download_samples.sh` | ECMWF, ERA5-Land, EURO-CORDEX, Climate DT |

Source downloads go to `data/raw/<source>/`. Filtered, extracted, cropped, or
converted data goes to `data/interim/<source>/`. The plant processor also
publishes `data/app_input/facilities.csv`.
