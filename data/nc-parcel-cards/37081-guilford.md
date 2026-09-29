# Guilford County, NC — GIS County Card

## Summary

Guilford County (Greensboro / Winston-Salem MSA footprint, FIPS **37081**, slug **guilford**) publishes rich cadastral REST at `gcgis.guilfordcountync.gov`. **Wire-first parcels:** **GC_Parcels** FeatureServer/0 — ~**223.2k** polygons with owner, mailing, **situs** (LOCATION_ADDR + PHYADDR_*), acreage, land/bldg assessed split, package & land sale fields, zoning attribute, and NCPTS `WHITE_CARD_URL` / parcel-detail by `PARCEL_PK`. ~**12,978** with `CALCULATED_ACRES` 5–150 (~**5,523** with building value 0/null). **Zoning:** prefer **city hosts inside Greensboro / High Point**; county **Combined_Zoning** (~6.6k, jurisdiction-coded) for Summerfield, Oak Ridge, Stokesdale, Jamestown, Pleasant Garden, Sedalia, Whitsett, Gibsonville tip, Burlington tip, and unincorporated. **FLU:** county **FLUM** (~50k; REID-joinable) + Greensboro CompPlan2040 Map 7 / Place Types + High Point Place Types. **NC OneMap** (`cntyfips='081'`) is a solid fallback. Markets: **Winston-Salem**, **Greensboro**.

## Portals

- **GIS Data Viewer** — https://gisdv.guilfordcountync.gov/Guilford/
- **County ArcGIS REST** — https://gcgis.guilfordcountync.gov/arcgis/rest/services
- **Property search (NCPTS)** — https://lrcpwa.ncptscloud.com/guilford/parcel-search — Deep link: `https://lrcpwa.ncptscloud.com/guilford/parcel-detail/{PARCEL_PK}`
- **White card attachment** — `https://lrcpwa.ncptscloud.com/guilford/CustomAttachmentsResource.ashx?parcelPk={PARCEL_PK}` (also on parcel field `WHITE_CARD_URL`)
- **Tax CAMA redirect** — https://taxcama.guilfordcountync.gov/ → NCPTS
- **Parcel research builder** — https://parcelresearch.guilfordcountync.gov/
- **City of Greensboro GIS** — https://gis.greensboro-nc.gov/arcgis/rest/services — Zoning_MS + CompPlan2040_MS
- **City of High Point GIS** — https://gisentapp01.highpointnc.gov/server/rest/services — Zoning + Planning (Place Types)
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)
- **County planning jurisdictions page** — https://www.guilfordcountync.gov/government/departments-and-agencies/planning-and-development/jurisdictions-within-guilford-county

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `PIN_PLUS_EXT`, `PARCEL_PK`, `REID`, `GEOPIN`; OneMap `parno` | Prefer `PIN` (10-digit); `PARCEL_PK` for NCPTS deep link |
| polygons | Yes | GC_Parcels FS/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALCULATED_ACRES`, `ACREAGE`, `TOTAL_ACRES` | ~**12,978** CALC 5–150; ~**12,973** ACREAGE; ~**12,820** TOTAL |
| ownerName | Yes | `PROPERTY_OWNER` / `PROP_OWNER1_FULLNAME` (+ owner2); OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `OWNER_MAIL_1` + city/state/zip fields | Structured (not combined line) |
| situs address | Yes | `LOCATION_ADDR` / `PHYADDR_*` / `CITY` | **On primary parcel layer** |
| lastSale date/price | Partial | `PKG_SALE_*`, `LAND_SALE_*`, `DEED_DATE` | Last sale on parcel; PKG>0 in ~3.6k of 5–150; no multi-xfer SalesApp |
| tax values | Yes | `TOTAL_PROP_VALUE`, `TOTAL_LAND_VALUE_ASSESSED`, `TOTAL_BLDG_VALUE_ASSESSED` | **Has land/improve split** on primary |
| zoning | Yes | Parcel `ZONING`; Combined `ZONING`+`JURISDICTION`; GSO `ZONINGDISTRICT`; HP `ZONE` | Prefer city hosts inside GSO/HP |
| flu | Yes (partial) | County `FLUM_New`; GSO `DISTRICT` (Map7/PlaceTypes); HP `PlaceTypes` | Small towns via county FLUM |
| appraiser / viewer link | Yes | NCPTS parcel-detail / WHITE_CARD_URL; GISDV viewer | Templates below |

### Combined_Zoning JURISDICTION (verified counts)

| Jurisdiction | Zoning polygons | Notes |
|--------------|-----------------|-------|
| GREENSBORO | **2,949** | Prefer city Zoning_MS/7 (**3,248**) inside city |
| GUILFORD COUNTY | **1,720** | Unincorporated |
| HIGH POINT | **746** | Prefer city Zoning/0 (**781**); spans Forsyth tip |
| SUMMERFIELD | **242** | No town REST — Combined primary; PDF map on town site |
| GIBSONVILLE | **206** | Independent planning; Combined stub |
| OAK RIDGE | **179** | County Combined primary |
| (null) | **165** | QA / unclassified |
| STOKESDALE | **117** | Also GISDV **127**; county planning services |
| PLEASANT GARDEN | **62** | GISDV **62**; county planning services |
| JAMESTOWN | **50** (+ ETJ **22**) | County Combined |
| BURLINGTON | **33** | Alamance tip only |
| ARCHDALE | **25** | Randolph tip |
| KERNERSVILLE | **25** | Forsyth tip — prefer Forsyth/Kernersville card |
| SEDALIA | **22** | GISDV **28**; county planning services |
| WHITSETT | **1** | **Gap on Combined** — use GISDV Zoning **43** |

### GISDV Zoning only (county + small towns)

| JURISDICTION | Count |
|--------------|-------|
| GUILFORD | 1819 |
| STOKESDALE | 127 |
| PLEASANT GARDEN | 62 |
| WHITSETT | 43 |
| SEDALIA | 28 |

Does **not** include Greensboro, High Point, Summerfield, Oak Ridge, or Jamestown.

### Parcel CITY distribution (municipality inventory)

| CITY (parcel attr) | Approx parcels |
|--------------------|----------------|
| Greensboro | 106,284 |
| (null / unincorporated) | 50,370 |
| High Point | 43,919 |
| Summerfield | 4,975 |
| Oak Ridge | 4,016 |
| Stokesdale | 3,564 |
| Gibsonville | 3,183 |
| Pleasant Garden | 2,351 |
| Jamestown | 2,081 |
| Burlington | 836 |
| Sedalia | 587 |
| Whitsett | 449 |
| PTI Airport | 312 |
| Archdale | 216 |
| Kernersville | 81 |

## Layers (verified)

### 1. GC_Parcels — parcels + ownership + tax + situs + sale + zoning attr (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last package/land) | situs | zoning (attr)
- **REST URL (wire-first):** https://gcgis.guilfordcountync.gov/arcgis/rest/services/GC_Cadastral_Current/GC_Parcels/FeatureServer/0
- **Mirror:** …/GC_Cadastral_Current/Parcels_Ownership/FeatureServer/0 (same count)
- **Layer name / id:** GC_Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` / `PIN_PLUS_EXT` / `GEOPIN` → parcelId
  - `PARCEL_PK` → NCPTS deep-link key
  - `REID` / `REID_TRIM` → alternate account id (join to FLUM)
  - `CALCULATED_ACRES`, `ACREAGE`, `TOTAL_ACRES`, `DEEDED_ACRES` → acreage
  - `PROPERTY_OWNER`, `PROP_OWNER1_FULLNAME`, `PROP_OWNER2_FULLNAME` → ownerName
  - `OWNER_MAIL_1`…`OWNER_MAIL_ZIP` → mailing
  - `LOCATION_ADDR`, `PHYADDR_*`, `CITY` → situs
  - `PKG_SALE_DATE`/`PKG_SALE_PRICE`, `LAND_SALE_*`, `DEED_DATE`, `DEED_BOOK`/`DEED_PAGE`, `REVENUE_STAMPS` → lastSale
  - `TOTAL_PROP_VALUE`, `TOTAL_LAND_VALUE_ASSESSED`, `TOTAL_BLDG_VALUE_ASSESSED`, `LAND_USE_VALUE` → tax
  - `ZONING` → zoning (attribute; often includes description text)
  - `LAND_CLASS` → local use / dor-like class
  - `WHITE_CARD_URL` → appraiser attachment URL
  - `HEATED_AREA`, `YEAR_BUILT` → improvement hints
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **223,245**; `CALCULATED_ACRES` 5–150 → **12,978**; `ACREAGE` 5–150 → **12,973**; BLDG=0/null in range → **5,523**; PKG_SALE_PRICE>0 in range → **3,588**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. Prefer `CALCULATED_ACRES` for GIS acres. Spatial zoning join still recommended for jurisdiction-aware districts.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Key fields:** `parno`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`/`scity`, `gisacres`, `saledate`, `parval`/`landval`/`improvval`, `cntyfips`=`081`
- **Verified:** yes — filter count **222,443**; gisacres 5–150 → **12,953**; improvval=0/null in range → **5,491**
- **Notes:** Fallback when county host flaky. No sale price. MaxRecordCount **5000**.

### 3. Combined_Zoning — multi-jurisdiction zoning (PRIMARY zoning stack)

- **Purpose:** zoning
- **REST URL:** https://gcgis.guilfordcountync.gov/arcgis/rest/services/Planning_Zoning/Combined_Zoning/FeatureServer/0
- **Fields:** `ZONING`, `BASE_ZONING`, `CLASSIFICATION`, `JURISDICTION`, `New_Zoning_UDO2020`, `CODE`, `DESCRIPTION`
- **WKID / CRS:** 102719 / 2264
- **Join to parcels:** spatial join (intersect/centroid) in 2264; route by `JURISDICTION` or City Limits `CITY_NAMES`
- **Verified:** yes — total **6,569** (see jurisdiction table)
- **Notes:** Single layer covers all Guilford munis with zoning polygons. Prefer Greensboro/High Point city hosts inside city limits. Overlay with parcel `ZONING` for QA.

### 4. GISDV Zoning — county + Stokesdale / Pleasant Garden / Whitsett / Sedalia

- **REST URL:** https://gcgis.guilfordcountync.gov/arcgis/rest/services/GISDV/Zoning/FeatureServer/0
- **Verified:** count **2,079**
- **Notes:** Best **Whitsett** coverage (43 vs Combined 1). Not countywide for GSO/HP/Summerfield/Oak Ridge/Jamestown.

### 5. Greensboro Zoning Districts (prefer inside Greensboro)

- **REST URL:** https://gis.greensboro-nc.gov/arcgis/rest/services/Planning/Zoning_MS/MapServer/7
- **Fields:** `ZONINGDISTRICT`, `ZONINGDISTRICTTITLE`, `CATEGORY`, `ACREAGE`, `LINK`
- **Verified:** count **3,248**
- **CRS:** **102100 / 3857** — reproject before overlay with county 2264 parcels
- **Notes:** Also on DevelopmentServices_MS layer 35 (same count).

### 6. High Point Zoning (prefer inside High Point)

- **REST URL:** https://gisentapp01.highpointnc.gov/server/rest/services/Zoning/MapServer/0
- **Fields:** `ZONE`, `DIST`, `FILENAME`, `CASE_No`
- **Verified:** count **781**
- **CRS:** 102719 / 2264
- **Notes:** Citywide (Guilford + Forsyth tip) — clip as needed. Mentioned on Forsyth card for tip.

### 7. Planning_Zoning FLUM — county Future Land Use (PRIMARY county FLU)

- **Purpose:** flu
- **REST URL:** https://gcgis.guilfordcountync.gov/arcgis/rest/services/Planning_Zoning/FLUM/FeatureServer/0
- **Fields:** `REID`, `PIN_PLUS_E`, `FLUM_New`, `DW_FLUM`, `FLUM`, `DW_Acres`
- **Verified:** count **50,097**; DW_Acres 5–150 → **5,414**
- **Join:** attribute-join `REID`↔`GC_Parcels.REID` (or `PIN_PLUS_E`↔`PIN_PLUS_EXT`)
- **Notes:** Top categories Residential / Working Farm-Agriculture / Rural Residential. Prefer GSO CompPlan / HP Place Types inside those cities.

### 8. Greensboro CompPlan2040 — Future Land Use + Place Types

- **Future Land Use (Map 7):** https://gis.greensboro-nc.gov/arcgis/rest/services/Planning/CompPlan2040_MS/MapServer/1 — field `DISTRICT`; count **761**
- **Place Types:** …/CompPlan2040_MS/MapServer/9 — `DISTRICT`, `TAG`, `Acres`; count **998**
- **CRS:** 3857
- **Notes:** Prefer most-local FLU for Greensboro.

### 9. High Point Place Types

- **REST URL:** https://gisentapp01.highpointnc.gov/server/rest/services/Planning/MapServer/29
- **Fields:** `PlaceTypes`, `PT_All`, `ACRES`
- **Verified:** count **68** (coarse)
- **Notes:** Existing Land Use layer 30 is existing-use (~266k), not FLU.

### 10. City Limits + ETJ

- **City Limits:** https://gcgis.guilfordcountync.gov/arcgis/rest/services/CityLimits/FeatureServer/0 — field `CITY_NAMES`
- **ETJ:** https://gcgis.guilfordcountync.gov/arcgis/rest/services/GISDV/Extra_Territorial_Jurisdictions/FeatureServer/0 — `NAME` (Greensboro / High Point / Jamestown / Oak Ridge / Gibsonville ETJ observed)

## Cities / towns first-class routing

| Muni | Prefer for zoning | Prefer for FLU | Parcel host |
|------|-------------------|----------------|-------------|
| Greensboro | City Zoning_MS/7 | CompPlan2040 Map7 + Place Types | GC_Parcels (countywide CAMA) |
| High Point | City Zoning/0 | Place Types/29 | GC_Parcels |
| Summerfield | Combined_Zoning SUMMERFIELD | County FLUM | GC_Parcels |
| Oak Ridge | Combined_Zoning OAK RIDGE | County FLUM | GC_Parcels |
| Stokesdale | Combined or GISDV | County FLUM | GC_Parcels |
| Jamestown (+ETJ) | Combined JAMESTOWN* | County FLUM | GC_Parcels |
| Pleasant Garden | Combined / GISDV | County FLUM | GC_Parcels |
| Sedalia | Combined / GISDV | County FLUM | GC_Parcels |
| Whitsett | **GISDV Zoning** (not Combined) | County FLUM | GC_Parcels |
| Gibsonville | Combined_Zoning | County FLUM | GC_Parcels |
| Burlington tip | Combined (or Alamance city) | — | GC_Parcels tip only |
| Archdale tip | Combined (or Randolph) | — | tip only |
| Kernersville tip | Forsyth/Kernersville card | Forsyth/KE | tip only |
| Unincorporated | Combined GUILFORD COUNTY / GISDV GUILFORD | County FLUM | GC_Parcels |

County planning services (per county site): Whitsett, Sedalia, Stokesdale, Pleasant Garden (+ unincorporated). County permitting contracts also cover Jamestown, Oak Ridge, PTI. Independent: Greensboro, High Point, Archdale, Burlington, Gibsonville; Summerfield has own planning but uses county GIS viewer / PDF maps.

## Gaps

- **Small towns lack dedicated public FeatureServers** — Combined_Zoning / GISDV Zoning stubs only; Summerfield PDF zoning map, no town REST.
- **Combined_Zoning WHITSETT = 1** — use GISDV Zoning Whitsett (**43**).
- **Burlington / Archdale / Kernersville tips** — edge fragments only; prefer home-county city cards for core of those cities.
- **No multi-transfer sales history REST** (no Forsyth-style SalesApp) — last `PKG_SALE_*` / `LAND_SALE_*` on parcel; Hosted CommercialSales is commercial-only (~7.3k).
- **Greensboro zoning/FLU CRS is 3857** — reproject to 2264 for parcel overlay.
- **GISDV Zoning is not countywide** — excludes GSO/HP/Summerfield/Oak Ridge/Jamestown.
- **FLUM source spelling** includes “Industrial Inovation”.
- **Owner phones/emails** not collected (do not scrape NCPTS PII beyond public REST fields).
- **MaxRecordCount 2000** on GC_Parcels / Combined_Zoning — paginate.
- **No paid vendor data** used; **no AADT / utilities dig** in this card.

## Hand-off notes for Land Search Builder

1. **Wire first:** `GC_Parcels/FeatureServer/0` — polygons + owner, mailing, **situs**, acreage, land/bldg tax, PKG/LAND sale, ZONING attr, WHITE_CARD_URL. Filter `CALCULATED_ACRES BETWEEN 5 AND 150` (~13.0k). Optional vacant-ish: `TOTAL_BLDG_VALUE_ASSESSED = 0 OR IS NULL` (~5.5k in range).
2. **Zoning:** parcel `ZONING` for fast attr; authoritative spatial join **Combined_Zoning** by `JURISDICTION`. Inside Greensboro → Zoning_MS/7; inside High Point → Zoning/0. Whitsett → GISDV Zoning.
3. **FLU:** attribute-join county FLUM on `REID`; Greensboro → CompPlan2040/1 (+ Place Types/9); High Point → Place Types/29.
4. **Sales:** use `PKG_SALE_PRICE`/`LAND_SALE_PRICE` on parcel; no full transfer history REST.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='081'`.
6. **Viewer / appraiser links:**
   - NCPTS detail: `https://lrcpwa.ncptscloud.com/guilford/parcel-detail/{PARCEL_PK}`
   - Search: `https://lrcpwa.ncptscloud.com/guilford/parcel-search`
   - White card: `https://lrcpwa.ncptscloud.com/guilford/CustomAttachmentsResource.ashx?parcelPk={PARCEL_PK}`
   - GIS Data Viewer: `https://gisdv.guilfordcountync.gov/Guilford/`
7. **Join keys:** `PIN` (preferred), `PIN_PLUS_EXT`, `PARCEL_PK`, `REID`, OneMap `parno`↔`PIN_PLUS_EXT`.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities/towns are first-class:** never treat GISDV Zoning alone as countywide coverage.

verifiedAt: **2026-09-24** · verifiedBy: **North Carolina Public Info Researcher**


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://gcgis.guilfordcountync.gov/arcgis/rest/services/GC_Cadastral_Current/GC_Parcels/FeatureServer/0 polygons load (sample centroid [-80.0456, 35.921]); `PIN` filled on 223,240 of 223,244; `CALCULATED_ACRES` 5–150 ac **12,978**.
- **Attribute layer for Pass 2:** https://gcgis.guilfordcountync.gov/arcgis/rest/services/GC_Cadastral_Current/GC_Parcels/FeatureServer/0 · id `PIN` · live count **223,244** · 5–150 ac **12,978** (`CALCULATED_ACRES >= 5 AND CALCULATED_ACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='GUILFORD'` gives **1995** stations (297 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27GUILFORD%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Guilford'` gives **2053** stations (1799 with AADT_2025, 381 with AADT_2024, 1856 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Guilford%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `TOTAL_PROP_VALUE` non-zero **207,940**, `TOTAL_LAND_VALUE_ASSESSED` non-zero **214,758**
- **Sale history (ok):** price `PKG_SALE_PRICE` >0 **158,908**; date `PKG_SALE_DATE` non-null **158,992**
- **Owner entity:** field `PROPERTY_OWNER`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **4,630** (all parcels: 51,482), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://lrcpwa.ncptscloud.com/guilford/parcel-detail/{PARCEL_PK}`. Tested `99842` (https://lrcpwa.ncptscloud.com/guilford/parcel-detail/99842) → HTTP **200** (text/html), content verified: False. NCPTS SPA shell (200, 496 B, client-rendered): parcel content cannot be checked server-side. WHITE_CARD_URL (CustomAttachmentsResource.ashx?parcelPk=) also returns the 496 B shell.
- **Jurisdiction GIS viewer:** https://gisdv.guilfordcountync.gov/Guilford/ → HTTP **200** (GIS Data Viewer)
- **Municipal zoning/FLU layers re-checked:** 10 of 10 answer.
- **Pass 2 gaps:** PA content not verifiable (SPA)
