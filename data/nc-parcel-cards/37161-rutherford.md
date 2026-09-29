# Rutherford County, NC — GIS County Card

## Summary

Rutherford County (Asheville / Charlotte shed, FIPS **37161**, slug **rutherford**, `cntyfips='161'`) publishes a strong public ArcGIS stack at **`gis.rutherfordcountync.gov`**. **Wire-first parcels + CAMA:** `Addressing/MapServer/2` — ~**57,442** polys with `Parcel_Number`/`PIN`/`ParcelID`, owner, mailing, situs, `Acreage`/`Deeded_Acreage`, land/bldg/total assessed values, **`Sale_Price`**, **`Package_Sale_Date`/`Package_Sale_Price`**, **`Land_Sale_Date`/`Land_Sale_Price`**, parcel `Zoning` + `Planning_Jurisdiction`, `City` tax district. ~**11,199** with acres 5–150 (~**4,769** with `Sale_Price>0` in range). Twin CAMA on `EnerGov/EnerGov/FeatureServer/3` (~**57,838**) and `TemplateSite/SearchableLayers/MapServer/1`. **Cities-first zoning:** `NewLayers/MapServer/22` City Zoning (~**462**) — Forest City (+ ETJ), Rutherfordton, Spindale, Lake Lure (`ZONE_CODE`/`CITY`/`LR_ZONING`). Unincorporated mostly `Zoning='NONE'` (unzoned). **FLU:** PDF-only (Forest City Comp LUP; Lake Lure Comp Plan maps) — **no public FLU FeatureServer**. **PA deep-link:** `https://lrcpwa.ncptscloud.com/rutherford/parcel-detail?YearFor=2010&REID={Parcel_Number}` (county GIS Templates.htm; `REID` param = tax `Parcel_Number`). Alt SPA: `…/parcel-detail/{id}`. **Jurisdiction GIS:** `https://gis.rutherfordcountync.gov/maps/` — deep link `…/maps/default.htm?pin={Parcel_Number}` (query maps `Parcel_Number`). **NC OneMap** `cntyfips='161'` geometry/owner/tax fallback (`parno`↔`Parcel_Number`, `altparno`↔`PIN`; no sale price; saledate empty). Markets: **[Asheville, Charlotte]**.

## Portals

- **Jurisdiction GIS (Map Viewer)** — https://gis.rutherfordcountync.gov/maps/ — Deep link: `https://gis.rutherfordcountync.gov/maps/default.htm?pin={Parcel_Number}`
- **County GIS department** — https://www.rutherfordcountync.gov/departments/planning/gis.php
- **County Planning** — https://www.rutherfordcountync.gov/departments/planning/
- **County ArcGIS REST** — https://gis.rutherfordcountync.gov/server/rest/services
- **PA / NCPTS Property Record Card** — https://lrcpwa.ncptscloud.com/Rutherford/ — Deep link: `https://lrcpwa.ncptscloud.com/rutherford/parcel-detail?YearFor=2010&REID={Parcel_Number}`
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/Rutherford/parcel-search
- **Find & Pay Taxes (collections)** — https://www.rutherfordcountync.gov/tax_search/index.php#/
- **Tax / Assessor** — https://www.rutherfordcountync.gov/departments/revenue_department_tax_administrator/
- **Register of Deeds (Cott)** — https://cotthosting.com/NCRUTHERFORDEXTERNAL/LandRecords/protected/v4/SrchBookPage.aspx
- **Town of Forest City Planning** — https://www.townofforestcity.com/planning-code-enforcement/planning-zoning
- **Town of Rutherfordton Maps / Zoning** — https://www.rutherfordton.net/maps/
- **Town of Lake Lure Comp Plan Maps** — https://www.townoflakelure.com/bc-zoning/page/comprehensive-plan-maps-0
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='161'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `Parcel_Number`; `PIN`; `ParcelID`; OneMap `parno`/`altparno` | Prefer **Parcel_Number** for PA/GIS deep-links; **PIN** geopin |
| polygons | Yes | Addressing/2; EnerGov FS/3; SearchableLayers/1; OneMap | CRS **102719 / 2264** |
| acreage | Yes | `Acreage`; `Deeded_Acreage`; OneMap `gisacres` | ~**11,199** in 5–150 |
| ownerName | Yes | `Property_Owner`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `Owner_Mailing_Address_*` | |
| situs address | Yes | `Physical_Address` / `Physical_Address_*` | |
| lastSale date/price | Yes | `Sale_Price`; `Package_Sale_*`; `Land_Sale_*`; Possible Sales `PRICE`/`SALE_DATE` | ~**28,893** Sale_Price>0; Possible Sales ~**17,519** |
| tax values | Yes | `Total_Property_Value`, `Total_Land_Value_Assessed`, `Total_Building_Value_Assessed` | Typed ints |
| zoning | Yes (cities-first) | NewLayers/22 `ZONE_CODE`/`CITY`; parcel `Zoning` attr | Route by `City` / spatial join; unincorp NONE |
| flu | Partial (PDF) | Forest City Comp LUP; Lake Lure Comp Plan maps | **No FLU REST** |
| appraiser / viewer link | Yes | NCPTS `REID={Parcel_Number}`; GIS `?pin=` | TRANCHE-3 |

### City tax-district → municipality (Addressing/2 parcel counts)

| City (tax) | Approx parcels | Zoning source (prefer) |
|------------|----------------|------------------------|
| *(null / unincorp)* | **40,379** | Unzoned (`Zoning='NONE'`) — no county zoning polygons |
| **LAKE LURE** | **5,065** | NewLayers/22 `CITY='LAKE LURE'` (~120 polys) |
| **FOREST CITY** | **4,768** | NewLayers/22 `CITY='FOREST CITY'` (~115) + `ETJ-FORESTCITY` (~29) |
| **SPINDALE** | **2,973** | NewLayers/22 `CITY='SPINDALE'` (~66) |
| **RUTHERFORDTON** | **2,587** | NewLayers/22 `CITY='RUTHERFORDTON'` (~129) |
| ELLENBORO | **572** | **Gap** — no City Zoning polys; parcel Zoning all NONE |
| CHIMNEY ROCK VILLAGE | **525** | **Gap** — essentially unzoned on REST (~3 non-NONE) |
| BOSTIC | **301** | **Gap** — no City Zoning polys |
| RUTH | **255** | **Gap** — essentially unzoned |

## Layers (verified 2026-09-24)

### 1. Addressing/Parcels — parcels + ownership + tax + sale (PRIMARY CAMA)

- **Purpose:** parcels | tax | ownership | sales | zoning attr
- **REST URL:** https://gis.rutherfordcountync.gov/server/rest/services/Addressing/MapServer/2
- **Layer name / id:** Parcels / 2
- **Geometry:** Polygon
- **Key fields → targets:**
  - `Parcel_Number` → parcelId (PA / GIS pin key)
  - `PIN` → parcelIdGeopin / OneMap altparno
  - `ParcelID` → parcelIdInternal
  - `MBL` → map-block-lot
  - `Acreage`, `Deeded_Acreage` → acreage
  - `Property_Owner` → ownerName
  - `Owner_Mailing_Address_*` → mailing
  - `Physical_Address`, `Physical_Address_*` → situs
  - `Sale_Price` → lastSale.price
  - `Package_Sale_Date`, `Package_Sale_Price` → lastSale (package; price is string)
  - `Land_Sale_Date`, `Land_Sale_Price` → lastSale (land-only)
  - `Deed_Date`, `Deed_Book`, `Deed_Page`, `Revenue_Stamp` → deed
  - `Total_Property_Value`, `Total_Land_Value_Assessed`, `Total_Building_Value_Assessed` → tax
  - `Zoning`, `Planning_Jurisdiction`, `City` → zoning router / tax district
  - `Land_Class`, `Township`, `Market_Area_ID` → land-use hints
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **57,442**; `Acreage` 5–150 → **11,199**; `Sale_Price>0` → **28,893** (in-range **4,769**); `Land_Sale_Price>0` → **9,859**; Package_Sale_Price non-empty/non-zero → **21,067**; `Total_Property_Value>0` → **54,346**; geo-check Parcel_Number `1010256` centroid ≈ **-81.82, 35.41** (Rutherford)
- **Notes:** **PRIMARY** for tax/sale/owner. MaxRecordCount **2000** — paginate. Prefer `Sale_Price` (typed int) over string `Package_Sale_Price` when both present.

### 2. EnerGov Parcel — FeatureServer CAMA twin

- **REST URL:** https://gis.rutherfordcountync.gov/server/rest/services/EnerGov/EnerGov/FeatureServer/3
- **MapServer twin:** …/EnerGov/EnerGov/MapServer/3
- **Verified:** count **57,838** — same attr family as Addressing/2
- **Notes:** Slightly higher count than Addressing/2; MaxRecordCount **1000**. Prefer Addressing/2 for wire unless FeatureServer needed.

### 3. TemplateSite/SearchableLayers Parcels + Possible Sales

- **Parcels:** https://gis.rutherfordcountync.gov/server/rest/services/TemplateSite/SearchableLayers/MapServer/1 — count **57,838** (same CAMA family)
- **Possible Sales (points):** …/SearchableLayers/MapServer/3 — `PARCELNUM`, `PRICE`, `SALE_DATE`, `SALE_TYPE`, `Deeded_Acreage`; count **17,547** (`PRICE>0` → **17,519**; acres 5–150 → **2,960**)
- **Notes:** Join sales on `PARCELNUM`↔`Parcel_Number`. Secondary sale history layer.

### 4. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='161'`
- **Fields:** `parno`,`altparno`,`ownname`,`mailadd`/`mcity`/`mstate`/`mzip`,`siteadd`,`gisacres`,`parval`/`landval`/`improvval`,`saledate` (empty here), `cntyfips`
- **Verified:** yes — **57,599**; `gisacres` 5–150 → **11,390**; `parval>0` → **54,929**; `saledate IS NOT NULL` → **0**
- **Notes:** No sale price; saledate unused. Join `parno`↔`Parcel_Number`, `altparno`↔`PIN` (verified `1010256` / `1661042179`).

### 5. NewLayers City Zoning — cities-first zoning (PRIMARY zoning)

- **REST URL:** https://gis.rutherfordcountync.gov/server/rest/services/NewLayers/MapServer/22
- **Alternate:** NewLayersII/MapServer/22 (same inventory)
- **Layer name / id:** City Zoning(check with town to confirm) / 22
- **Geometry:** Polygon
- **Key fields:** `ZONE_CODE`, `CITY`, `CO_NAME`, `LR_ZONING`, `LR_ETJ`, `Z_NUM`
- **Verified:** count **462**
- **By CITY:** Rutherfordton **129**; Lake Lure **120**; Forest City **115**; Spindale **66**; ETJ-FORESTCITY **29**; FORESTCITY typo stubs **3**
- **Sample codes:** FC R-6/R-8/R-15/C-1/C-2/C-3/M-1/OI/PRD; Rutherfordton SFR-1/2/3, CIV, MU-1/2, MS, RMST, C-74, C-221, IND, VSR; Spindale R-6/R-10/R-20, GC, HCI, NB, CC; Lake Lure R-1/R-1A/B/C/D, R-2/3/4, CG, CN, GU, LAKE, L-1
- **Notes:** County disclaimer — confirm with town. Prefer spatial join / `CITY` filter over parcel `Zoning` text for code hygiene. No independent municipal ArcGIS hosts found.

### 6. City Limits / Municipalities

- **NewLayers/3 City Limits** / **Addressing/3 Municipalities** — count **17** polys
- **Fields:** `MUNICIPALITY`, `TEXT_NAME`, `LR_CITY`, `ACRES`
- **Distinct:** Forest City, Rutherfordton, Spindale, Lake Lure, Ellenboro, Bostic, Ruth, Chimney Rock

### 7. EnerGov Forest City And ETJ Area

- **REST URL:** https://gis.rutherfordcountync.gov/server/rest/services/EnerGov/EnerGov/FeatureServer/2
- **Count:** **7** — `taxcode`/`dist_name` Forest City tax/ETJ districts (routing aid)

### 8. FLU — PDF only (gap for REST)

- **Forest City Comp LUP (2012):** https://www.townofforestcity.com/sites/default/files/uploads/adopted-comprehensive-lup-10-15-12.pdf
- **Lake Lure Comp Plan Maps:** https://www.townoflakelure.com/bc-zoning/page/comprehensive-plan-maps-0
- **Rutherfordton Official Zoning Map PDF:** https://www.rutherfordton.net/documents/official-zoning-map/
- **Notes:** No county or city FLU FeatureServer on public REST.

## Municipalities (cities-first)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| Unincorporated Rutherford | Parcel Zoning=NONE | ~40k | County | No | Unzoned mountain/rural pattern |
| **Forest City** | NewLayers/22 CITY=FOREST CITY (+ETJ) | 115+29 | No public FS | PDF Comp LUP | Largest trade center; ETJ layer present |
| **Rutherfordton** | NewLayers/22 | 129 | No public FS | Zoning PDF only | County seat; UDO districts |
| **Spindale** | NewLayers/22 | 66 | No | No | |
| **Lake Lure** | NewLayers/22 | 120 | No public FS | Comp Plan PDF maps | Resort zoning strong |
| Ellenboro | — | 0 | No | No | Zoning REST gap |
| Bostic | — | 0 | No | No | Zoning REST gap |
| Ruth | — | ~0 | No | No | Zoning REST gap |
| Chimney Rock Village | — | ~0 | No | No | Zoning REST gap |

## Gaps / caveats

- No public **FLU FeatureServer** (Forest City / Lake Lure PDF plans only)
- Unincorporated county **unzoned** on public REST (`Zoning='NONE'` ~39.9k)
- Ellenboro / Bostic / Ruth / Chimney Rock Village — **no City Zoning polygons**
- City Zoning layer labeled “check with town to confirm”
- OneMap `saledate` empty; no sale price on OneMap — prefer county `Sale_Price`
- NCPTS is SPA; Templates.htm deep-link uses query `REID={Parcel_Number}` (not GeoPIN); SPA also supports `parcel-detail/{internalId}`
- `Package_Sale_Price` is string — cast when filtering; prefer typed `Sale_Price`
- Addressing/2 count (57,442) slightly behind EnerGov/SearchableLayers/OneMap (~57.6–57.8k)
- Utilities and AADT intentionally excluded; no emails/phones/paid vendors

## License / attribution

Rutherford County GIS / Revenue (Tax) Administration; towns of Forest City, Rutherfordton, Spindale, Lake Lure where zoning used. Data for tax/reference — not a survey. Commercial resale subject to **NCGS 132-10**. Attribute Rutherford County GIS.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 12+
- Live `returnCountOnly` + sample attribute queries against Addressing/2, EnerGov FS/3, SearchableLayers/1+PossibleSales/3, NewLayers/22 City Zoning (per CITY), City Limits/3, EnerGov Forest City ETJ/2, NC OneMap `cntyfips='161'`, NCPTS Templates.htm `REID={Parcel_Number}` deep-link + GIS `default.htm?pin={Parcel_Number}`, geo-check centroid in Rutherford.
