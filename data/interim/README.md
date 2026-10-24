# Interim data

Store reproducible filtered, extracted, or standardized data here before it is
shaped for the application. Use one subdirectory per source, with the same
source name used under `data/raw/`. Processing scripts live in
`data_processing/`.

Data that combines several sources gets its own folder named after its content:

- `nuclear_units/`: GEM operating reactor units merged with JRC cooling data
  (`units_gem_jrc.csv`, written by `data_processing/plants/merge_units.py`)
  and the facility table before the water-type filter (`facilities_all.csv`,
  written by `data_processing/plants/build_facilities.py`).
