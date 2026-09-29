# Bertie County, NC — GIS County Card

## Summary

Bertie County (markets **[Eastern NC]**, FIPS **37015**, slug **bertie**, `cntyfips='015'`) publishes public AGOL FeatureServers under org **atlasgeodata** / **bertiecounty.maps.arcgis.com** (`services3.arcgis.com/tiupcc8dC1j2CPV5`). **Wire-first parcels:** **Bertie_Parcel_Viewer/FeatureServer/4** — ~**18,788** polys with owner (`OWNER`), mailing (`ADDR1`/`OWNCITY`/`OWNST`/`OWNZIP`), situs (`PARADDR`), `CALCACRE`/`DEEDACRE`/`ASDACRES`/`CALACRES`, tax `LANDVAL`/`BLDGVAL`/`DEFRVAL`/`TAXVAL`, use `PARCLASS`/`PARZONE`, deed `DEEDBKPG`, stamp `STAMPS`, parcel id `GEOPIN`/`GEOPIN27`, and **PRC** AppraisalCard PDF deep-link. ~**4,455** with `CALCACRE` 5–150 (~**3,402** vacant/no bldg in band; ~**1,570** with `STAMPS>0` in band). **No `SALE_PRICE` on REST** — `STAMPS` is excise-stamp proxy only (sale price REST **gap**). **Cities-first zoning:** parcel **`PARZONE`** attribute (~**6,331** non-empty) + **City Limits** Static/10 — **Windsor** PRIMARY (UDO + Zoning Map PDF; R-5/R-10/RA-20/… district codes on parcels); other munis carry PARZONE stubs (Aulander/Colerain/Lewiston/…). **No dedicated zoning FeatureServer.** Unincorporated Bertie **lacks countywide base zoning** (Subdivision Ordinance only). **FLU:** County CAMA LUP + **FLUM.pdf** (and related LUP maps) — **no FLU FeatureServer**. **PA:** AGD PRC `https://dl.agd.cc/prc/nc/bertie/{GEOPIN}.pdf` + NCPTS `parcel-detail?reid={GEOPIN}` + jurisdiction Experience Builder / webappviewer.

## Portals

- **Jurisdiction GIS (Experience Builder Parcel Viewer)** — https://experience.arcgis.com/experience/35c1e586958d4014b177c8b4082a9051
- **Jurisdiction GIS (webappviewer)** — https://bertiecounty.maps.arcgis.com/apps/webappviewer/index.html?id=6b7b91023ce84d778d1a207f75fe0454
- **County Tax / Mapping** — http://www.co.bertie.nc.us/departments/tm/tm.html
- **GIS shapefile downloads** — http://www.co.bertie.nc.us/departments/tm/shapedownload.html
- **Parcel polygons ZIP** — http://www.co.bertie.nc.us/departments/tm/gisdownloads/Parcel_Polygon.zip
- **MontyData CAMA DBF ZIP** — http://www.co.bertie.nc.us/departments/tm/gisdownloads/MontyData.zip
- **County ArcGIS REST (AGOL)** — https://services3.arcgis.com/tiupcc8dC1j2CPV5/arcgis/rest/services
- **Bertie_Parcel_Viewer** — https://services3.arcgis.com/tiupcc8dC1j2CPV5/arcgis/rest/services/Bertie_Parcel_Viewer/FeatureServer
- **Bertie_Static** — https://services3.arcgis.com/tiupcc8dC1j2CPV5/arcgis/rest/services/Bertie_Static/FeatureServer
- **NCPTS Bertie hub** — https://lrcpwa.ncptscloud.com/Bertie/
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/Bertie/parcel-search
- **NCPTS deep-link (reid query)** — `https://lrcpwa.ncptscloud.com/Bertie/parcel-detail?reid={GEOPIN}`
- **NCPTS deep-link (path)** — `https://lrcpwa.ncptscloud.com/Bertie/parcel-detail/{GEOPIN}`
- **AGD PRC / AppraisalCard PDF** — `https://dl.agd.cc/prc/nc/bertie/{GEOPIN}.pdf`
- **AGD site photos** — `https://dl.agd.cc/bertie/site-photos/?pid={GEOPIN}`
- **Tax pay portal** — http://bertie.webtaxpay.com/
- **Register of Deeds search** — https://search.bertiedeeds.com/
- **NC OneMap parcels** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='015'`)
- **Planning & Inspections** — http://bertiecounty.nc.gov/departments/pi/pi.html
- **County CAMA LUP hub** — http://bertiecounty.nc.gov/departments/pi/LUP/lup.html
- **County LUP PDF** — http://bertiecounty.nc.gov/departments/pi/LUP/LUP.pdf
- **County FLUM PDF** — http://bertiecounty.nc.gov/departments/pi/LUP/FLUM.pdf
- **Windsor UDO PDF** — https://windsornc.com/wp-content/uploads/2020/12/Amended-UDO_10-8-2020.pdf
- **Windsor Zoning Map PDF** — https://windsornc.com/wp-content/uploads/2020/04/Zoning-Map-8-22-18.pdf
- **Windsor codes / ordinances** — https://windsornc.com/codes-ordinances-and-regulations/
- **DEQ certified LUP (mirror)** — https://www.deq.nc.gov/documents/pdf/land-use-plans/bertie-county-lup-crc-certified-2-10-16/download

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `GEOPIN`; OneMap `parno`; `GEOPIN27`/`altparno` | GEOPIN e.g. `6863878402` |
| polygons | Yes | Bertie_Parcel_Viewer/4; OneMap FS/1; Parcel_Polygon.zip | CRS **102719 / 2264** |
| acreage | Yes | `CALCACRE` (prefer); `DEEDACRE`/`ASDACRES`/`CALACRES`; OneMap `gisacres` | ~**4,455** in 5–150 |
| ownerName | Yes | `OWNER`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `ADDR1`/`ADDR2`/`OWNCITY`/`OWNST`/`OWNZIP` | OWNCITY = mailing city, not situs muni |
| situs address | Yes | `PARADDR`; OneMap `siteadd` | |
| lastSale date/price | Partial | **stamp** `STAMPS`; deed `DEEDBKPG`; OneMap sale empty | **No SALE_PRICE**; saledate/saledatetx empty |
| tax values | Yes | `LANDVAL`/`BLDGVAL`/`DEFRVAL`/`TAXVAL`; OneMap `parval`/`landval`/`improvval` | Strong |
| zoning | Yes (cities-first attr) | Parcel `PARZONE` + City Limits; Windsor UDO/Map PDF | No zoning FS; unincorp unzoned |
| flu | Gap (PDF) | County LUP + FLUM.pdf (+ ECM/WM/LSM/PAM/BELU/SM) | No FLU FeatureServer |
| appraiser / viewer link | Yes | PRC `{GEOPIN}.pdf`; NCPTS `?reid={GEOPIN}`; Experience/webappviewer | TRANCHE-3 |

### Municipality router (City Limits CITY → city-first zoning)

| CITY (Static/10) | Municipality | ~Acres | Zoning source |
|------------------|--------------|--------|---------------|
| WINDSOR | **Windsor** (county seat) | ~1,709 | PARZONE district codes + UDO/Zoning Map PDF (city-first PRIMARY) |
| AULANDER | **Aulander** | ~1,040 | PARZONE stubs; no zoning FS |
| LEWISTON | **Lewiston-Woodville** | ~1,258 | PARZONE stubs; no zoning FS |
| ROXOBEL | **Roxobel** | ~667 | PARZONE stubs; no zoning FS |
| ASKEWVILLE | **Askewville** | ~366 | PARZONE stubs; no zoning FS |
| KELFORD | **Kelford** | ~328 | PARZONE stubs; no zoning FS |
| POWELLSVILLE | **Powellsville** | ~216 | PARZONE stubs; no zoning FS |
| COLERAIN | **Colerain** | ~173 | PARZONE stubs; no zoning FS |
| *(outside limits)* | Unincorporated | — | No countywide base zoning FS (Subdivision Ordinance only; VAD overlay present) |

**Note:** Parcel `OWNCITY` is **mailing** city (WINDSOR 5603, COLERAIN 2083, MERRY HILL 1242, AHOSKIE 1207, AULANDER 1010, LEWISTON WOODVILLE 844, …) — do **not** use as situs municipality; spatial-join City Limits / Boundary.

### Windsor PARZONE (TOWNSHIP=WINDSOR; top district codes)

| PARZONE | Count |
|---------|-------|
| R-5 SINGLE & 2 FAMILY RES DIST | 523 |
| R-10 SINGLE & 2 FAMILY RES DIST | 500 |
| RESIDENTIAL | 344 |
| R-5MH SINGLE FAMILY RES DISTRICT | 313 |
| RA-20 SINGLE FAMILY RES DISTRICT | 300 |
| HIGHWAY COMMERCIAL DISTRICT | 196 |
| CENTRAL BUSINESS | 112 |
| R-75 RESIDENTIAL DISTRICT | 60 |
| MANUFACTURING & INDUSTRIAL | 44 |
| OFFICE & INSTITUTIONAL | 14 |

Matches Town of Windsor Zoning Map legend (C-1/C-2/M-1/O-I/R-10/R-10MH/R-5/R-5MH/R-7/R-75/RA-20).

## Layers (verified 2026-09-24)

### 1. Bertie_Parcel_Viewer/Parcels — PRIMARY county AGOL CAMA (+ STAMPS)

- **Purpose:** parcels | tax | ownership | zoning-attr | situs
- **REST URL:** https://services3.arcgis.com/tiupcc8dC1j2CPV5/arcgis/rest/services/Bertie_Parcel_Viewer/FeatureServer/4
- **Also (legacy twin):** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Bertie_ParcelViewer/FeatureServer/4
- **Shapefile geometry:** http://www.co.bertie.nc.us/departments/tm/gisdownloads/Parcel_Polygon.zip (GEOPIN/CALCACRE only — join MontyData or AGOL for CAMA)
- **MontyData CAMA table:** http://www.co.bertie.nc.us/departments/tm/gisdownloads/MontyData.zip (OWNER/tax/PARZONE/STAMPS keyed by GEOPIN)
- **Key fields → targets:** `GEOPIN`→parcelId; `GEOPIN27`→parcelIdAlt; `OWNER`→ownerName; `ADDR1`/`OWNCITY`/`OWNST`/`OWNZIP`→mailing; `PARADDR`→situs; `CALCACRE`→acreage; `LANDVAL`/`BLDGVAL`/`DEFRVAL`/`TAXVAL`→tax; `PARCLASS`→dorCode/landUse; `PARZONE`→zoning; `DEEDBKPG`→deed; `STAMPS`→lastSale.stamps (proxy); `PRC`→appraiserDeepLink; `PIC_LINK`→sitePhotoUrl; `TOWNSHIP`→township; `NUMBLDG`→buildingCount
- **WKID / CRS:** 102719 / 2264
- **Verified:** count **18,788**; CALCACRE 5–150 → **4,455**; LANDVAL>0 → **18,731**; TAXVAL>0 → **18,731**; OWNER non-null → **18,731**; STAMPS>0 → **7,736**; stamps+band → **1,570**; vacant band → **3,402**; PARZONE non-empty → **6,331**; PRC non-null → **18,788**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **1000** — paginate. Geo-check GEOPIN `5892825294` PARZONE `RA-20…` centroid ≈ **-76.976, 35.992** (Windsor). Auth: none (public). **No SALE_PRICE field** — do not invent sale from STAMPS without local stamp schedule. Field `PRC` embeds AGD AppraisalCard PDF URL.

### 2. NC OneMap Parcels — statewide REST fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='015'`
- **Key fields:** `parno`, `altparno`, `ownname`, mail/site, `gisacres`, `Shape__Area`, `landval`/`improvval`/`parval`, `saledate`/`saledatetx` (empty here)
- **Verified:** count **18,788**; gisacres 5–150 → **4,455**; Shape__Area 5–150 → **4,430**; ownname **18,788**; parval>0 **18,731**; landval>0 **18,731**; **saledate 0**; **saledatetx non-empty 0**
- **Notes:** Join `parno`=`GEOPIN`. Prefer county layer for PARZONE/STAMPS/PRC. MaxRecordCount **5000**.

### 3. City Limits + Boundary + ETJ — municipality router

- **City Limits:** https://services3.arcgis.com/tiupcc8dC1j2CPV5/arcgis/rest/services/Bertie_Static/FeatureServer/10 — CITY ASKEWVILLE/AULANDER/COLERAIN/KELFORD/LEWISTON/ROXOBEL/WINDSOR/POWELLSVILLE (**8**)
- **Boundary (muni+township):** Bertie_Parcel_Viewer/FeatureServer/6 — **17** polys (includes townships)
- **ETJ:** Bertie_Static/FeatureServer/2 — **5** polylines (FTRCODE ETJ; no muni name field)
- **Use CITY** for city-first router (not mailing OWNCITY)

### 4. Zoning — cities-first via PARZONE + Windsor PDF (no zoning FS)

- **PRIMARY (Windsor):** parcel `PARZONE` district codes inside WINDSOR City Limits / Township; confirm against https://windsornc.com/wp-content/uploads/2020/04/Zoning-Map-8-22-18.pdf + UDO https://windsornc.com/wp-content/uploads/2020/12/Amended-UDO_10-8-2020.pdf
- **Other towns:** PARZONE attribute stubs present (no public district FeatureServer found 2026-09-24)
- **Unincorporated:** county FAQ/LUP — Bertie lacks countywide zoning; Subdivision Ordinance governs plats only
- **VAD overlay:** Bertie_Parcel_Viewer/FeatureServer/3 Voluntary_Agricultural (not base zoning)

### 5. FLU — gap (PDF / plan docs)

- County CAMA LUP hub: http://bertiecounty.nc.gov/departments/pi/LUP/lup.html
- LUP PDF: http://bertiecounty.nc.gov/departments/pi/LUP/LUP.pdf (covers unincorporated + Roxobel/Kelford/Aulander/Powellsville/Colerain/Lewiston-Woodville/Askewville; Windsor prepares individual LUP)
- FLUM PDF: http://bertiecounty.nc.gov/departments/pi/LUP/FLUM.pdf
- Related maps (HTTP 200): ECM.pdf, WM.pdf, LSM.pdf, PAM.pdf, BELU.pdf, SM.pdf
- DEQ certified mirror: https://www.deq.nc.gov/documents/pdf/land-use-plans/bertie-county-lup-crc-certified-2-10-16/download
- **No public FLU FeatureServer** found 2026-09-24

### 6. Supporting Parcel_Viewer layers

- Centerlines/0, Softlines/1, Subdivision/2, Voluntary_Agricultural/3, FireDistricts/5, Boundary/6

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS (Experience) | https://experience.arcgis.com/experience/35c1e586958d4014b177c8b4082a9051 |
| Jurisdiction GIS (webappviewer) | https://bertiecounty.maps.arcgis.com/apps/webappviewer/index.html?id=6b7b91023ce84d778d1a207f75fe0454 |
| AGD PRC / AppraisalCard PDF | `https://dl.agd.cc/prc/nc/bertie/{GEOPIN}.pdf` |
| AGD site photos | `https://dl.agd.cc/bertie/site-photos/?pid={GEOPIN}` |
| NCPTS parcel detail (reid query) | `https://lrcpwa.ncptscloud.com/Bertie/parcel-detail?reid={GEOPIN}` |
| NCPTS parcel detail (path) | `https://lrcpwa.ncptscloud.com/Bertie/parcel-detail/{GEOPIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/Bertie/parcel-search |
| Tax pay | http://bertie.webtaxpay.com/ |
| County Tax/Mapping hub | http://www.co.bertie.nc.us/departments/tm/tm.html |

Example: GEOPIN `6863878402` → https://dl.agd.cc/prc/nc/bertie/6863878402.pdf (HTTP 200 PDF); NCPTS reid query/path HTTP 200 (SPA shell). Field `PRC` on the parcel layer already stores the AGD PDF URL.

## Gaps

- **Sale price REST gap** — no `SALE_PRICE`/`SALEPRICE`; `STAMPS` excise-stamp proxy only; OneMap `saledate`/`saledatetx` empty for `cntyfips='015'`
- No dedicated zoning FeatureServer (cities-first via parcel `PARZONE` + Windsor UDO/Map PDFs; other towns stubs only)
- Unincorporated Bertie: no countywide base-zoning FS (Subdivision Ordinance + VAD overlay only)
- FLU FeatureServer gap (County CAMA LUP + FLUM.pdf only)
- Parcel_Polygon.zip is geometry/acres only — CAMA requires MontyData join or AGOL
- Parcel `OWNCITY` is mailing city — situs municipality requires City Limits spatial join
- ETJ layer is nameless polylines (no per-muni ETJ attribute)
- AGD print `apps.agdmaps.com/print/nc/bertie` **404** — use PRC PDF instead
- Utilities / AADT / emails / phones / paid vendors intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** Bertie_Parcel_Viewer/4 count/acres/tax/owner/STAMPS/PARZONE/PRC + Windsor geo sample; OneMap `cntyfips='015'` counts (sale empty); City Limits 8 munis; Boundary 17; ETJ 5; NCPTS reid + PRC PDF + Experience/webappviewer 200; Windsor UDO+Zoning Map PDF 200; County LUP+FLUM PDF 200; Parcel_Polygon+MontyData ZIP field audit; rejected AGD print 404
