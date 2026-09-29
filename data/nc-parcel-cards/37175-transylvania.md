# Transylvania County, NC — GIS County Card

## Summary

Transylvania County (Asheville MSA, FIPS **37175**, slug **transylvania**, `cntyfips='175'`) publishes a strong public ArcGIS stack at `gis.transylvaniacounty.org`. **Wire-first parcels (TRANCHE-3):** **Parcels/FeatureServer/2** — ~**31,781** polys with `PIN`, owner, mailing (`ADDRESS_*`+`CITY`/`STATE`/`ZIP_CODE`), situs hint (`LEGAL_ADDR`), `ACRES`, tax (`LAND_VALUE`/`ASSESSED_V`/`BUILDING_V`/`XFOB_VALUE`), **`SALE_PRICE`/`SALE_DATE`/`SALE_QUALI`**. ~**5,188** with acres 5–150; ~**11,666** with `SALE_PRICE>0`. **Zoning is cities-first:** City of Brevard AGOL **Zoning_Districts/200** (~**129**); county-hosted **Pisgah Forest Zoning** OpenUse (~**329**) + CorridorMixedUse (~**99**) parcel subsets; **Rosman** town limits only (zoning REST gap). **FLU:** Brevard **FutureLandUse_CLUP2030/800** (~**79** character areas). **PA deep-link:** NCPTS `parcel-detail/{PIN}` (preferred; AppraisalCard needs internal `idP`, not PIN). **Jurisdiction GIS:** Tax & Land Records webappviewer + county Hub. Markets: **[Asheville]**.

## Portals

- **Jurisdiction GIS (Tax & Land Records viewer)** — https://gis.transylvaniacounty.org/portal/apps/webappviewer/index.html?id=072e71230d03460898f502e66961d5cf
- **County Hub Site** — https://gis.transylvaniacounty.org/portal/apps/sites/#/transylvania-county-hub-site
- **Hub explore (same app)** — https://gis.transylvaniacounty.org/portal/apps/sites/#/transylvania-county-hub-site/apps/072e71230d03460898f502e66961d5cf/explore
- **County ArcGIS REST** — https://gis.transylvaniacounty.org/server/rest/services
- **Tax Administration** — https://www.transylvaniacounty.org/departments/tax-administration
- **Real Estate Search** — https://tax.transylvaniacounty.org/RealEstateSearch
- **Tax Basic Search** — https://tax.transylvaniacounty.org/
- **Tax Bill Search** — https://tax.transylvaniacounty.org/TaxBillSearch
- **Sales Search** — https://tax.transylvaniacounty.org/SalesSearch
- **NCPTS parcel detail (PA deep-link, preferred)** — `https://lrcpwa.ncptscloud.com/transylvania/parcel-detail/{PIN}`
- **NCPTS search** — https://lrcpwa.ncptscloud.com/transylvania/parcel-search
- **AppraisalCard (internal idP only)** — `https://tax.transylvaniacounty.org/AppraisalCard.aspx?Action=Auto&idP={idP}` — not PIN-wireable from REST
- **City of Brevard Official Zoning Map (ViewPro)** — https://map.viewprogis.com/ecp/brevard-nc
- **Brevard Official Zoning Map page** — https://www.cityofbrevard.com/479/Official-Zoning-Map
- **Building Brevard 2030 CLUP** — https://www.cityofbrevard.com/473/2030-Comprehensive-Land-Use-Plan
- **Brevard CLUP PDF** — https://www.cityofbrevard.com/DocumentCenter/View/4616/Brevard-Adopted-CLUP-Reduced
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='175'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`; OneMap `parno`; `ACCOUNT_NO` alt | e.g. `7499-35-0631-000` ↔ OneMap `parno` |
| polygons | Yes | Parcels FS/2; OneMap | CRS **102719 / 2264** |
| acreage | Yes | `ACRES`; OneMap `gisacres` | County ~**5,188** in 5–150 |
| ownerName | Yes | `OWNER_NAME`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `ADDRESS_1`–`3`,`CITY`,`STATE`,`ZIP_CODE`; OneMap `mailadd` | |
| situs address | Partial | `LEGAL_ADDR`; Addresses `FULLADDR` via `PARCELNUM`; OneMap `siteadd` | LEGAL_ADDR often lot/road desc; Addresses ~28.1k points |
| lastSale date/price | Yes | `SALE_DATE`,`SALE_PRICE`,`SALE_QUALI`,`SALE_INST` | ~**11,666** SALE_PRICE>0; date as YYYYMM text |
| tax values | Yes | `ASSESSED_V`,`LAND_VALUE`,`BUILDING_V`,`XFOB_VALUE`; OneMap `parval`/`landval`/`improvval` | ASSESSED_V ≈ total (land+bldg) |
| zoning | Yes (cities-first) | Brevard `District_Code`; Pisgah zone layers; parcel `ZONING` attr sparse | Unincorp mostly unzoned; Rosman REST gap |
| flu | Yes (Brevard) | FLU `FLU` character areas | County / Rosman no FLU REST |
| appraiser / viewer link | Yes | NCPTS `{PIN}`; RealEstateSearch; GIS viewer | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. Parcels FeatureServer — parcels + ownership + tax + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | situs-hint
- **REST URL:** https://gis.transylvaniacounty.org/server/rest/services/Parcels/FeatureServer/2
- **MapServer mirror:** https://gis.transylvaniacounty.org/server/rest/services/Parcels/MapServer/2
- **Layer name / id:** Parcels / 2
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (e.g. `7499-35-0631-000`)
  - `ACCOUNT_NO` → parcelIdAccount
  - `ACRES` → acreage
  - `OWNER_NAME` → ownerName
  - `ADDRESS_1`,`ADDRESS_2`,`ADDRESS_3`,`CITY`,`STATE`,`ZIP_CODE` → mailing
  - `LEGAL_ADDR` → situs / legal description
  - `SALE_DATE`,`SALE_PRICE`,`SALE_QUALI`,`SALE_INST`,`SALE_IMP` → lastSale
  - `LAND_VALUE`,`ASSESSED_V`,`BUILDING_V`,`XFOB_VALUE` → tax
  - `ZONING` → zoning attr (sparse; old R1/C1… codes)
  - `DEED_BK`,`PAGE`,`USE_MODEL`,`TWSP`,`TAX_DISTRI`,`FIREDIST` → other
- **WKID / CRS:** 102719 (latest 2264)
- **Verified:** yes — count **31,781**; `ACRES BETWEEN 5 AND 150` → **5,188**; `SALE_PRICE>0` → **11,666**; `ASSESSED_V>0` → **31,648**; `OWNER_NAME IS NOT NULL` → **31,664**; `PIN` nonblank → **31,770**; `ZONING IS NOT NULL` → **3,801**. Sample `PIN=7499-35-0631-000` Hood / sale $2,530,000 / 11.236 ac / centroid ≈ **-83.03, 35.05** (Transylvania / Lake Jocassee); join OneMap `parno` OK
- **Notes:** PRIMARY wire-first. MaxRecordCount **2000** — paginate. Auth **none**. `Report_URL` present but null on all queried rows. Empty/stub polys with blank PIN exist (filter `PIN <> ' '`).

### 2. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date text)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='175'`
- **Key fields:** `parno`↔`PIN`, `ownname`, `mailadd`, `siteadd`, `gisacres`, `saledate`/`saledatetx`, `parval`/`landval`/`improvval`
- **Verified:** count **31,755**; `gisacres` 5–150 → **5,179**; `parval>0` → **31,555**; `saledatetx IS NOT NULL` → **31,755**; join verified `parno='7489-69-9405-000'`
- **Notes:** No sale **price**. Prefer county `ACRES` / CAMA for values and sale price. MaxRecordCount **5000**.

### 3. City of Brevard Zoning_Districts — municipal districts (cities-first PRIMARY)

- **REST URL:** https://services7.arcgis.com/qkz4LIZAMHN41UKn/ArcGIS/rest/services/Zoning_Districts/FeatureServer/200
- **County MapServer mirror (older labels):** https://gis.transylvaniacounty.org/server/rest/services/Brevard_Zoning_Districts/MapServer/0 — count **95** (`District` text; no District_Code)
- **Fields:** `District`, `District_Code`, `Area_Acres`, `Ordinance`, `Date_Est`, UDO link fields
- **Verified:** total **129**
- **District_Code values:** CD, CMX, DMX, GI, GR4, GR8, IC, NMX, PGX, RMX
- **Viewer:** https://map.viewprogis.com/ecp/brevard-nc
- **Join:** spatial join Zoning → parcels inside Brevard City Limits / ETJ
- **Notes:** Prefer AGOL FS/200 (authoritative encode layer) over county MS/0.

### 4. Pisgah Forest Zoning — unincorporated zoning (county-hosted)

- **OpenUse:** https://gis.transylvaniacounty.org/server/rest/services/Pisgah_Forest_Zoning/FeatureServer/0 — count **329** (parcel polygons in Open Use district; full CAMA attrs incl. PIN)
- **Corridor Mixed Use:** https://gis.transylvaniacounty.org/server/rest/services/Pisgah_Forest_Zoning/FeatureServer/1 — count **99**
- **Notes:** Not traditional district polygons — **parcel subsets** tagged by zone. Use layer membership as zone code (`OpenUse` / `CorridorMixedUse`). MapServer twins exist.

### 5. FutureLandUse_CLUP2030 — Brevard FLU (PRIMARY)

- **REST URL:** https://services7.arcgis.com/qkz4LIZAMHN41UKn/arcgis/rest/services/FutureLandUse_CLUP2030/FeatureServer/800
- **Fields:** `FLU`, `Character_Description`, `ApplicableZoningDistricts`, `Ordinance`, `DateAdopted`
- **Verified:** count **79**
- **FLU values:** Activity Center - Major/Minor; Conservation / Open Space / Parks; Conservation Design / Low Density; Downtown / City Center; Office / Institutional / Special District; Pisgah Gateway; Traditional Neighborhood; Urban Corridor
- **Notes:** Building Brevard 2030 Comp Plan; city-only. County / Rosman **no FLU FeatureServer**.

### 6. Municipal / planning boundaries

- **Brevard City Limits FS/0:** https://gis.transylvaniacounty.org/server/rest/services/Brevard_City_Limits/FeatureServer/0 — count **1**
- **City of Brevard ETJ MS/0:** https://gis.transylvaniacounty.org/server/rest/services/City_of_Brevard_ETJ/MapServer/0 — count **1**
- **Rosman Town Limits FS/0:** https://gis.transylvaniacounty.org/server/rest/services/Rosman_Town_Limits/FeatureServer/0 — count **1**
- **Brevard Planning_Jurisdiction AGOL/130:** https://services7.arcgis.com/qkz4LIZAMHN41UKn/arcgis/rest/services/Planning_Jurisdiction/FeatureServer/130 — count **1**
- **County Boundary:** https://gis.transylvaniacounty.org/server/rest/services/County_Boundary/FeatureServer

### 7. Addresses — situs supplement

- **REST URL:** https://gis.transylvaniacounty.org/server/rest/services/Addresses/FeatureServer/0
- **Fields:** `FULLADDR`, `PARCELNUM`, `POSTALCOM`, `POSTALZIP`, `Inc_Muni`, `RESIDENT` (occupant — not owner of record)
- **Verified:** count **28,147**
- **Notes:** Point situs; `PARCELNUM` ≈ PIN digits without hyphens (join carefully — not always exact). Prefer over `LEGAL_ADDR` for street situs when match found. Do **not** scrape `PHONE`/`AREACODE` (excluded).

### 8. Overlays (optional)

- **Manufactured Home Overlay (Brevard):** county MS + AGOL `Manufactured_Home_Overlay`
- **Voluntary Ag District:** https://gis.transylvaniacounty.org/server/rest/services/Voluntary_Ag_District/FeatureServer
- Parcel `ZONING` attr codes (R1/R2/R3/R1M/C1–C4/I1/I2/OI/F1) — sparse legacy (~3.8k); do not treat as county-wide zoning

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS REST? | FLU REST? | Notes |
|--------------|---------------|------:|:-------------:|:---------:|-------|
| **Brevard** | AGOL Zoning_Districts/200 | 129 | Yes (AGOL + ViewPro) | **Yes** FLU/800 (79) | Seat; CLUP 2030 |
| **Rosman** | *(none)* | — | Limits only | No | **Zoning REST gap** |
| Pisgah Forest (CDP) | Pisgah_Forest_Zoning FS/0+1 | 329+99 | County host | No | Unincorporated district overlays |
| Unincorporated | parcel `ZONING` sparse / none | — | County | No | Mostly **unzoned** on public REST |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| NCPTS detail (preferred) | `https://lrcpwa.ncptscloud.com/transylvania/parcel-detail/{PIN}` |
| Encoding | Use dashed PIN as on parcels (`7499-35-0631-000`) |
| NCPTS search | https://lrcpwa.ncptscloud.com/transylvania/parcel-search |
| Real Estate Search | https://tax.transylvaniacounty.org/RealEstateSearch (search by Parcel Number / Account) |
| AppraisalCard PDF | `https://tax.transylvaniacounty.org/AppraisalCard.aspx?Action=Auto&idP={idP}` — **internal numeric idP**; PIN/ACCOUNT_NO do not wire from REST |
| Tax Bill Search | https://tax.transylvaniacounty.org/TaxBillSearch |
| Jurisdiction GIS | https://gis.transylvaniacounty.org/portal/apps/webappviewer/index.html?id=072e71230d03460898f502e66961d5cf |

Verified NCPTS URL returns 200 SPA shell for `PIN=7499-35-0631-000`. Sample CAMA cross-check: same PIN owner **Hood Brian Jennings &**, sale **202603** @ **$2,530,000**, assessed **$1,658,380**.

## Gaps / caveats

- **Rosman zoning REST gap** — town limits only; no public district FeatureServer
- **Unincorporated zoning** — mostly unzoned; Pisgah Forest is the main county-hosted exception; parcel `ZONING` attr is sparse legacy (~12%)
- **County / Rosman FLU REST gap** — Brevard CLUP2030 only
- **AppraisalCard not PIN-deep-linkable** — requires internal `idP` from tax UI session; use NCPTS `{PIN}` + RealEstateSearch
- **Situs** — `LEGAL_ADDR` is often lot/road description; prefer Addresses/`siteadd` join
- **SALE_DATE** is YYYYMM string (not epoch date)
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Transylvania County GIS / Tax Administration. Maps compiled from recorded deeds/plats/public records; consult primary sources; not survey quality; County disclaims warranties. City of Brevard zoning/FLU — attribute City of Brevard Planning. Commercial resale subject to **NCGS 132-10**.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 12+
- **tranche:** 3 (tax/sale/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- Live `returnCountOnly` + sample attribute/geo queries against Parcels FS/2, Pisgah Forest Zoning, Brevard Zoning/FLU AGOL, Addresses, boundaries, NC OneMap `cntyfips='175'`; NCPTS URL check; centroid geo-check in Transylvania; Hub/webappviewer portals.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://gis.transylvaniacounty.org/server/rest/services/Parcels/FeatureServer/2 · id `PIN` · live count **31,781** · 5–150 ac **5,188** (`ACRES >= 5 AND ACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='TRANSYLVANIA'` gives **225** stations (154 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27TRANSYLVANIA%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Transylvania'` gives **224** stations (122 with AADT_2025, 151 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Transylvania%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `ASSESSED_V` non-zero **31,648**, `LAND_VALUE` non-zero **31,584**
- **Sale history (ok):** price `SALE_PRICE` >0 **11,664**; date `SALE_DATE` non-null **28,115**
- **Owner entity:** fields `OWNER_NAME`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **1,420** (all parcels: 6,024), using the SQL approximation on `OWNER_NAME`.
- **PA deep link:** `https://lrcpwa.ncptscloud.com/transylvania/parcel-detail/{PIN}`. Tested `7489-89-5451-000` → HTTP **200** (text/html), content verified: False. NCPTS SPA shell (200, 496 B, client-rendered): parcel content cannot be checked server-side.
- **Jurisdiction GIS viewer:** https://gis.transylvaniacounty.org/portal/apps/webappviewer/index.html?id=072e71230d03460898f502e66961d5cf → HTTP **200** (ArcGIS Web Application); ArcGIS item access=public
- **Pass 2 gaps:** none
