# Chatham County, NC — GIS County Card

## Summary

Chatham County (Raleigh-Durham footprint, FIPS **37037**, slug **chatham**) publishes rich cadastral + planning REST at `gisservices.chathamcountync.gov`. **Wire-first parcels:** **LandReference/Parcels** MapServer/17 (twin **Cadastral/Chatham_CamaParcels**/0) — ~**49.4k** polygons with owner, mailing, **situs**, deeded acres, land/bldg FMV+ASV, zoning attribute, tax district. ~**13,943** with `gross_current_acres` 5–150 (~**5,446** with building FMV 0/null). **Sale price** lives on **PropertySales** table (~26.7k rows; ~14.3k with price>0) — join on `parcel_Number`. **Cities-first zoning:** **Pittsboro** (23), **Siler City** (22), **Goldston** (24) on county LandUsePlanning; Cary/Apex Chatham tips; **County Zoning** (25) for unincorporated. **FLU:** Pittsboro FLU Features (37) + Siler City FLU (57) city-first; county FLU Framework is thematic group (partial). **NC OneMap** (`cntyfips='037'`) fallback. Markets: **Raleigh-Durham**.

## Portals

- **Public GIS viewer (jurisdiction homepage)** — https://gisservices.chathamcountync.gov/landinformation/
- **Legacy Tax & Land Information (WAB)** — https://chathamncgis.maps.arcgis.com/apps/webappviewer/index.html?id=f694f711114b47a5bee18d595cc22727
- **Future Land Use Experience** — https://experience.arcgis.com/experience/291c078dc958401ab4ad972c85743ff8
- **ChatView Experience** — https://experience.arcgis.com/experience/757490e2e49b4b90a128eeb8241005ae
- **GIS Open Data Hub** — https://opendata-chathamncgis.opendata.arcgis.com/
- **GIS AGOL org** — https://chathamncgis.maps.arcgis.com/home/index.html
- **County ArcGIS REST (webapps)** — https://gisservices.chathamcountync.gov/webapps/rest/services
- **County ArcGIS REST (opendataagol)** — https://gisservices.chathamcountync.gov/opendataagol/rest/services
- **PA / property search (NCPTS)** — https://lrcpwa.ncptscloud.com/chatham/parcel-search
- **PA deep-link** — `https://lrcpwa.ncptscloud.com/chatham/parcel-detail/{parcel_number}`
- **GIS Mapping Division** — https://www.chathamcountync.gov/government/departments-programs-i-z/tax-administration/gis-mapping-division
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)
- **City/town GIS:** no dedicated public hosts for Pittsboro / Siler City / Goldston — county LandUsePlanning layers are the city zoning REST

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `parcel_number`, `alternate_parcel_number` (PIN), `parcel_number_short`; OneMap `parno`/`altparno` | Prefer `parcel_number` (e.g. `0081218`) for NCPTS deep link; PIN joins OneMap `altparno` |
| polygons | Yes | LandReference MS/17 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `gross_current_acres` | ~**13,943** deeded 5–150 |
| ownerName | Yes | `current_owners` / `jan1_owners`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `address1`/`address2`/`csz` | Combined CSZ string |
| situs address | Yes | `physical_street_address` / `community_name`; AddressPoints | **On primary parcel layer** |
| lastSale date/price | Yes (join) | PropertySales `net_selling_price`/`date_of_sale`/`valid_sale_flag`; parcel has instrument/grantor/book-page only | Join table on `parcel_Number` |
| tax values | Yes | `jan1_total_FMV`, `jan1_land_FMV`, `jan1_bldg_FMV`, `jan1_total_ASV` (+ land/bldg ASV) | **Has land/improve split** on primary |
| zoning | Yes | City layers (Pittsboro/Siler/Goldston) + County Zoning/25; parcel `zoning` attr | Cities-first inside munis/ETJs |
| flu | Yes (partial) | Pittsboro/37, Siler City/57; county framework thematic group | No single countywide FLU-code coverage |
| appraiser / viewer link | Yes | NCPTS parcel-detail by `parcel_number`; Tax & Land Information viewer | Templates below |

### Tax district inventory (verified parcel counts)

| tax_district_desc | Parcels |
|-------------------|---------|
| NORTH CHATHAM FIRE DIST | 16,216 |
| CIRCLE CITY FIRE DISTRICT | 5,398 |
| HOPE FIRE DISTRICT | 3,784 |
| **PITTSBORO CITY** | **3,740** |
| CENTRAL CHATHAM FIRE DIST | 3,233 |
| **SILER CITY CITY** | **2,961** |
| BONLEE FIRE DISTRICT | 2,773 |
| **CARY CITY** | **2,516** |
| MONCURE FIRE DISTRICT | 2,432 |
| GOLDSTON FIRE DISTRICT | 1,964 |
| BENNETT FIRE DISTRICT | 1,428 |
| **GOLDSTON CITY** | **262** |
| **APEX CITY** | **23** |
| Other fire / split / null | remainder |

### Community / situs inventory (top)

| community_name | Approx parcels |
|----------------|----------------|
| (null) | 19,122 |
| Pittsboro / PITTSBORO | ~9,239 |
| Siler City / SILER CITY | ~6,453 |
| SILER CITY ETJ | 2,003 |
| PITTSBORO ETJ | 1,283 |
| Chapel Hill | ~3,683 |
| Cary / CARY | ~2,281 |
| Bear Creek / Moncure / Apex / Goldston / New Hill / Bennett / … | see REST |

### Municipal boundaries (verified)

Pittsboro, Siler City, Goldston, Cary (Chatham portion), Apex (Chatham tip).

## Layers (verified)

### 1. LandReference Parcels — parcels + ownership + tax + situs + zoning attr (PRIMARY)

- **Purpose:** parcels | tax | ownership | situs | zoning (attr)
- **REST URL (wire-first):** https://gisservices.chathamcountync.gov/webapps/rest/services/DedicatedDatasets/LandReference/MapServer/17
- **Open-data twin:** https://gisservices.chathamcountync.gov/opendataagol/rest/services/Cadastral/Chatham_CamaParcels/MapServer/0
- **Layer name / id:** Parcels / 17 (Cama Parcels / 0)
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parcel_number` → parcelId (**NCPTS key**)
  - `alternate_parcel_number` → PIN (joins OneMap `altparno`)
  - `parcel_number_short` → short id
  - `gross_current_acres` → acreage
  - `current_owners` / `jan1_owners` → ownerName
  - `address1`/`address2`/`csz` → mailing
  - `physical_street_address` / `community_name` → situs
  - `current_book`/`current_page`/`grantor_*`/`sale_instrument` → lastSale meta (no price)
  - `jan1_*_FMV` / `jan1_*_ASV` → tax market/assessed + land/improve split
  - `zoning` / `land_use` / `tax_district_desc` / `py_use_code` → zoning attr / use / district
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **49,387**; acres 5–150 → **13,943**; bldg FMV 0/null in range → **5,446**
- **Notes:** **PRIMARY**. MaxRecordCount **100000** (LandReference) / **2000** (CamaParcels twin — paginate). **MapServer only** (FeatureServer SOE missing). Geo-check `0081218` ≈ **-79.109, 35.717**. Skip utility fields.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='037'`
- **Verified:** count **48,850**; gisacres 5–150 → **13,253**; vacant-ish → **5,308**
- **Join:** `parno` = `parcel_number`; `altparno` = `alternate_parcel_number`
- **Status:** usable fallback (no sale price)

### 3. PropertySales (DEVNET Sales) — sale price/date/qualified (PRIMARY sales)

- **REST:** https://gisservices.chathamcountync.gov/opendataagol/rest/services/Cadastral/Chatham_PropertySales/MapServer/0
- **Geometry:** none (table)
- **Join:** `parcel_Number` = parcels.`parcel_number`
- **Key fields:** `net_selling_price`, `gross_selling_price`, `date_of_sale`, `sale_year`, `valid_sale_flag`, `grantor`, `grantee`, `book`, `page`
- **Verified:** count **26,656**; price>0 → **14,282**; valid_sale_flag=Y → **11,280**
- **Status:** usable

### 4–8. Zoning (cities-first)

| Priority | Layer | REST | Count | Coverage |
|----------|-------|------|-------|----------|
| 1 | Pittsboro Zoning | LandUsePlanning/MapServer/**23** | 24 | Pittsboro + ETJ |
| 2 | Siler City Zoning | LandUsePlanning/MapServer/**22** | 22 | Siler City + ETJ |
| 3 | Goldston Zoning | LandUsePlanning/MapServer/**24** | 8 | Goldston |
| 4 | Cary Zoning (Chatham tip) | MapServer/**21** | 7 | Cary edge |
| 5 | Apex Zoning (Chatham tip) | MapServer/**30** | 2 | Apex tip (partial) |
| 6 | County Zoning | MapServer/**25** | 555 | Unincorporated + stubs |

Open-data twins under `opendataagol/rest/services/LandUsePlanning/Chatham_*Zoning/MapServer/0`. Field: `ZoningClassification`.

### 9–12. FLU

| Layer | REST | Count | Notes |
|-------|------|-------|-------|
| Pittsboro Future Land Use Features | MapServer/**37** | 111 | `FLU_Class` / `FLU_Class_Type` — CITY-FIRST |
| Siler City Future Land Use Framework | MapServer/**57** | 11 | `FLU` — CITY-FIRST |
| County Future Land Use Framework | MapServer/**11** (group) | thematic leafs | partial — not single FLU-code coverage |
| Chatham-Cary Joint Land Use | MapServer/**7** (group) | Density Types/9 = 119 | Cary edge |
| Moncure FLU Framework | MapServer/**39** (group) | thematic | Plan Moncure area |

### 13. ETJ / Municipal Boundaries / Address Points / OZ note

- **ETJ** MapServer/3 — SILER CITY ETJ, PITTSBORO ETJ
- **Municipal Boundaries** LandReference/12 — 5 munis
- **Address Points** Addressing/Chatham_AddressPoints/0 — ~50.5k
- **Federal Opportunity Zones** MapServer/20 — 3 tracts (county TIGER); prefer **national OZ 2.0** tract join for product

## Link templates (Tranche-3 required)

```
PA search:     https://lrcpwa.ncptscloud.com/chatham/parcel-search
PA deep-link:  https://lrcpwa.ncptscloud.com/chatham/parcel-detail/{parcel_number}
GIS portal:    https://gisservices.chathamcountync.gov/landinformation/
FLU viewer:    https://experience.arcgis.com/experience/291c078dc958401ab4ad972c85743ff8
```

Example: parcel `0081218` → https://lrcpwa.ncptscloud.com/chatham/parcel-detail/0081218

## Cities-first ingest rule

Inside **Pittsboro / Pittsboro ETJ** prefer Pittsboro Zoning + Pittsboro FLU Features; inside **Siler City / Siler City ETJ** prefer Siler City Zoning + Siler City FLU; inside **Goldston** prefer Goldston Zoning; Cary/Apex Chatham tips use county tip layers but defer core to Wake cards; elsewhere County Zoning + parcel `zoning` attr + county FLU thematic leafs.

## Gaps

- Sale price requires PropertySales table join (not on parcel polygons)
- Zoning district layers are merged (few polys) vs dense parcel zoning attribute
- County FLU Framework is thematic group, not countywide FLU-code polygons
- No city-hosted GIS for Pittsboro/Siler City/Goldston
- Apex tip zoning partial (2 polys); Cary/Apex cores → Wake cards
- MapServer only (no FeatureServer SOE)
- Comper commercial tool excluded; no utilities/AADT/phones/emails/paid vendors

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **CRS checks:** county REST WKID 102719/2264; sample WGS84 centroids in Chatham
- **OneMap:** `cntyfips='037'` count 48850; PIN/parcel_number join verified


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://gisservices.chathamcountync.gov/webapps/rest/services/DedicatedDatasets/LandReference/MapServer/17 · id `parcel_number` · live count **49,387** · 5–150 ac **13,943** (`gross_current_acres >= 5 AND gross_current_acres <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='CHATHAM'` gives **422** stations (236 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CHATHAM%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Chatham'` gives **426** stations (247 with AADT_2025, 254 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Chatham%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Chatham'` gives **421** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `jan1_total_FMV` non-zero **48,662**, `jan1_total_ASV` non-zero **46,618**
- **Sale history (ok-separate-table):** no sale fields on primary layer. Parcels carry only deed/grantor; price+date on Cadastral/Chatham_PropertySales MapServer/0 (join parcel_Number=parcel_number; multi-transfer history).
- **Owner entity:** fields `current_owners`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **2,234** of 13,943 (extended regex: 3,242).
- **PA deep link:** `https://lrcpwa.ncptscloud.com/chatham/parcel-detail/{parcel_number}`. Tested `0010604` → HTTP **200** (text/html), content verified: False. NCPTS PWA returns HTTP 200 SPA shell for any path; parcel resolves client-side. Headless Chrome render from box showed app-level '404 Page Not Found' even for /{tenant}/parcel-search, so resolution is UNVERIFIED (may be headless/network gating). Manual browser check recommended.
- **Jurisdiction GIS viewer:** https://gisservices.chathamcountync.gov/landinformation/ → HTTP **200** (Chatham County Tax & Land Information)
- **Pass 2 gaps:** Sale price in separate PropertySales table (join); PA link is NCPTS SPA only — parcel resolution unverified
