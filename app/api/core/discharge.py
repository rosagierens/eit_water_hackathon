"""River discharge and water temperature at a plant, read from the application-ready parquet tables.

Both tables have one row per (dataset, plant, date) and, for ensemble forecasts, one row per
member and forecast run. Columns: location_id, date, dataset_id, source, scenario, track,
member, forecast_run, value.

Forecasts are shown from FORECAST_DAYS_BACK days before today to the last forecast day.
Each day takes the newest forecast run that covers it, and discharge and water temperature
of the same pair use the same run and the same dates, so the charts line up day by day.
"""

from functools import lru_cache

import pandas as pd
from api.helper import get_path

TABLES = {
    "discharge": get_path("RAW_DISCHARGE_DATA"),
    "water_temperature": get_path("WATER_TEMPERATURE_DATA"),
}
FORECAST_DAYS_BACK = 2
UNITS = {"discharge": "m3 s-1", "water_temperature": "degC"}

# Track 1 = operations (next days), track 2 = planning (scenarios).
# `dataset` is the dataset_id in the tables; `pair` groups the datasets whose dates are aligned.
SOURCES = {
    "River_discharge": {"track": 1, "label": "GloFAS river discharge", "dataset": "glofas_forecast",
                        "variable": "discharge", "pair": "forecast"},
    "River_temperature": {"track": 1, "label": "Water temperature from GloFAS forecast", "dataset": "wt_forecast",
                          "variable": "water_temperature", "pair": "forecast"},
    # "glofas_reanalysis": {"track": 1, "label": "GloFAS reanalysis (ERA5)", "variable": "discharge", "pair": "reanalysis"},
    # "wt_reanalysis": {"track": 1, "label": "Water temperature from GloFAS reanalysis + ERA5-Land",
    #                   "variable": "water_temperature", "pair": "reanalysis"},
    # "hydroland_hist": {"track": 2, "label": "HydroLand historical", "variable": "discharge"},
    # "hydroland_ssp370": {"track": 2, "label": "HydroLand SSP3-7.0", "variable": "discharge"},
    # "c3s_historical": {"track": 2, "label": "C3S historical", "variable": "discharge"},
    # "c3s_rcp26": {"track": 2, "label": "C3S RCP2.6", "variable": "discharge"},
    # "c3s_rcp45": {"track": 2, "label": "C3S RCP4.5", "variable": "discharge"},
    # "c3s_rcp85": {"track": 2, "label": "C3S RCP8.5", "variable": "discharge"},
    # "power_generation_constraint": {"track": 1, "label": "Power generation constraint", "variable": "discharge"},
}


@lru_cache(maxsize=None)
def _table(variable):
    """One whole table, read once."""
    df = pd.read_parquet(TABLES[variable], columns=["location_id", "date", "dataset_id", "track", "member", "forecast_run", "value"])
    df["location_id"] = df["location_id"].astype(str)
    df["date"] = pd.to_datetime(df["date"])
    return df


def available_sources():
    stats = pd.concat([_table(v) for v in TABLES]).groupby("dataset_id").agg(
        track=("track", "first"), rows=("track", "size"))
    keys = {spec["dataset"]: key for key, spec in SOURCES.items()}
    return {
        keys.get(dataset, dataset): {
            "track": int(row["track"]),
            "label": SOURCES.get(keys.get(dataset), {}).get("label", dataset),
            "rows": int(row["rows"]),
        }
        for dataset, row in stats.iterrows()
    }


def _points(frame):
    """Collapse a plant's rows to one point per date; ensembles get median plus p10/p90 over members."""
    g = frame.groupby("date")["value"]
    if g.size().max() > 1:
        out = pd.DataFrame({"value": g.median(), "p10": g.quantile(0.10), "p90": g.quantile(0.90)})
    else:
        out = frame.set_index("date")[["value"]]
    return out.sort_index().dropna(subset=["value"])


def _plant_frame(source, plant_id):
    spec = SOURCES[source]
    df = _table(spec["variable"])
    return df[(df["dataset_id"] == spec["dataset"]) & (df["location_id"] == str(plant_id))]


def _forecast_window(frame):
    """Forecast rows from FORECAST_DAYS_BACK days ago onwards; rows without a forecast run unchanged."""
    if frame.empty or frame["forecast_run"].isna().all():
        return frame
    start = pd.Timestamp.now().normalize() - pd.Timedelta(days=FORECAST_DAYS_BACK)
    return frame[frame["date"] >= start]


def _newest_runs(frames):
    """Per date, keep only the newest forecast run that every frame has for that date.

    Dates missing from any frame are dropped, so paired datasets end up on the same dates.
    Frames without forecast runs are only trimmed to the common dates.
    """
    frames = {k: f for k, f in frames.items() if not f.empty}
    if not frames:
        return frames
    if all(f["forecast_run"].notna().any() for f in frames.values()):
        pairs = set.intersection(*(set(zip(f["date"], f["forecast_run"])) for f in frames.values()))
        newest = {}
        for date, run in pairs:
            newest[date] = max(run, newest.get(date, run))
        return {k: f[[newest.get(d) == r for d, r in zip(f["date"], f["forecast_run"])]]
                for k, f in frames.items()}
    dates = set.intersection(*(set(f["date"]) for f in frames.values()))
    return {k: f[f["date"].isin(dates)] for k, f in frames.items()}


def _series(source, frame):
    """Series for one source, ready for JSON. `series` is empty if there is no data."""
    spec = SOURCES[source]
    result = {
        "source": source,
        "label": spec["label"],
        "track": spec["track"],
        "variable": spec["variable"],
        "units": UNITS[spec["variable"]],
        "cell": None,
        "series": [],
    }
    if frame is None or frame.empty:
        result["message"] = "No data for this plant in this source"
        return result

    runs = frame["forecast_run"].dropna()
    if len(runs):
        result["forecast_run"] = str(pd.Timestamp(runs.max()).date())  # newest run used

    for date, row in _points(frame).iterrows():
        point = {"time": date.isoformat(), "value": float(row["value"])}
        if "p10" in row and pd.notna(row["p10"]) and pd.notna(row["p90"]):
            point.update(p10=float(row["p10"]), p90=float(row["p90"]))
        result["series"].append(point)
    return result


def plant_sources(plant_id, track=None):
    """All sources of a track at a plant; paired discharge and water temperature share dates and runs."""
    keys = [k for k, s in SOURCES.items() if track is None or s["track"] == track]
    frames = {k: _forecast_window(_plant_frame(k, plant_id)) for k in keys}
    groups = {}
    for k in keys:
        groups.setdefault(SOURCES[k].get("pair") or k, []).append(k)
    for group in groups.values():
        frames.update(_newest_runs({k: frames[k] for k in group}))
    return [_series(k, frames.get(k)) for k in keys]
