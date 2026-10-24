"""Monthly quantile grids of daily discharge and water temperature, per source and scenario (climate track).

  python data_processing/environment/build_statistics.py

Output: data/interim/<source>/statistics/<scenario>.zarr with variable `<variable>_quantile`,
dimensions (month, quantile, lat/lon or y/x). From these, the probability of exceeding any limit
(e.g. a plant's 28 degC permit) or falling below a low-flow level can be read for any grid cell,
including new plant locations in planning mode: P(value > limit) ~ 1 - (quantile level at which the
monthly distribution crosses the limit). Forecast stores are skipped.

The statistics describe the period covered by the downloaded data (attribute `period`); with the
current samples (1 month to 1 year per scenario) they are placeholders until longer periods are
downloaded. Rerun this script after build_grids.py / water_temperature.py.
"""

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INTERIM, SPACE_CHUNK, horizontal_dims

QUANTILES = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
MAX_BLOCK_BYTES = 400e6


def stores():
    for store in sorted(INTERIM.glob("*/europe_daily/*.zarr")):
        if not store.name.startswith("forecast"):
            yield store


def build(store):
    ds = xr.open_zarr(store)
    variable = next(v for v in ("discharge", "water_temperature") if v in ds) if (
        "discharge" in ds or "water_temperature" in ds) else None
    if variable is None:
        return None  # air temperature is an input only
    da = ds[variable]
    if "member" in da.dims:
        da = da.isel(member=0, drop=True)
    rows, cols = horizontal_dims(da)
    months = da["time"].dt.month.values
    present = np.unique(months)
    n_time, n_cols = da.sizes["time"], da.sizes[cols]
    block_rows = max(1, int(MAX_BLOCK_BYTES // (n_time * n_cols * 4)) // SPACE_CHUNK * SPACE_CHUNK) or 1

    out = np.full((12, len(QUANTILES), da.sizes[rows], n_cols), np.nan, dtype="float32")
    for start in range(0, da.sizes[rows], block_rows):
        block = slice(start, min(start + block_rows, da.sizes[rows]))
        values = da.isel({rows: block}).transpose("time", rows, cols).values
        # Cells are either complete or all-NaN (sea, no river), so the fast np.quantile is exact here;
        # all-NaN cells simply stay NaN. (np.nanquantile gives the same result but is ~100x slower.)
        for m in present:
            out[m - 1, :, block] = np.quantile(values[months == m], QUANTILES, axis=0)

    coords = {"month": np.arange(1, 13), "quantile": QUANTILES,
              **{c: ds[c] for c in ("lat", "lon") if c in ds.coords}}
    stats = xr.Dataset({f"{variable}_quantile": (("month", "quantile", rows, cols), out)}, coords=coords)
    stats["n_days"] = ("month", np.array([(months == m).sum() for m in range(1, 13)]))
    stats[f"{variable}_quantile"].attrs = {"units": da.attrs.get("units", "")}
    years = da["time"].dt.year.values
    stats.attrs = {**ds.attrs, "statistic": "quantiles of daily values per calendar month",
                   "period": f"{years.min()}-{years.max()}",
                   "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    target = store.parent.parent / "statistics" / store.name
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    stats.chunk({"month": 1, rows: SPACE_CHUNK * 4, cols: SPACE_CHUNK * 4}).to_zarr(
        target, mode="w", zarr_format=2, consolidated=True)
    print(f"{store.parent.parent.name}/{store.stem}: {variable}, period {stats.attrs['period']}, "
          f"months with data {[int(m) for m in present]} -> {target}")
    return target


def main():
    for store in stores():
        build(store)


if __name__ == "__main__":
    main()
