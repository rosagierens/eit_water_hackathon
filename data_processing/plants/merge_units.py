"""Merge GEM operating reactor units with JRC cooling data.

JRC rows are turbogenerators, GEM rows are reactors. Each JRC generator is mapped
to a GEM reactor, its cooling type and water type are taken per reactor, and the
heat that reaches the river is computed per reactor. Status comes from GEM only.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

MAX_SITE_DISTANCE_KM = 2.0  # every real GEM-JRC plant match is under 1 km
CAPACITY_CHECK_TOLERANCE = 0.10  # report reactors where JRC and GEM net capacity differ by more

# JRC generator name -> GEM Unit Name, for generators the default rule does not resolve.
OVERRIDES = {
    # Kozloduy: JRC numbers the generators of units 5 and 6 as G9 and G10.
    "NPP KZL G9": "5",
    "NPP KZL G10": "6",
    # Heysham: HEYM1x is Heysham 1 (GEM A1/A2), HEYM2x is Heysham 2 (GEM B1/B2).
    "HEYM11": "A1",
    "HEYM12": "A2",
    "HEYM27": "B1",
    "HEYM28": "B2",
    # Hartlepool: GEM names the two reactors A1 and A2.
    "HRTL-1": "A1",
    "HRTL-2": "A2",
    # Paks: two generators (gép) per reactor.
    "PA_gép1": "1",
    "PA_gép2": "1",
    "PA_gép3": "2",
    "PA_gép4": "2",
    "PA_gép5": "3",
    "PA_gép6": "3",
    "PA_gép7": "4",
    "PA_gép8": "4",
    # Tihange 1: two generators, north and south.
    "TIHANGE 1N": "1",
    "TIHANGE 1S": "1",
    # Sizewell B: one reactor, two generators.
    "SIZB-1": "B",
    "SIZB-2": "B",
}

GEM_COLUMNS = [
    "GEM unit ID",
    "GEM location ID",
    "Project Name",
    "Unit Name",
    "Country/Area",
    "Latitude",
    "Longitude",
    "Capacity (MW)",
    "Reference Net Capacity (MW)",
    "Thermal Capacity (MWt)",
]

OUTPUT_COLUMNS = GEM_COLUMNS + [
    "jrc_site_distance_km",
    "jrc_name_g",
    "jrc_eic_g",
    "n_generators",
    "jrc_capacity_sum",
    "cooling_type",
    "water_type",
    "cooling_source",
    "alpha",
    "Q_cool_MW_th",
    "Q_river_MW_th",
]


def unit_key(name) -> str:
    """GEM Unit Name without the "B-" prefix some French plants use (B-1 -> 1)."""
    name = str(name).strip()
    return name[2:] if name.startswith("B-") else name


def jrc_reactor_number(name_g: str):
    """Reactor number in a JRC generator name, or None.

    The first number is the reactor (DOEL 4, Loviisa 1 G11, Ringhals block 2 G21,
    EDUK_B2____), except two-digit turbine codes like Bohunice TG42, where the
    first digit is the reactor.
    """
    turbine = re.search(r"TG(\d)\d\b", name_g)
    if turbine:
        return turbine.group(1)
    number = re.search(r"\d+", name_g)
    return number.group(0) if number else None


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def match_sites(gem: pd.DataFrame, jrc: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per GEM location with its nearest JRC site (generators sharing lat/lon) within the
    limit (jrc_site -1 if none), and the JRC generators with their site number."""
    sites = jrc[["lat", "lon"]].drop_duplicates().reset_index(drop=True)
    sites["jrc_site"] = sites.index
    plants = gem.groupby("GEM location ID")[["Latitude", "Longitude"]].mean().reset_index()
    dist = haversine_km(
        plants["Latitude"].values[:, None],
        plants["Longitude"].values[:, None],
        sites["lat"].values[None, :],
        sites["lon"].values[None, :],
    )
    matched = dist.min(axis=1) <= MAX_SITE_DISTANCE_KM
    plants["jrc_site"] = np.where(matched, sites["jrc_site"].values[dist.argmin(axis=1)], -1)
    plants["jrc_site_distance_km"] = np.where(matched, dist.min(axis=1).round(3), np.nan)
    claimed = plants.loc[plants["jrc_site"] >= 0, "jrc_site"]
    if claimed.duplicated().any():
        raise ValueError(f"JRC sites claimed by more than one GEM plant: {sorted(claimed[claimed.duplicated()])}")
    jrc_sites = jrc.merge(sites, on=["lat", "lon"])
    return plants[["GEM location ID", "jrc_site", "jrc_site_distance_km"]], jrc_sites


def assign_generators(gem: pd.DataFrame, jrc_sites: pd.DataFrame, plants: pd.DataFrame) -> pd.DataFrame:
    """JRC generators at matched sites, each with the GEM location ID and unit key it belongs to."""
    gens = jrc_sites.merge(plants.loc[plants["jrc_site"] >= 0, ["GEM location ID", "jrc_site"]], on="jrc_site")
    units_per_plant = gem.groupby("GEM location ID").size()
    gens_per_site = gens.groupby("jrc_site").size()

    def key(row):
        if row["name_g"] in OVERRIDES:
            return OVERRIDES[row["name_g"]]
        loc = row["GEM location ID"]
        if units_per_plant[loc] == 1 and gens_per_site[row["jrc_site"]] == 1:
            # Single reactor, single generator (Cofrentes, Gösgen, Krško, Borssele 30, ...).
            return unit_key(gem.loc[gem["GEM location ID"] == loc, "Unit Name"].iloc[0])
        return jrc_reactor_number(row["name_g"])

    gens["unit_key"] = gens.apply(key, axis=1).map(unit_key)
    return gens


def check_leftovers(leftovers: pd.DataFrame, gem_all: pd.DataFrame) -> pd.DataFrame:
    """JRC generators with no operating GEM reactor must be retired in GEM; anything else is an error."""
    gem_all = gem_all.assign(unit_key=gem_all["Unit Name"].map(unit_key))
    status = leftovers.merge(
        gem_all[["GEM location ID", "unit_key", "Status", "Retirement Year"]],
        on=["GEM location ID", "unit_key"],
        how="left",
    )
    unexplained = status[status["Status"] != "retired"]
    if not unexplained.empty:
        raise ValueError(
            "JRC generators with no operating GEM reactor that GEM does not list as retired:\n"
            + unexplained[["name_g", "GEM location ID", "unit_key", "Status"]].to_string(index=False)
        )
    return status


def combine_generators(gens: pd.DataFrame) -> pd.DataFrame:
    """One row per GEM reactor; cooling and water type must agree across its generators."""
    for column in ["cooling_type", "water_type"]:
        n_values = gens.groupby("GEM unit ID")[column].nunique(dropna=False)
        if (n_values > 1).any():
            raise ValueError(f"Generators of one reactor disagree on {column}: {list(n_values[n_values > 1].index)}")
    return (
        gens.groupby("GEM unit ID")
        .agg(
            jrc_name_g=("name_g", lambda s: ";".join(sorted(s))),
            jrc_eic_g=("eic_g", lambda s: ";".join(sorted(s))),
            n_generators=("name_g", "size"),
            jrc_capacity_sum=("capacity_g", "sum"),
            cooling_type=("cooling_type", "first"),
            water_type=("water_type", "first"),
        )
        .reset_index()
        .assign(cooling_source="jrc")
    )


def fill_from_site(units: pd.DataFrame, matched_locations: set) -> pd.DataFrame:
    """Reactors at a matched site but missing from JRC (built after 2019) copy the site's cooling,
    if all JRC reactors there agree. Everything else stays missing."""
    units = units.copy()
    from_jrc = units[units["cooling_source"] == "jrc"]
    site_values = from_jrc.groupby("GEM location ID")[["cooling_type", "water_type"]].agg(
        lambda s: s.iloc[0] if s.nunique() == 1 else None
    )
    for i in units.index[units["cooling_source"].isna()]:
        loc = units.at[i, "GEM location ID"]
        if loc in matched_locations and loc in site_values.index and site_values.loc[loc].notna().all():
            units.loc[i, ["cooling_type", "water_type"]] = site_values.loc[loc].values
            units.at[i, "cooling_source"] = "site_sibling"
        else:
            units.at[i, "cooling_source"] = "missing"
    return units


def add_heat(units: pd.DataFrame, alpha_table: pd.DataFrame) -> pd.DataFrame:
    unknown = set(units["cooling_type"].dropna()) - set(alpha_table["cooling_type"])
    if unknown:
        raise ValueError(f"Cooling types missing from cooling_type_alpha.csv: {sorted(unknown)}")
    units = units.merge(alpha_table[["cooling_type", "alpha"]], on="cooling_type", how="left")
    units["Q_cool_MW_th"] = units["Thermal Capacity (MWt)"] - units["Capacity (MW)"]
    units["Q_river_MW_th"] = units["alpha"] * units["Q_cool_MW_th"]
    return units


def report(units: pd.DataFrame, leftovers: pd.DataFrame) -> None:
    print(f"GEM operating units: {len(units)}")
    print(units["cooling_source"].value_counts().to_string())

    inferred = units[units["cooling_source"] == "site_sibling"]
    print("\nCooling type copied from other reactors at the same site:")
    print(inferred[["Project Name", "Unit Name", "cooling_type", "water_type"]].to_string(index=False))

    missing = units[units["cooling_source"] == "missing"]
    print(f"\nWARNING: {len(missing)} units have no cooling data (alpha and Q_river left empty):")
    print(missing.groupby(["Country/Area", "Project Name"]).size().rename("units").to_string())

    print("\nJRC generators at matched sites whose reactor GEM lists as retired:")
    print(leftovers[["name_g", "Status", "Retirement Year"]].to_string(index=False))

    jrc = units[units["cooling_source"] == "jrc"]
    ratio = jrc["jrc_capacity_sum"] / jrc["Reference Net Capacity (MW)"] - 1
    off = jrc.loc[ratio.abs() > CAPACITY_CHECK_TOLERANCE]
    print(f"\nReactors where JRC capacity differs from GEM net capacity by more than {CAPACITY_CHECK_TOLERANCE:.0%}:")
    print(
        off.assign(diff=ratio[off.index].map("{:+.1%}".format))[
            ["Project Name", "Unit Name", "jrc_name_g", "jrc_capacity_sum", "Reference Net Capacity (MW)", "diff"]
        ].to_string(index=False)
        if not off.empty
        else "none"
    )

    mixed = units.groupby("GEM location ID").filter(lambda d: d["cooling_type"].nunique() > 1)
    print("\nFacilities whose units use different cooling types (check against operator information):")
    print(mixed[["Project Name", "Unit Name", "cooling_type"]].to_string(index=False))


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    gem_csv = repo_root / "data" / "interim" / "global_nuclear_power_tracker" / "Operating_Europe.csv"
    gem_xlsx = (
        repo_root / "data" / "raw" / "global_nuclear_power_tracker" / "Global-Nuclear-Power-Tracker-August-2026.xlsx"
    )
    jrc_csv = repo_root / "data" / "interim" / "jrc_open_power_plants" / "Nuclear_commissioned.csv"
    alpha_csv = repo_root / "data" / "raw" / "project_parameters" / "cooling_type_alpha.csv"
    out_csv = repo_root / "data" / "interim" / "nuclear_units" / "units_gem_jrc.csv"

    gem = pd.read_csv(gem_csv, dtype={"Unit Name": str})
    gem["unit_key"] = gem["Unit Name"].map(unit_key)
    jrc = pd.read_csv(jrc_csv)
    alpha_table = pd.read_csv(alpha_csv)

    plants, jrc_sites = match_sites(gem, jrc)
    gens = assign_generators(gem, jrc_sites, plants)
    gens = gens.merge(gem[["GEM location ID", "unit_key", "GEM unit ID"]], on=["GEM location ID", "unit_key"], how="left")

    leftovers = gens[gens["GEM unit ID"].isna()]
    gem_all = pd.read_excel(gem_xlsx, sheet_name="Data", dtype={"Unit Name": str})
    leftovers = check_leftovers(leftovers, gem_all)

    units = gem[GEM_COLUMNS].merge(plants, on="GEM location ID")
    units = units.merge(combine_generators(gens.dropna(subset=["GEM unit ID"])), on="GEM unit ID", how="left")
    matched_locations = set(plants.loc[plants["jrc_site"] >= 0, "GEM location ID"])
    units = fill_from_site(units, matched_locations)
    units = add_heat(units, alpha_table)

    report(units, leftovers)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    units[OUTPUT_COLUMNS].to_csv(out_csv, index=False)


if __name__ == "__main__":
    main()
