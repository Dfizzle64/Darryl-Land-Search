# Washington County, NC — GIS County Card

## Summary

Washington County (markets **[Eastern NC]**, FIPS **37187**, slug **washington**, `cntyfips='187'`) publishes public AGOL FeatureServers under org **WashingtonCountyGIS** / **washconc.maps.arcgis.com** (`services6.arcgis.com/hBMRLv0wWV0IhJ8I`). **Wire-first parcels:** **Washington_Service/FeatureServer/9** Parcels_in_use — ~**12,630** polys with owner (`Owner`/`OwnerName2`), mailing (`AddressLine*`), situs (`PropertyLocation`), `CalculatedAcres`/`LandAcres`, **SalePrice** + `SaleDate` + `Qualified`, tax `LandAssessedValue`/`BldgAssessedValue`/`TotalAssessedValue`, parcel id `NCPin`/`Pin`/`parcel_num`/`WCParcel`, and embedded **PropRecCard** + AGD **Print_** deep-links. ~**1,800** with `CalculatedAcres` 5–150 (~**617** with sale price in band; ~**1,372** vacant/no bldg in band). **Cities-first zoning:** **PLYMOUTH_ZONING/21** PRIMARY (**313** `DISTRICT` polys) for **Plymouth**; **Roper** / **Creswell** city-limits + ETJ only (no zoning FS); county **Zoning/10** is **CI stubs only (24)** — Official Zoning Map not fully digitized (Zoning Ordinance PDF applies outside town limits/ETJ; default R-A). **FLU:** DEQ CAMA LUP edocs (county 1994 Under Review; Plymouth CAMA Comp/Strategic certified 2024-06-24) — **no FLU FeatureServer** (`landuse/5` LUSE W/C = existing LU, reject as FLU). **PA:** taxweb `Parcel.aspx?{WCParcel}` + AGD print `?NCPIN={NCPin}` + NCPTS `parcel-detail?reid={NCPin}` + jurisdiction Experience Parcel Viewer / webappviewer.

> **Not Beaufort:** City of Washington is in **Beaufort County (37013)**. This card is **Washington County** (seat **Plymouth**).

## Portals

- **Jurisdiction GIS (Parcel Viewer Experience)** — https://experience.arcgis.com/experience/3bffabc4dd484e1bbfa49186361dce5d
- **Jurisdiction GIS (webappviewer)** — https://washconc.maps.arcgis.com/apps/webappviewer/index.html?id=1a51e666286842138be02492cab0ec95
- **Online Land Records (Experience)** — https://experience.arcgis.com/experience/dd9851d8899942f1a03842e372b2c228/
- **Office Viewer (webappviewer)** — https://washconc.maps.arcgis.com/apps/webappviewer/index.html?id=e1513afa991c41e0b0206c1bc492b156
- **Experience alt** — https://experience.arcgis.com/experience/907e4539cc314066b1103d475b23cbdb
- **County AGOL REST root** — https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services
- **Washington_Service** — https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services/Washington_Service/FeatureServer
- **Parcels (GIS twin)** — https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services/Parcels/FeatureServer/0
- **PLYMOUTH_ZONING** — https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services/PLYMOUTH_ZONING/FeatureServer/21
- **Tax web / Property & Building Records (PA)** — http://taxweb.washconc.org/
- **PA deep-link** — `http://taxweb.washconc.org/Parcel.aspx?{WCParcel}`
- **AGD print deep-link** — `https://apps.agdmaps.com/print/nc/washington/index.html?NCPIN={NCPin}`
- **NCPTS Washington hub** — https://lrcpwa.ncptscloud.com/Washington/
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/Washington/parcel-search
- **NCPTS deep-link (reid query)** — `https://lrcpwa.ncptscloud.com/Washington/parcel-detail?reid={NCPin}`
- **NCPTS deep-link (path)** — `https://lrcpwa.ncptscloud.com/Washington/parcel-detail/{NCPin}`
- **County website** — https://washconc.org/
- **Tax Office** — https://washconc.org/tax-office/
- **Planning & Inspections** — https://washconc.org/planning-and-inspections/
- **Ordinances hub** — https://washconc.org/ordinances/
- **Zoning Ordinance PDF (2021)** — https://washconc.org/wp-content/uploads/2022/04/2021-Zoning-Ordinance-Updated-for-7-1-2021-160-D-changes.pdf
- **Subdivision Ordinance PDF (2026)** — https://washconc.org/wp-content/uploads/2026/03/Washington-County-Subdivision-Ordinance-March-16-2026-jjb.pdf
- **NC OneMap parcels** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='187'`)
- **DEQ certified CAMA LUP hub** — https://www.deq.nc.gov/about/divisions/division-coastal-management/coastal-management-land-use-planning/certified-lups/washington-county
- **DEQ county Plan (edocs id=247907)** — https://edocs.deq.nc.gov/CoastalManagement/DocView.aspx?dbid=0&id=247907
- **DEQ Plymouth CAMA Comp/Strategic Plan (edocs id=329963)** — https://edocs.deq.nc.gov/CoastalManagement/DocView.aspx?dbid=0&id=329963
- **NCDOT CTP hub** — https://connect.ncdot.gov/projects/planning/Pages/CTP-Details.aspx?study_id=Washington%20County
- **NCDOT CTP REPORT PDF** — https://connect.ncdot.gov/projects/planning/TPBCTP/Washington%20County/REPORT.pdf

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `NCPin`; OneMap `parno`; `Pin`/`TAX_PIN`; `parcel_num`/`WCParcel` | NCPin e.g. `7841626695` |
| polygons | Yes | Washington_Service/9; Parcels/0; OneMap FS/1 | CRS **3359 / 3404** |
| acreage | Yes | `CalculatedAcres` (prefer); `LandAcres`; `parcels__1`; OneMap `gisacres` | ~**1,800** in 5–150 |
| ownerName | Yes | `Owner`/`OwnerName2`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `AddressLine1`–`4`/`ZipCode` | AddressLine2 often city/state; not situs muni |
| situs address | Yes | `PropertyLocation`; OneMap `siteadd` | scity empty on OneMap |
| lastSale date/price | Yes | **price** `SalePrice`; **date** `SaleDate`; `Qualified`; OneMap `saledatetx` | OneMap `saledate` date field **null** |
| tax values | Yes | `LandAssessedValue`/`BldgAssessedValue`/`TotalAssessedValue`; OneMap `parval`/`landval`/`improvval` | Strong |
| zoning | Yes (cities-first) | Plymouth `DISTRICT`/`NAME` FS/21; county CI stubs | Roper/Creswell/unincorp REST gap |
| flu | Gap (PDF/edocs) | DEQ CAMA LUP + Plymouth 2024 plan | No FLU FeatureServer; reject landuse/5 |
| appraiser / viewer link | Yes | taxweb `{WCParcel}`; AGD print `{NCPin}`; NCPTS; Experience/webappviewer | TRANCHE-3 |

### Municipality router (City_Limits CITY / MunicipalBoundaryName → city-first zoning)

| CITY / Name | Municipality | ~Acres | Zoning source |
|-------------|--------------|--------|---------------|
| PLYMOUTH | **Plymouth** (county seat) | ~2,503 | PLYMOUTH_ZONING/21 PRIMARY (313) + Plymouth ETJ |
| ROPER | **Roper** | ~543 | City limits + Roper ETJ; **no zoning FS** |
| CRESWELL | **Creswell** | ~264 | City limits + Old Creswell ETJ; **no zoning FS** |
| *(outside limits)* | Unincorporated | — | Zoning Ordinance PDF (R-A default + C-C + overlays); Zoning/10 CI stubs only (24); Official Zoning Map REST gap |

**Note:** Parcel mailing city (`AddressLine2` / Parcels/0 `CITY`) is **mailing** — do **not** use as situs municipality; spatial-join City_Limits / Municipal / ETJ. `TownFlag` I≈inside town (~2966) / O≈outside (~7363).

### Plymouth DISTRICT (top; 313 polys)

| DISTRICT | Count | NAME (sample) |
|----------|-------|---------------|
| R10 | 56 | SINGLE FAMILY RESIDENTIAL |
| R7 | 54 | SINGLE / MULTI-FAMILY |
| R20 | 51 | SINGLE FAMILY RESIDENTIAL |
| C2 | 37 | HIGHWAY BUSINESS |
| R20A | 23 | — |
| R15 | 20 | — |
| OI | 18 | OFFICE AND INSTITUTIONAL |
| C | 18 | CONSERVATION |
| IL | 17 | LIGHT INDUSTRIAL |
| IH | 10 | HEAVY INDUSTRIAL |
| C1 | 6 | CENTRAL BUSINESS |
| R7A | 3 | MULTI-FAMILY |

## Layers (verified 2026-09-24)

### 1. Washington_Service/Parcels_in_use — PRIMARY county AGOL CAMA + sale

- **Purpose:** parcels | tax | ownership | sales | situs
- **REST URL:** https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services/Washington_Service/FeatureServer/9
- **Also (legacy twin):** Washington_Service/FeatureServer/11 Parcels_old (same schema)
- **GIS geometry twin:** https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services/Parcels/FeatureServer/0 (weaker CAMA — no SalePrice/tax)
- **Key fields → targets:** `NCPin`→parcelId; `Pin`/`parcels_ta`→parcelIdDashed; `parcel_num`/`TaxpayerNumber`→acct; `WCParcel`→webId; `Owner`/`OwnerName2`→ownerName; `AddressLine*`/`ZipCode`→mailing; `PropertyLocation`→situs; `CalculatedAcres`→acreage; `LandAcres`→acreageCama; `SalePrice`→lastSale.price; `SaleDate`→lastSale.dateText; `Qualified`→lastSale.qualified; `LandAssessedValue`/`BldgAssessedValue`/`TotalAssessedValue`→tax; `PropertyClass`→dorCode; `TypeUse`→landUseDescription; `PropRecCard`→appraiserDeepLink; `Print_`→agdPrintUrl; `TownFlag`→insideTownFlag
- **WKID / CRS:** 3359 / 3404 (NAD83 2011 NC ftUS)
- **Verified:** count **12,630**; CalculatedAcres 5–150 → **1,800**; LandAcres 5–150 → **1,943**; Shape__Area/43560 5–150 → **1,999**; SalePrice>0 → **4,374**; sale+band → **617**; TotalAssessedValue>0 → **10,326**; LandAssessedValue>0 → **10,323**; BldgAssessedValue>0 → **5,348**; vacant band → **1,372**; Owner → **10,331**; PropRecCard/Print_ → **12,630**; Qualified Qual → **2,036** / Disq → **7,632**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **1000** — paginate. Geo-check NCPin `6767312559` / WCParcel `4842` TownFlag=I centroid ≈ **-76.762, 35.849** (Plymouth). Auth: none (public). `SaleDate` mixed YYYYMMDD and M/D/YYYY — normalize. Field `PropRecCard` embeds taxweb URL; `Print_` embeds AGD print URL.

### 2. NC OneMap Parcels — statewide REST + saledatetx backup

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='187'`
- **Key fields:** `parno` (=NCPin), `altparno`, `ownname`, mail/site, `gisacres`, `Shape__Area`, `landval`/`improvval`/`parval`, `saledatetx` (text)
- **Verified:** count **12,608**; gisacres 5–150 → **2,000**; ownname **12,608**; parval>0 **10,297**; landval>0 **10,294**; improvval>0 **6,228**; vacant band → **1,334**; saledatetx nonempty **9,558** (excl `00000000` → **8,458**); **saledate date field null (0)**; scity empty (0)
- **Notes:** Join `parno`=`NCPin`. Prefer county layer for **SalePrice** + typed tax. Prefer OneMap `saledatetx` only as text backup. MaxRecordCount **5000**.

### 3. PLYMOUTH_ZONING — city-first PRIMARY

- **REST:** https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services/PLYMOUTH_ZONING/FeatureServer/21
- **Fields:** `DISTRICT`, `NAME`
- **Verified:** count **313** (2026-09-24)
- **Notes:** Spatial-join inside Plymouth City_Limits / Plymouth ETJ. Roper/Creswell **not** on this layer.

### 4. County Zoning /10 — CI stubs only (partial)

- **REST:** https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services/Washington_Service/FeatureServer/10
- **Verified:** count **24**, all `ZONE='CI'`
- **Notes:** Incomplete Official Zoning Map digitization. County Zoning Ordinance (Art. 1.F) applies **outside** town corporate limits and ETJ; default unclassified → **R-A** Rural Areas; also **C-C** Corridor Commercial + overlays. Confirm against ordinance PDF + Planning office Official Zoning Map.

### 5. Municipal + City_Limits + ETJ — municipality router

- **Municipal:** https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services/Static/FeatureServer/0 — Plymouth / Roper / Creswell (**3**)
- **City_Limits:** InternalLayers/FeatureServer/40 — CITY PLYMOUTH/ROPER/CRESWELL (**3**)
- **ETJ:** InternalLayers/FeatureServer/41 — TWNSHP PLYMOUTH / ROPER / OLD CRESWELL ETJ (**3**)
- **Use CITY / MunicipalBoundaryName** for city-first router (not mailing AddressLine2)

### 6. FLU — gap (DEQ CAMA edocs / plan docs)

- DEQ hub: https://www.deq.nc.gov/about/divisions/division-coastal-management/coastal-management-land-use-planning/certified-lups/washington-county
- County Plan edocs id=247907 (certified 1994-07-29; status Under Review)
- Plymouth CAMA Comprehensive / Strategic Plan edocs id=329963 (certified 2024-06-24)
- Creswell / Roper: See County
- NCDOT CTP REPORT.pdf (transportation — not FLU substitute)
- `landuse/5` LUSE W/C (**773**) = existing LU — **reject as FLU**
- **No public FLU FeatureServer** found 2026-09-24

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS (Parcel Viewer) | https://experience.arcgis.com/experience/3bffabc4dd484e1bbfa49186361dce5d |
| Jurisdiction GIS (webappviewer) | https://washconc.maps.arcgis.com/apps/webappviewer/index.html?id=1a51e666286842138be02492cab0ec95 |
| Online Land Records | https://experience.arcgis.com/experience/dd9851d8899942f1a03842e372b2c228/ |
| taxweb Parcel card (PRIMARY) | `http://taxweb.washconc.org/Parcel.aspx?{WCParcel}` |
| AGD print | `https://apps.agdmaps.com/print/nc/washington/index.html?NCPIN={NCPin}` |
| NCPTS parcel detail (reid query) | `https://lrcpwa.ncptscloud.com/Washington/parcel-detail?reid={NCPin}` |
| NCPTS parcel detail (path) | `https://lrcpwa.ncptscloud.com/Washington/parcel-detail/{NCPin}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/Washington/parcel-search |
| Tax Office hub | https://washconc.org/tax-office/ |

Example: WCParcel `7586` / NCPin `7841626695` → http://taxweb.washconc.org/Parcel.aspx?7586 (HTTP 200); AGD print `?NCPIN=7841626695` (HTTP 200). Field `PropRecCard` / `Print_` on the parcel layer already store these URLs. **dl.agd.cc/prc/nc/washington** → **404** — do not use.

## Gaps

- County Official Zoning Map REST gap (Zoning/10 = 24 CI stubs only; ordinance PDF for unincorporated)
- Roper / Creswell zoning FeatureServer gap (limits+ETJ only)
- FLU FeatureServer gap (DEQ CAMA edocs + Plymouth 2024 plan; reject landuse/5 as FLU)
- Growth Opportunities Plan PDF not found on public county site 2026-09-24
- OneMap `saledate` date field null — use county `SalePrice`/`SaleDate` or `saledatetx`
- `SaleDate` mixed string formats on county layer
- Standalone Parcels/0 weaker/stale vs Parcels_in_use
- AGD PRC path `dl.agd.cc/prc/nc/washington` 404
- `washconc.org/gis` is JPEG stub — use Experience/webappviewer
- Utilities / AADT / emails / phones / paid vendors intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** Washington_Service/9 count/acres/tax/owner/SalePrice/Qualified/PropRecCard/Print_ + Plymouth geo sample; OneMap `cntyfips='187'` counts (saledate empty); PLYMOUTH_ZONING 313 DISTRICT/NAME; Zoning/10 CI=24; Municipal/City_Limits/ETJ 3; landuse LUSE W/C reject-as-FLU; taxweb Parcel.aspx + AGD print + NCPTS + Experience/webappviewer 200; Zoning Ordinance + Subdivision Ordinance PDF 200; DEQ certified LUP hub + edocs ids; NCDOT CTP REPORT PDF 200; rejected dl.agd.cc/prc 404 + Beaufort City-of-Washington miswire


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services/Washington_Service/FeatureServer/9 · id `NCPin` · live count **12,630** · 5–150 ac **1,800** (`CalculatedAcres >= 5 AND CalculatedAcres <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='WASHINGTON'` gives **185** stations (104 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27WASHINGTON%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Washington'` gives **183** stations (122 with AADT_2025, 121 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Washington%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `TotalAssessedValue` non-zero **10,326**, `LandAssessedValue` non-zero **10,323**
- **Sale history (ok):** price `SalePrice` >0 **4,374**; date `SaleDate` non-null **9,596**
- **Owner entity:** fields `Owner`, `OwnerName2`, `parcels_ow`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **389** (all parcels: 1,414), using the SQL approximation on `Owner`.
- **PA deep link:** `http://taxweb.washconc.org/Parcel.aspx?{WCParcel}`. Tested `4350` → HTTP **200** (text/html; charset=utf-8), content verified: True. Owner and parcel id verified in the response.
- **Jurisdiction GIS viewer:** https://experience.arcgis.com/experience/3bffabc4dd484e1bbfa49186361dce5d → HTTP **200** (Experience); ArcGIS item access=public
- **Pass 2 gaps:** none
