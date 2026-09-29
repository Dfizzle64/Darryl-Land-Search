# Yadkin County, NC — GIS County Card

## Summary

Yadkin County (Winston-Salem MSA, FIPS **37197**, slug **yadkin**, `cntyfips='197'`) publishes a strong **public** ArcGIS REST stack at `gis.yadkincountync.gov`. **Wire-first parcels (TRANCHE-3):** `CountyGISmap/MapServer/1` — **~28,364** polygons with PIN, owner, mailing, **situs street**, GIS acres, land/building FMV + land ASV/use-value, **last sale amount + deed date + qualified code**, and pre-built **TAXCARD** deep link by `PARCEL_NO`. **~8,175** with `TOTAL_ACRES` 5–150 (~**3,793** with `BLDG_FMV_CURRENT=0`; ~**5,079** `DESCRIPTION='VACANT'`). **Zoning is municipal-first but county-hosted (cities-first):** separate MapServer layers for **Yadkinville / Jonesville / Boonville / East Bend** + County Zoning for unincorporated (no independent town ArcGIS hosts). **FLU:** **no public FeatureServer** — 2023 Comprehensive Land Use Plan + Future Land Use Map are **PDFs only**; MapServer “Land Use” (38) is crop/land-cover, not planning FLU. **NC OneMap** (`cntyfips='197'`) is a solid fallback with land/improve split (**saledate count 0**; no sale price). **PA:** Bitek `AppraisalCard.aspx?id={PARCEL_NO}/{TAX_YEAR}` (PDF verified) + NCPTS `{PIN}`/`{PARCEL_NO}`. **jurisdictionGisUrl:** https://gis.yadkincountync.gov/. Markets: **[Winston-Salem]**.

## Portals

- **Public GIS viewer (jurisdictionGisUrl)** — https://gis.yadkincountync.gov/
- **AGOL Web AppViewer** — https://yadkincounty.maps.arcgis.com/apps/webappviewer/index.html?id=1762d0186a0749569e53e66fae91eecd
- **County ArcGIS REST** — https://gis.yadkincountync.gov/arcgis/rest/services
- **County GIS department** — https://www.yadkincountync.gov/161/GIS
- **GIS Maps and Downloads** — https://www.yadkincountync.gov/306/GIS-Maps-and-Downloads
- **Tax Assessor / Collector** — https://www.yadkincountync.gov/206/Tax-Assessor-Collector
- **PA deep-link (AppraisalCard PDF)** — `https://www.bttaxpayerportal.com/ITSPublicYK/AppraisalCard.aspx?id={PARCEL_NO}/{TAX_YEAR}` (live `TAXCARD` uses **2027**)
- **Tax bill search** — https://www.bttaxpayerportal.com/ITSPublicYK/TaxBillSearch
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/yadkin/
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/yadkin/parcel-detail/{PIN}` (also try `{PARCEL_NO}`)
- **Planning** — https://www.yadkincountync.gov/163/Planning — 2023 Land Use Plan + FLUM PDFs
- **2023 Comprehensive Land Use Plan (PDF)** — https://www.yadkincountync.gov/DocumentCenter/View/5990/Yadkin-County-Comprehensive-Land-Use-Plan-2023-
- **2023 Future Land Use Map (PDF)** — https://www.yadkincountync.gov/DocumentCenter/View/6126/Future-Land-Use-Map-
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels filter `cntyfips='197'`
- **Town of Yadkinville (PRIMARY city / county seat)** — https://www.yadkinville.org/ — Planning/zoning ordinance; **no independent ArcGIS REST**
- **Town of Jonesville** — https://www.townofjonesvillenc.com/ — **no independent ArcGIS REST**
- **Town of Boonville** — https://www.boonvillenc.com/ — **no independent ArcGIS REST**
- **Town of East Bend** — https://www.eastbendnc.com/ — **no independent ArcGIS REST**

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `PARCEL_NO`; OneMap `parno`/`altparno` | Prefer 12-digit `PIN`; `PARCEL_NO` for TAXCARD/PA; OneMap `parno`↔`PIN`, `altparno`↔`PARCEL_NO` |
| polygons | Yes | CountyGISmap MapServer/1 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `TOTAL_ACRES`, `SUM_LAND_ACRES`; OneMap `gisacres` | **8,175** TOTAL 5–150; OneMap gisacres 5–150 → **8,163** |
| ownerName | Yes | `NAME1`+`NAME2` / OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `ADDRESS1`,`ADDRESS2`,`CITY`,`STATE`,`ZIP` | Owner mail — **not** situs city |
| situs address | Partial | `STREET_ADDRESS`; Addresses `full_addre`+`CITY`+`ZIP`; OneMap `siteadd` | Street on parcels; **no situs city/zip on parcel** — optional join to Addresses (~21.4k) |
| lastSale date/price | Yes | `SALES_AMT`, `DEED_DATE`, `QUALIFIED_CODE` | **12,488** with SALES_AMT>0 (**2,961** in 5–150); OneMap `saledate` count **0** |
| tax values | Yes | `LAND_FMV_CURRENT`,`LAND_ASV_CURRENT`,`LAND_LUV_CURRENT`,`BLDG_FMV_CURRENT`; OneMap `parval`,`landval`,`improvval` | No single TOTAL_* — sum land+bldg FMV for market |
| zoning | Yes (cities-first) | Yadkinville/44, Jonesville/43, Boonville/41, East Bend/42, County/40 | Spatial join; route by Town Limits / ETJ |
| flu | **Gap** | PDF FLUM only | MapServer/38 is cropland/land-cover — **not** planning FLU |
| appraiser / viewer link | Yes | `TAXCARD`; AppraisalCard `{PARCEL_NO}`; NCPTS; GIS viewer | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. CountyGISmap Parcels — parcels + ownership + tax + situs + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | situs (street)
- **REST URL (wire-first):** https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer/1
- **Mirror:** https://gis.yadkincountync.gov/arcgis/rest/services/WebsiteMap/MapServer/1 (same count/schema)
- **Layer name / id:** Parcels / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (12-digit NC-style)
  - `PARCEL_NO` → account / TAXCARD / PA key
  - `TOTAL_ACRES`, `SUM_LAND_ACRES` → acreage
  - `NAME1`, `NAME2` → ownerName
  - `ADDRESS1`, `ADDRESS2`, `CITY`, `STATE`, `ZIP` → mailing
  - `STREET_ADDRESS` → situs (street only)
  - `SALES_AMT`, `DEED_DATE`, `QUALIFIED_CODE`, `DEED_BOOK`/`DEED_PAGE` → lastSale
  - `LAND_FMV_CURRENT`, `LAND_ASV_CURRENT`, `LAND_LUV_CURRENT`, `BLDG_FMV_CURRENT` → tax
  - `TAXCARD` → appraiser URL (pre-built)
  - `DEEDLINK` → Register of Deeds document link
  - `DESCRIPTION`, `YEAR_BUILT`, `FINISHED_AREA`, `FIRE_DISTRICT`, `NEIGHBORHOOD`, `DISTRICT_CODE` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **28,364**; `TOTAL_ACRES` 5–150 → **8,175**; `BLDG_FMV_CURRENT=0` in 5–150 → **3,793**; `DESCRIPTION='VACANT'` in 5–150 → **5,079**; `SALES_AMT>0` → **12,488** (in 5–150 → **2,961**); `STREET_ADDRESS` non-null → **28,297**
- **Geo-check:** PIN `484400879441` / PARCEL_NO `112756` (41.1 ac, OFF OF HOWARD BRIDGE RD) ≈ **-80.861, 36.066**; TAXCARD → AppraisalCard PDF **200**
- **Notes:** **PRIMARY** wire-first (MapServer, CRS matches zoning). Auth **none**. MaxRecordCount **1000** — paginate. Prefer MapServer over FeatureServer tax_view (3857 + editing caps advertised). Filter junk deed stubs (`DEED_BOOK='@@@@@'`, `NAME1='UNKNOWN OWNER'`).

### 2. BASIC_LOOKUP2 / PARCEL_ROADS tax_view_fc — FeatureServer alternate

- **Purpose:** parcels | tax | ownership | sales | situs (street)
- **REST URLs:**
  - https://gis.yadkincountync.gov/arcgis/rest/services/BASIC_LOOKUP2/FeatureServer/2
  - https://gis.yadkincountync.gov/arcgis/rest/services/PARCEL_ROADS_ADDRESS_PTS/FeatureServer/2
- **Geometry:** Polygon
- **Schema:** Same CAMA fields as CountyGISmap/1
- **WKID / CRS:** 102100 / 3857
- **Verified:** yes — same CAMA schema/count family as MapServer/1
- **Notes:** Queryable with auth none; service advertises Create/Update/Delete — **prefer MapServer/1** for read-only 2264 joins to zoning. Use only if MapServer flaky.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | situs | sales (date text only)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='197'`
- **Key fields:** `parno`(=PIN), `altparno`(=PARCEL_NO), `ownname`, mail/site, `gisacres`, `parval`/`landval`/`improvval`, `saledatetx` (**`saledate` count 0**; **no sale price**)
- **Verified:** count **28,320**; gisacres 5–150 → **8,163**; sample saledatetx present without saledate
- **Notes:** Prefer county MapServer/1 for sales + TAXCARD. OneMap useful for portable land/improve split. MaxRecordCount **5000**. CRS 102719/2264.

### 4. Yadkinville Zoning (PRIMARY city — cities-first)

- **REST URL:** https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer/44
- **Fields:** `ZONE_CODE`, `ZONE`
- **Codes:** CB, CZ, HB, HI, LI, NB, OI, RH, RM, RMH, RO CD, RR (some `ZONE` labels conflict for same code — prefer `ZONE_CODE`)
- **Verified:** count **88**
- **CRS:** 102719 / 2264
- **Route:** YADKINVILLE / YADKINVILLE ETJ on Town Limits/45

### 5. Jonesville Zoning

- **REST URL:** https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer/43
- **Fields:** `ZONING`, `JONESVILLE` (often null)
- **Codes:** B-1, B-2, B-2CU, B-3, M-1, R-10, R-12, R-20, R-MH, R-MH-A
- **Verified:** count **2,236** (parcel-scale polygons)
- **Route:** JONESVILLE / JONESVILLE ETJ

### 6. Boonville Zoning

- **REST URL:** https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer/41
- **Fields:** `BOONVILLE_` (code), `BOONVILLE1` (name)
- **Codes:** CS, HC, M-1, R-10, R-15, RA
- **Verified:** count **97**
- **Route:** BOONVILLE / BOONVILLE ETJ

### 7. East Bend Zoning

- **REST URL:** https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer/42
- **Fields:** `ZONING_NO`, `ZONING_NAM`
- **Codes:** CS, HC, I, R1, R2, RMF
- **Verified:** count **50**
- **Route:** EAST BEND (no separate ETJ polygon on layer 45)

### 8. County Zoning — unincorporated

- **REST URL:** https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer/40
- **FeatureServer mirror:** https://gis.yadkincountync.gov/arcgis/rest/services/BASIC_LOOKUP2/FeatureServer/3 (3857; count **1,248**)
- **Fields:** `ZONING`, `ZONE_NAME`, `ACRES`, `NCPIN` (almost always null — **~3** non-null)
- **Codes:** AO-1, CB, CB-CD, CP, HB, MHP, MI-1, MI-2, RA, RG, RG-CD, RI, RL, RR, TZ
- **Verified:** count **1,248**
- **Join:** **spatial join** in 2264; do **not** rely on NCPIN
- **Notes:** County zoning **does not apply** inside town limits/ETJs — use Town Limits/45 to route.

### 9. Town Limits with ETJ — jurisdiction routing

- **REST URL:** https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer/45
- **Fields:** `NAME`
- **Verified names:** BOONVILLE, BOONVILLE ETJ, EAST BEND, JONESVILLE, JONESVILLE ETJ, YADKINVILLE, YADKINVILLE ETJ
- **Count:** **11** polygons

### 10. Addresses — situs city/zip enrichment (optional)

- **REST URL:** https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer/0
- **Also:** BASIC_LOOKUP2/FeatureServer/0
- **Fields:** `full_addre`, `number`, `street`, `CITY`, `ZIP`, `ADD_TYPE`, …
- **Verified:** count **21,437**
- **Notes:** Point layer; no PIN — join by normalized address or spatial. Do **not** treat `resident` as current owner (CAMA NAME1 is authoritative).

### 11. Land Use (MapServer/38) — NOT planning FLU

- **REST URL:** https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer/38
- **Fields:** `CLASS_NAME` (e.g. Corn, Soybeans, Deciduous Forest, Developed/*)
- **Verified:** count **42**
- **Status:** **wrong role for FLU** — cropland/land-cover; catalog as `other` only. Planning FLU = PDF gap.

### 12. CountyGISmap_Internal — do not wire

- **REST URL:** https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap_Internal/MapServer
- **Notes:** Labeled internal; prefer public `CountyGISmap` / `WebsiteMap`. Includes utility layers out of scope.

## Municipalities (first-class — cities-first)

County parcels are countywide; **zoning authority is municipal** (or county unincorporated / ETJ carve-outs). Join: CountyGISmap Parcels/1 (2264) → spatial join Town Limits/45 → route to zoning **44 → 43 → 41 → 42 → 40** → FLU via PDF FLUM only (no REST). **No separate municipal parcel REST.**

### Town of Yadkinville (PRIMARY / county seat)

- **Zoning:** CountyGISmap/MapServer/44 — **88**; fields `ZONE_CODE` / `ZONE`
- **FLU:** **gap** (town ordinance PDFs on yadkinville.org; no FLU FeatureServer)
- **Independent GIS:** none verified
- **Join:** Spatial join inside YADKINVILLE / YADKINVILLE ETJ; county zoning does not apply in town/ETJ.

### Town of Jonesville

- **Zoning:** CountyGISmap/MapServer/43 — **2,236**; field `ZONING`
- **FLU:** **gap**
- **Independent GIS:** none
- **Join:** Prefer layer 43 for JONESVILLE / JONESVILLE ETJ (parcel-scale districts).

### Town of Boonville

- **Zoning:** CountyGISmap/MapServer/41 — **97**; fields `BOONVILLE_` / `BOONVILLE1`
- **FLU:** **gap**
- **Independent GIS:** none
- **Join:** Spatial join inside BOONVILLE / BOONVILLE ETJ.

### Town of East Bend

- **Zoning:** CountyGISmap/MapServer/42 — **50**; fields `ZONING_NO` / `ZONING_NAM`
- **FLU:** **gap**
- **Independent GIS:** none
- **Join:** Spatial join inside EAST BEND corporate limit (no ETJ polygon on layer 45).

### Unincorporated Yadkin County (+ CDPs)

- **Zoning:** CountyGISmap/MapServer/40 — **1,248**; fields `ZONING` / `ZONE_NAME`
- **FLU:** PDF FLUM only (https://www.yadkincountync.gov/DocumentCenter/View/6126/Future-Land-Use-Map-)
- **Communities without separate zoning layers:** Hamptonville, Arlington (historic), Courtney, Forbush, Buck Shoals, etc. — use **county** zoning; not separate munis.

## PA / viewer deep-links (TRANCHE-3)

| Template | Key | Status |
|----------|-----|--------|
| `https://www.bttaxpayerportal.com/ITSPublicYK/AppraisalCard.aspx?id={PARCEL_NO}/2027` | PARCEL_NO | **Verified** PDF (200 / application/pdf); also live `TAXCARD` field |
| `https://www.bttaxpayerportal.com/ITSPublicYK/TaxBillSearch` | — | Tax bill search portal |
| `https://lrcpwa.ncptscloud.com/yadkin/parcel-detail/{PIN}` | PIN | **Verified** SPA shell (200); also try `{PARCEL_NO}` |
| https://lrcpwa.ncptscloud.com/yadkin/ | — | NCPTS search |
| https://gis.yadkincountync.gov/ | — | **jurisdictionGisUrl** |
| https://yadkincounty.maps.arcgis.com/apps/webappviewer/index.html?id=1762d0186a0749569e53e66fae91eecd | — | AGOL viewer mirror |

## Gaps

1. **No public Future Land Use FeatureServer** — biggest schema gap; 2023 FLUM + Comp Plan are PDFs only.
2. **MapServer “Land Use” (38) is cropland/land-cover** — do not map to `flu`.
3. **Situs city/zip missing on parcels** — only `STREET_ADDRESS`; enrich via Addresses points or OneMap `scity` (often empty).
4. **No TOTAL market/assessed column** — sum `LAND_FMV_CURRENT`+`BLDG_FMV_CURRENT` for market; land ASV/LUV present; no BLDG_ASV field.
5. **County zoning NCPIN join unusable** (~3 non-null) — spatial join required.
6. **OneMap `saledate` empty for Yadkin** — use county `DEED_DATE` / `SALES_AMT`; OneMap has no sale price.
7. **No independent municipal ArcGIS hosts** — town zoning published only on county MapServer (prefer those town layers as most-local).
8. **Yadkinville ZONE label inconsistencies** for some codes — QA `ZONE_CODE` over free-text `ZONE`.
9. **MaxRecordCount 1000** on county MapServer — paginate.
10. No AADT / utilities / emails / phones / paid vendors collected (per ask).
11. **CountyGISmap_Internal** — avoid as primary wire target.

## Hand-off notes for Land Search Builder

1. **Wire first:** `CountyGISmap/MapServer/1` — polygons + PIN, owner, mailing, STREET_ADDRESS, TOTAL_ACRES, land/bldg values, SALES_AMT, DEED_DATE, QUALIFIED_CODE, TAXCARD. Filter `TOTAL_ACRES BETWEEN 5 AND 150` (~8.2k). Optional vacant-ish: `BLDG_FMV_CURRENT = 0` (~3.8k in range) or `DESCRIPTION = 'VACANT'`.
2. **Zoning (cities-first):** spatial join in 2264 after routing by Town Limits/45 → layers **44 Yadkinville / 43 Jonesville / 41 Boonville / 42 East Bend / 40 County**. Prefer town layers over county inside munis/ETJs.
3. **FLU:** **gap** — no REST; optional offline digitize from 2023 FLUM PDF if product requires it.
4. **Sales:** on primary parcel (`SALES_AMT` + `DEED_DATE` + `QUALIFIED_CODE`); OneMap does not help for Yadkin sale dates/prices.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='197'` (land/improve values; ~28.3k).
6. **TRANCHE-3 links:** AppraisalCard `{PARCEL_NO}`; NCPTS `{PIN}`; jurisdictionGisUrl `gis.yadkincountync.gov`.
7. **Join keys:** `PIN`↔OneMap `parno`; `PARCEL_NO`↔`altparno` / TAXCARD; spatial for zoning.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities/towns are first-class:** never treat County Zoning alone as countywide coverage.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **tranche:** 3 (tax/sale/owner on parcels; PA deep-link `{PARCEL_NO}`; jurisdictionGisUrl; parcels + cities-first zoning + FLU suite)

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='YADKIN'`, field `AADT_2022` (string) — **345 stations live**, 163 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27YADKIN%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27YADKIN%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Yadkin'`, `AADT_2025` (int) — 343 stations; 221 with 2025, 210 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://gis.yadkincountync.gov/arcgis/rest/services/CountyGISmap/MapServer/1` — total 28364, 5–150 ac 8175 (`TOTAL_ACRES>=5 AND TOTAL_ACRES<=150`).
- Non-zero county: `LAND_FMV_CURRENT` 28295, `BLDG_FMV_CURRENT` 18382, `LAND_ASV_CURRENT` 28295; in 5–150: `LAND_ASV_CURRENT` 8156. **Status: ok.**
- LAND_FMV_CURRENT/LAND_ASV_CURRENT integer, BLDG_FMV_CURRENT double. No single total field — sum land+bldg.

### 3. Sale history
- Price `SALES_AMT`>0 12488 (5–150: 2962); date non-null `DEED_DATE` 28120. **Status: ok.**
- DEED_DATE esriDate; SALES_AMT integer; QUALIFIED_CODE.

### 4. Owner entity
- Owner fields: `NAME1`, `NAME2`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 859** (of 8175 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: `https://www.bttaxpayerportal.com/ITSPublicYK/AppraisalCard.aspx?id={PARCEL_NO}/2027`
- Tested `https://www.bttaxpayerportal.com/ITSPublicYK/AppraisalCard.aspx?id=112756/2027` → **200**. HTTP 200 returns application/pdf appraisal card; pdftotext confirms owner + parcel 112756. Tax year segment must track current year (2027 in portal now). Alt NCPTS https://lrcpwa.ncptscloud.com/yadkin/parcel-detail/{PIN} (200 shell).

### 6. Jurisdiction GIS viewer
- `https://gis.yadkincountync.gov/` → **200**. Yadkin County GIS

### Pass2 gaps
- AADT_2022 blank at 182 of 345 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- No multi-transfer sale history on primary layer (last sale only)
