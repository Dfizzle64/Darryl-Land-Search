# Martin County, NC — GIS County Card

## Summary

Martin County (markets **[Eastern NC / Greenville shed]**, FIPS **37117**, slug **martin**, `cntyfips='117'`) publishes public ArcGIS REST under **gis.martincountyncgov.com**. **Wire-first parcels:** **TaxParcels/FeatureServer/0** (twin **ParcelMapSQLExpress/FeatureServer/22** ParcelPolygon) — ~**17,048** polys with owner (`OWNER_NAME_1`/`OWNER_NAME_2`), mailing, situs (`PROPERTY_LOCATION`), `ACRES`/`TOTAL_ACRES`, **SALE_PRICE** + sale date (`SALE_DATE2` typed / `SALE_DATE` YYYYMMDD), tax `CURRENT_TOTAL_VALUE`, parcel id `PARCEL_ID` / `MAP_BLOCK_LOT` / `PPN_2`. ~**3,588** with `ACRES` 5–150 (~**971** with sale price in band). **Cities-first zoning:** county **ZONING** FS/5 (**65** polys, `ZONE`) = **Williamston** (+ETJ) districts (CH/R*/M*/O&I/…); **Robersonville** zoning map PDF only; **Hamilton** ordinance exists (no public FS/PDF found); Bear Grass / Everetts / Hassell / Jamesville / Oak City / Parmele + **unincorporated** — **no countywide zoning** (EDC). **FLU:** County Comp Plan 2013 + NCDOT Future Land Use 2017 PDFs — **no FLU FeatureServer**. **PA:** ITSPublicMT `AppraisalCard.aspx?id={PARCEL_ID}` + PropertyRecordCards/`PropertyCards/{PARCEL_ID}-01.pdf` + NCPTS `parcel-detail/{PARCEL_ID}` + jurisdiction GIS `gis.martincountyncgov.com`.

## Portals

- **Jurisdiction GIS viewer** — https://gis.martincountyncgov.com/
- **County ArcGIS REST root** — https://gis.martincountyncgov.com/server/rest/services
- **TaxParcels FeatureServer** — https://gis.martincountyncgov.com/server/rest/services/TaxParcels/FeatureServer/0
- **ParcelMapSQLExpress (parcels+zoning+limits)** — https://gis.martincountyncgov.com/server/rest/services/ParcelMapSQLExpress/FeatureServer
- **ParcelMapNewDataLocation MapServer (twin stack)** — https://gis.martincountyncgov.com/server/rest/services/ParcelMapNewDataLocation/MapServer
- **GIS shapefile downloads** — https://gis.martincountyncgov.com/DataDownloads/ (`Parcels.zip`, `CityLimits.zip`, …)
- **GIS Downloads hub** — https://www.martincountync.gov/departments/tax_assessor/gis_downloads.php
- **Tax Assessor / Real Property** — https://www.martincountync.gov/departments/tax_assessor/real_property.php
- **Tax Collector search (Catalis)** — https://tax.martincountyncgov.com/taxSearch
- **ITSPublicMT AppraisalCard (PA deep-link)** — `https://bttaxpayerportal.com/itspublicmt/AppraisalCard.aspx?id={PARCEL_ID}`
- **ITSPublicMT BasicSearch** — https://bttaxpayerportal.com/itspublicmt/BasicSearch
- **ITSPublicMT TaxBillSearch** — https://bttaxpayerportal.com/itspublicmt/TaxBillSearch
- **Property Record Cards (GIS host)** — `https://gis.martincountyncgov.com/PropertyRecordCards/default.aspx?ID={PARCEL_ID}`
- **Property card PDF** — `https://gis.martincountyncgov.com/PropertyCards/{PARCEL_ID}-01.pdf`
- **NCPTS Martin hub / search** — https://lrcpwa.ncptscloud.com/martin/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/martin/parcel-detail/{PARCEL_ID}`
- **NC OneMap parcels** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='117'`)
- **County Comp Plan 2013 (FLU chapter)** — https://cms9files.revize.com/martincountync/Document%20Center/Government/Comprehensive%20Plan/ComprehensivePlan13.pdf
- **NCDOT / CTP Future Land Use map (2017)** — https://connect.ncdot.gov/projects/planning/TPBCTP/Martin%20County/Future%20Land%20Use%202017_0830.pdf
- **Williamston Comp Plan exec summary** — http://cms4files.revize.com/townofwilliamston/Williamston_CompPlan_ExecutiveSummary.pdf
- **Robersonville Zoning Map PDF** — https://robersonville.org/Robersonville_Zoning_Map_11-25-19.pdf
- **Robersonville Planning & Zoning** — https://robersonville.org/town_services/planning/index.php
- **EDC permitting / zoning note** — https://martincountyedc.com/permitting/
- **Unified Development Ordinance PDF** — https://www.martincountync.gov/Unified%20Development%20Ordinance.pdf
- **Towns directory** — https://www.martincountync.gov/how_do_i/find_martin_county_towns.php

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PARCEL_ID`; `MAP_BLOCK_LOT`; `PPN_2`; OneMap `parno` | PARCEL_ID e.g. `0300695`; MBL e.g. `5772-94-6258` |
| polygons | Yes | TaxParcels/0; ParcelMapSQLExpress/22; OneMap FS/1 | CRS **102719 / 2264** |
| acreage | Yes | `ACRES` (prefer); `TOTAL_ACRES`; `DEEDACRES`; OneMap `gisacres` / `Shape__Area/43560` | gisacres OK (~3647 in 5–150) |
| ownerName | Yes | `OWNER_NAME_1`/`OWNER_NAME_2`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `MAILING_ADDRESS`/`CITY`/`STATE`/`ZIP_CODE` | CITY = **mailing** city, not situs muni |
| situs address | Yes | `PROPERTY_LOCATION`; OneMap `siteadd` | |
| lastSale date/price | Yes | **price** `SALE_PRICE`; **date** `SALE_DATE2` (prefer) / `SALE_DATE` YYYYMMDD; OneMap `saledatetx` | OneMap `saledate` date field **null** here |
| tax values | Yes (total) | `CURRENT_TOTAL_VALUE`; OneMap `parval` | County land/improv split **absent**; OneMap landval/improvval **0** |
| zoning | Yes (cities-first) | Williamston `ZONE` FS/5; Robersonville PDF | Hamilton + other towns + unincorp REST gap |
| flu | Gap (PDF) | Comp Plan 2013 + NCDOT FLU 2017 PDFs | No FLU FeatureServer |
| appraiser / viewer link | Yes | ITSPublicMT `{PARCEL_ID}`; PropertyCards; NCPTS; GIS viewer | TRANCHE-3 |

### Municipality router (City Limits NAME → city-first zoning)

| NAME (City Limits) | Municipality | Annex polys | Zoning source |
|--------------------|--------------|-------------|---------------|
| WILLIAMSTON (+ AREA A / ORD#) | **Williamston** (seat) | 6+2 | County ZONING FS/5 `ZONE` (city-first PRIMARY) + WILLIAMSTON ETJ |
| ROBERSONVILLE | **Robersonville** | 1 | Zoning Map PDF (no FS) |
| HAMILTON | **Hamilton** | 1 | Ordinance exists per EDC; **no public FS/PDF** found; HAMILTON ETJ present |
| JAMESVILLE | **Jamesville** | 1 | No zoning ordinance (unzoned) |
| OAK CITY | **Oak City** | 1 | Unzoned |
| BEAR GRASS | **Bear Grass** | 1 | Unzoned |
| EVERETTS | **Everetts** | 1 | Unzoned |
| HASSELL | **Hassell** | 1 | Unzoned |
| PARMELE | **Parmele** | 1 | Unzoned |
| *(outside limits)* | Unincorporated | — | **No countywide zoning** (EDC) |

**Note:** Parcel `CITY` is **mailing** city (WILLIAMSTON ~7369, ROBERSONVILLE ~2073, JAMESVILLE ~1743, …) — do **not** use as situs municipality; spatial-join City Limits / ETJ.

### Williamston ZONE (top; 65 polys)

| ZONE | Count |
|------|-------|
| CH | 11 |
| O&I | 9 |
| M1 | 6 |
| R15 | 6 |
| R8 | 5 |
| M2 | 5 |
| R20-AO | 4 |
| R15-AO | 3 |
| CN | 3 |
| R10 | 3 |
| SHO | 2 |
| R8-MHO | 2 |
| R4 | 2 |
| CD / CDB / R4-MHO / None | 1 each |

Matches Williamston Comp Plan district set (CH, R*, M1/M2, O&I, SHO, MHO overlays).

## Layers (verified 2026-09-24)

### 1. TaxParcels — PRIMARY county CAMA + sale

- **Purpose:** parcels | tax | ownership | sales | situs
- **REST URL:** https://gis.martincountyncgov.com/server/rest/services/TaxParcels/FeatureServer/0
- **Also MapServer:** https://gis.martincountyncgov.com/server/rest/services/TaxParcels/MapServer/0
- **Twin:** ParcelMapSQLExpress/FeatureServer/22 ParcelPolygon (same schema/count)
- **Shapefile:** https://gis.martincountyncgov.com/DataDownloads/Parcels.zip
- **Key fields → targets:** `PARCEL_ID`→parcelId; `MAP_BLOCK_LOT`→parcelIdPin; `PPN_2`→parcelIdAlt; `OWNER_NAME_1`/`OWNER_NAME_2`→ownerName; `MAILING_ADDRESS`/`CITY`/`STATE`/`ZIP_CODE`→mailing; `PROPERTY_LOCATION`→situs; `ACRES`→acreage; `TOTAL_ACRES`→acreageReported; `DEEDACRES`→acreageDeed; `SALE_PRICE`→lastSale.price; `SALE_DATE2`→lastSale.date; `SALE_DATE`→lastSale.dateYyyymmdd; `CURRENT_TOTAL_VALUE`→tax.marketValue; `DEED_BOOK`/`DEED_PAGE`→deed; `LAST_UPDATE`→recordUpdatedYyyymmdd; `TOWNSHIP_NAME`/`DISTRICT_NO`→admin
- **WKID / CRS:** 102719 / 2264 (NAD83 NC ftUS)
- **Verified:** count **17,048**; ACRES 5–150 → **3,588**; TOTAL_ACRES 5–150 → **3,606**; Shape__Area/43560 5–150 → **3,591**; SALE_PRICE>0 → **6,057**; sale+band → **971**; SALE_DATE2 present → **6,186**; CURRENT_TOTAL_VALUE>0 → **16,917**; owner → **16,919**; situs → **16,919**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **1000** — paginate. Geo-check PARCEL_ID `0300695` / MBL `5772-94-6258` ≈ **-77.05, 35.71** (Williamston area). Auth: none (public). `SALE_DATE` numeric YYYYMMDD mirrors `SALE_DATE2`.

### 2. NC OneMap Parcels — statewide REST + saledatetx backup

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='117'`
- **Key fields:** `parno` (=PARCEL_ID), `ownname`, mail/site, `gisacres`, `Shape__Area`, `parval`, `saledatetx` (text)
- **Verified:** count **17,415**; gisacres 5–150 → **3,647**; Shape__Area 5–150 → **3,648**; ownname **17,415**; parval>0 **17,290**; saledatetx present **17,415**; **saledate date field null** (0); **landval/improvval all 0** — do not use for vacant filter
- **Notes:** Join `parno`=`PARCEL_ID`. Prefer county layer for **SALE_PRICE** + typed `SALE_DATE2`. Prefer OneMap `saledatetx` only as text backup. MaxRecordCount **5000**.

### 3. ZONING — city-first PRIMARY (Williamston)

- **REST:** https://gis.martincountyncgov.com/server/rest/services/ParcelMapSQLExpress/FeatureServer/5
- **Also:** ParcelMapNewDataLocation/MapServer/5; ParcelMapBITek/MapServer/5
- **Fields:** `ZONE`
- **Verified:** count **65** (2026-09-24); districts match Williamston Comp Plan
- **Notes:** Spatial-join inside Williamston City Limits / WILLIAMSTON ETJ (FS/7). Coarse district polygons. Robersonville/Hamilton **not** on this layer.

### 4. City Limits + ETJ — municipality router

- **City Limits:** ParcelMapSQLExpress/FeatureServer/6 — NAME WILLIAMSTON / ROBERSONVILLE / JAMESVILLE / OAK CITY / BEAR GRASS / EVERETTS / HASSELL / HAMILTON / PARMELE (+ WILLIAMSTON AREA A / ORD#) — **16** polys
- **WILLIAMSTON ETJ:** FeatureServer/7 — **1**
- **HAMILTON ETJ:** FeatureServer/8 — **1**
- **Shapefile:** https://gis.martincountyncgov.com/DataDownloads/CityLimits.zip
- **Use with NAME** for city-first router (not mailing `CITY`)

### 5. Robersonville zoning — PDF only (city-first secondary)

- Zoning Map PDF: https://robersonville.org/Robersonville_Zoning_Map_11-25-19.pdf (HTTP 200)
- Planning page: https://robersonville.org/town_services/planning/index.php
- **No public FeatureServer** found 2026-09-24

### 6. FLU — gap (PDF / plan docs)

- County Comp Plan 2013 (Section 6 Future Land Use Maps for unincorp + towns): https://cms9files.revize.com/martincountync/Document%20Center/Government/Comprehensive%20Plan/ComprehensivePlan13.pdf
- NCDOT CTP Future Land Use 2017 map: https://connect.ncdot.gov/projects/planning/TPBCTP/Martin%20County/Future%20Land%20Use%202017_0830.pdf (Regional/Local Service Node, Industrial, Town Center, Neighborhood Mixed Use, Rural Transition, Agricultural Mixed Use, Rural Protection, Conservation)
- Williamston Comp Plan / FLU narrative: http://cms4files.revize.com/townofwilliamston/Williamston_CompPlan_ExecutiveSummary.pdf
- **No public FLU FeatureServer** found 2026-09-24

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS viewer | https://gis.martincountyncgov.com/ |
| ITSPublicMT AppraisalCard (PRIMARY) | `https://bttaxpayerportal.com/itspublicmt/AppraisalCard.aspx?id={PARCEL_ID}` |
| ITSPublicMT BasicSearch | https://bttaxpayerportal.com/itspublicmt/BasicSearch |
| ITSPublicMT TaxBillSearch | https://bttaxpayerportal.com/itspublicmt/TaxBillSearch |
| Property Record Cards (GIS) | `https://gis.martincountyncgov.com/PropertyRecordCards/default.aspx?ID={PARCEL_ID}` |
| Property card PDF | `https://gis.martincountyncgov.com/PropertyCards/{PARCEL_ID}-01.pdf` |
| NCPTS parcel detail | `https://lrcpwa.ncptscloud.com/martin/parcel-detail/{PARCEL_ID}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/martin/parcel-search |
| Tax Collector search | https://tax.martincountyncgov.com/taxSearch |
| Tax Assessor hub | https://www.martincountync.gov/departments/tax_assessor/real_property.php |

Example: PARCEL_ID `0300695` → https://bttaxpayerportal.com/itspublicmt/AppraisalCard.aspx?id=0300695 (HTTP 200 PDF); https://gis.martincountyncgov.com/PropertyRecordCards/default.aspx?ID=0300695 (HTTP 200); https://lrcpwa.ncptscloud.com/martin/parcel-detail/0300695 (HTTP 200 SPA). Viewer config `?pin=` uses legacy `PIN15` field (**not on ParcelPolygon**) — prefer AppraisalCard / PropertyRecordCards over fragile GIS querystring.

## Gaps

- No public zoning FeatureServer for Robersonville (PDF only) or Hamilton (ordinance only)
- Bear Grass, Everetts, Hassell, Jamesville, Oak City, Parmele unzoned; unincorporated Martin has **no countywide base zoning**
- FLU FeatureServer gap (Comp Plan 2013 + NCDOT FLU 2017 + Williamston Comp Plan PDFs only)
- County parcels lack land/improvement value split (total only); OneMap landval/improvval empty for `cntyfips='117'`
- OneMap `saledate` date field null — use county `SALE_DATE2`/`SALE_DATE` or OneMap `saledatetx`
- Parcel `CITY` is mailing city — situs municipality requires City Limits/ETJ spatial join
- GIS viewer `?pin=` deep-link config references missing `PIN15` field — fragile
- Williamston town website host DNS unresolved from research box (use revize CMS / Comp Plan PDFs)
- Utilities / AADT / emails / phones / paid vendors intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** TaxParcels/0 count/acres/sale/tax/owner + geo sample; ParcelPolygon twin 17048; OneMap `cntyfips='117'` counts + saledatetx + parno join; ZONING 65 + districts; City Limits 9 munis / ETJ 2; ITSPublicMT AppraisalCard + PropertyCards PDF + NCPTS + GIS viewer + Comp Plan/FLU/Robersonville PDF 200; DataDownloads Parcels.zip 200
