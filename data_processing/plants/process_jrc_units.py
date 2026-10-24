from pathlib import Path

import pandas as pd


def load_units(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def filter_units(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[
        (df["type_g"] == "Nuclear")
        # & (df["water_type"] != "Seawater")
        & (df["status_g"] != "DECOMMISSIONED")
    ].copy()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "data" / "raw" / "jrc_open_power_plants" / "JRC-PPDB-OPEN.ver1.0" / "JRC_OPEN_UNITS.csv"
    out_dir = repo_root / "data" / "interim" / "jrc_open_power_plants" / "Nuclear_commissioned.csv"
    df = load_units(src)
    filtered = filter_units(df)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(out_dir, index=False)

if __name__ == "__main__":
    main()
