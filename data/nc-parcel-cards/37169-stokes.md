# Stokes County, NC — GIS County Card

## Summary

Stokes County (Winston-Salem MSA, FIPS **37169**) publishes a solid **public** ArcGIS MapServer stack at `stokescountygis.com` (Enterprise 11.5). **Wire-first parcels:** `AllLayers/MapServer/24` (**Parcel Layer**) — ~**32,127** polygons with owner, mailing, **situs**, acreage, **land/building/total assessed**, parcel `ZONING`, deed date, and **PACKAGE_SALE_PRICE / LAND_SALE_PRICE**. ~**8,865** with `CALCULATED_ACREAGE` 5–150 (~**3,633** with `TOTAL_BLDG_VAL_ASSESSED=0`; **4,718** `LAND_CLASS='VACANT'` in range). **Zoning** is municipality-aware on one countywide layer (`ZONE_AREA` / `ZONING_JURI`: County, King, Walnut Cove, Danbury). **FLU:** Land Use 2035 (`LUP_CODE`/`LUP_DESC`) covers county + all three munis. **City of King** has local WebGIS (`webgis.net` `NC/CityOfKing`) — prefer for King-side QA; county zoning/parcels remain authoritative countywide. **NC OneMap** (`cntyfips='169'`) is a solid fallback. **No FeatureServer SOE** on county host (MapServer query only). Main gaps: interactive map-viewer homepage is a stub (no stable webappviewer id found); Walnut Cove / Danbury have **no independent** public zoning REST; `PACKAGE_SALE_PRICE>0` on only ~**10,143** parcels.

## Portals

- **Stokes County GIS** — https://www.stokescountygis.com/ — REST directory live; **homepage HTML is a broken stub** (verified 2026-09-23)
- **County ArcGIS REST** — https://stokescountygis.com/server/rest/services
- **Property search (NCPTS)** — https://lrcpwa.ncptscloud.com/stokes/parcel-search — Deep link: `https://lrcpwa.ncptscloud.com/stokes/parcel-detail/{PARCEL_PK}`
- **NCPTS (alt case)** — https://lrcpwa.ncptscloud.com/Stokes/
- **Tax Administration** — https://www.co.stokes.nc.us/departments/tax_administration.php
- **Tax pay portal** — https://www.stokescountytax.com/#/
- **Planning** — https://www.co.stokes.nc.us/departments/planning.php
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)
- **City of King WebGIS** — https://www.webgis.net/nc/cityofking/
- **City of King REST** — https://www.webgis.net/arcgis/rest/services/NC/CityOfKing/MapServer
- **Town of Walnut Cove Planning** — https://townofwalnutcove.org/government/planning_and_zoning_board.php — Zoning ordinance / map (PDF; no town REST)
- **Town of Danbury** — https://townofdanbury.org/ — No public ArcGIS REST verified

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `PIN_12D`, `PARCEL_PK`, `REID`, `PARCEL_NUMBER`; OneMap `parno` | Prefer `PIN` (10-digit); `PARCEL_PK` for NCPTS deep link; `parno`↔`PIN` |
| polygons | Yes | AllLayers/24 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALCULATED_ACREAGE`, `TOTAL_ACREAGE`, `ACREAGE`, `DEEDED_ACREAGE` | ~**8,865** CALC 5–150; prefer CALCULATED |
| ownerName | Yes | `PROPERTY_OWNER_1` (+ `_2`); OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `OWNER_MAIL_ADDR_1`–`3`, `_CITY`, `_STATE`, `_ZIP` | Structured |
| situs address | Yes | `PHYSICAL_ADDRESS` + `PHYS_ADDR_*` components / OneMap `siteadd` | **On primary parcel layer** |
| lastSale date/price | Partial | `PACKAGE_SALE_DATE`/`PACKAGE_SALE_PRICE`, `LAND_SALE_*`, `DEED_DATE`, `REVENUE_STAMP` | Price on ~**10.1k** parcels; use package then land; deed date always available |
| tax values | Yes | `TOTAL_LAND_VAL_ASSESSED`, `TOTAL_BLDG_VAL_ASSESSED`, `TOTAL_PROPERTY_VALUE`, deferred/use-value fields | **Land/improve split on primary** |
| zoning | Yes | Parcel `ZONING`; polygon `ZONING` + `ZONE_AREA`/`ZONING_JURI` | Prefer spatial zoning for authority |
| flu | Yes | `LUP_CODE`, `LUP_DESC` (Land Use 2035) | Spatial join; covers County/King/Walnut Cove/Danbury |
| appraiser / viewer link | Yes | NCPTS parcel-detail by PARCEL_PK | Map viewer deep-link **gap** (homepage stub) |

### ZONING_JURI / ZONE_AREA / PLANNING_JURIS codes

| Code / field value | Jurisdiction | Zoning layer notes (verified counts) |
|------|----------------|--------------------------------------|
| ZONE_AREA=`County` / ZONING_JURI=`RPO-COUNTY`+`MPO-COUNTY` | Stokes County (unincorporated) | Zoning **25,614** (RPO 19,917 + MPO 5,709) |
| ZONE_AREA=`King` / ZONING_JURI=`MPO-KING` | City of King | Zoning **6,066**; prefer town WebGIS for local QA |
| ZONE_AREA=`Walnut Cove` / ZONING_JURI=`RPO-WALNUT COVE` | Town of Walnut Cove | Zoning **2,346** — **county host only** |
| ZONE_AREA=`Danbury` / ZONING_JURI=`RPO-DANBURY` | Town of Danbury | Zoning **624** — **county host only** |
| PLANNING_JURIS=`STOKES` | Unincorporated | Parcels **23,900** |
| PLANNING_JURIS=`KING` | King planning | Parcels **5,485** |
| PLANNING_JURIS=`WALNUT COVE` | Walnut Cove planning | Parcels **2,111** |
| PLANNING_JURIS=`DANBURY` | Danbury planning | Parcels **427** |

Incorporated limits (`Inc_Muni`): **KING** (Stokes + Forsyth edge polygons), **WALNUT COVE**, **DANBURY**. Unincorporated places (Germanton, Pinnacle, Pine Hall, Lawsonville, Francisco, Westfield, Sandy Ridge, etc.) → **County** zoning / STOKES planning.

## Layers (verified)

### 1. AllLayers Parcel Layer — parcels + ownership + tax + situs + sale + zoning attr (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | situs | zoning (attr)
- **REST URL (wire-first):** https://stokescountygis.com/server/rest/services/AllLayers/MapServer/24
- **Alternate (same rich schema):** https://stokescountygis.com/server/rest/services/WebApp2026/MapServer/13 (Parcel for Orthos)
- **Also:** OperationalLayers/MapServer/24
- **Layer name / id:** Parcel Layer / 24
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN`, `PIN_12D` → parcelId
  - `PARCEL_PK` → NCPTS deep-link key
  - `REID`, `PARCEL_NUMBER` → alternate ids
  - `CALCULATED_ACREAGE`, `TOTAL_ACREAGE`, `ACREAGE`, `DEEDED_ACREAGE` → acreage
  - `PROPERTY_OWNER_1`, `PROPERTY_OWNER_2` → ownerName
  - `OWNER_MAIL_ADDR_1`–`3`, `_CITY`, `_STATE`, `_ZIP` → mailing
  - `PHYSICAL_ADDRESS`, `PHYS_ADDR_*` → situs
  - `PACKAGE_SALE_DATE`, `PACKAGE_SALE_PRICE`, `LAND_SALE_DATE`, `LAND_SALE_PRICE`, `DEED_DATE`, `REVENUE_STAMP` → lastSale
  - `TOTAL_LAND_VAL_ASSESSED`, `TOTAL_BLDG_VAL_ASSESSED`, `TOTAL_PROPERTY_VALUE`, `LAND_USE_VALUE`, deferred fields → tax
  - `ZONING`, `PLANNING_JURIS` → zoning / jurisdiction hint
  - `LAND_CLASS` → dorCode / land-use class (e.g. VACANT, SINGLE FAMILY RES)
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **32,127**; `CALCULATED_ACREAGE` 5–150 → **8,865**; bldg assessed =0 in range → **3,633**; VACANT in range → **4,718**; `PACKAGE_SALE_PRICE>0` → **10,143**; `TOTAL_PROPERTY_VALUE>0` → **30,941**; sample OK
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. **No FeatureServer** (SOE missing). Prefer over `Parcels/MapServer/2` (missing tax/sale). Prefer `PACKAGE_SALE_*` then `LAND_SALE_*`; `DEED_DATE` is deed not always sale.

### 2. Parcels/MapServer/2 — thinner parcels (no tax/sale)

- **Purpose:** parcels | ownership | situs | acreage
- **REST URL:** https://stokescountygis.com/server/rest/services/Parcels/MapServer/2
- **Verified:** yes — count **32,127**; acres 5–150 CALC **8,865**
- **Notes:** Same geometry/owner/situs as primary but **lacks** assessed values and sale price. Prefer AllLayers/24. ParcelsNew/2 similar thin schema.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parno` → parcelId (aligns with `PIN`)
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs
  - `gisacres` → acreage (~**8,847** in 5–150)
  - `saledate`,`saledatetx` → lastSale.date (**no sale price**)
  - `parval`,`landval`,`improvval` → tax
  - `cntyfips`=`169`, `cntyname` → Stokes filter
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — filter count **31,982**; gisacres 5–150 → **8,847**
- **Notes:** May lag county CAMA. MaxRecordCount **5000**. County primary already has land/improve — OneMap useful as FeatureServer fallback / cross-check.

### 4. County Zoning — municipal + county zoning (PRIMARY zoning stack)

- **Purpose:** zoning
- **REST URL (wire-first):** https://stokescountygis.com/server/rest/services/AllLayers/MapServer/27
- **Mirrors:** WebApp2026/MapServer/33; Baselayers/MapServer/17
- **Fields:** `ZONING`, `ZONING_JURI`, `ZONE_AREA`, `TOWNSHIP`, `EDIT_DATE`
- **WKID / CRS:** 102719 / 2264
- **Join to parcels:** spatial join (intersect/centroid) in 2264; route by `ZONE_AREA` or parcel `PLANNING_JURIS`; overlay parcel attr `ZONING` for QA
- **Verified:** yes — total **34,669**; by ZONE_AREA: County **25,614**, King **6,066**, Walnut Cove **2,346**, Danbury **624**
- **Notes:** Single layer covers all Stokes zoning authorities. King also on webgis.net (no separate zoning polygon layer — parcels carry `ZONING`).

### 5. Land Use 2035 — FLU (PRIMARY)

- **Purpose:** flu
- **REST URL:** https://stokescountygis.com/server/rest/services/WebApp2026/MapServer/34
- **Mirror:** https://stokescountygis.com/server/rest/services/Baselayers/MapServer/18
- **Fields:** `LUP_CODE`, `LUP_DESC`, `LUP_EFFDAT`, `ZONING_JUR`, `ZONE_AREA`, `TOWNSHIP`, `NAME`, `TYPE`
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **1,518**; by ZONING_JUR: COUNTY **1,058**, KING **207**, WALNUT COVE **158**, DANBURY **95**
- **Codes (top):** O-2 RESERVED LANDS/CONSERVATION (561), G-1 LOW DENSITY GROWTH (327), O-1 PRESERVED LANDS (251), G-2 CONTROLLED GROWTH (225), G-3A MIXED USE (77), G-4 DOWNTOWN (48), G-3B INDUSTRIAL (29)
- **Notes:** Spatial join to parcels (not PIN-keyed). Covers all three munis + county.

### 6. City Limits + County ETJ

- **City Limits:** https://stokescountygis.com/server/rest/services/AllLayers/MapServer/16 — `Inc_Muni`, `County`, `FTR_CODE`; count **23** (KING Stokes+Forsyth, WALNUT COVE, DANBURY)
- **County ETJ:** https://stokescountygis.com/server/rest/services/WebApp2026/MapServer/4 — `FTR_CODE` Danbury / Walnut Cove / KING ETJ; count **584**
- **Verified:** yes
- **Notes:** Use to route zoning/FLU joins; King has Forsyth-county Inc_Muni polygons (edge).

### 7. City of King Parcels — local host (prefer most local for King QA)

- **Purpose:** parcels | tax | ownership | situs | zoning (attr) — King area
- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/CityOfKing/MapServer/7
- **Viewer:** https://www.webgis.net/nc/cityofking/
- **Geometry:** Polygon; CRS **102719 / 2264**
- **Fields:** PIN, owner/mail/situs, acreage, ZONING, PLANNING_JURIS, land/bldg/total assessed, DEED_*, REID, PARCEL_PK — **no PACKAGE_SALE_PRICE**
- **Verified:** yes — count **4,302**; CALC acres 5–150 → **238**
- **Notes:** Prefer for King municipal QA; **county AllLayers/24** still primary for sale price + countywide. No separate King zoning FeatureServer — zoning polygons on county County Zoning (`ZONE_AREA='King'`).

## Municipalities (first-class)

County parcels are countywide; **zoning authority is municipal** (or County). Join pattern: start from AllLayers/24 (2264) → use parcel `ZONING`/`PLANNING_JURIS` quickly → spatial join County Zoning filtered by `ZONE_AREA` → FLU spatial join Land Use 2035.

### City of King (KING)

- **Zoning (county host — primary polygons):** AllLayers/27 where `ZONE_AREA='King'` / `ZONING_JURI='MPO-KING'` — count **6,066**; field `ZONING` (R-15, R-20, B-2, R-R, L-I, R-MF, …)
- **Zoning (attr on parcels):** county AllLayers/24 or King MapServer/7 `ZONING`
- **FLU:** Land Use 2035 where `ZONING_JUR='KING'` — **207**
- **Local GIS:** https://www.webgis.net/arcgis/rest/services/NC/CityOfKing/MapServer — Parcels/7 (**4,302**); City Boundary/1; **no dedicated zoning layer**
- **Join note:** Prefer county Zoning polygons for authority; King WebGIS for local parcel QA. City spans **Stokes + Forsyth** — filter `County='STOKES'` on City Limits / clip to FIPS 37169 when needed. Forsyth MapForsyth also has tiny KI edge (out of Stokes card scope unless dual-county).

### Town of Walnut Cove (WALNUT COVE)

- **Zoning:** county AllLayers/27 filter `ZONE_AREA='Walnut Cove'` — **2,346** (R-A, R-20, R-6, R-8, NB-1/2, B-1, I-1, …)
- **FLU:** Land Use 2035 `ZONING_JUR='WALNUT COVE'` — **158**
- **Local GIS:** **none verified** — planning page + zoning map PDF only
- **Join note:** Use county Zoning + FLU; ETJ polygons on WebApp2026/4 (`Walnut Cove`)

### Town of Danbury (DANBURY) — county seat

- **Zoning:** county AllLayers/27 filter `ZONE_AREA='Danbury'` — **624** (R-3, R-2, R-1, B-1, I-1, …)
- **FLU:** Land Use 2035 `ZONING_JUR='DANBURY'` — **95**
- **Local GIS:** **none verified** (townofdanbury.org)
- **Join note:** County Zoning + FLU; ETJ on WebApp2026/4 (`Danbury`)

### Stokes County unincorporated (STOKES / County)

- **Zoning:** `ZONE_AREA='County'` — **25,614** (dominated by R-A)
- **FLU:** Land Use 2035 `ZONING_JUR='COUNTY'` — **1,058**
- **Communities without municipal zoning authority:** Germanton, Pinnacle, Pine Hall, Lawsonville, Francisco, Westfield, Sandy Ridge, and similar — treat as County / STOKES

## Gaps

- **Interactive GIS viewer URL unpublished** — `stokescountygis.com` homepage returns a ~105-byte stub; no stable webappviewer/experience app id verified. Use NCPTS + REST.
- **No FeatureServer SOE** on county ArcGIS Server — MapServer query only; MaxRecordCount **2000**.
- **Walnut Cove / Danbury — no independent public ArcGIS REST** for zoning or FLU (county-hosted only; WC has PDF zoning map).
- **King local parcels lack sale-price fields** — use county AllLayers/24 for `PACKAGE_SALE_*`.
- **PACKAGE_SALE_PRICE sparse** (~10.1k / 32.1k); many parcels need `LAND_SALE_*` or deed-only.
- **OneMap has no sale price** (date only); may lag county.
- **King Forsyth-edge** parcels/limits — clip to Stokes when building county-only extracts.
- **Owner phones/emails** not collected (do not scrape NCPTS PII beyond public REST fields).
- **No paid vendor data** used (CoreLogic/Regrid/ATTOM avoided).

## Hand-off notes for Land Search Builder

1. **Wire first:** `AllLayers/MapServer/24` — polygons + owner, mailing, **situs**, acreage, land/bldg/total assessed, ZONING, PACKAGE/LAND sale, DEED_DATE. Filter `CALCULATED_ACREAGE BETWEEN 5 AND 150` (~8.9k). Optional vacant-ish: `LAND_CLASS='VACANT'` (~4.7k in range) or `TOTAL_BLDG_VAL_ASSESSED=0` (~3.6k).
2. **Zoning:** parcel `ZONING` for fast attr; authoritative spatial join AllLayers/27 by `ZONE_AREA`. For King prefer county King filter; town WebGIS has no zoning polygons.
3. **FLU:** spatial-join WebApp2026/34 (`LUP_CODE`/`LUP_DESC`); filter `ZONING_JUR` for muni.
4. **Sales:** prefer `PACKAGE_SALE_PRICE` when >0; else `LAND_SALE_PRICE`; else deed date only.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='169'` (FeatureServer).
6. **Viewer / appraiser links:**
   - NCPTS detail: `https://lrcpwa.ncptscloud.com/stokes/parcel-detail/{PARCEL_PK}`
   - Search: `https://lrcpwa.ncptscloud.com/stokes/parcel-search`
7. **Join keys:** `PIN` (preferred), `PARCEL_PK`, `REID`, `PIN_12D`, OneMap `parno`↔`PIN`.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities/towns are first-class:** never treat County Zoning alone without `ZONE_AREA` routing — King / Walnut Cove / Danbury have distinct district sets.

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='STOKES'`, field `AADT_2022` (string) — **371 stations live**, 136 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27STOKES%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27STOKES%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Stokes'`, `AADT_2025` (int) — 370 stations; 214 with 2025, 223 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://stokescountygis.com/server/rest/services/AllLayers/MapServer/24` — total 32131, 5–150 ac 8866 (`CALCULATED_ACREAGE>=5 AND CALCULATED_ACREAGE<=150`).
- Non-zero county: `TOTAL_LAND_VAL_ASSESSED` 31874, `TOTAL_BLDG_VAL_ASSESSED` 21911, `TOTAL_PROPERTY_VALUE` 30939; in 5–150: `TOTAL_PROPERTY_VALUE` 8663. **Status: ok.**
- Integer fields; TOTAL_PROPERTY_VALUE assessed.

### 3. Sale history
- Price `PACKAGE_SALE_PRICE`>0 10147, `LAND_SALE_PRICE`>0 5260 (5–150: 1628); date non-null `PACKAGE_SALE_DATE` 12722, `DEED_DATE` 31934. **Status: ok.**
- PACKAGE_SALE_DATE esriDate is sparse (12,722); DEED_DATE is near-complete (31,934) — use DEED_DATE as fallback date. PACKAGE_SALE_PRICE primary; LAND_SALE_PRICE secondary.

### 4. Owner entity
- Owner fields: `PROPERTY_OWNER_1`, `PROPERTY_OWNER_2`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 786** (of 8801 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: `https://lrcpwa.ncptscloud.com/stokes/parcel-detail/{PARCEL_PK}`
- Tested `https://lrcpwa.ncptscloud.com/stokes/parcel-detail/29818` → **200**. HTTP 200; NCPTS PWA shell (client-rendered; not server-verifiable).

### 6. Jurisdiction GIS viewer
- `https://www.stokescountygis.com/maps/` → **200**. stokescountygis.com meta-refreshes to /maps/ (200)

### Pass2 gaps
- PACKAGE_SALE_DATE sparse (12,722 of 32,131) — use DEED_DATE fallback
- AADT_2022 blank at 235 of 371 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- No multi-transfer sale history on primary layer (last sale only)
