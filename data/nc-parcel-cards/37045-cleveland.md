# Cleveland County, NC — GIS County Card

## Summary

Cleveland County (Charlotte MSA, FIPS **37045**) publishes a strong **public** ArcGIS REST stack at `gis.clevelandcounty.com`: countywide **parcel polygons + CAMA** (owner, mailing, situs, calculated/deeded acres, land/building/total values) on `Basemap/Basemap` FeatureServer **Parcels / 2**. **Zoning is city-first** via county-hosted `Planning/Zoning` layers for **Shelby**, **Kings Mountain**, **Boiling Springs**, plus unincorporated **Cleveland County Zoning**. **FLU** exists as county `Original_LandUsePlan` (`USE_`) and city-first **Boiling Springs Land Use Plan** (`Future` on webgis). Last-sale **price** is not on the parcel layer — join `Tax/Vacant_ImprovedLot_Sales`. **NC OneMap** (`cntyfips='045'`) is a usable ownership/tax fallback but **gisacres is zero** for Cleveland. Main gaps: small-town ZoneType stubs (`N/A`), no Shelby/KM public FLU REST, Belmont is **Gaston** (not Cleveland).

## Portals

- **WebGIS viewer** — https://www.webgis.net/nc/Cleveland/
- **Property card (PA deep-link)** — https://www.webgis.net/nc/Cleveland/PropertyCard.php?pid={COUNTY_PID}
- **Parcel history** — https://www.webgis.net/nc/Cleveland/ParcelHistory.php?pid={COUNTY_PID}
- **County ArcGIS REST** — https://gis.clevelandcounty.com/arcgis/rest/services
- **WebGIS MapServer mirror** — https://www.webgis.net/arcgis/rest/services/NC/Cleveland/MapServer
- **Tax payments (Catalis)** — https://www.clevelandcountytaxes.com/taxes.html — search UI; no stable parcel deep-link verified
- **County GIS Services page** — https://www.clevelandcounty.com/main/departments/planning___zoning/gis_services.php
- **City of Shelby GIS** — https://www.cityofshelby.com/o/cos/page/gis — staff-only Hub; defers to county for public parcels/zoning
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `GIS_PIN` (map PIN); `COUNTY_PID`/`GIS_PID` (account) | Prefer `GIS_PIN` for spatial; `COUNTY_PID` for PropertyCard + sales join; OneMap `parno`↔`COUNTY_PID` |
| polygons | Yes | Basemap/Basemap/FeatureServer/2 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `GIS_Calculated_Acres`; `GIS_Deeded_Acres`; `COUNTY_ACRES` | ~**14,154** parcels in 5–150 ac; OneMap `gisacres` **unusable** (0) |
| ownerName | Yes | `COUNTY_OWNER_1`+`_2`; `GIS_Owner1`+`2`; OneMap `ownname` | Prefer COUNTY_*; no phones/emails |
| mailing address | Yes | `COUNTY_MAILING_ADDRESS`,`COUNTY_CITY`,`COUNTY_STATE`,`COUNTY_ZIP` | |
| situs address | Yes (partial) | `COUNTY_ADDRESS` / `LOCATE_ADDRESS`; OneMap `siteadd` | Often street-only on vacant |
| lastSale date/price | Partial | Vacant/Improved Lot Sales `Sales_Amount`,`DateSold*` | Join by `Parcel_Number`=`COUNTY_PID`; not on parcel attrs; not full history |
| tax values | Yes | `COUNTY_LAND_VALUE`,`COUNTY_BUILDING_VALUE`,`COUNTY_TOTAL_VALUE`; OneMap `parval`/`landval`/`improvval` | Integers on county |
| zoning | Yes (split by city) | Shelby/KM/BS/County `ZoneType` polygons | **City-first** — see Municipalities |
| FLU | Partial | County `USE_`; Boiling Springs `Future` | No Shelby/KM public FLU FS |
| appraiser / viewer link | Yes | PropertyCard.php?pid=; ParcelHistory.php?pid= | Templates below |

## Layers (verified)

### 1. Basemap Parcels — parcels + ownership + tax (PRIMARY)

- **Purpose:** parcels | tax | ownership
- **REST URL:** https://gis.clevelandcounty.com/arcgis/rest/services/Basemap/Basemap/FeatureServer/2
- **Mirrors:** Basemap/Basemap/MapServer/2; Basemap/Parcels/MapServer/0 (ParcelsAtt)
- **Layer name / id:** Parcels / 2
- **Geometry:** Polygon
- **Key fields → targets:**
  - `GIS_PIN` → parcelId (map PIN)
  - `GIS_PID` / `COUNTY_PID` / `LOCATE_PID` → account id (PropertyCard + sales join)
  - `GIS_Calculated_Acres`, `GIS_Deeded_Acres`, `COUNTY_ACRES` → acreage
  - `COUNTY_OWNER_1`, `COUNTY_OWNER_2` → ownerName
  - `COUNTY_MAILING_ADDRESS`, `COUNTY_CITY`, `COUNTY_STATE`, `COUNTY_ZIP` → mailing
  - `COUNTY_ADDRESS`, `LOCATE_ADDRESS` → situs
  - `COUNTY_LAND_VALUE`, `COUNTY_BUILDING_VALUE`, `COUNTY_TOTAL_VALUE` → tax
- **WKID / CRS:** 102719 (latest 2264) — NAD 1983 StatePlane NC Feet
- **Verified:** yes — count **70,189**; `GIS_Calculated_Acres BETWEEN 5 AND 150` → **14,154**; `COUNTY_TOTAL_VALUE>0` → **69,677**; sample centroid ≈ **-81.43, 35.25** (in-county)
- **Notes:** No sale price on layer. MaxRecordCount **2000** — paginate. License: attribute Cleveland County GIS; NCGS 132-10 commercial resale limits.

### 2. Tax Parcel Area — geometry subset

- **REST URL:** https://gis.clevelandcounty.com/arcgis/rest/services/Tax/Tax/FeatureServer/1
- **Verified:** count **60,300** — closer to OneMap; thinner attrs (no COUNTY_* tax/mailing). Prefer Basemap/2.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='045'` → **59,964**
- **Join:** `parno` ↔ `COUNTY_PID` (verified `parno='10011'`)
- **Caveat:** `gisacres` is **0.0** for Cleveland samples — acreage filters fail; use county acres. No sale price.

### 4. Vacant + Improved Lot Sales — last-sale price join

- **Vacant:** https://gis.clevelandcounty.com/arcgis/rest/services/Tax/Vacant_ImprovedLot_Sales/MapServer/0 — count **2,765** (`Sales_Amount>0` → 2759)
- **Improved:** …/MapServer/1 — count **6,481** (`Sales_Amount>0` → 6475)
- **Fields:** `Parcel_Number`, `Sales_Amount`, `DateSold` / `DateSold_YYYYMMDD`, acres
- **Join:** `Parcel_Number` = `COUNTY_PID` (verified PID 38691)

### 5. Shelby Zoning — city-first

- **REST URL:** https://gis.clevelandcounty.com/arcgis/rest/services/Planning/Zoning/FeatureServer/6
- **Fields:** `ZoneType`, `Municipality`
- **Verified:** count **1,371**
- **Notes:** Prefer over county Zoning inside Shelby / Shelby-ETJ. No public city-native FS.

### 6. Kings Mountain Zoning — city-first (Cleveland-side)

- **REST URL:** …/Planning/Zoning/FeatureServer/5
- **Verified:** count **7,888**
- **Notes:** KM straddles Gaston — Cleveland FIPS only here; Gaston card for west side.

### 7. Boiling Springs Zoning — city-first

- **REST URL:** …/Planning/Zoning/FeatureServer/9
- **Verified:** count **241**

### 8. Cleveland County Zoning — unincorporated

- **REST URL:** …/Planning/Zoning/FeatureServer/0
- **Verified:** count **370**
- **Notes:** Use outside municipal zoning footprints.

### 9. Town Jurisdiction Zoning — stubs (gap)

- **REST URL:** …/Planning/Zoning/FeatureServer/40
- **Verified:** count **7** — Casar, Fallston, Kingstown, Lattimore, Patterson Springs, Polkville, Waco with `ZoneType_Code='N/A'`
- **Status:** gap for district codes; fall back to county Zoning/0

### 10. Original Land Use Plan — county FLU

- **REST URL:** https://gis.clevelandcounty.com/arcgis/rest/services/Planning/LandUse/FeatureServer/0
- **Field:** `USE_` — PRIMARY/SECONDARY GROWTH AREA, RURAL PRESERVATION, AIRPORT COMPATIBILITY, TOWNS AND CITIES
- **Verified:** count **28**

### 11. Boiling Springs Land Use Plan — city FLU

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Cleveland/MapServer/30
- **Field:** `Future`
- **Verified:** count **70**

### 12. Jurisdiction polygons

- **REST URL:** https://gis.clevelandcounty.com/arcgis/rest/services/Basemap/Basemap/FeatureServer/4
- **Names:** Shelby (+ETJ), Kings Mountain (+ETJ), Boiling Springs (+ETJ), Grover, Belwood, Casar, Earl, Fallston, Kingstown, Lattimore, Lawndale, Mooresboro, Patterson Springs, Polkville, Waco, Cleveland County
- **Not present:** Belmont (Gaston County)

## Municipalities (city-first routing)

| Municipality | Zoning source | FLU | Notes |
|--------------|---------------|-----|-------|
| Shelby | Planning/Zoning/6 | county USE_ only | No public city FS |
| Kings Mountain | Planning/Zoning/5 | county USE_ only | Also in Gaston |
| Boiling Springs | Planning/Zoning/9 | webgis MapServer/30 `Future` | Strongest city FLU |
| Unincorporated | Planning/Zoning/0 | Original_LandUsePlan | |
| Grover / Belwood / Earl / Lawndale / Mooresboro | county Zoning/0 | county USE_ | No town ZoneType layer |
| Casar / Fallston / Kingstown / Lattimore / Patterson Springs / Polkville / Waco | layer 40 stubs N/A → county/0 | county USE_ | District gap |
| Belmont | n/a | n/a | **Gaston** (37071) — not Cleveland |

## Appraiser / viewer deep-links

- **Property card:** `https://www.webgis.net/nc/Cleveland/PropertyCard.php?pid={COUNTY_PID}` — verified live (PID 10011)
- **Parcel history:** `https://www.webgis.net/nc/Cleveland/ParcelHistory.php?pid={COUNTY_PID}`
- **Map viewer:** `https://www.webgis.net/nc/Cleveland/` — `?pid=` / `?PIN=` accepted by shell; prefer PropertyCard for stable PA
- **REST by PIN:** `…/Basemap/Basemap/FeatureServer/2/query?where=GIS_PIN='{GIS_PIN}'&outFields=*&f=json`
- **REST by account:** `…/query?where=COUNTY_PID='{COUNTY_PID}'&…`

## Gaps

- Sale price/date not on parcel layer (join sales layers; partial sets)
- OneMap `gisacres` zero for Cleveland
- Parcel count mismatch Basemap 70k vs Tax/OneMap ~60k
- Small-town ZoneType gap; Grover et al. no district layer
- No Shelby/KM public FLU FeatureServer
- No city-native public ArcGIS hosts
- Utilities / AADT / emails / phones / paid vendors excluded by suite rules

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live probes:** county REST root + layer counts/fields/samples; NC OneMap `cntyfips='045'`; PropertyCard.php; geo-centroid in Cleveland; Belmont absent from Jurisdiction


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://gis.clevelandcounty.com/arcgis/rest/services/Basemap/Basemap/FeatureServer/2 · id `COUNTY_PID` · live count **70,189** · 5–150 ac **14,154** (`GIS_Calculated_Acres >= 5 AND GIS_Calculated_Acres <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='CLEVELAND'` gives **716** stations (299 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CLEVELAND%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Cleveland'` gives **737** stations (460 with AADT_2025, 398 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Cleveland%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Cleveland'` gives **719** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `COUNTY_TOTAL_VALUE` non-zero **69,677**, `COUNTY_LAND_VALUE` non-zero **69,618**
- **Sale history (partial):** no sale fields on primary layer. No sale fields on Basemap/2 parcels. Sale subset polygons: Tax/Vacant_ImprovedLot_Sales MapServer/0 (vacant) + /1 (improved), fields Sales_Amount, DateSold, Parcel_Number(=COUNTY_PID). OneMap saledate empty for 045. Full history → PropertyCard.php.
- **Owner entity:** fields `COUNTY_OWNER_1`, `COUNTY_OWNER_2`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **2,022** of 14,154 (extended regex: 2,486).
- **PA deep link:** `https://www.webgis.net/nc/Cleveland/PropertyCard.php?pid={COUNTY_PID}`. Tested `42589` → HTTP **200** (text/html), content verified: True. Parcel id found in the response body.
- **Jurisdiction GIS viewer:** https://www.webgis.net/nc/Cleveland/ → HTTP **200** (Cleveland County NC WebGIS)
- **Pass 2 gaps:** No sale price/date on parcel layer — only vacant/improved lot sales subset layers + PropertyCard
