"""Per-plant daily discharge and water temperature for the app (data/app_input/environment/).

  python data_processing/environment/build_app_input.py              # track 1 only (current app scope)
  python data_processing/environment/build_app_input.py --tracks 1 2 # later: add the climate scenarios

Track 1 = operations (forecast + reanalysis to verify it); track 2 = climate scenarios. The current minimal
app uses track 1 only; the track 2 grids stay in data/interim/ for later.

Reads plant locations and Water_type from data/app_input/facilities.csv (read only) and the standardized grids in
data/interim/*/europe_daily/. For every plant and discharge source it picks one river grid cell:
the nearest cell on the main river, i.e. the nearest cell within SEARCH_RADIUS_KM whose mean discharge is at
least MAIN_RIVER_SHARE of the largest mean discharge within that radius. (The strictly nearest cell is often a
small side stream.) Water temperature is taken from the same cell of the water temperature grid derived from
that discharge source. The grids contain no plant heat, so the cell represents river water upstream of the
plant's own discharge.

Outputs (long tables, one row per plant, day and dataset; filter by location_id on click):
  discharge.parquet          location_id, date, dataset_id, source, scenario, track, member, forecast_run, value
  water_temperature.parquet  same columns + method, calibrated
  plant_statistics.parquet   location_id, dataset_id, variable, month, quantile, value, n_days (track 2 only)
  plant_cells.csv            the grid cell used per plant and dataset, with distance and status
  sources.json               description of every dataset_id
"""

import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_statistics import QUANTILES
from common import (APP_INPUT, DISCHARGE, WATER_TEMPERATURE, distance_km, grid_store, horizontal_dims,
                    lat_lon_2d, load_plants, water_store)

OUT = APP_INPUT / "environment"
SEARCH_RADIUS_KM = 10
EXTENDED_RADIUS_KM = 20  # used when the 10 km search finds only a small stream (model river displaced)
MIN_RIVER_DISCHARGE = 10.0  # m3/s; below this the cell is flagged as a small stream
MAIN_RIVER_SHARE = 0.5


def latest_store(dataset_id):
    spec = DISCHARGE[dataset_id]
    if spec.get("forecast"):
        runs = sorted(grid_store(dataset_id, spec).parent.glob("forecast_*.zarr"))
        return runs[-1] if runs else None
    store = grid_store(dataset_id, spec)
    return store if store.exists() else None


def mean_discharge_map(stores):
    """Time-mean discharge per cell, averaged over all datasets of one source (control member only).

    Choosing the river cell from this shared map puts every scenario and the forecast of one model
    on the same cell, so they can be compared directly.
    """
    maps = []
    for store in stores:
        q = xr.open_zarr(store)["discharge"]
        maps.append((q.isel(member=0) if "member" in q.dims else q).mean("time").values)
    with warnings.catch_warnings():  # all-NaN sea cells
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(np.stack(maps), axis=0)


def find_cell(mean_map, lat2d, lon2d, plat, plon, allow_extended=True):
    """Main-river cell near a plant as (row, col, distance_km, mean_discharge, status), or None."""
    cell = choose_cell(mean_map, lat2d, lon2d, plat, plon, SEARCH_RADIUS_KM)
    if cell is not None and cell[3] >= MIN_RIVER_DISCHARGE:
        return (*cell, "ok")
    if allow_extended:
        wider = choose_cell(mean_map, lat2d, lon2d, plat, plon, EXTENDED_RADIUS_KM)
        if wider is not None and wider[3] >= MIN_RIVER_DISCHARGE:
            return (*wider, "extended_search")
    return None if cell is None else (*cell, "small_stream")


def choose_cell(mean_map, lat2d, lon2d, plat, plon, radius_km):
    """(row, col, distance_km, mean_discharge) of the main-river cell within radius_km, or None."""
    dist = distance_km(lat2d, lon2d, plat, plon)
    near = np.argwhere(dist <= radius_km)
    if near.size == 0:
        return None
    r0, c0 = near.min(axis=0)
    r1, c1 = near.max(axis=0) + 1
    mean_q = mean_map[r0:r1, c0:c1]
    window_dist = dist[r0:r1, c0:c1]
    mean_q = np.where(window_dist <= radius_km, mean_q, np.nan)
    if np.all(np.isnan(mean_q)) or np.nanmax(mean_q) <= 0:
        return None
    candidates = mean_q >= MAIN_RIVER_SHARE * np.nanmax(mean_q)
    i, j = np.unravel_index(np.argmin(np.where(candidates, window_dist, np.inf)), mean_q.shape)
    return r0 + i, c0 + j, float(window_dist[i, j]), float(mean_q[i, j])


def series_rows(da, location_id, dataset_id, spec, forecast_run, extra=None):
    """Long-format rows for one plant from a point DataArray (time[, member])."""
    if "member" not in da.dims:
        da = da.expand_dims(member=[0])
    frame = da.transpose("time", "member").to_pandas().stack().rename("value").reset_index()
    frame = frame.rename(columns={"time": "date"}).dropna(subset=["value"])
    frame["date"] = frame["date"].dt.date
    frame = frame.assign(location_id=location_id, dataset_id=dataset_id, source=spec["source"],
                         scenario=spec["scenario"], track=spec["track"], forecast_run=forecast_run,
                         **(extra or {}))
    return frame


def monthly_quantiles(frame, variable):
    frame = frame[frame["forecast_run"].isna() & (frame["member"] == 0)]  # forecasts have no climatology
    frame = frame.assign(month=pd.to_datetime(frame["date"]).dt.month)
    grouped = frame.groupby(["location_id", "dataset_id", "month"])["value"]
    q = grouped.quantile(QUANTILES).rename("value").reset_index().rename(columns={"level_3": "quantile"})
    n = grouped.size().rename("n_days").reset_index()
    return q.merge(n, on=["location_id", "dataset_id", "month"]).assign(variable=variable)


def main(tracks=(1,)):
    plants = load_plants()
    discharge_rows, water_rows, cells, sources = [], [], [], {}
    wt_for = {pair["discharge"]: wt_id for wt_id, pair in WATER_TEMPERATURE.items()}
    water_type = dict(zip(plants["location_id"], plants["water_type"]))
    datasets = {d: spec for d, spec in DISCHARGE.items() if spec["track"] in tracks}
    stores = {d: latest_store(d) for d in datasets}

    # 1. One river cell per model (source) and plant, shared by all its scenarios and the forecast.
    by_source = {}
    for dataset_id, store in stores.items():
        if store is not None:
            by_source.setdefault(DISCHARGE[dataset_id]["source"], []).append(store)
    chosen = {}  # (source, location_id) -> (row, col, distance_km, mean_discharge, status) or None
    for source, source_stores in by_source.items():
        lat2d, lon2d = lat_lon_2d(xr.open_zarr(source_stores[0]))
        mean_map = mean_discharge_map(source_stores)
        for plant in plants.itertuples():
            sea = water_type[plant.location_id] == "Seawater"
            cell = find_cell(mean_map, lat2d, lon2d, plant.lat, plant.lon, allow_extended=not sea)
            chosen[source, plant.location_id] = cell
            record = dict(location_id=plant.location_id, source=source,
                          cooling_water=water_type[plant.location_id], status="no_river_cell")
            if cell is not None:
                r, c, dist, mean_q, status = cell
                if sea:  # a river may be nearby, but it is not this plant's cooling water
                    status = "sea_cooled"
                record.update(status=status, row=r, col=c, cell_lat=round(float(lat2d[r, c]), 4),
                              cell_lon=round(float(lon2d[r, c]), 4), distance_km=round(dist, 2),
                              mean_discharge=round(mean_q, 1))
            cells.append(record)
        counts = pd.Series([c["status"] for c in cells if c["source"] == source]).value_counts().to_dict()
        print(f"{source}: river cells {counts} (mean discharge over {len(source_stores)} dataset(s))")

    # 2. Daily series at those cells for every dataset.
    for dataset_id, spec in datasets.items():
        store = stores[dataset_id]
        if store is None:
            print(f"{dataset_id}: no grid, skipped (run build_grids.py)")
            continue
        ds = xr.open_zarr(store)
        forecast_run = ds.attrs.get("forecast_run") or None
        wt_id = wt_for.get(dataset_id)
        wt_ds = xr.open_zarr(water_store(wt_id)) if wt_id and water_store(wt_id).exists() else None
        rows, cols = horizontal_dims(ds["discharge"])
        years = ds["time"].dt.year.values
        sources[dataset_id] = dict(variable="discharge", units="m3 s-1", label=spec["label"], source=spec["source"],
                                   scenario=spec["scenario"], track=spec["track"], forecast_run=forecast_run,
                                   period=f"{str(ds.time.values[0])[:10]}..{str(ds.time.values[-1])[:10]}",
                                   years=f"{years.min()}-{years.max()}",
                                   grid_store=str(store.relative_to(APP_INPUT.parents[1])))
        if wt_ds is not None:
            sources[wt_id] = dict(variable="water_temperature", units="degC", label=wt_ds.attrs["label"],
                                  source=spec["source"], scenario=spec["scenario"], track=spec["track"],
                                  forecast_run=forecast_run, method=wt_ds.attrs["method"],
                                  calibrated=wt_ds.attrs["calibrated"], discharge_dataset=dataset_id,
                                  air_temperature_dataset=wt_ds.attrs["air_temperature_source"],
                                  period=f"{str(wt_ds.time.values[0])[:10]}..{str(wt_ds.time.values[-1])[:10]}",
                                  grid_store=str(water_store(wt_id).relative_to(APP_INPUT.parents[1])))
        for plant in plants.itertuples():
            cell = chosen[spec["source"], plant.location_id]
            if cell is None:
                continue
            point = {rows: cell[0], cols: cell[1]}
            discharge_rows.append(series_rows(ds["discharge"].isel(point).load(), plant.location_id,
                                              dataset_id, spec, forecast_run))
            if wt_ds is not None:
                water_rows.append(series_rows(
                    wt_ds["water_temperature"].isel(point).load(), plant.location_id, wt_id, spec,
                    forecast_run, extra=dict(method=wt_ds.attrs["method"],
                                             calibrated=wt_ds.attrs["calibrated"] == "yes")))
        print(f"{dataset_id}: series extracted" + (f", water temperature from {wt_id}" if wt_ds is not None
                                                     else ", no water temperature"))

    OUT.mkdir(parents=True, exist_ok=True)
    columns = ["location_id", "date", "dataset_id", "source", "scenario", "track", "member", "forecast_run", "value"]
    discharge = pd.concat(discharge_rows, ignore_index=True)[columns]
    water = pd.concat(water_rows, ignore_index=True)[columns + ["method", "calibrated"]]
    for frame in (discharge, water):
        frame["value"] = frame["value"].astype("float32").round(3)
        frame.sort_values(["location_id", "dataset_id", "member", "date"], inplace=True)
    discharge.to_parquet(OUT / "discharge.parquet", index=False)
    water.to_parquet(OUT / "water_temperature.parquet", index=False)
    stats_path = OUT / "plant_statistics.parquet"
    if 2 in tracks:  # climate statistics belong to the planning track
        stats = pd.concat([monthly_quantiles(discharge, "discharge"),
                           monthly_quantiles(water, "water_temperature")], ignore_index=True)
        stats[["location_id", "dataset_id", "variable", "month", "quantile", "value", "n_days"]].to_parquet(
            stats_path, index=False)
    else:
        stats = pd.DataFrame()
        stats_path.unlink(missing_ok=True)  # stale output of an earlier run with track 2
    pd.DataFrame(cells).to_csv(OUT / "plant_cells.csv", index=False)
    meta = {"created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tracks": list(tracks),
            "plants": str(Path("data/app_input/facilities.csv")),
            "cell_selection": (
                f"nearest cell within {SEARCH_RADIUS_KM} km with mean discharge >= {MAIN_RIVER_SHARE:.0%} of the "
                f"largest within that radius. If that river carries < {MIN_RIVER_DISCHARGE:g} m3/s, the search is "
                f"repeated within {EXTENDED_RADIUS_KM} km (status extended_search; not for sea-cooled plants); "
                f"otherwise status small_stream."),
            "status_values": {
                "ok": "main river within the normal search radius",
                "sea_cooled": "plant cools with sea or estuary water (facilities.csv Water_type); river values are "
                              "for reference only",
                "extended_search": f"river found only within {EXTENDED_RADIUS_KM} km (model river displaced)",
                "small_stream": f"no river >= {MIN_RIVER_DISCHARGE:g} m3/s nearby: sea-, lake- or reservoir-cooled "
                                "plant, or the river is missing in this model; do not use as cooling water",
                "no_river_cell": "no grid cell with discharge nearby"},
            "datasets": sources}
    (OUT / "sources.json").write_text(json.dumps(meta, indent=2))
    print(f"discharge: {len(discharge)} rows, water temperature: {len(water)} rows, statistics: {len(stats)} rows "
          f"-> {OUT}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tracks", type=int, nargs="+", default=[1], choices=[1, 2])
    main(tuple(parser.parse_args().tracks))
