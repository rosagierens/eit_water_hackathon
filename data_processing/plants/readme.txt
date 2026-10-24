# Data for nuclear power plants

First-version processing. Later versions may sum capacities and count units
per location, and fill cooling type and temperature limits.

Run: python data_processing/plants/process_plants.py

## Step A — unit extract

Source: data/raw/global_nuclear_power_tracker/Global-Nuclear-Power-Tracker-August-2026.xlsx, sheet "Data".

- Filter to Status "operating" and Region "Europe", excluding Country/Area "Russia".
- Keep all GEM columns; no rename.

Saved as data/interim/global_nuclear_power_tracker/Operating_Europe.csv.

## Step B — facility file for the app (to be updated)

Input: the filtered table from step A.

- For each unique GEM location ID, keep the first row in GEM Data sheet order
  (pandas drop_duplicates keep="first"). Do not sum other units. This is a
  temporary solution. Location_ID is unique. Lat/Lon come from that first unit
  (four plants have slightly different coordinates per unit: Cernavoda, Heysham,
  Kursk, Olkiluoto).

Columns in data/app_input/facilities.csv, in this order:

Kept and renamed:

- Location_ID       <- GEM location ID
- Name              <- Project Name
- Lat               <- Latitude
- Lon               <- Longitude
- Country           <- Country/Area
- Capacity_MW       <- Capacity (MW) of the kept unit only
- P_thermal_MW_th   <- Thermal Capacity (MWt) of the kept unit only

Added:

- N_units           always 1 in this version
- Cooling_type      "Once-through" for every facility (provisional, unverified)
- Temp_limit        30.0 °C for every facility (provisional, unverified)
- Temp_change_limit 5.0 °C for every facility (provisional, unverified)

Dropped: every other GEM column (Unit Name, operator, dates, wiki URL, etc.).

This file is the GEM facility table. The JRC script is run separately with
`python data_processing/plants/process_jrc_units.py` and writes
`data/interim/jrc_open_power_plants/Nuclear_commissioned.csv`; it does not
overwrite the GEM facility table or supply its provisional cooling fields.
