## River discharge: dataset choice

| Track                       | Dataset (store, ID)                                                   | Coverage                    | Resolution             |
|-----------------------------|-----------------------------------------------------------------------|-----------------------------|------------------------|
| 1 Forecast                  | GloFAS forecast (EWDS, cems-glofas-forecast)                          | 2019-11 to today, global    | 0.05° (~5 km), daily, 1-30 day lead, control + 50 members |
| 1 Verification (past)       | GloFAS historical (EWDS, cems-glofas-historical)                      | 1979 to ~yesterday, global  | 0.05°, daily           |
| 2 Climate projections       | HydroLand, DestinE Climate DT (Data Lake, EO.UFZ.DAT.HYDROLAND)       | 1990-2014 historical, 2015-2049 projection, global | 0.05° (~5 km) or 0.1°, daily or hourly |
| 2 Complement: scenarios     | C3S hydrology projections (CDS, sis-hydrology-variables-derived-projections) | 1971-2005 historical, 2006-2100 RCP2.6/4.5/8.5, Europe | 5 km grid (E-HYPEgrid) or catchments, daily |

Why these:
- Forecast: GloFAS is the only operational river discharge forecast that is
  public in real time. EFAS (efas-forecast) has better resolution in Europe
  (~1.5 km), but the public archive has a 30-day delay. Real-time EFAS is for
  EFAS partners only, so it doesn't work for an operational forecast.
  EFAS is still useful later to hindcast past events.
- Verification: GloFAS historical uses the same LISFLOOD model and grid as the
  forecast, forced by ERA5. Verifying against it measures forecast skill
  without the model's own bias mixed in, which is the standard GloFAS approach.
  It is a model reanalysis, not gauge measurements. For a few key rivers,
  check it against gauge data from GRDC (https://portal.grdc.bafg.de, free,
  manual download) or EStreams (pan-European streamflow, Zenodo).
  EFAS historical (efas-historical, 1992-present, ~1.5 km, forced by
  observed weather) is a higher-resolution European alternative.
- Projections, primary: HydroLand routes mHM runoff through the river network
  (mRM, variable Qrouted) at ~5 km, with daily or hourly output. It is driven
  by the same Climate DT simulations that provide air temperature, so heat and
  low-flow stress at a plant come from one consistent climate. That is what
  the planning track needs. It needs DestinE upgraded access (we have it).
  Limits: it ends in 2049, and there is one simulation: IFS-NEMO,
  SSP3-7.0, a single realization. That's one scenario with no ensemble spread.
- Projections, complement: the C3S dataset is the only pan-European daily
  discharge set with bias-adjusted EURO-CORDEX forcing and several RCPs. Use it
  for scenario spread (several model chains, RCP2.6/4.5/8.5), for the period
  after 2050. It also has water_temperature_in_local_streams, but only as
  30-year monthly or annual means per catchment (climate impact indicators),
  not as a daily series. HydroLand has no water temperature at all. ISIMIP3b is global but at 0.5° (~50 km), which is too
  coarse for single plants.

## Sample data (download_samples.sh)

To get a small, comparable sample from every source in one go (once the
credentials below are set up):

  bash data_in/environmental_variables/river_discharge/download_samples.sh

The sample has:
  - GloFAS: the latest 10-day forecast, plus the reanalysis for July-August 2022
    (drought summer)
  - C3S: 2003 historical, and 2045 under RCP2.6, RCP4.5 and RCP8.5
  - HydroLand: August 2003 (hist) and August 2045 (SSP3-7.0)

So 2003 can be compared across both historical runs, and 2045 across four
scenarios. Edit the script to change years or areas.

## Scenario options for the planning track

| Source    | Scenario            | Years      | Strength                                   |
|-----------|---------------------|------------|--------------------------------------------|
| HydroLand | SSP3-7.0            | 2015-2049  | ~5 km, hourly, same climate as Climate DT air temperature |
| C3S       | RCP2.6 (low)        | 2006-2100  | Paris-aligned, low-emission pathway             |
| C3S       | RCP4.5 (medium)     | 2006-2100  | intermediate                               |
| C3S       | RCP8.5 (high)       | 2006-2100  | high-end / stress test                     |

SSP3-7.0 is between RCP4.5 and RCP8.5 in warming by 2050. Several C3S scenarios
can be fetched in one call (`--experiment rcp_2_6 rcp_4_5 rcp_8_5`). More
model chains (`--gcm`, `--rcm`) add spread within a scenario.

## Access: HydroLand (download_hydroland.py)

1. Log in to the DestinE Service Platform (https://platform.destine.eu) with
   upgraded access to Climate DT data.
2. `export DESP_USERNAME=<user> DESP_PASSWORD=<password>`, or let the script
   prompt you. If your account uses one, you'll also be asked for an OTP code.
3. `pip install -r requirements.txt` (requires destinelab, requests, xarray).
4. Summarise what's available, then download by date range:

  python data_in/environmental_variables/river_discharge/download_hydroland.py list
  python .../download_hydroland.py download --start 2040-06-01 --end 2040-08-31 --dry-run
  python .../download_hydroland.py download --start 2040-06-01 --end 2040-08-31
  python .../download_hydroland.py download --product 5th_percentile_discharge_indicators

What is published (checked with `list`, 2026-10-24; 1454 items):
  - One simulation only: IFS-NEMO, generation-2, realization-1.
  - hist (activity "baseline"): 1990-01 to 2014-12. SSP3-7.0 ("projections"):
    2015-01 to 2049-12.
  - mrm: one item per month. Hourly routed discharge `Qrouted`, global.
  - mhm: one item per month. Daily soil water (SWC_L01-03), aET, runoff Q.
  - Indicators, one item each: 1st/5th/95th/99th_percentile_discharge_indicators
    and aridity_index (hist only), soil_moisture_deficit_{ref,scen,percent_change}_SWC_L0x.
    There are no discharge percentile indicators for the projection. Compute
    low-flow changes yourself from the mrm data.

The default product is mrm. Each downloaded month is cropped to Europe and
averaged from hourly to daily means right away. Only the small result is kept,
in raw/hydroland/<experiment>/<product>/*_europe_daily.nc.
`--hourly` keeps hourly values, `--no-crop` keeps the global grid,
`--experiment hist|SSP3-7.0` restricts the experiment, `--product mhm` gets
soil and runoff. Global hourly monthly files are large: use `--dry-run`
first to see file sizes, and try one month before downloading decades.
Downloads that are already done are skipped, so an interrupted run can
simply be restarted.

Docs: https://platform.destine.eu/docs/climate-dt-user-guide/doc/apps/hydroland/data_description.html

## Access: GloFAS and C3S (download_river_discharge.py)

1. Register at https://www.ecmwf.int (one account serves both the CDS and the EWDS).
2. Copy your personal access token from your profile page on
   https://cds.climate.copernicus.eu and store it in
   `export CDSAPI_KEY=<token>`
   or in ~/.cdsapirc as the line `key: <token>`.
3. Accept each dataset's licence once (bottom of the "Download" tab):
   - https://ewds.climate.copernicus.eu/datasets/cems-glofas-forecast
   - https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical
   - https://cds.climate.copernicus.eu/datasets/sis-hydrology-variables-derived-projections
4. `pip install -r requirements.txt` (requires cdsapi).

## Usage

Run from the repo root. Files go to `raw/` here (git-ignored). Add `--dry-run`
to any command to print the request without downloading.

  # Track 1: today's forecast run, 10 days ahead (control run, Europe)
  python data_in/environmental_variables/river_discharge/download_river_discharge.py forecast --date 2026-10-23
  # all 50 ensemble members (much larger)
  python .../download_river_discharge.py forecast --date 2026-10-23 --members ensemble

  # Track 1 verification: e.g. the 2022 European drought summer
  python .../download_river_discharge.py historical --start 2022-06-01 --end 2022-08-31

  # Track 2 complement (C3S): one model chain, mid-century in all three scenarios, plus the reference period
  python .../download_river_discharge.py projection --experiment rcp_2_6 rcp_4_5 rcp_8_5 --years 2041 2042 2043
  python .../download_river_discharge.py projection --experiment historical --years 1991 1992 1993

## Caveats

- GloFAS version: version_4_0 "intermediate" is updated daily, while
  version_5_0 only has "consolidated" data, which lags by about a month.
  Before verifying, check in the GloFAS release notes which version the
  operational forecast runs (https://confluence.ecmwf.int/display/CEMS), and
  use the same version for the historical data (--version / --product-type).
- Projection model chains: not every GCM/RCM/member combination exists. The
  default (e_hypegrid, ec_earth, rca4, r12i1p1) is valid. ec_earth only comes
  with r12i1p1. Check other combinations with --dry-run and the CDS web form.
  For planning, use several chains, because one chain is not an ensemble.
- HydroLand vs C3S: different hydrological models and climate forcing. Compare
  each projection with its own historical period (HydroLand 1990-2014, C3S
  1971-2005) and use the changes, not the absolute values. Don't mix them
  with GloFAS absolute values.
- Projection years must be split into a historical run (1971-2005) and an RCP
  run (2006-2100). Compare future periods with the model's own historical
  period, not with GloFAS. The two model systems have different biases.
- Projection downloads are an archive (.zip) with NetCDF inside, covering the
  whole of Europe; there is no area subsetting on the server.
- Getting a plant's time series: don't simply take the nearest grid cell. On a
  5 km grid it can be a small tributary next to the main river. Use the
  upstream-area auxiliary file to snap each plant to the cell on its cooling
  water river (the one with the largest upstream area within ~2-3 cells).
  Coastal plants that use seawater for cooling don't depend on river discharge.

## Citation / licence

- HydroLand: DestinE Climate DT & UFZ, HydroLand, DestinE Data Lake collection
  EO.UFZ.DAT.HYDROLAND; software doi:10.5281/zenodo.15584779. Licence: CC BY 4.0.

- GloFAS: Copernicus Emergency Management Service, GloFAS forecast / historical
  data, EWDS, doi:10.24381/cds.ff1aef77 (forecast), doi:10.24381/cds.a4fdd6b9
  (historical). Licence: CEMS-FLOODS data licence (free, attribution).
- Projections: C3S, Hydrology-related climate impact indicators from 1970 to
  2100 derived from bias adjusted European climate projections, CDS,
  doi:10.24381/cds.73237ad6. Licence: CC BY 4.0.

Accessed: 2026-10-24.
