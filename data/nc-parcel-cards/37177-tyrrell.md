# Tyrrell County, NC — GIS County Card

## Summary

Tyrrell County (markets **[Eastern NC]**, FIPS **37177**, slug **tyrrell**, `cntyfips='177'`) publishes public AGOL FeatureServers under org owner **tpenegar** / **agdonline.maps.arcgis.com** (`services3.arcgis.com/nJbIFHiSnaX0z0hS`). **Wire-first parcels:** **TyrrellService/FeatureServer/7** TaxParcels — ~**4,378** polys with owner (`NAME1`/`NAME2`), mailing (`ADDRESS`/`CITY`/`ST`/`ZIP`), situs (`F911HouseNumber`+`SitusRoad`; `NOTES1`), acreage (`ACRESPARCEL`/`ACRES`/`calcacres`/`deedacres`), tax `LANDVALUE`/`BLDGVALUE`/`OBLDGVALUE`/`PARCELVALUE`/`DEFERREDVALUE`/`LANDUSEVALUE`, sale `SALEAMOUNT`+`SALEDATE`+`SALEQUALIFIED`, parcel id `pin`/`mapid`/`SimpleMap`/`MASTERRECORD`, and **PRC** AppraisalCard deep-link. ~**1,164** with `ACRESPARCEL` 5–150 (~**965** vacant/no bldg in band; ~**323** with `SALEAMOUNT>0` in band). **Cities-first zoning:** only incorporated muni **Columbia** (`Town=1` ~**520** parcels; Municipal_area COLUMBIA) — zoning districts **A-1 / R-7 / R-7(PUD) / MF / MFM / B-1 / B-2 / I-1 / OS** per CAMA LUP Table 40 + Map 12 PDF; **no zoning FeatureServer**. Unincorporated Tyrrell **has no countywide zoning** (Subdivision Ordinance only; 2022 ISR: draft zoning never adopted). Parcel `ZONE1`/`ZONE2`/`ZONE3` are numeric stubs (**0**) — not usable district codes. **FLU:** joint Tyrrell–Columbia CAMA Core LUP (certified 2010) + Appendix II Maps 17A/17B — **no FLU FeatureServer**. **PA:** AGD PRC `http://dl.agd.cc/PRC/nc/Tyrrell/index.php?pid={MASTERRECORD}` (card JPG `cards/{MASTERRECORD}-1.jpg`) + NCPTS `parcel-detail?reid={pin}` + jurisdiction GIS `http://tyrrellcountygis.com/` → TyrrellWebApp.

## Portals

- **Jurisdiction GIS (alias → TyrrellWebApp)** — http://tyrrellcountygis.com/
- **Jurisdiction GIS (webappviewer)** — https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=1c2493cb8eb1484eb1ecc571131f5ee6
- **Jurisdiction GIS (legacy path still serves webapp)** — http://tyrrellcountygis.com/mapguide/tyrrellgis/
- **County site** — http://tyrrellcounty.org/en/
- **County map hub** — http://tyrrellcounty.org/en/map
- **County pay taxes / permits** — http://tyrrellcounty.org/en/pay-taxes-permits
- **County ArcGIS REST (AGOL)** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services
- **TyrrellService** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/TyrrellService/FeatureServer
- **AGD PRC / AppraisalCard (PA deep-link)** — `http://dl.agd.cc/PRC/nc/Tyrrell/index.php?pid={MASTERRECORD}`
- **AGD PRC card image** — `http://dl.agd.cc/PRC/nc/Tyrrell/cards/{MASTERRECORD}-1.jpg`
- **NCPTS Tyrrell hub** — https://lrcpwa.ncptscloud.com/Tyrrell/
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/Tyrrell/parcel-search
- **NCPTS deep-link (reid query)** — `https://lrcpwa.ncptscloud.com/Tyrrell/parcel-detail?reid={pin}`
- **NCPTS deep-link (path)** — `https://lrcpwa.ncptscloud.com/Tyrrell/parcel-detail/{pin}`
- **Tax pay (eGovPayments)** — https://tyrrellcounty.egovpayments.com/egov/apps/payment/center.egov?view=form;page=1;id=1359
- **Tax pay (WebTaxPay)** — http://tyrrell.webtaxpay.com/
- **NC OneMap parcels** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='177'`)
- **DEQ Tyrrell–Columbia CAMA LUP hub** — https://www.deq.nc.gov/about/divisions/coastal-management/coastal-management-land-use-planning/certified-lups/tyrrell-county
- **CAMA LUP PDF (certified 2010)** — https://www.deq.nc.gov/documents/pdf/land-use-plans/tyrrelllup/download
- **CAMA LUP PDF (files.nc.gov mirror)** — https://files.nc.gov/ncdeq/Coastal%20Management/documents/PDF/Land%20Use%20Plans/tyrrelllup.pdf
- **CAMA LUP Appendix II Maps (Map 12 Zoning + Maps 17A/17B FLU)** — https://www.deq.nc.gov/documents/pdf/land-use-plans/tyrrellcolumbiacamalupappendixii-maps-3-25-2010/download
- **CAMA LUP ISR 2022 (county)** — https://www.deq.nc.gov/coastal-management/planning/lup/isr/tyrrell-county-isr/download
- **Town of Columbia (site)** — https://townofcolumbianc.com/ (fetch may IP-block; zoning via LUP Map 12 / Table 40)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `pin`; OneMap `parno`; `mapid`/`SimpleMap`; `MASTERRECORD` | pin e.g. `7890400992` |
| polygons | Yes | TyrrellService/7; OneMap FS/1 | CRS **102719 / 2264** |
| acreage | Yes | `ACRESPARCEL` (prefer); `ACRES`; `calcacres` (~529 null); Shape__Area/43560; OneMap Shape/recareano (gisacres often 0) | ~**1,164** ACRESPARCEL 5–150; Shape ~**1,175** |
| ownerName | Yes | `NAME1`/`NAME2`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `ADDRESS`/`CITY`/`ST`/`ZIP` | CITY = mailing city, not situs muni |
| situs address | Yes | `F911HouseNumber`+`SitusRoad`; `NOTES1`; OneMap `siteadd` | |
| lastSale date/price | Yes | `SALEAMOUNT`+`SALEDATE`+`SALEQUALIFIED`; OneMap `saledatetx` (saledate null) | Strong sale price on county REST |
| tax values | Yes | `LANDVALUE`/`BLDGVALUE`/`OBLDGVALUE`/`PARCELVALUE`/`DEFERREDVALUE`; OneMap `parval`/`landval`/`improvval` | Strong |
| zoning | Partial (cities-first PDF) | Columbia Town=1 + LUP Table 40 / Map 12; unincorp unzoned | **No zoning FS**; ZONE1/2/3 stubs |
| flu | Gap (PDF) | CAMA LUP Maps 17A/17B + plan text | No FLU FeatureServer |
| appraiser / viewer link | Yes | PRC `pid={MASTERRECORD}`; NCPTS `?reid={pin}`; tyrrellcountygis.com | TRANCHE-3 |

### Municipality router (Municipal_area / Town → city-first zoning)

| Key | Municipality | ~Parcels | Zoning source |
|-----|--------------|----------|---------------|
| Municipal_area=`COLUMBIA`; parcel `Town=1` | **Columbia** (county seat; only incorporated muni) | ~520 (`Town=1`) | Cities-first PRIMARY — LUP Table 40 districts A-1/R-7/R-7(PUD)/MF/MFM/B-1/B-2/I-1/OS + Appendix II **Map 12**; no public zoning FeatureServer found 2026-09-24 |
| *(Town=0 / outside)* | Unincorporated (townships Alligator / Columbia / Gum Neck / Scuppernong / South Fork; CDPs/communities) | — | **No countywide base zoning** — Subdivision Ordinance only (ISR 2022: draft zoning never adopted) |

**Note:** Parcel `CITY` is **mailing** city — do **not** use as situs municipality; use `Town=1` / Municipal_area spatial join / Township (`TOWNSHIP` codes 1–11). OneMap `mcity` is a **0/1 Town flag**, not a city name.

### Columbia zoning districts (CAMA LUP Table 40 — planning jurisdiction acres)

| District | ~Acres | % |
|----------|--------|---|
| A-1 | 2,495 | 81.7% |
| R-7 | 237 | 7.7% |
| R-7 (PUD) | 92 | 3.0% |
| MF | 60 | 2.0% |
| B-2 | 142 | 4.7% |
| B-1 | 10 | 0.3% |
| OS | 18 | 0.6% |
| MFM / I-1 | 0 | — |

## Layers (verified 2026-09-24)

### 1. TyrrellService/TaxParcels — PRIMARY county AGOL CAMA (+ SALEAMOUNT)

- **Purpose:** parcels | tax | ownership | sale | situs
- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/TyrrellService/FeatureServer/7
- **Key fields → targets:** `pin`→parcelId; `mapid`/`SimpleMap`→mapNumber; `MASTERRECORD`→camaRecordId / PRC pid; `ACCOUNT`→accountNumber; `NAME1`/`NAME2`→ownerName; `ADDRESS`/`CITY`/`ST`/`ZIP`→mailing; `F911HouseNumber`+`SitusRoad`→situs; `NOTES1`→situsAlt; `ACRESPARCEL`→acreage (prefer); `ACRES`/`calcacres`/`deedacres`→acreageAlt; `LANDVALUE`/`BLDGVALUE`/`OBLDGVALUE`/`PARCELVALUE`→tax; `DEFERREDVALUE`/`LANDUSEVALUE`→tax.deferred/use; `SALEAMOUNT`→lastSale.price; `SALEDATE`→lastSale.date; `SALEQUALIFIED`→lastSale.qualified; `DEEDBOOK`/`DEEDPAGE`→deed; `Town`→inColumbia (1/0); `TOWNSHIP`→townshipCode; `PRC`→appraiserDeepLink
- **WKID / CRS:** 102719 / 2264
- **Verified:** count **4,378**; ACRESPARCEL 5–150 → **1,164**; ACRES 5–150 → **1,135**; Shape acres 5–150 → **1,175**; calcacres 5–150 → **1,023** (null **529**); LANDVALUE>0 → **4,186**; PARCELVALUE>0 → **4,294**; NAME1 non-null → **4,301**; SALEAMOUNT>0 → **1,456**; sale+ACRESPARCEL band → **323**; SALEQUALIFIED=Q → **985**; vacant ACRESPARCEL band → **965**; Town=1 → **520**; PRC non-null → **4,378**; ZONE1 non-empty → **0**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **1000** — paginate. Geo-check pin `8810716323` Town=1 centroid ≈ **-76.238, 35.920** (Columbia). Auth: none (public). Field `PRC` embeds AGD AppraisalCard URL with `pid={MASTERRECORD}` — **do not substitute pin** (PRC `?pin=` returns empty card list). Prefer `ACRESPARCEL` over often-null `calcacres`.

### 2. NC OneMap Parcels — statewide REST fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='177'`
- **Key fields:** `parno`, `altparno`, `ownname`, mail/site, `gisacres` (often 0), `recareano`, `Shape__Area`, `landval`/`improvval`/`parval`, `saledate` (empty), `saledatetx` (populated)
- **Verified:** count **4,368**; gisacres 5–150 → **1,034** (many gisacres=0); Shape acres 5–150 → **1,170**; recareano 5–150 → **786**; ownname **4,368**; parval>0 **4,272**; landval>0 **4,173**; **saledate 0**; saledatetx non-empty **4,368**
- **Notes:** Join `parno`=`pin`. Prefer county layer for SALEAMOUNT/PRC/Town. OneMap `mcity` is 0/1 (Town flag), not mailing city. MaxRecordCount **5000**.

### 3. Municipal_area + Township — municipality router

- **Municipal_area:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/TyrrellService/FeatureServer/4 — municipality **COLUMBIA** (**2** polys; town + ETJ/annexation footprint)
- **Township:** TyrrellService/FeatureServer/6 — ALLIGATOR / COLUMBIA / GUM NECK / SCUPPERNONG / SOUTH FORK (**5**)
- **Parcel flag:** `Town=1` ≈ Columbia (~520)

### 4. Zoning — cities-first Columbia PDF only (no zoning FS)

- **PRIMARY (Columbia):** CAMA LUP Table 40 districts + Appendix II **Map 12** Town of Columbia Zoning PDF — https://www.deq.nc.gov/documents/pdf/land-use-plans/tyrrellcolumbiacamalupappendixii-maps-3-25-2010/download
- **Parcel attrs:** `ZONE1`/`ZONE2`/`ZONE3` are **0 stubs** — do not use as district codes
- **Unincorporated:** no countywide zoning FS; Subdivision Ordinance + CAMA LUP policies only (ISR 2022 confirms draft zoning never adopted)

### 5. FLU — gap (PDF / plan docs)

- Joint Tyrrell–Columbia CAMA Core LUP (certified 2010-03-25): https://www.deq.nc.gov/documents/pdf/land-use-plans/tyrrelllup/download
- Appendix II Maps **17A** Tyrrell County Future Land Use + **17B** Town of Columbia Future Land Use
- DEQ hub: https://www.deq.nc.gov/about/divisions/coastal-management/coastal-management-land-use-planning/certified-lups/tyrrell-county
- ISR 2022: https://www.deq.nc.gov/coastal-management/planning/lup/isr/tyrrell-county-isr/download
- **No public FLU FeatureServer** found 2026-09-24

### 6. Supporting TyrrellService layers

- AddressPoint/0, Centerlines_Addressing/1, FirePoly/2, Flood_hazards/3, Parks_area/5, MapIndex/8, Buildings/9, soils/10

### 7. Rejected / empty twins

- **Tyrrell_parcels** FS/0,/2 — count **0** (empty publish); do not wire
- **TyrrellService_test** — test twin; prefer production TyrrellService/7
- **maps.agdmaps.com/nc/tyrrell/** — HTTP 404
- **apps.agdmaps.com/print/nc/tyrrell/** — HTTP 404
- **dl.agd.cc/prc/nc/tyrrell/{pin}.pdf** — HTTP 404 (use PRC index.php?pid=MASTERRECORD)

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS (alias) | http://tyrrellcountygis.com/ |
| Jurisdiction GIS (webappviewer) | https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=1c2493cb8eb1484eb1ecc571131f5ee6 |
| AGD PRC / AppraisalCard | `http://dl.agd.cc/PRC/nc/Tyrrell/index.php?pid={MASTERRECORD}` |
| AGD PRC card JPG | `http://dl.agd.cc/PRC/nc/Tyrrell/cards/{MASTERRECORD}-1.jpg` |
| NCPTS parcel detail (reid = pin) | `https://lrcpwa.ncptscloud.com/Tyrrell/parcel-detail?reid={pin}` |
| NCPTS parcel detail (path) | `https://lrcpwa.ncptscloud.com/Tyrrell/parcel-detail/{pin}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/Tyrrell/parcel-search |
| Tax pay (eGovPayments) | https://tyrrellcounty.egovpayments.com/egov/apps/payment/center.egov?view=form;page=1;id=1359 |
| Tax pay (WebTaxPay) | http://tyrrell.webtaxpay.com/ |
| County map hub | http://tyrrellcounty.org/en/map |

Example: pin `7890400992` / MASTERRECORD `9289` → http://dl.agd.cc/PRC/nc/Tyrrell/index.php?pid=9289 (HTTP 200; card `cards/9289-1.jpg` JPEG 200); NCPTS `?reid=7890400992` HTTP 200 (SPA shell). Field `PRC` on the parcel layer already stores the AGD URL.

## Gaps

- **No zoning FeatureServer** — cities-first Columbia via LUP Map 12 / Table 40 PDF only; parcel ZONE1/2/3 unusable stubs
- Unincorporated Tyrrell: **no countywide base-zoning FS** (Subdivision Ordinance; ISR 2022 draft zoning never adopted)
- FLU FeatureServer gap (CAMA LUP Maps 17A/17B PDF only)
- AGD print `apps.agdmaps.com/print/nc/tyrrell` **404**; maps.agdmaps.com/nc/tyrrell **404** — use tyrrellcountygis.com / webappviewer
- PRC PDF-by-PIN path 404; PRC `?pin=` empty — **must** use `pid={MASTERRECORD}`
- OneMap `gisacres` often 0 / `mcity` is Town flag / `saledate` null (use county SALEAMOUNT or OneMap saledatetx carefully)
- Tyrrell_parcels FeatureServer empty (0 features)
- Town of Columbia website may IP-block automated fetches — zoning documented via DEQ LUP maps
- Utilities / AADT / emails / phones / paid vendors intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** TyrrellService/7 count/acres/tax/owner/SALEAMOUNT/Town/PRC + Columbia geo sample; Municipal_area COLUMBIA; Township 5; OneMap `cntyfips='177'` counts; NCPTS reid + PRC pid JPG 200; tyrrellcountygis.com→webappviewer 200; CAMA LUP+Appendix II Maps+ISR PDF 200; rejected empty Tyrrell_parcels, AGD print/maps 404, PRC-by-PIN 404


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/TyrrellService/FeatureServer/7 · id `pin` · live count **4,378** · 5–150 ac **1,164** (`ACRESPARCEL >= 5 AND ACRESPARCEL <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='TYRRELL'` gives **80** stations (40 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27TYRRELL%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Tyrrell'` gives **76** stations (54 with AADT_2025, 44 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Tyrrell%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `PARCELVALUE` non-zero **4,294**, `LANDVALUE` non-zero **4,186**
- **Sale history (ok):** price `SALEAMOUNT` >0 **1,456**; date `SALEDATE` non-null **4,317**
- **Owner entity:** fields `NAME1`, `NAME2`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **253** (all parcels: 728), using the SQL approximation on `NAME1`.
- **PA deep link:** `http://dl.agd.cc/PRC/nc/Tyrrell/index.php?pid={MASTERRECORD}`. Tested `536` → HTTP **200** (text/html; charset=UTF-8), content verified: True. 200 HTML wrapper that embeds cards/{MASTERRECORD}-1.jpg (image card); id present in body.
- **Jurisdiction GIS viewer:** http://tyrrellcountygis.com/ → HTTP **200** (ArcGIS Web Application)
- **Pass 2 gaps:** none
