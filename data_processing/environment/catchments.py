"""Plant-level daily discharge, water temperature and inputs for curtailment from the C3S catchment discharge.

The catchment version (E-HYPEcatch) gives daily discharge per E-HYPE sub-basin instead of a 5 km grid, which
makes it ~27x smaller. Its files only carry sub-basin IDs, so plants are located with the E-HYPE sub-basin
map (data/raw/ehype_subbasins/, CC BY-SA 4.0):

  1. the sub-basin the plant lies in, if its mean discharge is >= MIN_RIVER_DISCHARGE (10 m3/s)   -> ok
  2. otherwise the nearest sub-basin within 10 km carrying >= 50 % of the largest flow there      -> ok
  3. otherwise the same search within 20 km (not for sea-cooled plants)                          -> extended_search
  4. otherwise the best candidate found, flagged                                                 -> small_stream

The assignment is written to data/interim/c3s_catchment/plant_subbasins.csv. Air temperature comes from the
nearest cell of the matching EURO-CORDEX grid (data/interim/euro_cordex/europe_daily/, build_grids.py).
"""

import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from build_app_input import EXTENDED_RADIUS_KM, MAIN_RIVER_SHARE, MIN_RIVER_DISCHARGE, SEARCH_RADIUS_KM
from common import AIR_TEMPERATURE, CATCHMENT, INTERIM, SUBBASINS, distance_km, files_for, grid_store, \
    horizontal_dims, lat_lon_2d

ASSIGNMENT = INTERIM / "c3s_catchment" / "plant_subbasins.csv"


def read_discharge(spec, ids=None):
    """Daily discharge (time, id) of one experiment from all its zip files; optionally only some sub-basins."""
    parts = []
    with tempfile.TemporaryDirectory(dir=INTERIM, prefix=".tmp_") as tmp:
        for path in files_for(spec):
            if not zipfile.is_zipfile(path):  # e.g. a download still in progress
                print(f"  skipping {Path(path).name}: not a complete zip file (download still running?)")
                continue
            with zipfile.ZipFile(path) as z:
                name = next(n for n in z.namelist() if n.endswith(".nc"))
                z.extract(name, tmp)
            with xr.open_dataset(Path(tmp) / name) as ds:
                q = ds[spec["var"]]
                parts.append((q.sel(id=ids) if ids is not None else q).load())
            (Path(tmp) / name).unlink()
    if not parts:
        return None
    q = xr.concat(parts, "time").sortby("time")
    return q.isel(time=~q.get_index("time").duplicated(keep="last"))


def mean_discharge_by_id(specs):
    """Time-mean discharge per sub-basin over all downloaded catchment files (all experiments)."""
    means = [q.mean("time").to_series() for q in (read_discharge(s) for s in specs) if q is not None]
    return pd.concat(means, axis=1).mean(axis=1) if means else pd.Series(dtype=float)


def load_subbasins():
    import shapefile
    from shapely.geometry import shape

    reader = shapefile.Reader(str(SUBBASINS))
    return [(rec["SUBID"], shape(shp.__geo_interface__)) for rec, shp in zip(reader.records(), reader.shapes())]


def _distance_to(geom, lat, lon):
    from shapely.geometry import Point
    from shapely.ops import nearest_points

    point = Point(lon, lat)
    if geom.contains(point):
        return 0.0
    near = nearest_points(point, geom)[1]
    return float(distance_km(near.y, near.x, lat, lon))


def assign_plants(plants, mean_q):
    """One sub-basin per plant (see module docstring), as a DataFrame with status."""
    subbasins = [(sid, g) for sid, g in load_subbasins() if sid in mean_q.index]
    bounds = np.array([g.bounds for _, g in subbasins])
    rows = []
    for p in plants.itertuples():
        def candidates(radius):
            dlat, dlon = radius / 111.0, radius / (111.0 * np.cos(np.radians(p.lat)))
            idx = np.where((bounds[:, 0] <= p.lon + dlon) & (bounds[:, 2] >= p.lon - dlon) &
                           (bounds[:, 1] <= p.lat + dlat) & (bounds[:, 3] >= p.lat - dlat))[0]
            c = pd.DataFrame([(subbasins[k][0], _distance_to(subbasins[k][1], p.lat, p.lon)) for k in idx],
                             columns=["subid", "distance_km"])
            c = c[c["distance_km"] <= radius].assign(mean_discharge=lambda x: x["subid"].map(mean_q))
            return c

        def main_river(c):
            return c[c["mean_discharge"] >= MAIN_RIVER_SHARE * c["mean_discharge"].max()].sort_values(
                "distance_km").iloc[0]

        near = candidates(SEARCH_RADIUS_KM)
        inside = near[near["distance_km"] == 0]
        pick, status = None, "no_river_cell"
        if len(inside) and inside["mean_discharge"].max() >= MIN_RIVER_DISCHARGE:
            pick, status = inside.sort_values("mean_discharge").iloc[-1], "ok"
        elif len(near) and near["mean_discharge"].max() >= MIN_RIVER_DISCHARGE:
            pick, status = main_river(near), "ok"
        else:
            wide = candidates(EXTENDED_RADIUS_KM) if p.water_type != "Seawater" else near.iloc[:0]
            if len(wide) and wide["mean_discharge"].max() >= MIN_RIVER_DISCHARGE:
                pick, status = main_river(wide), "extended_search"
            elif len(near):
                pick, status = main_river(near), "small_stream"
        rows.append(dict(location_id=p.location_id, name=p.name, status=status,
                         subid=None if pick is None else int(pick["subid"]),
                         distance_km=None if pick is None else round(float(pick["distance_km"]), 2),
                         mean_discharge=None if pick is None else round(float(pick["mean_discharge"]), 1)))
    assignment = pd.DataFrame(rows)
    ASSIGNMENT.parent.mkdir(parents=True, exist_ok=True)
    assignment.to_csv(ASSIGNMENT, index=False)
    return assignment


def air_temperature_at(air_id, plants):
    """Daily air temperature (time x location_id) at the nearest cell of an air temperature grid, or None."""
    store = grid_store(air_id, AIR_TEMPERATURE[air_id])
    if not store.exists():
        return None
    ds = xr.open_zarr(store)
    lat, lon = lat_lon_2d(ds)
    rows, cols = horizontal_dims(ds["air_temperature"])
    series = {}
    for p in plants.itertuples():
        i, j = np.unravel_index(np.argmin(distance_km(lat, lon, p.lat, p.lon)), lat.shape)
        series[p.location_id] = ds["air_temperature"].isel({rows: i, cols: j}).to_series()
    return pd.DataFrame(series)


def plant_series(plants):
    """Daily q (m3/s) and ta (degC) per plant and experiment, plus the sub-basin assignment."""
    specs = [s for s in CATCHMENT.values() if files_for(s)]
    if not specs:
        return None, None
    assignment = assign_plants(plants, mean_discharge_by_id(specs))
    located = assignment.dropna(subset=["subid"])
    out = {}
    for spec in specs:
        q = read_discharge(spec, ids=located["subid"].astype(int).unique())
        q_by_plant = pd.DataFrame({r.location_id: q.sel(id=int(r.subid)).to_series() for r in located.itertuples()})
        ta = air_temperature_at(spec["air"], plants[plants["location_id"].isin(located["location_id"])])
        out[spec["scenario"]] = dict(spec=spec, q=q_by_plant, ta=ta)
    return out, assignment
