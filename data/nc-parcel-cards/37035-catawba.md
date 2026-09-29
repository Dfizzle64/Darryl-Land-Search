# Catawba County, NC — GIS County Card

## Summary

Catawba County (Charlotte MSA, FIPS **37035**) publishes a strong **public** ArcGIS REST stack at `arcgis2.catawbacountync.gov`: countywide **parcel polygons + CAMA** (owner, mailing/situs pieces, calculated acreage, land/building/total values, last-sale date/amount, and parcel-joined zoning stubs) on `energov/energov_permit_ctr` FeatureServer **Parcels / 0**. **Zoning is city-first** via combined `Zoning_All` (District = Hickory / Newton / Conover / Claremont / Maiden / Catawba / Brookford / Long View / County) plus a separate **County Zoning** layer. City of **Hickory** also exposes native `arcgis.hickorync.gov` **Hickory_Zoning**, **Hickory_Future_Land_Use**, and overlays. **NC OneMap** (`cntyfips='035'`) is a solid statewide fallback. Main gaps: **no independent city ArcGIS** for Newton/Conover/Claremont/Maiden/Catawba/Brookford/Long View; county **FLU** is Small Area Plan districts (not full FLU polygons) outside Hickory; energov tax/sale fields are **currency strings**.

## Portals

- **GIS Real Estate Maps (viewer)** — https://gis.catawbacountync.gov/parcel/ — Deep link: `https://gis.catawbacountync.gov/parcel/?pinc={PIN}`
- **GIS Real Estate Reports (no map)** — https://gis.catawbacountync.gov/nomap/ — Also accepts `?pinc=` / `?lrk=`
- **County ArcGIS REST** — https://arcgis2.catawbacountync.gov/arcgis/rest/services
- **Tax Real Estate Search (ITS)** — https://taxbill.catawbacountync.gov/ITSPublicCT/RealEstateSearch — Search by REID/LRK
- **Parcel Analysis + county CSV** — https://gis.catawbacountync.gov/parcel_analysis/ — Full-county CSV: https://gis.catawbacountync.gov/DataWarehouse/csv/catco_pa.csv
- **Parcel report field dictionary** — https://gis.catawbacountync.gov/misc/datadesc.html
- **Planning & Parks (Small Area Plans)** — https://www.catawbacountync.gov/county-services/planning-and-parks/
- **City of Hickory ArcGIS REST** — https://arcgis.hickorync.gov/server/rest/services
- **SmartGov public portal** — https://co-catawba-nc.smartgovcommunity.com/Public/Home
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` / `Parcel_ID` (12-digit); `LRK` (REID) | Prefer `PIN` for map/OneMap joins; `LRK` for tax search |
| polygons | Yes | energov Parcels/0 or Real_Estate_Basemap/2 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `Caculated_Acreage` (energov; misspelled); `CALCAC` (geometry layers); OneMap `gisacres` | ~**8,502** parcels in 5–150 ac |
| ownerName | Yes | `Name`+`Name2` / table `owner`+`owner2` / OneMap `ownname` | Respect `LEO_HideName='Y'` (~223); no phones/emails |
| mailing address | Yes | `Address`,`Address2`,`City`,`State`,`Zip` | |
| situs address | Yes (partial) | `Building_Number`+`Street_Name`,`Parcel_Zip`; OneMap `siteadd`; address_all table | Many vacant lack building number |
| lastSale date/price | Yes (partial) | `Sale_Date`,`Sale_Amount` (strings); table `sale_date`/`sale_amount` (ints) | ~3,098 of 5–150 ac have non-empty Sale_Amount; CSV has Sale Validity; OneMap date only |
| tax values | Yes | `Land_Value`,`Total_Buildings_Value`,`Total_Value` (strings); table typed ints; OneMap `parval`/`landval`/`improvval` | Strip `$`/commas on energov |
| zoning | Yes (split by city) | Parcel `Zoning` stub **or** `Zoning_All` / County Zoning / Hickory_Zoning polygons | **City-first** — see Municipalities |
| FLU | Partial | Hickory `FLU`; county SAP `NAME` / parcel `Small_Area_Plan` | Full FLU REST only for Hickory |
| appraiser / viewer link | Yes | GIS map by `PIN`; reports by `pinc`/`lrk`; tax search by REID | Templates below |

## Layers (verified)

### 1. energov_permit_ctr Parcels — parcels + ownership + tax + last sale + zoning stub (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | zoning (joined stub)
- **REST URL:** https://arcgis2.catawbacountync.gov/arcgis/rest/services/energov/energov_permit_ctr/FeatureServer/0
- **Mirrors:** energov_permit_ctr/MapServer/0; ugly_map/FeatureServer/0 (same CAMA family)
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN`, `Parcel_ID` → parcelId (12-digit NC PIN; may be 16-char when structure owner differs)
  - `LRK` → REID / tax account
  - `Caculated_Acreage` → acreage (**spelling is Caculated**, not Calculated)
  - `Name`, `Name2` → ownerName
  - `Address`, `Address2`, `City`, `State`, `Zip` → mailing
  - `Building_Number`, `Street_Name`, `Parcel_Zip` → situs
  - `Sale_Date`, `Sale_Amount` → lastSale (currency **strings**)
  - `Land_Value`, `Total_Buildings_Value`, `Total_Value` → tax (currency **strings**)
  - `Zoning`, `Zoning2`, `Zoning3`, `Zoning_District`, `Zoning_Overlay` → zoning stub / jurisdiction
  - `Small_Area_Plan` → flu (SAP name text)
  - `LEO_HideName` → other (`Y` = redact owner)
- **WKID / CRS:** 102719 (latest 2264) — NAD 1983 StatePlane NC Feet
- **Verified:** yes — count **94,864**; `Caculated_Acreage BETWEEN 5 AND 150` → **8,502**; non-empty/non-zero `Sale_Amount` in range → **3,098**; sample attrs returned
- **Notes:** Best single county layer for land search. Prefer **spatial join** to `Zoning_All` / Hickory_Zoning for clean city-first codes. MaxRecordCount **1000** — paginate. License: attribute Catawba County GIS; NCGS 132-10 commercial resale limits.

### 2. Real_Estate_Basemap / Catawba_Basic Parcels — geometry + acreage

- **Purpose:** parcels (geometry)
- **REST URL:** https://arcgis2.catawbacountync.gov/arcgis/rest/services/Basemaps/Real_Estate_Basemap/MapServer/2
- **Alternates:** Real_Estate_Basemap_Map/FeatureServer/2; Catawba_Basic_MIL1/MapServer/2
- **Layer name / id:** Parcels / 2
- **Geometry:** Polygon
- **Key fields → targets:** `PIN`, `ACCOUNT`, `CALCAC`, `ASSEDAC`, `DEEDAC`, `SURVEYAC`
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **94,268**; `CALCAC` 5–150 → **8,494**
- **Notes:** No owner/sale/tax on layer. Join to energov or `cc_owner_all`. MaxRecordCount **2000**.

### 3. Catawba_Basic cc_owner_all — CAMA attribute table

- **Purpose:** ownership | tax | sales (join onto geometry)
- **REST URL:** https://arcgis2.catawbacountync.gov/arcgis/rest/services/Catawba_Basic_MIL1/MapServer/19
- **Geometry:** none (table)
- **Key fields → targets:** `pinc`→parcelId; `lrk`; `owner`/`owner2`; mailing fields; `sale_date`/`sale_amount` (ints); `land_value`/`bldg_value`/`total_value`
- **Verified:** yes — count **95,119**; `sale_amount>0` → **73,173**
- **Notes:** Typed numeric values — cleaner than energov currency strings. Pair with address_all (layer 15) for situs.

### 4. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date only)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1 *(layer 0 = points)*
- **Geometry:** Polygon
- **Key fields → targets:** `parno`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`/`scity`, `gisacres`, `saledate`/`saledatetx`, `parval`/`landval`/`improvval`, `cntyfips`
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — `cntyfips='035'` → **93,505**; `gisacres` 5–150 → **8,502**
- **Notes:** No sale price. Join `parno`↔`PIN`.

### 5. Zoning_All — municipal + county zoning (city-first)

- **Purpose:** zoning (by municipality)
- **REST URL:** https://arcgis2.catawbacountync.gov/arcgis/rest/services/energov/energov_permit_ctr/FeatureServer/60
- **Mirrors:** ugly_map/FeatureServer/7; energov_map/MapServer/66
- **Geometry:** Polygon
- **Fields:** `Zoning`, `GenZoning`, `District`
- **WKID / CRS:** 102719 / 2264
- **Verified District counts (2026-09-24):** Hickory **1736**, Newton **796**, Conover **621**, Long View **276**, Maiden **334**, County **1719**, Claremont **161**, Catawba **126**, Brookford **69**; total **5838**
- **Join to parcels:** spatial join (intersect/centroid) on CRS 2264; optionally pre-filter by `Zoning_District` / Cities polygons, then overlay matching District.

### 6. County Zoning — unincorporated only

- **REST URL:** https://arcgis2.catawbacountync.gov/arcgis/rest/services/energov/energov_permit_ctr/FeatureServer/59
- **Fields:** `ZONING`, `GENZONING`, `District`
- **Verified:** count **1714**

### 7. City of Hickory — Zoning + FLU (city native, prefer inside city limits)

- **Zoning:** https://arcgis.hickorync.gov/server/rest/services/Zoning_Overlays/Hickory_Zoning/MapServer/0 — fields `Zoning`, `Description`, `General_Zoning`; count **1740**; CRS 2264
- **FLU:** https://arcgis.hickorync.gov/server/rest/services/Zoning_Overlays/Hickory_Future_Land_Use/MapServer/0 — field `FLU`; count **142**
- **Overlays:** https://arcgis.hickorync.gov/server/rest/services/Zoning_Overlays/Hickory_Overlays/MapServer (petitions, historic, revitalization, airport, etc.)
- **Notes:** Prefer these over county `Zoning_All` District='Hickory' inside Hickory limits.

### 8. Small Area Districts / SAP — county planning areas (partial FLU)

- **REST URL:** https://arcgis2.catawbacountync.gov/arcgis/rest/services/energov/ugly_map/FeatureServer/27 (also energov_map/MapServer/43)
- **Fields:** `NAME`, `Acres`
- **Verified:** count **23** (duplicate NAME rows). Districts: ST STEPHENS/OXFORD, SHERRILLS FORD, MOUNTAIN VIEW, STARTOWN, PLATEAU, BALLS CREEK, CATAWBA
- **Notes:** Community planning areas — **not** parcel-level future land-use polygons. PDF SAP maps also published under county Planning.

### 9. Cities / City ETJs — jurisdiction polygons

- **Cities:** https://arcgis2.catawbacountync.gov/arcgis/rest/services/catawba/Basemap/FeatureServer/5 — `CITY_NAME`
- **ETJs:** FeatureServer/6 (also Real_Estate_Basemap/12–13)
- **Distinct cities:** BROOKFORD, CATAWBA, CLAREMONT, CONOVER, HICKORY, LONG VIEW, MAIDEN, NEWTON

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| Unincorporated Catawba | County Zoning /59 or Zoning_All District='County' | 1714 / 1719 | County | SAP only | Unincorporated UDO |
| Hickory | **Hickory_Zoning** (prefer) or Zoning_All District='Hickory' | 1740 / 1736 | **Yes** — arcgis.hickorync.gov | **Yes** — Hickory FLU (142) | Also overlays MapServer |
| Newton | Zoning_All District='Newton' | 796 | No | No | Defers to county |
| Conover | Zoning_All District='Conover' | 621 | No | No | Defers to county |
| Claremont | Zoning_All District='Claremont' | 161 | No | No | |
| Maiden | Zoning_All District='Maiden' | 334 | No | No | Also extends into Lincoln County |
| Catawba (town) | Zoning_All District='Catawba' | 126 | No | No | |
| Brookford | Zoning_All District='Brookford' | 69 | No | No | |
| Long View | Zoning_All District='Long View' | 276 | No | No | District spelling has space |

## Gaps / caveats

- No public city-native ArcGIS for Newton, Conover, Claremont, Maiden, Town of Catawba, Brookford, or Long View — use county `Zoning_All` with `District` filter
- County FLU outside Hickory is SAP districts + parcel `Small_Area_Plan` text / PDF policy maps — not full FLU FeatureServer
- energov `Sale_Amount` / value fields are currency strings; Sale Validity only on CSV warehouse
- Real_Estate geometry parcels need CAMA join; MaxRecordCount 1000 on energov FS
- `LEO_HideName='Y'` redacts some owners; do not collect phones/emails
- Utilities and AADT intentionally excluded from this card

## License / attribution

Catawba County Geospatial Information Services (GIS). County disclaimer: data prepared from county systems; independent verification recommended; county not liable for damages from use. Commercial resale subject to **NCGS 132-10**. Attribute Catawba County GIS (and City of Hickory GIS where used).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 11
- Live `returnCountOnly` + sample attribute queries against energov Parcels, Real_Estate Basemap, Zoning_All (per District), County Zoning, Hickory Zoning/FLU, SAP, Cities, NC OneMap `cntyfips='035'`, and cc_owner_all.

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='CATAWBA'`, field `AADT_2022` (string) — **800 stations live**, 49 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CATAWBA%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CATAWBA%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Catawba'`, `AADT_2025` (int) — 793 stations; 772 with 2025, 0 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://arcgis2.catawbacountync.gov/arcgis/rest/services/energov/energov_permit_ctr/FeatureServer/0` — total 94864, 5–150 ac 8502 (`Caculated_Acreage>=5 AND Caculated_Acreage<=150`).
- Non-zero county: `Land_Value` 91012, `Total_Buildings_Value` 69875, `Total_Value` 91271; in 5–150: `Total_Value` 8387. **Status: ok.**
- Tax values are STRING currency (e.g. '$177,700'; Total_Value may carry suffix '/ Use Total Value: $31,000' for PUV parcels) — strip $ and commas, take first number. CSV fallback: https://gis.catawbacountync.gov/DataWarehouse/csv/catco_pa.csv

### 3. Sale history
- Price `Sale_Amount`>0 48177 (5–150: 3098); date non-null `Sale_Date` 48177. **Status: ok.**
- Sale_Amount STRING currency ('$203,500'); Sale_Date STRING MM/DD/YY — parse 2-digit year (<=26 → 20xx). Last sale only; no multi-transfer history on REST.

### 4. Owner entity
- Owner fields: `Name`, `Name2`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 2127** (of 8502 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: `https://gis.catawbacountync.gov/parcel/?pinc={PIN}`
- Tested `https://gis.catawbacountync.gov/parcel/?pinc=279006488235` → **200**. HTTP 200; JS app (Catawba GIS Real Estate Maps) renders parcel client-side, so parcel content not server-verifiable. Alt report: https://gis.catawbacountync.gov/nomap/?pinc={PIN} (200). Tax bill: https://taxbill.catawbacountync.gov/ITSPublicCT/RealEstateSearch

### 6. Jurisdiction GIS viewer
- `https://gis.catawbacountync.gov/parcel/` → **200**. Catawba County GIS Real Estate Maps

### Pass2 gaps
- AADT_2022 blank at 751 of 800 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- No multi-transfer sale history on primary layer (last sale only)
