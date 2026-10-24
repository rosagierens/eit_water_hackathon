"""River discharge time series at a plant, for every downloaded data source.

Each source is a set of NetCDF files under data_in/environmental_variables/river_discharge/raw/
(see the readme there). The reader is deliberately generic: it finds the discharge
variable, the lat/lon coordinates and the time axis by name, so GloFAS, HydroLand and
C3S files can all be read the same way.

Choosing the grid cell: the nearest cell is often a small side stream, so we take the
cell with the highest mean discharge within SEARCH_RADIUS_KM of the plant. That is
normally the main river the plant takes its cooling water from. Coastal plants that
cool with seawater get whatever river is nearby, so treat their values with care.
"""

import zipfile
from functools import lru_cache

import numpy as np
import pandas as pd
import xarray as xr
from ..helper import get_path

RAW = get_path("RAW_DISCHARGE_DATA")

SEARCH_RADIUS_KM = 10

DISCHARGE_VARS = ("dis24", "dis", "Qrouted", "rdis", "discharge", "river_discharge")
LAT_NAMES = ("latitude", "lat", "y")
LON_NAMES = ("longitude", "lon", "x")
TIME_NAMES = ("valid_time", "time")

# Track 1 = operations (next days), track 2 = planning (scenarios).
SOURCES = {
    "glofas_forecast": {"track": 1, "label": "GloFAS forecast", "glob": "forecast/*.nc", "latest_only": True},
    "glofas_reanalysis": {"track": 1, "label": "GloFAS reanalysis", "glob": "historical/*.nc"},
    "hydroland_hist": {"track": 2, "label": "HydroLand historical", "glob": "hydroland/hist/mrm/*.nc"},
    "hydroland_ssp370": {"track": 2, "label": "HydroLand SSP3-7.0", "glob": "hydroland/SSP3-7.0/mrm/*.nc"},
    "c3s_historical": {"track": 2, "label": "C3S historical", "glob": "projection/*_historical_*.zip"},
    "c3s_rcp26": {"track": 2, "label": "C3S RCP2.6", "glob": "projection/*_rcp_2_6_*.zip"},
    "c3s_rcp45": {"track": 2, "label": "C3S RCP4.5", "glob": "projection/*_rcp_4_5_*.zip"},
    "c3s_rcp85": {"track": 2, "label": "C3S RCP8.5", "glob": "projection/*_rcp_8_5_*.zip"},
}


def source_files(source):
    """NetCDF files of a source; C3S zip archives are unpacked next to themselves once."""
    spec = SOURCES[source]
    files = []
    for path in sorted(RAW.glob(spec["glob"])):
        if path.suffix == ".zip":
            folder = path.with_suffix("")
            if not folder.exists():
                with zipfile.ZipFile(path) as z:
                    z.extractall(folder)
            files += sorted(folder.rglob("*.nc"))
        elif not path.name.endswith(".part"):
            files.append(path)
    if spec.get("latest_only") and files:
        # Forecast names end in the run date (..._YYYYMMDD.nc); prefer the ensemble on the same date.
        files = [max(files, key=lambda p: (p.stem[-8:], "ensemble" in p.name))]
    return files


def available_sources():
    return {
        key: {
            "track": spec["track"],
            "label": spec["label"],
            "files": len(source_files(key)),
        }
        for key, spec in SOURCES.items()
    }


def _first(names, candidates):
    return next((n for n in candidates if n in names), None)


def _discharge_var(ds):
    name = _first(ds.data_vars, DISCHARGE_VARS)
    if name is None:  # fall back to the first gridded variable
        name = next(v for v in ds.data_vars if ds[v].ndim >= 2)
    return ds[name]


def _distance_km(lat, lon, plat, plon):
    dlat = np.radians(lat - plat)
    dlon = np.radians(lon - plon)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(plat)) * np.cos(np.radians(lat)) * np.sin(dlon / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


@lru_cache(maxsize=4096)
def _cell(path, plat, plon):
    """Index (as a dict for isel) of the main-river cell near the plant, or None if outside the grid."""
    with xr.open_dataset(path) as ds:
        da = _discharge_var(ds)
        lat_name, lon_name = _first(ds.coords, LAT_NAMES), _first(ds.coords, LON_NAMES)
        lat, lon = ds[lat_name], ds[lon_name]
        if lat.ndim == 1:
            lat2, lon2 = np.meshgrid(lat.values, lon.values, indexing="ij")
            dims = (lat.dims[0], lon.dims[0])
        else:
            lat2, lon2, dims = lat.values, lon.values, lat.dims
        dist = _distance_km(lat2, lon2, plat, plon)
        near = dist <= SEARCH_RADIUS_KM
        if not near.any():
            return None
        i0, i1 = np.nonzero(near)
        box = {dims[0]: slice(i0.min(), i0.max() + 1), dims[1]: slice(i1.min(), i1.max() + 1)}
        other = [d for d in da.dims if d not in dims]
        mean = da.isel(box).mean(other).values
        mean = np.where(near[box[dims[0]], box[dims[1]]], mean, np.nan)
        if np.all(np.isnan(mean)):
            return None
        j0, j1 = np.unravel_index(np.nanargmax(mean), mean.shape)
        index = {dims[0]: int(i0.min() + j0), dims[1]: int(i1.min() + j1)}
        i, j = index[dims[0]], index[dims[1]]
        cell = {
            "lat": float(lat2[i, j]),
            "lon": float(lon2[i, j]),
            "distance_km": float(dist[i, j]),
        }
        return index, cell


def _series(path, index):
    """Daily series from one file: a DataFrame indexed by time, ensemble members as columns."""
    with xr.open_dataset(path) as ds:
        da = _discharge_var(ds).isel(index).squeeze()
        units = da.attrs.get("units", "m3 s-1")
        time_name = _first(list(da.coords), TIME_NAMES)
        member = _first(da.dims, ("number", "realization", "member"))
        # Forecast files: valid_time depends on (reference time, step). Flatten it to one time
        # axis, in the time coordinate's own dimension order, with ensemble members as columns.
        da = da.load().transpose(*da[time_name].dims, *([member] if member else []))
        times = da[time_name].values.reshape(-1)
        values = da.values.reshape(len(times), -1)
    frame = pd.DataFrame(values, index=pd.DatetimeIndex(times)).sort_index()
    return frame, units


def plant_series(source, plat, plon):
    """Discharge at a plant for one source, ready for JSON. `series` is empty if nothing is downloaded."""
    spec = SOURCES[source]
    result = {
        "source": source,
        "label": spec["label"],
        "track": spec["track"],
        "units": None,
        "cell": None,
        "series": [],
    }
    files = source_files(source)
    if not files:
        result["message"] = "No data downloaded for this source yet"
        return result
    found = _cell(files[0], round(plat, 4), round(plon, 4))
    if found is None:
        result["message"] = f"Plant is outside this dataset's area (no river cell within {SEARCH_RADIUS_KM} km)"
        return result
    index, result["cell"] = found
    frames = []
    for path in files:
        frame, result["units"] = _series(path, index)
        frames.append(frame)
    data = pd.concat(frames)
    data = data[~data.index.duplicated(keep="last")]
    for time, row in data.iterrows():
        values = row.dropna().to_numpy()
        if values.size == 0:
            continue
        point = {"time": time.isoformat(), "value": float(np.median(values))}
        if values.size > 1:  # ensemble: add the spread
            point.update(p10=float(np.percentile(values, 10)), p90=float(np.percentile(values, 90)))
        result["series"].append(point)
    return result
