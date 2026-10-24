from pathlib import Path

import pandas as pd


def load_gem_units(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name="Data")


def filter_operating_europe(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[
        (df["Status"] == "operating")
        & (df["Region"] == "Europe")
        & (df["Country/Area"] != "Russia")
    ].copy()


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

    units = filter_operating_europe(load_gem_units(gem_xlsx))
    operating_csv.parent.mkdir(parents=True, exist_ok=True)
    units.to_csv(operating_csv, index=False)


if __name__ == "__main__":
    main()
