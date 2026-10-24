"""Aggregate the merged GEM-JRC reactor table to one row per facility (GEM location ID).

Heat is summed per facility and Alpha is the heat-weighted mean of the unit values.
Temperature limits come from the hand-made, sourced table
data/raw/project_parameters/temperature_limits.csv; there are no default values.
The water-type filter runs last, on the finished facility table, so it is easy to undo.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Facilities whose Water_type is in this set are left out of the app input.
# Empty the set to keep them; facilities_all.csv always has every facility.
EXCLUDED_WATER_TYPES = {"Seawater"}

# Limit tiers, most specific first. "missing" means no source was found: the limits stay empty.
LIMIT_TIERS = ["permit", "national_rule", "missing"]

# facilities.csv carries the limits that apply on this day (MM-DD), when heatwave curtailments happen.
# The full table, with every seasonal period, stays in temperature_limits.csv.
LIMIT_REFERENCE_DAY = "07-15"

# River limit columns in temperature_limits.csv and their names in facilities.csv. Each value is taken from
# the most specific tier that sets it, e.g. a national rule's downstream limit next to a permit's warming limit.
LIMIT_VALUES = {
    "T_max_downstream_C": "Temp_limit",
    "dT_max_C": "Temp_change_limit",
}

# Kept in temperature_limits.csv but not carried to facilities.csv: the app does not model outfall limits.
# Plants whose only regulated limit is the outfall temperature get Temp_limits_status "outfall_only".
OUTFALL_COLUMN = "T_max_outfall_C"

FACILITY_COLUMNS = [
    "Location_ID",
    "Name",
    "Lat",
    "Lon",
    "Country",
    "Capacity_MW",
    "P_thermal_MW_th",
    "N_units",
    "Cooling_type",
    "Temp_limits_status",
    "Temp_limit",
    "Temp_limit_tier",
    "Temp_change_limit",
    "Temp_change_limit_tier",
    "Temp_limit_sources",
    "Water_type",
    "Q_cool_MW_th",
    "Q_river_MW_th",
    "Alpha",
    "Cooling_data_flag",
]


def combined_type(values: pd.Series, mixed_label) -> str:
    """The single value, a mixed label if units differ, or empty if any unit has none."""
    if values.isna().any():
        return ""
    unique = sorted(values.unique())
    return unique[0] if len(unique) == 1 else mixed_label(unique)


def summarise(units: pd.DataFrame) -> pd.Series:
    first = units.iloc[0]
    complete = units["Q_river_MW_th"].notna().all()
    q_cool = units["Q_cool_MW_th"].sum()
    q_river = units["Q_river_MW_th"].sum() if complete else np.nan
    if (units["cooling_source"] == "missing").any():
        flag = "missing"
    elif (units["cooling_source"] == "site_sibling").any():
        flag = "inferred_from_site"
    else:
        flag = ""
    return pd.Series(
        {
            "Name": first["Project Name"],
            "Lat": first["Latitude"],
            "Lon": first["Longitude"],
            "Country": first["Country/Area"],
            "Capacity_MW": units["Capacity (MW)"].sum(),
            "P_thermal_MW_th": units["Thermal Capacity (MWt)"].sum(),
            "N_units": len(units),
            "Cooling_type": combined_type(
                units["cooling_type"], lambda v: f"Mixed ({'/'.join(v)})"
            ),
            "Water_type": combined_type(units["water_type"], lambda v: "Mixed"),
            "Q_cool_MW_th": q_cool,
            "Q_river_MW_th": q_river,
            "Alpha": q_river / q_cool,
            "Cooling_data_flag": flag,
        }
    )


def build_facilities(units: pd.DataFrame, limits: pd.DataFrame) -> pd.DataFrame:
    facilities = units.groupby("GEM location ID", sort=False).apply(
        summarise, include_groups=False
    )
    facilities.index.name = "Location_ID"
    facilities = facilities.reset_index().merge(limits, on="Location_ID", how="left")
    return facilities[FACILITY_COLUMNS]


def covers(valid_from, valid_to, day: str) -> bool:
    """Whether the MM-DD period covers `day`. Empty bounds mean all year; periods may wrap past 12-31."""
    if pd.isna(valid_from) and pd.isna(valid_to):
        return True
    if valid_from <= valid_to:
        return valid_from <= day <= valid_to
    return day >= valid_from or day <= valid_to


def check_limits(table: pd.DataFrame) -> None:
    """Stop on rows that break the rules in data/raw/project_parameters/readme.txt."""
    errors = []
    for i, row in table.iterrows():
        where = f"row {i + 2} ({row['Location_ID']} {row['Name']})"
        has_value = row[[*LIMIT_VALUES, OUTFALL_COLUMN]].notna().any()
        if row["tier"] not in LIMIT_TIERS:
            errors.append(f"{where}: tier {row['tier']!r} is not one of {LIMIT_TIERS}")
        elif row["tier"] == "missing" and has_value:
            errors.append(f"{where}: tier 'missing' must have empty limits")
        elif row["tier"] != "missing" and not has_value:
            errors.append(
                f"{where}: needs at least one of {[*LIMIT_VALUES, OUTFALL_COLUMN]}, or tier 'missing'"
            )
        if row["tier"] != "missing" and (pd.isna(row["source"]) or pd.isna(row["url"])):
            errors.append(f"{where}: a limit needs a source and url")
        if pd.isna(row["valid_from"]) != pd.isna(row["valid_to"]):
            errors.append(f"{where}: give both valid_from and valid_to, or neither")
    if errors:
        sys.exit("temperature_limits.csv:\n  " + "\n  ".join(errors))


def reference_limits(table: pd.DataFrame) -> pd.DataFrame:
    """One row per facility: each limit on LIMIT_REFERENCE_DAY, from the most specific tier that sets it.

    A limit that no sourced row sets stays empty with an empty tier: either the permit has no such
    limit (e.g. Loire plants have no downstream cap) or none was found; the notes say which.
    Temp_limits_status is "sourced" if any period has a river limit, "outfall_only" if the sourced
    rows only limit the outfall temperature, and "missing" if no row is sourced.
    """
    sourced = table[table["tier"] != "missing"]
    river = set(
        sourced.loc[sourced[list(LIMIT_VALUES)].notna().any(axis=1), "Location_ID"]
    )
    outfall_only = set(sourced["Location_ID"]) - river

    covering = [
        covers(f, t, LIMIT_REFERENCE_DAY)
        for f, t in zip(table["valid_from"], table["valid_to"])
    ]
    chosen = table[covering]
    counts = chosen.groupby(["Location_ID", "tier"]).size()
    errors = [
        f"{lid}: {n} {tier} periods cover {LIMIT_REFERENCE_DAY}"
        for (lid, tier), n in counts[counts > 1].items()
    ]
    errors += [
        f"{lid}: no period covers {LIMIT_REFERENCE_DAY}"
        for lid in set(table["Location_ID"]) - set(chosen["Location_ID"])
    ]
    mixed = chosen.groupby("Location_ID")["tier"].agg(
        lambda t: "missing" in set(t) and len(set(t)) > 1
    )
    errors += [
        f"{lid}: a 'missing' period and a sourced period both cover {LIMIT_REFERENCE_DAY}"
        for lid in mixed[mixed].index
    ]
    if errors:
        sys.exit("temperature_limits.csv:\n  " + "\n  ".join(sorted(errors)))

    records = []
    for lid, rows in chosen.groupby("Location_ID", sort=False):
        rows = rows.sort_values("tier", key=lambda t: t.map(LIMIT_TIERS.index))
        status = (
            "sourced"
            if lid in river
            else "outfall_only" if lid in outfall_only else "missing"
        )
        record = {"Location_ID": lid, "Temp_limits_status": status}
        used = []
        for column, name in LIMIT_VALUES.items():
            setting = rows[rows[column].notna()]
            record[name] = setting[column].iloc[0] if len(setting) else np.nan
            record[f"{name}_tier"] = setting["tier"].iloc[0] if len(setting) else ""
            if len(setting):
                used.append(setting["source"].iloc[0])
        record["Temp_limit_sources"] = "; ".join(dict.fromkeys(used))
        records.append(record)
    return pd.DataFrame(records)


def require_limits(facilities: pd.DataFrame) -> None:
    """Every app facility needs a row in temperature_limits.csv, even if only to record tier 'missing'."""
    absent = facilities[facilities["Temp_limits_status"].isna()]
    if len(absent):
        listed = "\n  ".join(f"{r.Location_ID} {r.Name}" for r in absent.itertuples())
        sys.exit(
            f"No row in temperature_limits.csv for {len(absent)} app facilities:\n  {listed}"
        )
    print("Temperature limit status:")
    print(facilities["Temp_limits_status"].value_counts().to_string())
    print("River temperature limits (facilities per tier of each value):")
    tiers = facilities[[f"{name}_tier" for name in LIMIT_VALUES.values()]].replace(
        "", "not set"
    )
    print(tiers.apply(pd.Series.value_counts).fillna(0).astype(int).to_string())


def exclude_water_types(facilities: pd.DataFrame) -> pd.DataFrame:
    dropped = facilities["Water_type"].isin(EXCLUDED_WATER_TYPES)
    print(
        f"Left out of the app input ({sorted(EXCLUDED_WATER_TYPES)} water type): {dropped.sum()} facilities"
    )
    print(
        ", ".join(
            facilities.loc[dropped, "Name"].str.replace(
                " nuclear power plant", "", regex=False
            )
        )
    )
    return facilities[~dropped].reset_index(drop=True)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    units_csv = repo_root / "data" / "interim" / "nuclear_units" / "units_gem_jrc.csv"
    all_csv = repo_root / "data" / "interim" / "nuclear_units" / "facilities_all.csv"
    limits_csv = (
        repo_root / "data" / "raw" / "project_parameters" / "temperature_limits.csv"
    )
    out_csv = repo_root / "data" / "app_input" / "facilities.csv"

    units = pd.read_csv(units_csv, dtype={"Unit Name": str})
    limits = pd.read_csv(limits_csv, dtype={"valid_from": str, "valid_to": str})
    check_limits(limits)
    facilities = build_facilities(units, reference_limits(limits))
    unknown = set(limits["Location_ID"]) - set(facilities["Location_ID"])
    if unknown:
        sys.exit(
            f"temperature_limits.csv has Location_IDs that are not facilities: {sorted(unknown)}"
        )
    print(f"Facilities: {len(facilities)}")
    print(
        facilities["Cooling_data_flag"].replace("", "none").value_counts().to_string()
    )
    facilities.to_csv(all_csv, index=False)

    app_facilities = exclude_water_types(facilities)
    print(f"Facilities in the app input: {len(app_facilities)}")
    require_limits(app_facilities)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    app_facilities.to_csv(out_csv, index=False)


if __name__ == "__main__":
    main()
