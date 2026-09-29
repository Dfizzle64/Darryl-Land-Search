# Greene County, NC — GIS County Card

## Summary

Greene County (markets **[Greenville/Eastern NC]**, FIPS **37079**, slug **greene**, OneMap `cntyfips='079'`) publishes public AGOL FeatureServers under **services3.arcgis.com/nJbIFHiSnaX0z0hS** (AGD / `agdonline.maps.arcgis.com`; owner `tpenegar`). **Jurisdiction GIS** `http://www.greenecountygis.com/` redirects to **Greene Web App** webappviewer `id=336dd11e889546b7806dded487e3fc57`. **PRIMARY parcels:** **Greene_Service/FeatureServer/4** TaxParcels — ~**12,778** polys with owner (`OWNER_NAME_1`/`_2`), mailing, situs `PROPERTY_LOCATION`, `calc_acre`/`TOTAL_ACRES`, tax `CURRENT_LAND_VALUE`/`CURRENT_BLDG_VALUE`/`CURRENT_TOTAL_VALUE`, deed `DEED_DATE`/`DEED_BOOK`/`DEED_PAGE`, and embedded **`PRC`** AGD deep-link by `prc_ppn`. ~**3,605** with `calc_acre` 5–150 (~**2,328** CURRENT_BLDG_VALUE 0/null in band). **Sale price REST gap** — `ADJUSTED_SALE_PRICE` all 0/null; OneMap `saledate`/`saledatetx` empty. **Cities-first zoning:** **Snow Hill** (seat) `Snow_Hill_Zoning` FS/0 (**101**, `NAME`); **Hookerton** GreeneStatic/13 (**9**); **Walstonburg** GreeneStatic/15 (**8**); unincorporated **Greene_County_Zoning** FS/0 (**485**, `(AR)/(R)/(C)/(I)`). **Maury** = CDP/fire district only (not in TownLimits). **FLU:** county Comp Plan **in progress** (flyer PDF) + Snow Hill Comp Plan 2013 PDF; GreeneStatic/19 LandUse2016 `WOOD`/`CLEAR` = land cover **≠ FLU**. **PA:** AGD PRC `{prc_ppn}01.pdf` + NCPTS `{pin}` + webappviewer. Reject **Greene NY** AGOL + Spatialest 404.

## Portals

- **Jurisdiction GIS (greenecountygis.com → AGD Web App)** — http://www.greenecountygis.com/
- **Jurisdiction GIS (webappviewer)** — https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=336dd11e889546b7806dded487e3fc57
- **Viewer find template** — `https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=336dd11e889546b7806dded487e3fc57&find={pin}`
- **County AGOL REST org** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services
- **Greene_Service (parcels+addresses)** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Greene_Service/FeatureServer
- **GreeneStatic (zoning+limits+overlays)** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GreeneStatic/FeatureServer
- **GIS Department** — https://greenecountync.gov/departments/planning-and-inspections/gis/
- **Planning & Zoning** — https://greenecountync.gov/departments/planning-and-inspections/planning-and-zoning/
- **Tax Department** — https://greenecountync.gov/departments/tax/
- **Tax payments (Munis CSS)** — https://greenecounty.munisselfservice.com/citizens/default.aspx
- **PA / AGD PRC PDF (preferred deep-link)** — `https://dl.agd.cc/prc/nc/greene/{prc_ppn}01.pdf`
- **PA / AGD PRC viewer shell** — `https://dl.agd.cc/PRC/nc/greene/?pid={prc_ppn}01`
- **PA / NCPTS parcel search** — https://lrcpwa.ncptscloud.com/greene/parcel-search
- **PA NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/greene/parcel-detail/{pin}`
- **PA NCPTS alt (account)** — `https://lrcpwa.ncptscloud.com/greene/parcel-detail/{ACCOUNT_NO}`
- **Register of Deeds (Courthouse Computer Systems)** — https://greenenc.courthousecomputersystems.com/
- **County Ordinances hub** — https://greenecountync.gov/ordinances/
- **Zoning Ordinance (Google Drive)** — https://drive.google.com/file/d/1q8PnWMv8GT3uFmmX_NC9-ZB29iw0nIEu/view?usp=sharing
- **Subdivision Ordinance (Google Drive)** — https://drive.google.com/file/d/1uGPA_nQEyu6ucZO3vydzk5ixaT2r_MIn/view?usp=sharing
- **New Comp Land Use Plan (in progress)** — https://greenecountync.gov/new-greene-county-comprehensive-land-use-plan/
- **CLUP flyer PDF** — https://greenecountync.gov/wp-content/uploads/2026/07/GC-CLUP-Flyer.pdf
- **Town of Snow Hill** — https://www.snowhillnc.com/
- **Snow Hill Comp Plan 2013 PDF** — https://www.snowhillnc.com/document_center/Governments/Comprehensive%20Plan/Snow%20Hill%20Comp%20Plan%2012-17-13.pdf
- **Town of Hookerton** — https://www.hookertonnc.com/
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`) `cntyfips='079'`

## Municipalities (first-class)

| Municipality | Local public GIS? | Zoning / FLU source |
|--------------|-------------------|---------------------|
| **Snow Hill** (seat) | County AGOL host | **Snow_Hill_Zoning** FS/0 (**101**) `NAME` — city-first PRIMARY. FLU = Comp Plan **PDF** (2013) |
| **Hookerton** | County AGOL host | **Hookerton_Zoning** GreeneStatic/13 (**9**) `NAME` |
| **Walstonburg** | County AGOL host | **Walstonburg_Zoning** GreeneStatic/15 (**8**) `NAME` |
| **Maury** (CDP) | No | Fire district only; **not** in TownLimits — treat as unincorporated → County_Zoning |
| Unincorporated / GTP | County AGOL | **Greene_County_Zoning** FS/0 (**485**); GTP_Overlay/17 (1 poly) |

**TownLimits** GreeneStatic/6: Snow Hill, Hookerton, Walstonburg (+ blank). Parcel `CITY` is **mailing** city — do **not** use as situs municipality; spatial-join TownLimits.

### Snow Hill NAME (top; 101 polys)

| NAME | Count |
|------|-------|
| R-10 RESIDENTIAL | 32 |
| R-15 RESIDENTIAL | 28 |
| H-C HIGHWAY COMMERCIAL | 20 |
| R-20M RESIDENTIAL MFG HOMES | 10 |
| I-U INDUSTRIAL | 5 |
| C-D COMMERCIAL DOWNTOWN | 3 |
| R-20 RESIDENTIAL | 2 |
| R-8 RESIDENTIAL | 1 |

### County Zoning NAME (485 polys)

| NAME | Count |
|------|-------|
| (AR) AG/RURAL | 272 |
| (R) RESIDENTIAL | 151 |
| (C) COMMERCIAL | 57 |
| (I) INDUSTRIAL | 5 |

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `pin` (preferred); `parcelid`/`ACCOUNT_NO`; `prc_ppn`; OneMap `parno`/`altparno` | pin e.g. `3598556748`; altparno↔ACCOUNT_NO |
| polygons | Yes | Greene_Service/4; OneMap FS/1 | CRS **102719 / 2264** |
| acreage | Yes | `calc_acre` (prefer); `TOTAL_ACRES`; OneMap `gisacres` | ~**3,605** GIS 5–150 |
| ownerName | Yes | `OWNER_NAME_1`/`_2`/`_3`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `MAILING_ADDRESS_*`/`CITY`/`STATE_OR_COUNTRY`/`ZIP_CODE` | CITY = mailing, not situs muni |
| situs address | Yes | `PROPERTY_LOCATION`; AddrPts; OneMap `siteadd` | |
| lastSale date/price | Partial | **date** `DEED_DATE` YYYYMMDD + book/page; **price gap** | ADJUSTED_SALE_PRICE empty; OneMap sale empty |
| tax values | Yes | `CURRENT_LAND_VALUE`/`CURRENT_BLDG_VALUE`/`CURRENT_TOTAL_VALUE`; OneMap `parval`/`landval`/`improvval` | Strong |
| zoning | Yes (cities-first) | Snow Hill / Hookerton / Walstonburg / County layers `NAME` | Parcel ZONING attr null |
| flu | Gap (PDF) | Comp Plan in progress + Snow Hill Comp Plan PDF | LandUse2016 ≠ FLU |
| dorCode / land use | Partial | `CLASS` / `STATE_CLASS` | Not DOR codes |
| appraiser / viewer link | Yes | PRC `{prc_ppn}01`; NCPTS `{pin}`; webappviewer | TRANCHE-3 |

## Layers (verified)

### 1. Greene_Service / TaxParcels — PRIMARY (viewer wire-first)

- **Purpose:** parcels | tax | ownership | deed date | situs
- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Greene_Service/FeatureServer/4
- **Layer name / id:** TaxParcels / 4
- **Geometry:** Polygon | **CRS:** 102719 / 2264 | **MaxRecordCount:** 1000
- **Key fields → targets:** `pin`→parcelId; `parcelid`/`ACCOUNT_NO`→parcelIdAccount; `prc_ppn`/`PPN_2`→PA key; `calc_acre`/`TOTAL_ACRES`→acreage; `OWNER_NAME_*`→owner; mailing fields; `PROPERTY_LOCATION`→situs; `DEED_DATE`/`DEED_BOOK`/`DEED_PAGE`→lastSale.deed*; `ADJUSTED_SALE_PRICE`→lastSale.price (**empty**); `CURRENT_*_VALUE`/`TOTAL_ASSESSED`→tax; `CLASS`/`STATE_CLASS`; `FIRE_DISTRICT_NAME`/`TOWNSHIP_NAME`; **`PRC`**→appraiserSearchUrl
- **Verified:** count **12,778**; calc_acre 5–150 → **3,605**; TOTAL_ACRES 5–150 → **3,548**; CURRENT_TOTAL_VALUE>0 → **12,604**; owner → **12,645**; situs → **12,613**; PRC → **12,645**; DEED_DATE>0 → **11,783**; CURRENT_BLDG_VALUE=0/null in band → **2,328**; ADJUSTED_SALE_PRICE>0 → **0**
- **Geo-check:** pin `3598556748` / parcelid `0300720` centroid ≈ **-77.673, 35.353** (Grays Mill Rd / Hookerton Twp)
- **Notes:** **PRIMARY** wire-first. Paginate MRC 1000. Auth: none. Parcel `ZONING` all null.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='079'`
- **Key fields:** `parno`,`altparno`,`ownname`,`mailadd`/`mcity`,`siteadd`,`gisacres`,`parval`/`landval`/`improvval`
- **Verified:** count **12,720**; gisacres 5–150 → **3,606**; improvval=0/null in band → **2,324**; parval>0 → **12,573**; saledate/saledatetx → **0**
- **Join:** `parno`↔`pin`; `altparno`↔`parcelid`/`ACCOUNT_NO`
- **Notes:** No sale price/date. MaxRecordCount **5000**.

### 3. Snow_Hill_Zoning — city-first PRIMARY

- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Snow_Hill_Zoning/FeatureServer/0
- **GreeneStatic twin:** FS/14 (**100**)
- **Count:** **101** | field `NAME`
- **Notes:** Prefer dedicated FS/0 inside Snow Hill TownLimits.

### 4. Hookerton_Zoning — city-first

- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GreeneStatic/FeatureServer/13
- **Count:** **9** | `NAME` R-12 / RA-20 / IN-1 / R-15 / CBD / GBD

### 5. Walstonburg_Zoning — city-first

- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GreeneStatic/FeatureServer/15
- **Count:** **8** | `NAME` R-12 / GB-1 / CBD / R-15 / RA-20 / IN-1 / R-15M

### 6. Greene_County_Zoning — unincorporated

- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Greene_County_Zoning/FeatureServer/0
- **Twins:** GreeneStatic/12 (**479**); Greene_Zoning/0 (**485**)
- **Count:** **485** | `NAME` (AR)/(R)/(C)/(I)
- **Notes:** Prefer city layers inside munis; use for unincorporated + Maury CDP.

### 7. TownLimits / GTP / Townships (routers)

- **TownLimits:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GreeneStatic/FeatureServer/6 — Snow Hill, Hookerton, Walstonburg
- **GTP_Overlay_District:** GreeneStatic/17 — **1** poly `GTP DEVELOPMENT AREA`
- **Townships:** GreeneStatic/7 — Bull Head, Carrs, Hookerton, Jason, Olds, Ormonds, Shine, Snow Hill, Speights Bridge
- **Fire_Districts:** GreeneStatic/3 — ARBA, BULLHEAD, CASTORIA, FORT RUN, HOOKERTON, JASON, **MAURY**, SCUFFLETON, SHINE, SNOW HILL, WALSTONBURG

### 8. Address_Point — situs ZIP join

- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Greene_Service/FeatureServer/0
- **Count:** **~10,236** | NG911 fields `add_number`/`st_name`/`post_code`/`inc_muni`
- **Notes:** Prefer parcel `PROPERTY_LOCATION` when present; spatial join for ZIP.

### 9. Do-not-wire / wrong geography

- **services6…/EbVsqZ18sv1kVJ3k/Greene_County_Tax_Parcels** — **Greene County NY** (Windham ≈ -74.25, 42.37) — never use
- **greenecounty.prosgar.com / greenecountyassessor.org** — NY assessor / PROS — wrong state
- **property.spatialest.com/nc/greene** — **404**
- **webapp.agdmaps.com/nc/greene** / **apps.agdmaps.com/print/nc/greene** — **404**; use agdonline webappviewer
- **GreeneStatic/19 LandUse2016** — WOOD/CLEAR land cover — **not FLU**
- **Hydrants / Fire Stations / water** — utilities — excluded

## Cities / towns first-class routing

1. Inside **Snow Hill** TownLimits → Snow_Hill_Zoning FS/0
2. Inside **Hookerton** → GreeneStatic/13 Hookerton_Zoning
3. Inside **Walstonburg** → GreeneStatic/15 Walstonburg_Zoning
4. Else unincorporated (incl. **Maury** CDP) → Greene_County_Zoning FS/0; check GTP_Overlay/17

## Deep links (TRANCHE-3)

- **PA AGD PRC PDF (preferred):** `https://dl.agd.cc/prc/nc/greene/{prc_ppn}01.pdf`
- **PA AGD PRC shell:** `https://dl.agd.cc/PRC/nc/greene/?pid={prc_ppn}01`
- **PA field on layer:** `PRC` already stores shell URL
- **PA NCPTS:** `https://lrcpwa.ncptscloud.com/greene/parcel-detail/{pin}`
- **Jurisdiction GIS:** https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=336dd11e889546b7806dded487e3fc57
- **Alias homepage:** http://www.greenecountygis.com/

## Gaps

- **Sale price REST gap** — ADJUSTED_SALE_PRICE empty; OneMap saledate empty; deed date/book/page only
- **FLU REST gap** — Comp Plan in progress (flyer); Snow Hill Comp Plan PDF; LandUse2016 ≠ FLU
- Parcel ZONING attrs null — spatial join required
- Hookerton/Walstonburg zoning coarse (9/8 polys)
- Maury CDP has no municipal zoning REST
- AGD print / webapp.agdmaps greene path 404; Spatialest 404
- Reject Greene NY Tax Parcels org
- MaxRecordCount 1000 — paginate
- No phones/emails; no AADT/utilities; no paid vendors on this card

## License / verification

Greene County / AGD public AGOL + NC OneMap; public query endpoints; attribution recommended; no paid vendors.

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **method:** Live ArcGIS REST counts + field samples + WGS84 geo-check; AGD PRC PDF HTTP 200; NCPTS greene SPA shell; OneMap `cntyfips='079'`; municipal TownLimits + zoning NAME tallies; reject Greene NY centroid / Spatialest 404
