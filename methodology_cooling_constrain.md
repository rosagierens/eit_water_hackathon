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

A power plant converts input energy to electricty and wasted heat. The energy balance equation for a thermal power plant can be written as

\[
P_{\mathrm{th}} = P_{\mathrm{el}} + Q_{\mathrm{cool}} + Q_{\mathrm{stack}} + Q_{\mathrm{other}}
\]

where

| Term | Meaning | Units |
| --- | --- | --- |
| \(P_{\mathrm{th}}\) | Thermal input from fuel or reactor | \(\mathrm{MW_{th}}\) |
| \(P_{\mathrm{el,gross}}\) | Gross electrical output | \(\mathrm{MW_{el}}\) |
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

**Table 1.** Share of cooling heat reaching the river (\(\alpha\)), by cooling type. From Claude, needs to be verified.

| Cooling type | \(\alpha\) |
| --- | --- |
| Once-through | \(\sim 1.0\) |
| Wet cooling tower (closed loop) | \(\sim 0\)–\(0.05\): most heat goes to the air by evaporation; only blowdown warms the river |
| Hybrid or “helper” towers | Between those, and often operated seasonally. Some plants switch towers on in summer specifically to protect the river |
| Dry / air-cooled | \(0\) |

The cooling need for the nuclear power plant is thus expressed as

\[
Q_{\mathrm{cool}} = \alpha \, (P_{\mathrm{th}} - P_{\mathrm{el}}).
\]

To consider the cooling constraint relative to the maximum amount of electricity the plant can produce, we can simply use capacity for \(P_{\mathrm{el}}\).

## River heat absorption capacity

We calculate the river heat absorption capacity following the equation for energy balance of a flowing fluid (Ptak et al., 2026):

\[
Q_{\mathrm{heat,max}} = \rho \, c_p \, Q_{\mathrm{river}} \, (T_{\mathrm{limit}} - T_{\mathrm{river}})
\]

| Symbol | Meaning | Units | Additional information |
| --- | --- | --- | --- |
| \(Q_{\mathrm{heat,max}}\) | Maximum heat the river can absorb before downstream temperature reaches the limit | W (J/s), often shown as \(\mathrm{MW_{th}}\) |  |
| \(\rho\) | Density of water | \(\mathrm{kg/m^3}\) | 1000 (constant) |
| \(c_p\) | Specific heat capacity of water | \(\mathrm{J/(kg \cdot K)}\) | 4186 (constant) |
| \(Q_{\mathrm{river}}\) | River discharge (volume flow) upstream of the plant | \(\mathrm{m^3/s}\) |  |
| \(T_{\mathrm{limit}}\) | Highest downstream water temperature allowed by the plant’s permit | \(^\circ\mathrm{C}\) | Plant- or country-specific, often 25–28 \(^\circ\mathrm{C}\) in Europe. (from Claude, unverified.) |
| \(T_{\mathrm{river}}\) | River water temperature upstream of the plant | \(^\circ\mathrm{C}\) | |
| \(\Delta T = T_{\mathrm{limit}} - T_{\mathrm{river}}\) | Remaining temperature rise the river can take before hitting the limit | \(^\circ\mathrm{C}\) | Some regulations also cap \(\Delta T\) itself (maximum warming of the river by the plant), not only the absolute downstream temperature. (from Claude, unverified.) |

## Data sources

| Parameter | Data source | Variable in data source |
| --- | --- | --- | 
| location | GEM Global Nuclear Power Tracker | lat, lon |
| \(P_{\mathrm{th}}\) | GEM Global Nuclear Power Tracker | Thermal Capacity (MWt)
| \(P_{\mathrm{el}}\) | GEM Global Nuclear Power Tracker | Capacity (MW)
| cooling-type | JRC Open Power Plants Database | 
| \(Q_{\mathrm{river}}\) | | 
| \(T_{\mathrm{river}}\) | | 
| \(T_{\mathrm{limit}}\) | |
| \(\Delta T_{\mathrm{limit}}\) | |

## Citations

Ptak et al., Cooling Potential of the Warta River in Poznań (Poland) for Sustainable Energy Systems: Determinants and Seasonal Variability, Sustainability, 2026, 18(16), 8392; https://doi.org/10.3390/su18168392
