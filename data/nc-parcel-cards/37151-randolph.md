# Randolph County, NC — GIS County Card

## Summary

Randolph County (Winston-Salem / Triad footprint, FIPS **37151**, slug **randolph**) publishes strong **public** ArcGIS REST at `gis.randolphcountync.gov`. Countywide **tax parcel polygons** with ownership, mailing, situs, GIS/tax acreage, and **CAMA values** live on **`PW/ParcelQuery` FeatureServer/0** (~**81,155**; ~**16,961** with `TAX_ACRES` 5–150). Prefer **`REID`** / **`PARCEL_PK`** for PA deep-links; **`PIN`** (10-digit) for statewide / OneMap joins (`parno`≈`PIN`, `altparno`≈`REID`). Thinner mirror without tax values: `PW/PW_ParcelMap` FeatureServer/**14**. **Zoning is cities-first on one county layer** — `Zoning Districts` (31) with `JURISDICTION` filter (Asheboro 559, Archdale 206, Trinity 185, Randleman 122, Liberty 79, Ramseur 60, … plus unincorporated **RANDOLPH COUNTY** 2303). **FLU-like:** Growth Management Areas (33) `GMCODE`. **No independent city ArcGIS REST** found (Asheboro / Archdale / Randleman / etc.). **Sale price is not on public REST** — use CAMA PropertySummary deep-link (HTML shows Land/Package Sale Price + date); OneMap supplies `saledate` + tax values. Markets: **Winston-Salem**.

## Portals

- **Public GIS viewer (jurisdiction GIS)** — https://gis.randolphcountync.gov/randolphjs/ (also `/randolphts/`, `/RandolphTS/`)
- **GIS landing** — https://gis.randolphcountync.gov/
- **GIS department** — https://randolphcountync.gov/255/GIS
- **GIS Data downloads (shapefiles)** — https://randolphcountync.gov/432/GIS-Data
- **County ArcGIS REST** — https://gis.randolphcountync.gov/arcgis/rest/services
- **Open Data** — https://randolphcounty-randolphctygis.opendata.arcgis.com/
- **AGOL org** — https://randolphconc.maps.arcgis.com/
- **Property Search / CAMA PWA (PA)** — https://txpwa.randolphcountync.gov/camapwa/ — deep link `PropertySummary.aspx?REID={REID}` or `?PARCELPK={PARCEL_PK}`
- **Tax Department** — https://randolphcountync.gov/238/Tax
- **Planning / Zoning (admin)** — https://randolphcountync.gov/261/Planning-Zoning
- **NC OneMap** — https://www.nconemap.gov — `services.nconemap.gov` / `services.gis.nc.gov` filter `cntyfips='151'`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `REID`, `PARCEL_PK`, `PIN`; OneMap `parno`≈PIN, `altparno`≈REID | Prefer `REID`/`PARCEL_PK` for PA; `PIN` for joins |
| polygons | Yes | ParcelQuery/0 (PRIMARY); PW_ParcelMap/14 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `TAX_ACRES`, `CALC_ACRES`; OneMap `gisacres` / `recareano` | TAX_ACRES 5–150 → **16961**; CALC → **16484**; gisacres → **16449** |
| ownerName | Yes | `ACCT_NAME`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `ACCT_ADDR`, `ACCT_ADDR2`, `ACCT_CITY`, `ACCT_STATE`, `ACCT_ZIP` | |
| situs address | Yes | `LOCADDRESS`, `LOCZIP`; ParcelAddresses `FULLADDRESS` by PIN | ~60.5k real situs; ~20.7k "No Physical Address" |
| lastSale date/price | Partial | OneMap `saledate`/`saledatetx`; CAMA HTML sale fields; `DEED_BK_PG` | **No sale price on REST** — PA deep-link has Land/Package Sale Price |
| tax values | Yes | `LAND_VALUE`, `BLDG_VALUE`, `TOT_REAL_VALUE`, `DEF_VALUE`; OneMap `parval`/`landval`/`improvval` | TOT_REAL_VALUE>0 → **79768**; DEF_VALUE>0 → **4636** |
| zoning | Yes (cities-first) | `ZONE_CODE` + `JURISDICTION` on layer 31 | Filter by JURISDICTION for city-first routing |
| flu | Yes (partial) | GMA `GMCODE` (layer 33) | Growth management policy areas — not parcel-keyed FLUM |
| appraiser / viewer link | Yes | CAMA PropertySummary + randolphjs | Templates below |

## Layers (verified)

### 1. PW/ParcelQuery — parcels + CAMA tax + owner + situs (PRIMARY)

- **Purpose:** parcels | tax | ownership | situs
- **REST URL:** https://gis.randolphcountync.gov/arcgis/rest/services/PW/ParcelQuery/FeatureServer/0
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `REID`, `PARCEL_PK`, `PIN` → parcelId*
  - `TAX_ACRES`, `CALC_ACRES` → acreage
  - `ACCT_NAME` → ownerName
  - `ACCT_ADDR*` / `ACCT_CITY` / `ACCT_STATE` / `ACCT_ZIP` → mailing
  - `LOCADDRESS`, `LOCZIP` → situs
  - `LAND_VALUE`, `BLDG_VALUE`, `TOT_REAL_VALUE`, `DEF_VALUE` → tax
  - `DEED_BK_PG`, `DOCUMENT_BOOK`/`DOCUMENT_PAGE`, `DEEDLINK` → deed / lastSale.deed*
- **Related tables:** ParcelAddresses/1 (`FULLADDRESS` by `PIN`); ParcelOwners/2 (`COMPLETE_NAME` by `PIN`)
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **81,155**; `TAX_ACRES BETWEEN 5 AND 150` → **16,961**; `TOT_REAL_VALUE>0` → **79,768**; `BLDG_VALUE>0` → **57,475**; sample centroids in Randolph (−80.07, 35.51 / −80.06, 35.53)
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. MapServer mirror same fields. No sale-price field on REST.

### 2. PW/PW_ParcelMap Parcels — geometry mirror (no tax values)

- **REST:** https://gis.randolphcountync.gov/arcgis/rest/services/PW/PW_ParcelMap/FeatureServer/14
- **Count:** **81,155** | fields include REID/PIN/owner/mailing/situs/acres/`PARCEL_PK` — **no** LAND/BLDG/TOT values
- **Status:** usable (geometry / thin attrs); prefer ParcelQuery for CAMA

### 3. Zoning Districts — cities-first via JURISDICTION (PRIMARY zoning)

- **REST:** https://gis.randolphcountync.gov/arcgis/rest/services/PW/PW_ParcelMap/FeatureServer/31
- **Count:** **3,601** | fields `ZONE_CODE`, `JURISDICTION`, `BASECODE`, `ZD_ID`, `ZONE_DIST`
- **By JURISDICTION:** RANDOLPH COUNTY 2303; ASHEBORO 559; ARCHDALE 206; TRINITY 185; RANDLEMAN 122; LIBERTY 79; RAMSEUR 60; SEAGROVE 36; FRANKLINVILLE 17; STALEY 14; THOMASVILLE 10; HIGH POINT 10
- **County top codes:** RA 653, RR 496, RM 210, HC 122, HC-CD 118, CVOE-CD 111, LI 108, …
- **Asheboro top:** B2 75, R10 53, B2 (CZ) 52, OA6 41, RA6 36, R40 30, I2 30, …
- **Status:** usable — **route by `JURISDICTION`** (no separate city FS)

### 4. Growth Management Areas — FLU-like (PRIMARY county FLU proxy)

- **REST:** …/PW_ParcelMap/FeatureServer/33
- **Count:** **77** | `GMCODE`: MUNICIPAL GROWTH AREA 34; RURAL GROWTH AREA 15; PRIMARY GROWTH AREA 13; SECONDARY GROWTH AREA 12; ZOO ENVIRONMENTAL AREA 3
- **Status:** usable (policy FLU; spatial join — not parcel-keyed place types)

### 5. Special Development Districts (overlay)

- **REST:** …/FeatureServer/32 | count **4**
- **Types:** AIRPORT OVERLAY (Approach/Buffer); SMALL AREA PLAN (Birkhead/Uwharrie; NC HWY 705)
- **Status:** partial (overlay / SAP, not base zoning)

### 6. NC OneMap Parcels — fallback (+ sale date + tax)

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='151'` | count **80,940**; `gisacres` 5–150 → **16,449**; `siteadd` present → **60,160**; `parval>0` → **79,478**
- **Notes:** `parno`≈PIN; `altparno`≈REID; `saledate` populated; **no saleprice field**. Alternate host `services.gis.nc.gov`. MaxRecordCount 5000.
- **Status:** usable (fallback / sale-date / situs fill)

### 7. Municipalities + City Limits + ETJ

- **Randolph Municipalities /42** & **City Limits /6** — CITY_CODE: 01 Asheboro, 02 Archdale, 03 Franklinville, 04 Liberty, 05 Ramseur, 06 Randleman, 07 Seagrove, 08 Staley, 09 High Point, 10 Thomasville, 11 Trinity (count **100** multipart polys)
- **Municipal ETJ /30** — count **57** (`ZONE_DIST` jurisdiction id)
- **Status:** usable

### 8. Planning/LandUseCases — case history (not FLU)

- **REST:** https://gis.randolphcountync.gov/arcgis/rest/services/Planning/LandUseCases/FeatureServer/0
- **Status:** other (rezoning/variance cases — not base FLU)

## Municipalities (city-first routing)

| Municipality | Zoning REST | FLU REST | Notes |
|--------------|-------------|----------|-------|
| Asheboro | PW_ParcelMap/31 `JURISDICTION='ASHEBORO'` (559) | County GMA/33 | County seat; no city FS |
| Archdale | /31 `='ARCHDALE'` (206) | GMA/33 | Spans Randolph tip; High Point MSA edge |
| Randleman | /31 `='RANDLEMAN'` (122) | GMA/33 | |
| Liberty | /31 `='LIBERTY'` (79) | GMA/33 | |
| Ramseur | /31 `='RAMSEUR'` (60) | GMA/33 | |
| Trinity | /31 `='TRINITY'` (185) | GMA/33 | |
| Franklinville | /31 `='FRANKLINVILLE'` (17) | GMA/33 | |
| Seagrove | /31 `='SEAGROVE'` (36) | GMA/33 | |
| Staley | /31 `='STALEY'` (14) | GMA/33 | |
| High Point (edge) | /31 `='HIGH POINT'` (10) | prefer Guilford/HP card | Randolph-side tip only |
| Thomasville (edge) | /31 `='THOMASVILLE'` (10) | prefer Davidson card | Randolph-side tip only |
| Unincorporated | /31 `='RANDOLPH COUNTY'` (2303) | GMA/33 | County base codes RA/RR/RM/HC/LI/… |

## Deep-link templates

- **Appraiser / property card (preferred):** `https://txpwa.randolphcountync.gov/camapwa/PropertySummary.aspx?REID={REID}`
- **Appraiser alt (PARCEL_PK):** `https://txpwa.randolphcountync.gov/camapwa/PropertySummary.aspx?PARCELPK={PARCEL_PK}`
- **PA search:** https://txpwa.randolphcountync.gov/camapwa/SearchProperty.aspx
- **Jurisdiction GIS viewer:** https://gis.randolphcountync.gov/randolphjs/
- **Deed image (from layer):** `DEEDLINK` field (Courthouse Computer Systems RandolphNC2)

## Gaps

- **No sale price on public ArcGIS REST** — CAMA PropertySummary HTML has Land/Package Sale Price + dates; OneMap has `saledate` only
- No independent **city** ArcGIS FeatureServers (Asheboro, Archdale, Randleman, Liberty, Ramseur, Trinity, …)
- No parcel-keyed **comprehensive-plan FLUM** — GMA growth-policy areas only; Small Area Plans are overlays
- `LOCADDRESS` = "No Physical Address" on ~20.7k — join ParcelAddresses or OneMap `siteadd`
- High Point / Thomasville zoning rows are Randolph-side tips — prefer Guilford / Davidson cards for core city
- PW_ParcelMap/14 lacks tax value fields — always prefer ParcelQuery/0 for CAMA
- MaxRecordCount 2000 — paginate; no phones/emails; no AADT/utilities; no paid vendors

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- Live REST counts, field maps, sample attributes, WGS84 centroids, JURISDICTION zoning splits, OneMap `cntyfips='151'`, and CAMA PropertySummary deep-links (`REID` / `PARCELPK`) checked.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://gis.randolphcountync.gov/arcgis/rest/services/PW/ParcelQuery/FeatureServer/0 · id `REID` · live count **81,157** · 5–150 ac **16,963** (`TAX_ACRES >= 5 AND TAX_ACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='RANDOLPH'` gives **1001** stations (513 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27RANDOLPH%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Randolph'` gives **1002** stations (635 with AADT_2025, 541 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Randolph%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Randolph'` gives **997** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `TOT_REAL_VALUE` non-zero **79,759**, `LAND_VALUE` non-zero **79,759**
- **Sale history (partial-date-only):** no sale fields on primary layer. No sale price/date on ParcelQuery. Sale date via NC OneMap saledate (cntyfips='151', join altparno=REID or parno=PIN): 59122 rows with saledate>1901. Price gap on REST → CAMA PropertySummary (public).
- **Owner entity:** fields `ACCT_NAME`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **1,529** of 16,963 (extended regex: 2,652).
- **PA deep link:** `https://txpwa.randolphcountync.gov/camapwa/PropertySummary.aspx?REID={REID}`. Tested `64499` → HTTP **200** (text/html), content verified: True. Parcel id found in the response body.
- **Jurisdiction GIS viewer:** https://gis.randolphcountync.gov/randolphjs/ → HTTP **200** (Randolph County GIS)
- **Pass 2 gaps:** Sale price not on public REST — CAMA PropertySummary only; sale date via OneMap join
