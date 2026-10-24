# Data for nuclear power plants

First-version processing. Later versions may sum capacities and count units
per location, and fill cooling type and temperature limits.

Run: python data_in/src/pp_data_processing/process_plants.py

## Step A — unit extract

Source: nucler_plants/Global-Nuclear-Power-Tracker-August-2026.xlsx, sheet "Data".

- Filter to Status "operating" and Region "Europe".
- Keep all GEM columns; no rename.

Saved as nucler_plants/Operating_Europe.csv.

## Step B — facility file for the app (to be updated)

Input: the filtered table from step A.

- For each unique GEM location ID, keep the first row in GEM Data sheet order
  (pandas drop_duplicates keep="first"). Do not sum other units. This is a
  temporary solution. Location_ID is unique. Lat/Lon come from that first unit
  (four plants have slightly different coordinates per unit: Cernavoda, Heysham,
  Kursk, Olkiluoto).

Columns in data_cleaned/units.csv, in this order:

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
- Cooling_type      empty (NaN); fill later (JRC)
- Temp_limit        empty (NaN)
- Temp_change_limit empty (NaN)

Dropped: every other GEM column (Unit Name, operator, dates, wiki URL, etc.).

This file is the GEM facility table. The JRC script writes
data_cleaned/jrc_units.csv instead, so it does not overwrite this file.
