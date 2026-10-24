from pathlib import Path
import pandas as pd

base_dir = Path(__file__).resolve().parent
src = (
    base_dir
    / "data_in/JRC Open Power Plants Database/JRC-PPDB-OPEN.ver1.0/JRC_OPEN_UNITS.csv"
)
out = base_dir / "data_cleaned/units.csv"

# Keep only nuclear units that do not use seawater cooling.
df = pd.read_csv(src)
filtered = df.loc[(df["type_g"] == "Nuclear") & (df["water_type"] != "Seawater")].copy()

out.parent.mkdir(parents=True, exist_ok=True)
filtered.to_csv(out, index=False)
