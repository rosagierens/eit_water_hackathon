# Project context: climate/drought impact on power plant cooling (handoff from claude.ai)

## Goal
Build an application to plan and assess how droughts and high temperatures affect nuclear power plants (priority 1) and gas/combined-cycle plants (priority 2). The data must be comparable to plant water withdrawal/discharge, cooling constraints, and legislation (permit limits).

## Requirements (agreed)
- Geographic scope: Europe-wide
- Spatial detail: plant level AND catchment/river-reach scale (later extension to siting of new plants)
- Data access: no constraints (open, commercial, API all fine)
- Working preference: ask clarifying questions before giving detailed answers
- Date of research: 2026-10-24

Legend: [V] = verified against current docs in the previous conversation; [M] = from memory, verify version/URL/access before relying on it.

## Key insight
Plants are typically limited by (a) river discharge (dilution / available cooling water) and (b) downstream water temperature (permit limits). Discharge data is good Europe-wide. River water temperature (forecast and projection) is NOT available as a plant-scale European product, so it likely has to be modelled (e.g. air2stream-type statistical model or RBM-type process model) from air temperature + discharge, calibrated on gauge temperature records.

## Category 1: Observations, reanalyses, forecasts

### Discharge
| Dataset | Variables | Frequency | Resolution / coverage | Period / lead |
|---|---|---|---|---|
| EFAS v5 historical [V] | discharge, soil moisture, snow water equiv. | 6-hourly | 1 arcmin (~1.4 km), Europe; calibrated at 1903 gauges, regionalised for ungauged | 1992-01-01 to near real time (~6 day delay) |
| EFAS v5 forecasts [V] | discharge etc. | init. 00 and 12 UTC, 6-hourly | same grid | up to 15 days |
| EFAS reforecasts [V] | discharge | twice weekly init., 6-hourly | same grid | up to 46 days lead, 20 years |
| EFAS seasonal forecast/reforecast [V partly] | discharge, soil moisture, snow | daily | same grid | reforecasts from 1991; ~7 month horizon [M] |
| GloFAS v4 [M] | discharge | daily | ~0.05 deg, global | 1979-NRT; forecasts ~30 days |
| Hagemann & Stacke ERA5/E-OBS discharge [V] | discharge (HD model) | daily | high-res European | 1979-2018; no direct human impacts, better for trends |
| In-situ gauges | discharge (+ sometimes temperature) | 10 min to daily | points | varies |

In-situ sources: GRDC, European Water Archive, Copernicus hydrological data collection centre (feeds EFAS), national services (France Hub'Eau/Hydroportail, Swiss BAFU/FOEN, German BfG/Laender, UK NRFA + Environment Agency API, Spanish SAIH). Use gauges to bias-correct EFAS at each plant's river reach.

### Water temperature
| Dataset | Variables | Frequency | Coverage |
|---|---|---|---|
| National in-situ networks (BfG, BAFU, Hub'Eau, UK EA) | river water temperature | 10 min to daily | points, best on large rivers |
| BfG Rhine dataset [V] | daily water temp + discharge at Basel, Worms, Koblenz, Cologne; yearly NPP heat input 1969-2018 | daily/yearly | Rhine; rare pairing of plant heat input and river data |
| EEA WISE Waterbase [M] | water temperature among physico-chemical vars | irregular | station level, patchy |
| ESA CCI / C3S Lake Surface Water Temperature [M] | lake surface temperature | daily | ~1 km, 1995+ |
| LSTM reconstruction Switzerland [V, abstract only] | daily catchment-level water temp + discharge | daily | Switzerland, 1962-2023; check whether data is released |

### Meteorology and drought context
| Dataset | Variables | Frequency | Resolution / period |
|---|---|---|---|
| ERA5-Land [M] | air temp, humidity, wind, radiation, precip | hourly | 0.1 deg, 1950-NRT |
| E-OBS [M] | temp, precip, humidity, wind, radiation | daily | 0.1 deg, 1950+ |
| ECMWF ENS / extended range / SEAS5 / C3S seasonal [M] | air temp, precip, etc. | sub-daily to monthly | 15 days to 7 months lead |
| European Drought Observatory [M] | Combined Drought Indicator, SPI, low-flow index, soil moisture anomaly | 10-daily | ~5 km |

## Category 2: Climate-projection-based data
| Dataset | Variables | Frequency | Resolution / coverage | Period |
|---|---|---|---|---|
| DestinE HydroLand (Climate DT, mHM) [V] | evapotranspiration, soil moisture, runoff, river discharge, percentile-based flood/drought discharge indicators | hourly | 5 km, global | Climate DT simulation period (check exact coverage and access route); supports what-if/storyline runs (e.g. similar event at +2 deg C) |
| C3S hydrology-related climate impact indicators (sis-hydrology-variables-derived-projections) [V] | daily mean discharge, return values of annual max discharge, mean annual min discharge, N and P loads | daily (indicators are 30-year stats) | E-HYPE sub-basins, Europe [M] | 1970-2100, bias-adjusted European projections |
| EURO-CORDEX (+ bias-adjusted via C3S) [M] | air temp, humidity, wind, radiation, precip | hourly to daily | 0.11 deg (~12 km); some 3 km convection-permitting | to 2100, CMIP5 and newer CMIP6-driven |
| ISIMIP3b [M] | discharge from multiple hydrological models; some lake temperature | daily/monthly | 0.5 deg, global | to 2100, CMIP6-based |
| JRC LISFLOOD climate-impact discharge runs [M] | discharge, low-flow indicators | daily | ~5 km | to 2100 |
| Hydro-CH2018 / Michel et al. Switzerland [V] | river temperature projections (explicitly linked to nuclear cooling impacts) | daily | Swiss river network | 21st century, several scenarios, CC BY |
| van Vliet et al. global river temperature [M] | river water temp + discharge | weekly | 0.5 deg | to 2099, CMIP5-based, dated |

## Plant-side data (supporting)
- Locations/capacity: JRC Open Power Plants Database, WRI Global Power Plant Database [M]
- Actual generation and outage/derating notices (good validation signal): ENTSO-E Transparency Platform; IAEA PRIS for nuclear [M]
- Cooling type (once-through vs closed-loop, river vs sea) is patchy in open data; needs a per-plant compilation
- Legislation: no ready dataset. Permit limits (max downstream temperature, max temperature rise, minimum flow, discharge limits) are plant-specific and set by national regulators. Needs manual digitisation, starting with France, Germany, Switzerland.

## Design notes
1. EFAS (~1.4 km, calibrated, operational) for present-day/forecast; HydroLand (5 km, hourly) for forward-looking and what-if. Cross-check both against gauges at each site.
2. Permits are often assessed hourly/daily, so avoid monthly or 30-year indicator products for operational thresholds; use them only for planning-level trends.
3. Water temperature model: drive with ERA5-Land or CORDEX air temp plus EFAS/HydroLand discharge; calibrate on gauge temperature data.

## Useful URLs (seen in research)
- HydroLand use case: https://destine.ecmwf.int/use-case/global-freshwater-availability/
- HydroLand user story: https://destine.ecmwf.int/strengthening-flood-and-drought-preparedness-with-hydroland/
- EFAS historical: https://ewds.climate.copernicus.eu/datasets/efas-historical
- EFAS forecast: https://ewds.climate.copernicus.eu/datasets/efas-forecast
- EFAS reforecast: https://ewds.climate.copernicus.eu/datasets/efas-reforecast
- EFAS seasonal reforecast: https://ewds.climate.copernicus.eu/datasets/efas-seasonal-reforecast
- EFAS v5 docs: https://confluence.ecmwf.int/display/CEMS/EFAS+v5.0
- C3S hydrology projections: https://cds.climate.copernicus.eu/datasets/sis-hydrology-variables-derived-projections
- BfG Rhine water temp + NPP heat input: https://gdk.gdi-de.org/geonetwork/srv/api/records/84613bfc-118d-42fe-9c30-38b38151e888
- Swiss river temperature projections: https://envidat.ch/dataset/81b2d366-133f-4c2f-9d67-3499f93f3791 (DOI 10.16904/envidat.272)

## Open question / suggested next step
Draft a data-access plan (APIs, formats, update cadence) for the first sources to ingest. Undecided: focus on the Category 1 operational stack (EFAS + gauges + ERA5-Land) or on HydroLand/projections first.