# McDowell County, NC — GIS County Card

## Summary

McDowell County (Asheville shed, FIPS **37111**, slug **mcdowell**, `cntyfips='111'`) publishes public ArcGIS REST via HandP **WebGIS** at **`www.webgis.net/arcgis/rest/services/NC/McDowell/MapServer`**. **Wire-first parcels + CAMA:** layer **2 Parcels** — ~**33,500** polys with `PIN`/`ParcelNumber`/`AccountNumber`, owner, mailing, situs components, land/bldg/total market + assessed values, deed book/page, **`SaleYear1`/`SaleMonth1`/`SaleDay1`** + `DeedDate` (**no SalePrice on REST**). Prefer **`Shape.STArea()/43560`** or **OneMap `gisacres`** for acreage — `CALCULATED_ACREAGE` is null on ~**26.5k** parcels; shape/OneMap 5–150 → **~5,638**. **Cities-first zoning:** **City of Marion** native `OfficialZoningDistricts` (**168**) + parcel-join `Current_Zoning_WFL1` (~**3,956**); county host mirror `McDowell/7`. **McDowell Co Zoning** `/236` (**669** PIN-attributed polys — limited districts, not countywide). **Old Fort** — municipal boundary only; **no public zoning REST**. **FLU:** Comp Land Use Plan **PDF only**. **PA deep-link:** `https://www.bttaxpayerportal.com/ITSPublicMD/AppraisalCard.aspx?id={PIN}`. **Jurisdiction GIS:** `https://www.webgis.net/nc/McDowell/`. **NC OneMap** `cntyfips='111'` geometry/owner/tax/saledatetx fallback (no sale price; `saledate` epoch empty). Markets: **[Asheville]**.

## Portals

- **Jurisdiction GIS (WebGIS)** — https://www.webgis.net/nc/McDowell/
- **County ArcGIS REST** — https://www.webgis.net/arcgis/rest/services/NC/McDowell/MapServer
- **County website** — https://mcdowellnc.gov/ (alias mcdowellgov.com)
- **Planning** — https://mcdowellnc.gov/departments/planning
- **Planning ordinances** — https://mcdowellnc.gov/departments/planning/ordinances
- **County plans (FLU PDFs)** — https://mcdowellnc.gov/county/plans
- **Land Use Plan PDF** — https://mcdowellnc.gov/county/plans/McDowell%20County%20Land%20Use%20Plan-2.pdf
- **Adopted plan PDF (2024)** — https://mcdowellnc.gov/county/plans/McDowellCountyadoptedplan11-18-24.pdf
- **PA / AppraisalCard (ITSPublicMD)** — https://www.bttaxpayerportal.com/ITSPublicMD/ — Deep link: `https://www.bttaxpayerportal.com/ITSPublicMD/AppraisalCard.aspx?id={PIN}`
- **PA Real Estate Search** — https://www.bttaxpayerportal.com/ITSPublicMD/RealEstateSearch
- **PA Basic Search** — https://www.bttaxpayerportal.com/ITSPublicMD/BasicSearch
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/mcdowell/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/mcdowell/parcel-detail/{PIN}`
- **Tax bills (Catalis)** — https://mcdowellnctax.com/
- **SmartGov permits / parcels** — https://co-mcdowell-nc.smartgovcommunity.com/Parcels/ParcelHome
- **Deeds search** — http://search.mcdowelldeeds.com/index.php
- **City of Marion GIS (AGOL)** — https://marion.maps.arcgis.com/home/index.html
- **Marion Zoning Map app** — https://marion.maps.arcgis.com/apps/Viewer/index.html?appid=9493de66cb89495eb0bc30803f9789
- **Marion Planning & Development** — https://www.marionnc.org/159/Planning-Development
- **Town of Old Fort** — https://townofoldfort.org/
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='111'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` / `ParcelNumber`; `AccountNumber`; `MDFormattedFirst13`; OneMap `parno` | Prefer **PIN** (12-digit) for PA/OneMap |
| polygons | Yes | McDowell/MapServer/2; OneMap | CRS **102719 / 2264** |
| acreage | Yes (prefer shape/OneMap) | `Shape.STArea()/43560`; OneMap `gisacres`; `CALCULATED_ACREAGE` / `TOTAL_ACREAGE` when populated | Shape/OneMap 5–150 → **~5,638**; CALC populated only ~**6,975** |
| ownerName | Yes | `Name1` / `Name2`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `Address1`/`Address2`/`City`/`State`/`ZipCode` | |
| situs address | Yes (compose) | `HouseNumber` + `StreetName` + `StreetType` | Often thin vs mailing |
| lastSale date/price | Partial | `SaleYear1`/`SaleMonth1`/`SaleDay1`; `DeedDate`; OneMap `saledatetx` | **Sale price REST gap**; date strong (~**32.9k** SaleYear1>0) |
| tax values | Yes | `TotalMarketValue`, `TotalAssessedValue`, `ParcelLandValue`, `ParcelBuildingValue`, `ParcelObxfValue` | Typed doubles; mkt>0 → **~33,112** |
| zoning | Yes (cities-first) | Marion OfficialZoningDistricts / Current_Zoning_WFL1; county Zoning/236 | Old Fort REST gap; most unincorp unzoned |
| flu | Gap | Comp Land Use Plan PDFs | No FLU FeatureServer |
| appraiser / viewer link | Yes | ITSPublicMD AppraisalCard `{PIN}`; NCPTS `{PIN}`; WebGIS | TRANCHE-3 |

### CityCode → municipality (parcel tax district)

| CityCode | Approx parcels | Jurisdiction | Zoning source (prefer) |
|----------|----------------|--------------|------------------------|
| C1 | **3,637** | City of Marion | **Marion OfficialZoningDistricts** (+ Current_Zoning_WFL1 PIN join) |
| C2 | **619** | Town of Old Fort | **Gap** — boundary only; contact town |
| *(blank/null)* | **~29,234** | Unincorporated McDowell | County Zoning/236 where present (**669**); else unzoned |
| other junk codes | ~9 | — | Ignore / verify spatially |

## Layers (verified 2026-09-24)

### 1. NC/McDowell Parcels — parcels + ownership + tax + sale date (PRIMARY CAMA)

- **Purpose:** parcels | tax | ownership | sales (date only)
- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/McDowell/MapServer/2
- **Layer name / id:** Parcels / 2
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN`, `ParcelNumber` → parcelId
  - `AccountNumber` → parcelIdAccount
  - `MDFormattedFirst13`, `PinNumber`, `MD10Digit` → parcelIdAlt
  - `CALCULATED_ACREAGE`, `TOTAL_ACREAGE` → acreage (sparse)
  - `Name1`, `Name2` → ownerName
  - `Address1`, `Address2`, `City`, `State`, `ZipCode` → mailing
  - `HouseNumber`, `StreetName`, `StreetType` → situs (compose)
  - `SaleYear1`, `SaleMonth1`, `SaleDay1`, `DeedDate` → lastSale.date
  - `DeedBook1`, `DeedPage1` → deed
  - `TotalMarketValue`, `TotalAssessedValue` → tax.market / assessed
  - `ParcelLandValue`, `ParcelBuildingValue`, `ParcelObxfValue` → tax split
  - `CityCode` → municipality router (C1/C2)
  - `TownshipCode`, `TaxCode2` → fire/township hints
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **33,500**; `Shape.STArea()/43560` 5–150 → **5,638**; `CALCULATED_ACREAGE` 5–150 → **1,789** (CALC>0 → **6,975**; CALC null → **26,519**); `TotalMarketValue>0` → **33,112**; `SaleYear1>0` → **32,912**; vacant (bldg 0/null) in 5–150 CALC → **1,030**
- **Notes:** **PRIMARY** for tax/owner/sale-date. MapServer only (no FeatureServer twin). MaxRecordCount **1000** — paginate. **No SalePrice field** — use PA card for price QA. Prefer shape acres or OneMap when CALC null. WebGIS identify wires AppraisalCard to `PIN`.

### 2. OpenGovSpatJoin — point CAMA twin (secondary)

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/McDowell/MapServer/4
- **Geometry:** Point
- **Verified:** count **31,435**
- **Notes:** Same CAMA attr family as Parcels (+ `GIS_Lat`/`GIS_Long`, multi-deed slots). Prefer polygons /2 for outlines.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='111'`
- **Fields:** `parno`,`altparno`,`ownname`,`mailadd`/`mcity`/`mstate`/`mzip`,`siteadd`,`gisacres`,`parval`/`landval`/`improvval`,`saledatetx` (epoch `saledate` empty), `cntyfips`
- **Verified:** yes — **33,449**; `gisacres` 5–150 → **5,638**; `parval>0` → **33,074**; `saledate IS NOT NULL` → **0**; `saledatetx` populated ~all
- **Notes:** Strong acreage when county CALC null. No sale price. Join `parno`↔`PIN`.

### 4. City of Marion OfficialZoningDistricts — PRIMARY Marion zoning

- **Purpose:** zoning (city-first)
- **REST URL:** https://services3.arcgis.com/q5DjgI77eZ9vJ4mD/arcgis/rest/services/OfficialZoningDistricts/FeatureServer/0
- **County mirror:** https://www.webgis.net/arcgis/rest/services/NC/McDowell/MapServer/7 (`ZONE_ID`, `District_N`, `URL`) — count **167**
- **Fields:** `ZONE_ID`, `District_N`, `Acres`, `URL`, `piclink`
- **Verified:** yes — count **168**
- **ZONE_ID (top):** R2 (72), C2 (32), M1 (25), R3 (11), R4 (7), OI (6), R1 (6), PR (5), B1/C1/DO (1 each)
- **Notes:** Prefer city AGOL host inside Marion. Ordinance URL on features. Updated Oct 2021 per service description.

### 5. Marion Current_Zoning_WFL1 — parcel polygons with ZONE_ID (Marion)

- **REST URL:** https://services3.arcgis.com/q5DjgI77eZ9vJ4mD/arcgis/rest/services/Current_Zoning_WFL1/FeatureServer/0
- **Fields (truncated):** `…_Merge_PIN` → PIN; `…_AddSpatialJoin_ZONE_ID` / `_District_N`
- **Verified:** count **3,956**
- **Notes:** Attribute-friendly PIN→zone join for Marion; still cross-check OfficialZoningDistricts for authority. Downtown overlay FS separate (count **1**).

### 6. McDowell Co Zoning — limited county districts

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/McDowell/MapServer/236
- **Fields:** `PIN`, `Zoning`
- **Verified:** count **669**
- **Zoning values:** Open (229), R-A1 (145), R2 (105), R1 (61), R-A3 (56), R-A2 (46), G-B (26), Utility (1)
- **Notes:** PIN-attributed polys — **not** countywide coverage. Most unincorporated land is **unzoned** on public REST; use only where feature exists. Lake James / watershed overlays are separate layers (226–227, 235) — constraints, not base zoning.

### 7. Municipal boundaries

- **Marion Limits:** McDowell/MapServer/5 — count **1** (`Name`, `Acres`)
- **Marion Municipal Boundary:** /229 — count **43** (legacy zone-tagged polys)
- **Old Fort Municipal Boundary:** /230 — count **1** (`Name`)
- **Marion AGOL boundary:** https://services3.arcgis.com/q5DjgI77eZ9vJ4mD/arcgis/rest/services/MarionMunicipalBoundary/FeatureServer

### 8. Marion City_Tax_Parcel — city extract (optional)

- **REST URL:** https://services3.arcgis.com/q5DjgI77eZ9vJ4mD/arcgis/rest/services/City_Tax_Parcel/FeatureServer/0
- **Verified:** count **3,804**
- **Notes:** Truncated CAMA field names; prefer county Parcels/2 countywide.

### 9. FLU — PDF only (gap)

- McDowell County Land Use Plan: https://mcdowellnc.gov/county/plans/McDowell%20County%20Land%20Use%20Plan-2.pdf
- Adopted plan 11-18-24: https://mcdowellnc.gov/county/plans/McDowellCountyadoptedplan11-18-24.pdf
- No public FLU FeatureServer (county or Marion/Old Fort).

## Municipalities (cities-first)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| **Marion** | **OfficialZoningDistricts** (prefer) + Current_Zoning_WFL1 + county /7 | 168 / 3956 / 167 | **Yes** — marion.maps.arcgis.com | No — PDF/county plan | County seat; CityCode C1 ~3637 |
| **Old Fort** | — | — | Town site only | No | Boundary /230; **zoning REST gap** — contact town |
| Unincorporated McDowell | County Zoning /236 where present | 669 | County WebGIS | PDF only | Mostly unzoned outside limited districts |

## PA / deep-link templates

| Purpose | Template |
|---------|----------|
| Appraisal card (PRIMARY PA) | `https://www.bttaxpayerportal.com/ITSPublicMD/AppraisalCard.aspx?id={PIN}` |
| NCPTS parcel detail | `https://lrcpwa.ncptscloud.com/mcdowell/parcel-detail/{PIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/mcdowell/parcel-search |
| Jurisdiction GIS | https://www.webgis.net/nc/McDowell/ |
| Catalis tax pay | https://mcdowellnctax.com/ |

WebGIS identify popup embeds AppraisalCard with `atts.PIN` (siteCustom.js). RealEstateSearch `/Parcel/{PIN}` returns **404** — use AppraisalCard.

## Gaps / caveats

- **Sale price** not on public REST (sale date/deed only) — PA AppraisalCard for price QA
- `CALCULATED_ACREAGE` null on ~79% of parcels — use `Shape.STArea()/43560` or OneMap `gisacres`
- County Zoning **669** only — majority of unincorporated land unzoned on REST
- **Old Fort zoning REST gap** (boundary only)
- **FLU PDF-only** — no FeatureServer
- OneMap `saledate` epoch empty; use `saledatetx` or county SaleYear/Month/Day
- MapServer-only parcels (no FeatureServer) — paginate MaxRecordCount 1000
- Utilities and AADT intentionally excluded; no emails/phones/paid vendors

## License / attribution

McDowell County GIS / Land Records / Tax Administration (HandP WebGIS); City of Marion GIS; NC OneMap. Data for tax/reference — not a survey. Commercial resale subject to **NCGS 132-10**. Attribute McDowell County GIS (+ City of Marion where used).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 10+
- Live `returnCountOnly` + sample attribute queries against NC/McDowell/MapServer Parcels/2, OpenGovSpatJoin/4, Marion Zoning/7, County Zoning/236, munis boundaries, Marion OfficialZoningDistricts + Current_Zoning_WFL1 + City_Tax_Parcel, NC OneMap `cntyfips='111'`, and ITSPublicMD AppraisalCard `?id={PIN}` + NCPTS parcel-detail.
- **tranche:** 3 (tax/owner + sale date public; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning suite; FLU/sale-price/Old Fort gaps documented)


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://www.webgis.net/arcgis/rest/services/NC/McDowell/MapServer/2 · id `PIN` · live count **33,500** · 5–150 ac **1,789** (`CALCULATED_ACREAGE >= 5 AND CALCULATED_ACREAGE <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='MCDOWELL'` gives **317** stations (208 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27MCDOWELL%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='McDowell'` gives **318** stations (196 with AADT_2025, 155 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27McDowell%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `TotalMarketValue` non-zero **33,112**, `TotalAssessedValue` non-zero **33,112**
- **Sale history (partial):** price not on REST; date `DeedDate` non-null **32,912**, `SaleYear1` non-null **32,912**. Price not on REST; ITSPublicMD AppraisalCard PDF has SALES DATA grid (BOOK/PAGE/MO/YR/SALES PRICE).
- **Owner entity:** fields `Name1`, `Name2`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **284** (all parcels: 4,391), using the SQL approximation on `Name1`.
- **PA deep link:** `https://www.bttaxpayerportal.com/ITSPublicMD/AppraisalCard.aspx?id={PIN}`. Tested `068600758106` → HTTP **200** (application/pdf), content verified: True. Owner and parcel id verified in the response.
- **Jurisdiction GIS viewer:** https://www.webgis.net/nc/McDowell/ → HTTP **200** (McDowell County NC WebGIS)
- **Pass 2 gaps:** sale partial
