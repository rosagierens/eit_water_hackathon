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
