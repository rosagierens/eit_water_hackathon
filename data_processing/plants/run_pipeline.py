"""Run the whole plant pipeline, from the raw GEM and JRC files to data/app_input/facilities.csv.

Run from anywhere: python data_processing/plants/run_pipeline.py
Stops at the first step that fails.
"""

import subprocess
import sys
from pathlib import Path

STEPS = [
    "process_gem_units.py",
    "process_jrc_units.py",
    "merge_units.py",
    "build_facilities.py",
]


def main() -> None:
    here = Path(__file__).resolve().parent
    for step in STEPS:
        print(f"\n=== {step}", flush=True)
        result = subprocess.run([sys.executable, str(here / step)], cwd=here.parents[1])
        if result.returncode != 0:
            sys.exit(f"{step} failed (exit code {result.returncode}); later steps were not run.")
    print("\nDone: data/app_input/facilities.csv is up to date.")


if __name__ == "__main__":
    main()
