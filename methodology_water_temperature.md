# Methodology: River and lake water temperature

This document explains how we get the water temperature upstream of each freshwater-cooled plant (\(T_{\mathrm{river}}\) in [methodology_cooling_constrain.md](methodology_cooling_constrain.md)). Europe has no ready-made dataset of daily river temperature at plant scale for forecasts or projections, so we **derive it from air temperature and river discharge**. We calibrate and validate it against observed water temperature.

Planned output: daily mean water temperature (°C) at each plant location
(`Location_ID` in `data/app_input/facilities.csv`) for
- **Track 1:** the next ~10 days (forecast), plus past periods to check how good the forecast is.
- **Track 2:** historical and future periods under several climate scenarios.

## 1. Rivers: air2stream model

We use **air2stream** (Toffolon & Piccolroaz, 2015). It is a small model, physically based but calibrated on data, that is widely used for this purpose. Water temperature follows air temperature with a delay, and the delay is shorter at low flow, when a shallow river warms faster:

\[
\frac{dT_w}{dt} = \frac{1}{\delta}\Big[a_1 + a_2 T_a - a_3 T_w + \theta\big(a_5 + a_6\cos\big(2\pi(\tfrac{t}{t_y} - a_7)\big) - a_8 T_w\big)\Big],
\qquad \theta = \frac{Q}{\bar Q},\quad \delta = \theta^{a_4}
\]

| Symbol | Meaning |
| --- | --- |
| \(T_w\) | River water temperature (°C), the model output |
| \(T_a\) | Daily mean air temperature (°C) at the plant |
| \(Q\), \(\bar Q\) | Daily river discharge and its long-term mean (m³/s) |
| \(t/t_y\) | Day of year as a fraction of the year |
| \(a_1 \dots a_8\) | Parameters calibrated for each location |

- **Current version (uncalibrated):** until observations are used, `data_processing/environment/water_temperature.py` runs a 4-parameter form (\(a_5 \dots a_8 = 0\)) with placeholder parameters: equilibrium \(T_w = 5 + 0.75\,T_a\) and a 3-day response at mean flow. All outputs are labelled `calibrated = false`.
- **Calibration:** at each observation station, fit \(a_1 \dots a_8\) to the observed \(T_w\), using the same \(T_a\) and \(Q\) sources as in operation, so that their biases are absorbed into the parameters.
- **Plants without a nearby station:** reuse the parameters of the most similar calibrated station (same river, or similar catchment size and climate). If no such station exists, use a simpler fallback: a logistic fit of \(T_w\) against 7-day mean air temperature (Mohseni et al., 1998).

## 2. Lakes and reservoirs

**Current assumption: every freshwater plant is treated as river-cooled.** The JRC field `water_type` only says "Freshwater". A manual check of the 35 freshwater plants in `data/app_input/facilities.csv` (2026-10-24) found:
- **28** take water directly from a river.
- **3** take it from a reservoir on a river: Dukovany, Temelín and Bohunice.
- **4** use a cooling pond or lake: Almaraz, Khmelnytskyi, South Ukraine and Zaporizhzhia.

So the river method covers most plants. The 7 non-river plants are flagged for later, once the intake and outlet locations are known. For the 4 pond/lake plants, the river method is likely to be least accurate.

For plants cooled by a lake or reservoir (later):
- **Past and present:** ERA5-Land lake mix-layer temperature (`lake_mix_layer_temperature`, simulated by the FLake lake model). Check it against satellite lake surface temperature (C3S LSWT).
- **Forecast and projections:** **air2water** (Piccolroaz et al., 2013), the lake version of air2stream driven by air temperature only. Calibrate it on the satellite lake temperatures.

To switch a plant to this method, record the **intake depth** as well as the water body type (see below).

### Vertical structure: surface vs. deeper water

| Water body | What the method gives | When that is not enough |
| --- | --- | --- |
| River | One depth-averaged temperature. Turbulence mixes flowing rivers top to bottom, so surface and bottom differ by only a few tenths of a degree. Stations measure in the flow, as plant intakes draw from it. | **Impounded reaches** behind dams or weirs (layers can form in summer, e.g. Rhône, Rhine, Aare). **Estuaries** (salt water under fresh water, e.g. Doel). **The outfall plume**: warm water floats on top until it mixes. Permits regulate this zone, but it is outside this method. |
| Lake / reservoir | air2water: upper mixed layer only. Satellite LSWT: the skin, top millimetres. ERA5-Land FLake: two layers, `lake_mix_layer_temperature` (upper), `lake_bottom_temperature`, plus `lake_total_layer_temperature` (column mean). | **Deep intakes in stratified lakes or reservoirs**: a surface model **overestimates** the intake temperature in summer. Use `lake_bottom_temperature` (or a mix of upper and bottom layers matching the intake depth) instead. |

## 3. Input data per track

| Track | Air temperature \(T_a\) | Discharge \(Q\) |
| --- | --- | --- |
| 1 Forecast | ECMWF open data HRES/ENS | GloFAS forecast |
| 1 Past (verification) | ERA5-Land daily mean | GloFAS reanalysis |
| 2 Projections (main) | Climate DT IFS-NEMO, SSP3-7.0 | HydroLand (same simulation) |
| 2 Projections (scenarios) | EURO-CORDEX EC-EARTH/RCA4, RCP2.6/4.5/8.5 | C3S E-HYPEgrid (same model chain) |

Download scripts: `data_processing/air_temperature/` and
`data_processing/river_discharge/`.

## 4. Water temperature data for calibration and validation

| Source | Coverage | Use | Status |
| --- | --- | --- | --- |
| Hub'Eau temperature API (France) | 872 stations, hourly, incl. the Loire, Rhône, Meuse and Moselle | Calibration and validation | Checked: open, no login. The main-river stations checked end ≤ 2015 |
| FOEN / BAFU hydrological data (Switzerland) | Aare and Rhine at the Swiss plants | Calibration and validation | Not checked yet |
| BfG and German state agencies | Rhine and other rivers | Calibration and validation | Not checked yet |
| TempER (European rivers) | >4,000 stations, 26 countries, daily | Calibration and validation | Not published yet; ask the authors |
| C3S satellite lake surface temperature | Lakes, 1995 to present | Lakes | Checked: available on CDS |
| FutureStreams (Bosmans et al., 2022) | Global, weekly, ~10 km, 1976–2099, RCP2.6–8.5 | Independent check of projected change | Checked: CC BY 4.0, download by hand |
| C3S E-HYPE `water_temperature_in_local_streams` | Europe, 30-year monthly means, RCPs | Independent check of projected change | Checked: available on CDS |
| Loire stream temperature (Seyedhashemi et al., 2023) | Loire basin, daily, 1963–2100 | Independent check for the Loire plants | Checked: **CC BY-NC**, research use only |

## 5. Validation

1. **Model skill.** Split each observed record into a calibration period and a separate validation period, for example odd and even years. Report the following per station:
   - RMSE, bias and NSE (Nash–Sutcliffe efficiency) of daily \(T_w\). NSE is the standard skill score in hydrology: it compares the model's errors with the natural variation in the observations (1 = perfect, 0 = no better than the long-term mean).
   - **Error on hot days** (\(T_w > 20\) °C), because that is where the cooling limit matters.
   - **Hit rate and false alarms for permit exceedances** (\(T_w \ge T_{\mathrm{limit}}\)).
   - Target from the literature: RMSE ≈ 1–1.5 °C for daily air2stream.
2. **Forecast skill (track 1).** Run the model on past forecasts and compare with the observed \(T_w\) for each lead time (day 1 … 10). Compare against a **persistence baseline** ("tomorrow is like today"). The forecast is only useful where it beats that baseline.
3. **Projections (track 2).** Compare the historical runs with observations, and correct a constant bias if one is found. Report **changes against the model's own historical period**, not absolute values. Cross-check the projected change against FutureStreams and the C3S indicators.
4. **Real-world check.** Compare days with predicted cooling constraints against reported nuclear curtailments (ENTSO-E Transparency Platform). The test years are 2003, 2018, 2019 and 2022.

## 6. Known limitations

- **Upstream plants and dams:** heat from upstream plants and releases from dams aren't in the model. Examples are the chain of plants along the Rhône, and lake outflows on the Aare/Rhine. Calibrating on observations downstream of these partly captures them.
- **Snow and glacier melt rivers** (Alps): the cooling effect is captured only through discharge.
- **Grid-cell discharge** may not represent the exact river reach at the plant (see `app/README.md` on how the cell is chosen).
- **Climate DT/HydroLand** is one model run and one scenario. Use CORDEX/C3S for scenario spread.

## References

- Toffolon, M. & Piccolroaz, S. (2015). A hybrid model for river water temperature as a function of air temperature and discharge. *Environ. Res. Lett.* 10, 114011. https://doi.org/10.1088/1748-9326/10/11/114011
- Piccolroaz, S., Toffolon, M. & Majone, B. (2013). A simple lumped model to convert air temperature into surface water temperature in lakes. *HESS* 17, 3323–3338. https://doi.org/10.5194/hess-17-3323-2013
- Mohseni, O., Stefan, H. G. & Erickson, T. R. (1998). A nonlinear regression model for weekly stream temperatures. *Water Resour. Res.* 34(10), 2685–2692. https://doi.org/10.1029/98WR01877
- Bosmans, J. et al. (2022). FutureStreams, a global dataset of future streamflow and water temperature. *Sci. Data* 9, 307. https://doi.org/10.1038/s41597-022-01410-6
- Seyedhashemi, H. et al. (2023). Past and future discharge and stream temperature at high spatial resolution in a large European basin (Loire basin, France). *ESSD* 15, 2827–2839. https://doi.org/10.5194/essd-15-2827-2023
