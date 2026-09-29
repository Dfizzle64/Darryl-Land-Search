# Beaufort County, NC — GIS County Card

## Summary

Beaufort County (markets **[Eastern NC]**, FIPS **37013**, slug **beaufort**, `cntyfips='013'`) publishes public AGOL FeatureServers under org **BeaufortCoNC** (`services1.arcgis.com/oXsk9nimtmSEU8Ko`). **Wire-first parcels:** **Beaufort_Service/FeatureServer/4** — ~**45,229** polys with owner (`NAME1`), mailing, situs (`PROP_ADDR`), `CalcAcres`, **SALE_PRICE** + sale date (`DATE` / `date_dt`), tax `LAND_VAL`/`BLDG_VAL`/`TOT_VAL`/`TAXABLE_VAL`, use `USE_CDE`/`USE_DESC`, parcel id `ALPHA`/`GPIN`/`REID`. ~**8,050** with `CalcAcres` 5–150 (~**5,597** vacant/no bldg in band; ~**2,307** with sale price in band). **Cities-first zoning:** **Washington** `Beaufort_Static/16` WasingtonZoning2021 (~**556**, `ZONING`) + **Belhaven** `Beaufort_Static/28` BelhavenZoning2024 (**11**, `Zoning_District`). Aurora / Bath / Chocowinity / Pantego / Washington Park / unincorporated — **no public base-zoning FeatureServer** (ETJs present; Ag Districts overlay only). **FLU:** Washington 2024 Comp/CAMA LUP + FLU Map PDFs — **no FLU FS** (Static/18 LandUse is not FLU). **PA:** NCPTS `parcel-detail?reid={REID}` (+ path `/{REID}`) + AGD print `?GPIN={GPIN}` + jurisdiction webappviewer.

## Portals

- **County GIS / Land Records** — https://co.beaufort.nc.us/239/GIS-Land-Records
- **Jurisdiction GIS viewer (webappviewer)** — https://beaufortnc.maps.arcgis.com/apps/webappviewer/index.html?id=e97b027e0d7d49ca8849e716662628f8
- **Legacy GIS redirect host** — http://beaufortcountygis.com → webappviewer
- **Experience Builder (alt viewer)** — https://experience.arcgis.com/experience/d291549628354e2aa3c0416439cd913f/
- **County ArcGIS REST (AGOL)** — https://services1.arcgis.com/oXsk9nimtmSEU8Ko/arcgis/rest/services
- **Parcels shapefile download** — https://co.beaufort.nc.us/DocumentCenter/View/2591/Beaufort-County-Parcels-ZIP
- **Streets shapefile** — https://co.beaufort.nc.us/DocumentCenter/View/2590/Beaufort-County-Streets-ZIP
- **Tax Assessor** — https://co.beaufort.nc.us/238/Tax-Assessor
- **NCPTS Beaufort hub** — https://lrcpwa.ncptscloud.com/Beaufort/
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/beaufort/parcel-search
- **NCPTS deep-link (reid query)** — `https://lrcpwa.ncptscloud.com/Beaufort/parcel-detail?reid={REID}`
- **NCPTS deep-link (path)** — `https://lrcpwa.ncptscloud.com/Beaufort/parcel-detail/{REID}`
- **AGD property print card** — `https://apps.agdmaps.com/print/nc/beaufort/index.html?GPIN={GPIN}`
- **Tax bill search (NCPTS bill)** — https://bcpwa.ncptscloud.com/beauforttax/BillSearchResults.aspx
- **Register of Deeds** — https://us5.courthousecomputersystems.com/BeaufortNC2
- **NC OneMap parcels** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='013'`)
- **Washington Planning / Maps** — https://www.washingtonnc.gov/departments/planning___zoning/planning___zoning/map.php
- **Washington Comp / CAMA LUP** — https://www.washingtonnc.gov/residents/cama_land_use_plan.php
- **Washington LUP PDF (2024)** — https://www.washingtonnc.gov/PLANNING/New%20node/LUP_Washington_20240213_FINAL.pdf
- **Washington FLU Map PDF** — https://www.washingtonnc.gov/PLANNING/Planning%20%26%20Zoining/map/FLU%20Map%2024-02.pdf

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `ALPHA`/`GPIN`; OneMap `parno`; `REID`; `PIN_1` | ALPHA e.g. `5657-09-8487` |
| polygons | Yes | Beaufort_Service/4; OneMap FS/1 | CRS **102719 / 2264** |
| acreage | Yes | `CalcAcres` (prefer); OneMap `gisacres` / `Shape__Area/43560` | gisacres OK here (~8401 in 5–150) |
| ownerName | Yes | `NAME1`/`NAME2`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `ADDR1`/`ADDR2`/`CITY`/`STATE`/`ZIP` | CITY = mailing city, not situs muni |
| situs address | Yes | `PROP_ADDR`; OneMap `siteadd` | |
| lastSale date/price | Yes | **price** `SALE_PRICE`; **date** `DATE`/`date_dt` (prefer); OneMap `saledatetx` | OneMap `saledate` date field **null** here |
| tax values | Yes | `LAND_VAL`/`BLDG_VAL`/`TOT_VAL`/`TAXABLE_VAL`; OneMap `parval`/`landval`/`improvval` | Strong on both |
| zoning | Yes (cities-first) | Washington `ZONING`; Belhaven `Zoning_District` | Other munis + unincorp REST gap |
| flu | Gap (PDF) | Washington 2024 Comp/CAMA LUP + FLU Map PDFs | Static/18 LandUse not FLU |
| appraiser / viewer link | Yes | NCPTS `?reid={REID}`; AGD `?GPIN={GPIN}`; webappviewer | TRANCHE-3 |

### Municipality router (MunicipalLimits CityCode → city-first zoning)

| CityCode | Municipality | Annex polys | Zoning source |
|----------|--------------|-------------|---------------|
| WAS | **Washington** | 65 (~5,569 ac) | Washington Zoning Static/16 (city-first PRIMARY) |
| BEL | **Belhaven** | 4 (~1,485 ac) | Belhaven Zoning Static/28 (city-first) |
| CHO | **Chocowinity** | 13 | No public zoning FS (ETJ present) |
| AUR | **Aurora** | 2 (~696 ac) | No public zoning FS (ETJ present) |
| BAT | **Bath** | 1 (~628 ac) | No public zoning FS (ETJ present) |
| PAN | **Pantego** | 1 (~421 ac) | No public zoning FS |
| WPK | **Washington Park** | 1 (~170 ac) | No public zoning FS |
| *(outside limits)* | Unincorporated | — | No countywide base zoning FS (Ag Districts overlay only) |

**Note:** Parcel `CITY` is **mailing** city (WASHINGTON 14645, CHOCOWINITY 4186, AURORA 3230, BELHAVEN 2921, BATH 2497, …) — do **not** use as situs municipality; spatial-join MunicipalLimits / ETJ.

### Washington ZONING (top; 556 polys)

| ZONING | Count |
|--------|-------|
| R6S | 106 |
| RA20 | 90 |
| B2 | 87 |
| O&I | 47 |
| R9S | 46 |
| R15S | 38 |
| RMF | 29 |
| RHD | 22 |
| I1 | 20 |
| I2 | 19 |
| B4 / B1H | 11 each |

### Belhaven Zoning_District (11 polys)

| Zoning_District | Count |
|-----------------|-------|
| (R5) Residential | 2 |
| (R5M) Residential Mobile Home | 2 |
| (MB) Marine Business | 1 |
| (GB) General Business | 1 |
| (HB) Highway Business | 1 |
| Industrial | 1 |
| Commercial Overlay | 1 |
| (RAW) Residential Agricultural Water | 1 |
| (RA) Residential Agricultural | 1 |

## Layers (verified 2026-09-24)

### 1. Beaufort_Service/Parcels — PRIMARY county AGOL CAMA + sale

- **Purpose:** parcels | tax | ownership | sales | situs
- **REST URL:** https://services1.arcgis.com/oXsk9nimtmSEU8Ko/arcgis/rest/services/Beaufort_Service/FeatureServer/4
- **Also:** Condos_Leaseholds/FeatureServer/0 (~1,241 condo/leasehold polys, same CAMA schema)
- **Shapefile:** https://co.beaufort.nc.us/DocumentCenter/View/2591/Beaufort-County-Parcels-ZIP
- **Key fields → targets:** `ALPHA`/`GPIN`→parcelId; `REID`→parcelIdAcct; `PIN_1`→parcelIdAlt; `NAME1`/`NAME2`→ownerName; `ADDR1`/`CITY`/`STATE`/`ZIP`→mailing; `PROP_ADDR`→situs; `CalcAcres`→acreage; `SALE_PRICE`→lastSale.price; `DATE`/`date_dt`→lastSale.date; `LAND_VAL`/`BLDG_VAL`/`TOT_VAL`/`TAXABLE_VAL`→tax; `USE_CDE`/`USE_DESC`→dorCode/landUse; `DEED_BOOK`/`DEED_PAGE`→deed; `PRC`→appraiserDeepLink; `Print_`→printCardUrl; `deed_link`→deedImageUrl
- **WKID / CRS:** 102719 / 2264
- **Verified:** count **45,229**; CalcAcres 5–150 → **8,050**; SALE_PRICE>0 → **19,370**; sale+band → **2,307**; TOT_VAL>0 → **43,776**; LAND_VAL>0 → **43,661**; vacant band → **5,597**; owner ~**44,888**; PRC/date_dt non-null ~**44,888**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. Geo-check ALPHA `5657-09-8487` ≈ **-77.148, 35.602** (Washington). Auth: none (public). `PRC` embeds NCPTS reid deep-link.

### 2. NC OneMap Parcels — statewide REST + saledatetx backup

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='013'`
- **Key fields:** `parno`, `ownname`, mail/site, `gisacres`, `Shape__Area`, `landval`/`improvval`/`parval`, `saledatetx` (text)
- **Verified:** count **46,322**; gisacres 5–150 → **8,401**; Shape__Area 5–150 → **8,402**; ownname **46,322**; parval>0 **44,254**; landval>0 **43,021**; saledatetx present **46,010**; **saledate date field null** (0)
- **Notes:** Join `parno`=`ALPHA`. Prefer county layer for **SALE_PRICE** + typed `date_dt`. Prefer OneMap `saledatetx` only as text backup. MaxRecordCount **5000**.

### 3. Washington Zoning — city-first PRIMARY (Washington)

- **REST:** https://services1.arcgis.com/oXsk9nimtmSEU8Ko/arcgis/rest/services/Beaufort_Static/FeatureServer/16
- **Fields:** `ZONING`, `PREV_ZONE`, `ACRES_1`, `NOTES`, `RZONE_DATE` (`LUP_COMP` blank)
- **Verified:** count **556** (2026-09-24)
- **Notes:** Spatial-join inside Washington City Limits / ETJ (`Municipal_ETJs` ALPHA=`Washington ETJ`). Layer name typo: **Wasington**Zoning2021.

### 4. Belhaven Zoning — city-first PRIMARY (Belhaven)

- **REST:** https://services1.arcgis.com/oXsk9nimtmSEU8Ko/arcgis/rest/services/Beaufort_Static/FeatureServer/28
- **Fields:** `Zoning_District`, `CalcAcres`, `ACRES`, `GID`
- **Verified:** count **11** district polys
- **Notes:** Coarse district polygons (not parcel-level). Spatial-join Belhaven limits / `Belhaven ETJ`.

### 5. Parcels_QS_2022_2024 — supplemental qualified sales extract

- **REST:** https://services1.arcgis.com/oXsk9nimtmSEU8Ko/arcgis/rest/services/Beaufort_Static/FeatureServer/29
- **Fields:** same CAMA core + `SALE_DATE1`, `SALE_PRICE1`, `Year`
- **Verified:** **2,350** (Year: 2022=1087, 2023=622, 2024=641)
- **Notes:** Prefer for recent QS join; countywide last-sale still on Beaufort_Service/4 `SALE_PRICE`/`DATE`.

### 6. Municipal Limits + ETJ

- **City Limits:** https://services1.arcgis.com/oXsk9nimtmSEU8Ko/arcgis/rest/services/Beaufort_Static/FeatureServer/9 — CityCode WAS/BEL/CHO/AUR/BAT/PAN/WPK (**87** annex polys)
- **ETJ:** FeatureServer/30 — Washington, Belhaven, Chocowinity, Bath, Aurora (**5**)
- **Use with CityCode** for city-first router (not mailing `CITY`)

### 7. Agriculture Districts (overlay, not base zoning)

- **REST:** https://services1.arcgis.com/oXsk9nimtmSEU8Ko/arcgis/rest/services/Beaufort_Static/FeatureServer/2 — **75** polys
- **Notes:** VAD/Ag overlay only — not municipal base zoning.

### 8. FLU — gap (PDF / plan docs)

- Washington Comp/CAMA LUP hub: https://www.washingtonnc.gov/residents/cama_land_use_plan.php (adopted 2024-01-08; NCDCM certified 2024-02-08)
- LUP PDF: https://www.washingtonnc.gov/PLANNING/New%20node/LUP_Washington_20240213_FINAL.pdf
- FLU Map PDF: https://www.washingtonnc.gov/PLANNING/Planning%20%26%20Zoining/map/FLU%20Map%2024-02.pdf
- Beaufort_Static/18 LandUse — **not FLU** (ALPHA mostly `NC`; no land-use class field) — do not wire as FLU
- County / other towns: joint CAMA archives (DEQ / State Library) — no public FLU FeatureServer found 2026-09-24

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS viewer | https://beaufortnc.maps.arcgis.com/apps/webappviewer/index.html?id=e97b027e0d7d49ca8849e716662628f8 |
| NCPTS parcel detail (reid query) | `https://lrcpwa.ncptscloud.com/Beaufort/parcel-detail?reid={REID}` |
| NCPTS parcel detail (path) | `https://lrcpwa.ncptscloud.com/Beaufort/parcel-detail/{REID}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/beaufort/parcel-search |
| AGD print / property card | `https://apps.agdmaps.com/print/nc/beaufort/index.html?GPIN={GPIN}` |
| Tax bill search | https://bcpwa.ncptscloud.com/beauforttax/BillSearchResults.aspx |
| County GIS hub | https://co.beaufort.nc.us/239/GIS-Land-Records |

Example: REID `16054` / GPIN `5657-09-8487` → https://lrcpwa.ncptscloud.com/Beaufort/parcel-detail?reid=16054 (HTTP 200); https://apps.agdmaps.com/print/nc/beaufort/index.html?GPIN=5657-09-8487 (HTTP 200). Field `PRC` on the parcel layer already stores the NCPTS reid URL.

## Gaps

- No public zoning FeatureServer for Aurora, Bath, Chocowinity, Pantego, Washington Park
- Unincorporated Beaufort: no countywide base-zoning FS (Agriculture Districts overlay only)
- FLU FeatureServer gap (Washington 2024 Comp/CAMA LUP + FLU Map PDFs only; Static/18 LandUse unusable as FLU)
- OneMap `saledate` date field null for `cntyfips='013'` — use county `DATE`/`date_dt` or OneMap `saledatetx`
- Parcel `CITY` is mailing city — situs municipality requires MunicipalLimits/ETJ spatial join
- Belhaven zoning is coarse district polys (11), not parcel fabric
- Utilities / AADT / emails / phones / paid vendors intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** Beaufort_Service/4 count/acres/sale/tax/owner + geo sample; OneMap `cntyfips='013'` counts + saledatetx; Washington ZONING 556 + groups; Belhaven 11 districts; MunicipalLimits CityCode 7 munis / ETJ 5; Parcels_QS 2350; NCPTS reid + AGD GPIN + webappviewer + LUP/FLU PDFs 200; Condos_Leaseholds 1241
