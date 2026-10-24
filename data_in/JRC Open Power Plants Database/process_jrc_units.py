from pathlib import Path

import pandas as pd


def load_units(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def filter_units(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[
        (df["type_g"] == "Nuclear")
        & (df["water_type"] != "Seawater")
        & (df["status_g"] != "DECOMMISSIONED")
    ].copy()


def create_locations(filtered: pd.DataFrame) -> pd.DataFrame:
    locations = filtered[["lat", "lon"]].copy()
    locations["lat"] = locations["lat"].round(3)
    locations["lon"] = locations["lon"].round(3)
    locations = locations.drop_duplicates().reset_index(drop=True)
    locations["location_id"] = range(len(locations))
    return locations


def build_units(filtered: pd.DataFrame, locations: pd.DataFrame) -> pd.DataFrame:
    units = filtered.copy()
    units["lat_round"] = units["lat"].round(3)
    units["lon_round"] = units["lon"].round(3)
    units = units.merge(
        locations.rename(columns={"lat": "lat_round", "lon": "lon_round"}),
        on=["lat_round", "lon_round"],
        how="left",
    )
    units = units.drop(columns=["lat", "lon", "lat_round", "lon_round"])
    units = units[[col for col in units.columns if col != "location_id"] + ["location_id"]]
    return units


def save_outputs(out_dir: Path, pp_locations: pd.DataFrame, units: pd.DataFrame) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pp_locations[["lat", "lon"]].to_csv(out_dir / "pp_locations.csv", index=False)
    units.to_csv(out_dir / "jrc_units.csv", index=False)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    repo_root = base_dir.parent.parent
    src = base_dir / "JRC-PPDB-OPEN.ver1.0/JRC_OPEN_UNITS.csv"
    out_dir = repo_root / "data_cleaned"

    df = load_units(src)
    filtered = filter_units(df)
    locations = create_locations(filtered)
    units = build_units(filtered, locations)
    save_outputs(out_dir, locations, units)


if __name__ == "__main__":
    main()
