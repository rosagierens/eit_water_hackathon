# Data Organisation Suggestion

This repository can be structured with a clear two-stage data workflow:

## 1. `data_in/`

Use this folder for source data **as accessed** (raw or original form), along with all context needed to understand and reproduce data usage.

Recommended contents:
- Original input datasets
- Notes about each dataset (source details, assumptions, caveats)
- Citation/reference information for each source
- Code/scripts for initial cleaning and transformation of each dataset

## 2. `data_cleaned/`

Use this folder for processed input data outputs produced from `data_in/` preparation steps.

Recommended contents:
- Cleaned/standardized datasets
- Intermediate outputs that are ready to be combined

The goal is to keep analysis/app-ready data separate from raw inputs while maintaining a reproducible path from source to processed data.
