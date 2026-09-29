# Warren County, NC — GIS County Card

## Summary

Warren County (Raleigh–Durham footprint, FIPS **37185**, slug **warren**) publishes public ArcGIS REST through Roktech **Warren/RokMap**. **Wire-first parcels:** **RokMap/MapServer/4 — Parcels Large Scale**, about **23,585** polygons with owner, mailing, **situs on the polygon**, assessed acreage, land/building/other/assessed values, and **last sale** (price + deed date/book/page). **Zoning is cities-first via Town Limits** against a parcelized countywide **Zoning/6** layer (no independent municipal FeatureServers for Warrenton / Norlina / Macon). **FLU is a gap** (2022 Comp Plan PDF-only). **NC OneMap** (`cntyfips='185'`) is a usable fallback — use **`recareano`** (gisacres is empty). Markets: **Raleigh–Durham**.

## Portals and primary links

- **Public GIS viewer (jurisdiction homepage / ROKMAPS):** https://maps.roktech.net/ROKMAPS_Warren/
- **County GIS department page:** https://www.warrencountync.com/162/GIS
- **County ArcGIS REST folder:** https://arcgis4.roktech.net/arcgis/rest/services/Warren
- **Primary parcel REST:** https://arcgis4.roktech.net/arcgis/rest/services/Warren/RokMap/MapServer/4
- **NCPTS / property search:** https://lrcpwa.ncptscloud.com/warren/parcel-search
- **PA deep-link by parcel ID:** `https://lrcpwa.ncptscloud.com/warren/parcel-detail/{NEWPIN}`
- **CAMA / BT Taxpayer Portal (ITSPublicWN):** https://www.bttaxpayerportal.com/ITSPublicWN
- **Appraisal card deep-link:** `https://www.bttaxpayerportal.com/ITSPublicWN/AppraisalCard.aspx?id={NEWPIN}`
- **Tax bill deep-link:** `https://www.bttaxpayerportal.com/ITSPublicWN/TaxBillSearch/Parcel/{NEWPIN}`
- **Planning / Zoning:** https://www.warrencountync.com/346/Planning-Zoning-Code-Enforcement
- **Zoning ordinance (PDF):** https://www.warrencountync.com/DocumentCenter/View/4443/Warren-County-Zoning-Ordinance-Updated-March-3-2022
- **Comp Plan 2022 (PDF; FLU source, not REST):** https://www.warrencountync.com/DocumentCenter/View/5281/Warren-County-Comprehensive-Development-Plan-2022
- **NC OneMap parcels fallback:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|---|---|---|---|
| id / parcelId | Yes | `NEWPIN`, `MAPN`, `RECN`; OneMap `parno` | Prefer **NEWPIN** (10-digit) for NCPTS / ITSPublic |
| polygons | Yes | RokMap/4 | CRS **WKID 102100 / 3857** |
| acreage | Yes | `ASSESSED_ACREAGE`; OneMap `recareano` | 5–150 → **5,949** / OneMap **5,942**; do **not** use OneMap `gisacres` (all 0) |
| ownerName | Yes | `NAME1` / `NAME2`; OneMap `ownname` | Public REST fields |
| mailing address | Yes | `ADDR`, `CITY`, `STATE`, `ZIP` | Structured on primary |
| situs address | Yes | `SITUS_ADDRESS` on parcels; Addresses `NEW_ADDR` | ~19.5k situs on polygons |
| lastSale date/price | Yes (last) | `SALE_PRICE`, `DEEDDATE`, `DEEDBOOK`, `DEEDPAGE` | SALE_PRICE>0 → **11,948** |
| tax values | Yes | `LAND_VAL`, `BLDG_VAL`, `OTHER_VAL`, `ASSESSED_VAL` | |
| zoning | Yes / cities-first | RokMap Zoning `ZONING` + Town Limits | No town-owned FS |
| FLU | Gap | Comp Plan PDF only | No public FLU polygon REST |
| appraiser / viewer link | Yes | NCPTS detail + ROKMAPS + ITSPublic | Templates below |

## Layers (verified)

### 1. RokMap Parcels Large Scale — parcels + CAMA + situs + sale + tax (PRIMARY)

- **REST:** https://arcgis4.roktech.net/arcgis/rest/services/Warren/RokMap/MapServer/4
- **Layer:** 4 · Polygon · county-wide · **23,585** features · max record count **1,000** · minScale **24000**
- **Fields:** `NEWPIN`/`MAPN`/`RECN` → parcel id; `ASSESSED_ACREAGE` → acreage; `NAME1`/`NAME2` → owner; `ADDR`/`CITY`/`STATE`/`ZIP` → mailing; `SITUS_ADDRESS` → situs; `LAND_VAL`/`BLDG_VAL`/`OTHER_VAL`/`ASSESSED_VAL` → tax; `SALE_PRICE`/`DEEDDATE`/`DEEDBOOK`/`DEEDPAGE` → last sale; `IMP_CODE` → use class.
- **Verified counts:** `ASSESSED_ACREAGE` 5–150 **5,949**; `SALE_PRICE>0` **11,948**; building zero/null in range **4,533**; `NAME1 IS NOT NULL` **23,526**.
- **Notes:** Primary wire-first layer. Companion **layer 3** (Small Scale, maxScale 24000) is the same CAMA set for zoomed-out display — prefer **/4** for queries. Paginate. Geo sample ~-78.27/36.33 (Warren).

### 2. RokMap Parcels Small Scale — display companion

- **REST:** https://arcgis4.roktech.net/arcgis/rest/services/Warren/RokMap/MapServer/3
- **Layer:** 3 · same schema/count as /4 · maxScale **24000**
- **Notes:** Do not treat as a second inventory; use /4.

### 3. NC OneMap parcels — statewide fallback

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer:** 1 · Polygon · filter `cntyfips='185'` · **23,477** Warren features · max record count **5,000**
- **Fields:** `parno`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`, **`recareano`** (acreage), `landval`/`improvval`/`parval`, `sourceref`/`sourcedate`, `cntyfips`.
- **Verified counts:** `recareano` 5–150 **5,942**; improvement zero/null in range **3,981**; `siteadd` populated **19,319**.
- **Notes:** **`gisacres` is entirely 0** for Warren — always use `recareano`. No sale price; `saledate` empty. `parno` ≈ county `NEWPIN`. Alternate host: https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1

### 4. RokMap Zoning — countywide parcelized (cities-first with Town Limits)

- **REST:** https://arcgis4.roktech.net/arcgis/rest/services/Warren/RokMap/MapServer/6
- **Layer:** 6 · Polygon · **24,069** features
- **Field:** `ZONING` → zoning
- **Districts:** AR **14,805**; R **5,075**; RL **3,605**; NB **483**; LB **53**; LI **20**; HB **20**; GC **5**; TC **2**
- **Notes:** Parcel-sized polygons covering county including towns. No separate Warrenton/Norlina/Macon FeatureServer found. Spatial join / filter with Town Limits for municipal routing.

### 5. Interstate Overlay District

- **REST:** https://arcgis4.roktech.net/arcgis/rest/services/Warren/RokMap/MapServer/5
- **Layer:** 5 · Polygon · **1** feature · `ZONING=IO`
- **Notes:** I-85 corridor overlay on base Zoning/6.

### 6. Future Land Use — honest gap

- **REST:** none
- **Status:** gap. Comp Plan 2022 PDF: https://www.warrencountync.com/DocumentCenter/View/5281/Warren-County-Comprehensive-Development-Plan-2022 (+ Appendix /5279). Do not invent a polygon REST URL.

### 7. Addresses — E-911 / situs points

- **REST:** https://arcgis4.roktech.net/arcgis/rest/services/Warren/RokMap/MapServer/1
- **Layer:** 1 · Point · **15,857** features
- **Fields:** `NEW_ADDR`, `ADD_NUM`, `ST_NAME`, `ST_TYPE`, `COMMUN`, etc.
- **Communities:** WARRENTON, NORLINA, MACON, LITTLETON, MANSON, HENRICO, HOLLISTER, EBONY, HENDERSON
- **Notes:** Optional; primary parcels already expose `SITUS_ADDRESS`.

### 8. Town Limits

- **REST:** https://arcgis4.roktech.net/arcgis/rest/services/Warren/RokMap/MapServer/8
- **Layer:** 8 · Polygon · **4** features · field `MB_NAME`
- **Values:** Warrenton, Norlina, Macon, Littleton
- **Parcel spatial counts:** Warrenton **778**; Norlina **703**; Macon **137**; Littleton tip **19**

### 9. Town ETJs

- **REST:** https://arcgis4.roktech.net/arcgis/rest/services/Warren/RokMap/MapServer/18
- **Layer:** 18 · Polygon · **2** features
- **Values:** Town of Warrenton ETJ; Town of Norlina ETJ

### 10. Subdivisions

- **REST:** https://arcgis4.roktech.net/arcgis/rest/services/Warren/RokMap/MapServer/7
- **Layer:** 7 · Polygon · **227** features · `SubName`
- **Notes:** Optional context.

## Jurisdiction routing (cities-first)

| Jurisdiction | Zoning source | FLU | Viewer / routing note |
|---|---|---|---|
| Warrenton | RokMap Zoning/6 clipped to Town Limits `MB_NAME=Warrenton` (~791) | Gap (Comp Plan PDF) | ROKMAPS; ETJ on /18 |
| Norlina | Zoning/6 ∩ Norlina limits (~701) | Gap | ROKMAPS; ETJ on /18 |
| Macon | Zoning/6 ∩ Macon limits (~142) | Gap | ROKMAPS; no ETJ poly |
| Littleton (Warren tip) | Zoning/6 ∩ Littleton limits (~19, all AR) | Gap | Mostly Halifax — use Halifax card outside tip |
| Unincorporated Warren | Zoning/6 (AR/R/RL dominant) + IO overlay /5 | Gap | ROKMAPS county view |

## Deep-link templates

- **PA / NCPTS detail:** `https://lrcpwa.ncptscloud.com/warren/parcel-detail/{NEWPIN}`
- **PA / NCPTS search:** https://lrcpwa.ncptscloud.com/warren/parcel-search
- **Appraisal card:** `https://www.bttaxpayerportal.com/ITSPublicWN/AppraisalCard.aspx?id={NEWPIN}`
- **Tax bill search:** `https://www.bttaxpayerportal.com/ITSPublicWN/TaxBillSearch/Parcel/{NEWPIN}`
- **Jurisdiction GIS viewer:** https://maps.roktech.net/ROKMAPS_Warren/

## Gaps and cautions

- No public FLU polygon REST; Comp Plan / Appendix are PDF-only.
- No independent municipal zoning FeatureServers (Warrenton / Norlina / Macon) — county Zoning/6 + Town Limits.
- Littleton is mostly Halifax County (Warren tip only).
- OneMap `gisacres` empty for Warren — use `recareano`; no OneMap sale price/date.
- OneMap `improvval` can lag county `BLDG_VAL`.
- RokMap layers 3/4 are scale duplicates — prefer /4; MaxRecordCount 1000.
- ITSPublic `RealEstateSearch` path not configured (HTTP 500); use NCPTS + AppraisalCard / TaxBillSearch.
- AppraisalCard is a thin ASP shell (card body loads via client script).
- webtaxpay.com endpoints are bot-challenged — not used as REST.
- No multi-transfer sales history beyond last deed on parcels.
- No paid vendor data, phones/emails, AADT, or utilities dig.

## Hand-off notes

1. **Wire first:** RokMap/4 for countywide polygons, owner, mailing, situs, tax, last sale, NEWPIN.
2. **Acreage:** `ASSESSED_ACREAGE` on /4; OneMap `recareano` (never `gisacres` here).
3. **Owner / tax / sale:** `NAME1`/`NAME2`; `LAND_VAL`/`BLDG_VAL`/`ASSESSED_VAL`; `SALE_PRICE`/`DEEDDATE`.
4. **Zoning:** cities-first via Town Limits/8 against Zoning/6; IO overlay /5 where applicable.
5. **PA detail:** `https://lrcpwa.ncptscloud.com/warren/parcel-detail/{NEWPIN}`.
6. **Jurisdiction GIS viewer:** https://maps.roktech.net/ROKMAPS_Warren/.
7. **Auth:** none observed on listed public query endpoints.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live quick checks (2026-09-24 ET):** RokMap/4 count **23,585**; SALE_PRICE>0 **11,948**; Zoning/6 **24,069**; Town Limits **4**; OneMap `cntyfips='185'` **23,477**; NCPTS search/detail SPA HTTP **200**; ITSPublicWN HTTP **200**; TaxBillSearch/Parcel/2914119156 HTTP **200**; ROKMAPS viewer HTTP **200**; county GIS page HTTP **200**.
- **Sample primary query:** `NEWPIN=2914119156` returned owner MUDHEN FAMILY FARMS LLC, land/bldg/assessed values, SALE_PRICE **635000**, DEEDDATE, situs 260 JONES CHAPEL RD.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://arcgis4.roktech.net/arcgis/rest/services/Warren/RokMap/MapServer/4 · id `NEWPIN` · live count **23,584** · 5–150 ac **5,948** (`ASSESSED_ACREAGE >= 5 AND ASSESSED_ACREAGE <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='WARREN'` gives **274** stations (116 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27WARREN%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Warren'` gives **273** stations (162 with AADT_2025, 174 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Warren%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Warren'` gives **273** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `ASSESSED_VAL` non-zero **23,525**, `LAND_VAL` non-zero **23,525**
- **Sale history (ok):** price `SALE_PRICE` >0 **11,944**; date `DEEDDATE` non-null **21,760**
- **Owner entity:** fields `NAME1`, `NAME2`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **716** of 5,948 (extended regex: 877).
- **PA deep link:** `https://www.bttaxpayerportal.com/ITSPublicWN/TaxBillSearch/Parcel/{NEWPIN}`. Tested `2937483505` → HTTP **200** (text/html), content verified: True. bttaxpayerportal TaxBillSearch 200 with ID in page. NCPTS parcel-detail/{NEWPIN} 200 SPA shell only — unverified.
- **Jurisdiction GIS viewer:** https://maps.roktech.net/ROKMAPS_Warren/ → HTTP **200** (ROKMAPS&trade;)
- **Pass 2 gaps:** none
