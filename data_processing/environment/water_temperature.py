"""Derive daily river water temperature grids from discharge + air temperature (see methodology_water_temperature.md).

  python data_processing/environment/water_temperature.py            # all pairings
  python data_processing/environment/water_temperature.py wt_rcp_4_5

Output: data/interim/water_temperature/europe_daily/<scenario>.zarr on the grid of the discharge source.

Model: air2stream (Toffolon & Piccolroaz, 2015) restricted to its first four parameters, i.e. water temperature
relaxes towards an equilibrium a1/a3 + (a2/a3) * Ta with time constant delta/a3, where delta = (Q / Qmean)^a4:

    Tw(t) = Teq(t) + (Tw(t-1) - Teq(t)) * exp(-a3 / delta(t))      (exact solution over one day, always stable)

UNCALIBRATED: the default parameters below give Teq = 5 + 0.75 * Ta (a common linear air-water relation for
mid-latitude rivers, cf. Stefan & Preud'homme, 1993) and a 3-day response time at mean flow. They are
placeholders until the model is calibrated against observed river temperature; every output is labelled with
`method` so calibrated values can replace them without changing the format.
"""

import shutil
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr
from scipy.spatial import cKDTree

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (AIR_TEMPERATURE, DISCHARGE, SPACE_CHUNK, TIME_CHUNK, WATER_TEMPERATURE, grid_store,
                    horizontal_dims, lat_lon_2d, water_store)

METHOD = "air2stream-4p-uncalibrated-v0"
DEFAULT_PARAMS = dict(a1=5.0 / 3, a2=0.75 / 3, a3=1.0 / 3, a4=0.5)
BLOCK_ROWS = 2 * SPACE_CHUNK  # rows of the discharge grid processed at once (multiple of the chunk size)


def _unit_vectors(lat, lon):
    lat, lon = np.radians(lat.ravel()), np.radians(lon.ravel())
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def nearest_index(src_ds, dst_ds):
    """For each destination cell, the flat index of the nearest source cell (works for any grid type)."""
    tree = cKDTree(_unit_vectors(*lat_lon_2d(src_ds)))
    return tree.query(_unit_vectors(*lat_lon_2d(dst_ds)))[1].reshape(lat_lon_2d(dst_ds)[0].shape)


def model(q, ta, params=DEFAULT_PARAMS):
    """Water temperature (time, cells) from discharge and air temperature (time, cells)."""
    a1, a2, a3, a4 = (params[k] for k in ("a1", "a2", "a3", "a4"))
    with warnings.catch_warnings():  # cells without any discharge (sea, land) are all-NaN
        warnings.simplefilter("ignore", RuntimeWarning)
        q_mean = np.nanmean(q, axis=0)
    theta = np.clip(q / np.where(q_mean > 0, q_mean, np.nan), 0.05, 20)
    decay = np.exp(-a3 / theta ** a4)
    t_eq = (a1 + a2 * ta) / a3
    tw = np.empty_like(t_eq)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        tw[0] = (a1 + a2 * np.nanmean(ta[:7], axis=0)) / a3  # start in equilibrium with the first week
    for t in range(1, len(tw)):
        tw[t] = t_eq[t] + (tw[t - 1] - t_eq[t]) * decay[t]
    return np.maximum(tw, 0.0)


def build(wt_id, pair):
    q_id, air_id = pair["discharge"], pair["air"]
    q_spec, air_spec = DISCHARGE[q_id], AIR_TEMPERATURE[air_id]
    q_stores = sorted(grid_store(q_id, q_spec).parent.glob(
        "forecast_*.zarr" if q_spec.get("forecast") else f"{q_spec['scenario']}.zarr"))
    air_stores = sorted(grid_store(air_id, air_spec).parent.glob(
        "forecast_*.zarr" if air_spec.get("forecast") else f"{air_spec['scenario']}.zarr"))
    if not q_stores or not air_stores:
        print(f"{wt_id}: missing {q_id if not q_stores else air_id} grid, skipped (run build_grids.py)")
        return None
    q_ds, air_ds = xr.open_zarr(q_stores[-1]), xr.open_zarr(air_stores[-1])  # forecasts: latest runs
    days = np.intersect1d(q_ds.time.values, air_ds.time.values)
    if len(days) < 2:
        print(f"{wt_id}: discharge and air temperature share {len(days)} day(s), skipped")
        return None
    q = q_ds["discharge"].sel(time=days)
    air = air_ds["air_temperature"].sel(time=days).load()
    air_flat = air.values.reshape(len(days), -1)
    index = nearest_index(air_ds, q_ds)
    rows, cols = horizontal_dims(q)
    has_member = "member" in q.dims

    store = water_store(wt_id)
    if store.exists():
        shutil.rmtree(store)
    store.parent.mkdir(parents=True, exist_ok=True)
    template = xr.zeros_like(q, dtype="float32").to_dataset(name="water_temperature")
    template["water_temperature"].attrs = {"units": "degC"}
    template.attrs = {
        "dataset_id": wt_id, "source": "water_temperature", "scenario": q_spec["scenario"],
        "track": str(q_spec["track"]), "label": f"Water temperature from {q_spec['label']} + {air_spec['label']}",
        "discharge_source": q_id, "air_temperature_source": air_id, "method": METHOD,
        "parameters": str(DEFAULT_PARAMS), "calibrated": "no",
        "forecast_run": q_ds.attrs.get("forecast_run", ""),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "time_convention": "calendar day (UTC) described by the daily value",
    }
    chunks = {"time": min(TIME_CHUNK, len(days)), rows: SPACE_CHUNK, cols: SPACE_CHUNK}
    if has_member:
        chunks["member"] = 1
    template.chunk(chunks).to_zarr(store, mode="w", zarr_format=2, compute=False, consolidated=True)

    for start in range(0, q.sizes[rows], BLOCK_ROWS):
        block = slice(start, min(start + BLOCK_ROWS, q.sizes[rows]))
        q_block = q.isel({rows: block}).load()
        idx = index[block].ravel()
        ta = air_flat[:, idx]
        order = (["member"] if has_member else []) + ["time", rows, cols]
        qv_all = q_block.transpose(*order).values
        qv_all = qv_all if has_member else qv_all[None]
        out = np.empty(qv_all.shape, dtype="float32")
        for m, qv in enumerate(qv_all):  # one ensemble member at a time
            tw = model(qv.reshape(len(days), -1), ta).reshape(qv.shape)
            tw[np.isnan(qv)] = np.nan
            out[m] = tw
        out = xr.DataArray(out if has_member else out[0], dims=order).transpose(*q.dims)
        xr.Dataset({"water_temperature": out}).to_zarr(store, region={rows: block}, zarr_format=2)
    print(f"{wt_id}: {len(days)} days ({str(days[0])[:10]} .. {str(days[-1])[:10]}) -> {store}")
    return store


def main(selected=None):
    for wt_id, pair in WATER_TEMPERATURE.items():
        if not selected or wt_id in selected:
            build(wt_id, pair)


if __name__ == "__main__":
    main(sys.argv[1:])
