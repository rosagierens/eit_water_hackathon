from pathlib import Path

import pandas as pd


def load_units(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def filter_units(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[
        (df["type_g"] == "Nuclear")
        # & (df["water_type"] != "Seawater")
        & (df["status_g"].str.upper() != "DECOMMISSIONED")  # JRC uses both cases
    ].copy()


def count_cooling_types(all_units: pd.DataFrame, nuclear: pd.DataFrame) -> pd.DataFrame:
    """Rows per cooling_type in the whole JRC table and in the nuclear extract; empty values count as ""."""
    counts = pd.DataFrame(
        {
            "n_rows_all_jrc": all_units["cooling_type"].fillna("").value_counts(),
            "n_rows_nuclear": nuclear["cooling_type"].fillna("").value_counts(),
        }
    )
    counts = counts.fillna(0).astype(int).sort_values("n_rows_all_jrc", ascending=False)
    counts.index.name = "cooling_type"
    return counts.reset_index()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "data" / "raw" / "jrc_open_power_plants" / "JRC-PPDB-OPEN.ver1.0" / "JRC_OPEN_UNITS.csv"
    out_dir = repo_root / "data" / "interim" / "jrc_open_power_plants"
    df = load_units(src)
    filtered = filter_units(df)
    out_dir.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(out_dir / "Nuclear_commissioned.csv", index=False)
    count_cooling_types(df, filtered).to_csv(out_dir / "cooling_types.csv", index=False)

if __name__ == "__main__":
    main()
