# Data licences

Licence and commercial-use status of every dataset in the project. Checked on 2026-10-25 against the licence each provider publishes (catalogue entries, licence PDFs, file metadata, terms accepted at registration). This is a working overview, not legal advice. Check again before a commercial release.

✅ commercial use allowed · ❌ not allowed · ⚠️ not clear

## Datasets in use

| Dataset | Used for | Licence | Commercial | Conditions / notes |
| --- | --- | --- | --- | --- |
| GEM Global Nuclear Power Tracker (Aug 2026) | Plant locations, capacities | CC BY 4.0 | ✅ | Attribution: "Global Nuclear Power Tracker, Global Energy Monitor" |
| JRC Open Power Plants Database (JRC-PPDB-OPEN v1.0) | Cooling type, water type | CC BY 4.0 (Zenodo 10.5281/zenodo.3574566) | ✅ | Cite Kanellopoulos et al. (2019) |
| GloFAS forecast & reanalysis (CEMS, EWDS) | River discharge, track 1 | CEMS-FLOODS licence (Copernicus, Reg. (EU) 377/2014 & 1159/2013) | ✅ | Free reproduction, distribution and modification. Notice required: "Generated using Copernicus Emergency Management Service information [year]", or "Contains modified …" for derived data. Provided "as is", and it is not an official flood warning. Real-time EFAS data is restricted (not used here). |
| ECMWF open data (IFS HRES 2 m temperature) | Air temperature forecast | CC BY 4.0 | ✅ | Attribution to ECMWF |
| ERA5-Land daily statistics (C3S, CDS) | Air temperature, past | CC BY 4.0 | ✅ | Attribution to C3S / ECMWF |
| C3S hydrology projections (E-HYPEgrid, `sis-hydrology-variables-derived-projections`) | River discharge, scenarios | CC BY 4.0 | ✅ | Attribution to C3S |
| EURO-CORDEX ICHEC-EC-EARTH / SMHI-RCA4 (CDS) | Air temperature, scenarios | CORDEX terms of use; SMHI-RCA4 registered as **unrestricted** | ✅ | CORDEX lets each modelling group choose "unrestricted" or "non-commercial only"; SMHI-RCA4 is unrestricted in the official IS-ENES RCM list. **Other RCMs may be non-commercial: check before adding model chains.** |
| DestinE HydroLand (Data Lake, `EO.UFZ.DAT.HYDROLAND`) | River discharge, scenarios | Labelled CC BY 4.0 in the Data Lake, **but** accessed under the *DestinE Terms and Conditions for upgraded access* | ⚠️ | See "DestinE" below |
| DestinE Climate DT, IFS-NEMO 2 m temperature (Polytope) | Air temperature, scenarios | Same as HydroLand | ⚠️ | See "DestinE" below |

### Derived data (made in this project)

| Product | Built from | Commercial |
| --- | --- | --- |
| Water temperature forecast & reanalysis | GloFAS + ECMWF open data / ERA5-Land | ✅ with all their notices (CEMS "Contains modified …", ECMWF, C3S) |
| Water temperature scenarios (`historical`, `rcp_*`) | C3S E-HYPEgrid + EURO-CORDEX (SMHI-RCA4) | ✅ with C3S and CORDEX attribution |
| App tables `data/app_input/environment/` | Currently GloFAS (+ water temperature from GloFAS, ECMWF, ERA5-Land) only | ✅ with the notices above |
| HydroLand / Climate DT based outputs | DestinE data | ⚠️ |

## DestinE: why it is unclear

The Data Lake catalogue lists Climate DT and HydroLand as CC BY 4.0, which would allow commercial use. Our access, however, runs through *upgraded access*, whose Terms and Conditions (v1.0, 18 Oct 2024) say:

- **Art. 2.1:** access is granted "strictly for official use within the scope of activities of the User".
- **Art. 2.3:** users may only distribute services, tools or data "from which the original DestinE Data cannot be retrieved or reverse engineered".
- **Art. 2.5:** no reproducing, distributing, licensing, selling or forwarding of DestinE data to third parties without prior written consent of the European Commission.
- **Art. 3.4:** derived products must carry: "This service/application/tool/data is created [based on data of the European Commission] and/or [using Destination Earth Platform] (but has been modified by [User's name])."

**Consequence:** a commercial product is not explicitly ruled out, but showing HydroLand or Climate DT daily values per plant in an app would likely count as passing on retrievable DestinE data. That needs the Commission's consent. **Until DestinE confirms which licence applies, keep DestinE data out of anything shared outside the project**, or only show derived indicators from which the original values cannot be recovered. This is one reason the app tables currently contain no HydroLand data.

## Considered, not downloaded

| Dataset | Licence | Commercial | Note |
| --- | --- | --- | --- |
| Loire stream temperature (Seyedhashemi et al. 2023, doi:10.57745/LBPGFS) | CC BY-NC 4.0 | ❌ | Research use only |
| FutureStreams (Bosmans et al. 2022) | CC BY 4.0 | ✅ | |
| TempER European river temperature stations | Not published yet | ⚠️ | Ask the authors |

## Sources

- CDS / EWDS catalogue licence fields: `https://cds.climate.copernicus.eu/api/catalogue/v1/collections/<dataset>` (and the same path on `ewds.climate.copernicus.eu`)
- CEMS-FLOODS licence PDF, linked from the GloFAS dataset pages on the EWDS
- CORDEX terms of use (2 May 2013) and the RCM list: https://is-enes-data.github.io/CORDEX_RCMs_ToU.txt
- DestinE Data Lake STAC: `https://hda.data.destination-earth.eu/stac/v2/collections/EO.UFZ.DAT.HYDROLAND` and `.../EO.ECMWF.DAT.DT_CLIMATE_ADAPTATION`
- DestinE Terms and Conditions for upgraded access: https://platform.destine.eu/wp-content/uploads/2024/11/Terms-and-Conditions-for-DestinE-Users-Granted-Upgraded-Access.pdf
- ECMWF open data: licence notice shown by the `ecmwf-opendata` client (CC BY 4.0)
- Plant data: `data/raw/global_nuclear_power_tracker/readme.txt`, Zenodo record 3574566
