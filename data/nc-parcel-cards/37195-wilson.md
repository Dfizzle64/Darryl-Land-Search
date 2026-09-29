# Wilson County, NC — GIS County Card

## Summary

Wilson County (Raleigh–Durham footprint, FIPS **37195**, slug **wilson**) publishes rich cadastral REST on **gis.wilson-co.com** with a City of Wilson mirror on **gis.wilsonnc.org**. **Wire-first parcels:** **Tax/Taxparcels** FeatureServer/0 — **43,549** polygons with owner, mailing, situs, CACRES, FMV/ASV land+improve split, last sale + qualify code, PIN/ParcelNumber/OwnerID. **~6,144** with CACRES 5–150 (**~3,213** improve value 0/null; **~1,798** SalesAmount>0). **Zoning is cities-first:** City of Wilson Zoning FS/1 (**984**), town layers on the county Planning Application (Lucama, Black Creek, Stantonsburg, Sims, Saratoga, Sharpsburg), then County Zoning (**12,528**) for unincorporated. **FLU:** City FutureLandUse_2043 (**93**, `CGF_CA`) city-first; county FLU Plan 2045 is only **6** coarse growth-area polygons. **PA deep-link:** DevNet wEdge `https://wilsonnc.devnetwedge.com/parcel/view/{OwnerID}`. Markets: **Raleigh-Durham**.

## Portals

- **Public GIS viewer (jurisdiction homepage)** — https://gis.wilson-co.com/maps
- **GIS department** — https://www.wilsoncountync.gov/departments/technology-services/gis-services
- **County ArcGIS REST** — https://gis.wilson-co.com/arcgis/rest/services
- **City of Wilson Community Maps** — https://gis.wilsonnc.org/communitymaps/
- **City ArcGIS REST** — https://gis.wilsonnc.org/services/rest/services
- **PA / property search (DevNet wEdge)** — https://wilsonnc.devnetwedge.com/
- **PA deep-link** — `https://wilsonnc.devnetwedge.com/parcel/view/{OwnerID}` (OwnerID = ParcelNumber with `.` removed; e.g. `2657886513.000` → `2657886513000`)
- **County property report** — `https://gis.wilson-co.com/maps/assets/wilson/PropertyReport.html?PIN={PIN}`
- **NC OneMap parcels** — filter `cntyfips='195'` on NC1Map_Parcels FeatureServer/1

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `ParcelNumber`, `OwnerID`, `GISPIN`; OneMap `parno` | Prefer `PIN`; `OwnerID` for PA deep-link |
| polygons | Yes | Tax/Taxparcels FS/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CACRES`, `DeedAcres`, `MapAcres`; OneMap `gisacres` | **~6,144** CACRES 5–150 |
| ownerName | Yes | `Name1` / `Name2` / `Name3`; OneMap `ownname` | Public on REST |
| mailing address | Yes | `TaxpayerAddress1` + city/state/zip | Structured |
| situs address | Yes | `PhysicalStreetAddress` + PhysLc* parts; `CityCodeDesc` | Join Master Addresses when sparse |
| lastSale date/price | Yes (last) | `SalesAmount`, `DateSold` (YYYYMMDD), `SaleDate`, `QualifyCode` | QualifyCode A ≈ arms-length; Three_Year_Sales complements |
| tax values | Yes | `TotalFMVCurrent`, `LandFMVCur`, `ImproveFMVCur`, `TotalASVCurrent`, land/improve ASV | Market + assessed with split |
| zoning | Yes / split | City CURRENTZONE; town ZONES/ZONING/CODE; county ZONING | Cities-first routing |
| flu | Yes / partial | City `CGF_CA`; county `FLU_v3` (6 polys) | Town FLU beyond Wilson city not public |
| appraiser / viewer link | Yes | DevNet parcel/view/{OwnerID}; PropertyReport?PIN=; county maps | Templates below |

### CityCodeDesc inventory (municipality routing)

| CityCodeDesc | Approx parcels | Zoning source |
|--------------|----------------|---------------|
| Wilson | 21,609 | City Zoning FS/1 (CITY-FIRST) |
| (blank unincorporated) | ~17,239 | County Zoning |
| Elm City | 1,015 | **GAP** — county zoning + boundaries |
| Lucama | 755 | Planning App FS/33 |
| Stantonsburg | 657 | Planning App FS/37 |
| Sims | 606 | Planning App FS/35 |
| (null) | ~610 | treat as unincorporated |
| Black Creek | 332 | Planning App FS/32 |
| SARATOGA | 267 | Planning App FS/34 |
| SHARPSBURG | 194 | Planning App FS/36 (multi-county tip) |
| KENLY | 180 | Johnston card (tip) |
| Bailey / Macclesfield / Middlesex / Walstonburg / Rocky Mount / Fountain / Fremont | ≤36 each | Adjacent county cards |

### Municipal Boundaries (Planning App FS/18) — 9 features

CITY OF WILSON, ELM CITY, LUCAMA, BLACK CREEK, STANTONSBURG, SIMS, SARATOGA, SHARPSBURG, KENLY.

## Layers (verified)

### 1. Tax/Taxparcels — parcels + CAMA (PRIMARY)

- **REST:** https://gis.wilson-co.com/arcgis/rest/services/Tax/Taxparcels/FeatureServer/0
- **Layer:** 0 · Polygon · county-wide · **43,549** · maxRecordCount **2,000**
- **Fields:** `PIN`/`ParcelNumber`/`GISPIN`/`OwnerID` → id; `CACRES`/`DeedAcres`/`MapAcres` → acreage; `Name1`–`Name3` → owner; `TaxpayerAddress*` → mailing; `PhysicalStreetAddress` + PhysLc* → situs; `SalesAmount`/`DateSold`/`SaleDate`/`QualifyCode`/`DeedBook`/`DeedPage` → last sale; `TotalFMVCurrent`/`LandFMVCur`/`ImproveFMVCur`/`TotalASVCurrent`/ASV splits/`TaxableValue` → tax; `CityCodeDesc` → muni routing.
- **Verified counts:** CACRES 5–150 **6,144**; improve 0/null in band **3,213**; SalesAmount>0 in band **1,798**; QualifyCode=A in band **867**.
- **Notes:** Wire-first. `OwnerID` = ParcelNumber without `.` (PA key). City mirror: `publiclayers/Parcels` FS/0 (maxRecordCount 200000). Geo-verify sample centroids ~-78.13 / 35.61 (Wilson). Paginate.

### 2. NC OneMap parcels — statewide fallback

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='195'` · **43,308** · gisacres 5–150 **6,143** · improvval 0/null **10,256**
- **Fields:** `parno`, `ownname`, mailing/site parts, `gisacres`, `saledate`, `parval`/`landval`/`improvval`
- **Notes:** No sale price. `parno` ≈ county ParcelNumber. Alt host: services.gis.nc.gov.

### 3. Three_Year_Sales_Beta — recent sales subset

- **REST:** https://gis.wilson-co.com/arcgis/rest/services/Tax/Three_Year_Sales_Beta/FeatureServer/0
- **Count:** **7,673** polygons with SalesTable* transfer fields + parcel CAMA.
- **Notes:** Supplement; parcel `SalesAmount`/`DateSold` remains general last-sale source.

### 4. City of Wilson Zoning — CITY-FIRST

- **REST:** https://gis.wilsonnc.org/services/rest/services/publiclayers/Zoning/FeatureServer/1
- **Count:** **984** · fields `CURRENTZONE`, `ZONENAME`, …
- **Codes (sample):** GC, OS, RMX, GR6, RA, SR6, LI, NC, SR4, ICD, NMX, UR, HC, HI, MHR, CCMX, IMX
- **Notes:** Prefer inside City of Wilson / ETJ where city zoning applies. Mirror: Planning Application FS/40. Conditional Use FS/0 companion.

### 5. County Zoning — unincorporated

- **REST:** https://gis.wilson-co.com/arcgis/rest/services/Planning/County_Zoning/MapServer/0
- **Count:** **12,528** · field `ZONING`
- **Top codes:** AR (~10,162), R20MH, R20, B1, R15MH, M1, M2, R15S, R30, OI (+ CD variants)
- **Notes:** Pair with Municipal Boundaries; do not override city/town layers inside limits.

### 6–11. Town zoning (Planning Application FeatureServer)

| Town | Layer | Count | Zone field | Notes |
|------|-------|------:|------------|-------|
| Lucama | FS/33 | 31 | ZONES | CH, R-15, LI, R-7, RA-20, CD, R-10, R-10MH |
| Black Creek | FS/32 | 13 | ZONES | R-10, MH, R-15, RA, CD, LI, CH |
| Stantonsburg | FS/37 | 15 | ZONES | RA, C, RS, RH, RMH, LI |
| Sims | FS/35 | 12 | ZONING_TYP | H I, H C, R-15, R-10, RA, L I, C D |
| Saratoga | FS/34 | 20 | ZONING | RA, GB, R-15, R-10, LI |
| Sharpsburg | FS/36 | 32 | CODE | R-6M, B-1, RA-30, MHP, R-10, R-12; multi-county |

**Elm City:** no public town zoning FS — gap.

### 12. City FutureLandUse_2043 — CITY-FIRST FLU

- **REST:** https://gis.wilsonnc.org/services/rest/services/publiclayers/FutureLandUse_2043/FeatureServer/0
- **Count:** **93** · field `CGF_CA`
- **Values:** MEDIUM HIGH RESIDENTIAL, LOW DENSITY RESIDENTIAL, MIXED USE COMMERCIAL, INDUSTRIAL, INFRASTRUCTURE, INSTITUTIONAL, DOWNTOWN
- **Notes:** Companion FutureLandUseOverlay_2043 (26) is project overlays, not FLU class.

### 13. Future Land Use Plan 2045 — county (partial)

- **REST:** Planning Application FS/43 · **6** polys · field `FLU_v3`
- **Values:** Agriculture / Rural, Conservation, Employment Center, Municipal Center, Reserved Growth Area, Rural Commercial Crossroad
- **Status:** partial — coarse growth framework only.

### 14. Municipal Boundaries / ETJ / Master Addresses

- Boundaries FS/18 — **9** munis (see table)
- ETJ MapServer/0 — **9** polys (mirror FS/20)
- Master Addresses FS/0 — **53,140** points for situs join

## Jurisdiction routing

| Jurisdiction | Zoning source | FLU | Viewer |
|--------------|---------------|-----|--------|
| City of Wilson | City Zoning FS/1 (first) | FutureLandUse_2043 | Community Maps |
| Lucama / Black Creek / Stantonsburg / Sims / Saratoga / Sharpsburg | Planning App town layers (first) | County FLU 2045 coarse | County maps |
| Elm City | County Zoning + boundaries (**gap** town FS) | County FLU 2045 coarse | County maps |
| Unincorporated | County Zoning | County FLU 2045 coarse | County maps |
| Kenly / other tips | Adjacent county cards | — | — |

## Gaps and cautions

- Elm City lacks a public zoning FeatureServer
- County FLU Plan 2045 is 6 coarse polygons — not parcel-grain; no town FLU REST beyond City of Wilson
- DateSold is YYYYMMDD integer — cast for date filters
- No multi-decade sales history beyond last sale + Three_Year_Sales
- Sharpsburg / Kenly / Bailey tips are multi-county — clip or defer to adjacent cards
- No AADT, utilities, phones, emails, or paid-vendor data in this card

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Files:** `37195-wilson.md` · `37195-wilson.json` · `37195-wilson.yaml`


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://gis.wilson-co.com/arcgis/rest/services/Tax/Taxparcels/FeatureServer/0 · id `OwnerID` · live count **43,549** · 5–150 ac **6,144** (`CACRES >= 5 AND CACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='WILSON'` gives **606** stations (316 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27WILSON%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Wilson'` gives **606** stations (378 with AADT_2025, 324 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Wilson%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Wilson'` gives **605** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `TotalFMVCurrent` non-zero **42,705**, `TotalASVCurrent` non-zero **40,890**, `TaxableValue` non-zero **40,890**
- **Sale history (ok):** price `SalesAmount` >0 **23,083**; date `SaleDate` non-null **42,548**
- **Owner entity:** fields `Name1`, `Name2`, `Name3`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **1,806** of 6,144 (extended regex: 1,909).
- **PA deep link:** `https://wilsonnc.devnetwedge.com/parcel/view/{OwnerID}`. Tested `3637665541000` → HTTP **200** (text/html), content verified: True. Parcel id found in the response body.
- **Jurisdiction GIS viewer:** https://gis.wilson-co.com/maps → HTTP **200** (Wilson County, North Carolina GIS)
- **Pass 2 gaps:** none
