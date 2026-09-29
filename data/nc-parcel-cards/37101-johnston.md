# Johnston County, NC — GIS County Card

## Summary

Johnston County (Raleigh–Durham / Triangle footprint, FIPS **37101**) publishes strong **public** ArcGIS REST at `cityworks.johnstonnc.com`: countywide **tax parcel polygons** (~**126,846**; ~**14,287** with `CALC_ACREAGE` 5–150) with ownership, mailing, assessed/market values, last sale date/price, and GIS acreage on `TAX/ParcelMap` (mirrors on `Public_Layers` and `Planning/Land_Use`). Prefer **`TAG`** (tax parcel number) over **`PIN`** / `ACCOUNT_NUMBER`. **Situs is not on parcel polygons** — join **Address Points** on `TAG` (or use NC OneMap `siteadd`). **Zoning is city-first where local GIS exists:** only **Clayton** publishes true local zoning + FLU (`cw2.townofclaytonnc.org` Clariti). Other munis (Smithfield, Selma, Benson, Archer Lodge, Four Oaks, Kenly, Pine Level, Princeton, Micro, Wilson’s Mills) use county **`town_zoning`** (4042 polys, no muni attribute — clip with `city_limits`) plus unincorporated **`county_zoning`**. County-host folders named for Clayton/Selma/Smithfield/Wilson’s Mills largely **republish countywide** layers (not city-clipped). **NC OneMap** (`cntyfips='101'`) is a solid fallback with situs on polys. Main gaps: no countywide FLU; Municipal Transition Districts shapefile-only; Brady property card POST-only.

## Portals

- **MapClick (viewer)** — https://mapclick8.johnstonnc.com/mapclick6/index.html/
- **GIS Department / downloads** — https://www.johnstonnc.gov/gis2/content.cfm?PD=data
- **County ArcGIS REST** — https://cityworks.johnstonnc.com/server/rest/services
- **Tax / Property Record Cards (Brady ITS)** — https://www.johnstonnc.gov/taxcards/ → https://www.bttaxpayerportal.com/itspublicjo
- **Tax bill deep-link** — `https://www.bttaxpayerportal.com/ITSPublicJO/TaxBillSearch/Parcel/{TAG}`
- **Sales search (HTML)** — https://www.bttaxpayerportal.com/TaxJO/Sales.aspx
- **Town of Clayton GIS REST** — https://cw2.townofclaytonnc.org/gis/rest/services — Clariti Zoning + Future Land Use
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Municipalities (first-class)

| Municipality | Local public GIS? | Zoning / FLU source |
|--------------|-------------------|---------------------|
| **Clayton** | **Yes** — `cw2.townofclaytonnc.org` Clariti + Planning | Zoning FS/7 (1349); FLU FS/9 (71). Prefer over county republish |
| Smithfield | County-host folder only (republish) | County `town_zoning` + `city_limits` |
| Selma | County-host folder only (countywide parcels) | County `town_zoning` + `city_limits` |
| Wilson’s Mills | County-host folder only (republish) | County `town_zoning` + `city_limits` |
| Benson | None found | County `town_zoning` + `city_limits` |
| Archer Lodge | None found | County `town_zoning` + `city_limits` |
| Four Oaks | None found | County `town_zoning` + `city_limits` |
| Kenly | None found | County `town_zoning` + `city_limits` |
| Pine Level | None found | County `town_zoning` + `city_limits` |
| Princeton | None found | County `town_zoning` + `city_limits` |
| Micro | None found | County `town_zoning` + `city_limits` |
| Unincorporated / ETJ | County | `county_zoning` + IHI overlay; ETJ layer (10) |

`city_limits` distinct names (335 polys): Archer Lodge, Benson, Clayton, Four Oaks, Kenly, Micro, Pine Level, Princeton, Selma, Smithfield, Wilson’s Mills.

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `TAG` (preferred); `PIN`; `ACCOUNT_NUMBER`; OneMap `parno`≈PIN | TAG ≈ tax number for MapClick / Brady bill link |
| polygons | Yes | TAX/ParcelMap FS/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALC_ACREAGE`, `ASSESSED_ACREAGE` | ~**14,287** CALC 5–150; ~**14,243** ASSESSED 5–150 |
| ownerName | Yes | `Name1`/`Name2` / OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `Address1`,`Address2`,`City`,`State`,`ZipCode` | On parcel layer |
| situs address | Yes (join) | Address Points `FULL_ADDRESS`+parts on `TAG`; OneMap `siteadd` | **Not** on county parcel polys |
| lastSale date/price | Yes | `SALES_DATE`,`SALES_PRICE`; `QualifiedCode` | Last sale only; epoch ms |
| tax values | Yes | `MARKET_VALUE`,`LAND_VALUE`,`BUILDING_VALUE`,`OTHER_VALUE`,`TOTAL_VALUE` | |
| zoning | Yes (split) | `county_zoning.ZONING`; `town_zoning.ZONING`; Clayton `Abreviation` | Spatial join; Clayton local first |
| flu | Partial | Clayton Clariti `FLU` only | Countywide FLU gap |
| dorCode / land use | Yes | `LAND_CLASSIFICATION`,`USE_CODE` | Local strings |
| appraiser / viewer link | Partial | Brady Basic Search + TaxBillSearch/Parcel/{TAG}; MapClick | Full card = POST ViewParcel (no durable GET) |

## Layers (verified)

### 1. TAX/ParcelMap Parcels — PRIMARY

- **Purpose:** parcels | tax | ownership | sales (last)
- **REST URL:** https://cityworks.johnstonnc.com/server/rest/services/TAX/ParcelMap/FeatureServer/0
- **Mirrors:** Public_Layers/PublicLayers/MapServer/1 ; Planning/Land_Use/FeatureServer/3
- **Geometry:** Polygon | **CRS:** 102719 / 2264 | **MaxRecordCount:** 5000
- **Key fields → targets:** `TAG`→parcelId; `PIN`→parcelIdPin; `ACCOUNT_NUMBER`; `CALC_ACREAGE`/`ASSESSED_ACREAGE`→acreage; `Name1`/`Name2`→owner; `Address1`–`ZipCode`→mailing; `SALES_DATE`/`SALES_PRICE`/`QualifiedCode`→lastSale; `MARKET_VALUE`/`LAND_VALUE`/`BUILDING_VALUE`/`TOTAL_VALUE`→tax; `LAND_CLASSIFICATION`/`USE_CODE`
- **Verified:** count **126,846**; CALC 5–150 → **14,287**; ASSESSED 5–150 → **14,243**; vacant-ish (BUILDING_VALUE=0) in CALC 5–150 → **9,042**; ~1 null TAG; ~470 null PIN
- **Notes:** PRIMARY. Mailing only on polygon. Shapefile daily download also on GIS data page.

### 2. Address Points — situs join

- **REST URL:** https://cityworks.johnstonnc.com/server/rest/services/Public_Layers/PublicLayers/MapServer/0
- **Mirror:** Planning/Land_Use/FeatureServer/2
- **Geometry:** Point | count **124,576**
- **Join:** `TAG` → parcel `TAG` (many-to-one)
- **Fields:** `FULL_ADDRESS`, `ST_*`, `Inc_Muni`, `ETJ`, `MSAG_Comm`, `ZIPCODE` (often 0)

### 3. NC OneMap Parcels (fallback)

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='101'`
- **Verified:** count **125,583**; gisacres 5–150 → **14,291**
- **Notes:** Has `siteadd`/`scity` on polys; `parno` tracks PIN not TAG; no sale price. MaxRecordCount 5000.

### 4. County Zoning (unincorporated)

- **REST URL:** https://cityworks.johnstonnc.com/server/rest/services/Planning/Land_Use/FeatureServer/7
- **Count:** **2,168** | field `ZONING` (AR, RR, GB, I-1/I-2, NB, O-I, CB, PUD, MHPD, CLD, conditional/SUD variants, …)

### 5. Town Zoning (aggregate)

- **REST URL:** https://cityworks.johnstonnc.com/server/rest/services/Planning/Land_Use/FeatureServer/9
- **Count:** **4,042** | ~115 codes | **no municipality field** — clip with city_limits
- **Caveat:** Smithfield/Wilson’s Mills/Clayton **county-host** “Town_Zoning” layers are this same countywide republish (count 4042)

### 6. Clayton Zoning (Clariti) — city-first

- **REST URL:** https://cw2.townofclaytonnc.org/gis/rest/services/Clariti/Clariti/FeatureServer/7
- **Count:** **1,349** | CRS **6543** | `Abreviation`→zoning, `Zoning`→label
- **Alternate:** Planning/Zoning/MapServer/0 (count 1384)

### 7. Clayton Future Land Use (Clariti) — city-first

- **REST URL:** https://cw2.townofclaytonnc.org/gis/rest/services/Clariti/Clariti/FeatureServer/9
- **Count:** **71** | field `FLU`
- **Alternate:** Planning/Future_Land_Use/MapServer/1 (count 71)

### 8. IHI Overlay

- **REST URL:** …/Planning/Land_Use/FeatureServer/8 | count **54** | overlay on base zoning

### 9. City Limits + ETJ (routers)

- **City limits:** …/FeatureServer/6 | count **335** | `NAME` / `Inc_Muni`
- **ETJ:** …/FeatureServer/0 | count **10** | `ETJ_NAME` (no Archer Lodge row)

## Gaps

- No situs on county parcel polygons — join Address Points / OneMap
- No countywide FLU — Clayton only on public REST
- Municipal Transition Districts = shapefile download only (no REST)
- town_zoning lacks municipality attribute
- County muni folders are mostly republishes; only Clayton Clariti is true local
- No independent REST for Archer Lodge, Benson, Four Oaks, Kenly, Micro, Pine Level, Princeton
- Last-sale only; Brady full card POST-only; TaxBillSearch GET by TAG for bills
- MaxRecordCount pagination; no phones/emails; no AADT/utilities on this card

## License / verification

County + Clayton open GIS; public query endpoints; attribution required; no paid vendors.

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://cityworks.johnstonnc.com/server/rest/services/TAX/ParcelMap/FeatureServer/0 · id `TAG` · live count **126,850** · 5–150 ac **14,285** (`CALC_ACREAGE >= 5 AND CALC_ACREAGE <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='JOHNSTON'` gives **793** stations (302 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27JOHNSTON%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Johnston'` gives **803** stations (562 with AADT_2025, 400 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Johnston%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Johnston'` gives **794** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `MARKET_VALUE` non-zero **123,978**, `TOTAL_VALUE` non-zero **123,978**, `LAND_VALUE` non-zero **123,741**
- **Sale history (ok):** price `SALES_PRICE` >0 **77,052**; date `SALES_DATE` non-null **124,270**
- **Owner entity:** fields `Name1`, `Name2`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **3,594** of 14,285 (extended regex: 3,773).
- **PA deep link:** `https://www.bttaxpayerportal.com/ITSPublicJO/TaxBillSearch/Parcel/{TAG}`. Tested `05I05020L` → HTTP **200** (text/html), content verified: True. Parcel id found in the response body.
- **Jurisdiction GIS viewer:** https://mapclick8.johnstonnc.com/mapclick6/index.html/ → HTTP **200** (MapClick)
- **Pass 2 gaps:** Brady property card is POST-only; deep link is the tax-bill page (TaxBillSearch/Parcel/{TAG}), not the full appraisal card
