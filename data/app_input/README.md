# Application input

Store reproducible, application-ready datasets here. The plant loader currently
reads `facilities.csv` from this directory: one row per facility, built by
`data_processing/plants/build_facilities.py` (columns are listed in
`data_processing/plants/readme.txt`). Seawater-cooled facilities are left out;
the unfiltered table is `data/interim/nuclear_units/facilities_all.csv`. The discharge reader still uses its
former source path and needs a separate migration.
