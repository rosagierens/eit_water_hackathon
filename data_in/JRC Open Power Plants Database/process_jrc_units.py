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
    base_dir = Path(__file__).resolve().parent
    repo_root = base_dir.parent.parent
    src = base_dir / "JRC-PPDB-OPEN.ver1.0/JRC_OPEN_UNITS.csv"
    out_dir = base_dir / "Nuclear_commissioned.csv"
    df = load_units(src)
    filtered = filter_units(df)
    filtered.to_csv(out_dir, index=False)

if __name__ == "__main__":
    main()
