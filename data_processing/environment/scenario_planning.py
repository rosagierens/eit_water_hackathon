"""DRAFT: scenario planning statistics per plant (track 2). See the scenario planning draft in the chat/README.

  python data_processing/environment/scenario_planning.py

For every climate scenario with discharge + air temperature. Preferred source: the C3S catchment discharge
(E-HYPEcatch, see catchments.py) + EURO-CORDEX at the plant; fallback: the gridded C3S sample (E-HYPEgrid).
  1. daily curtailment at each plant, with the same river cell and formula as the forecast
     (build_app_input.find_cell, build_curtailment.curtailment)
  2. monthly statistics per plant, scenario and calendar month, across the available years:
       p_reduced_month        share of years whose monthly mean curtailment is > REDUCED_MONTH_PCT (10 %)
       curtailed_pct_p10/50/90  monthly mean curtailed share of capacity (%) across years
       days_over_25pct        mean number of days per month with daily curtailment > EXTREME_DAY_PCT (25 %)
       p_day_over_25pct       share of years with at least one such day in the month
       longest_spell_days     longest run of consecutive extreme days (worst year)
       lost_energy_gwh        mean lost energy per month
       delta_*                scenario minus the model's own historical run (option 1: change, not absolute)

Outputs:
  data/interim/curtailment/scenario_daily.parquet          daily curtailment per plant and scenario
  data/app_input/environment/scenario_monthly.parquet      monthly statistics (draft, for the planning view)

With the current sample data each scenario has ONE year, so probabilities are 0 or 1 (n_years = 1).
The format stays the same when 30-year periods are downloaded.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_app_input import find_cell, mean_discharge_map
from build_curtailment import curtailment, plant_inputs
from water_temperature import model as water_temperature_model
from common import APP_INPUT, DISCHARGE, INTERIM, WATER_TEMPERATURE, grid_store, horizontal_dims, lat_lon_2d, \
    load_plants, water_store

REDUCED_MONTH_PCT = 10.0
EXTREME_DAY_PCT = 25.0
REFERENCE = {"c3s_hydrology": "historical", "c3s_catchment": "historical"}  # the model's own historical run


def climate_pairs():
    """Track-2 discharge datasets that have a matching water temperature grid."""
    for wt_id, pair in WATER_TEMPERATURE.items():
        spec = DISCHARGE[pair["discharge"]]
        if spec["track"] == 2 and grid_store(pair["discharge"], spec).exists() and water_store(wt_id).exists():
            yield pair["discharge"], wt_id, spec


def daily_curtailment_catchment():
    """Daily curtailment from the catchment discharge (preferred: long periods at a small size), or None."""
    import catchments

    plants = load_plants()
    series, assignment = catchments.plant_series(plants)
    if not series:
        return None
    params = plant_inputs()
    params = params[params["status"] == "ok"].set_index("location_id")
    status = assignment.set_index("location_id")["status"]
    frames = []
    for scenario, item in series.items():
        q, ta = item["q"], item["ta"]
        if ta is None:
            print(f"catchment {scenario}: no air temperature grid ({item['spec']['air']}), skipped")
            continue
        days = q.index.intersection(ta.index)
        ids = [i for i in q.columns if i in params.index and i in ta.columns]
        if len(days) < 2 or not ids:
            print(f"catchment {scenario}: discharge and air temperature share {len(days)} day(s), skipped")
            continue
        qv, tv = q.loc[days, ids].to_numpy("float32"), ta.loc[days, ids].to_numpy("float32")
        tw = water_temperature_model(qv, tv)  # same uncalibrated model as the gridded water temperature
        for k, pid in enumerate(ids):
            p = params.loc[pid]
            frames.append(pd.DataFrame({"date": days, "q": qv[:, k], "t_river": tw[:, k]}).assign(
                location_id=pid, dataset_id=f"curtailment_{scenario}", source="c3s_catchment", scenario=scenario,
                river_cell_status=status[pid], p_el_mw=p.p_el_mw, q_river_cooling_mw=p.q_river_cooling_mw,
                t_limit_c=p.t_limit_c, dt_limit_c=p.dt_limit_c))
        print(f"catchment {scenario}: {len(ids)} plants, {len(days)} days ({days.min():%Y-%m-%d} .. {days.max():%Y-%m-%d})")
    if not frames:
        return None
    daily = curtailment(pd.concat(frames, ignore_index=True))
    daily["curtailed_pct"] = (1 - daily["available_fraction"]) * 100
    return daily


def daily_curtailment():
    plants = load_plants()
    params = plant_inputs()
    params = params[params["status"] == "ok"]
    pairs = list(climate_pairs())
    frames, cells = [], {}
    for source in {spec["source"] for _, _, spec in pairs}:
        stores = [grid_store(q_id, spec) for q_id, _, spec in pairs if spec["source"] == source]
        lat2d, lon2d = lat_lon_2d(xr.open_zarr(stores[0]))
        mean_map = mean_discharge_map(stores)
        for p in plants.itertuples():
            cells[source, p.location_id] = find_cell(mean_map, lat2d, lon2d, p.lat, p.lon,
                                                     allow_extended=p.water_type != "Seawater")
    for q_id, wt_id, spec in pairs:
        q_ds, t_ds = xr.open_zarr(grid_store(q_id, spec)), xr.open_zarr(water_store(wt_id))
        rows, cols = horizontal_dims(q_ds["discharge"])
        for p in params.itertuples():
            cell = cells.get((spec["source"], p.location_id))
            if cell is None:
                continue
            point = {rows: cell[0], cols: cell[1]}
            frame = pd.DataFrame({"date": pd.to_datetime(q_ds["time"].values),
                                  "q": q_ds["discharge"].isel(point).values,
                                  "t_river": t_ds["water_temperature"].isel(point).values})
            frames.append(frame.assign(location_id=p.location_id, dataset_id=f"curtailment_{spec['scenario']}",
                                       source=spec["source"], scenario=spec["scenario"], river_cell_status=cell[4],
                                       p_el_mw=p.p_el_mw, q_river_cooling_mw=p.q_river_cooling_mw,
                                       t_limit_c=p.t_limit_c, dt_limit_c=p.dt_limit_c))
        print(f"{q_id} + {wt_id}: daily series for {len(params)} plants")
    daily = curtailment(pd.concat(frames, ignore_index=True))
    daily["curtailed_pct"] = (1 - daily["available_fraction"]) * 100
    return daily


def longest_run(flags):
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def monthly_statistics(daily):
    d = daily.dropna(subset=["curtailed_pct"]).assign(year=lambda x: x["date"].dt.year,
                                                       month=lambda x: x["date"].dt.month)
    keys = ["location_id", "source", "scenario", "month"]
    per_year = d.groupby(keys + ["year"]).agg(
        curtailed_pct=("curtailed_pct", "mean"),
        extreme_days=("curtailed_pct", lambda v: int((v > EXTREME_DAY_PCT).sum())),
        longest_spell=("curtailed_pct", lambda v: longest_run(v.to_numpy() > EXTREME_DAY_PCT)),
        lost_energy_gwh=("value", lambda v: v.sum() * 24 / 1000),
    ).reset_index()
    g = per_year.groupby(keys)
    stats = pd.DataFrame({
        "n_years": g.size(),
        "period": g["year"].agg(lambda y: f"{y.min()}-{y.max()}"),
        "p_reduced_month": g["curtailed_pct"].agg(lambda v: (v > REDUCED_MONTH_PCT).mean()),
        "curtailed_pct_p10": g["curtailed_pct"].quantile(0.1),
        "curtailed_pct_p50": g["curtailed_pct"].quantile(0.5),
        "curtailed_pct_p90": g["curtailed_pct"].quantile(0.9),
        "days_over_25pct": g["extreme_days"].mean(),
        "p_day_over_25pct": g["extreme_days"].agg(lambda v: (v > 0).mean()),
        "longest_spell_days": g["longest_spell"].max(),
        "lost_energy_gwh": g["lost_energy_gwh"].mean(),
    }).reset_index()
    # Option 1: change against the model's own historical run, same plant and month.
    ref = stats[stats["scenario"] == stats["source"].map(REFERENCE)]
    metrics = ["p_reduced_month", "curtailed_pct_p50", "days_over_25pct", "lost_energy_gwh"]
    stats = stats.merge(ref[["location_id", "source", "month"] + metrics], on=["location_id", "source", "month"],
                        how="left", suffixes=("", "_ref"))
    for m in metrics:
        stats[f"delta_{m}"] = stats[m] - stats.pop(f"{m}_ref")
    cell_status = daily.drop_duplicates(["location_id", "source"]).set_index(["location_id", "source"])
    stats["river_cell_status"] = [cell_status.at[(l, s), "river_cell_status"]
                                  for l, s in zip(stats["location_id"], stats["source"])]
    stats["dataset_id"] = "scenario_" + stats["scenario"]
    return stats.round(3)


def main():
    daily = daily_curtailment_catchment()
    if daily is None:  # no catchment files yet: fall back to the gridded sample years
        print("no catchment discharge found; using the gridded C3S sample")
        daily = daily_curtailment()
    out_daily = INTERIM / "curtailment" / "scenario_daily.parquet"
    out_daily.parent.mkdir(parents=True, exist_ok=True)
    daily[["location_id", "date", "dataset_id", "source", "scenario", "value", "curtailed_pct", "available_fraction",
           "limiting_limit", "river_cell_status"]].to_parquet(out_daily, index=False)
    stats = monthly_statistics(daily)
    out = APP_INPUT / "environment" / "scenario_monthly.parquet"
    stats.to_parquet(out, index=False)
    print(f"daily: {len(daily)} rows -> {out_daily}\nmonthly statistics: {len(stats)} rows "
          f"({stats['location_id'].nunique()} plants, scenarios {sorted(stats['scenario'].unique())}, "
          f"years per scenario {sorted(stats['n_years'].unique())}) -> {out}")


if __name__ == "__main__":
    main()
