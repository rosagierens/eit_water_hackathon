# Data for nuclear power plants

GEM operating units are merged with JRC cooling data and then aggregated to
facility level for the app.

Run from the repository root, in this order:

    python data_processing/plants/process_gem_units.py
    python data_processing/plants/process_jrc_units.py
    python data_processing/plants/merge_units.py
    python data_processing/plants/build_facilities.py

## GEM unit extract (process_gem_units.py)

Source: data/raw/global_nuclear_power_tracker/Global-Nuclear-Power-Tracker-August-2026.xlsx, sheet "Data".

- Filter to Status "operating" and Region "Europe", excluding Country/Area "Russia".
- Keep all GEM columns; no rename.

Saved as data/interim/global_nuclear_power_tracker/Operating_Europe.csv.

## JRC unit extract (process_jrc_units.py)

Source: data/raw/jrc_open_power_plants/JRC-PPDB-OPEN.ver1.0/JRC_OPEN_UNITS.csv.

- Filter to type_g "Nuclear" and drop rows whose status_g is "DECOMMISSIONED".
  JRC writes this status in both upper and lower case, so the comparison
  ignores case.
- Keep all JRC columns; no rename.
- JRC rows are generators, not reactors: some reactors have two turbogenerators
  (for example Loviisa, Forsmark, Ringhals, Bohunice, Mochovce, Paks).

Saved as data/interim/jrc_open_power_plants/Nuclear_commissioned.csv.

The script also writes data/interim/jrc_open_power_plants/cooling_types.csv:
every cooling_type value in JRC with its row count in the whole JRC table
(n_rows_all_jrc) and in the nuclear extract (n_rows_nuclear). An empty
cooling_type means JRC gives none. The alpha value for each cooling type is
set by hand in data/raw/project_parameters/cooling_type_alpha.csv.

## GEM-JRC unit merge (merge_units.py)

Inputs: the two extracts above, the full GEM workbook (for the status of
leftover JRC generators) and data/raw/project_parameters/cooling_type_alpha.csv.

Status always comes from GEM (2026). JRC (2019) is used only for cooling_type
and water_type; its capacities are used only to check the match.

1. Plant match. JRC generators that share lat/lon form a site. Each GEM
   location is matched to the nearest JRC site within 2 km (all matches are
   within about 1 km). The script stops if two GEM plants claim one JRC site.
2. Generator to reactor. JRC rows are generators; some reactors have two.
   Default rule: the first number in name_g is the reactor (DOEL 4,
   Loviisa 1 G11, Ringhals block 2 G21, EDUK_B2____), except two-digit turbine
   codes such as Bohunice TG42, where the first digit is the reactor. GEM
   "B-1" style unit names are read as "1". A plant with one GEM reactor and one
   JRC generator is matched directly. OVERRIDES in the script covers the rest:
   Kozloduy (G9/G10 -> 5/6), Heysham (HEYM11/12 -> A1/A2, HEYM27/28 -> B1/B2),
   Hartlepool (HRTL-1/2 -> A1/A2), Paks (gép pairs -> 1-4), Tihange (1N/1S -> 1)
   and Sizewell (SIZB-1/2 -> B). The generators of one reactor must agree on
   cooling_type and water_type, or the script stops.
3. Leftover JRC generators at matched sites are looked up in the full GEM
   workbook. They must be "retired" there, or the script stops.
4. Gaps. A reactor at a matched site that is not in JRC (built after 2019:
   Flamanville 3, Mochovce 3) copies cooling_type and water_type from the other
   reactors at the site if they all agree (cooling_source "site_sibling").
   Reactors at plants with no JRC site (Ukraine, Belarus) are not filled:
   cooling_source "missing", and cooling_type, water_type, alpha and
   Q_river_MW_th are empty. The script prints a warning listing them.
5. Heat. alpha is joined by cooling_type; the script stops on a cooling type
   that is not in the alpha table.
   Q_cool_MW_th = Thermal Capacity (MWt) - Capacity (MW)
   Q_river_MW_th = alpha * Q_cool_MW_th

The script prints a report: match counts, inferred and missing units, the
retired leftovers, reactors whose JRC capacity differs from GEM net capacity by
more than 10% (UK AGRs, Sizewell B and Ringhals 4; the names match, so these
are rating differences between the sources, not matching errors), and facilities whose units use different cooling types (Doel, Bugey;
Bugey's pattern, towers at units 3 and 5 only, should be checked against EDF).

Saved as data/interim/nuclear_units/units_gem_jrc.csv, one row per operating
GEM reactor (131). Columns: the GEM key columns (GEM unit ID, GEM location ID,
Project Name, Unit Name, Country/Area, Latitude, Longitude, Capacity (MW),
Reference Net Capacity (MW), Thermal Capacity (MWt)), then
jrc_site_distance_km, jrc_name_g and jrc_eic_g (";"-separated generators),
n_generators, jrc_capacity_sum, cooling_type, water_type, cooling_source
(jrc / site_sibling / missing), alpha, Q_cool_MW_th, Q_river_MW_th.

## Facility table (build_facilities.py)

Input: data/interim/nuclear_units/units_gem_jrc.csv. One row per GEM location
ID, in GEM sheet order.

- Location_ID       <- GEM location ID
- Name, Lat, Lon, Country <- first unit at the location (three plants have
  slightly different coordinates per unit: Cernavoda, Heysham, Olkiluoto)
- Capacity_MW       sum of Capacity (MW) over the units
- P_thermal_MW_th   sum of Thermal Capacity (MWt) over the units
- N_units           number of operating units
- Cooling_type      the units' cooling type, "Mixed (A/B)" if units differ,
                    empty if any unit has none
- Temp_limit        30.0 °C for every facility (provisional, unverified)
- Temp_change_limit 5.0 °C for every facility (provisional, unverified)
- Water_type        Freshwater / Seawater, "Mixed" if units differ, empty if
                    any unit has none
- Q_cool_MW_th      sum of Q_cool_MW_th over the units
- Q_river_MW_th     sum of Q_river_MW_th over the units; empty if any unit
                    has no cooling data
- Alpha             Q_river_MW_th / Q_cool_MW_th, the heat-weighted mean of
                    the unit alphas
- Cooling_data_flag empty, "inferred_from_site" (some unit copied its cooling
                    type from other reactors at the site) or "missing" (some
                    unit has no cooling data; Alpha and Q_river_MW_th empty)

All 51 facilities are saved as data/interim/nuclear_units/facilities_all.csv.

Water-type filter (last step): facilities whose Water_type is in
EXCLUDED_WATER_TYPES at the top of the script (currently {"Seawater"}) are left
out of data/app_input/facilities.csv, because the river constraint does not
apply to them. This drops 16 facilities and leaves 35. Facilities with an empty
Water_type (Ukraine, Belarus) are kept. To undo the filter, empty the set and
rerun the script. Note that JRC labels Blayais (Gironde estuary) as seawater
and Doel (Scheldt estuary) as freshwater.
