# Yancey County, NC — GIS County Card

## Summary

Yancey County (Asheville shed, FIPS **37199**, slug **yancey**, `cntyfips='199'`) publishes a public ArcGIS REST stack at **`gis.yanceycountync.org`**. **Wire-first parcels (TRANCHE-3):** **OperationalLayers2025/MapServer/0 TaxParcels** — ~**17,394** polys with 15-digit `PIN`, `OWNER`/`OWNER_NAME`, mailing, situs (`PROPERTY_LOCATION`/`STREET_NUMBER`/`STREET_NAME`), `CALCULATED_ACREAGE`/`ASSESSED_ACREAGE`, full tax (`CURRENT_LAND_VALUE`/`CURRENT_BLDG_VALUE`/`CURRENT_TOTAL_VALUE`), deed refs (`DEED_DATE`/`DEED_BOOK`/`DEED_PAGE`), and deed-excise `STAMPS` (sale-price proxy; no dedicated `SALE_PRICE` field). ~**4,555** with calculated acres 5–150 (~**1,576** with `STAMPS>0` in range). **Zoning is cities-first:** **Town of Burnsville** only via **Reference/MapServer/0 Zoning** (10 district polys: C-1/C-2/C-3/I-1/R-10). County site directs zoning questions to Burnsville Public Works — **unincorporated Yancey has no countywide zoning REST**. **FLU:** Burnsville Comprehensive Land Use Plan 2021 PDF (includes Future Land Use Map) — no public FLU FeatureServer. **PA deep-link:** `https://yancey.ias-clt.com/parcel.detail.php?id={PIN}{Card}` (IAS id = 15-digit PIN + 2-digit card, typically `01`; vacant sometimes `00`). **Jurisdiction GIS:** https://gis.yanceycountync.org/maps/. **NC OneMap** `cntyfips='199'` geometry/owner fallback (parval/saledate empty). Markets: **[Asheville]**. Only incorporated municipality: **Burnsville**.

## Portals

- **Jurisdiction GIS (Map Viewer)** — https://gis.yanceycountync.org/maps/
- **Viewer deep-link** — `https://gis.yanceycountync.org/maps/?pin={PIN}` (SPA accepts query; pin search on TaxParcels)
- **County ArcGIS REST** — https://gis.yanceycountync.org/server/rest/services
- **OperationalLayers2025 TaxParcels (PRIMARY)** — https://gis.yanceycountync.org/server/rest/services/OperationalLayers2025/MapServer/0
- **OperationalLayers TaxParcels (legacy twin)** — https://gis.yanceycountync.org/server/rest/services/OperationalLayers/MapServer/6
- **Reference Zoning (Burnsville)** — https://gis.yanceycountync.org/server/rest/services/Reference/MapServer/0
- **PA / Assessor (IAS-CLT Tyler)** — https://yancey.ias-clt.com/parcel.list.php
- **PA deep-link** — `https://yancey.ias-clt.com/parcel.detail.php?id={PIN}{Card}` (e.g. `07070001934000001`)
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/yancey/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/yancey/parcel-detail/{PIN}`
- **Tax pay portal** — https://secure.webtaxpay.com/?county=yancey&state=NC (also http://www.yancey.webtaxpay.com/)
- **County GIS page** — https://www.yanceycountync.gov/184/GIS
- **Town of Burnsville** — https://townofburnsville.org/
- **Burnsville Comp Land Use Plan 2021 (FLU PDF)** — https://townofburnsville.org/wp-content/uploads/Burnsville-Comprehensive-Land-Use-Plan-Draft.pdf
- **Burnsville Zoning Map 2022 (page)** — https://townofburnsville.org/burnsville-zoning-map-2022/
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='199'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` (15-digit); OneMap `parno` | Prefer **PIN** for IAS/NCPTS/viewer; IAS detail appends 2-digit **Card** |
| polygons | Yes | Op2025 TaxParcels/0; Op Layers/6; OneMap | CRS **102719 / 2264** |
| acreage | Yes | `CALCULATED_ACREAGE`; `ASSESSED_ACREAGE`; OneMap `gisacres` | ~**4,555** calc 5–150 |
| ownerName | Yes | `OWNER_NAME` (prefer); `OWNER`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `MAILING_ADDRESS1`/`MAILING_ADDRESS2`/`CITY`/`STATE_OR_COUNTRY`/`ZIP_CODE` | |
| situs address | Yes | `PROPERTY_LOCATION`; `STREET_NUMBER`+`STREET_NAME`; OneMap `siteadd` | |
| lastSale date/price | Partial | `DEED_DATE`; `STAMPS` (excise proxy); IAS Sales History Price | No `SALE_PRICE` REST field |
| tax values | Yes | `CURRENT_TOTAL_VALUE`/`CURRENT_LAND_VALUE`/`CURRENT_BLDG_VALUE`; `AG_LAND_VALUE` | |
| zoning | Yes (cities-first) | Reference Zoning `Zoning` (Burnsville) | Unincorp unzoned on REST |
| flu | Gap (PDF) | Burnsville CLUP 2021 PDF | No public FLU FeatureServer |
| appraiser / viewer link | Yes | IAS `{PIN}{Card}`; viewer `?pin=`; NCPTS `{PIN}` | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. OperationalLayers2025 TaxParcels — parcels + ownership + tax + deed (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (partial)
- **REST URL:** https://gis.yanceycountync.org/server/rest/services/OperationalLayers2025/MapServer/0
- **Layer name / id:** TaxParcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (15-digit; PA/NCPTS/viewer key)
  - `CALCULATED_ACREAGE`, `ASSESSED_ACREAGE` → acreage
  - `OWNER_NAME` → ownerName (prefer over `OWNER`; matches OneMap `ownname`)
  - `OWNER`, `GRANTOR` → ownerName / other
  - `MAILING_ADDRESS1`/`MAILING_ADDRESS2`, `CITY`, `STATE_OR_COUNTRY`, `ZIP_CODE` → mailing
  - `PROPERTY_LOCATION`, `STREET_NUMBER`, `STREET_NAME` → situsAddress
  - `DEED_DATE`, `TRANSACTION_DATE`, `DEED_BOOK`, `DEED_PAGE`, `STAMPS` → lastSale (date + excise proxy)
  - `CURRENT_TOTAL_VALUE`, `CURRENT_LAND_VALUE`, `CURRENT_BLDG_VALUE`, `AG_LAND_VALUE` → tax
  - `CLASS`, `STATE_CLAS`, `NEIGHBORHOOD`, `TOWNSHIP`, `FIRE_DISTRICT_CODE`/`FIRE_DISRICT_NAME` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **17,394**; `CALCULATED_ACREAGE` 5–150 → **4,555**; `ASSESSED_ACREAGE` 5–150 → **4,723**; `CURRENT_TOTAL_VALUE>0` → **17,216**; `CAST(STAMPS AS FLOAT)>0` → **7,581** (in-range **1,576**); `OWNER_NAME` non-empty → **17,275**; sample PIN `070700019340000` = OWNER_NAME **MELTON, MICHAEL K & DALE W**, acres calc **8.93**, tax **465,500**, DEED_DATE **2020-08-03**, STAMPS **21.00** (matches 1996 $10,500 IAS sale — stamps lag latest deed), centroid ≈ **-82.37, 35.82** (Yancey)
- **Notes:** Best single county layer (`CALCULATED_ACREAGE` present). MaxRecordCount **2000**. Auth **none**. NC excise ≈ **$1 per $500** → approximate consideration ≈ `float(STAMPS)*500` when stamps reflect that deed; **not always synced** with latest `DEED_DATE` — prefer IAS Sales History for reliable last sale **price**.

### 2. OperationalLayers TaxParcels — legacy twin

- **REST URL:** https://gis.yanceycountync.org/server/rest/services/OperationalLayers/MapServer/6
- **Verified:** count **17,306**
- **Notes:** Same CAMA family; **lacks `CALCULATED_ACREAGE`** — prefer Op2025. QueryLayers/2 is another TaxParcels mirror without calc acres.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='199'`
- **Key fields:** `parno`↔`PIN`, `ownname`, `mailadd`…, `siteadd`, `gisacres`, `parval`/`landval`/`improvval`, `saledatetx`
- **Verified:** yes — count **17,378**; `gisacres` 5–150 → **4,552**; `ownname` non-empty → **17,378**; `parval>0` → **0**; `saledate IS NOT NULL` → **0**
- **Notes:** No sale price / empty tax values for Yancey. Prefer county TaxParcels for tax + deed. Join verified `parno='070700019340000'` ↔ county PIN / OWNER_NAME MELTON.

### 4. Reference Zoning — cities-first Burnsville

- **REST URL:** https://gis.yanceycountync.org/server/rest/services/Reference/MapServer/0
- **Layer name / id:** Zoning / 0
- **Key fields:** `Zoning` → zoning
- **Verified:** count **10** district polys — codes **C-1, C-2, C-3, I-1, R-10**; centroids ≈ **-82.28–82.32, 35.91–35.92** (Town of Burnsville)
- **Notes:** County GIS page: zoning questions → Town of Burnsville Public Works. Unincorporated county has **no** zoning FeatureServer.

### 5. Reference Townships — Burnsville city-limits routing

- **REST URL:** https://gis.yanceycountync.org/server/rest/services/Reference/MapServer/5
- **Verified:** **Town of Burnsville** (`TOWN_CODE=12`) — **1** polygon (town limits); plus Burnsville township + Ramseytown/Egypt/Cane River/… civil townships
- **Notes:** Use `TOWNSHIP_N='Town of Burnsville'` for incorporated membership routing when joining zoning.

## Municipalities (cities-first)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| **Burnsville** | **Reference/Zoning/0** `Zoning` | 10 districts | townofburnsville.org (map page + CLUP PDF) | No (PDF) | County seat; only incorporated town; Townships/5 limits poly |
| Unincorporated Yancey | No countywide zoning REST | — | County | No | Zoning directed to Burnsville for town; county ordinance/flood/watershed only |

CDPs (Micaville, Celo, Green Mountain, Swiss, etc.) are unincorporated — no separate zoning REST.

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| IAS Property Detail (preferred) | `https://yancey.ias-clt.com/parcel.detail.php?id={PIN}{Card}` |
| Encoding | `PIN` = 15-digit string; `Card` = 2-digit card (`01` typical improved; `00` some vacant; `02`+ multi-card) |
| Example | `https://yancey.ias-clt.com/parcel.detail.php?id=07070001934000001` → MELTON / 1951 OGLE MEADOWS RD / Sales History price **56,000** (08/03/2020) |
| IAS search | https://yancey.ias-clt.com/parcel.list.php (`parcel.search[p_parid]={PIN}`) |
| Viewer deep-link | `https://gis.yanceycountync.org/maps/?pin={PIN}` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/yancey/parcel-detail/{PIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/yancey/parcel-search |
| Jurisdiction GIS | https://gis.yanceycountync.org/maps/ |

Verified: IAS list for PIN `070700019340000` → detail id `…00001`; PIN `070600897684000` → `…00000`. Sales History exposes Book/Page/Sale Date/**Price**/Validity/Sale Type. SSL on ias-clt.com may need modern CA bundle from some egress.

## Gaps / caveats

- **No dedicated SALE_PRICE on REST** — use IAS Sales History for reliable price; `STAMPS` is NC deed-excise proxy (≈ consideration/500) and can lag latest `DEED_DATE`
- **FLU REST gap** — Burnsville CLUP 2021 PDF only (Future Land Use Map inside PDF); no county FLU FeatureServer; county CTP is transportation not FLU
- **Unincorporated zoning REST gap** — only Burnsville Zoning/0; county does not publish countywide zoning polygons
- OneMap `parval`/`saledate` empty for `cntyfips='199'`; **no sale price** on OneMap — use county TaxParcels + IAS
- OperationalLayers/6 lacks `CALCULATED_ACREAGE` — prefer Op2025/0
- IAS PA id requires **PIN + Card** suffix (not bare PIN); wrong card → "Unable to select item in database"
- Burnsville zoning-map page / CLUP PDF may 202/block from some datacenter egress — Reference Zoning REST + town PDF URL documented
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Yancey County GIS / Tax Administration; Town of Burnsville; Tyler CLT / IAS (assessor DB); NC OneMap where used. Map data from recorded deeds/plats/public records; consult primary sources; not survey quality. Commercial resale subject to **NCGS 132-10**. Attribute Yancey County GIS (and Town of Burnsville where zoning applies).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 6
- **tranche:** 3 (tax/sale/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- Live `returnCountOnly` + sample attribute queries against Op2025 TaxParcels, OperationalLayers/6, Reference Zoning + Townships, NC OneMap `cntyfips='199'`; IAS list/detail `{PIN}{Card}` + Sales History cross-check; OneMap `parno` join; geo-check centroids in Yancey / Burnsville.


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://gis.yanceycountync.org/server/rest/services/OperationalLayers2025/MapServer/0 polygons load (sample centroid [-82.2116, 35.9066]); `PIN` filled on 17,383 of 17,393; `CALCULATED_ACREAGE` 5–150 ac **4,555**.
- **Attribute layer for Pass 2:** https://gis.yanceycountync.org/server/rest/services/OperationalLayers2025/MapServer/0 · id `PIN` · live count **17,393** · 5–150 ac **4,555** (`CALCULATED_ACREAGE >= 5 AND CALCULATED_ACREAGE <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='YANCEY'` gives **152** stations (103 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27YANCEY%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Yancey'` gives **148** stations (100 with AADT_2025, 101 with AADT_2024, 146 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Yancey%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `CURRENT_TOTAL_VALUE` non-zero **17,226**, `CURRENT_LAND_VALUE` non-zero **17,207**
- **Sale history (ok):** price `STAMPS` >0 **7,586**; date `DEED_DATE` non-null **16,949**, `TRANSACTION_DATE` non-null **17,351**. STAMPS is NC excise stamps (string): price ≈ CAST(STAMPS AS FLOAT) × 500. Actual Sales History price is on the IAS-CLT parcel page.
- **Owner entity:** field `OWNER_NAME`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **605** (all parcels: 2,297), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://yancey.ias-clt.com/parcel.detail.php?id={PIN}{Card}`. Tested `070800148426000` (https://yancey.ias-clt.com/parcel.detail.php?id=07080014842600000) → HTTP **200** (text/html; charset=UTF-8), content verified: True. IAS id = 15-digit PIN + 2-digit card. Card 01 returned "Unable to select item" for this vacant parcel; card 00 returned the owner. LSB: try 01 then 00.
- **Jurisdiction GIS viewer:** https://gis.yanceycountync.org/maps/ → HTTP **200** (Avineon Web Map Template)
- **Pass 2 gaps:** none
