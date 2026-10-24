"""Filter the GEM Global Nuclear Power Tracker to operating units in Europe.

Writes data_cleaned/nuclear_plants_europe_units.csv (one row per unit, all
columns kept, see notes.txt). Run from anywhere:

  python data_in/nucler_plants/clean_plants.py
"""

from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).parent / "Global-Nuclear-Power-Tracker-August-2026.xlsx"
TARGET = REPO / "data_cleaned" / "nuclear_plants_europe_units.csv"


def main():
    units = pd.read_excel(SOURCE, sheet_name="Data")
    units = units[(units["Status"] == "operating") & (units["Region"] == "Europe")]
    TARGET.parent.mkdir(exist_ok=True)
    units.to_csv(TARGET, index=False)
    print(f"{len(units)} units at {units['GEM location ID'].nunique()} plants -> {TARGET}")


if __name__ == "__main__":
    main()
