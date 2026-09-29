# Alexander County, NC — GIS County Card

## Summary

Alexander County (Hickory–Lenoir–Morganton MSA, FIPS **37003**, slug **alexander**, `cntyfips='003'`) publishes a strong **public** ArcGIS REST stack at **`maps.alexandercountync.gov`**. **Wire-first parcels (TRANCHE-3):** **Website_map/MapServer/26 Parcels** (mirrors Parcels/MapServer/0) — ~**26,977** polys with owner, mailing, situs (`PHYSICAL_ADDRESS`), `CALCULATED_ACREAGE`/`DEEDED_ACREAGE`, full tax split (`MARKET_VALUE`/`ASSESED_VALUE`/`LAND_VALUE`/`STRUCTURE_VALUE`/`OTHER_VALUE`), deed refs, and **`DATE_SOLD`/`SALES_PRICE`**. ~**7,303** with acres 5–150 (~**1,144** with `SALES_PRICE>0` in range). **Zoning is cities-first:** only incorporated town is **Taylorsville** — route via City Limits (`TYPE='CITYLIMIT'`) + **Downtown Overlay** / **Business Corridor Overlay** / Historic Overlay on top of countywide parcel **`ProposedZoning`**. CDPs Bethlehem / Hiddenite / Stony Point are unincorporated (county zoning). **FLU:** parcel **`FLU_Classification`** (USA/RTA/RAA/IND) preferred; Overlay/30 Future Land Use `MERGE_SRC` present but inventory skewed. **PA deep-link:** `https://maps.alexandercountync.gov/PRC/{PARCELID}.html` (7-digit zero-pad). **Jurisdiction GIS:** https://maps.alexandercountync.gov/maps/ (`?pin={PARCELID}`). **NC OneMap** `cntyfips='003'` geometry/owner/tax fallback (no sale price; saledate empty). Markets: **[Hickory]**.

## Portals

- **Jurisdiction GIS (Map Viewer)** — https://maps.alexandercountync.gov/maps/
- **Viewer deep-link** — `https://maps.alexandercountync.gov/maps/?pin={PARCELID}` (also `default.htm?pin=`)
- **County ArcGIS REST** — https://maps.alexandercountync.gov/arcgis/rest/services
- **GIS department** — https://alexandercountync.gov/departments/gis/
- **Property Record Card (PA deep-link, preferred)** — `https://maps.alexandercountync.gov/PRC/{PARCELID}.html`
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/alexander/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/alexander/parcel-detail/{PIN}`
- **SmartGov public parcels** — https://co-alexander-nc.smartgovcommunity.com/Parcels/ParcelHome
- **Planning & Development** — https://alexandercountync.gov/departments/planning/ (Comp Plan 2045 / FLU documented; site may 403 from some egress)
- **Town of Taylorsville** — https://www.taylorsvillenc.com/ (Planning & Development; defers zoning map to county GIS)
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='003'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` (10-digit); `PARCELID` (7-digit zero-pad); `PROPERTY`; `ACCOUNT` | Prefer **PARCELID** for PRC/viewer; **PIN** for OneMap/NCPTS |
| polygons | Yes | Website_map/26; Parcels/0; OneMap | CRS **102719 / 2264** |
| acreage | Yes | `CALCULATED_ACREAGE`; `DEEDED_ACREAGE`; OneMap `gisacres` | ~**7,303** in 5–150 |
| ownerName | Yes | `OWNER_NAME1`+`2`+`3`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `MAILING_ADDRESS`,`MAILING_CITY`,`MAILING_STATE`,`MAILING_ZIP_CODE` | |
| situs address | Yes | `PHYSICAL_ADDRESS` (+ house/street parts); OneMap `siteadd` | |
| lastSale date/price | Yes | `DATE_SOLD`,`SALES_PRICE`; year Sales layers | DATE_SOLD = YYYYMMDD double; ~**6,411** with price>0 |
| tax values | Yes | `MARKET_VALUE`,`ASSESED_VALUE`,`LAND_VALUE`,`STRUCTURE_VALUE`,`OTHER_VALUE` | Note **ASSESED** spelling |
| zoning | Yes (cities-first) | `ProposedZoning` + Taylorsville overlays | R1/R1-CD/R2/R2R/R3/RC/CC/MU/OI/WR/I |
| flu | Yes (prefer parcel attr) | `FLU_Classification`; Overlay/30 `MERGE_SRC` | USA/RTA/RAA/IND; Overlay inventory skewed |
| appraiser / viewer link | Yes | PRC `{PARCELID}`; viewer `?pin=`; NCPTS `{PIN}` | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. Website_map Parcels — parcels + ownership + tax + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales
- **REST URL:** https://maps.alexandercountync.gov/arcgis/rest/services/Website_map/MapServer/26
- **Mirror:** https://maps.alexandercountync.gov/arcgis/rest/services/Parcels/MapServer/0
- **Layer name / id:** Parcels / 26
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PARCELID` → parcelIdAlt (PA / viewer key; zero-padded 7-digit)
  - `PIN` → parcelId (10-digit; OneMap/NCPTS)
  - `PROPERTY` → parcelIdInt
  - `ACCOUNT` → parcelIdAccount
  - `CALCULATED_ACREAGE`, `DEEDED_ACREAGE` → acreage
  - `OWNER_NAME1`–`3` → ownerName
  - `MAILING_ADDRESS`,`MAILING_CITY`,`MAILING_STATE`,`MAILING_ZIP_CODE` → mailing
  - `PHYSICAL_ADDRESS` → situsAddress
  - `DATE_SOLD`, `SALES_PRICE` → lastSale
  - `MARKET_VALUE`, `ASSESED_VALUE`, `LAND_VALUE`, `STRUCTURE_VALUE`, `OTHER_VALUE` → tax
  - `DEED_BOOK`, `DEED_PAGE`, `DEED_YEAR` → deed
- **WKID / CRS:** 102719 (latest 2264)
- **Verified:** yes — count **26,977**; `CALCULATED_ACREAGE BETWEEN 5 AND 150` → **7,303**; `SALES_PRICE>0` → **6,411** (in-range **1,144**); `MARKET_VALUE>0` → **25,420**; sample PARCELID `0000076` / PIN `3787978905` = V&J ENTERPRISES LLC (centroid ≈ **-81.06, 35.87** Alexander)
- **Notes:** Best single county layer. MaxRecordCount **1000** — paginate. Auth **none**.

### 2. Tax Map and Lot — CAMA twin

- **REST URL:** https://maps.alexandercountync.gov/arcgis/rest/services/Website_map/MapServer/19
- **Mirror:** Zoning_Website_map/MapServer/4
- **Verified:** count **25,405**
- **Notes:** Same CAMA family with `#` field names (`PIN_#`, `PARCEL#`). Prefer Parcels/26.

### 3. BoundaryLayers — year Sales by Parcel

- **REST root:** https://maps.alexandercountync.gov/arcgis/rest/services/BoundaryLayers/MapServer
- **Layers:** 0=2026 (**70**), 1=2025 (**491**), 2=2024 (**450**), 3=2023 (**447**)
- **Fields:** `PIN`,`PARCEL`,`DATE_SOLD`,`SALES_PRIC` (truncated), values
- **Also:** Website_map/28 = 2022 Sales by Parcel (**607**)
- **Notes:** Use for recent comps; parcel layer already carries last sale.

### 4. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='003'`
- **Key fields:** `parno`↔`PIN`, `altparno`, `ownname`, `mailadd`…, `siteadd`, `gisacres`, `saledatetx`, `parval`/`landval`/`improvval`
- **Verified:** yes — count **25,265**; `gisacres` 5–150 → **5,990**; `saledate IS NOT NULL` → **0**
- **Notes:** No sale price. Prefer county acreage/CAMA. Join verified `parno='3787978905'` ↔ county PIN.

### 5. Website_map Zoning — ProposedZoning + FLU_Classification (cities-first base)

- **REST URL:** https://maps.alexandercountync.gov/arcgis/rest/services/Website_map/MapServer/72
- **Mirrors:** Zoning_Website_map/MapServer/5 County Zoning; Overlay/MapServer/27
- **Geometry:** Polygon (parcel-based)
- **Fields:** `ProposedZoning`, `FLU_Classification` (+ full CAMA)
- **Verified ProposedZoning counts (2026-09-24):** R2R **8103**, R2 **6082**, R1 **5375**, R3 **3020**, WR **1030**, MU **607**, OI **502**, I **194**, RC **78**, CC **78**, R1-CD **4**, null **1** (total **25,074**)
- **Verified FLU_Classification:** RTA **10917**, RAA **7032**, USA **6854**, IND **48**, `0` **20**, null **203**
- **Notes:** Inside Taylorsville limits, apply overlays below on top of `ProposedZoning`.

### 6. Taylorsville overlays (city-first)

| Layer | REST | Count | Notes |
|-------|------|------:|-------|
| Downtown Overlay | Website_map/73 (Overlay/25) | **97** | City-first |
| Business Corridor Overlay | Website_map/74 (Overlay/24) | **112** | City-first |
| Historic Overlay District | Overlay/26 | **1** | Thin |

### 7. Overlay Future Land Use — county FLU polygons (partial)

- **REST URL:** https://maps.alexandercountync.gov/arcgis/rest/services/Overlay/MapServer/30
- **Field:** `MERGE_SRC`
- **Verified:** total **1,064** — Conservation **1029**, Community Service Center **17**, Industrial **11**, Urban Services Area **4**, Rural Transition Area **2**, Rural Agricultural Area **1**
- **Notes:** Planning site directs users here; polygon inventory skewed — **prefer parcel `FLU_Classification`**. Comp Plan 2045 PDF also published under Planning.

### 8. City Limits — Taylorsville + ETJ

- **REST URL:** https://maps.alexandercountync.gov/arcgis/rest/services/Website_map/MapServer/29
- **Fields:** `CITY_NAME`, `TYPE`, `ACRES`
- **Verified:** **39** polys; `TYPE='CITYLIMIT'` **34**; `TYPE='ETJ'` **5**; `CITY_NAME` = **TAYLORSVILLE** only

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| Unincorporated Alexander | ProposedZoning on Zoning/72 | 25074 | County | Parcel FLU_Classification + Overlay/30 | Includes CDPs |
| **Taylorsville** | ProposedZoning + Downtown/Biz/Historic overlays; filter City Limits | overlays 97 / 112 / 1 | No (defers to county) | Parcel FLU inside USA | County seat; only incorporated town |
| Bethlehem | County ProposedZoning | — | No | Parcel FLU | CDP |
| Hiddenite | County ProposedZoning | — | No | Parcel FLU | CDP |
| Stony Point | County ProposedZoning | — | No | Parcel FLU | CDP |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| Property Record Card HTML (preferred) | `https://maps.alexandercountync.gov/PRC/{PARCELID}.html` |
| Encoding | `PARCELID` = zero-padded 7 digits (e.g. PROPERTY `76` → `0000076`) |
| Viewer deep-link | `https://maps.alexandercountync.gov/maps/?pin={PARCELID}` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/alexander/parcel-detail/{PIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/alexander/parcel-search |
| Jurisdiction GIS | https://maps.alexandercountync.gov/maps/ |

Viewer `assets/Alexander/SearchConfig.js` wires Tax Card → `PRC/${PARCELID}.html`. Verified PRC for `0000076` returns V&J ENTERPRISES LLC with SALES PRICE **78,000**.

## Gaps / caveats

- No independent Taylorsville (or CDP) ArcGIS zoning FeatureServer — county `ProposedZoning` + overlays only
- Overlay/30 Future Land Use `MERGE_SRC` inventory skewed (~1029/1064 Conservation) — prefer parcel `FLU_Classification`
- OneMap `saledate` empty for Alexander; `saledatetx` text only; no sale price on OneMap
- County website HTML (planning/GIS dept pages) often **403** from datacenter egress — REST + maps viewer + PRC verified live
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Alexander County Geographic Information Systems (GIS). Map data compiled from recorded deeds/plats/public records; consult primary sources; not survey quality. Commercial resale subject to **NCGS 132-10**. Attribute Alexander County GIS (and Town of Taylorsville where overlays apply).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 12
- **tranche:** 3 (tax/sale/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- Live `returnCountOnly` + sample attribute queries against Website_map Parcels/Tax Map/Zoning/Overlays/City Limits, BoundaryLayers sales, Overlay FLU, NC OneMap `cntyfips='003'`; PRC HTML cross-check; SearchConfig.js deep-link wiring; geo-check centroid in Alexander.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://maps.alexandercountync.gov/arcgis/rest/services/Website_map/MapServer/26 · id `PIN` · live count **26,980** · 5–150 ac **7,305** (`CALCULATED_ACREAGE >= 5 AND CALCULATED_ACREAGE <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='ALEXANDER'` gives **291** stations (146 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27ALEXANDER%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Alexander'` gives **286** stations (161 with AADT_2025, 169 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Alexander%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `MARKET_VALUE` non-zero **25,423**, `ASSESED_VALUE` non-zero **25,423**
- **Sale history (ok):** price `SALES_PRICE` >0 **6,412**; date `DATE_SOLD` non-null **25,419**
- **Owner entity:** fields `OWNER_NAME1`, `OWNER_NAME2`, `OWNER_NAME3`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **406** (all parcels: 1,686), using the SQL approximation on `OWNER_NAME1`.
- **PA deep link:** `https://maps.alexandercountync.gov/PRC/{PARCELID}.html`. Tested `0000953` → HTTP **200** (text/html), content verified: True. Static PRC HTML; id and owner verified.
- **Jurisdiction GIS viewer:** https://maps.alexandercountync.gov/maps/ → HTTP **200** (Alexander County, North Carolina GIS)
- **sampleQueryForm:** resultRecordCount is rejected unless orderByFields is set (the layer has no OID). Use &orderByFields=PIN&resultRecordCount=N, or an unpaged where query (capped at 1000 rows, exceededTransferLimit=true). Count queries work normally.
- **Pass 2 gaps:** none
