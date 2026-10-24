"""Convert every downloaded discharge and air temperature source into a standardized Europe-wide daily Zarr grid.

  python data_processing/environment/build_grids.py            # all sources
  python data_processing/environment/build_grids.py glofas_reanalysis c3s_rcp_4_5

Output: data/interim/<source>/europe_daily/<scenario>.zarr (forecasts: forecast_<run date>.zarr).
Conventions are described in common.py. Stores are rebuilt from all files on every run, so newly
downloaded months or years are included by simply running this again.
"""

import shutil
import sys
import tempfile
import zipfile
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (AIR_TEMPERATURE, DISCHARGE, INTERIM, ONE_DAY, SPACE_CHUNK, TIME_CHUNK, files_for,
                    grid_store, horizontal_dims)


def _standard_axes(ds):
    """Rename source-specific dimension and coordinate names to time / lat / lon (or y / x)."""
    if "valid_time" in ds.variables and "time" in ds.coords and "time" not in ds.dims:
        ds = ds.drop_vars("time")  # ECMWF: scalar run time next to valid_time
    rename = {"valid_time": "time", "latitude": "lat", "longitude": "lon", "rlat": "y", "rlon": "x"}
    ds = ds.rename({k: v for k, v in rename.items() if k in ds.dims or k in ds.coords})
    if "lat" in ds.data_vars:  # C3S keeps 2-D lat as a variable
        ds = ds.set_coords("lat")
    drop = [v for v in ("number", "surface", "heightAboveGround", "height", "time_bnds", "rotated_pole", "bnds",
                        "rlat", "rlon") if v in ds.variables and v not in ds.dims]
    return ds.drop_vars(drop, errors="ignore")


def _daily_mean_from_steps(da):
    """Daily means from sub-daily forecast steps, keeping only days with at least 4 values (6-hourly coverage)."""
    days = da["time"].dt.floor("D")
    counts = days.to_series().value_counts()
    full_days = counts[counts >= 4].index
    daily = da.groupby(days.rename("day")).mean("time").rename(day="time")
    return daily.sel(time=daily["time"].isin(full_days))


def open_source(dataset_id, spec, path, tmp_dir):
    """One file of a source as a standardized DataArray (time, lat/lon or y/x[, member])."""
    path = Path(path)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.endswith(".nc")]
            z.extractall(tmp_dir, members=names)
        path = Path(tmp_dir) / names[0]
    ds = xr.open_dataset(path, chunks={})
    da = _standard_axes(ds)[spec["var"]]
    if "forecast_reference_time" in da.dims:  # GloFAS forecast: one run per file
        da = da.squeeze("forecast_reference_time", drop=True)
    if "forecast_period" in da.dims:
        da = da.swap_dims(forecast_period="time").drop_vars("forecast_period")
    if "step" in da.dims:  # ECMWF forecast: sub-daily steps -> daily means
        da = da.swap_dims(step="time").drop_vars("step")
        da = _daily_mean_from_steps(da)
    da = da.drop_vars([c for c in da.coords if c not in da.dims and c not in ("lat", "lon")])
    da["time"] = da["time"].dt.floor("D") + spec.get("shift_days", 0) * ONE_DAY
    if da.attrs.get("units") in ("K", "kelvin"):
        da = da - 273.15
    return da.astype("float32")


def _encode(da, name, units, attrs):
    hdims = horizontal_dims(da)
    chunks = {"time": min(TIME_CHUNK, da.sizes["time"]), hdims[0]: SPACE_CHUNK, hdims[1]: SPACE_CHUNK}
    if "member" in da.dims:
        chunks["member"] = 1
    ds = da.to_dataset(name=name).chunk(chunks)
    ds[name].attrs = {"units": units}
    for coord in ("lat", "lon"):
        ds[coord].attrs = {"units": "degrees_north" if coord == "lat" else "degrees_east"}
        ds[coord] = ds[coord].astype("float64")
    ds.attrs = {**attrs, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "time_convention": "calendar day (UTC) described by the daily value"}
    return ds


def build(dataset_id, spec, variable, units):
    files = files_for(spec)
    if not files:
        print(f"{dataset_id}: no files, skipped")
        return []
    base_attrs = {k: str(v) for k, v in spec.items() if k not in ("files", "var")}
    written = []
    with ExitStack() as stack:
        tmp = stack.enter_context(tempfile.TemporaryDirectory(dir=INTERIM, prefix=".tmp_"))
        arrays = [open_source(dataset_id, spec, f, tmp) for f in files]
        if spec.get("forecast"):  # one store per forecast run
            groups = [(Path(f), [da]) for f, da in zip(files, arrays)]
        else:
            groups = [(None, arrays)]
        for path, group in groups:
            da = xr.concat(group, "time").sortby("time")
            da = da.isel(time=~da.get_index("time").duplicated(keep="last"))
            attrs = {**base_attrs, "dataset_id": dataset_id, "source_files": ", ".join(Path(f).name for f in files)}
            store = grid_store(dataset_id, spec)
            if path is not None:
                run = pd.Timestamp(path.stem[-8:])
                attrs.update(forecast_run=f"{run:%Y-%m-%d}", source_files=path.name)
                store = store.with_name(f"forecast_{run:%Y%m%d}.zarr")
                da = da.expand_dims(member=[0]) if "member" not in da.dims else da
            ds = _encode(da, variable, units, attrs)
            if store.exists():
                shutil.rmtree(store)
            store.parent.mkdir(parents=True, exist_ok=True)
            ds.to_zarr(store, mode="w", zarr_format=2, consolidated=True)
            print(f"{dataset_id}: {ds.sizes['time']} days "
                  f"({pd.Timestamp(ds.time.values[0]):%Y-%m-%d} .. {pd.Timestamp(ds.time.values[-1]):%Y-%m-%d}) -> {store}")
            written.append(store)
    return written


def main(selected=None):
    for dataset_id, spec in DISCHARGE.items():
        if not selected or dataset_id in selected:
            build(dataset_id, spec, "discharge", "m3 s-1")
    for dataset_id, spec in AIR_TEMPERATURE.items():
        if not selected or dataset_id in selected:
            build(dataset_id, spec, "air_temperature", "degC")


if __name__ == "__main__":
    main(sys.argv[1:])
