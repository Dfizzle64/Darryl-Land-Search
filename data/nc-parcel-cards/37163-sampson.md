# Sampson County, NC — GIS County Card

## Summary

Sampson County (Raleigh–Durham footprint, FIPS **37163**, slug **sampson**) publishes public cadastral + planning REST on AGOL org **SampsonCountyGIS** (`services3.arcgis.com/fM4kjZmPOS4ay2Ff`). **Wire-first parcels:** **Parcels** FeatureServer/0 — **50,665** polygons with owner, mailing parts, situs (`PARCEL_ADD`), calc/deed acreage, assessed/total tax values, last sale price/date, deed refs, and building CAMA stubs. **~14,195** with `CALC_ACRES` 5–150 (**~11,515** living area 0/null; **~5,004** `SALE_PRICE`>0). **Cities-first:** **City of Clinton Zoning** FS/1 (**62**) is the only detailed municipal zoning REST; county **Zoning** FS/0 (**412**) covers unincorporated codes (C/MRD/R/I/RA/…) plus coarse Municipal ETJ/town stubs. **FLU:** county **Future Land Use** FS/1 (**697**). **NC OneMap** (`cntyfips='163'`) fallback (**50,538**). **PA:** Tyler iasWorld/PropertyTax at sampsonlandrecords.com `{PIN}` + NCPTS. Markets: **[Raleigh-Durham]**.

## Portals

- **Public GIS viewer (Experience Builder)** — https://experience.arcgis.com/experience/6ceb46567480458387fcd2e9ad156d3b
- **GIS Hub** — https://gis-sampsoncounty.hub.arcgis.com
- **AGOL org** — https://sampson.maps.arcgis.com
- **County GIS / property records landing** — https://www.sampsoncountync.gov/My-Property/GIS-Maps-Property-Records (Akamai often **403** to bots — use Hub/Experience)
- **GIS Data Viewer (county page)** — https://www.sampsoncountync.gov/My-Property/GIS-Maps-Property-Records/GIS-Data-Viewer
- **PA / property assessment (Tyler iasWorld PT)** — https://sampsonlandrecords.com/
- **PA search (parcel ID)** — https://sampsonlandrecords.com/PT/Search/commonsearch.aspx?mode=parid
- **PA deep-link** — `https://sampsonlandrecords.com/PT/Datalets/Datalet.aspx?mode=profileall&UseSearch=no&pin={PIN}&jur=000&ownseq=0&card=1&roll=REAL`
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/sampson/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/sampson/parcel-detail/{PIN}`
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)
- **City/town GIS:** no dedicated public ArcGIS host for Clinton or other towns — county AGOL **City_of_Clinton_Zoning** is first-class Clinton zoning

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `GEO_PIN`, `GIS_APN`, `APN`, `UNIQUE_ID`; OneMap `parno` | Prefer **PIN** (11-digit); OneMap `parno`↔`PIN` verified |
| polygons | Yes | Parcels FS/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALC_ACRES`, `ACREAGE` | **~14,195** CALC 5–150 |
| ownerName | Yes | `CURRENT_OW`; OneMap `ownname` | **~49,889** non-blank; ~776 blank |
| mailing address | Yes | `CURRENT_AD` / `CURRENT_CI` / `CURRENT_ST` / `CURRENT_ZI` | Structured |
| situs address | Yes | `PARCEL_ADD` (**~49,501**); Address_Points | OneMap `scity` blank |
| lastSale date/price | Yes (last) | `SALE_PRICE`, `DATE_RECOR`, `BK_PG` / `DEED` / `MB_PG` | Sale_Price>0 in **~5,004** of 5–150; no multi-transfer REST |
| tax values | Yes | `ASSESSED_V`, `TOTAL_TAX_`, `LAND_TAX_D`, `APPRAISED` | APPRAISED often pipe-delimited segment string — prefer ASSESSED_V/TOTAL_TAX_ |
| zoning | Yes | City Clinton `LABEL_2` / `LABEL` / `ZONING_LBL`; county `CLASS` / `ZONING_CLASS` / `ZONING_TYPE` | Cities-first: Clinton FS inside city; county FS outside |
| flu | Yes | Future_Land_Use `Label` | 697 countywide polys; no city FLU FS |
| appraiser / viewer link | Yes | Tyler Datalet `{PIN}`; NCPTS parcel-detail; Experience viewer | Templates below |

### Zoning inventory (verified)

| Layer | Count | ZONING_TYPE / scope | Notes |
|-------|-------|---------------------|-------|
| City of Clinton Zoning (FS/1) | **62** | City | **PRIMARY city-first** |
| County Zoning (FS/0) County | **395** | County | C, MRD, R, I, RA, … |
| County Zoning (FS/0) Municipal stubs | **17** | Municipal | ETJ envelopes + Autryville polys — **not** full town zoning |
| Clinton_Data/0 | **62** | City | Mirror of City_of_Clinton_Zoning |
| Zoning_Overlays/1 | **43** | Overlay | Airport Height, MHB-O, etc. |

### Clinton LABEL_2 (top)

| LABEL_2 | LABEL | Count |
|---------|-------|-------|
| RA-20 | RA-20 Residential Agriculture | 13 |
| OI | Office Institutional | 12 |
| R-8 | R-8 Residential | 11 |
| NS | Neighborhood Shopping | 5 |
| HC | Highway Commercial | 5 |
| I-1 / R-15 / R-6 | Light Industrial / Residential | 3 each |
| CB / PC | Central Business / Public Conservation | 2 each |
| PID / PRD / I-2 | Planned / Heavy Industrial | 1 each |

### County Zoning CLASS (County TYPE)

| CLASS | Count |
|-------|-------|
| C | 171 |
| MRD | 74 |
| R | 60 |
| I | 55 |
| RA | 23 |
| CONDITIONAL COMMERCIAL | 4 |
| I-1 | 3 |
| AUTRYVILLE (County) | 4 |
| I-40 ROW | 1 |

### Municipal stub CLASS (on county Zoning)

CLINTON ETJ, ROSEBORO ETJ, GARLAND ETJ, SALEMBURG ETJ, NEWTON GROVE ETJ, TURKEY ETJ, FAISON ETJ, HARRELLS, AUTRYVILLE (Municipal polys), plus one Municipal RA tied to Faison.

### Future Land Use Label

| Label | Count |
|-------|-------|
| Rural Residential Agricultural | 514 |
| Residential Growth | 87 |
| Conservation | 60 |
| Industrial Growth Corridor | 18 |
| Commercial Industrial Growth Node | 18 |

### Municipal Limits inventory

Newton Grove, Roseboro, Falcon (mostly Cumberland), Garland, **Clinton**, Salemburg, Autryville, Turkey, Harrells. Address_Points `Inc_Muni` top: Unincorporated ~27,307; CLINTON ~4,678; ROSEBORO ~792; GARLAND ~509; SALEMBURG ~390; NEWTON GROVE ~361; AUTRYVILLE ~196; TURKEY ~167; HARRELLS ~135.

## Layers (verified)

### 1. Parcels — parcels + ownership + tax + situs + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | situs
- **REST URL (wire-first):** https://services3.arcgis.com/fM4kjZmPOS4ay2Ff/arcgis/rest/services/Parcels/FeatureServer/0
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (joins OneMap `parno`)
  - `GEO_PIN`, `GIS_APN`, `APN`, `UNIQUE_ID` → alternate ids
  - `CALC_ACRES`, `ACREAGE` → acreage
  - `CURRENT_OW` → ownerName
  - `CURRENT_AD` / `CURRENT_CI` / `CURRENT_ST` / `CURRENT_ZI` → mailing
  - `PARCEL_ADD` → situs
  - `SALE_PRICE`, `DATE_RECOR`, `BK_PG`, `DEED`, `MB_PG` → lastSale
  - `ASSESSED_V`, `TOTAL_TAX_`, `LAND_TAX_D`, `APPRAISED` → tax
  - `PARCEL_CLA`, `USE_DESC`, `TAX_CODE`, `TWP_CODE` → class / fire-tax / township
  - `LIVING_ARE`, `YEAR_BUILT`, building attrs → improvement proxies
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **50,665**; CALC 5–150 → **~14,195**; LIVING_ARE 0/null in range → **~11,515**; SALE_PRICE>0 in range → **~5,004**; ASSESSED_V>0 → **~49,885**; CURRENT_OW non-blank → **~49,889**
- **Notes:** **PRIMARY** wire-first. Field names are 10-char truncations (shapefile-era). `APPRAISED` often multi-segment text — use `ASSESSED_V`/`TOTAL_TAX_` for numeric totals. `TAX_CODE` looks like fire/tax district codes (F06, F19, …), not city names. MaxRecordCount **2000** — paginate. Geo-check PIN `14020913106` centroid ≈ **-78.54475, 35.31163** (Plain View / Sampson).

### 2. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Key fields:** `parno`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`/`scity`, `gisacres`, `saledate`, `parval`/`landval`/`improvval`, `cntyfips`=`163`
- **Verified:** yes — filter count **50,538**; gisacres 5–150 → **~14,177**; improvval=0/null in range → **~14,177** (improvval sparsely populated for this county extract)
- **Notes:** Fallback when AGOL flaky. No sale price. `scity` blank for Sampson. MaxRecordCount **5000**. PIN↔parno verified (`14020913106`).

### 3. City of Clinton Zoning — city zoning (PRIMARY city-first)

- **Purpose:** zoning
- **REST URL:** https://services3.arcgis.com/fM4kjZmPOS4ay2Ff/arcgis/rest/services/City_of_Clinton_Zoning/FeatureServer/1
- **Fields:** `ZONING_LBL`, `LABEL`, `LABEL_2`
- **WKID / CRS:** 102719 / 2264
- **Join to parcels:** spatial join (intersect/centroid) in 2264; gate with Municipal_Limits `CITY='Clinton'` or Address_Points `Inc_Muni='CLINTON'`
- **Verified:** yes — **62**
- **Notes:** No separate Clinton city GIS REST host — this county AGOL layer **is** the public city zoning. Mirror: `Clinton_Data/FeatureServer/0`.

### 4. Zoning — county / unincorporated (+ municipal stubs)

- **REST URL:** https://services3.arcgis.com/fM4kjZmPOS4ay2Ff/arcgis/rest/services/Zoning/FeatureServer/0
- **Fields:** `CLASS`, `ZONING_CLASS`, `ZONING_TYPE`, `Acres`, `ZONING_`, `ZONING_ID`
- **Verified:** count **412** (County **395** + Municipal **17**)
- **Notes:** Use `ZONING_TYPE='County'` outside Clinton limits. Municipal rows are mostly **ETJ envelopes** (and Autryville) — **not** substitute for missing town zoning maps.

### 5. Zoning Overlays

- **REST URL:** https://services3.arcgis.com/fM4kjZmPOS4ay2Ff/arcgis/rest/services/Zoning_Overlays/FeatureServer/1
- **Verified:** count **43** (Airport Height Restrictions, MHB-O, …)
- **Notes:** Optional overlay stack; not base zoning.

### 6. Future Land Use — county FLU (PRIMARY)

- **Purpose:** flu
- **REST URL:** https://services3.arcgis.com/fM4kjZmPOS4ay2Ff/arcgis/rest/services/Future_Land_Use/FeatureServer/1
- **Fields:** `Label`
- **Verified:** count **697**
- **Join:** spatial join in 2264
- **Notes:** County Land Use Plan 2022 polygons. Covers city + county — **no municipal FLU FeatureServer**.

### 7. Municipal Limits

- **REST URL:** https://services3.arcgis.com/fM4kjZmPOS4ay2Ff/arcgis/rest/services/Municipal_Limits/FeatureServer/0
- **Fields:** `CITY`, `FIPS`, `Descriptio`
- **Verified:** **11** polys (Clinton×2, Salemburg×2, plus Newton Grove, Roseboro, Falcon, Garland, Autryville, Turkey, Harrells)
- **Notes:** Router for cities-first zoning.

### 8. Address Points (optional situs assist)

- **REST URL:** https://services3.arcgis.com/fM4kjZmPOS4ay2Ff/arcgis/rest/services/Address_Points/FeatureServer/0
- **Fields:** `ADDRESS`, `COMMUNITY`, `Inc_Muni`, `Post_Code`, … — **no PIN**
- **Verified:** count **~34,539**
- **Notes:** Spatial join only (no PIN key). Prefer parcel `PARCEL_ADD` first.

### 9. Deferred Tax Parcels (optional)

- **REST URL:** https://services3.arcgis.com/fM4kjZmPOS4ay2Ff/arcgis/rest/services/Deferred_Tax_Parcels/FeatureServer/1
- **Verified:** count **~99,934** (soil/use-value segments; many per PIN)
- **Notes:** Present-use value / deferred segments — not primary CAMA; do not use as parcel geometry source.

## Cities / towns first-class routing

| Muni | Prefer for zoning | Prefer for FLU | Parcel host |
|------|-------------------|----------------|-------------|
| **Clinton** | City_of_Clinton_Zoning FS/1 (62) | County Future_Land_Use | Parcels FS/0 |
| Autryville | County Zoning Municipal/Autryville stubs (coarse) | County FLU | Parcels FS/0 |
| Roseboro, Garland, Salemburg, Newton Grove, Turkey, Harrells | **Gap** — only ETJ envelope stubs on county Zoning; no detailed town zoning REST | County FLU | Parcels FS/0 |
| Falcon | Mostly Cumberland — use Cumberland card inside Falcon proper | — | — |
| Faison ETJ (Duplin spill) | County Zoning FAISON ETJ stub only | County FLU | Parcels FS/0 |
| Unincorporated | Zoning FS/0 `ZONING_TYPE='County'` | County FLU | Parcels FS/0 |

No dedicated public ArcGIS hosts for Clinton or other Sampson towns — **county AGOL City_of_Clinton_Zoning is first-class for Clinton**. Unofficial third-party Garland zoning web layer exists on a personal AGOL account — **do not treat as authoritative**.

## Gaps

- **Detailed zoning REST only for Clinton** — Roseboro, Garland, Salemburg, Newton Grove, Turkey, Harrells lack public district FeatureServers (ETJ stubs only); Autryville has coarse Municipal polys.
- **No municipal FLU FeatureServer** — county Future_Land_Use only.
- **Field names truncated** (10-char) — document aliases carefully (`CURRENT_OW`, `ASSESSED_V`, `PARCEL_ADD`, …).
- **`APPRAISED` non-atomic** — pipe-delimited segment strings; prefer `ASSESSED_V` / `TOTAL_TAX_`.
- **`TAX_CODE` ≠ municipality** — fire/tax district codes; use Municipal_Limits / Address `Inc_Muni` for city routing.
- **~776 blank CURRENT_OW** — prefer PIN; fallback OneMap ownname.
- **No multi-transfer sales history REST** — last sale on parcel only; no sale-qualification code on layer.
- **OneMap `scity` blank** + `improvval` sparse for Sampson extract — use county `PARCEL_ADD` / `LIVING_ARE`.
- **sampsoncountync.gov often 403** to automated fetchers — prefer Hub / Experience / AGOL REST.
- **sampsonlandrecords.com** intermittently shows maintenance banner; Datalet may render “No Data” header while profile body still loads — retry.
- **Address_Points lack PIN** — spatial join only.
- **Owner phones/emails** not collected (do not scrape PA PII beyond public REST fields).
- **MaxRecordCount 2000** on AGOL layers — paginate.
- **No paid vendor data** used; **no AADT / utilities dig** in this card.

## Hand-off notes for Land Search Builder

1. **Wire first:** `Parcels/FeatureServer/0` — polygons + owner, mailing, **situs**, acreage, assessed/total tax, last sale. Filter `CALC_ACRES BETWEEN 5 AND 150` (~14.2k). Optional vacant-ish: `LIVING_ARE = 0 OR IS NULL` (~11.5k in range).
2. **Zoning (cities-first):** inside Clinton → City_of_Clinton_Zoning FS/1; unincorporated → Zoning FS/0 `ZONING_TYPE='County'`; other towns → **gap** (ETJ stubs only).
3. **FLU:** spatial join Future_Land_Use (`Label`); expect plan-grain regions.
4. **Sales:** use `SALE_PRICE` / `DATE_RECOR` / `BK_PG` / `DEED` on parcel.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='163'` (PIN↔parno).
6. **Viewer / appraiser links:**
   - Tyler Datalet: `https://sampsonlandrecords.com/PT/Datalets/Datalet.aspx?mode=profileall&UseSearch=no&pin={PIN}&jur=000&ownseq=0&card=1&roll=REAL`
   - Tyler search: https://sampsonlandrecords.com/PT/Search/commonsearch.aspx?mode=parid
   - NCPTS detail: `https://lrcpwa.ncptscloud.com/sampson/parcel-detail/{PIN}`
   - NCPTS search: https://lrcpwa.ncptscloud.com/sampson/parcel-search
   - GIS Viewer: https://experience.arcgis.com/experience/6ceb46567480458387fcd2e9ad156d3b
   - Hub: https://gis-sampsoncounty.hub.arcgis.com
7. **Join keys:** `PIN` (preferred), `GEO_PIN`, `GIS_APN`, OneMap `parno`↔`PIN`.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities/towns are first-class:** Clinton = City_of_Clinton_Zoning/1; other munis lack detailed zoning REST.

verifiedAt: **2026-09-24** · verifiedBy: **North Carolina Public Info Researcher**


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services3.arcgis.com/fM4kjZmPOS4ay2Ff/arcgis/rest/services/Parcels/FeatureServer/0 · id `PIN` · live count **50,665** · 5–150 ac **14,195** (`CALC_ACRES >= 5 AND CALC_ACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='SAMPSON'` gives **669** stations (250 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27SAMPSON%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Sampson'` gives **677** stations (423 with AADT_2025, 385 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Sampson%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Sampson'` gives **670** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `ASSESSED_V` non-zero **49,885**, `TOTAL_TAX_` non-zero **48,212**
- **Sale history (ok):** price `SALE_PRICE` >0 **21,542**; date `DATE_RECOR` non-null **47,206**
- **Owner entity:** fields `CURRENT_OW`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **2,501** of 14,195 (extended regex: 2,784).
- **PA deep link:** `https://sampsonlandrecords.com/PT/Datalets/Datalet.aspx?mode=profileall&UseSearch=no&pin={PIN}&jur=000&ownseq=0&card=1&roll=REAL`. Tested `08069212009` → HTTP **200** (text/html), content verified: True. Prefer iasWorld datalet (200, parcel resolved). NCPTS parcel-detail/{PIN} returns 200 SPA shell only; headless render shows app-level 404 (even for tenant search page) — unverified.
- **Jurisdiction GIS viewer:** https://experience.arcgis.com/experience/6ceb46567480458387fcd2e9ad156d3b → HTTP **200** (Experience)
- **Pass 2 gaps:** none
