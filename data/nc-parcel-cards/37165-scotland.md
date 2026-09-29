# Scotland County, NC — GIS County Card

## Summary

Scotland County (Fayetteville MSA shed, FIPS **37165**, slug **scotland**, `cntyfips='165'`) publishes a joint **Laurinburg–Scotland AGOL** stack (`services3.arcgis.com/bgKigTDifCMNj8OU`, owner `krivera_laurinburg`). **Wire-first parcels:** **Tax Parcels Scotland County - Public View** FS/**6** — **22,022** polys with owner, mailing, situs (`PropertyAd`), `ACRES`, full market split (`MarketValu`/`MarketLand`/`BuildingVa`), deed book/page/**DeedDate**, and `CityCode` muni router. **~3,361** with `ACRES` 5–150. **Cities-first zoning:** **Laurinburg** Zoning FS/**14** (**9,705**) wins inside city; **County Zoning** FS/**9** (**10,632**, mostly **RA**/R1) for unincorporated. Wagram / Gibson / East Laurinburg — limits only (no town zoning FS). **FLU:** Comp Land Use Plan **PDF only**. **Sale price REST gap** (DeedDate + SaleInstru; Parcel Sales FS/7 ~3,378 date overlay). **PA deep-link:** `https://www.bttaxpayerportal.com/ITSPublicSC/AppraisalCard.aspx?id={PIN}` (**space in PIN → `%20`**, PDF verified). **Jurisdiction GIS:** Parcel Explorer webappviewer + hub. Markets: **[Fayetteville]**.

## Portals

- **Jurisdiction GIS (Parcel Explorer)** — https://laurinburg.maps.arcgis.com/apps/webappviewer/index.html?id=889f012d9e2645278a18addbedd03d74
- **GIS Hub** — https://scotland-laurinburg.hub.arcgis.com/
- **County GIS Maps** — https://www.scotlandcounty.org/456/GIS-Maps
- **Instant Parcel Explorer** — https://laurinburg.maps.arcgis.com/apps/instant/basic/index.html?appid=d9ec1327e84a4cf48eeeb538c9bfbfa2
- **AGOL Tax Parcels FS/6** — https://services3.arcgis.com/bgKigTDifCMNj8OU/arcgis/rest/services/Tax_Parcels_Scotland_County_view/FeatureServer/6
- **AGOL Parcel Sales FS/7** — https://services3.arcgis.com/bgKigTDifCMNj8OU/arcgis/rest/services/Parcel_Sales_Scotland_County_view/FeatureServer/7
- **AGOL Zoning Laurinburg FS/14** — https://services3.arcgis.com/bgKigTDifCMNj8OU/arcgis/rest/services/Zoning_Laurinburg_-_Public_View/FeatureServer/14
- **AGOL Zoning County FS/9** — https://services3.arcgis.com/bgKigTDifCMNj8OU/arcgis/rest/services/Zoning_Scotland_County_view/FeatureServer/9
- **PA AppraisalCard (deep-link)** — `https://www.bttaxpayerportal.com/ITSPublicSC/AppraisalCard.aspx?id={PIN}` (space → `%20`)
- **Tax Bill Search** — https://www.bttaxpayerportal.com/ITSPublicSC/TaxBillSearch
- **Basic Search** — https://www.bttaxpayerportal.com/ITSPublicSC/BasicSearch
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/scotland/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/scotland/parcel-detail/{PINID}`
- **Tax Office** — https://www.scotlandcounty.org/335/Taxes
- **Zoning Ordinance + Land Use Plan** — https://www.scotlandcounty.org/848/Scotland-County-Zoning-Ordinance-and-Lan
- **Zoning Map PDF** — https://www.scotlandcounty.org/DocumentCenter/View/3743/20220627122202scan
- **Comp Land Use Plan (FLU PDF)** — https://www.scotlandcounty.org/DocumentCenter/View/4523/Scotland-County-Comprehensive-Land-Use-Plan-
- **Land Use Plan 2022 PDF** — https://www.scotlandcounty.org/DocumentCenter/View/3729/Land-Use-2022
- **Zoning Ordinance 2022 PDF** — https://www.scotlandcounty.org/DocumentCenter/View/3918/Zoning-Ordinance-2022-signed-2-2
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='165'`)
- **Laurinburg Planning** — https://www.laurinburg.org/225/Planning-Zoning

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` / `PINID`; OneMap `parno`/`altparno` | Prefer **PIN** (space) for AppraisalCard; **PINID** compact for NCPTS |
| polygons | Yes | Tax Parcels FS/6; OneMap | CRS **102719 / 2264** |
| acreage | Yes | `ACRES`; OneMap `gisacres` | gisacres **matches** ACRES here |
| ownerName | Yes | `Name` / `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `Address*`/`City`/`State`/`ZipCode` | |
| situs address | Yes | `PropertyAd`; OneMap `siteadd` | ~18,878 nonblank |
| lastSale date/price | Partial | `DeedDate` / Sales FS; **no price** | **Sale price REST gap** |
| tax values | Yes | `MarketValu`/`MarketLand`/`BuildingVa` | Prefer MarketValu over sparse AssessedVa |
| zoning | Yes (cities-first) | Laurinburg `ZONING`; County `Zoning` | Laurinburg wins in city |
| flu | Gap | Comp Plan PDF | No FeatureServer |
| appraiser / viewer link | Yes | AppraisalCard `{PIN}`; NCPTS `{PINID}`; Parcel Explorer | TRANCHE-3 |

### CityCode → municipality (Tax Parcels)

| CityCode | Municipality | Approx parcels | Zoning source |
|----------|--------------|----------------|---------------|
| *(blank)* | Unincorporated | **12,869** | County Zoning FS/9 |
| L | **Laurinburg** | **7,883** | Laurinburg Zoning FS/14 (city-first) |
| W | **Wagram** | **627** | Limits only — no town FS |
| G | **Gibson** | **313** | Limits only — no town FS |
| E | **East Laurinburg** | **184** | Limits only — no town FS |
| M | **Maxton** (tip) | **130** | Prefer Robeson `Mxtn*` |
| C | (sparse) | **2** | Anomalous |

### Laurinburg Zoning inventory (FS/14)

| ZONING | Approx polys |
|--------|--------------|
| R-15 | **3,792** |
| R-6 | **3,157** |
| GB | **656** |
| R-20 | **575** |
| R-6-MH | **434** |
| O-I | **399** |
| R-20-MH | **227** |
| East LBG | **187** |
| I | **156** |
| CB | **122** |

### County Zoning inventory (FS/9)

| Zoning | Approx polys |
|--------|--------------|
| RA | **8,826** |
| R1 | **1,133** |
| R1MHA | **154** |
| C1 | **93** |
| HC / RAMHA / I2 / OS / I1 / R2 | **~403** |

## Layers (verified 2026-09-24)

### 1. Tax Parcels Scotland County — PRIMARY CAMA

- **REST:** https://services3.arcgis.com/bgKigTDifCMNj8OU/arcgis/rest/services/Tax_Parcels_Scotland_County_view/FeatureServer/6
- **Key fields:** `PIN`, `PINID`, `AccountNum`, `RECNO`, `Name`, mail/site, `ACRES`, `MarketValu`/`MarketLand`/`BuildingVa`/`AssessedVa`/`DeferredVa`, `DeedBook`/`DeedPage`/`DeedDate`, `SaleInstru`, `CityCode`
- **Verified:** count **22,022**; ACRES 5–150 → **3,361**; MarketValu>0 **21,898**; BuildingVa>0 **12,105**; DeedDate>0 **21,422**
- **Notes:** No sale price. MaxRecordCount **2000**. CRS **102719/2264**.

### 2. Parcel Sales — sale-date overlay

- **REST:** …/Parcel_Sales_Scotland_County_view/FeatureServer/7
- **Verified:** count **3,378**; DeedStamps>0 → **0** (no price)

### 3. NC OneMap Parcels — statewide fallback

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='165'`
- **Verified:** count **21,992**; gisacres 5–150 → **3,345**; landval/parval>0 ~**21,866**
- **Notes:** gisacres **usable** (matches ACRES). Join `parno`=`PIN`; `altparno`=`RECNO`. No saledate.

### 4. Zoning Laurinburg FS/14 — cities-first PRIMARY

- Count **9,705** — `ZONING`

### 5. Zoning Scotland County FS/9 — unincorporated

- Count **10,632** — `Zoning` / `ZoningDesc`

### 6. City Limits FS/5 + ETJ FS/8 + Laurinburg Addresses

- Limits **7**; ETJ present; Addresses city-only

### 7. FLU — gap (Comp Plan PDF)

- https://www.scotlandcounty.org/DocumentCenter/View/4523/Scotland-County-Comprehensive-Land-Use-Plan-

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS viewer | https://laurinburg.maps.arcgis.com/apps/webappviewer/index.html?id=889f012d9e2645278a18addbedd03d74 |
| Appraisal card PDF by PIN | `https://www.bttaxpayerportal.com/ITSPublicSC/AppraisalCard.aspx?id={PIN}` (**encode space as `%20`**) |
| NCPTS parcel detail | `https://lrcpwa.ncptscloud.com/scotland/parcel-detail/{PINID}` |
| Tax bill search | https://www.bttaxpayerportal.com/ITSPublicSC/TaxBillSearch |
| GIS hub | https://scotland-laurinburg.hub.arcgis.com/ |

Example: PIN `040169 01013` → https://www.bttaxpayerportal.com/ITSPublicSC/AppraisalCard.aspx?id=040169%2001013 (HTTP 200 `application/pdf` verified). Compact `04016901013` returns empty BI-Tek shell — do **not** strip the space.

## Gaps

- Sale price not on public ArcGIS REST (Tax Parcels / Parcel Sales / OneMap)
- FLU FeatureServer gap (Comp Land Use Plan + Land Use 2022 PDFs only)
- Wagram / Gibson / East Laurinburg — no dedicated municipal zoning FeatureServer
- Maxton zoning primarily on Robeson card; Scotland tip only (`CityCode=M`)
- ITSPublicSC RealEstateSearch not configured (HTTP 500)
- AssessedVa sparse (~1,467) — prefer MarketValu
- Utilities / AADT intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** AGOL Tax Parcels/6 + Sales/7 + Zoning Laurinburg/14 + County Zoning/9 + City Limits/5 counts + CityCode/Zoning groupBy; OneMap `cntyfips='165'` counts + gisacres join sample `parno`=`PIN`; AppraisalCard PDF 200 with spaced PIN; NCPTS SPA 200; hub/webappviewer/TaxBillSearch/planning DocumentCenter PDFs 200
