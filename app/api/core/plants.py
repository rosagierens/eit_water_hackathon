"""Nuclear plant locations from the application-ready facility table."""

from functools import lru_cache
from pathlib import Path
from ..helper import get_path
import pandas as pd


@lru_cache
def load_plants():
    facilities_csv = get_path("FACILITIES_CSV")

    if not facilities_csv.exists():
        raise FileNotFoundError(
            f"{facilities_csv} missing"
        )
    plants = pd.read_csv(facilities_csv).rename(columns={
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
