"""Daily curtailment per plant from river discharge and water temperature (methodology_cooling_constrain.md).

  python data_processing/environment/build_curtailment.py      (after build_app_input.py)

Inputs (read only):
  data/app_input/facilities.csv                       Capacity_MW, Q_river_MW_th, Temp_limit, Temp_change_limit
  data/app_input/environment/discharge.parquet        Q_river (m3/s)
  data/app_input/environment/water_temperature.parquet  T_river (degC)

Per plant, day, dataset and ensemble member:
  allowed rise   dT = min(T_limit - T_river, dT_limit)   (only the limit that exists is used)
  Q_heat_max     = rho * c_p * Q_river * dT              (MW_th)
  f              = min(1, max(0, Q_heat_max) / Q_river_cooling)
  curtailment    = (1 - f) * P_el                        (MW_el)

Outputs:
  data/app_input/environment/curtailment.parquet         same columns as discharge.parquet (value = curtailed MW) + available_fraction,
                              available_mw, q_heat_max_mw, limiting_limit, river_cell_status, method, calibrated
  data/interim/curtailment/curtailment_inputs.csv
                              the plant parameters used, and why a plant has no curtailment (status)
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import APP_INPUT, FACILITIES, INTERIM

ENV = APP_INPUT / "environment"
RECORD = INTERIM / "curtailment" / "curtailment_inputs.csv"  # processing record, not read by the app
RHO, CP = 1000.0, 4186.0  # kg/m3, J/(kg K)
METHOD = "cooling-constraint-v1"
KEYS = ["location_id", "date", "source", "scenario", "track", "member", "forecast_run"]


def plant_inputs():
    """Plant parameters from facilities.csv (read only), with a status per plant."""
    f = pd.read_csv(FACILITIES)
    plants = pd.DataFrame({
        "location_id": f["Location_ID"], "name": f["Name"], "p_el_mw": f["Capacity_MW"],
        "q_river_cooling_mw": f["Q_river_MW_th"], "t_limit_c": f["Temp_limit"], "dt_limit_c": f["Temp_change_limit"],
    })
    plants["status"] = "ok"
    plants.loc[plants["t_limit_c"].isna() & plants["dt_limit_c"].isna(), "status"] = "no_temperature_limit"
    plants.loc[plants["q_river_cooling_mw"].isna(), "status"] = "no_cooling_data"
    return plants


def curtailment(frame):
    """Add the curtailment columns to rows with q (m3/s), t_river (degC) and the plant parameters."""
    rise_abs = frame["t_limit_c"] - frame["t_river"]
    rise = np.fmin(rise_abs, frame["dt_limit_c"])  # fmin: a missing limit is ignored, not propagated
    q_heat_max = RHO * CP * frame["q"] * rise / 1e6  # W -> MW_th
    cooling = frame["q_river_cooling_mw"]
    fraction = np.where(cooling > 0, np.minimum(1.0, np.maximum(0.0, q_heat_max) / cooling), 1.0)
    fraction = np.where(rise.isna() | frame["q"].isna() | frame["t_river"].isna(), np.nan, fraction)
    limiting = np.where(rise_abs.notna() & (rise_abs.fillna(np.inf) <= frame["dt_limit_c"].fillna(np.inf)),
                        "T_limit", "dT_limit")
    return frame.assign(q_heat_max_mw=q_heat_max.round(1), available_fraction=np.round(fraction, 4),
                        available_mw=(fraction * frame["p_el_mw"]).round(1),
                        value=((1 - fraction) * frame["p_el_mw"]).round(1), limiting_limit=limiting)


def main():
    plants = plant_inputs()
    q = pd.read_parquet(ENV / "discharge.parquet").rename(columns={"value": "q"})
    t = pd.read_parquet(ENV / "water_temperature.parquet").rename(columns={"value": "t_river"})
    # Water temperature is derived from one discharge dataset; pair them through sources.json.
    meta = json.loads((ENV / "sources.json").read_text())
    q_for_wt = {wt: info["discharge_dataset"] for wt, info in meta["datasets"].items()
                if info.get("variable") == "water_temperature"}
    t["discharge_dataset"] = t["dataset_id"].map(q_for_wt)
    rows = q.merge(t.drop(columns=["dataset_id", "method", "calibrated"]),
                   left_on=KEYS + ["dataset_id"], right_on=KEYS + ["discharge_dataset"], how="inner")
    rows = rows.merge(plants[plants["status"] == "ok"], on="location_id", how="inner")
    rows = curtailment(rows)
    rows["dataset_id"] = "curtailment_" + rows["scenario"]
    rows["method"] = METHOD
    rows["calibrated"] = False  # the water temperature input is not calibrated yet
    # Quality of the river input: small_stream / extended_search cells give unreliable curtailment.
    cells = pd.read_csv(ENV / "plant_cells.csv")[["location_id", "source", "status"]]
    rows = rows.merge(cells.rename(columns={"status": "river_cell_status"}), on=["location_id", "source"], how="left")
    columns = KEYS[:1] + ["date", "dataset_id"] + KEYS[2:] + ["value", "available_fraction", "available_mw",
                                                             "q_heat_max_mw", "limiting_limit", "river_cell_status",
                                                             "method", "calibrated"]
    out = rows[columns].sort_values(["location_id", "dataset_id", "member", "date"])
    out.to_parquet(ENV / "curtailment.parquet", index=False)

    covered = set(out["location_id"])
    plants["has_curtailment"] = plants["location_id"].isin(covered)
    plants.loc[(plants["status"] == "ok") & ~plants["has_curtailment"], "status"] = "no_river_data"
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    plants.drop(columns="has_curtailment").to_csv(RECORD, index=False)
    (ENV / "curtailment_inputs.csv").unlink(missing_ok=True)  # moved to data/interim/curtailment/

    # Describe the new datasets next to the discharge and water temperature ones.
    for scenario, group in out.groupby("scenario"):
        dataset_id = f"curtailment_{scenario}"
        first = group.iloc[0]
        meta["datasets"][dataset_id] = dict(
            variable="curtailment", units="MW", label=f"Curtailment ({scenario})", source=first["source"],
            scenario=scenario, track=int(first["track"]), forecast_run=first["forecast_run"], method=METHOD,
            calibrated="no", period=f"{group['date'].min()}..{group['date'].max()}",
            inputs="discharge + water temperature of the same scenario; plant parameters from facilities.csv")
    (ENV / "sources.json").write_text(json.dumps(meta, indent=2))

    counts = plants["status"].value_counts().to_dict()
    print(f"curtailment: {len(out)} rows for {len(covered)} plants; plant status {counts} -> {ENV}")


if __name__ == "__main__":
    main()
