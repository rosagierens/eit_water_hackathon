# Methodology: Cooling constraint

Thermal power plants, such as nuclear plants, turn only part of their fuel energy into electricity. The rest is waste heat that must be removed by cooling, often with river water. In droughts and heatwaves, rivers carry less water and are already warm, so they can take less of that heat. When that happens, plants have to reduce output.

Key concepts:

- **Cooling need**: the waste heat a power plant has to get rid of while generating electricity. It depends on how large the plant is, how efficient it is, and how hard it is running. How much of this heat ends up in the river depends on the cooling system:
  - Once-through cooling takes in river water, warms it, and returns it, so almost all the waste heat goes into the river.
  - Cooling towers release most of the heat to the air by evaporating water, so very little heat reaches the river, but water is lost.
- **River heat absorption capacity** (\(Q_{\mathrm{heat,max}}\)): the most waste heat a river can take before its downstream temperature reaches the legal limit set to protect river ecosystems. It’s larger when the river carries more water and when the water is cool. It shrinks sharply during droughts (less water) and heatwaves (warmer water), often both at once.

**How the two are used together**
We compare the amount of the plant’s cooling need that the river needs to absorb (\(Q_{\mathrm{river,cooling}}\)) with the river’s heat absorption capacity (\(Q_{\mathrm{heat,max}}\)) at a given location and time:

- If the river can absorb all the heat, the plant can run at full output.
- If the plant’s heat exceeds what the river can absorb, the plant must cut output until its waste heat fits within the river’s limit.

## Cooling need

A power plant converts input energy to electricity and wasted heat. The energy balance equation for a thermal power plant can be written as

\[
P_{\mathrm{th}} = P_{\mathrm{el}} + Q_{\mathrm{cool}} + Q_{\mathrm{stack}} + Q_{\mathrm{other}}
\]

where

| Term | Meaning | Units |
| --- | --- | --- |
| \(P_{\mathrm{th}}\) | Thermal input from fuel or reactor | \(\mathrm{MW_{th}}\) |
| \(P_{\mathrm{el}}\) | Gross electrical output (capacity) | \(\mathrm{MW_{el}}\) |
| \(Q_{\mathrm{cool}}\) | Heat taken away by the cooling system | \(\mathrm{MW_{th}}\) |
| \(Q_{\mathrm{stack}}\) | Heat lost through the exhaust stack | \(\mathrm{MW_{th}}\) |
| \(Q_{\mathrm{other}}\) | Small losses: heat escaping from pipes, buildings, generator, transformers | \(\mathrm{MW_{th}}\) |

For nuclear power plants, we can assume \(Q_{\mathrm{stack}} \approx 0\) and \(Q_{\mathrm{other}} \approx 0\). The above equation then becomes

\[
Q_{\mathrm{cool}} = P_{\mathrm{th}} - P_{\mathrm{el}}.
\]

The heat reaching the river can be approximated as

\[
Q_{\mathrm{river,cooling}} = \alpha \, Q_{\mathrm{cool}}
\]

where \(\alpha\) is set based on the cooling technology as given in Table 1.

**Table 1.** Share of cooling heat reaching the river (\(\alpha\)), by cooling type. The cooling types are the values of `cooling_type` in the JRC Open Power Plants Database. The values are project assumptions and still need to be verified. This table must stay identical to `data/raw/project_parameters/cooling_type_alpha.csv`, which the processing scripts read.

| Cooling type (JRC) | \(\alpha\) | Rationale |
| --- | --- | --- |
| Once-through | 1.0 | River water passes the condenser once and returns warmed, so almost all condenser heat reaches the river. |
| Natural Draught Tower | 0.05 | Closed loop: most heat leaves by evaporation to the air; only blowdown warms the river. Upper end of the 0–0.05 range. |
| Mechanical Draught Tower | 0.05 | Closed loop like a natural draught tower; fans only change how air moves through the tower. Upper end of the 0–0.05 range. |
| Air Cooling | 0.0 | Dry cooling: heat goes to the air without cooling water. |
| No Cooling | 0.0 | No cooling system, so no heat reaches the river. |

All operating nuclear units in JRC are once-through, natural draught tower or mechanical draught tower. JRC has no hybrid or "helper" tower category. Such towers fall between once-through and closed-loop towers, and some plants switch them on only in summer to protect the river, so a single \(\alpha\) does not describe them well.

The heat from the nuclear power plant that the river has to absorb is thus

\[
Q_{\mathrm{river,cooling}} = \alpha \, (P_{\mathrm{th}} - P_{\mathrm{el}}).
\]

To consider the cooling constraint relative to the maximum amount of electricity the plant can produce, we can simply use capacity for \(P_{\mathrm{el}}\).

### Facilities with several units

The river constraint applies to a whole facility (one intake and outfall, one permit), but \(P_{\mathrm{th}}\), \(P_{\mathrm{el}}\) and the cooling type belong to each reactor unit. Units at the same facility can use different cooling types (for example Doel and Bugey). Heat is additive, so the heat reaching the river is calculated per unit \(i\) and summed:

\[
Q_{\mathrm{river,cooling}} = \sum_i \alpha_i \, (P_{\mathrm{th},i} - P_{\mathrm{el},i})
\]

The facility \(\alpha\) is the heat-weighted mean of the unit values:

\[
\alpha_{\mathrm{facility}} = \frac{\sum_i \alpha_i \, (P_{\mathrm{th},i} - P_{\mathrm{el},i})}{\sum_i (P_{\mathrm{th},i} - P_{\mathrm{el},i})}
\]

so that \(Q_{\mathrm{river,cooling}} = \alpha_{\mathrm{facility}} \sum_i (P_{\mathrm{th},i} - P_{\mathrm{el},i})\). If any unit at a facility has no cooling type, \(\alpha_{\mathrm{facility}}\) is left empty rather than computed from the remaining units.

JRC lists turbogenerators rather than reactors, and some reactors have two. Their cooling type is taken per reactor; capacities always come from GEM.

## River heat absorption capacity

We calculate the river heat absorption capacity following the equation for energy balance of a flowing fluid (Ptak et al., 2026):

\[
Q_{\mathrm{heat,max}} = \rho \, c_p \, Q_{\mathrm{river}} \, \min\left(T_{\mathrm{limit}} - T_{\mathrm{river}},\ \Delta T_{\mathrm{limit}}\right)
\]

Permits can cap the absolute downstream temperature (\(T_{\mathrm{limit}}\)), the warming caused by the plant (\(\Delta T_{\mathrm{limit}}\)), or both. The smaller of the two allowed rises applies. If a plant has only one of the two limits, only that term is used.

| Symbol | Meaning | Units | Additional information |
| --- | --- | --- | --- |
| \(Q_{\mathrm{heat,max}}\) | Maximum heat the river can absorb before downstream temperature reaches the limit | W (J/s), often shown as \(\mathrm{MW_{th}}\) |  |
| \(\rho\) | Density of water | \(\mathrm{kg/m^3}\) | 1000 (constant) |
| \(c_p\) | Specific heat capacity of water | \(\mathrm{J/(kg \cdot K)}\) | 4186 (constant) |
| \(Q_{\mathrm{river}}\) | River discharge (volume flow) upstream of the plant | \(\mathrm{m^3/s}\) |  |
| \(T_{\mathrm{limit}}\) | Highest downstream water temperature allowed by the plant’s permit | \(^\circ\mathrm{C}\) | Plant-specific, from `data/raw/project_parameters/temperature_limits.csv`. Empty when no source was found. |
| \(T_{\mathrm{river}}\) | River water temperature upstream of the plant | \(^\circ\mathrm{C}\) | |
| \(T_{\mathrm{limit}} - T_{\mathrm{river}}\) | Remaining temperature rise the river can take before hitting the absolute limit | \(^\circ\mathrm{C}\) | |
| \(\Delta T_{\mathrm{limit}}\) | Highest warming of the river by the plant (downstream minus upstream) allowed by the permit | \(^\circ\mathrm{C}\) | Plant-specific, from `data/raw/project_parameters/temperature_limits.csv`. Empty when no source was found. |

## Curtailment

The first version uses four simplifying assumptions:

1. **One facility, one plant.** Each facility is treated as a single plant with \(\alpha_{\mathrm{facility}}\), so all its units cut output by the same share.
2. **Heat scales with output.** Efficiency is constant, so at a share \(f\) of full output the heat reaching the river is \(f\) times its full-output value.
3. **Full mixing.** The plant's warm water mixes completely with the whole river flow.
4. **Only the river heat limit counts.** Other limits, such as water for tower make-up or the intake temperature, are ignored.

The share of its capacity the facility can use is

\[
f = \min\left(1,\ \frac{\max(0,\ Q_{\mathrm{heat,max}})}{Q_{\mathrm{river,cooling}}}\right)
\]

where \(Q_{\mathrm{river,cooling}}\) is the facility's heat to the river at full output and \(Q_{\mathrm{heat,max}}\) is converted to \(\mathrm{MW_{th}}\). The \(\max(0, \cdot)\) covers a river that is already warmer than \(T_{\mathrm{limit}}\): the plant can then put no heat into it. Available output and curtailment are

\[
P_{\mathrm{el,available}} = f \, P_{\mathrm{el}}, \qquad P_{\mathrm{el,curtailed}} = (1 - f) \, P_{\mathrm{el}}
\]

with \(P_{\mathrm{el}}\) the facility's total capacity.


## Data sources

| Parameter | Data source | Variable in data source |
| --- | --- | --- | 
| location | GEM Global Nuclear Power Tracker | Latitude, Longitude |
| \(P_{\mathrm{th}}\) | GEM Global Nuclear Power Tracker | Thermal Capacity (MWt)
| \(P_{\mathrm{el}}\) | GEM Global Nuclear Power Tracker | Capacity (MW)
| cooling type | JRC Open Power Plants Database | cooling_type (per generator, combined per reactor)
| \(\alpha\) | Project assumption, `data/raw/project_parameters/cooling_type_alpha.csv` | alpha (by cooling_type, Table 1)
| \(Q_{\mathrm{river}}\) | | 
| \(T_{\mathrm{river}}\) | | 
| \(T_{\mathrm{limit}}\) | Plant permits, national rules or the EU Freshwater Fish Directive, collected by hand in `data/raw/project_parameters/temperature_limits.csv` | T_max_downstream_C
| \(\Delta T_{\mathrm{limit}}\) | As for \(T_{\mathrm{limit}}\) | dT_max_C

## Temperature limits

Europe has no dataset of permit limits, so they are collected by hand (carried out by Claude, unverified), one row per plant (and per season where the permit differs by season), in `data/raw/project_parameters/temperature_limits.csv`. Each value comes from the most specific source found:

1. **permit**: the plant's own permit or regulator decision, or a document that quotes it (environmental impact assessment, operator or regulator report).
2. **national_rule**: a national rule for thermal discharges into that river.
3. **missing**: no source found. The limits stay empty.

Every row cites its source, so values can be checked and replaced when a better source turns up. Each value comes from the most specific tier that sets it.

Some permits do not fit the equation above as written:

- **Only one of the two limits.** The four Loire plants have only \(\Delta T_{\mathrm{limit}}\) (1 °C), and Paks and Bohunice only \(T_{\mathrm{limit}}\). Only the term that exists is used.
- **Only an outfall limit.** These plants are not covered by the app; see below.
- **Conditional rules.** Some limits change with upstream temperature or flow. Examples: Cattenom allows no warming above 28 °C upstream; Civaux allows none above 25 °C; the Loire plants allow 1.5 °C at low flow and cool water; Tricastin allows 6 °C below 480 m³/s. These rules are in the notes of `temperature_limits.csv`, and the facility table carries only the base values.

### Plants not covered: outfall limits

Some permits cap the temperature of the water the plant discharges (the outfall), measured before it mixes into the river. The app does not model outfall limits. Plants whose only limit is on the outfall are not covered. Plants with both a river limit and an outfall limit are covered through the river limit only.

The outfall values collected are stored in `T_max_outfall_C` in `temperature_limits.csv` but not used in the application.

Why the river equation does not apply: an outfall limit is reached when the intake water plus the condenser warming exceeds the cap. The flow that matters is the plant's own cooling-water flow, not the river discharge. The outfall of tower plants and cooling reservoirs depends on the tower or reservoir heat balance instead, which needs a separate model.

## Citations

Ptak et al., Cooling Potential of the Warta River in Poznań (Poland) for Sustainable Energy Systems: Determinants and Seasonal Variability, Sustainability, 2026, 18(16), 8392; https://doi.org/10.3390/su18168392
