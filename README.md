# Cooling Water Risk

This project studies how drought and high temperatures may constrain power
generation at European nuclear plants. The planned work covers short-term
operations and longer-term climate scenarios. The current app maps operating
plants that cool with fresh water; the cooling-impact model is still under
development.

## Repository layout

| Path | Purpose |
| --- | --- |
| `app/` | FastAPI service and static map interface. |
| `data/raw/<source>/` | Source files as obtained, with source notes. |
| `data/interim/<source>/` | Filtered, extracted, or converted data from that source. `nuclear_units/` combines GEM and JRC. |
| `data/app_input/` | Processed files read by the application, currently `facilities.csv`. |
| `data_processing/plants/` | GEM and JRC plant processing, the GEM-JRC unit merge, and the facility table. |
| `data_processing/river_discharge/` | GloFAS, C3S hydrology, and HydroLand download scripts. |
| `data_processing/air_temperature/` | ECMWF, ERA5-Land, EURO-CORDEX, and Climate DT download scripts. |

Keep processing code in `data_processing/`. Do not edit source files in place.
See [data/README.md](data/README.md) for placement rules and
[data_processing/README.md](data_processing/README.md) for the script groups.

## Run the plant app

From the repository root, with dependencies from `requirements.txt` installed:

```bash
python data_processing/plants/run_pipeline.py
python -m app --reload
```

`run_pipeline.py` runs the four plant scripts in order and rebuilds
`data/app_input/facilities.csv` from the raw GEM and JRC files; skip it if the
committed file is current. See
[data_processing/plants/readme.txt](data_processing/plants/readme.txt) for what
each one does.

Open http://127.0.0.1:8050. See [app/README.md](app/README.md) for the app's
current capabilities and discharge-data limitation.

## Known issues

- **No cooling data for Ukraine and Belarus.** The JRC Open Power Plants
  Database does not cover these countries, so 17 operating units at 5
  facilities (Zaporizhzhia, Rivne, South Ukraine, Khmelnitski, Astravets) have
  no cooling type or water type. They are not filled by hand. In
  `data/app_input/facilities.csv` their `Alpha` and `Q_river_MW_th` are empty
  and `Cooling_data_flag` is `missing`, so the cooling constraint cannot be
  calculated for them.
- Seawater-cooled facilities are left out of the app input on purpose; see
  `EXCLUDED_WATER_TYPES` in `data_processing/plants/build_facilities.py`.
