# Caldwell County, NC — GIS County Card

## Summary

Caldwell County (Hickory–Lenoir–Morganton MSA, FIPS **37027**, slug **caldwell**, `cntyfips='027'`) publishes a strong **public** ArcGIS REST stack at `gis.caldwellcountync.org`. **Wire-first parcels (TRANCHE-3):** **NCOnemap/NCOneMap FeatureServer/45** (mirrors Public_Access/45, OpenGov TaxParcels) — ~**52,754** polys with owner, mailing, situs (`FullPropAddress`), `TotalCalcAcres`, full tax split (`MarketValue`/`AssessedValue`/`LandValue`/`BuildingValue`/`ObxfValue`), deed book/page, and parcel-joined `ZoningInfo` stub. ~**8,142** with acres 5–150 (~**4,592** BuildingValue 0/null). **Zoning is cities-first** on `WarehouseServices/Zoning` + `Underlay` per-muni layers (Lenoir, Hudson, Granite Falls, Gamewell, Sawmills, …) plus **County Zoning**. **FLU:** county Comprehensive Plan + Living Lenoir 2045 **PDF**; Hickory city FLU REST for Hickory fringe; planning-district polygons only (not FLU). **PA deep-link:** `AppraisalCard.aspx?id={PID}` (spaces → `+`). **Jurisdiction GIS:** https://gis.caldwellcountync.org/maps/default.htm (`?pid={NCPIN}`). Markets: **[Hickory]**. Main gaps: **no sale price/date on REST** (sales on AppraisalCard PDF only); Rhodhiss Zoning layer miswired (~663 null-CITY_NAME features ≈ COUNTY); no independent city ArcGIS except Hickory.

## Portals

- **Jurisdiction GIS (Map Viewer)** — https://gis.caldwellcountync.org/maps/default.htm
- **Viewer deep-link** — `https://gis.caldwellcountync.org/maps/default.htm?pid={NCPIN}`
- **County ArcGIS REST** — https://gis.caldwellcountync.org/arcgis/rest/services
- **GIS / Mapping dept** — https://www.caldwellcountync.org/238/GIS-Mapping
- **Appraisal card (PA deep-link, preferred)** — `https://gis.caldwellcountync.org/itspublic/AppraisalCard.aspx?id={PID}`
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/caldwell/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/caldwell/parcel-detail/{NCPIN}`
- **Tax portal (Catalis)** — https://caldwellcountynctax.com/#/
- **Tax Administration** — https://www.caldwellcountync.org/159/Tax-Administration
- **Planning Department** — https://www.caldwellcountync.org/267/Planning-Department
- **Comprehensive Plan (PDF)** — https://www.caldwellcountync.org/DocumentCenter/View/490/Comprehensive-Plan-PDF
- **Zoning Map (PDF)** — https://www.caldwellcountync.org/DocumentCenter/View/519/Zoning-Map-PDF
- **Zoning Ordinance** — https://www.caldwellcountync.org/DocumentCenter/View/1570/Zoning-Ordinance
- **Living Lenoir 2045 (city FLU PDF)** — https://www.cityoflenoir.com/233/Living-Lenoir-2045-Comprehensive-Plan
- **City of Hickory ArcGIS (fringe)** — https://arcgis.hickorync.gov/server/rest/services
- **Register of Deeds** — https://caldwellrod.org/real-estate-records
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='027'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PID` (map/PA); `NCPIN` (viewer/OneMap/`parno`); `AcctNumber` | Prefer **PID** for AppraisalCard; **NCPIN** for viewer/`?pid=` |
| polygons | Yes | NCOneMap FS/45; Public_Access/45; OpenGov/1 | CRS **102719 / 2264** |
| acreage | Yes | `TotalCalcAcres`; OneMap `gisacres` | ~**8,142** in 5–150 ac |
| ownerName | Yes | `AcctName1`+`AcctName2`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `MailAddr1`–`3`,`MailCity`,`MailState`,`MailZipCode` | |
| situs address | Yes | `FullPropAddress`; SmartGov `SitusCity`/`SitusZip`; OneMap `siteadd` | |
| lastSale date/price | Gap (REST) | AppraisalCard PDF SALES DATA | **Sale price/date REST gap**; OneMap `saledate` empty |
| tax values | Yes | `MarketValue`,`AssessedValue`,`LandValue`,`BuildingValue`,`ObxfValue` | Typed doubles |
| zoning | Yes (cities-first) | Per-muni `ZONE_ID` layers; parcel `ZoningInfo` stub | Prefer spatial join to muni layers |
| flu | Partial / PDF | Comp Plan + Lenoir 2045 PDF; Hickory FLU REST | No county FLU FeatureServer |
| appraiser / viewer link | Yes | AppraisalCard `{PID}`; viewer `?pid={NCPIN}`; NCPTS `{NCPIN}` | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. NCOnemap/NCOneMap Parcels — parcels + ownership + tax + zoning stub (PRIMARY)

- **Purpose:** parcels | tax | ownership | zoning (joined stub)
- **REST URL:** https://gis.caldwellcountync.org/arcgis/rest/services/NCOnemap/NCOneMap/FeatureServer/45
- **Mirrors:** Public_Access/MapServer/45; OpenGov/MapServer/1; OpenGov/OpenGov/FeatureServer/1
- **Layer name / id:** Parcels / 45
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PID` → parcelId (PA deep-link key; spaced map ID)
  - `NCPIN` → parcelId / join to OneMap `parno` / viewer `?pid=`
  - `AcctNumber` → parcelIdAccount
  - `TotalCalcAcres` → acreage
  - `AcctName1`, `AcctName2` → ownerName
  - `MailAddr1`–`3`, `MailCity`, `MailState`, `MailZipCode` → mailing
  - `FullPropAddress` → situsAddress
  - `MarketValue`, `AssessedValue`, `LandValue`, `BuildingValue`, `ObxfValue`, `DeferredValue`, `SpecialLandValue` → tax
  - `ZoningInfo` → zoning stub (e.g. ` Lenoir: B-2`, ` COUNTY: RA-20`)
  - `DeedBook`, `DeedPage` → other
- **WKID / CRS:** 102719 (latest 2264)
- **Verified:** yes — count **52,754**; `TotalCalcAcres BETWEEN 5 AND 150` → **8,142**; `MarketValue>0` → **52,552**; BuildingValue 0/null in range → **4,592**; sample NCPIN `2871952916` = JOINER LONNIE R (centroid ≈ **-81.44, 35.97** Caldwell)
- **Notes:** Best single county layer. MaxRecordCount **2000**. Prefer spatial join to WarehouseServices/Zoning city layers over `ZoningInfo` text. Auth **none**.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date text only)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='027'`
- **Key fields:** `parno`↔`NCPIN`, `ownname`, `mailadd`…, `siteadd`, `gisacres`, `saledatetx`, `parval`/`landval`/`improvval`
- **Verified:** yes — count **52,777**; `gisacres` 5–150 → **8,136**; `saledate IS NOT NULL` → **0** (no usable epoch sale date); join verified `parno='2871952916'` ↔ county NCPIN
- **Notes:** No sale price. Prefer county `TotalCalcAcres` / CAMA for values when present.

### 3. WarehouseServices/Zoning — municipal + county zoning (city-first PRIMARY)

- **REST root:** https://gis.caldwellcountync.org/arcgis/rest/services/WarehouseServices/Zoning/MapServer
- **Mirrors:** Underlay/MapServer/15–27; OpenGov/OpenGov/FeatureServer/2–14; SmartGov/SmartGovParcels/0–12
- **Fields:** `ZONE_ID`, `CITY_NAME` (+ TYPE*/CATEGORY on some)
- **Verified counts (2026-09-24):**

| Layer id | Municipality | Count | Notes |
|---------|--------------|------:|-------|
| 8 | **Lenoir** Zoning | **1100** | City seat — city-first PRIMARY |
| 7 | Lenoir North Main overlay | 1 | Special overlay S-2 |
| 6 | **Hudson** Zoning | **2665** | Largest muni poly count |
| 4 | **Granite Falls** Zoning | **344** | |
| 3 | **Gamewell** Zoning | **1738** | CATEGORY present |
| 11 | **Sawmills** Zoning | **179** | |
| 1 | **Cajahs Mountain** Zoning | **109** | |
| 2 | **Cedar Rock** Zoning | **57** | |
| 0 | **Blowing Rock** Zoning | **17** | Mostly Watauga; Caldwell fringe |
| 5 | **Hickory** Zoning (county copy) | **14** | Prefer **arcgis.hickorync.gov** Hickory_Zoning inside Hickory |
| 10 | Rutherford College Zoning | 1 | Thin |
| 9 | Rhodhiss Zoning | 663* | **MISWIRED** — CITY_NAME null; count ≈ COUNTY; do not trust |

### 4. County Zoning — unincorporated (+ coded multi-jurisdiction)

- **REST URL:** https://gis.caldwellcountync.org/arcgis/rest/services/WarehouseServices/Planning/MapServer/2
- **Mirrors:** Underlay/MapServer/27 (count **779**); OpenGov FS/2
- **Fields:** `ZONE_ID`, `CITY_NAME` (coded: BLOWING ROCK, CAJAHS MOUNTAIN, CEDAR ROCK, COUNTY, FEDERAL, GAMEWELL, GRANITE FALLS, HICKORY, HUDSON, LENOIR, SAWMILLS)
- **Verified:** Planning/2 total **874**; `CITY_NAME='COUNTY'` → **663**; FEDERAL **49**; LENOIR **79**; etc.
- **Notes:** Use for unincorporated; inside cities prefer dedicated WarehouseServices/Zoning layers. RHODHISS not in CITY_NAME domain.

### 5. City of Hickory — Zoning + FLU (prefer inside Hickory limits)

- **Zoning:** https://arcgis.hickorync.gov/server/rest/services/Zoning_Overlays/Hickory_Zoning/MapServer/0
- **FLU:** https://arcgis.hickorync.gov/server/rest/services/Zoning_Overlays/Hickory_Future_Land_Use/MapServer/0 — field `FLU`; count **142**
- **Notes:** Caldwell fringe only; prefer over county Hickory Zoning/14.

### 6. Planning districts — partial FLU proxy (not parcel FLU)

- **Yadkin Valley Planning:** WarehouseServices/Planning/MapServer/0 — count **1**
- **Collettsville Planning:** WarehouseServices/Planning/MapServer/1 — count **1**
- **Underlay mirrors:** Collettsville/9, Yadkin Valley/10
- **Notes:** Community planning areas — **not** future land-use polygons. Full FLU = PDF (county Comp Plan; Living Lenoir 2045).

### 7. Municipalities / ETJ

- **Municipalities:** Public_Access/MapServer/48 — `CITY_NAME` includes LENOIR, HUDSON, GRANITE FALLS, GAMEWELL, SAWMILLS, CAJAHS MOUNTAIN, CEDAR ROCK, BLOWING ROCK, HICKORY, RHODHISS, RUTHERFORD COLLEGE
- **ETJ:** Public_Access/MapServer/46

### 8. SmartGov_parcels — geometry + situs city/zip (join helper)

- **REST URL:** https://gis.caldwellcountync.org/arcgis/rest/services/SmartGov/SmartGovParcels/MapServer/16
- **Fields:** `NCPIN`, `ParcelID`, owners, `FullPropAddress`, `SitusCity`/`SitusState`/`SitusZip`, mailing
- **Verified:** count **52,754** — no tax/sale values; use for situs city/zip join onto primary parcels

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| Unincorporated Caldwell | County Zoning Planning/2 CITY_NAME='COUNTY' / Underlay/27 | 663 / 779 | County | Comp Plan PDF | Unincorp UDO |
| **Lenoir** | Warehouse Zoning/8 (+ North Main/7) | 1100 (+1) | Via county viewer | Living Lenoir 2045 **PDF** | County seat; city Mapping defers to county GIS |
| **Hudson** | Warehouse Zoning/6 | 2665 | No | No | |
| **Granite Falls** | Warehouse Zoning/4 | 344 | No | No | |
| **Gamewell** | Warehouse Zoning/3 | 1738 | No | No | |
| **Sawmills** | Warehouse Zoning/11 | 179 | No | No | |
| **Cajahs Mountain** | Warehouse Zoning/1 | 109 | No | No | |
| **Cedar Rock** | Warehouse Zoning/2 | 57 | No | No | |
| **Blowing Rock** | Warehouse Zoning/0 | 17 | No | No | Fringe (mostly Watauga) |
| **Hickory** | **Hickory_Zoning** (prefer) or county/5 | 1740 / 14 | **Yes** — arcgis.hickorync.gov | **Yes** — Hickory FLU | Caldwell fringe |
| Rhodhiss | *(broken layer)* | — | No | No | Layer miswired; use ZoningInfo / rematch |
| Rutherford College | Warehouse Zoning/10 | 1 | No | No | Thin |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| Appraisal card PDF (preferred) | `https://gis.caldwellcountync.org/itspublic/AppraisalCard.aspx?id={PID}` |
| Encoding | Replace spaces in `PID` with `+` (e.g. `05 26  1 16B` → `05+26++1+16B`) |
| Viewer deep-link | `https://gis.caldwellcountync.org/maps/default.htm?pid={NCPIN}` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/caldwell/parcel-detail/{NCPIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/caldwell/parcel-search |
| Tax portal | https://caldwellcountynctax.com/#/ |
| Jurisdiction GIS | https://gis.caldwellcountync.org/maps/default.htm |

Viewer Config (`assets/Caldwell/Caldwell.js`) wires Tax Card → `AppraisalCard.aspx?id=${PID}` and Mail-To → `default.htm?pid=${NCPIN}`. Verified PDF for PID `05 26  1 16B` returns JOINER LONNIE R with SALES DATA block.

## Gaps / caveats

- **Sale price/date REST gap** — not on parcel layers; scrape AppraisalCard PDF SALES DATA or Catalis tax portal (HTML SPA) as last resort
- **Rhodhiss Zoning** FeatureServer appears miswired (663 features, CITY_NAME null ≈ COUNTY) — do not use for city-first routing
- No independent city ArcGIS for Lenoir/Hudson/Granite Falls/etc. — county WarehouseServices/Zoning is authoritative
- County / Lenoir **FLU** are PDF only; Hickory FLU REST covers Hickory fringe only
- OneMap `saledate` empty for Caldwell; `saledatetx` present but often blank
- Folder listings under `/arcgis/rest/services/{folder}` may 403; known service paths query fine with auth none
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Caldwell County Geographic Information Services (GIS). Map disclaimer: compiled from recorded deeds/plats/public records; consult primary sources; not survey quality; county and contractors assume no legal responsibility. Commercial resale subject to **NCGS 132-10**. Attribute Caldwell County GIS (and City of Hickory GIS / City of Lenoir where used).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 14+
- **tranche:** 3 (tax/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- Live `returnCountOnly` + sample attribute queries against NCOneMap Parcels, Public_Access, OpenGov, WarehouseServices/Zoning (per muni), Planning County Zoning, SmartGov_parcels, Municipalities, NC OneMap `cntyfips='027'`, Hickory FLU; AppraisalCard PDF cross-check; Caldwell.js deep-link wiring; geo-check centroid in Caldwell.
