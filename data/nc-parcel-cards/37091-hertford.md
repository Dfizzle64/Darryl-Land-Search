# Hertford County, NC — GIS County Card

## Summary

Hertford County (markets **[Eastern NC]**, FIPS **37091**, slug **hertford**, `cntyfips='091'`) hosts public ArcGIS Server at **`gis.hertfordcounty.org`** (AGOL org **MOvVToSDbOGFaHPk** / `hertfordcountync.maps.arcgis.com`). **Wire-first parcels:** **TaxParcels/MapServer/2** — ~**16,106** polys with owner (`PROPERTY_OWNER`), mailing (`OWNER_MAIL_*`), situs (`LOCATION_ADDR` / `PHYADDR_*`), `ACREAGE`/`ASSESSED_ACREAGE`/`CALCULATED_ACRES`, **PKG_SALE_PRICE** + `PKG_SALE_DATE` (and land-sale twins), tax `TOTAL_LAND_ASSESSED`/`TOTAL_BLDG_ASSESSED`/`TOTAL_PROP_VALUE`, parcel zoning attr `ZONING`, ids `REID`/`Tax_REID`/`PIN`/`PIN83`/`PARCEL_PK`. ~**2,711** with `ACREAGE` 5–150 (~**1,962** vacant/no bldg in band; ~**305** with package sale price in band). **Cities-first zoning:** **Ahoskie** Zoning/2 (340) + **Murfreesboro** Zoning/5 (239) + **Winton** Zoning/6 (103) + **Cofield** Zoning/3 (37) + **Como** Zoning/4 (5); county Zoning/1 (413) for unincorporated. **Harrellsville** — explicit **NO ZONING**. **FLU:** CAMA LUP Jan 2011 PDF (DEQ certified) + Ahoskie Draft Comp Plan FLU PDF — **no FLU FS** (LandUse/0 is current cover, not FLU). **PA:** NCPTS `PropertySummary.aspx?PIN={Tax_REID}` (webmap official) + `parcel-detail?reid={REID}` / path; jurisdiction Tax Parcel Viewer Instant Sidebar.

## Portals

- **Jurisdiction GIS (Tax Parcel Viewer / Instant Sidebar)** — https://hertfordcountync.maps.arcgis.com/apps/instant/sidebar/index.html?appid=26b28f8a51164fc89431eedd61072339
- **AGOL / Public Maps hub** — https://hertfordcountync.maps.arcgis.com/home/index.html
- **Legacy webappviewer** — https://www.arcgis.com/apps/webappviewer/index.html?id=53620a0b6458437aa82bd5e91d8cc47b
- **County GIS / Land Records** — https://www.hertfordcountync.gov/departments/county_administration/gis___land_records/index.php
- **Planning and Zoning** — https://www.hertfordcountync.gov/departments/county_administration/planning_and_zoning.php
- **County ArcGIS REST root** — https://gis.hertfordcounty.org/server/rest/services
- **TaxParcels MapServer** — https://gis.hertfordcounty.org/server/rest/services/TaxParcels/MapServer
- **Zoning MapServer** — https://gis.hertfordcounty.org/server/rest/services/Zoning/MapServer
- **NCPTS Hertford hub / search** — https://lrcpwa.ncptscloud.com/hertford/parcel-search
- **NCPTS PropertySummary (preferred PA)** — `https://lrcpwa.ncptscloud.com/Hertford/PropertySummary.aspx?PIN={Tax_REID}`
- **NCPTS parcel-detail (reid query)** — `https://lrcpwa.ncptscloud.com/Hertford/parcel-detail?reid={REID}`
- **NCPTS parcel-detail (path)** — `https://lrcpwa.ncptscloud.com/Hertford/parcel-detail/{REID}`
- **NCPTS Parcel-detail (PARCEL_PK alt)** — `https://lrcpwa.ncptscloud.com/Hertford/Parcel-detail/{PARCEL_PK}`
- **Tax pay portal** — https://www.hertfordtax.com/
- **Register of Deeds** — https://www.hertfordrod.net/
- **Unified Development Ordinance (UDO)** — https://www.hertfordcountync.gov/Revised%20UDO%2012012025.pdf
- **CAMA Land Use Plan Update PDF (Jan 2011)** — https://www.hertfordcountync.gov/Document%20Center/Department/County%20Administration/Planning%20and%20Zoning/Hertford%20Co%20CAMA%20LUP%20JAN2011.pdf
- **DEQ certified LUP download** — https://www.deq.nc.gov/documents/pdf/land-use-plans/hertfordcountycertiflup-022411/download
- **Ahoskie Draft Comp Plan (FLU map PDF)** — https://www.ahoskienc.gov/media/NewsImages/Ahoskie%20Comprehensive%20Plan%20-%20Draft_4.20.pdf
- **NC OneMap parcels** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='091'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `REID`/`Tax_REID`; `PIN`/`PIN83`; OneMap `parno`/`altparno`; `PARCEL_PK` | Prefer REID for PA; PIN83 display |
| polygons | Yes | TaxParcels/2; OneMap FS/1; Parcels/0 | CRS **102719 / 2264** |
| acreage | Yes | `ACREAGE` (prefer); `ASSESSED_ACREAGE`/`CALCULATED_ACRES`; OneMap `gisacres` | ~**2,711** in 5–150 |
| ownerName | Yes | `PROPERTY_OWNER`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `OWNER_MAIL_1`/`OWNER_MAIL_CITY`/`OWNER_MAIL_STATE`/`OWNER_MAIL_ZIP` | |
| situs address | Yes | `LOCATION_ADDR`; `PHYADDR_*`; OneMap `siteadd` | |
| lastSale date/price | Yes | **price** `PKG_SALE_PRICE`; **date** `PKG_SALE_DATE`; land twins; OneMap `saledatetx` | OneMap `saledate` null |
| tax values | Yes | `TOTAL_LAND_ASSESSED`/`TOTAL_BLDG_ASSESSED`/`TOTAL_PROP_VALUE`; OneMap `parval`/`landval`/`improvval` | Strong on both |
| zoning | Yes (cities-first) | Zoning/2–6 `ZONING_COD`; county Zoning/1; parcel `ZONING` attr | Harrellsville NO ZONING |
| flu | Gap (PDF) | CAMA LUP 2011 + Ahoskie Comp Plan FLU PDFs | LandUse/0 not FLU |
| appraiser / viewer link | Yes | NCPTS `PropertySummary?PIN={Tax_REID}`; Instant Sidebar | TRANCHE-3 |

### Municipality router (Municipalities NAME / CCODE → city-first zoning)

| CCODE | Municipality | Zoning source |
|-------|--------------|---------------|
| C01 | **Ahoskie** | Zoning/2 Ahoskie Zoning (340) — city-first PRIMARY; AHOSKIE ETJ |
| C04 | **Murfreesboro** | Zoning/5 Murfreesboro Zoning (239) — city-first PRIMARY; MURFREESBORO ETJ |
| C06 | **Winton** (seat) | Zoning/6 Winton Zoning (103) — city-first PRIMARY |
| C07 | **Cofield** | Zoning/3 Cofield Zoning (37) |
| C03 | **Como** | Zoning/4 Como Zoning (5) |
| C02 | **Harrellsville** | No base zoning (Planning_Jurisdictions NO ZONING) |
| *(outside limits)* | Unincorporated | Zoning/1 Hertford County Zoning (413; RA-30/CH/IH/IL/…) |

**Note:** Parcel `CITY` is **tax-city district** (AHOSKIE 2760, MURFREESBORO 1313, WINTON 495, …). `PHYADDR_CITY` is postal city (includes Aulander/Woodland/Colerain). Do **not** use either as situs municipality alone — spatial-join Municipalities / ETJ (or use parcel `ETJ` attr: COUNTY/AHOSKIE/MURFREESBORO/WINTON/COFIELD/HARRELLSVILLE/COMO).

### Ahoskie ZONING_COD (top; 340 polys)

| ZONING_COD | Count |
|------------|-------|
| R-6 | 124 |
| R-10 | 41 |
| B-2 | 40 |
| O-I | 35 |
| R-15 | 25 |
| I-L / B-1 | 21 each |
| R-20 | 19 |
| B-3 | 8 |
| I-H | 5 |

### Murfreesboro ZONING_COD (top; 239 polys)

| ZONING_COD | Count |
|------------|-------|
| R-10 | 57 |
| R-20 | 41 |
| O-I | 26 |
| R-15 | 24 |
| C-2 | 23 |
| R-20 MH | 18 |
| C-1 | 10 |
| R-6 | 9 |

### County ZONING_COD (413 polys)

| ZONING_COD | Count |
|------------|-------|
| RA-30 | 244 |
| CH | 86 |
| IH / IL | 31 each |
| RR&C | 16 |
| RB | 4 |

## Layers (verified 2026-09-24)

### 1. TaxParcels/Parcels — PRIMARY county CAMA + sale

- **Purpose:** parcels | tax | ownership | sales | situs | zoning-attr
- **REST URL:** https://gis.hertfordcounty.org/server/rest/services/TaxParcels/MapServer/2
- **Also:** Parcels/MapServer/0 (~15,764 geometry twin, no CAMA sale/tax/owner); GrowthMap_WFL1/FeatureServer/0 AGOL mirror (~16,112, thinner)
- **Key fields → targets:** `REID`/`Tax_REID`→parcelId; `PIN`/`PIN83`/`PIN27`→PIN; `PARCEL_PK`→pk; `PROPERTY_OWNER`→owner; `OWNER_MAIL_*`→mailing; `LOCATION_ADDR`/`PHYADDR_*`→situs; `ACREAGE`→acreage; `PKG_SALE_PRICE`/`PKG_SALE_DATE`→lastSale; `LAND_SALE_*`→land sale; `TOTAL_*_ASSESSED`/`TOTAL_PROP_VALUE`→tax; `ZONING`→zoning attr; `LAND_CLASS`→dorCode; `ETJ`→etj; `DEED_BOOK`/`DEED_PAGE`/`DEED_DATE`→deed
- **WKID / CRS:** 102719 / 2264
- **Verified:** count **16,106**; ACREAGE 5–150 → **2,711**; PKG_SALE_PRICE>0 → **5,165**; sale+band → **305**; TOTAL_PROP_VALUE>0 → **15,029**; LAND assessed → **15,624**; BLDG assessed → **10,155**; vacant band → **1,962**; owner → **15,994**; ZONING attr → **15,668**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. Geo-check PIN `6926024860` / REID `6926024860000` ≈ **-76.892, 36.377**. Auth: none (public). Older AGOL `Tax_Parcels` FeatureServer URL is **Invalid URL (400)** — do not wire.

### 2. NC OneMap Parcels — statewide REST + tax/owner fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='091'`
- **Key fields:** `parno`↔REID, `altparno`↔PIN83, `ownname`, mail/site, `gisacres`, `landval`/`improvval`/`parval`, `saledatetx` (text)
- **Verified:** count **16,102**; gisacres 5–150 → **2,709**; parval>0 **15,060**; landval>0 **15,647**; improvval>0 **10,175**; siteadd **15,984**; saledatetx present **16,102**; **saledate date field null** (0)
- **Notes:** Prefer county layer for **PKG_SALE_PRICE** + typed sale dates. OneMap `saledatetx` often placeholder `12/30/1899`. MaxRecordCount **5000**.

### 3–7. Cities-first Zoning MapServer layers

| Layer | REST | Count | Notes |
|-------|------|-------|-------|
| Ahoskie Zoning | …/Zoning/MapServer/2 | 340 | PRIMARY Ahoskie; `ZONING_COD`/`ZONING`; DISTRICT=AHOSKIE |
| Murfreesboro Zoning | …/Zoning/MapServer/5 | 239 | PRIMARY Murfreesboro |
| Winton Zoning | …/Zoning/MapServer/6 | 103 | PRIMARY Winton |
| Cofield Zoning | …/Zoning/MapServer/3 | 37 | Village |
| Como Zoning | …/Zoning/MapServer/4 | 5 | Coarse districts |

### 8. Hertford County Zoning — unincorporated

- **REST:** https://gis.hertfordcounty.org/server/rest/services/Zoning/MapServer/1 — **413** (RA-30/CH/IH/IL/RR&C/RB); DISTRICT=COUNTY
- **Notes:** Use outside city-first layers / ETJ.

### 9. Planning Jurisdictions — combined stack / Harrellsville gap

- **REST:** https://gis.hertfordcounty.org/server/rest/services/Planning_Jurisdictions/MapServer/0 — **1,172**
- **DISTRICT counts:** COUNTY 432, AHOSKIE 348, MURFREESBORO 240, WINTON 107, COFIELD 37, COMO 5, **HARRELLSVILLE 1 (ZONING_COD=NONE / NO ZONING)**

### 10. Municipalities + ETJ

- **City Limits:** …/Jurisdictional_Boundaries/MapServer/0 — AHOSKIE/HARRELLSVILLE/COMO/MURFREESBORO/WINTON/COFIELD (+ COUNTY stubs)
- **ETJ:** …/MapServer/2 — **AHOSKIE ETJ** + **MURFREESBORO ETJ** only (**2**)

### 11. FLU — gap (PDF / plan docs)

- County CAMA LUP Jan 2011 PDF (county site) + DEQ certified download (2011-02-24)
- Ahoskie Draft Comp Plan FLU map PDF
- UDO (Revised 2025-12-01) on county Planning page
- LandUse/MapServer/0 (~5,865, `LU_FEAT_CODE`) — **current land cover / CREP** — do **not** wire as FLU
- Growth_Map_WFL1 — zoning/boundary, not FLU
- No public FLU FeatureServer found 2026-09-24

### 12. Overlays (not base zoning)

- Zoning_Overlay_Districts: Floodplain + Airport
- VolAgDist (Voluntary Ag District) overlay

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS (Tax Parcel Viewer) | https://hertfordcountync.maps.arcgis.com/apps/instant/sidebar/index.html?appid=26b28f8a51164fc89431eedd61072339 |
| NCPTS PropertySummary (preferred; webmap expr) | `https://lrcpwa.ncptscloud.com/Hertford/PropertySummary.aspx?PIN={Tax_REID}` |
| NCPTS parcel-detail (reid query) | `https://lrcpwa.ncptscloud.com/Hertford/parcel-detail?reid={REID}` |
| NCPTS parcel-detail (path) | `https://lrcpwa.ncptscloud.com/Hertford/parcel-detail/{REID}` |
| NCPTS Parcel-detail (PARCEL_PK) | `https://lrcpwa.ncptscloud.com/Hertford/Parcel-detail/{PARCEL_PK}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/hertford/parcel-search |
| County GIS hub | https://www.hertfordcountync.gov/departments/county_administration/gis___land_records/index.php |

Example: Tax_REID / REID `6926024860000` → https://lrcpwa.ncptscloud.com/Hertford/PropertySummary.aspx?PIN=6926024860000 (HTTP 200 SPA shell); https://lrcpwa.ncptscloud.com/Hertford/parcel-detail?reid=6926024860000 (HTTP 200). Webmap popup expression uses `Tax_REID` in the `PIN=` query param.

## Gaps

- Harrellsville: no base zoning FeatureServer (Planning_Jurisdictions explicitly NO ZONING)
- FLU FeatureServer gap (CAMA LUP 2011 + Ahoskie Comp Plan FLU PDFs only; LandUse/0 unusable as FLU)
- OneMap `saledate` date field null for `cntyfips='091'` — use county `PKG_SALE_DATE`/`LAND_SALE_DATE` or OneMap `saledatetx` (filter placeholders)
- Parcel `CITY` / `PHYADDR_CITY` are not reliable situs municipality — join Municipalities/ETJ
- Como zoning coarse (5 polys); ETJ FS only Ahoskie + Murfreesboro
- AGOL `Tax_Parcels` FeatureServer Invalid URL — use on-prem TaxParcels/MapServer/2
- Utilities / AADT / emails / phones / paid vendors intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** TaxParcels/2 count/acres/sale/tax/owner/zoning-attr + geo sample; OneMap `cntyfips='091'` counts + sample; Zoning/1–6 district counts + ZONING_COD histograms; Planning_Jurisdictions Harrellsville NO ZONING; Municipalities 6 + ETJ 2; NCPTS PropertySummary/parcel-detail + Instant Sidebar + CAMA LUP/UDO/Ahoskie Comp Plan PDFs 200; LandUse/0 rejected as FLU; AGOL Tax_Parcels FS 400 rejected
