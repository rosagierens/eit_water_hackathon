"""Download river discharge data for the three project tracks.

Datasets (see readme.txt in this folder for the reasoning):

  forecast     GloFAS medium-range forecast       (EWDS: cems-glofas-forecast)
  historical   GloFAS historical / reanalysis     (EWDS: cems-glofas-historical)
  projection   C3S hydrology climate projections  (CDS:  sis-hydrology-variables-derived-projections)

Examples:

  python download_river_discharge.py forecast --date 2026-10-23
  python download_river_discharge.py historical --start 2022-06-01 --end 2022-08-31
  python download_river_discharge.py projection --experiment rcp_2_6 rcp_4_5 rcp_8_5 --years 2045
  python download_river_discharge.py forecast --date 2026-10-23 --dry-run

Credentials: one ECMWF account works for both data stores. Put your personal
access token in the environment variable CDSAPI_KEY, or in ~/.cdsapirc as
"key: <token>". You must accept each dataset's licence once on its web page.
"""

import argparse
import os
from datetime import date, timedelta
from pathlib import Path

EWDS_URL = "https://ewds.climate.copernicus.eu/api"
CDS_URL = "https://cds.climate.copernicus.eu/api"

# Europe [North, West, South, East]; covers all European nuclear plants.
EUROPE_AREA = [72, -25, 34, 45]

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO / "data" / "raw"


def read_api_key():
    key = os.environ.get("CDSAPI_KEY")
    if key:
        return key
    rc = Path.home() / ".cdsapirc"
    if rc.exists():
        for line in rc.read_text().splitlines():
            if line.strip().startswith("key:"):
                return line.split(":", 1)[1].strip()
    raise SystemExit("No API key: set CDSAPI_KEY or add 'key: <token>' to ~/.cdsapirc")


def retrieve(url, dataset, request, target, dry_run):
    print(f"\n{dataset} -> {target}\n  {request}")
    if dry_run:
        return
    if target.exists():
        print("  already downloaded, skipping")
        return
    import cdsapi

    target.parent.mkdir(parents=True, exist_ok=True)
    client = cdsapi.Client(url=url, key=read_api_key())
    client.retrieve(dataset, request, str(target))


def download_forecast(args):
    """One GloFAS forecast run (00 UTC) with daily lead times."""
    day = date.fromisoformat(args.date)
    product = "control_forecast" if args.members == "control" else "ensemble_perturbed_forecasts"
    request = {
        "system_version": ["operational"],
        "hydrological_model": ["lisflood"],
        "product_type": [product],
        "variable": "river_discharge_in_the_last_24_hours",
        "year": [f"{day.year}"],
        "month": [f"{day.month:02d}"],
        "day": [f"{day.day:02d}"],
        "leadtime_hour": [str(24 * d) for d in range(1, args.lead_days + 1)],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": args.area,
    }
    target = args.out_dir / "glofas" / "forecast" / f"glofas_forecast_{product}_{day:%Y%m%d}.nc"
    retrieve(EWDS_URL, "cems-glofas-forecast", request, target, args.dry_run)


def glofas_product_type(version, year, month):
    """'consolidated' where it exists for that month, else 'intermediate' (only the recent months)."""
    import requests

    inputs = {"system_version": [version], "product_type": ["consolidated"], "year": [f"{year}"],
              "variable": ["average_river_discharge_in_the_last_24_hours"]}
    r = requests.post(f"{EWDS_URL}/retrieve/v1/processes/cems-glofas-historical/constraints",
                      json={"inputs": inputs}, timeout=60)
    r.raise_for_status()
    return "consolidated" if f"{month:02d}" in r.json().get("month", []) else "intermediate"


def download_historical(args):
    """GloFAS reanalysis, one request per month to keep requests small."""
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    month = start.replace(day=1)
    while month <= end:
        next_month = (month + timedelta(days=32)).replace(day=1)
        first = max(month, start)
        last = min(next_month - timedelta(days=1), end)
        product_type = args.product_type
        if product_type == "auto":
            product_type = glofas_product_type(args.version, month.year, month.month)
        request = {
            "system_version": [args.version],
            "hydrological_model": ["lisflood"],
            "product_type": [product_type],
            "timespan": ["time_mean"],
            "variable": ["average_river_discharge_in_the_last_24_hours"],
            "year": [f"{month.year}"],
            "month": [f"{month.month:02d}"],
            "day": [f"{d:02d}" for d in range(first.day, last.day + 1)],
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": args.area,
        }
        target = args.out_dir / "glofas" / "historical" / f"glofas_historical_{args.version}_{month:%Y%m}.nc"
        retrieve(EWDS_URL, "cems-glofas-historical", request, target, args.dry_run)
        month = next_month


# Years each C3S experiment covers.
PROJECTION_YEARS = {"historical": range(1971, 2006), **{rcp: range(2006, 2101) for rcp in ("rcp_2_6", "rcp_4_5", "rcp_8_5")}}


def download_projection(args):
    """Daily river discharge from one hydrological model / GCM / RCM chain, one file per experiment and year."""
    for experiment in args.experiment:
        for year in args.years:
            if year not in PROJECTION_YEARS[experiment]:
                span = PROJECTION_YEARS[experiment]
                print(f"\nskipping {experiment} {year}: only {span.start}-{span.stop - 1} exists")
                continue
            download_projection_year(args, experiment, year)


def download_projection_year(args, experiment, year):
    request = {
        "product_type": ["essential_climate_variables"],
        "variable": ["river_discharge"],
        "variable_type": ["absolute_values"],
        "time_aggregation": ["daily"],
        "experiment": [experiment],
        "hydrological_model": [args.hydrological_model],
        "gcm": [args.gcm],
        "rcm": [args.rcm],
        "ensemble_member": [args.ensemble_member],
        "period": [str(year)],
    }
    name = f"{args.hydrological_model}_{args.gcm}_{args.rcm}_{args.ensemble_member}_{experiment}_{year}"
    # The CDS returns an archive of NetCDF files for this dataset.
    target = args.out_dir / "c3s_hydrology" / "projection" / f"{name}.zip"
    retrieve(CDS_URL, "sis-hydrology-variables-derived-projections", request, target, args.dry_run)


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    common.add_argument("--area", type=float, nargs=4, default=EUROPE_AREA, metavar=("N", "W", "S", "E"),
                        help="bounding box (forecast and historical only)")
    common.add_argument("--dry-run", action="store_true", help="print the requests without downloading")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="track", required=True)

    p = sub.add_parser("forecast", parents=[common], help="GloFAS forecast (track 1)")
    p.add_argument("--date", default=(date.today() - timedelta(days=1)).isoformat(),
                   help="forecast start date, YYYY-MM-DD (default: yesterday)")
    p.add_argument("--lead-days", type=int, default=10, choices=range(1, 31), metavar="1-30")
    p.add_argument("--members", choices=["control", "ensemble"], default="control",
                   help="control run (1 member) or the 50 perturbed members")
    p.set_defaults(func=download_forecast)

    p = sub.add_parser("historical", parents=[common], help="GloFAS reanalysis for verification (track 1)")
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--version", default="version_4_0", choices=["version_4_0", "version_5_0"])
    p.add_argument("--product-type", default="auto", choices=["auto", "consolidated", "intermediate"],
                   help="auto: consolidated where available, else intermediate (recent months, version_4_0 only)")
    p.set_defaults(func=download_historical)

    p = sub.add_parser("projection", parents=[common], help="C3S climate projections (track 2)")
    p.add_argument("--experiment", nargs="+", default=["rcp_4_5"], choices=list(PROJECTION_YEARS),
                   help="one or more scenarios, e.g. rcp_2_6 rcp_4_5 rcp_8_5")
    p.add_argument("--years", type=int, nargs="+", required=True,
                   help="historical: 1971-2005, RCPs: 2006-2100")
    p.add_argument("--hydrological-model", default="e_hypegrid", choices=["e_hypegrid", "vic_wur"])
    p.add_argument("--gcm", default="ec_earth", choices=["ec_earth", "hadgem2_es", "mpi_esm_lr"])
    p.add_argument("--rcm", default="rca4", choices=["rca4", "racmo22e", "cclm4_8_17", "csc_remo2009"])
    p.add_argument("--ensemble-member", default="r12i1p1", choices=["r1i1p1", "r2i1p1", "r12i1p1"])
    p.set_defaults(func=download_projection)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
