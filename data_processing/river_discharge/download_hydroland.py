"""Download HydroLand (DestinE Climate DT, mHM/mRM) river discharge projections.

Source: DestinE Data Lake, Harmonised Data Access (HDA) STAC API,
collection EO.UFZ.DAT.HYDROLAND. Item IDs encode the simulation, e.g.

  EO.UFZ.DAT.HYDROLAND_20490801T000000_20490831T230000__IFS-NEMO__SSP3-7.0__generation-2__projections__realization-1__mrm
                       start           end               model      experiment generation   activity    realization  product

Products (one item per month for mrm/mhm, one item per indicator):
  mrm        hourly routed river discharge `Qrouted` (m3/s)   hist 1990-2014, SSP3-7.0 2015-2049
  mhm        daily soil water, evapotranspiration, runoff     same periods
  others     period indicators, e.g. 5th_percentile_discharge_indicators (hist only), aridity_index,
             soil_moisture_deficit_* (run `list` for the full set)

  python download_hydroland.py list                          # one line per product/experiment
  python download_hydroland.py download --start 2040-06-01 --end 2040-08-31 --dry-run
  python download_hydroland.py download --start 2040-06-01 --end 2040-08-31
  python download_hydroland.py download --product 5th_percentile_discharge_indicators

Downloads are kept under data/raw/hydroland. Cropped and daily-mean files are
written to data/interim/hydroland (see --no-crop, --hourly).

Credentials: your DestinE Service Platform (DESP) login, with upgraded access.
Set DESP_USERNAME and DESP_PASSWORD, or you will be prompted (also for an
OTP code if your account uses one).
"""

import argparse
import functools
import os
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime
from getpass import getpass
from pathlib import Path

import requests

STAC_URL = "https://hda.data.destination-earth.eu/stac/v2"
COLLECTION = "EO.UFZ.DAT.HYDROLAND"

# Europe [North, West, South, East], same box as download_river_discharge.py.
EUROPE_AREA = [72, -25, 34, 45]

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO / "data" / "raw" / "hydroland"
DEFAULT_INTERIM_DIR = REPO / "data" / "interim" / "hydroland"

ID_FIELDS = ("model", "experiment", "generation", "activity", "realization", "product")


def prompt(text):
    # Prompt on stderr so it stays visible when stdout is redirected to a file.
    print(text, end="", file=sys.stderr, flush=True)
    return input()


def auth_headers():
    import destinelab

    username = os.environ.get("DESP_USERNAME") or prompt("DESP username or email: ")
    password = os.environ.get("DESP_PASSWORD") or getpass("DESP password: ", stream=sys.stderr)
    desp_auth = functools.partial(destinelab.DESPAuth, otp_provider=lambda: prompt("DESP OTP code: "))
    token = destinelab.AuthHandler(username, password, desp_auth_class=desp_auth).get_token()
    if not token:
        raise SystemExit("Could not obtain a Data Lake token; check your DESP credentials and upgraded access")
    return {"Authorization": f"Bearer {token}"}


def search_items(headers, start=None, end=None):
    body = {"collections": [COLLECTION], "limit": 100}
    if start and end:
        body["datetime"] = f"{start}T00:00:00Z/{end}T23:59:59Z"
    url, items = f"{STAC_URL}/search", []
    while url:
        r = requests.post(url, json=body, headers=headers, timeout=120)
        r.raise_for_status()
        page = r.json()
        items += page.get("features", [])
        nxt = next((l for l in page.get("links", []) if l.get("rel") == "next"), None)
        url, body = (nxt["href"], nxt.get("body", body)) if nxt else (None, None)
    return items


def parse_id(item_id):
    """Split an item ID into its period and simulation fields (None if it doesn't match)."""
    head, *fields = item_id.split("__")
    m = re.search(r"_(\d{8})T\d{6}_(\d{8})T\d{6}$", head)
    if not m or len(fields) != len(ID_FIELDS):
        return None
    info = dict(zip(ID_FIELDS, fields))
    info["start"], info["end"] = (datetime.strptime(s, "%Y%m%d").date() for s in m.groups())
    return info


def nc_asset(item):
    """The item's NetCDF file (name, href); falls back to the generic downloadLink."""
    for key, asset in item.get("assets", {}).items():
        name = Path(asset.get("href", "").split("?")[0]).name
        if name.endswith(".nc"):
            return name, asset["href"]
    link = item["assets"]["downloadLink"]["href"]
    return f"{item['id']}.nc", link


def list_items(args):
    items = search_items(auth_headers())
    if not items:
        print("No items visible. Is upgraded access to Climate DT data active on your DESP account?")
    if args.full:
        for item in items:
            print(item["id"])
            for key, asset in item.get("assets", {}).items():
                print(f"    {key}: {asset.get('href')}")
        return
    groups = defaultdict(list)
    for item in items:
        info = parse_id(item["id"])
        if info is None:
            print(f"unrecognised item ID: {item['id']}")
            continue
        groups[tuple(info[f] for f in ID_FIELDS)].append(info)
    print(f"{len(items)} items\n")
    print(f"{'items':>5}  {'first':10}  {'last':10}  model / experiment / generation / activity / realization / product")
    for key, infos in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][5])):
        first = min(i["start"] for i in infos)
        last = max(i["end"] for i in infos)
        print(f"{len(infos):5d}  {first}  {last}  {' / '.join(key)}")


def postprocess(path, out, area, crop, hourly):
    """Crop to `area` and average hourly data to daily means, one day at a time to limit memory."""
    import numpy as np
    import xarray as xr

    with xr.open_dataset(path) as ds:
        if crop:
            north, west, south, east = area
            lat = next(c for c in ("lat", "latitude") if c in ds.coords)
            lon = next(c for c in ("lon", "longitude") if c in ds.coords)
            lat_slice = slice(north, south) if ds[lat][0] > ds[lat][-1] else slice(south, north)
            ds = ds.sel({lat: lat_slice, lon: slice(west, east)})
        steps = ds["time"].size if "time" in ds.dims else 0
        if not hourly and steps > 1 and (ds["time"][1] - ds["time"][0]).values < np.timedelta64(1, "D"):
            day_of_step = ds["time"].dt.floor("D").values
            days = [ds.isel(time=np.flatnonzero(day_of_step == d)).mean("time", keep_attrs=True)
                    .expand_dims(time=[d]) for d in np.unique(day_of_step)]
            ds = xr.concat(days, "time")
            ds.attrs["hydroland_postprocessing"] = "daily mean of hourly values"
        ds.load().to_netcdf(out)


def download(args):
    headers = auth_headers()
    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None
    if (start is None) != (end is None):
        raise SystemExit("Give both --start and --end, or neither")

    items = []
    for item in search_items(headers, start, end):
        info = parse_id(item["id"])
        if info is None or info["product"] != args.product:
            continue
        if args.experiment and info["experiment"] != args.experiment:
            continue
        if start and not (info["start"] <= end and info["end"] >= start):
            continue
        items.append((info, item))
    if not items:
        raise SystemExit(f"No '{args.product}' items between {start} and {end}; run `list` to see what exists")

    # Only mrm is hourly; mhm is already daily and indicators have no time axis.
    suffix = ("_europe" if not args.no_crop else "") + ("_daily" if args.product == "mrm" and not args.hourly else "")
    print(f"{len(items)} file(s) -> {args.out_dir} (processed: {args.interim_dir})")
    for info, item in sorted(items, key=lambda x: x[0]["start"]):
        name, href = nc_asset(item)
        raw_dir = args.out_dir / info["experiment"] / info["product"]
        raw_path = raw_dir / name
        out_dir = args.interim_dir / info["experiment"] / info["product"]
        out = out_dir / f"{Path(name).stem}{suffix}.nc"
        if args.dry_run:
            size = requests.head(href, headers=headers, allow_redirects=True, timeout=60).headers.get("Content-Length")
            print(f"  {name}  ({int(size) / 1e9:.1f} GB)" if size else f"  {name}  (size unknown)")
            continue
        print(f"  {name}")
        if out.exists() or (args.no_crop and args.hourly and raw_path.exists()):
            print("    already done, skipping")
            continue
        if not raw_path.exists():
            raw_dir.mkdir(parents=True, exist_ok=True)
            tmp = raw_dir / (name + ".part")
            fetch(href, headers, tmp)
            tmp.rename(raw_path)
        if args.no_crop and args.hourly:
            print(f"    -> {raw_path}")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            print("    cropping / averaging (no progress shown, can take a few minutes) ...", flush=True)
            postprocess(raw_path, out, args.area, crop=not args.no_crop, hourly=args.hourly)
            print(f"    -> {out}")


def fetch(href, headers, tmp):
    """Stream href to tmp with a progress line, resuming a partial .part file if the server allows it."""
    done = tmp.stat().st_size if tmp.exists() else 0
    resume_headers = {**headers, "Range": f"bytes={done}-"} if done else headers
    with requests.get(href, headers=resume_headers, stream=True, timeout=600) as r:
        if r.status_code == 416:  # range starts at the end: already complete
            return
        r.raise_for_status()
        if done and r.status_code != 206:
            print("    server does not support resuming; starting over", flush=True)
            done = 0
        total = done + int(r.headers.get("Content-Length", 0)) or None
        start, last = time.monotonic(), 0.0
        with open(tmp, "ab" if done else "wb") as f:
            got = done
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                got += len(chunk)
                now = time.monotonic()
                if now - last > 2:
                    rate = (got - done) / 1e6 / max(now - start, 1e-6)
                    of = f" of {total / 1e9:.1f} GB ({100 * got / total:.0f}%)" if total else ""
                    print(f"\r    {got / 1e9:.2f} GB{of}, {rate:.1f} MB/s   ", end="", flush=True)
                    last = now
        print(flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="summarise the available HydroLand items")
    p.add_argument("--full", action="store_true", help="print every item ID and asset link")
    p.set_defaults(func=list_items)

    p = sub.add_parser("download", help="download one product for a date range")
    p.add_argument("--product", default="mrm",
                   help="mrm (discharge, default), mhm, or an indicator name from `list`")
    p.add_argument("--start", help="YYYY-MM-DD (omit for indicator products)")
    p.add_argument("--end", help="YYYY-MM-DD")
    p.add_argument("--experiment", help="e.g. hist or SSP3-7.0 (default: any)")
    p.add_argument("--area", type=float, nargs=4, default=EUROPE_AREA, metavar=("N", "W", "S", "E"))
    p.add_argument("--no-crop", action="store_true", help="keep the global grid")
    p.add_argument("--hourly", action="store_true", help="keep hourly values instead of daily means")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--interim-dir", type=Path, default=DEFAULT_INTERIM_DIR)
    p.add_argument("--dry-run", action="store_true", help="show matching files and their sizes only")
    p.set_defaults(func=download)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
