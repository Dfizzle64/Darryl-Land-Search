# Chowan County, NC — GIS County Card

## Summary

Chowan County (markets **[Eastern NC]**, FIPS **37041**, slug **chowan**, `cntyfips='041'`) publishes public AGOL FeatureServers under org owner **tpenegar** / **agdonline.maps.arcgis.com** (`services3.arcgis.com/nJbIFHiSnaX0z0hS`). **Wire-first parcels:** **Chowan_Feature_Service/FeatureServer/0** Parcels_Polygon (twin **/23** Parcels) — ~**12,888** polys (~**12,768** real `PIN`≠OUTSIDE) with owner (`OWNER1`/`OWNER2`), mailing (`MAILADDRESS1`/`MAILCITY`/`MAILSTATE`/`MAILZIPCODE`), situs (`SITUS_ADDR`), `ACRES`, tax fields `LAND_VAL`/`BLDG_VAL`/`DEF_VAL`/`TOT_VAL`/`OBXF_VAL` (**REST values mostly scrubbed to 0**), sale `SALE_PRICE`+`SALE_DT`/`DATE_REC`, zoning attr `ZONING_CDE`, deed `DEED_BK_PG`, parcel id `PIN`/`PIN_1`/`ACCT_NUM`, and **PRC** AppraisalCard deep-link. ~**2,153** with `ACRES` 5–150 (~**763** with `SALE_PRICE>0` in band). **Cities-first zoning:** **Edenton_Zoning** FS/16 (**420** polys; R-5/R-10/R-14/R-20/CH/CD/CN/IW/MA/SC/RA) PRIMARY for Town of Edenton; **County_Zoning** FS/15 (**77** polys; A-1/R-25/R-5/R-15/I-*/B-1/RMH-25/…) for county jurisdiction; parcel `ZONING_CDE` (~**12,553** non-empty) mirrors both. Only incorporated muni: **Edenton** (City_Limit FS/2 ALPHA=EDENTON). Unincorp communities Tyner/Hobbsville are not separate zoning jurisdictions. **FLU:** joint Chowan–Edenton CAMA LUP (certified 2018) PDF — Landuse FS/13 is weak (ALPHA C/W only), **no labeled FLU FeatureServer**. **PA:** ITS `http://taxonline.chowancountync.email/itspubliccw/AppraisalCard.aspx?id={PIN}` (PDF) + AGD print `?PIN=` + NCPTS `parcel-detail?reid={PIN}` + jurisdiction webappviewer / Experience Builder.

## Portals

- **Jurisdiction GIS (webappviewer / chowancountygis.com)** — https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=dc1c3a48141744c1a123bcad4e5cef50
- **Jurisdiction GIS (alias)** — http://www.chowancountygis.com/
- **Jurisdiction GIS (Experience Builder)** — https://experience.arcgis.com/experience/c156654f7d4b4a0fa8a240c6f09fe3b8
- **County Land Records** — https://www.chowancounty-nc.gov/land-records
- **County GIS page** — https://www.chowancounty-nc.gov/?SEC=C78A6AD6-60E6-4DF3-ACE1-2A20F1238FF8
- **County ArcGIS REST (AGOL)** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services
- **Chowan_Feature_Service** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Chowan_Feature_Service/FeatureServer
- **Chowan2021Sales** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Chowan2021Sales/FeatureServer
- **Tax Online / ITS Real Estate** — http://taxonline.chowancountync.email/itsnet/RealEstate.aspx
- **ITS AppraisalCard PDF (PA deep-link)** — `http://taxonline.chowancountync.email/itspubliccw/AppraisalCard.aspx?id={PIN}`
- **AGD print map** — `http://apps.agdmaps.com/print/nc/chowan/index.html?PIN={PIN}`
- **NCPTS Chowan hub** — https://lrcpwa.ncptscloud.com/Chowan/
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/Chowan/parcel-search
- **NCPTS deep-link (reid query)** — `https://lrcpwa.ncptscloud.com/Chowan/parcel-detail?reid={PIN}`
- **NCPTS deep-link (path)** — `https://lrcpwa.ncptscloud.com/Chowan/parcel-detail/{PIN}`
- **Tax pay (GovPayments / MuniciPay)** — https://www.govpayments.com/nc_chowan/search
- **Register of Deeds (Courthouse Computer Systems)** — https://us4.courthousecomputersystems.com/ChowanNC/
- **NC OneMap parcels** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='041'`)
- **Planning / Building** — https://www.chowancounty-nc.gov/building-planning
- **County Zoning Ordinance (hub)** — https://www.chowancounty-nc.gov/index.asp?SEC=%7B60CC2A8D-8C91-4266-A092-8206C3D8F31A%7D&Type=B_BASIC
- **County Zoning Art. 4 districts PDF** — https://www.chowancounty-nc.gov/vertical/sites/%7B10E82D50-AAE0-43D7-A98A-42E82683885E%7D/uploads/Article_4_Zoning_Districts_and_Zoning_Map.pdf
- **2018 Chowan–Edenton CAMA LUP PDF** — https://www.chowancounty-nc.gov/vertical/sites/%7B10E82D50-AAE0-43D7-A98A-42E82683885E%7D/uploads/Chowan-Edenton_LUP_Updated_10-25-18_Plan_and_Appendices_11-19-2018.pdf
- **DEQ certified LUP mirror** — https://files.nc.gov/ncdeq/Coastal%20Management/documents/PDF/Land%20Use%20Plans/ChowanEdentonLUPCertified_111518.pdf
- **DEQ Chowan LUP hub** — https://www.deq.nc.gov/about/divisions/coastal-management/coastal-management-land-use-planning/certified-lups/chowan-county
- **Edenton UDO hub** — https://www.townofedenton.com/planning-department/page/unified-development-ordinance

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`; OneMap `parno`; `PIN_1`/`ACCT_NUM` | PIN e.g. `791500844573` |
| polygons | Yes | Chowan_Feature_Service/0 (/23 twin); OneMap FS/1 | CRS **3359 / 3404** |
| acreage | Yes | `ACRES` (prefer); Shape__Area/43560; OneMap `recareano` (gisacres=0) | ~**2,153** in 5–150 |
| ownerName | Yes | `OWNER1`/`OWNER2`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `MAILADDRESS1`/`MAILADDRESS2`/`MAILCITY`/`MAILSTATE`/`MAILZIPCODE` | MAILCITY = mailing city, not situs muni |
| situs address | Yes | `SITUS_ADDR`; OneMap `siteadd` | |
| lastSale date/price | Yes | `SALE_PRICE` + `SALE_DT`/`DATE_REC`; Chowan2021Sales twin; OneMap `saledatetx` | Strong sale price on county REST |
| tax values | Partial | Fields `LAND_VAL`/`BLDG_VAL`/`DEF_VAL`/`TOT_VAL` present but **~all 0 on REST**; live values via AppraisalCard PDF | REST tax scrub gap |
| zoning | Yes (cities-first) | Edenton_Zoning/16 PRIMARY + County_Zoning/15 + parcel `ZONING_CDE` | Full suite |
| flu | Gap (PDF) | 2018 Chowan–Edenton CAMA LUP PDF; Landuse/13 ALPHA-only | No labeled FLU FS |
| appraiser / viewer link | Yes | AppraisalCard `id={PIN}` PDF; AGD print `?PIN=`; NCPTS; webappviewer/Experience | TRANCHE-3 |

### Municipality router (City Limits → city-first zoning)

| ALPHA (City_Limit/2) | Municipality | Zoning source |
|----------------------|--------------|---------------|
| EDENTON | **Edenton** (county seat; only incorporated muni) | Edenton_Zoning FS/16 PRIMARY (R-5/R-10/R-14/R-20/CH/CD/CN/IW/MA/SC/RA + CU-*); UDO hub |
| *(outside limits)* | Unincorporated (incl. Tyner, Hobbsville CDPs) | County_Zoning FS/15 + parcel ZONING_CDE (A1/R15/R5/R25/…) + County Development Codes |

**Note:** Parcel `MAILCITY` is **mailing** city (EDENTON 7428, TYNER 1314, HOBBSVILLE 208, …) — do **not** use as situs municipality; spatial-join City_Limit / Township (`TWP_NAME`: EDENTON/ROCKY HOCK/YEOPIM/WARDVILLE).

### Edenton_Zoning top districts (ZONE / LABEL)

| ZONE | LABEL | ~Count |
|------|-------|--------|
| R 5 | R-5 Residential | 116 |
| R 10 | R-10 Residential | 43 |
| CH | Highway Commercial | 42 |
| R 20 | R-20 Residential | 40 |
| R 14 | R-14 Residential | 29 |
| RA | RA | 25 |
| CN | Neighborhood Commercial | 17 |
| IW | Industrial | 16 |
| MA | Medical Arts | 14 |
| CD | Downtown Commercial | 12 |
| SC | Shopping Center | 5 |

### County_Zoning top districts

| ZONE | LABEL | ~Count |
|------|-------|--------|
| Residential 25 | R-25 | 20 |
| Agricultural | A-1 / A1 | 14 |
| Residential 5 | R-5 | 8 |
| Heavy Industrial | I-2 | 5 |
| Residential 15 | R-15 | 4 |
| Light Industrial | I-1 | 4 |
| General Business | B-1 | 4 |
| Residential MH25 | RMH-25 | 3 |

## Layers (verified 2026-09-24)

### 1. Chowan_Feature_Service/Parcels_Polygon — PRIMARY county AGOL CAMA (+ SALE_PRICE)

- **Purpose:** parcels | tax-fields | ownership | sale | zoning-attr | situs
- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Chowan_Feature_Service/FeatureServer/0
- **Twin:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Chowan_Feature_Service/FeatureServer/23
- **Key fields → targets:** `PIN`→parcelId; `PIN_1`→parcelIdAlt; `ACCT_NUM`→accountNumber; `OWNER1`/`OWNER2`→ownerName; `MAILADDRESS1`/`MAILCITY`/`MAILSTATE`/`MAILZIPCODE`→mailing; `SITUS_ADDR`→situs; `ACRES`→acreage; `LAND_VAL`/`BLDG_VAL`/`DEF_VAL`/`TOT_VAL`→tax (scrubbed); `SALE_PRICE`→lastSale.price; `SALE_DT`/`DATE_REC`→lastSale.date; `DEED_BK_PG`→deed; `ZONING_CDE`→zoning; `PRC`→appraiserDeepLink; `Print_`→agdPrintUrl; `TWP_NAME`→township; `TAXCDE`→taxCode; `SUBDIVISION`→subdivision
- **WKID / CRS:** 3359 / 3404 (NAD 1983 (2011) StatePlane NC Feet)
- **Verified:** count **12,888**; PIN≠OUTSIDE **12,768**; ACRES 5–150 → **2,153**; Shape acres 5–150 → **2,109**; OWNER1 non-null → **12,736**; SALE_PRICE>0 → **6,581**; sale+band → **763**; ZONING_CDE non-empty → **12,553**; PRC non-null → **12,788**; LAND_VAL>0 → **1** (scrub); TOT_VAL>0 → **1**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. Filter `PIN <> 'OUTSIDE'`. Field `PRC` embeds ITS AppraisalCard URL; `Print_` embeds AGD print URL. Geo-check PIN `688700852910` ZONING_CDE `A1` centroid ≈ **-76.673, 36.135** (Edenton township). Auth: none (public). **Tax REST values scrubbed** — open AppraisalCard PDF for live land/bldg/total.

### 2. NC OneMap Parcels — statewide REST fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='041'`
- **Key fields:** `parno`, `ownname`, mail/site, `gisacres` (**all 0**), `recareano`, `Shape__Area`, `landval`/`improvval`/`parval` (**all 0**), `saledate`/`saledatetx`
- **Verified:** count **25,690** (inflated vs county ~12.8k — prefer county); parno≠OUTSIDE **25,650**; ownname non-empty **25,438**; recareano 5–150 → **4,302**; Shape acres 5–150 → **4,244**; saledatetx≠''/'0' → **25,400**; **parval/landval/gisacres all 0**
- **Notes:** Join `parno`=`PIN`. Prefer county layer for SALE_PRICE/ZONING_CDE/PRC/ACRES. MaxRecordCount **5000**.

### 3. City Limits — municipality router

- **City_Limit_Polygon:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Chowan_Feature_Service/FeatureServer/2 — **1** poly, ALPHA=**EDENTON**
- **Use ALPHA** for city-first router (not mailing MAILCITY)

### 4. Zoning — cities-first Edenton + countywide County_Zoning

- **PRIMARY (Edenton):** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Chowan_Feature_Service/FeatureServer/16 — **420** polys; fields `ZONE`/`LABEL`
- **County (unincorp + county districts):** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Chowan_Feature_Service/FeatureServer/15 — **77** polys; fields `ZONE`/`LABEL`
- **Parcel attribute:** `ZONING_CDE` on /0 (~12,553 non-empty; top A1/R15/R5/R25/R10/R20/R14/…)
- **Supporting docs:** County Art. 4 Zoning Districts PDF; County Zoning Ordinance hub; Edenton UDO hub
- **VAD overlay:** FS/28 VAD_PARCELS (**219**) — not base zoning
- **Historic District:** FS/20 (**1**) overlay

### 5. FLU — gap (CAMA LUP PDF; Landuse ALPHA-only)

- County Planning hub lists **2018 Chowan–Edenton Land Use Plan**
- LUP PDF: https://www.chowancounty-nc.gov/vertical/sites/%7B10E82D50-AAE0-43D7-A98A-42E82683885E%7D/uploads/Chowan-Edenton_LUP_Updated_10-25-18_Plan_and_Appendices_11-19-2018.pdf (HTTP 200, ~16.5 MB)
- DEQ certified mirror: https://files.nc.gov/ncdeq/Coastal%20Management/documents/PDF/Land%20Use%20Plans/ChowanEdentonLUPCertified_111518.pdf
- Landuse FS/13 (**1,289** polys) — ALPHA only (`C`/`W`/` `) — **not usable labeled FLU**
- **No public labeled FLU FeatureServer** found 2026-09-24

### 6. Sales history twin

- **Chowan2021Sales:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Chowan2021Sales/FeatureServer/0 — **603** features; `SalePrice`/`SaleYear`/`ParcelNumb`/`PIN` — supplemental 2021 vintage join (prefer parcel-layer `SALE_PRICE` for current)

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS (webappviewer) | https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=dc1c3a48141744c1a123bcad4e5cef50 |
| Jurisdiction GIS (chowancountygis.com) | http://www.chowancountygis.com/ |
| Jurisdiction GIS (Experience) | https://experience.arcgis.com/experience/c156654f7d4b4a0fa8a240c6f09fe3b8 |
| ITS AppraisalCard PDF | `http://taxonline.chowancountync.email/itspubliccw/AppraisalCard.aspx?id={PIN}` |
| AGD print map | `http://apps.agdmaps.com/print/nc/chowan/index.html?PIN={PIN}` |
| NCPTS parcel detail (reid query) | `https://lrcpwa.ncptscloud.com/Chowan/parcel-detail?reid={PIN}` |
| NCPTS parcel detail (path) | `https://lrcpwa.ncptscloud.com/Chowan/parcel-detail/{PIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/Chowan/parcel-search |
| Tax Online Real Estate search | http://taxonline.chowancountync.email/itsnet/RealEstate.aspx |
| Tax pay | https://www.govpayments.com/nc_chowan/search |
| County Land Records hub | https://www.chowancounty-nc.gov/land-records |

Example: PIN `791500844573` → http://taxonline.chowancountync.email/itspubliccw/AppraisalCard.aspx?id=791500844573 (HTTP 200 **application/pdf**); AGD print HTTP 200; NCPTS reid/path HTTP 200 (SPA shell). Field `PRC` on the parcel layer already stores the AppraisalCard URL.

## Gaps

- **Tax REST value scrub** — `LAND_VAL`/`BLDG_VAL`/`TOT_VAL` fields exist but nearly all 0 on public AGOL/OneMap; use AppraisalCard PDF for live tax
- OneMap `cntyfips='041'` count inflated (~25.7k vs county ~12.8k); `gisacres`/`parval`/`landval` all 0 — use `recareano`/`Shape__Area` or prefer county `ACRES`
- FLU FeatureServer gap (CAMA LUP PDF only; Landuse/13 ALPHA C/W unusable as labeled FLU)
- Only one incorporated municipality (Edenton); Tyner/Hobbsville are unincorporated CDPs
- Parcel `MAILCITY` is mailing city — situs municipality requires City_Limit spatial join
- Courthouse Computer Systems ROD portal may 403 from some egress IPs (URL still canonical)
- `dl.agd.cc/prc/nc/chowan/` **404** — use ITS AppraisalCard, not AGD PRC PDF path
- Chowan2021Sales is 2021-vintage supplemental only
- Utilities / AADT / emails / phones / paid vendors intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** Chowan_Feature_Service/0 count/acres/owner/sale/ZONING_CDE/PRC + Edenton geo sample; /15 County_Zoning 77; /16 Edenton_Zoning 420; /2 City_Limit EDENTON; /13 Landuse ALPHA audit; Chowan2021Sales 603; OneMap `cntyfips='041'` counts (gisacres/tax empty; recareano OK); AppraisalCard PDF content-type; AGD print + NCPTS + webappviewer/Experience 200; County LUP PDF + Art. 4 Zoning PDF 200; rejected dl.agd.cc/prc/nc/chowan 404


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Chowan_Feature_Service/FeatureServer/0 · id `PIN` · live count **12,888** · 5–150 ac **2,153** (`ACRES >= 5 AND ACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='CHOWAN'` gives **170** stations (96 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CHOWAN%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Chowan'` gives **165** stations (112 with AADT_2025, 108 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Chowan%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (scrubbed):** `TOT_VAL` non-zero **1**, `LAND_VAL` non-zero **1**. Fallback: {"source": "PA AppraisalCard PDF (values present, Tax Year 2026 card verified for PIN 791500625865)", "note": "REST TOT_VAL/LAND_VAL/BLDG_VAL are 0 on all but 1 of 12,888 rows (TAXYEAR=2027 roll, values blanked); NC OneMap parval>0 for cntyfips=041 is also 0 of 25,690."}
- **Sale history (ok):** price `SALE_PRICE` >0 **6,581**; date `SALE_DT` non-null **12,717**, `DATE_REC` non-null **12,717**. SALE_DT is an integer yyyymmdd; DATE_REC is a date string.
- **Owner entity:** fields `OWNER1`, `OWNER2`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **334** (all parcels: 1,449), using the SQL approximation on `OWNER1`.
- **PA deep link:** `http://taxonline.chowancountync.email/itspubliccw/AppraisalCard.aspx?id={PIN}`. Tested `791500625865` → HTTP **200** (application/pdf), content verified: True. 200 application/pdf. Owner HOBBS, WENDELL LYNN, parcel id and Tax Year 2026 values verified in the PDF text (http; confirmed on retry).
- **Jurisdiction GIS viewer:** https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=dc1c3a48141744c1a123bcad4e5cef50 → HTTP **200** (ArcGIS Web Application); ArcGIS item access=public
- **Pass 2 gaps:** tax scrubbed
