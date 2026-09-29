# Wilkes County, NC — GIS County Card

## Summary

Wilkes County (Winston-Salem MSA shed, FIPS **37193**, slug **wilkes**, `cntyfips='193'`) publishes a strong **public** ArcGIS REST stack at `gis.wilkescounty.net`. **Wire-first parcels (TRANCHE-3):** **Parcels/MapServer/0** (mirrors HMWebSite/WebMap2023/22, LandRecords/Parcels/0, Downloads/ParcelforDownload) — ~**52,720** polys with `PARCEL_ID`/`PIN`/`ACCOUNT`, owner, mailing, situs (`PROPLOCAT`), `TOTALACRES`, full cost/appraised split (`COSTLANDVA`/`COSTBLDGVA`/`COSTTOTVA`), and **SALEPRICE + SALEDATE + SALE_VALIDITY**. ~**14,800** with `TOTALACRES` 5–150 (~**6,300** COSTBLDGVA=0 in band). **Zoning is cities-first:** North Wilkesboro (WebMap/23, 149) + Wilkesboro (WebMap/24, 345) before county Wilkes County Zones (WebMap/26, 70) / Planning Zoning_Districts. **FLU:** Growth Management Plan + Wilkesboro Comp LUP/FLU + North Wilkesboro FLU — **PDF only** (no FLU FeatureServer). **PA deep-link:** `Datalets/Datalet.aspx?UseSearch=no&pin={PARCEL_ID}` (verified). **Jurisdiction GIS:** https://gis.wilkescounty.net/maps/ (`?PARCEL_ID=` / `?PIN=`). Markets: **[Winston-Salem shed]**. Main gaps: no county FLU REST; Elkin/Ronda lack Wilkes zoning FS; OneMap `parno`↔county `PIN` often remapped (prefer spatial/`PARCEL_ID`); CRS **32019 NAD27** (not 2264).

## Portals

- **Jurisdiction GIS (Map Viewer)** — https://gis.wilkescounty.net/maps/
- **Viewer deep-link** — `https://gis.wilkescounty.net/maps/default.htm?PARCEL_ID={PARCEL_ID}` (also `?PIN={PIN}`)
- **County ArcGIS REST** — https://gis.wilkescounty.net/arcgis/rest/services
- **GIS dept** — https://wilkescounty.net/640/GIS
- **Tax Administration** — https://wilkescounty.net/226/Tax-Administration
- **Parcel Information (BI-Tek / PA)** — https://parcelinfo.wilkescounty.net/
- **PA deep-link (preferred)** — `https://parcelinfo.wilkescounty.net/Datalets/Datalet.aspx?UseSearch=no&pin={PARCEL_ID}`
- **Parcel Information (county alias)** — https://wilkescounty.net/233/Parcel-Information
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/wilkes/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/wilkes/parcel-detail/{PIN}` (SPA; also try `{PARCEL_ID}`)
- **Open Data (AGOL Hub)** — https://data3-wilkescountygis.opendata.arcgis.com/
- **Planning** — https://wilkescounty.net/258/Planning
- **Ordinances** — https://wilkescounty.net/261/Ordinances
- **Wilkes Growth Plan** — https://wilkescounty.net/260/Wilkes-Growth-Plan
- **Growth Management Plan (PDF)** — https://wilkescounty.net/DocumentCenter/View/2172/Growth-Management-Plan---Final
- **Town of Wilkesboro Comp LUP (PDF)** — https://wilkesboronc.org/images/documents/Planning/AdoptedPlans/Comprehensive-LUP-12.10.12.pdf
- **Wilkesboro Future Land Use Map (PDF)** — https://wilkesboronc.org/images/documents/Planning/AdoptedPlans/12-4-07-Future-Land-Use-Roads.pdf
- **North Wilkesboro Future Land Use Map (PDF)** — https://www.north-wilkesboro.com/DocumentCenter/View/94/Future-Land-Use-Map-PDF
- **Register of Deeds** — https://wilkescounty.net/268/Register-of-Deeds
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='193'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PARCEL_ID` (PA/viewer); `PIN` (map/NCPTS/OneMap); `ACCOUNT` | Prefer **PARCEL_ID** for Datalet |
| polygons | Yes | Parcels/0; WebMap/22; LandRecords/Parcels/0 | CRS **32019** (NAD27 NC StatePlane) |
| acreage | Yes | `TOTALACRES` (prefer); `ACRES`; OneMap `gisacres` | ~**14,800** TOTALACRES 5–150; `ACRES` alone under-counts |
| ownerName | Yes | `OWNER1`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `MAILADD1`/`MAILADD2`,`CITY`,`STATE`,`ZIP` | Owner mail — **not** situs city |
| situs address | Partial | `PROPLOCAT`; OneMap `siteadd` | Often street; sometimes plat/legal text; **no situs city/zip on parcel** |
| lastSale date/price | Yes | `SALEPRICE`,`SALEDATE`,`SALE_VALIDITY`,`SALETYPE` | ~**26,231** SALEPRICE>0 (~**6,911** in 5–150); filter outliers ≥$10M (2 in band) |
| tax values | Yes | `COSTLANDVA`,`COSTBLDGVA`,`COSTTOTVA`; OneMap `parval`/`landval`/`improvval` | COST* match Datalet appraised/assessed on sample |
| zoning | Yes (cities-first) | NW `ZoningCode`; WB `ZoneCode`; county `ZONE`/`District` | Prefer muni layers inside city limits |
| flu | PDF only | Growth Plan + Wilkesboro/NW FLU PDFs | **No FLU FeatureServer** |
| appraiser / viewer link | Yes | Datalet `{PARCEL_ID}`; viewer `?PARCEL_ID=`/`?PIN=`; NCPTS | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. Parcels/MapServer — parcels + ownership + tax + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | situs
- **REST URL:** https://gis.wilkescounty.net/arcgis/rest/services/Parcels/MapServer/0
- **Mirrors:** HMWebSite/WebMap2023/MapServer/22; LandRecords/Parcels/MapServer/0; Parcels_Data/MapServer/0; Downloads/ParcelforDownload/FeatureServer/0
- **Layer name / id:** wilkes_vector.WILKES.Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PARCEL_ID` → parcelId (PA deep-link key)
  - `PIN` → parcelIdMap / join candidate to OneMap `parno`
  - `ACCOUNT` → parcelIdAccount
  - `TOTALACRES` → acreage (prefer over `ACRES`)
  - `OWNER1` → ownerName
  - `MAILADD1`,`MAILADD2`,`CITY`,`STATE`,`ZIP` → mailing
  - `PROPLOCAT` → situsAddress
  - `COSTLANDVA`,`COSTBLDGVA`,`COSTTOTVA` → tax
  - `SALEPRICE`,`SALEDATE`,`SALE_VALIDITY`,`SALETYPE` → lastSale
  - `BK`,`PG`,`BOOK_PAGE` → deed
  - `CLASS`,`STATECLASS` → dorCode / land use
- **WKID / CRS:** **32019** (NAD 1927 StatePlane North Carolina FIPS 3200 Feet) — not 102719/2264
- **Verified:** yes — count **52,720**; `TOTALACRES` 5–150 → **14,800**; `SALEPRICE>0` → **26,231** (in band → **6,911**; under $10M in band → **6,909**); `COSTTOTVA>0` → **52,478**; COSTBLDGVA=0 in band → **6,300**; `SALEDATE IS NOT NULL` → **49,240**; sample PARCEL_ID `0702212` / PIN `2878-80-5271` = LEATHERWOOD MOUNTAINS PROPERTY OWNERS (centroid ≈ **-81.44, 36.14** Wilkes); sale sample `1405092` SALEPRICE 9,825,000 / COSTTOTVA 5,571,680
- **Notes:** Best single county layer. MaxRecordCount **1000** — paginate. Auth **none**. Prefer `TOTALACRES` for site-search acreage. Extreme SALEPRICE outliers rare — use SALE_VALIDITY / stamp heuristics.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='193'`
- **Key fields:** `parno`, `ownname`, `mailadd`…, `siteadd`, `gisacres`, `saledate`/`saledatetx`, `parval`/`landval`/`improvval`
- **Verified:** yes — count **52,847**; `gisacres` 5–150 → **14,886**; `parval>0` → **52,555**; usable `saledate` → **52,838**; improvval=0 in 5–150 → **6,339**
- **Notes:** **No sale price.** `parno`↔county `PIN` often **remapped** after reval (same owner/site near centroid may differ by check-digit); prefer county `PARCEL_ID` + spatial join when OneMap attrs needed. County CAMA preferred for sale price/tax when present.

### 3. Zoning — North Wilkesboro (city-first PRIMARY)

- **REST URL:** https://gis.wilkescounty.net/arcgis/rest/services/HMWebSite/WebMap2023/MapServer/23
- **Mirror:** Planning/Planning/MapServer/6 (`nwilkesboro_zoning`)
- **Fields:** `ZoningCode`, `ZoneDescri`
- **Verified:** count **149** — codes CBD, GB, GI, HB, LI, MF-CD, NB, OI, PD-CD, R10, R20, R6
- **Notes:** Prefer over county zones inside North Wilkesboro limits / NWETJ.

### 4. Zoning — Wilkesboro (city-first PRIMARY)

- **REST URL:** https://gis.wilkescounty.net/arcgis/rest/services/HMWebSite/WebMap2023/MapServer/24
- **Mirror:** Planning/Planning/MapServer/4 (`wilkesboro_zoning`)
- **Fields:** `ZoneCode`, `ZoneDescri`
- **Verified:** count **345** — codes B1, B2, B3, M1, M2, R20, R20A, R6, R8
- **Notes:** Town Planning staff + High Country COG maintenance (layer metadata). Prefer inside Wilkesboro / WETJ.

### 5. Wilkes County Zones — unincorporated / named communities

- **REST URL:** https://gis.wilkescounty.net/arcgis/rest/services/HMWebSite/WebMap2023/MapServer/26
- **Mirrors:** Planning/Planning/MapServer/3; Planning Zoning_Districts/1 (District codes, count **102**)
- **Fields:** `ZONE`, `ALPHA` (COUNTRY CLUB, MORAVIAN FALLS, PURLEAR, ROCK CREEK, WEST ELKIN, …)
- **Verified:** count **70** — zone codes C-S, H-B, L-1, R-15R, R-20, R-20A (+ District H-1 on Zoning_Districts)
- **Notes:** Use for unincorporated; inside cities prefer dedicated muni layers. Sparse named ALPHA communities are not full municipal zoning.

### 6. Municipalities / ETJ / overlays

- **Municipalities:** WebMap/11 — ALPHA: **WILKESBORO**, **NORTH WILKESBORO**, **ELKIN**, **RONDA** (count **4**)
- **ETJ:** WebMap/25 — NWETJ, WETJ (count **9** polys / 2 names)
- **Airport Overlay:** WebMap/2 (count **1**)
- **Wilkesboro Historic District:** WebMap/33 (parcel-attributed, count **84**)

### 7. Reval25ViewFC — reval join helper (optional)

- **REST URL:** https://gis.wilkescounty.net/arcgis/rest/services/Reval25/Reval25ViewFC/FeatureServer/0
- **Fields:** `PARID`,`OWN1`,`ACRES`,`CALCACRES`,`APRLAND`/`APRBLDG`/`APRTOT`,`PRICE`,`SALEDT`
- **Verified:** count **50,981**
- **Notes:** Reval-cycle view; prefer live Parcels/0 for production CAMA. May help reconcile remapped PINs.

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| Unincorporated Wilkes | County Zones WebMap/26 + Zoning_Districts/1 | 70 / 102 | County | Growth Plan **PDF** | Unincorp zoning sparse vs full county |
| **Wilkesboro** | WebMap/24 (+ Planning/4) | **345** | Via county viewer | Comp LUP + FLU **PDF** | County seat — city-first PRIMARY |
| **North Wilkesboro** | WebMap/23 (+ Planning/6) | **149** | Via county viewer | FLU Map **PDF** | City-first PRIMARY |
| **Elkin** | *(none on Wilkes host)* | — | No (Wilkes) | No | Mostly Surry; Wilkes fringe only — use Surry Elkin zoning if needed |
| **Ronda** | *(none)* | — | No | No | Limits only; no public zoning FS |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| Datalet summary (preferred) | `https://parcelinfo.wilkescounty.net/Datalets/Datalet.aspx?UseSearch=no&pin={PARCEL_ID}` |
| Datalet sales tab | `…/Datalet.aspx?mode=sales_summary&UseSearch=no&pin={PARCEL_ID}&jur=097&taxyr=2026` |
| Viewer deep-link | `https://gis.wilkescounty.net/maps/default.htm?PARCEL_ID={PARCEL_ID}` |
| Viewer by PIN | `https://gis.wilkescounty.net/maps/default.htm?PIN={PIN}` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/wilkes/parcel-detail/{PIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/wilkes/parcel-search |
| Jurisdiction GIS | https://gis.wilkescounty.net/maps/ |

Viewer `SearchConfig.js` wires Tax/PRC → Datalet `pin=${PARCEL_ID}`. Verified Datalet for `0702212` returns LEATHERWOOD MOUNTAINS PROPERTY OWNERS with valuation + Recorded Transaction sales block. Optional `jur=097&taxyr=2026` appears in sidebar links.

## Gaps / caveats

- **No FLU FeatureServer** — county Growth Plan + Wilkesboro/North Wilkesboro FLU are PDF only
- **Elkin / Ronda** — no dedicated Wilkes zoning layers; Elkin mostly Surry County
- **OneMap PIN drift** — `parno` often ≠ live county `PIN` for same site (reval remap); join spatially or via `PARCEL_ID`/attrs, not blind PIN equality
- **CRS 32019 (NAD27)** — uncommon vs NAD83 2264 peers; transform carefully for statewide overlays
- **Situs city/zip** absent on parcel polygons (mailing city only)
- **SALEPRICE outliers** — 2 parcels ≥$10M in 5–150 band; prefer SALE_VALIDITY / stamp context
- `ACRES` vs `TOTALACRES` diverge — use **TOTALACRES** for acreage filters
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Wilkes County GIS / Tax Administration. Map data compiled from recorded deeds, plats, and public records; not survey quality; consult primary sources. Attribute Wilkes County GIS (and Town of Wilkesboro / Town of North Wilkesboro / High Country COG where zoning layers used). Commercial resale subject to **NCGS 132-10**.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 12+
- **tranche:** 3 (tax/sale/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- Live `returnCountOnly` + sample attribute/geometry queries against Parcels/0, WebMap2023 zoning/munis/ETJ, Planning mirrors, Downloads, Reval25ViewFC, NC OneMap `cntyfips='193'`; Datalet HTML cross-check; SearchConfig.js / config.js deep-link wiring; geo-check centroids in Wilkes.
