# Project parameters

Hand-made parameter tables. They are written by the project team, not
downloaded, and are not produced by a script.

## cooling_type_alpha.csv

Share of condenser heat that reaches the river (alpha) for each cooling type.
Used in methodology_cooling_constrain.md:

    Q_river,cooling = alpha * (P_th - P_el)

- cooling_type: the exact values of cooling_type in the JRC Open Power Plants
  Database (JRC_OPEN_UNITS.csv). The list of values and how often each occurs
  is generated in data/interim/jrc_open_power_plants/cooling_types.csv by
  data_processing/plants/process_jrc_units.py. Rows with no cooling type in
  JRC have no alpha.
- alpha: dimensionless, 0 to 1.
- rationale: short reason for the value.

Source: project assumptions in methodology_cooling_constrain.md (Table 1).
The values are not yet verified against literature or plant permits. Tower
values use the upper end of the 0-0.05 range so tower plants still count a
little. Keep Table 1 in the methodology document identical to this file.

Created 2026-10-24.

## temperature_limits.csv

Regulatory limits on how far each plant may warm its river, collected by hand
from permits and regulations. Used for T_limit and dT_limit in
methodology_cooling_constrain.md ("Temperature limits"). There are no
assumed or default values: a limit without a source stays empty.

One row per app facility (data/app_input/facilities.csv) and season period.
build_facilities.py stops if an app facility has no row, so a plant without
a source still needs a row with tier "missing".

- Location_ID, Name: GEM location ID and facility name.
- T_max_downstream_C: highest river temperature allowed downstream (°C).
- dT_max_C: highest warming of the river by the plant (°C).
- T_max_outfall_C: highest temperature of the discharged water (°C), where
  the permit sets one. Not carried into facilities.csv: the app does not
  model outfall limits, and plants with only an outfall limit get
  Temp_limits_status outfall_only (not covered).
- valid_from, valid_to: period as MM-DD (may wrap past 12-31); both empty =
  all year. facilities.csv takes the periods that cover 10-25. A plant may
  have gaps between periods when the source defines no dates (Astravets).
- averaging: how compliance is assessed (hourly, daily mean, ...).
- compliance_point: where the limit applies (e.g. after full mixing).
- derogation_T_max_downstream_C: exceptional limit granted in heatwaves.
- tier: where the value comes from, most specific first:
    permit         the plant's own permit or regulator decision, or a
                   document quoting it (EIA, operator or regulator report)
    national_rule  a national rule for discharges into that river
    missing        no source found; all limit columns empty
- source_type: primary (the permit or legal text itself) or secondary (a
  report, paper or article that states the value).
- source, legal_ref, url, accessed: citation. Required unless tier is
  missing.
- notes: a short quote of the sentence stating the limit, conditional rules,
  unit differences, observed curtailment triggers, and for tier missing what
  was searched.

Rows with a limit need at least one of T_max_downstream_C, dT_max_C and
T_max_outfall_C, plus source and url. A plant may have a permit row and a
national_rule row for the same period (e.g. a permit outfall limit and a
national river limit); facilities.csv then takes each value from the most
specific tier that sets it. Two rows of the same tier, or a missing and a
sourced row, must not cover the same day. build_facilities.py checks these
rules.

An empty value in a sourced row means the source sets no such limit or none
was found; the notes say which. For example, the four Loire plants'
decisions set only a warming limit and explicitly no downstream cap.

Collected 2026-10-24 from permits, regulator decisions, laws, EIAs and
operator reports (one research pass per country group). Choices made when
building the table:
- Ukraine (4 plants): tier missing. The only rule found, USSR SanPiN
  4630-88, may be repealed in Ukraine.
- Cofrentes, Jun-Sep: tier missing. The permit allows "+3 °C" in summer
  without stating the resulting outfall value.
- Kozloduy: Bulgarian Ordinance 6/2000 (+3 °C, all year). The EIA's 3 °C
  warmest-month / 5 °C coldest-month values do not define the months and
  are kept in the notes.
- Astravets: the decree's general "other waters" category, as the Viliya's
  fish-water class is unknown; calendar summer and winter, as the decree
  does not define the seasons.
Local copies of some cited documents, with notes, are in data/raw/regulations/.
Several permits found are old (Ascó 1977, Trillo 1985) and may have been
revised; the notes list what was not found. Some values come from secondary
sources (source_type).
