"""Nuclear plant locations from the application-ready facility table."""

from functools import lru_cache
from pathlib import Path
from api.helper import get_path
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
        "Cooling_type": "cooling_type",
        "Water_type": "water_type",
        "Temp_limit": "temp_limit_c",  # max river temperature downstream of the plant
        "Temp_change_limit": "temp_change_limit_c",  # max warming of the river by the plant
        "Q_river_MW_th": "heat_to_river_mw_th",
        "Alpha": "alpha",
        "Cooling_data_flag": "cooling_data_flag",
    })
    plants = plants[["id", "name", "country", "lat", "lon", "units", "capacity_mw",
                     "cooling_type", "water_type", "temp_limit_c", "temp_change_limit_c",
                     "heat_to_river_mw_th", "alpha", "cooling_data_flag"]].copy()
    plants["name"] = plants["name"].str.replace(" nuclear power plant", "", regex=False)
    plants["country"] = plants["country"].fillna("")
    plants["operator"] = ""  # The facility table does not contain an operator.
    # Empty cells (e.g. no cooling data for Ukraine and Belarus) become null in the JSON.
    return plants.astype(object).where(plants.notna(), None)


def get_plant(plant_id):
    plants = load_plants()
    match = plants[plants["id"] == plant_id]
    return None if match.empty else match.iloc[0].to_dict()
