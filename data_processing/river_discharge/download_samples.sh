#!/usr/bin/env bash
# Download a small sample of every river discharge source, so the app can be
# developed before the full data is fetched. Run from anywhere with the
# project venv active; already-downloaded files are skipped on a rerun.
#
# The years are chosen so the sources can be compared:
#   2003  European heatwave, in both historical runs (C3S 1971-2005, HydroLand 1990-2014)
#   2022  European drought summer, for verifying the forecast setup (GloFAS reanalysis)
#   2045  mid-century in every scenario (C3S RCP2.6/4.5/8.5, HydroLand SSP3-7.0)
#
# Credentials: CDSAPI_KEY (or ~/.cdsapirc) for GloFAS and C3S;
# DESP_USERNAME / DESP_PASSWORD (or prompts) for HydroLand.
set -euo pipefail
cd "$(dirname "$0")"

echo "== Track 1: GloFAS forecast, latest run, 10 days (control member)"
python download_river_discharge.py forecast

echo "== Track 1: GloFAS reanalysis, summer 2022"
python download_river_discharge.py historical --start 2022-07-01 --end 2022-08-31

echo "== Track 2: C3S, 2003 (historical) and 2045 in three scenarios"
python download_river_discharge.py projection --experiment historical --years 2003
python download_river_discharge.py projection --experiment rcp_2_6 rcp_4_5 rcp_8_5 --years 2045

echo "== Track 2: HydroLand, August 2003 (hist) and August 2045 (SSP3-7.0), daily means over Europe"
python download_hydroland.py download --start 2003-08-01 --end 2003-08-31
python download_hydroland.py download --start 2045-08-01 --end 2045-08-31

echo "Done. Source files are in data/raw/<source>/; processed files are in data/interim/<source>/."
