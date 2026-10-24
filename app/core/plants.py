"""Nuclear plant locations from the application-ready facility table."""

from functools import lru_cache
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
FACILITIES_CSV = REPO / "data" / "app_input" / "facilities.csv"


@lru_cache
def load_plants():
    if not FACILITIES_CSV.exists():
        raise FileNotFoundError(f"{FACILITIES_CSV} missing; run data_processing/plants/run_pipeline.py")
    plants = pd.read_csv(FACILITIES_CSV).rename(columns={
        "Location_ID": "id",
        "Name": "name",
        "Country": "country",
        "Lat": "lat",
        "Lon": "lon",
        "N_units": "units",
        "Capacity_MW": "capacity_mw",
    })
    plants = plants[["id", "name", "country", "lat", "lon", "units", "capacity_mw"]].copy()
    plants["name"] = plants["name"].str.replace(" nuclear power plant", "", regex=False)
    plants["country"] = plants["country"].fillna("")
    plants["operator"] = ""  # The facility table does not contain an operator.
    return plants


def get_plant(plant_id):
    plants = load_plants()
    match = plants[plants["id"] == plant_id]
    return None if match.empty else match.iloc[0].to_dict()
