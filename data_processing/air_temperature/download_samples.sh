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

echo "== Track 1: ERA5-Land daily max and mean, summer 2022"
python download_air_temperature.py observed --start 2022-07-01 --end 2022-08-31

echo "== Track 2: EURO-CORDEX, 2003 (historical) and 2045 (RCP2.6/4.5/8.5)"
python download_air_temperature.py cordex --experiment historical --years 2003
python download_air_temperature.py cordex --experiment rcp_2_6 rcp_4_5 rcp_8_5 --years 2045

echo "== Track 2: Climate DT at the plants, August 2003 (hist) and August 2045 (SSP3-7.0)"
python download_air_temperature.py climatedt --experiment hist --start 2003-08-01 --end 2003-08-31
python download_air_temperature.py climatedt --experiment SSP3-7.0 --start 2045-08-01 --end 2045-08-31

echo "Done. Source files are in data/raw/<source>/; processed files are in data/interim/<source>/."
