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

echo "== Track 1: GloFAS reanalysis, 2023-01-01  2026-10-18"
python download_river_discharge.py historical --start 2023-01-01 --end  2026-10-18
