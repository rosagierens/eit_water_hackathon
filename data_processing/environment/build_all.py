"""Run the whole environmental data pipeline after new downloads (from the repo root):

  python data_processing/environment/build_all.py

1. build_grids.py         downloads -> standardized Europe-wide daily Zarr grids (data/interim/<source>/europe_daily/)
2. water_temperature.py   discharge + air temperature -> water temperature grids (data/interim/water_temperature/)
3. build_statistics.py    monthly quantile grids for the climate track (data/interim/<source>/statistics/)
4. build_app_input.py     per-plant tables for the app (data/app_input/environment/)
5. build_curtailment.py   daily curtailment per plant from those tables + facilities.csv
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_app_input  # noqa: E402
import build_curtailment  # noqa: E402
import build_grids  # noqa: E402
import build_statistics  # noqa: E402
import water_temperature  # noqa: E402

if __name__ == "__main__":
    for step in (build_grids, water_temperature, build_statistics, build_app_input, build_curtailment):
        print(f"\n=== {step.__name__}")
        step.main()
