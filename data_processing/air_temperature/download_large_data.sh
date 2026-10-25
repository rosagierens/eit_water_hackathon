#!/usr/bin/env bash
# Download a small air temperature sample matching the river discharge sample:
#   2003 (heatwave, historical runs), 2022 (drought summer, observations),
#   2045 (all scenarios), plus the latest forecast. Reruns skip finished files.
#
# Credentials: CDSAPI_KEY (or ~/.cdsapirc) and ~/.polytopeapirc.
set -euo pipefail
cd "$(dirname "$0")"

echo "== Track 1: latest ECMWF HRES forecast, 10 days"
python download_air_temperature.py forecast

echo "== Track 1: ERA5-Land daily max and mean, 2026-07-01 to  2026-10-18"
python download_air_temperature.py observed --start 2026-07-01 --end  2026-10-18