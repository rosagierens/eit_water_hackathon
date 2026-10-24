"""Aggregate the merged GEM-JRC reactor table to one row per facility (GEM location ID).

Heat is summed per facility and Alpha is the heat-weighted mean of the unit values.
The water-type filter runs last, on the finished facility table, so it is easy to undo.
"""

from pathlib import Path

import numpy as np
import pandas as pd

# Facilities whose Water_type is in this set are left out of the app input.
# Empty the set to keep them; facilities_all.csv always has every facility.
EXCLUDED_WATER_TYPES = {"Seawater"}

# Provisional placeholders applied to every facility (unverified).
TEMP_LIMIT_C = 30.0
TEMP_CHANGE_LIMIT_C = 5.0

FACILITY_COLUMNS = [
    "Location_ID",
    "Name",
    "Lat",
    "Lon",
    "Country",
    "Capacity_MW",
    "P_thermal_MW_th",
    "N_units",
    "Cooling_type",
    "Temp_limit",
    "Temp_change_limit",
    "Water_type",
    "Q_cool_MW_th",
    "Q_river_MW_th",
    "Alpha",
    "Cooling_data_flag",
]


def combined_type(values: pd.Series, mixed_label) -> str:
    """The single value, a mixed label if units differ, or empty if any unit has none."""
    if values.isna().any():
        return ""
    unique = sorted(values.unique())
    return unique[0] if len(unique) == 1 else mixed_label(unique)


def summarise(units: pd.DataFrame) -> pd.Series:
    first = units.iloc[0]
    complete = units["Q_river_MW_th"].notna().all()
    q_cool = units["Q_cool_MW_th"].sum()
    q_river = units["Q_river_MW_th"].sum() if complete else np.nan
    if (units["cooling_source"] == "missing").any():
        flag = "missing"
    elif (units["cooling_source"] == "site_sibling").any():
        flag = "inferred_from_site"
    else:
        flag = ""
    return pd.Series(
        {
            "Name": first["Project Name"],
            "Lat": first["Latitude"],
            "Lon": first["Longitude"],
            "Country": first["Country/Area"],
            "Capacity_MW": units["Capacity (MW)"].sum(),
            "P_thermal_MW_th": units["Thermal Capacity (MWt)"].sum(),
            "N_units": len(units),
            "Cooling_type": combined_type(units["cooling_type"], lambda v: f"Mixed ({'/'.join(v)})"),
            "Temp_limit": TEMP_LIMIT_C,
            "Temp_change_limit": TEMP_CHANGE_LIMIT_C,
            "Water_type": combined_type(units["water_type"], lambda v: "Mixed"),
            "Q_cool_MW_th": q_cool,
            "Q_river_MW_th": q_river,
            "Alpha": q_river / q_cool,
            "Cooling_data_flag": flag,
        }
    )


def build_facilities(units: pd.DataFrame) -> pd.DataFrame:
    facilities = units.groupby("GEM location ID", sort=False).apply(summarise, include_groups=False)
    facilities.index.name = "Location_ID"
    return facilities.reset_index()[FACILITY_COLUMNS]


def exclude_water_types(facilities: pd.DataFrame) -> pd.DataFrame:
    dropped = facilities["Water_type"].isin(EXCLUDED_WATER_TYPES)
    print(f"Left out of the app input ({sorted(EXCLUDED_WATER_TYPES)} water type): {dropped.sum()} facilities")
    print(", ".join(facilities.loc[dropped, "Name"].str.replace(" nuclear power plant", "", regex=False)))
    return facilities[~dropped].reset_index(drop=True)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    units_csv = repo_root / "data" / "interim" / "nuclear_units" / "units_gem_jrc.csv"
    all_csv = repo_root / "data" / "interim" / "nuclear_units" / "facilities_all.csv"
    out_csv = repo_root / "data" / "app_input" / "facilities.csv"

    units = pd.read_csv(units_csv, dtype={"Unit Name": str})
    facilities = build_facilities(units)
    print(f"Facilities: {len(facilities)}")
    print(facilities["Cooling_data_flag"].replace("", "none").value_counts().to_string())
    facilities.to_csv(all_csv, index=False)

    app_facilities = exclude_water_types(facilities)
    print(f"Facilities in the app input: {len(app_facilities)}")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    app_facilities.to_csv(out_csv, index=False)


if __name__ == "__main__":
    main()
