# Stanly County, NC — GIS County Card

## Summary

Stanly County (Charlotte MSA, FIPS **37167**) publishes a strong **public** ArcGIS Online stack under org `w1igg0Q14weqYXUh` (Stanly County GIS / Paul Reynolds): countywide **parcel polygons + CAMA** (owner, mailing, situs `PhyStreetAddr`, `ACRES`/`DeedAcres`, land/total FMV + ASV, last-sale date/amount) on `parcel_records_base_2` FeatureServer **Parcels / 3**. **Zoning is city-first** via combined **Zoning / 14** with `Jurisdiction2` = Albemarle / Locust / Norwood / Badin / Oakboro / New London / Richfield / Stanfield / Red Cross / Misenheimer / County. **Future Land Use** lives on `land_records_base` **Future Land Use Areas / 20** (`FLUM_Des` + `Comm_Type` on parcel-like polys). **NC OneMap** (`cntyfips='167'`) is a solid statewide fallback. Main gaps: **no independent city ArcGIS** for any municipality; Locust Cabarrus OpenData zoning is historic/sparse; FLU is FLUM-on-parcels (not pure FLU districts).

## Portals

- **Land Records App (viewer)** — https://stanlycounty.maps.arcgis.com/apps/webappviewer/index.html?id=195ae28fc5454875a5cc60eb8b28bbf6
- **Stanly GIS hub** — https://www.stanlygis.net/
- **Tax / appraiser search (Avalon)** — https://www.stanlytax.com/#/
- **Property card PDF (by TAXRECORD)** — `https://www2.stanlycountync.gov/gisphotoviewer/propertyCard.ashx?pin={TAXRECORD}`
- **Mapping / Land Records** — https://www.stanlycountync.gov/305/Mapping-Land-Records
- **Tax Administration** — https://www.stanlycountync.gov/157/Tax-Administration
- **City of Albemarle Maps/GIS** — https://www.albemarlenc.gov/departments/planning-and-development-services/city-county-maps-gis (defers to Stanly County GIS)
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` (12-digit); `TAXRECORD` (account) | Prefer `PIN` for map/OneMap joins; `TAXRECORD` for property-card PDF |
| polygons | Yes | parcel_records_base_2 Parcels/3 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `ACRES`; `DeedAcres`; OneMap `gisacres` | ~**8,560** parcels in 5–150 ac (`ACRES`) |
| ownerName | Yes | `Name1`+`Name2`+`Name3` / OneMap `ownname` | No phones/emails on REST |
| mailing address | Yes | `TaxPayerAddr1/2`,`TaxPayerCity`,`State`,`Zip` | |
| situs address | Yes | `PhyStreetAddr`; Address Points `FullAddressLabel` | Address points lack PIN — spatial join |
| lastSale date/price | Yes | `DateSold`,`SaleAmount` (ints); Sales/6 + OneTaxSales/20 history | ~2,084 of 5–150 ac have SaleAmount>0; DateSold epoch ms UTC |
| tax values | Yes | `LandFMVCurrent`,`TotalFMVCurrent`,`*ASVCurrent`,`LandLUVCurrent` | Typed integers |
| zoning | Yes (split by city) | Zoning/14 `ZONING` + `Jurisdiction2` | **City-first** — see Municipalities |
| FLU | Yes | `FLUM_Des`,`Comm_Type` on land_records_base/20 | Parcel-joined FLUM; join by PIN |
| appraiser / viewer link | Yes | stanlytax.com; propertyCard by TAXRECORD; Land Records App | Templates below |

## Layers (verified)

### 1. parcel_records_base_2 Parcels — parcels + ownership + tax + last sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last)
- **REST URL:** https://services6.arcgis.com/w1igg0Q14weqYXUh/arcgis/rest/services/parcel_records_base_2/FeatureServer/3
- **Mirrors:** parcel_records_base/FeatureServer/3 (44346); OpenGov2/FeatureServer/2 (44346)
- **Layer name / id:** Parcels / 3
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (12-digit NC PIN)
  - `TAXRECORD` → tax account / property-card key
  - `ACRES`, `DeedAcres` → acreage
  - `Name1`, `Name2`, `Name3` → ownerName
  - `TaxPayerAddr1/2`, `TaxPayerCity`, `State`, `Zip` → mailing
  - `PhyStreetAddr` → situs
  - `DateSold`, `SaleAmount` → lastSale (typed ints; DateSold epoch ms UTC)
  - `LandFMVCurrent`, `TotalFMVCurrent` → tax.marketValue
  - `LandASVCurrent`, `TotalASVCurrent`, `TotalMajorASVCurrent`, `TotalMiscASVCurrent` → assessed / improvements
  - `LandLUVCurrent`, `PUVParcel` → present-use / deferred
- **WKID / CRS:** 102719 (latest 2264) — NAD 1983 StatePlane NC Feet
- **Verified:** yes — count **44,458**; `ACRES BETWEEN 5 AND 150` → **8,560**; `SaleAmount>0` in range → **2,084**; sample centroids geo-verified in Stanly (~-80.09, 35.16)
- **Notes:** Best single county layer for land search. Spatial-join **Zoning/14** for city-first codes. MaxRecordCount **2000**. Prefer `_2` over older mirrors.

### 2. Address Points — situs join

- **REST URL:** https://services6.arcgis.com/w1igg0Q14weqYXUh/arcgis/rest/services/parcel_records_base_2/FeatureServer/4
- **Geometry:** Point
- **Fields:** `FullAddressLabel`, `ADDRNUM`, `ROAD_*`, `City`/`City2`, `ZipCode`
- **Verified:** count **36,456**
- **Notes:** No PIN — spatial/nearest join. Prefer `PhyStreetAddr` on parcels when populated.

### 3. Sales points + OneTaxSales table — sale history

- **Sales points:** FeatureServer/6 — count **34,957**; `ParcelID`≈TAXRECORD family; `DateSold`,`SaleAmount`,`DeedAcres`
- **OneTaxSales table:** FeatureServer/20 — count **43,260** (no geometry)
- **Notes:** Use for multi-sale history; wire-first last sale already on Parcels/3.

### 4. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date only)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1 *(layer 0 = points)*
- **Key fields → targets:** `parno`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`/`scity`, `gisacres`, `saledate`/`saledatetx`, `parval`/`landval`/`improvval`, `cntyfips`
- **Verified:** yes — `cntyfips='167'` → **44,171**; `gisacres` 5–150 → **8,533**
- **Notes:** No sale price. Join `parno`↔`PIN`.

### 5. Zoning — municipal + county (city-first)

- **Purpose:** zoning (by municipality)
- **REST URL:** https://services6.arcgis.com/w1igg0Q14weqYXUh/arcgis/rest/services/parcel_records_base_2/FeatureServer/14
- **Mirrors:** parcel_records_base/14; OpenGov2/12 (888)
- **Geometry:** Polygon
- **Fields:** `ZONING`, `PENDINGZONING`, `JURISDICTION`, `Jurisdiction2`, `Label`, `SymbolCode`
- **WKID / CRS:** 102719 / 2264
- **Verified Jurisdiction2 counts (2026-09-24):** County **361**, Albemarle **203**, Norwood **76**, Locust **63**, Oakboro **49**, Stanfield **33**, Richfield **30**, New London **25**, Red Cross **24**, Badin **18**, Misenheimer **13**; total **895**
- **Join to parcels:** spatial join (intersect/centroid) on CRS 2264; filter by `Jurisdiction2` (or JURISDICTION codes ALB/NOR/LOC/OAK/STA/RIC/NEW/RED/BAD/MIS/COU).

### 6. Zoning Overlay

- **REST URL:** https://services6.arcgis.com/w1igg0Q14weqYXUh/arcgis/rest/services/parcel_records_base_2/FeatureServer/13
- **Fields:** `Type`, `Jurisdiction`, `BufferDist`
- **Verified:** count **46** (RA-TO 21, S-O 2, SEPGS Overlay 1; many Type null)
- **Notes:** Not base zoning — apply after Zoning/14.

### 7. Future Land Use Areas — county FLUM

- **REST URL:** https://services6.arcgis.com/w1igg0Q14weqYXUh/arcgis/rest/services/land_records_base/FeatureServer/20
- **Fields:** `FLUM_Des`, `Comm_Type`, `PIN`, `ACRES` (+ truncated CAMA)
- **Verified:** count **23,116**
- **FLUM_Des:** Rural Preservation **14305**, Secondary Growth **5059**, Primary Growth **3271**, Airport Overlay **481**
- **Comm_Type:** Rural Living, Single/Multi-Family Neighborhood, Working Farm, Community/Mixed-Use Center, Industrial, Preserved/Recreational Open Space, K-12/University campuses, Airport
- **Notes:** Parcel-like polygons with FLUM attrs — join by `PIN` or spatial. MaxRecordCount **1000**.

### 8. City Limits — jurisdiction polygons

- **REST URL:** https://services6.arcgis.com/w1igg0Q14weqYXUh/arcgis/rest/services/parcel_records_base_2/FeatureServer/8 (also /7 City Limit Boundary; OpenGov2/13)
- **Fields:** `City`, `IMSLabel`, `CODE`, `DIST_NAME`
- **Verified:** count **40** (multi-part)
- **Codes:** ALB Albemarle, NOR Norwood, LOC Locust, OAK Oakboro, SFD Stanfield, RFD Richfield, NEW New London, RED Red Cross, BAD Badin, MIS Misenheimer

### 9. Locust Zoning (Cabarrus OpenData) — Cabarrus-side historic only

- **REST URL:** https://location.cabarruscounty.us/arcgisservices/rest/services/opendata/MapServer/39
- **Verified:** count **8** (sparse/historic)
- **Notes:** Locust spans Cabarrus + Stanly. Prefer Stanly Zoning `Jurisdiction2='Locust'` (63) for Stanly-side.

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| Unincorporated Stanly | Zoning Jurisdiction2='County' | 361 | County | County FLUM/20 | Unincorporated |
| Albemarle | Zoning Jurisdiction2='Albemarle' | 203 | No (defers to Stanly GIS) | County FLUM | Largest city |
| Locust | Zoning Jurisdiction2='Locust' | 63 | No | County FLUM | Also Cabarrus OpenData Locust Zoning (8) for Cabarrus-side |
| Norwood | Zoning Jurisdiction2='Norwood' | 76 | No | County FLUM | |
| Badin | Zoning Jurisdiction2='Badin' | 18 | No | County FLUM | |
| Oakboro | Zoning Jurisdiction2='Oakboro' | 49 | No | County FLUM | |
| New London | Zoning Jurisdiction2='New London' | 25 | No | County FLUM | Space in Jurisdiction2 |
| Richfield | Zoning Jurisdiction2='Richfield' | 30 | No | County FLUM | City code RFD |
| Stanfield | Zoning Jurisdiction2='Stanfield' | 33 | No | County FLUM | City code SFD |
| Red Cross | Zoning Jurisdiction2='Red Cross' | 24 | No | County FLUM | Space in Jurisdiction2 |
| Misenheimer | Zoning Jurisdiction2='Misenheimer' | 13 | No | County FLUM | |

## Gaps / caveats

- No public city-native ArcGIS for Albemarle, Locust, Norwood, Badin, Oakboro, New London, Richfield, Stanfield, Red Cross, or Misenheimer — use county Zoning with `Jurisdiction2` filter
- Locust Cabarrus OpenData zoning is historic/sparse (8); Stanly `Jurisdiction2='Locust'` is authoritative for Stanly-side
- FLU is FLUM attributes on parcel-like polygons — not pure planning-district polygons; MaxRecordCount 1000 on FLU FS
- Address points lack PIN; Sales `ParcelID` is TAXRECORD family not 12-digit PIN
- Token-required AGOL (`Stanly_County_Data` / `StanlyCoParcels` on services9) — skipped
- Do not collect phones/emails; utilities and AADT intentionally excluded

## License / attribution

Stanly County GIS (stanlycounty.maps.arcgis.com / org w1igg0Q14weqYXUh). Data prepared from county systems; independent verification recommended. Commercial resale subject to **NCGS 132-10**. Attribute Stanly County GIS.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 10
- Live `returnCountOnly` + sample attribute/geometry queries against parcel_records_base_2 Parcels/Zoning/Overlays/City Limits/Address/Sales, land_records_base FLU, OpenGov2 mirrors, Cabarrus Locust Zoning, propertyCard PDF by TAXRECORD, stanlytax.com, and NC OneMap `cntyfips='167'`.

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='STANLY'`, field `AADT_2022` (string) — **534 stations live**, 272 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27STANLY%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27STANLY%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Stanly'`, `AADT_2025` (int) — 534 stations; 315 with 2025, 280 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://services6.arcgis.com/w1igg0Q14weqYXUh/arcgis/rest/services/parcel_records_base_2/FeatureServer/3` — total 44458, 5–150 ac 8560 (`ACRES>=5 AND ACRES<=150`).
- Non-zero county: `LandFMVCurrent` 44063, `TotalFMVCurrent` 44079, `TotalASVCurrent` 44079; in 5–150: `TotalASVCurrent` 8512. **Status: ok.**
- Integer fields; FMV = market, ASV = assessed.

### 3. Sale history
- Price `SaleAmount`>0 15902 (5–150: 2084); date non-null `DateSold` 30632. **Status: ok.**
- DateSold esriDate; SaleAmount integer. Last sale only.

### 4. Owner entity
- Owner fields: `Name1`, `Name2`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 1243** (of 8513 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: `https://www2.stanlycountync.gov/gisphotoviewer/propertyCard.ashx?pin={TAXRECORD}`
- Tested `https://www2.stanlycountync.gov/gisphotoviewer/propertyCard.ashx?pin=2453` → **200**. HTTP 200; owner name present in server HTML (verified). Tax portal (search only): https://www.stanlytax.com/#/

### 6. Jurisdiction GIS viewer
- `https://www.stanlygis.net/` → **200**. Stanly County GIS hub; AGOL viewer https://stanlycounty.maps.arcgis.com/apps/webappviewer/index.html?id=195ae28fc5454875a5cc60eb8b28bbf6 also 200

### Pass2 gaps
- AADT_2022 blank at 262 of 534 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- No multi-transfer sale history on primary layer (last sale only)
