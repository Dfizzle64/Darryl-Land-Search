# Pender County, NC — GIS County Card

## Summary

Pender County (Wilmington MSA, FIPS **37141**, `cntyfips='141'`) publishes public ArcGIS REST at `gis.pendercountync.gov`. **Wire-first parcels:** `Energov/MapServer/1` — countywide polygons with owner, mailing, situs (`PROPERTY_ADDRESS`), last sale date/price, GIS/deed acres, **tax values** (`LAND_VALUE`/`BUILDING_VALUE`/`TOTAL_VALUE`/`DEFERRED_VALUE`), and CAMA `ZONE` (~**55,487** features; **~7,466** with `CALCACRES` 5–150). Newer viewer stacks `LayersPro` / `OperationalLayers2026` Parcels match geometry/owner/sale/situs but **omit tax fields** — use Energov (or `LayersMapIASLink` / NC OneMap) for values. **Zoning is municipality-first** inside city limits (Burgaw, St Helena, Surf City, Topsail Beach, Watha on county host); unincorporated uses **Pender County Zoning** (`UDO_ZONING`). **Atkinson** has a town UDO/ordinance but **no public zoning FeatureServer**. **Hampstead** is unincorporated (CDP) — county zoning + Imagine Pender 2050 FLU. **FLU:** Imagine Pender 2050 (`CA_FLU_013`) preferred; legacy Pender 2.0 FLUM joins FLU+tax onto older parcel polys. **NC OneMap** (`cntyfips='141'`) is a solid fallback with `parval`/`siteadd`. Main gaps: tax missing on Op2026/LayersPro parcels; Atkinson zoning REST absent; municipal FLU REST thin (Imagine buckets munis as `Municipal/ETJ`).

## Portals

- **Parcel Viewer (Experience Builder)** — https://experience.arcgis.com/experience/3ef6176b28f644ecbeb43b88542f0e52/ — also https://gis.pendercountync.gov/maps/ (redirects here)
- **GIS & Addressing Services** — https://www.pendercountync.gov/246/GIS-Addressing-Services
- **County ArcGIS REST** — https://gis.pendercountync.gov/arcgis/rest/services
- **Tax / Property Information (Vision)** — https://tax.pendercountync.gov/ — disclaimer → CommonSearch; datalet by undashed PIN
- **Tax search (realprop)** — https://tax.pendercountync.gov/search/commonsearch.aspx?mode=realprop
- **Imagine Pender 2050** — county comprehensive plan FLU (REST layers below)
- **Surf City Maps & GIS** — https://surfcitync.gov/2511/Maps-and-GIS — StoryMaps collection (prefer town maps inside Surf City; county host also mirrors zoning)
- **Surf City GIS StoryMaps** — https://storymaps.arcgis.com/collections/703518609ac44d1fb01e7972c820a9c2
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)
- **Open data Hub** — https://pender-opendata-pendercountync.hub.arcgis.com/ — present but **API unauthorized / private org** (2026-09-23); do not rely on downloads

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `ACCOUNT`, `ALT_PIN`; OneMap `parno` | Dashed PIN e.g. `3245-52-0278-0000`; tax site wants undashed |
| polygons | Yes | Energov/1 or LayersPro/4 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALCACRES`, `ACRES` | ~**7,466** CALCACRES 5–150; ~**7,493** ACRES 5–150 |
| ownerName | Yes | `NAME` / OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `ADDR`,`CITY`,`STATE`,`ZIP` | |
| situs address | Yes (partial) | `PROPERTY_ADDRESS`; E911 `FULL_NAME`+`ZIP_CODE`; OneMap `siteadd` | Often null on vacant/acreage tracts — join E911 by PIN |
| lastSale date/price | Yes | `DATE`,`SALE_PRICE` | Last sale only; ~28.6k with SALE_PRICE>0 on Energov |
| tax values | Yes (Energov/IAS/OneMap) | `LAND_VALUE`,`BUILDING_VALUE`,`TOTAL_VALUE`,`DEFERRED_VALUE`; OneMap `parval`/`landval`/`improvval` | **Not** on LayersPro/Op2026 Parcels |
| zoning | Yes (split) | Spatial `UDO_ZONING` / muni fields; attr `ZONE` on Energov | Prefer spatial join; `ZONE` attr mixed/incomplete |
| flu | Yes (county plan) | Imagine `CA_FLU_013`; FLUM `FLU`/`ELU` | Municipal FLU REST gap |
| appraiser / viewer link | Yes | Tax datalet + Parcel Viewer | Templates below |

## Layers (verified)

### 1. Energov Parcels — polygons + ownership + situs + sale + tax + ZONE (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | zoning (attr)
- **REST URL:** https://gis.pendercountync.gov/arcgis/rest/services/Energov/MapServer/1
- **Layer name / id:** Parcels / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId
  - `ACCOUNT`, `ALT_PIN` → alt ids
  - `CALCACRES`, `ACRES` → acreage
  - `NAME` → ownerName
  - `ADDR`,`CITY`,`STATE`,`ZIP` → mailing
  - `PROPERTY_ADDRESS` → situsAddress
  - `DATE`,`SALE_PRICE` → lastSale
  - `LAND_VALUE`,`BUILDING_VALUE`,`TOTAL_VALUE`,`DEFERRED_VALUE` → tax
  - `ZONE` → zoning (CAMA attr; incomplete — see spatial zoning)
  - `USE_`,`PCL_CLASS`,`TOWNSHIP`,`TNSH_DESC`,`DEED_BOOK`,`DEED_PAGE` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **55,487**; `CALCACRES BETWEEN 5 AND 150` → **7,466**; `ACRES` 5–150 → **7,493**; non-null `TOTAL_VALUE` **54,643**; non-empty `PROPERTY_ADDRESS` **42,889**; `ZONE` populated **49,911**; `SALE_PRICE>0` **28,655**
- **Notes:** **PRIMARY** wire-first for land search (tax + geometry + owner/sale). MaxRecordCount **1000** — paginate. `TOTAL_VALUE` often equals land+bldg before use-value deferral; `DEFERRED_VALUE` holds deferred amount. Auth: none.

### 2. LayersPro / OperationalLayers2026 Parcels — newer viewer mirrors (no tax)

- **Purpose:** parcels | ownership | sales (last)
- **REST URLs:**
  - https://gis.pendercountync.gov/arcgis/rest/services/LayersPro/MapServer/4
  - https://gis.pendercountync.gov/arcgis/rest/services/OperationalLayers2026/MapServer/4
- **Geometry:** Polygon
- **Key fields:** Same owner/mail/situs/sale/acreage as Energov (`PIN`,`NAME`,`ADDR`…`PROPERTY_ADDRESS`,`DATE`,`SALE_PRICE`,`CALCACRES`,`ACRES`) — **no** `LAND_VALUE`/`TOTAL_VALUE`/`ZONE`
- **Verified:** yes — both count **55,487**; CALCACRES 5–150 → **7,466**. MaxRecordCount **2000**
- **Notes:** Prefer for higher page size / viewer parity; **join tax from Energov or OneMap by PIN**. Same CRS 2264.

### 3. LayersMapIASLink Parcels — tax-rich but fewer features

- **Purpose:** parcels | tax | ownership | sales
- **REST URL:** https://gis.pendercountync.gov/arcgis/rest/services/LayersMapIASLink/MapServer/4
- **Geometry:** Polygon
- **Key fields:** Full CAMA incl. `LAND_VALUE`,`BUILDING_VALUE`,`TOTAL_VALUE`,`DEFERRED_VALUE`,`ZONE` (same names as Energov)
- **Verified:** yes — count **52,748** (lags Energov); CALCACRES 5–150 → **7,359**
- **Notes:** Usable tax mirror but **stale vs Energov**. Prefer Energov.

### 4. E911 Address Points — situs join

- **Purpose:** other (situs)
- **REST URL:** https://gis.pendercountync.gov/arcgis/rest/services/LayersPro/MapServer/1
- **Also:** Op2026/1, LayersMapIASLink/1
- **Geometry:** Point
- **Key fields → targets:** `PIN` → join; `FULL_NAME` / `HouseNum`+`NAME`+`TYPE` → situsAddress; `ZIP_CODE`,`POSTAL_DISTRICT`,`MUNICIPALITY`
- **Verified:** yes — count **42,690**; with PIN **41,691**
- **Notes:** Many-to-one vs parcels. Use when `PROPERTY_ADDRESS` null. Do not harvest contact/PII beyond public address fields.

### 5. Pender County Zoning (unincorporated) — spatial

- **Purpose:** zoning
- **REST URL:** https://gis.pendercountync.gov/arcgis/rest/services/LayersPro/MapServer/36
- **Also:** Development_Activity/10; LayersMapIASLink/37
- **Geometry:** Polygon
- **Key fields:** `UDO_ZONING`, `DESC_`, `PAST_ZONING`, setbacks/heights
- **Verified:** yes — count **1,912**; distinct UDO codes include RA, RP, RM, GB, GI, EC, PD, MH, O&I, IT, INCORP, CZ-*
- **Notes:** Covers **unincorporated** (Hampstead area, Rocky Point, etc.). `INCORP` polygons mark municipal footprints — route to muni zoning layers. Spatial join parcels in **2264**.

### 6. Imagine Pender 2050 — FLU (PRIMARY flu)

- **Purpose:** flu
- **REST URLs:**
  - https://gis.pendercountync.gov/arcgis/rest/services/LayersPro/MapServer/35
  - https://gis.pendercountync.gov/arcgis/rest/services/ImaginePender/MapServer/53
- **Geometry:** Polygon
- **Key fields:** `CA_FLU_013` (alias FUTURE LAND USE CATEGORY), `NAME`
- **Verified:** yes — count **54,137**; categories: Coastal Neighborhood, Conservation, Hampstead Bypass, Heavy Commercial, Industry & Commerce, Municipal/ETJ, Neighborhood Center, Regional Center, Residential Neighborhood, Rural Agricultural, Rural Crossroads, Rural Neighborhood
- **Notes:** Current comprehensive-plan FLU. Spatial join to parcels. Munis largely tagged `Municipal/ETJ` — town-specific FLU REST still a gap.

### 7. Pender 2.0 FLUM — legacy parcel∩FLU (+ tax snapshot)

- **Purpose:** flu | tax (legacy join)
- **REST URL:** https://gis.pendercountync.gov/arcgis/rest/services/LayersPro/MapServer/34
- **Also:** Layers/MapServer/34; LayersMapIASLink/36 (`Future Land Use Classifications`)
- **Geometry:** Polygon
- **Key fields:** `FLU`,`ELU`,`ZONE`,`PIN`,`LAND_VALUE`,`BUILDING_V`,`TOTAL_VALU`,`DEFERRED_V`, owner/sale truncated names
- **Verified:** yes — count **49,408**; CALCACRES 5–150 → **7,440**; FLU values: Civic, Coastal Residential, Commercial Waterfront, Conservation, Incorporated, Industrial, Light Industrial, Low/Medium Density Residential, Neighborhood/Regional Mixed Use, Recreation, Rural Agriculture
- **Notes:** Older parcel join — prefer Imagine 2050 for FLU + Energov for live tax/geometry. Useful historical FLU labels.

### 8. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Geometry:** Polygon
- **Key fields → targets:** `parno`→parcelId; `ownname`; `mailadd`/`mcity`/`mstate`/`mzip`; `siteadd`/`scity`; `gisacres`; `saledate` (**no sale price**); `parval`/`landval`/`improvval`; filter `cntyfips='141'`
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — filter count **55,025**; gisacres 5–150 → **7,437**; sample owner/mail/`parval` OK
- **Notes:** Best single-table situs+tax fallback. May lag county CAMA. MaxRecordCount **5000**. No `SALE_PRICE`.

### 9. Municipal_Boundaries — jurisdiction polygons

- **Purpose:** other (municipality filter)
- **REST URL:** https://gis.pendercountync.gov/arcgis/rest/services/LayersPro/MapServer/9
- **Field:** `ALPHA` — verified: ATKINSON, BURGAW, ST HELENA, SURF CITY / Surf City, TOPSAIL BEACH, WALLACE, WATHA
- **Verified:** yes — count **26** (multi-part)
- **Notes:** Use to route which zoning layer to spatial-join. Wallace is mostly Duplin.

## Municipalities (first-class)

County parcels are countywide; **zoning inside towns is municipal**. Join pattern: Energov parcels (2264) → `Municipal_Boundaries.ALPHA` (or situs/postal city) → spatial join matching town zoning; else county `UDO_ZONING`. Prefer **most local** zoning: town layer when parcel intersects municipality; county UDO only for unincorporated (incl. Hampstead CDP).

### Town of Burgaw (county seat)

- **Zoning (county host):** https://gis.pendercountync.gov/arcgis/rest/services/LayersPro/MapServer/39 — `Zoning_Dis`; count **82**; CRS **2264**. Codes: B-1, B-2, C/P, I-1, I-2, O&I, PD-CZ, PUD-1, R-7/R-12/R-20, RA, CZ variants
- **Overlay:** LayersPro/MapServer/38 Burgaw Overlay Zoning — count **2**
- **FLU:** no town public REST (gap) — Imagine 2050 → `Municipal/ETJ`
- **Join note:** town zoning + county Energov parcels (spatial, 2264). Most local for Burgaw.

### Village of St Helena

- **Zoning:** LayersPro/MapServer/40 — `ZONING`; count **41**; CRS **2264**. Codes: B-2, I-1, I-2, O&I, R-12, R-20, RA
- **FLU:** no public REST (gap)
- **Join note:** village zoning + county parcels

### Town of Surf City (Pender + Onslow)

- **Zoning (county host mirror):** LayersPro/MapServer/41 — `ZONE`; count **169**; CRS **2264**. Codes: C1, C3, CON, CZ-*, G1, MFC, MHS, MU, NB, OI, PUD, R5/R5M/R10/R15, RA, SF, STATE
- **Town GIS (preferred UI inside town):** https://surfcitync.gov/2511/Maps-and-GIS — StoryMaps collection https://storymaps.arcgis.com/collections/703518609ac44d1fb01e7972c820a9c2 — no separate public FeatureServer catalog verified; use county host layer for wire queries
- **FLU:** no town public REST (gap)
- **Join note:** town zoning + **Pender** Energov parcels; filter out Onslow side with `cntyfips`/county parcels. Prefer Surf City layer over county UDO when `Municipal_Boundaries` = SURF CITY.

### Town of Topsail Beach

- **Zoning:** LayersPro/MapServer/42 — `ZONING_`; count **10**; CRS **2264**. Codes: B-1, B-2, C-4, PRD-1, PRD-2, R-1..R-4
- **FLU:** no public REST (gap)
- **Join note:** town zoning + county parcels (spatial)

### Town of Watha

- **Zoning:** LayersPro/MapServer/43 — `ZONING_`; count **30**; CRS **2264**. Codes: C1, C2, G, I, RA
- **FLU:** no public REST (gap)
- **Join note:** town zoning + county parcels

### Town of Atkinson

- **Zoning REST:** **none found** on county host or public town ArcGIS (gap). Town lists Zoning Ordinance / UDO at https://www.atkinsonnc.org/town-ordinances/ — PDF/ordinance only
- **Boundary:** `Municipal_Boundaries` ALPHA=`ATKINSON`
- **Join note:** cannot wire municipal zoning; leave zoning null or use CAMA `ZONE` / county layer with caution — do not invent. Ordinance is authoritative offline.

### Town of Wallace (mostly Duplin; Pender edge)

- **Boundary:** `Municipal_Boundaries` includes WALLACE
- **Zoning on Pender host:** no Wallace zoning layer
- **Join note:** prefer Duplin County GIS for Wallace proper; Pender card only for edge parcels in 37141

### Hampstead area (unincorporated CDP)

- **Not a municipality** — county zoning (`UDO_ZONING`) + Imagine Pender 2050 FLU (incl. Hampstead Bypass category)
- **Join note:** Energov parcels ∩ county Zoning/36; FLU spatial from Imagine 2050. No town zoning layer.

## Gaps

- **Tax values absent on LayersPro & OperationalLayers2026 Parcels** — wire Energov/1 (or IASLink / OneMap) for `LAND_VALUE`/`TOTAL_VALUE`.
- **Atkinson: no public zoning FeatureServer** — ordinance only; biggest municipal gap.
- **Municipal FLU REST thin** — Imagine 2050 collapses incorporated areas to `Municipal/ETJ`; Burgaw/Surf City/Topsail/St Helena/Watha lack town FLU layers.
- **Parcel CAMA `ZONE` incomplete/mixed** — spatial join municipal + county zoning preferred over attribute alone.
- **Situs often null** on vacant/large tracts — join E911 by PIN or OneMap `siteadd`.
- **Sale history** is last-sale only (`DATE`/`SALE_PRICE`); no multi-transfer FeatureServer.
- **LayersMapIASLink** parcel count lags Energov (~52.7k vs 55.5k).
- **Open data Hub** org API unauthorized — no free Hub download path verified.
- **Surf City** town GIS is StoryMaps-first; county REST zoning is the wire path.
- **MaxRecordCount** 1000 (Energov) / 2000 (LayersPro) / 5000 (OneMap) — paginate.
- **Owner phones/emails** not collected; no paid vendors (CoreLogic/Regrid/ATTOM avoided).

## Hand-off notes for Land Search Builder

1. **Wire first:** `Energov/MapServer/1` — polygons + owner, mailing, situs, acreage, tax, last sale, CAMA ZONE. Filter `CALCACRES BETWEEN 5 AND 150` (~7.5k). Paginate MaxRecordCount 1000.
2. **Alt geometry:** `LayersPro/MapServer/4` or `OperationalLayers2026/MapServer/4` (MaxRec 2000) then join tax from Energov on `PIN`.
3. **Situs fill:** E911 LayersPro/1 on `PIN`, or OneMap `siteadd`.
4. **Zoning:** spatial join — if in muni bounds use Burgaw/39, St Helena/40, Surf City/41, Topsail/42, Watha/43; else county Zoning/36 `UDO_ZONING`. Atkinson = gap.
5. **FLU:** spatial join Imagine Pender 2050 (`CA_FLU_013`); optional legacy FLUM `FLU`.
6. **Fallback:** NC OneMap layer 1 with `cntyfips='141'`.
7. **Viewer / appraiser links:**
   - Parcel Viewer: `https://experience.arcgis.com/experience/3ef6176b28f644ecbeb43b88542f0e52/`
   - Tax search: `https://tax.pendercountync.gov/search/commonsearch.aspx?mode=realprop`
   - Datalet deep link: `https://tax.pendercountync.gov/Datalets/Datalet.aspx?UseSearch=no&mode=&pin={PIN_NO_DASHES}` (strip hyphens from `PIN`)
8. **Join keys:** `PIN` (dashed), undashed PIN for tax URL, `ACCOUNT`, OneMap `parno`↔`PIN`.
9. **Auth:** none observed on listed public query endpoints.
10. **Cities/towns are first-class:** never treat county UDO alone as countywide zoning coverage.

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='PENDER'`, field `AADT_2022` (string) — **339 stations live**, 111 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27PENDER%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27PENDER%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Pender'`, `AADT_2025` (int) — 335 stations; 238 with 2025, 212 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://gis.pendercountync.gov/arcgis/rest/services/Energov/MapServer/1` — total 55487, 5–150 ac 7466 (`CALCACRES>=5 AND CALCACRES<=150`).
- Non-zero county: `LAND_VALUE` 53600, `BUILDING_VALUE` 34796, `TOTAL_VALUE` 54613; in 5–150: `TOTAL_VALUE` 7373. **Status: ok.**
- Double fields LAND_VALUE/BUILDING_VALUE/TOTAL_VALUE/DEFERRED_VALUE.

### 3. Sale history
- Price `SALE_PRICE`>0 28657 (5–150: 2554); date non-null `DATE` 46666. **Status: ok.**
- DATE esriDate; SALE_PRICE double. Last sale only.

### 4. Owner entity
- Owner fields: `NAME`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 1777** (of 7466 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: `https://tax.pendercountync.gov/Datalets/Datalet.aspx?UseSearch=no&mode=&pin={PIN_NO_DASHES}`
- Tested `https://tax.pendercountync.gov/Datalets/Datalet.aspx?UseSearch=no&mode=&pin=22237878330000` → **200 (external fetch)**. Loaded with owner IVY LODGE TIMBER LLC via external fetcher. Box HTTPS to *.pendercountync.gov resets at TLS; REST counts for this card were run via external fetch.

### 6. Jurisdiction GIS viewer
- `https://experience.arcgis.com/experience/3ef6176b28f644ecbeb43b88542f0e52/` → **200**. Pender ArcGIS Experience; https://gis.pendercountync.gov/maps/ loads it (external fetch)

### Pass2 gaps
- Box HTTPS to *.pendercountync.gov resets at TLS; all pass2 REST counts + PA test run via external fetch
- AADT_2022 blank at 228 of 339 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- No multi-transfer sale history on primary layer (last sale only)
