# Data layout

Data flows from `raw/` through `interim/` to `app_input/`. Processing code lives
in the repository's `data_processing/` directory.

- `raw/`: source datasets as obtained, organized by source.
- `interim/`: reproducible intermediate outputs and standardized datasets.
- `app_input/`: processed files in the format the application reads.

Keep source files unchanged. Record each dataset's origin, licence, access date,
and processing caveats beside its source files. Generate files in `interim/` and
`app_input/` with scripts in `data_processing/`.
