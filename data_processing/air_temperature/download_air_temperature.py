"""Download 2 m air temperature for the three project tracks.

Datasets (see readme.txt in this folder for the reasoning):

  forecast      ECMWF open data, IFS HRES or ENS, 0.25°, up to 10/15 days   (no account needed)
  observed      ERA5-Land daily statistics, 0.1°                             (CDS: derived-era5-land-daily-statistics)
  cordex        EURO-CORDEX EC-EARTH/RCA4, 0.11°, RCP2.6/4.5/8.5             (CDS: projections-cordex-domains-single-levels)
  climatedt     DestinE Climate DT IFS-NEMO, hourly, at each plant           (Polytope, same simulation as HydroLand)

Examples:

  python download_air_temperature.py forecast
  python download_air_temperature.py observed --start 2022-07-01 --end 2022-08-31
  python download_air_temperature.py cordex --experiment rcp_2_6 rcp_4_5 rcp_8_5 --years 2045
  python download_air_temperature.py climatedt --experiment SSP3-7.0 --start 2045-08-01 --end 2045-08-31
  python download_air_temperature.py observed --start 2022-07-01 --end 2022-07-31 --dry-run

Credentials:
  observed, cordex   CDSAPI_KEY or ~/.cdsapirc (same key as the river discharge downloads)
  climatedt          ~/.polytopeapirc, written once by DestinE's desp-authentication.py (see readme.txt)
"""

import argparse
import json
import os
import zipfile
from datetime import date, timedelta
from pathlib import Path

CDS_URL = "https://cds.climate.copernicus.eu/api"

# Europe [North, West, South, East], same box as the river discharge downloads.
EUROPE_AREA = [72, -25, 34, 45]

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO / "data" / "raw"
DEFAULT_INTERIM_DIR = REPO / "data" / "interim"
PLANTS_CSV = DEFAULT_INTERIM_DIR / "global_nuclear_power_tracker" / "Operating_Europe.csv"


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


def cds_retrieve(dataset, request, target, dry_run, unpack_dir=None):
    print(f"\n{dataset} -> {target}\n  {request}")
    if dry_run:
        return
    if target.exists() and (unpack_dir is None or unpack_dir.is_dir()):
        print("  already downloaded, skipping")
        return
    if not target.exists():
        import cdsapi

        target.parent.mkdir(parents=True, exist_ok=True)
        cdsapi.Client(url=CDS_URL, key=read_api_key()).retrieve(dataset, request, str(target))
    if zipfile.is_zipfile(target):  # some CDS datasets deliver a zip of NetCDF files
        folder = unpack_dir or target.with_suffix("")
        with zipfile.ZipFile(target) as z:
            z.extractall(folder)
        print(f"  unpacked to {folder}")


def crop(ds, area):
    north, west, south, east = area
    lat = "latitude" if "latitude" in ds.coords else "lat"
    lon = "longitude" if "longitude" in ds.coords else "lon"
    lat_slice = slice(north, south) if ds[lat][0] > ds[lat][-1] else slice(south, north)
    return ds.sel({lat: lat_slice, lon: slice(west, east)})


# --- Track 1: forecast ---------------------------------------------------------------------------

def forecast_steps(product, days):
    """Open-data steps: 3-hourly to 144 h, then 6-hourly (HRES to 240 h, ENS to 360 h)."""
    last = min(days * 24, 240 if product == "hres" else 360)
    return [s for s in list(range(0, 145, 3)) + list(range(150, 361, 6)) if s <= last]


def download_forecast(args):
    from ecmwf.opendata import Client

    client = Client(source="ecmwf")
    if args.product == "hres":
        request = dict(stream="oper", type="fc")
    else:
        request = dict(stream="enfo", type="pf", number=list(range(1, args.members + 1)))
    request.update(param="2t", step=forecast_steps(args.product, args.days))
    if args.date:
        request.update(date=args.date.replace("-", ""), time=0)
    run = client.latest(**request) if not args.date else date.fromisoformat(args.date)
    name = f"ecmwf_{args.product}_2t_{run:%Y%m%d}"
    target = args.interim_dir / "ecmwf" / "forecast" / f"{name}.nc"
    grib = args.out_dir / "ecmwf" / "forecast" / f"{name}.grib2"
    print(f"\nECMWF open data {args.product} {run:%Y-%m-%d} 00 UTC -> {target}\n  {request}")
    if args.dry_run:
        return
    if target.exists():
        print("  already downloaded, skipping")
        return
    import xarray as xr

    target.parent.mkdir(parents=True, exist_ok=True)
    grib.parent.mkdir(parents=True, exist_ok=True)
    if not grib.exists():
        client.retrieve(target=str(grib), **request)
    # Open data is global; keep only the area, in °C, as NetCDF.
    with xr.open_dataset(grib, engine="cfgrib", backend_kwargs={"indexpath": ""}) as ds:
        t2m = crop(ds, args.area)["t2m"].load() - 273.15
    t2m.attrs.update(units="degC", long_name="2 metre temperature")
    t2m.to_dataset(name="t2m").to_netcdf(target)
    print(f"  saved {target.name}")


# --- Track 1: observations -----------------------------------------------------------------------

def download_observed(args):
    """ERA5-Land daily statistics, one request per month and statistic."""
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    month = start.replace(day=1)
    while month <= end:
        next_month = (month + timedelta(days=32)).replace(day=1)
        first, last = max(month, start), min(next_month - timedelta(days=1), end)
        for stat in args.statistics:
            request = {
                "variable": ["2m_temperature"],
                "year": f"{month.year}",
                "month": [f"{month.month:02d}"],
                "day": [f"{d:02d}" for d in range(first.day, last.day + 1)],
                "daily_statistic": stat,
                "time_zone": "utc+00:00",
                "frequency": "1_hourly",
                "area": args.area,
            }
            target = args.out_dir / "era5_land" / "observed" / f"era5land_t2m_{stat}_{month:%Y%m}.nc"
            unpack_dir = args.interim_dir / "era5_land" / "observed" / target.stem
            cds_retrieve("derived-era5-land-daily-statistics", request, target, args.dry_run, unpack_dir)
        month = next_month


# --- Track 2: projections ------------------------------------------------------------------------

CORDEX_YEARS = {"historical": range(1970, 2006), **{r: range(2006, 2101) for r in ("rcp_2_6", "rcp_4_5", "rcp_8_5")}}


def download_cordex(args):
    """Daily mean and daily maximum temperature, matching the C3S discharge model chain by default."""
    for experiment in args.experiment:
        for year in args.years:
            if year not in CORDEX_YEARS[experiment]:
                span = CORDEX_YEARS[experiment]
                print(f"\nskipping {experiment} {year}: only {span.start}-{span.stop - 1} exists")
                continue
            request = {
                "domain": "europe",
                "experiment": experiment,
                "horizontal_resolution": "0_11_degree_x_0_11_degree",
                "temporal_resolution": "daily_mean",
                "variable": ["2m_air_temperature", "maximum_2m_temperature_in_the_last_24_hours"],
                "gcm_model": args.gcm,
                "rcm_model": args.rcm,
                "ensemble_member": args.ensemble_member,
                "year": [str(year)],
                "month": [f"{m:02d}" for m in range(1, 13)],
            }
            target = args.out_dir / "euro_cordex" / f"cordex_{args.gcm}_{args.rcm}_{args.ensemble_member}_{experiment}_{year}.zip"
            unpack_dir = args.interim_dir / "euro_cordex" / target.stem
            cds_retrieve("projections-cordex-domains-single-levels", request, target, args.dry_run, unpack_dir)


CLIMATEDT_ACTIVITY = {"hist": "baseline", "SSP3-7.0": "projections"}


def plant_points():
    import pandas as pd

    if not PLANTS_CSV.exists():
        raise SystemExit(f"{PLANTS_CSV} missing; run data_processing/plants/process_gem_units.py first")
    units = pd.read_csv(PLANTS_CSV)
    plants = units.groupby("GEM location ID")[["Latitude", "Longitude"]].mean().round(4)
    return plants.reset_index().rename(columns={"GEM location ID": "id", "Latitude": "lat", "Longitude": "lon"})


def covjson_to_table(path, plants):
    """Long table (plant id, time, t2m in °C) from a Polytope CoverageJSON time series."""
    import numpy as np
    import pandas as pd

    data = json.loads(path.read_text())
    coverages = data.get("coverages", [data])
    rows = []
    for cov in coverages:
        axes = cov["domain"]["axes"]
        lat = axes.get("latitude", axes.get("y"))["values"][0]
        lon = axes.get("longitude", axes.get("x"))["values"][0]
        times = axes["t"]["values"]
        values = next(iter(cov["ranges"].values()))["values"]
        nearest = ((plants["lat"] - lat) ** 2 + (plants["lon"] - lon) ** 2).idxmin()
        for t, v in zip(times, values):
            rows.append((plants.at[nearest, "id"], t, v))
    table = pd.DataFrame(rows, columns=["plant_id", "time", "t2m"])
    if table["t2m"].dropna().gt(200).all():  # Kelvin -> °C
        table["t2m"] = table["t2m"] - 273.15
    table["time"] = pd.to_datetime(table["time"])
    return table.sort_values(["plant_id", "time"]).replace({np.nan: None})


def download_climatedt(args):
    """Hourly 2 m temperature at every plant, extracted server-side by Polytope (small download)."""
    plants = plant_points()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    request = {
        "class": "d1",
        "dataset": "climate-dt",
        "activity": CLIMATEDT_ACTIVITY[args.experiment],
        "experiment": args.experiment,
        "generation": "2",
        "model": "IFS-NEMO",
        "realization": "1",
        "resolution": args.resolution,
        "expver": "0001",
        "stream": "clte",
        "type": "fc",
        "levtype": "sfc",
        "param": "167",  # 2 m temperature
        "date": f"{start:%Y%m%d}/to/{end:%Y%m%d}",
        "time": "0000/to/2300/by/0100",
        "feature": {
            "type": "timeseries",
            "points": plants[["lat", "lon"]].values.tolist(),
            "time_axis": "date",
        },
    }
    out_dir = args.out_dir / "climate_dt" / args.experiment
    raw = out_dir / f"climatedt_t2m_plants_{start:%Y%m%d}_{end:%Y%m%d}.covjson"
    table_path = args.interim_dir / "climate_dt" / args.experiment / f"{raw.stem}.csv"
    shown = {**request, "feature": {**request["feature"], "points": f"[{len(plants)} plant locations]"}}
    print(f"\nPolytope ({args.address}) -> {raw}\n  {shown}")
    if args.dry_run:
        return
    if not raw.exists():
        from polytope.api import Client

        out_dir.mkdir(parents=True, exist_ok=True)
        Client(address=args.address).retrieve("destination-earth", request, str(raw))
    try:
        table_path.parent.mkdir(parents=True, exist_ok=True)
        covjson_to_table(raw, plants).to_csv(table_path, index=False)
        print(f"  saved {table_path.name}")
    except Exception as exc:  # keep the raw file; the format is converted later if this fails
        print(f"  could not convert CoverageJSON to CSV ({exc!r}); raw file kept at {raw}")


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    common.add_argument("--interim-dir", type=Path, default=DEFAULT_INTERIM_DIR)
    common.add_argument("--area", type=float, nargs=4, default=EUROPE_AREA, metavar=("N", "W", "S", "E"),
                        help="bounding box (forecast and observed)")
    common.add_argument("--dry-run", action="store_true", help="print the requests without downloading")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="track", required=True)

    p = sub.add_parser("forecast", parents=[common], help="ECMWF open-data forecast (track 1)")
    p.add_argument("--product", choices=["hres", "ens"], default="hres",
                   help="hres: one high-resolution run (~40 MB); ens: perturbed ensemble members (~0.65 MB per member and step)")
    p.add_argument("--days", type=int, default=10, help="lead time in days (HRES max 10, ENS max 15)")
    p.add_argument("--members", type=int, default=10, choices=range(1, 51), metavar="1-50", help="ENS members")
    p.add_argument("--date", help="run date YYYY-MM-DD (default: latest; open data keeps only a few days)")
    p.set_defaults(func=download_forecast)

    p = sub.add_parser("observed", parents=[common], help="ERA5-Land daily statistics (track 1 verification)")
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--statistics", nargs="+", default=["daily_maximum", "daily_mean"],
                   choices=["daily_maximum", "daily_mean", "daily_minimum"])
    p.set_defaults(func=download_observed)

    p = sub.add_parser("cordex", parents=[common], help="EURO-CORDEX scenarios (track 2)")
    p.add_argument("--experiment", nargs="+", default=["rcp_4_5"], choices=list(CORDEX_YEARS))
    p.add_argument("--years", type=int, nargs="+", required=True, help="historical: 1970-2005, RCPs: 2006-2100")
    p.add_argument("--gcm", default="ichec_ec_earth", help="default matches the C3S discharge chain (ec_earth)")
    p.add_argument("--rcm", default="smhi_rca4", help="default matches the C3S discharge chain (rca4)")
    p.add_argument("--ensemble-member", default="r12i1p1")
    p.set_defaults(func=download_cordex)

    p = sub.add_parser("climatedt", parents=[common], help="DestinE Climate DT at the plants (track 2)")
    p.add_argument("--experiment", choices=list(CLIMATEDT_ACTIVITY), default="SSP3-7.0",
                   help="hist: 1990-2014, SSP3-7.0: 2015-2049 (same runs as HydroLand)")
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--resolution", choices=["standard", "high"], default="high",
                   help="high (~5 km) matches HydroLand; standard is coarser")
    p.add_argument("--address", default="polytope.mn5.apps.dte.destination-earth.eu",
                   help="Polytope server (the LUMI one is polytope.lumi.apps.dte.destination-earth.eu)")
    p.set_defaults(func=download_climatedt)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
