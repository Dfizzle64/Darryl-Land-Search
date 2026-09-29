# Currituck County, NC — GIS County Card

## Summary

Currituck County (Outer Banks / Eastern NC, FIPS **37053**, slug **currituck**, `cntyfips='053'`) is the **only NC county with no incorporated municipalities**. **Wire-first parcels (ArcGIS REST):** `GISWebsite/OperationalLayers/MapServer/20` Parcels — **~27,903** polygons with owner (`OWN1`–`OWN10`), mailing, situs (`LOC_*`), GIS/deed acres (`ACREAGE_GI`/`ACRE`), full tax split (`LAND_VAL`/`BLDG_VAL`/`TOT_VAL`/`DEFER_VAL`), and **on-layer sale** (`SALE_DATE`/`SALE_PRICE`/`SALE_QUAL`). **~2,913** with `ACREAGE_GI` 5–150 (~**1,574** BLDG_VAL 0/null in band; **~1,161** SALE_PRICE>0 in band). **Cities-first zoning/FLU:** no city zoning FS (none exist) — treat **Moyock / Corolla / Maple–Barco Small Area Plan** FLU polygons as community-first overlays on countywide **Official Zoning Base Districts** + overlays + **Imagine Currituck** LUP classes. **PA:** NCPTS `parcel-detail/{PARCEL_ID}` + viewer `?pin={PARCEL_ID}` (config variable `pin` filters **`PARCEL_ID`**) + Munis Real Estate search + ICARE/iasWorld (maintenance banner as of verify). **jurisdictionGisUrl:** https://maps.currituckcountync.gov/gis/. Markets: **[Outer Banks, Eastern NC]**.

## Portals

- **Public GIS viewer (jurisdictionGisUrl)** — https://maps.currituckcountync.gov/gis/
- **Interactive Online Mapping landing** — https://currituckcountync.gov/interactive-online-mapping/
- **GIS department** — https://currituckcountync.gov/geographic-information-services/
- **County REST root** — https://maps.currituckcountync.gov/arcgis/rest/services
- **OperationalLayers (PRIMARY)** — https://maps.currituckcountync.gov/arcgis/rest/services/GISWebsite/OperationalLayers/MapServer
- **Energov twin** — https://maps.currituckcountync.gov/arcgis/rest/services/Energov/MapServer
- **iasWorldBase2026** — https://maps.currituckcountync.gov/arcgis/rest/services/Currituck/iasWorldBase2026/MapServer
- **Tax Online Services** — https://currituckcountync.gov/tax/tax-online-services/
- **Munis Citizen Self Service (property / tax)** — https://currituck.munisselfservice.com/citizens/default.aspx
- **Munis Real Estate search** — https://currituck.munisselfservice.com/citizens/RealEstate/Default.aspx
- **ICARE / iasWorld (PA portal; maint banner)** — https://currituckncgov.com/ICARE/Main/Home.aspx
- **ICARE CommonSearch (parid)** — https://currituckncgov.com/search/CommonSearch.aspx?mode=parid
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/currituck/
- **NCPTS deep-link (parcel)** — `https://lrcpwa.ncptscloud.com/currituck/parcel-detail/{PARCEL_ID}`
- **Viewer deep-link** — `https://maps.currituckcountync.gov/gis/?pin={PARCEL_ID}`
- **Tax parcel data download (Excel CAMA)** — https://currituckcountync.gov/tax/tax-data/
- **Planning & Zoning** — https://currituckcountync.gov/planning-zoning/
- **UDO (2025 PDF)** — https://currituckcountync.gov/wp-content/uploads/UDO.pdf
- **Imagine Currituck LUP PDF** — https://currituckcountync.gov/wp-content/uploads/imagine-currituck-plan-25apr23.pdf
- **Imagine Currituck hub** — https://currituckcountync.gov/imagine-currituck/
- **Small Area Plans index** — https://currituckcountync.gov/planning-zoning/small-area-plan/
- **Moyock SAP** — https://www.currituckcountync.gov/planning-zoning/small-area-plan/moyock/
- **Corolla Village SAP** — https://www.currituckcountync.gov/planning-zoning/small-area-plan/sap-corolla-village/
- **Maple–Barco SAP** — https://www.currituckcountync.gov/planning-zoning/small-area-plan/maple-barco/
- **DEQ certified LUPs (Currituck)** — https://www.deq.nc.gov/about/divisions/coastal-management/coastal-management-land-use-planning/certified-lups/currituck-county
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels filter `cntyfips='053'`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PARCEL_ID` / `IASParcel` (PA/viewer); `PIN`/`PIN_1` (map); OneMap `parno`≈PARCEL_ID, `altparno`≈PIN | Prefer **`PARCEL_ID`** for NCPTS + `?pin=` |
| polygons | Yes | OperationalLayers/20; Energov/3; OneMap | CRS **102719 / 2264**; MaxRecordCount **2000** |
| acreage | Yes | `ACREAGE_GI`, `ACRE`; OneMap `gisacres` | **2,913** GIS 5–150 |
| ownerName | Yes | `OWN1`…`OWN10`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `MAIL_ADDR1`/`2`, `MAIL_CITY`, `MAIL_STATE`, `MAIL_ZIP` | |
| situs address | Yes | `LOC_NO`+`LOC_DIR`+`LOC_STR`+`LOC_TYP`+`LOC_UNIT*`; `LOC_CITY`/`LOC_ZIP` | |
| lastSale date/price | Yes | `SALE_DATE`, `SALE_PRICE`, `SALE_QUAL`/`QUAL_DESC`; OneMap `saledate` | **On parcel layer** — no join required |
| tax values | Yes | `TOT_VAL`, `LAND_VAL`, `BLDG_VAL`, `DEFER_VAL` | |
| zoning | Yes (countywide) | Official Zoning Base `Zone`/`Zone_Name` + overlays | No city FS — county UDO applies everywhere |
| flu | Yes (cities-first SAP + county Imagine) | Moyock/Corolla/Maple SAP FLU; Imagine LUP Classes | Community-first SAP → else Imagine Classes |
| appraiser / viewer link | Yes | NCPTS `{PARCEL_ID}`; viewer `?pin=`; Munis/ICARE | TRANCHE-3 |

### TWNSHIP_NAME parcel counts (OperationalLayers/20)

| TWNSHIP_NAME | Count | Community / SAP routing |
|-------------:|------:|-------------------------|
| POPLAR BRANCH ML | ~7,299 | Lower Currituck mainland |
| MOYOCK MAINLAND | ~5,196 | **Moyock SAP** FLU (cities-first) |
| CRAWFORD | ~5,051 | Northern mainland |
| POPLAR BRANCH BCH | ~4,412 | OBX barrier / beach |
| FRUITVILLE BEACH | ~3,404 | **Corolla SAP** FLU (cities-first) |
| OCEAN SANDS W/S | ~1,146 | Ocean Sands |
| FRUITVILLE ML | ~966 | Fruitville mainland |
| MOY GIBBS WOODS | ~338 | Gibbs Woods / Knotts Island area |
| (null) | ~91 | — |

## Layers (verified 2026-09-24)

### 1. OperationalLayers Parcels/20 — PRIMARY CAMA (ArcGIS REST)

- **Purpose:** parcels | ownership | tax | situs | sales
- **REST URL:** https://maps.currituckcountync.gov/arcgis/rest/services/GISWebsite/OperationalLayers/MapServer/20
- **Energov twin:** …/Energov/MapServer/3 (same CAMA fields)
- **iasWorldBase2026 twin:** …/Currituck/iasWorldBase2026/MapServer/0
- **Geometry:** Polygon — CRS **102719 / 2264** (NAD 1983 StatePlane North Carolina Feet)
- **Key fields → targets:**
  - `PARCEL_ID`, `IASParcel` → parcelId (PA / viewer key)
  - `PIN`, `PIN_1` → parcelIdPin / OneMap altparno
  - `ACREAGE_GI`, `ACRE` → acreage
  - `OWN1`…`OWN10` → ownerName
  - `MAIL_ADDR1`, `MAIL_CITY`, `MAIL_STATE`, `MAIL_ZIP` → mailing
  - `LOC_NO`, `LOC_DIR`, `LOC_STR`, `LOC_TYP`, `LOC_UNITNO`, `LOC_CITY`, `LOC_ZIP` → situsAddress
  - `LAND_VAL`, `BLDG_VAL`, `TOT_VAL`, `DEFER_VAL` → tax
  - `SALE_DATE`, `SALE_PRICE`, `SALE_QUAL`, `QUAL_DESC`, `BOOK`, `PAGE` → lastSale / deed
  - `TWNSHIP_NAME`, `SUBD_NAME`, `LUC` → township / subdivision / use
- **Verified:** count **27,903**; ACREAGE_GI 5–150 → **2,913**; TOT_VAL>0 → **27,803**; SALE_PRICE>0 → **16,207**; SALE_QUAL='Y' → **13,450**; band + SALE_PRICE>0 → **1,161**; band vacant (BLDG_VAL 0/null) → **1,574**
- **Geo-check:** Moyock `PARCEL_ID=000200000050000` / PIN `8002-98-0833` (252 Northwest Backwoods Rd) ≈ **-76.245, 36.546**; Fruitville Beach / Corolla `008600000030000` / PIN `9013-61-1850` ≈ **-75.882, 36.546**
- **Notes:** MaxRecordCount **2000**. PRIMARY wire-first. Auth: none. Sale price **on layer**. Viewer `?pin=` filters `PARCEL_ID` (not PIN).

### 2. NC OneMap Parcels — statewide ArcGIS REST fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='053'`
- **Key fields:** `parno`(=PARCEL_ID), `altparno`(=PIN), `ownname`, mail/site, `gisacres`, `parval`/`landval`/`improvval`, `saledate`
- **Verified:** count **27,885**; gisacres 5–150 → **2,909**; parval>0 → **27,786**; saledate present countywide
- **Join check:** parno `0086000006A0000` ↔ county PARCEL_ID; altparno `9013-60-6147` ↔ PIN
- **Notes:** Prefer county OperationalLayers for fuller CAMA + SALE_QUAL. MaxRecordCount **5000**.

### 3. Official Zoning Base Districts/30 — countywide zoning

- **REST URL:** https://maps.currituckcountync.gov/arcgis/rest/services/GISWebsite/OperationalLayers/MapServer/30
- **Energov twin:** …/Energov/MapServer/9
- **Fields:** `Zone`, `Zone_Name`, `CONDITIONAL`, `COND_CASE`, `UDO_DOC`, `Acreage`
- **Verified:** count **1,058**
- **Codes:** AG, SFM, SFO, SFR, SFI, MXR, GB, LB, LI, HI, PD-M, PD-R, + conditional C-* variants
- **Notes:** County UDO applies countywide (no munis). Spatial-join parcels → Zone.

### 4–7. Official Zoning overlays

| Layer | ID | Count | Purpose |
|-------|---:|------:|---------|
| Official Zoning: AP Overlay | 26 | 5 | Airport overlay |
| Official Zoning: RET Overlay | 27 | 2 | Retail overlay |
| Official Zoning: CDPUD Overlay | 28 | 2 | CDPUD |
| Official Zoning: PUD Overlay | 29 | 71 | PUD (`OVERLAY_ZO`/`ZONE`/`NAME`) |

### 8. Imagine Currituck Land Use Plan Land Use Classes/40 — county FLU

- **REST URL:** …/OperationalLayers/MapServer/40
- **Fields:** `Class`, `Class_Name`, `ACRES`, `LUP_DOC`
- **Verified:** count **1,139**
- **Classes:** G1 Low Density Growth; G2 Controlled Growth; G3 Mixed-Use Centers and Corridors; G4 Village Center; O1 Preserved Lands; O2 Reserved Lands
- **Supporting:** Geographic Areas/38 (**4**: Northern Mainland; Off-Road/Gibbs Woods/Knotts Island; Lower Currituck; Corolla); Subareas/39 (**11**)
- **PDF:** https://currituckcountync.gov/wp-content/uploads/imagine-currituck-plan-25apr23.pdf

### 9–11. Cities-first Small Area Plan FLU (community overlays)

| Layer | ID | Count | Fields | Codes / names |
|-------|---:|------:|--------|---------------|
| Moyock SAP Future Land Use | 42 | 19 | `FLUC`, `NAME`, `ACRES` | C CONSERVATION; F FULL SERVICE; L LIMITED SERVICE; R RURAL |
| Maple Barco SAP Future Land Use | 44 | 8 | `CATEGORY`, `NAME`, `ACRES` | C CONSERVATION; EII EMPLOYMENT; NMU MIXED USE; RR RURAL; T TRANSITIONAL |
| Corolla SAP Future Land Use | 46 | 17 | `LUC` | CIVIC_CULTURAL; CONSERVATION; MIXED USE; RESIDENTIAL |

- **Boundaries:** Moyock/41, Maple Barco/43, Corolla/45
- **Route:** TWNSHIP_NAME / community proximity → SAP FLU spatial-join first → else Imagine Classes/40; zoning always county Base/30 + overlays

### 12. Communities points/11 (routing labels)

- **18** named communities (Moyock, Corolla, Maple, Barco, Knotts Island, Coinjock, Grandy, Jarvisburg, …) — label/routing only, not zoning authority

## Municipalities / communities (first-class)

**No incorporated cities or towns.** Zoning authority is **countywide** under the UDO. **Cities-first** here means prefer **Small Area Plan FLU** polygons for Moyock / Corolla / Maple–Barco before county Imagine Classes; always keep county Official Zoning Base for district codes.

### Moyock (largest CDP — PRIMARY community)

- **FLU:** OperationalLayers/42 Moyock SAP Future Land Use — **19** (`FLUC`/`NAME`)
- **Parcels:** TWNSHIP_NAME='MOYOCK MAINLAND' — **~5,196** (+ Gibbs Woods ~338)
- **SAP page:** https://www.currituckcountync.gov/planning-zoning/small-area-plan/moyock/
- **Zoning:** county Base Districts (no town FS)

### Corolla (Outer Banks — PRIMARY beach community)

- **FLU:** OperationalLayers/46 Corolla SAP Future Land Use — **17** (`LUC`)
- **Parcels:** mostly FRUITVILLE BEACH — **~3,404** (+ Ocean Sands ~1,146)
- **SAP page:** https://www.currituckcountync.gov/planning-zoning/small-area-plan/sap-corolla-village/
- **Zoning:** county Base (SFO common on OBX) + overlays

### Maple / Barco

- **FLU:** OperationalLayers/44 Maple Barco SAP Future Land Use — **8**
- **SAP page:** https://www.currituckcountync.gov/planning-zoning/small-area-plan/maple-barco/
- **Zoning:** county Base Districts

### Other unincorporated communities (Coinjock, Grandy, Jarvisburg, Knotts Island, Point Harbor, Powells Point, Shawboro, Currituck seat, …)

- **Zoning:** county Official Zoning Base + overlays
- **FLU:** Imagine Currituck Classes/40 (+ Geographic Areas/38)

## PA / viewer deep-links (TRANCHE-3)

| Template | Key | Status |
|----------|-----|--------|
| `https://lrcpwa.ncptscloud.com/currituck/parcel-detail/{PARCEL_ID}` | PARCEL_ID | **Verified** SPA shell (200) |
| `https://maps.currituckcountync.gov/gis/?pin={PARCEL_ID}` | PARCEL_ID | **Verified** (config `pin` → `PARCEL_ID = '${value}'`) |
| https://currituck.munisselfservice.com/citizens/RealEstate/Default.aspx | — | Munis RE search (cookie/Upgrade friction) |
| https://currituckncgov.com/ICARE/Main/Home.aspx | — | iasWorld/ICARE — **maintenance** banner as of 2026-09-24 |
| https://currituckncgov.com/search/CommonSearch.aspx?mode=parid | — | ICARE parcel-id search mode |
| https://maps.currituckcountync.gov/gis/ | — | Jurisdiction GIS viewer |

## Gaps

- **No incorporated municipalities** — no city zoning FeatureServers by definition; community SAP FLU is the cities-first substitute
- **ICARE/iasWorld** public site shows maintenance banner; prefer NCPTS + Munis + GIS viewer for PA
- **Munis** Self Service may force Upgrade/cookie gate in headless clients — browser interactive OK
- **Spatialest** `property.spatialest.com/nc/currituck/` → **404** (not used)
- **courthousecomputersystems.com/curritucknc/** Cloudflare-blocked from some egress — use ICARE/Munis/NCPTS instead
- Do **not** collect emails, phones, AADT, utilities, or paid-vendor data

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- Live `returnCountOnly` + sample attribute/geometry queries against OperationalLayers/20 parcels, /30 zoning, /40 Imagine FLU, /42–46 SAP FLU, overlays, Energov twins, NC OneMap `cntyfips='053'`; SearchConfig.js / config.js `queryStringParameters` (`pin`→PARCEL_ID); NCPTS + viewer deep-link HTTP 200; geo-check Moyock + Corolla centroids


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://maps.currituckcountync.gov/arcgis/rest/services/GISWebsite/OperationalLayers/MapServer/20 polygons load (sample centroid [-76.3113, 36.5499]); `PARCEL_ID` filled on 27,892 of 27,897; `ACREAGE_GI` 5–150 ac **2,913**.
- **Attribute layer for Pass 2:** https://maps.currituckcountync.gov/arcgis/rest/services/GISWebsite/OperationalLayers/MapServer/20 · id `PARCEL_ID` · live count **27,897** · 5–150 ac **2,913** (`ACREAGE_GI >= 5 AND ACREAGE_GI <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='CURRITUCK'` gives **125** stations (36 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CURRITUCK%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Currituck'` gives **121** stations (87 with AADT_2025, 72 with AADT_2024, 121 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Currituck%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `TOT_VAL` non-zero **27,797**, `LAND_VAL` non-zero **27,796**
- **Sale history (ok):** price `SALE_PRICE` >0 **16,207**; date `SALE_DATE` non-null **27,805**
- **Owner entity:** field `OWN1`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **759** (all parcels: 5,877), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://lrcpwa.ncptscloud.com/currituck/parcel-detail/{PARCEL_ID}`. Tested `000100000020000` (https://lrcpwa.ncptscloud.com/currituck/parcel-detail/000100000020000) → HTTP **200** (text/html), content verified: False. NCPTS SPA shell (200, 496 B, client-rendered): parcel content cannot be checked server-side. Viewer alt https://maps.currituckcountync.gov/gis/?pin={PARCEL_ID}.
- **Jurisdiction GIS viewer:** https://maps.currituckcountync.gov/gis/ → HTTP **200** (Currituck County, North Carolina GIS)
- **Pass 2 gaps:** PA content not verifiable (SPA)
