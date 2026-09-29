# Craven County, NC — GIS County Card

## Summary

Craven County (markets **[New Bern/Eastern NC]**, FIPS **37049**, slug **craven**, `cntyfips='049'`) publishes public ArcGIS REST at `gis.cravencountync.gov`. **Wire-first parcels:** **JustParcels/MapServer/0** — ~**60,029** polys with owner, mailing, situs (`FULLADD`), `PACREA` acres, **SALE_PRICE**, tax `totval`/`totlnd`/`totbld`, land-use `PLUSC`/`LUDESC`, and unique `PREFN`. ~**5,943** with `PACREA` 5–150 (~**3,717** vacant/no bldg in band; ~**2,169** with sale price in band). **Do not use JustParcels/CSV `SALE_DATE`** (corrupt) — prefer **NC OneMap `saledate`** or deed recorded `PRECYR`/`PRECMN`/`PRECDY`. **Cities-first zoning:** **New Bern** `Dev_Services/Zoning` FS/0 (~**261**, `ZONE`) + **Havelock** `mMaps/Planning/5` (**373**, `ZONING`). Trent Woods / River Bend / Vanceboro / Bridgeton / Dover / Cove City / unincorporated — **no public base-zoning FeatureServer** (airport EWN overlay only). **FLU:** New Bern 2022 LUP + CAMA regional PDFs — **no FLU FS**. **PA:** iMaps/map.htm `?pid={PID}` + NCPTS `{PID}` + ITSPublicCRRP search / ITSPublicCR tax bills.

## Portals

- **County GIS hub** — https://gis.cravencountync.gov/new_home/
- **iMaps Property Viewer (jurisdictionGisUrl)** — https://gis.cravencountync.gov/maps/default.aspx
- **Classic map viewer + PA deep-link host** — https://gis.cravencountync.gov/maps/map.htm
- **GIS apps** — https://gis.cravencountync.gov/apps/
- **Downloads (shapefile/CSV)** — https://gis.cravencountync.gov/downloads-zip-files.aspx
- **County ArcGIS REST** — https://gis.cravencountync.gov/arcgis/rest/services
- **Mapping / GIS (county site)** — https://www.cravencountync.gov/1490/Mapping-GIS
- **Tax Administration** — https://www.cravencountync.gov/220/Tax-Administration
- **Real Estate Appraisal** — https://www.cravencountync.gov/2258/Real-Estate-Appraisal
- **View My Property Card (CRRP search)** — https://www.bttaxpayerportal.com/ITSPublicCRRP/RealEstateSearch
- **Tax bill search (ITSPublicCR)** — https://www.bttaxpayerportal.com/ITSPublicCR/TaxBillSearch
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/craven/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/craven/parcel-detail/{PID}`
- **GIS map deep-link** — `https://gis.cravencountync.gov/maps/map.htm?pid={PID}`
- **Ordinances & Plans** — https://cravencountync.gov/343/Ordinances-Plans
- **NC OneMap parcels** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='049'`)
- **New Bern GIS / maps** — https://www.newbernnc.gov/departments/development_services/maps.php
- **New Bern open data** — https://gis-newbern.opendata.arcgis.com/
- **New Bern zoning REST** — https://gis.newbernnc.gov/arcgis/rest/services/Dev_Services/Zoning/FeatureServer/0
- **Register of Deeds** — https://us5.courthousecomputersystems.com/CravenNC2

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | JustParcels/`CSV` `PID`; OneMap `parno`; `PREFN` | Same PIN format e.g. `2-036   -7000` (spaces significant) |
| polygons | Yes | JustParcels FS/MS/0; OneMap FS/1 | CRS **102719 / 2264** |
| acreage | Yes | `PACREA` (prefer); OneMap `gisacres` / `Shape__Area/43560` | gisacres OK here (~5902 in 5–150) |
| ownerName | Yes | `PANAME` / OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `TMADDR`/`CITYNM`/`TAXSTE`/`ZIP` | |
| situs address | Yes | `FULLADD`; components `PAST*`; OneMap `siteadd` | |
| lastSale date/price | Partial | **price** `SALE_PRICE`; **date** OneMap `saledate` or `PRECYR/M/D` | JustParcels/`parcels.csv` **SALE_DATE broken** |
| tax values | Yes | `totval`/`totlnd`/`totbld`; OneMap `parval`/`landval`/`improvval` | Strong on both |
| zoning | Yes (cities-first) | New Bern `ZONE`; Havelock `ZONING` | Other munis + unincorp REST gap |
| flu | Gap | New Bern 2022 LUP / CAMA regional PDFs | No FeatureServer |
| appraiser / viewer link | Yes | map.htm `?pid={PID}`; NCPTS `{PID}`; CRRP search | TRANCHE-3 |

### PACITY router (CSV / JustParcels → city-first zoning)

| PACITY | Municipality | Approx parcels | Zoning source |
|--------|--------------|----------------|---------------|
| *(blank)* | Unincorporated | 31,348 | No base zoning FS (EWN airport overlay only) |
| NEW BERN | **New Bern** | 17,964 | New Bern Zoning FS/0 (city-first PRIMARY) |
| HAVELOCK | **Havelock** | 4,984 | County Planning/5 Havelock Zoning (city-first) |
| TRENT WOODS | **Trent Woods** | 2,204 | No public zoning FS |
| RIVER BEND | **River Bend** | 1,756 | No public zoning FS |
| VANCEBORO | **Vanceboro** | 648 | No public zoning FS |
| BRIDGETON | **Bridgeton** | 402 | No public zoning FS |
| DOVER | **Dover** | 381 | No public zoning FS |
| COVE CITY | **Cove City** | 343 | No public zoning FS |

### New Bern ZONE (top; ~261 polys)

| ZONE | Count |
|------|-------|
| C-3 | 39 |
| C-4 | 29 |
| R-6 | 27 |
| C-5 | 25 |
| R-10 | 24 |
| I-1 / R-8 | 18 each |
| R-15 | 16 |
| R-10A | 14 |
| A-5 / A-5F / R-20 | 10 each |

### Havelock ZONING (373 polys)

| ZONING | Count |
|--------|-------|
| HC | 85 |
| R-20A | 57 |
| R-10 | 45 |
| RM | 30 |
| R-7 | 26 |
| GS | 24 |
| LI | 21 |
| RMH | 20 |
| R-20 | 18 |
| MR | 14 |

## Layers (verified 2026-09-24)

### 1. JustParcels/Parcels — PRIMARY county ArcGIS CAMA + sale price

- **Purpose:** parcels | tax | ownership | sales (price) | situs
- **REST URL:** https://gis.cravencountync.gov/arcgis/rest/services/JustParcels/MapServer/0
- **Also:** mMaps/Property/MapServer/19 (tax/owner/acres; **no** SALE_PRICE)
- **CSV twin:** https://gis.cravencountync.gov/Downloads/CSV_files/parcels.csv (~60,030 rows)
- **Key fields → targets:** `PID`→parcelId; `PREFN`→parcelIdProp; `PANAME`→ownerName; `TMADDR`/`CITYNM`/`TAXSTE`/`ZIP`→mailing; `FULLADD`→situs; `PACREA`→acreage; `SALE_PRICE`→lastSale.price; `totval`/`totlnd`/`totbld`→tax; `PLUSC`/`LUDESC`→dorCode/landUse; `PACITY`→municipality; `PABOOK`/`PAPAGE`→deed; `PRECYR`/`PRECMN`/`PRECDY`→recorded date parts
- **WKID / CRS:** 102719 / 2264
- **Verified:** count **60,029** (CSV 60,030); PACREA 5–150 → **5,943** (CSV **5,940**); SALE_PRICE>0 → **34,789**; sale+band → **2,169**; totval>0 → **59,883**; vacant band → **3,717**; owner ~**60,028**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. Cloudflare may **403** bare queries — send browser User-Agent (+ Referer to map.htm). **SALE_DATE unusable.** Geo-check PID `2-036   -7000` ≈ **-77.007, 35.119** (New Bern). Auth: none (public).

### 2. NC OneMap Parcels — statewide REST + usable sale date

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='049'`
- **Key fields:** `parno`, `ownname`, mail/site, `gisacres`, `Shape__Area`, `landval`/`improvval`/`parval`, `saledate`
- **Verified:** count **59,840**; gisacres 5–150 → **5,902**; Shape__Area 5–150 → **5,892**; ownname **59,840**; parval>0 **59,799**; landval>0 **59,506**; saledate present **59,840** (recent samples decode OK e.g. 2026-05-11)
- **Notes:** Join `parno`=`PID`. Prefer for **lastSale.date**; prefer JustParcels for **SALE_PRICE**. MaxRecordCount **5000**.

### 3. New Bern Zoning — city-first PRIMARY (New Bern)

- **REST:** https://gis.newbernnc.gov/arcgis/rest/services/Dev_Services/Zoning/FeatureServer/0
- **Also:** MapServer twin; overlays `Dev_Services/Zoning_Overlays`
- **Fields:** `ZONE`, `ZONE_DESC`, setbacks / use flags
- **Verified:** zone-group sum **~261** polygons (2026-09-24)
- **Notes:** Spatial-join inside New Bern limits / ETJ. Open data hub: https://gis-newbern.opendata.arcgis.com/

### 4. Havelock Zoning — city-first PRIMARY (Havelock)

- **REST:** https://gis.cravencountync.gov/arcgis/rest/services/mMaps/Planning/MapServer/5
- **Fields:** `ZONING`, `DETAILS`
- **Verified:** count **373**

### 5. EWN / airport land-use overlay (not city base zoning)

- **REST:** https://gis.cravencountync.gov/arcgis/rest/services/mMaps/Planning/MapServer/2 (EWN Landuse Zoning)
- **Verified:** count **538** — Coastal Carolina Regional Airport overlay (`AIRPORT_ZO`)
- **Downloads:** AICUZ / Cherry Point noise / accident potential shapefiles on county downloads page

### 6. City Limits + ETJ

- **City Limits:** https://gis.cravencountync.gov/arcgis/rest/services/Political_Boundaries/MapServer/2 — **8** cities: New Bern, Havelock, Trent Woods, River Bend, Vanceboro, Bridgeton, Dover, Cove City
- **ETJ:** MapServer/3 — Havelock, New Bern (2 polys), River Bend
- **Shapefile:** https://gis.cravencountync.gov/Downloads/Shape_files/city_limits.zip

### 7. Sales CSV (calendar export) — supplemental

- **URL:** https://gis.cravencountync.gov/Downloads/CSV_files/Sales_For_Current_Calendar_Year.csv
- **Fields:** `Parcel_Id`, `Sale_Date` (YYYYMMDD), `Sale_Price`, sellers/buyers, deed book/page
- **Verified:** **822** rows (file may lag “current year” naming — still valid sale attributes)
- **Notes:** Prefer for recent qualified sales join; countywide last-sale **price** still on JustParcels `SALE_PRICE`

### 8. FLU — gap (PDF / plan docs)

- New Bern maps / plans hub: https://www.newbernnc.gov/departments/development_services/maps.php
- Re-NewBern / 2022 Land Use Plan materials (docs, no public FLU FeatureServer found 2026-09-24)
- CAMA New Bern–Trent Woods–River Bend regional land use plan (DEQ / city PDF archives)
- County Ordinances & Plans: https://cravencountync.gov/343/Ordinances-Plans (Ch. 41 zoning article; CTP — not parcel FLU FS)

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS viewer (iMaps) | https://gis.cravencountync.gov/maps/default.aspx |
| Classic viewer + parcel deep-link | `https://gis.cravencountync.gov/maps/map.htm?pid={PID}` |
| NCPTS parcel detail | `https://lrcpwa.ncptscloud.com/craven/parcel-detail/{PID}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/craven/parcel-search |
| Property card search (BI-Tek CRRP) | https://www.bttaxpayerportal.com/ITSPublicCRRP/RealEstateSearch |
| Tax bill search | https://www.bttaxpayerportal.com/ITSPublicCR/TaxBillSearch |
| County GIS hub | https://gis.cravencountync.gov/new_home/ |

Example: PID `2-036   -7000` (URL-encode spaces) → https://gis.cravencountync.gov/maps/map.htm?pid=2-036%20%20%20-7000 (HTTP 200). CRRP has **no** public `RealEstateSearch/Parcel/{id}` GET deep-link (404); AppraisalCard.aspx returns empty shell — use map.htm / NCPTS for parcel-ID links.

## Gaps

- JustParcels / parcels.csv **`SALE_DATE` corrupt** — do not wire; use OneMap `saledate` or `PRECYR`/`PRECMN`/`PRECDY`
- No public zoning FeatureServer for Trent Woods, River Bend, Vanceboro, Bridgeton, Dover, Cove City
- Unincorporated Craven: no countywide base-zoning FS (airport/MCAS overlays only)
- FLU FeatureServer gap (plan PDFs / story maps only)
- BI-Tek CRRP lacks working parcel-ID GET deep-link / AppraisalCard payload
- Map2 legacy service 404 (Havelock zoning lives under mMaps/Planning/5)
- Utilities / AADT / emails / phones / paid vendors intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** JustParcels count/acres/sale/tax + geo sample; full parcels.csv parse (60030); OneMap `cntyfips='049'` counts + saledate samples; New Bern ZONE stats; Havelock Zoning 373 + zone groups; City Limits 8 / ETJ 4; map.htm?pid + NCPTS + ITSPublicCRRP/CR portals 200; downloads CSV 200
