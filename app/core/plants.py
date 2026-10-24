"""Nuclear plant locations, aggregated from the cleaned unit table to one row per plant."""

from functools import lru_cache
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
UNITS_CSV = REPO / "data_cleaned" / "nuclear_plants_europe_units.csv"


@lru_cache
def load_plants():
    if not UNITS_CSV.exists():
        raise FileNotFoundError(f"{UNITS_CSV} missing; run data_in/nucler_plants/clean_plants.py")
    units = pd.read_csv(UNITS_CSV)
    plants = units.groupby("GEM location ID").agg(
        name=("Project Name", "first"),
        country=("Country/Area", "first"),
        lat=("Latitude", "mean"),
        lon=("Longitude", "mean"),
        units=("Unit Name", "count"),
        capacity_mw=("Capacity (MW)", "sum"),
        operator=("Operator", "first"),
    )
    plants.index.name = "id"
    plants["name"] = plants["name"].str.replace(" nuclear power plant", "", regex=False)
    plants[["operator", "country"]] = plants[["operator", "country"]].fillna("")  # NaN is not valid JSON
    return plants.reset_index()


def get_plant(plant_id):
    plants = load_plants()
    match = plants[plants["id"] == plant_id]
    return None if match.empty else match.iloc[0].to_dict()
