# Cooling Water Risk

This project studies how drought and high temperatures may constrain power
generation at European nuclear plants. The planned work covers short-term
operations and longer-term climate scenarios. The current app maps operating
plants; the cooling-impact model is still under development.

## Repository layout

| Path | Purpose |
| --- | --- |
| `app/` | FastAPI service and static map interface. |
| `data/raw/<source>/` | Source files as obtained, with source notes. |
| `data/interim/<source>/` | Filtered, extracted, or converted data from that source. |
| `data/app_input/` | Processed files read by the application, currently `facilities.csv`. |
| `data_processing/plants/` | GEM and JRC plant processing scripts. |
| `data_processing/river_discharge/` | GloFAS, C3S hydrology, and HydroLand download scripts. |
| `data_processing/air_temperature/` | ECMWF, ERA5-Land, EURO-CORDEX, and Climate DT download scripts. |

Keep processing code in `data_processing/`. Do not edit source files in place.
See [data/README.md](data/README.md) for placement rules and
[data_processing/README.md](data_processing/README.md) for the script groups.

## Run the plant app

From the repository root, with dependencies from `requirements.txt` installed:

```bash
python data_processing/plants/process_plants.py
python -m app --reload
```

Open http://127.0.0.1:8050. See [app/README.md](app/README.md) for the app's
current capabilities and discharge-data limitation.
