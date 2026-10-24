## Air temperature: dataset choice

| Track                   | Dataset                                                       | Coverage                          | Resolution |
|-------------------------|---------------------------------------------------------------|-----------------------------------|------------|
| 1 Forecast              | ECMWF open data, IFS HRES (or ENS), 2 m temperature           | latest runs only (a few days)     | 0.25°, 3-hourly to 144 h, then 6-hourly; HRES 10 d, ENS 15 d |
| 1 Observations          | ERA5-Land daily statistics (CDS, derived-era5-land-daily-statistics) | 1950 to ~1 week ago        | 0.1°, daily max / mean / min |
| 2 Projections (main)    | DestinE Climate DT, IFS-NEMO (Polytope)                       | hist 1990-2014, SSP3-7.0 2015-2049 | hourly, extracted at each plant |
| 2 Projections (scenarios)| EURO-CORDEX EC-EARTH/RCA4 (CDS, projections-cordex-domains-single-levels) | hist 1970-2005, RCP2.6/4.5/8.5 2006-2100 | 0.11° (~12 km), daily mean + daily max |

Why these:
- Forecast: the ECMWF ensemble also drives the GloFAS discharge forecast, so
  heat and flow forecasts come from the same weather forecast. Free, no
  account, CC BY 4.0. HRES is one run (~40 MB for 10 days). ENS gives the
  spread (~0.65 MB per member and time step, for the whole globe). Only the
  last few days of runs are kept online, so download each day you need. The
  control run of the ensemble was missing from the open-data index when this
  was set up (2026-10-24), so `--product ens` uses perturbed members.
- Observations: ERA5-Land is based on ERA5, which also drives the GloFAS
  reanalysis (consistent verification). Daily maximum is what matters for
  heat limits. It is a reanalysis, not station data. E-OBS is the
  station-based alternative if needed.
- Climate DT: the same simulation as HydroLand, so heat and low flow in a
  future year come from one consistent climate. Polytope extracts the time
  series at each plant on the server, so the download is a few MB instead of
  global fields.
- EURO-CORDEX: by default the same GCM/RCM chain as the C3S discharge
  projections (EC-EARTH r12i1p1 + RCA4). That gives matching temperature and
  discharge for RCP2.6/4.5/8.5.

## Access

1. CDS (observed, cordex): the same key as for the river discharge downloads
   (CDSAPI_KEY or ~/.cdsapirc). Accept the licences once on:
   - https://cds.climate.copernicus.eu/datasets/derived-era5-land-daily-statistics
   - https://cds.climate.copernicus.eu/datasets/projections-cordex-domains-single-levels
     (CORDEX has its own terms; check them for your model chain)
2. Polytope (climatedt): store a DestinE token once in ~/.polytopeapirc with
   DestinE's own login script:

     pip install conflator lxml
     curl -O https://raw.githubusercontent.com/destination-earth-digital-twins/polytope-examples/main/desp-authentication.py
     python desp-authentication.py          # asks for your DESP username and password

   The token lasts a long time. Rerun the script if Polytope reports an
   authentication error.
3. Forecast: no account needed.
4. `pip install -r requirements.txt` (ecmwf-opendata, cfgrib, eccodes, polytope-client).

## Usage

Run from the repo root. Original downloads go to `data/raw/<source>/`; converted
and extracted files go to `data/interim/<source>/`. Add `--dry-run` to print a
request without downloading.

  S=data_processing/air_temperature/download_air_temperature.py
  python $S forecast                                   # latest HRES run, 10 days, Europe, °C
  python $S forecast --product ens --members 10        # 10 ensemble members, 15 days
  python $S observed --start 2022-07-01 --end 2022-08-31
  python $S cordex --experiment rcp_2_6 rcp_4_5 rcp_8_5 --years 2045
  python $S cordex --experiment historical --years 2003
  python $S climatedt --experiment SSP3-7.0 --start 2045-08-01 --end 2045-08-31
  python $S climatedt --experiment hist --start 2003-08-01 --end 2003-08-31

Or get the whole sample in one go: `bash data_processing/air_temperature/download_samples.sh`

Outputs:
- `data/raw/ecmwf/forecast/*.grib2`: original forecast. The cropped Celsius
  NetCDF is `data/interim/ecmwf/forecast/*.nc`.
- `data/raw/era5_land/observed/*.nc`: ERA5-Land response. If the response is a
  ZIP archive, it is extracted next to it under `data/raw/era5_land/observed/`
  (unpacking changes nothing).
- `data/raw/euro_cordex/<name>/`: the original NetCDF files, unpacked from the
  CDS zip (the zip itself is removed, since unpacking changes nothing). CORDEX daily
  files usually cover 5 years, so asking for one year may return the whole
  5-year file (a few hundred MB per variable).
- `data/raw/climate_dt/<experiment>/*.covjson`: original plant extraction.
  The hourly `plant_id`, `time`, `t2m` (°C) CSV is under
  `data/interim/climate_dt/<experiment>/`.

## Caveats

- Climate DT requests were tested for format, not against the live server:
  that needs your token. If the request fails, try `--resolution standard`
  (the setting used in DestinE's own example) or the LUMI server
  (`--address polytope.lumi.apps.dte.destination-earth.eu`). If the server
  rejects all plant points in one request, split the request by plant.
- **Open issue, Climate DT time steps:** the samples downloaded on 2026-10-24
  contain only one value per day (00 UTC), although the request asks for
  `time: 0000/to/2300/by/0100`. 00 UTC is close to the night minimum, so these
  values are **not** daily means or maxima. Before using them, find a request
  that returns hourly values (for example a different `time_axis`, or one
  request per hour) and test it with a DestinE token.
- Climate DT points are matched to plants by the returned grid-cell
  coordinates (within 0.25°). Points of plants removed from the plant list are
  skipped with a message. Re-extract if new plants are added.
- Daily maximum from the forecast is computed from 3- or 6-hourly values, so
  it can underestimate the true maximum by a few tenths of a degree.
- Time zones: all data is in UTC. ERA5-Land daily statistics can be shifted
  with --time_zone in the request, which the script fixes at UTC for
  consistency.
- CORDEX uses a rotated-pole grid with 2D lat/lon coordinates. Pick the
  nearest grid cell to a plant by distance, not by index.

## Citation / licence

- ECMWF open data: © ECMWF, CC BY 4.0.
- ERA5-Land: Muñoz Sabater (2019), ERA5-Land, C3S/CDS. Licence: CC BY 4.0.
- EURO-CORDEX: C3S, CORDEX regional climate model data on single levels, CDS;
  model-specific CORDEX terms of use.
- Climate DT: Destination Earth Climate Change Adaptation Digital Twin, ECMWF
  et al.; DestinE data policy.

Accessed: 2026-10-24.
