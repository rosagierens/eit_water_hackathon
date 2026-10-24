from pathlib import Path

import pandas as pd

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
]


def load_gem_units(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name="Data")


def filter_operating_europe(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[
        (df["Status"] == "operating")
        & (df["Region"] == "Europe")
        & (df["Country/Area"] != "Russia")
    ].copy()


def build_facilities(units: pd.DataFrame) -> pd.DataFrame:
    first = units.drop_duplicates(subset=["GEM location ID"], keep="first")
    facilities = pd.DataFrame(
        {
            "Location_ID": first["GEM location ID"],
            "Name": first["Project Name"],
            "Lat": first["Latitude"],
            "Lon": first["Longitude"],
            "Country": first["Country/Area"],
            "Capacity_MW": first["Capacity (MW)"],
            "P_thermal_MW_th": first["Thermal Capacity (MWt)"],
            "N_units": 1,
            "Cooling_type": "Once-through",
            "Temp_limit": 30.0,
            "Temp_change_limit": 5.0,
        }
    )
    return facilities[FACILITY_COLUMNS].reset_index(drop=True)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    gem_xlsx = (
        repo_root
        / "data"
        / "raw"
        / "global_nuclear_power_tracker"
        / "Global-Nuclear-Power-Tracker-August-2026.xlsx"
    )
    operating_csv = repo_root / "data" / "interim" / "global_nuclear_power_tracker" / "Operating_Europe.csv"
    out_csv = repo_root / "data" / "app_input" / "facilities.csv"

    units = filter_operating_europe(load_gem_units(gem_xlsx))
    operating_csv.parent.mkdir(parents=True, exist_ok=True)
    units.to_csv(operating_csv, index=False)

    facilities = build_facilities(units)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    facilities.to_csv(out_csv, index=False)


if __name__ == "__main__":
    main()
