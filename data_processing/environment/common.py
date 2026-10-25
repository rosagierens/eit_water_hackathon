"""Shared definitions for the environmental data pipeline: sources, paths and grid helpers.

Standard conventions for every gridded dataset written by this pipeline (data/interim/<source>/europe_daily/):
  - one Zarr store per source and scenario, variable `discharge` (m3 s-1), `air_temperature` (degC daily mean)
    or `water_temperature` (degC daily mean)
  - dimension `time`: the calendar day (UTC) the daily value describes, as datetime64 at 00:00
  - regular grids keep 1-D `lat`/`lon` dimensions; curvilinear grids keep `y`/`x` with 2-D `lat`/`lon` coordinates
    (native grids are kept: regridding discharge would break the river network)
  - optional dimension `member` for ensembles (0 = control)
  - chunked as (time up to 10 years, 32 x 32 cells) so the full daily series at one point loads quickly
"""

import glob
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
INTERIM = REPO / "data" / "interim"
APP_INPUT = REPO / "data" / "app_input"
# Plant locations: read only (owned by the plant data work).
FACILITIES = APP_INPUT / "facilities.csv"

TIME_CHUNK = 3650
SPACE_CHUNK = 32
ONE_DAY = pd.Timedelta(days=1)

# Discharge sources. `shift_days=-1`: GloFAS stamps a 24 h mean at the end of the day it describes.
DISCHARGE = {
    "glofas_forecast": dict(source="glofas", scenario="forecast", track=1, label="GloFAS forecast",
                            files="raw/glofas/forecast/*.nc", var="dis24", shift_days=-1, forecast=True),
    "glofas_reanalysis": dict(source="glofas", scenario="reanalysis", track=1, label="GloFAS reanalysis (ERA5)",
                              files="raw/glofas/historical/*.nc", var="avg_dis", shift_days=-1),
    "hydroland_hist": dict(source="hydroland", scenario="hist", track=2, label="HydroLand historical (IFS-NEMO)",
                           files="interim/hydroland/hist/mrm/*_europe_daily.nc", var="Qrouted"),
    "hydroland_ssp370": dict(source="hydroland", scenario="SSP3-7.0", track=2, label="HydroLand SSP3-7.0 (IFS-NEMO)",
                             files="interim/hydroland/SSP3-7.0/mrm/*_europe_daily.nc", var="Qrouted"),
    **{f"c3s_{exp}": dict(source="c3s_hydrology", scenario=exp, track=2, label=f"C3S E-HYPEgrid {label}",
                          files=f"raw/c3s_hydrology/projection/e_hypegrid_*_{exp}_*.zip", var="rdis")
       for exp, label in (("historical", "historical"), ("rcp_2_6", "RCP2.6"), ("rcp_4_5", "RCP4.5"),
                          ("rcp_8_5", "RCP8.5"))},
}

# Catchment version of the C3S discharge: values per E-HYPE sub-basin (no grid), 10-year files, ~27x smaller.
# Plants are located with the sub-basin map (SUBBASINS); see catchments.py.
CATCHMENT = {
    f"c3s_catchment_{exp}": dict(source="c3s_catchment", scenario=exp, track=2, label=f"C3S E-HYPEcatch {label}",
                                 files=f"raw/c3s_hydrology/projection/e_hypecatch_m00_*_{exp}_*.zip", var="rdis",
                                 air=f"cordex_{exp}")
    for exp, label in (("historical", "historical"), ("rcp_2_6", "RCP2.6"), ("rcp_4_5", "RCP4.5"),
                       ("rcp_8_5", "RCP8.5"))
}
SUBBASINS = RAW / "ehype_subbasins" / "SubbasinEHYPEv3pt0.zip"

# Daily mean air temperature sources (only used to derive water temperature).
AIR_TEMPERATURE = {
    "ecmwf_forecast": dict(source="ecmwf", scenario="forecast", track=1, label="ECMWF HRES forecast",
                           files="interim/ecmwf/forecast/ecmwf_hres_2t_*.nc", var="t2m", forecast=True),
    "era5_land": dict(source="era5_land", scenario="reanalysis", track=1, label="ERA5-Land",
                      files="raw/era5_land/observed/era5land_t2m_daily_mean_*.nc", var="t2m"),
    **{f"cordex_{exp}": dict(source="euro_cordex", scenario=exp, track=2, label=f"EURO-CORDEX EC-EARTH/RCA4 {exp}",
                             files=f"raw/euro_cordex/*_{exp}_*/tas_*.nc", var="tas")
       for exp in ("historical", "rcp_2_6", "rcp_4_5", "rcp_8_5")},
}

# Water temperature = discharge source + matching air temperature source.
# HydroLand is not paired yet: its Climate DT air temperature has only 00 UTC values (see air_temperature readme).
WATER_TEMPERATURE = {
    "wt_forecast": dict(discharge="glofas_forecast", air="ecmwf_forecast"),
    "wt_reanalysis": dict(discharge="glofas_reanalysis", air="era5_land"),
    **{f"wt_{exp}": dict(discharge=f"c3s_{exp}", air=f"cordex_{exp}")
       for exp in ("historical", "rcp_2_6", "rcp_4_5", "rcp_8_5")},
}


def files_for(spec):
    return sorted(glob.glob(str(REPO / "data" / spec["files"])))


def grid_store(dataset_id, spec, kind="europe_daily"):
    """Path of a standardized Zarr store, e.g. data/interim/glofas/europe_daily/reanalysis.zarr."""
    return INTERIM / spec["source"] / kind / f"{spec['scenario']}.zarr"


def water_store(wt_id):
    return INTERIM / "water_temperature" / "europe_daily" / f"{wt_id.removeprefix('wt_')}.zarr"


def horizontal_dims(da):
    """('lat', 'lon') for regular grids, ('y', 'x') for curvilinear ones."""
    return ("lat", "lon") if "lat" in da.dims else ("y", "x")


def lat_lon_2d(ds):
    lat, lon = ds["lat"].values, ds["lon"].values
    if lat.ndim == 1:
        lat, lon = np.meshgrid(lat, lon, indexing="ij")
    return lat, lon


def distance_km(lat, lon, plat, plon):
    dlat, dlon = np.radians(lat - plat), np.radians(lon - plon)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(plat)) * np.cos(np.radians(lat)) * np.sin(dlon / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def load_plants():
    """Plant locations from the plant data (read only): location_id, name, lat, lon, water_type."""
    plants = pd.read_csv(FACILITIES)
    plants = plants.rename(columns={"Location_ID": "location_id", "Name": "name", "Lat": "lat", "Lon": "lon",
                                    "Water_type": "water_type"})
    if "water_type" not in plants:
        plants["water_type"] = None
    plants["water_type"] = plants["water_type"].fillna("unknown")  # no cooling data (e.g. Ukraine, Belarus)
    return plants[["location_id", "name", "lat", "lon", "water_type"]]


def with_written_coords(ds):
    """Coordinates as plain arrays without inherited chunk settings.

    Used before writing a Zarr store with deferred (compute=False) data: the coordinates (e.g. 2-D lat/lon of
    curvilinear grids) are then written right away, with a chunk layout Zarr chooses itself.
    """
    coords = {}
    for name in ds.coords:
        coord = ds[name].load().variable.copy()
        coord.encoding = {}
        coords[name] = coord
    return ds.assign_coords(coords)
