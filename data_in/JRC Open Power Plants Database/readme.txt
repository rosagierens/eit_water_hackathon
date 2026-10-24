## Data processing

From JRC_OPEN_UNITS.csv, keep rows where type_g = "Nuclear", water_type != "Seawater", and status_g != "DECOMMISSIONED".

To create location IDs:
- round lat and lon to 3 decimal places;
- create a unique location key from the rounded (lat, lon) pair;
- keep only one row per unique rounded coordinate pair;
- assign a sequential location_id to each unique pair.

To create pp_locations.csv:
- use the deduplicated rounded-location table;
- keep only location_id, lat, and lon;
- write as pp_locations.csv.

To create units.csv:
- use the filtered data;
- remove the original lat and lon columns;
- add the matching location_id for each row based on the rounded coordinate pair;
- save the result as units.csv.