# Franklin County, NC — GIS County Card

## Summary

Franklin County (Raleigh–Durham footprint, FIPS **37069**, slug **franklin**) publishes public ArcGIS REST through `franklincountymaps.net`. **Wire-first parcels:** **OperationalLayers/MapServer/0 — Web View Parcels**, about **50,019** polygons with owner, mailing, land/building values, last sale, parcel zoning and PIN/PARID. **TaxZoning/42** is the preferred numeric-acreage joined CAMA/deeds stack; **tax/51** supplies numeric `COMPACRES`; **tax/53** is the CAMA table. **Zoning is jurisdiction-routed:** county Planning polygons for unincorporated Franklin, Youngsville AGOL inside Youngsville, and Wake Zoning/25 for the Franklin tip of Wake Forest. No public FLU polygon REST was found. Markets: **Raleigh–Durham**.

## Portals and primary links

- **Franklin County public GIS viewer (jurisdiction homepage):** https://www.franklincountymaps.net/maps/
- **County ArcGIS REST root:** https://www.franklincountymaps.net/arcgis/rest/services
- **Primary parcel REST:** https://www.franklincountymaps.net/arcgis/rest/services/OperationalLayers/MapServer/0
- **NCPTS / property search:** https://lrcpwa.ncptscloud.com/franklin/parcel-search
- **PA deep-link by parcel ID:** `https://lrcpwa.ncptscloud.com/franklin/parcel-detail/{PARID}` (PIN also accepted as an alternate template)
- **NC OneMap parcels fallback:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Youngsville zoning viewer:** https://experience.arcgis.com/experience/cd96cf06c7724708b7349a97be3beed7/

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|---|---|---|---|
| id / parcelId | Yes | `PARID`, `PIN`, `PID`, `ALTID`; OneMap `parno` | Prefer `PARID`; join county PIN/PID and OneMap `parno`. |
| polygons | Yes | OperationalLayers/0 | CRS **WKID 102719 / 2264**. |
| acreage | Yes | TaxZoning/42 `ACRES`; tax/51 `COMPACRES`; OneMap `gisacres` | Web View `ACRES` is a string; do not use numeric BETWEEN there. |
| ownerName | Yes | `OWN1`, `OWN2`; OneMap `ownname` | Public REST fields. |
| mailing address | Yes | `ADDR1`, `ADDR2`, `CITYNAME`, `STATECODE`, `ZIP1` | Structured mailing fields on primary. |
| situs address | Partial / join | primary `ADR*`; Address Points `L_FullAddress` | Join Address Points by `PIN`/`PID`; parcel ADR parts are often empty. |
| lastSale date/price | Yes (last) | `PRICE`, `SALEDT`, `DeedBook`, `DeedPage`; sales/55 qualified subset | Primary parcel last-sale source; annual qualified-sales layers complement it. |
| tax values | Yes | `APRLAND`, `APRBLDG`, `OBYVAL`; OneMap `parval`/`landval`/`improvval` | `TOT22` is null on REST; derive market approximately as land + building. |
| zoning | Yes / split | parcel `ZONING`; county 35; Youngsville 0; Wake 25 | Route by City Limits and local jurisdiction. |
| FLU | Gap | — | No public FLU FeatureServer; county/town plans are PDF-only. |
| appraiser / viewer link | Yes | NCPTS search/detail; Franklin County Maps homepage | Detail template is keyed by `PARID`. |

## Layers (verified from the YAML)

### 1. Web View Parcels — parcels + CAMA (PRIMARY)

- **REST:** https://www.franklincountymaps.net/arcgis/rest/services/OperationalLayers/MapServer/0
- **Layer:** 0 · Polygon · county-wide · **50,019** features · max record count **2,000**
- **Fields:** `PARID`/`PIN`/`ALTID` → parcel id; `ACRES` → acreage; `OWN1`/`OWN2` → owner; `ADDR1`/`ADDR2`/`CITYNAME`/`STATECODE`/`ZIP1` → mailing; `ADRNO`/`ADRDIR`/`ADRSTR`/`ADRSUF` → situs parts; `APRLAND`/`APRBLDG`/`OBYVAL` → tax; `PRICE`/`SALEDT`/`DeedBook`/`DeedPage` → last sale; `ZONING`/`CLASS`/`TAXDIST` → routing/class.
- **Verified counts:** `PRICE>0` **29,721**; `APRBLDG=0/null` **13,912**.
- **Notes:** Primary wire-first layer. `ACRES` is string; use TaxZoning/42 or tax/51 for numeric acreage. `TOT22` is entirely null on REST. Paginate.

### 2. TaxZoning Parcels — joined CAMA + deeds

- **REST:** https://www.franklincountymaps.net/arcgis/rest/services/TaxZoning/MapServer/42
- **Layer:** 42 · Polygon · county-wide · **46,464** features · max record count **1,000**
- **Fields:** prefixed ParcelPolys fields provide `PARID`, `PIN`, `COMPACRES`, `MAPACRES`; prefixed allparcels fields provide `ACRES`, owner, mailing, `APRLAND`, `APRBLDG`, `OBYVAL`, zoning, class, tax district; prefixed deeds fields provide `PRICE`, `SALEDT`, `BOOK`, `PAGE`.
- **Verified counts:** allparcels `ACRES` 5–150 **8,246**; building zero/null in range **3,854**; deed price >0 in range **3,423**.
- **Notes:** Prefer for acreage filters. Quote fully qualified field names; some queries require OBJECTID or envelope paging.

### 3. tax Parcels — geometry + numeric `COMPACRES`

- **REST:** https://www.franklincountymaps.net/arcgis/rest/services/tax/MapServer/51
- **Layer:** 51 · Polygon · county-wide · **46,464** features
- **Fields:** `PARID`, `PIN`, `PID`, `COMPACRES`, `MAPACRES`, `PRODNO`.
- **Verified counts:** `COMPACRES` 5–150 **7,702**; `MAPACRES` 5–150 **2,593**.
- **Notes:** Geometry-focused. Join to tax/53 on `PARID`; prefer layers 0 or 42 for rich attributes.

### 4. tax allparcels CAMA table

- **REST:** https://www.franklincountymaps.net/arcgis/rest/services/tax/MapServer/53
- **Layer:** 53 · table · county-wide · **47,127** records
- **Fields:** `PARID`, `ALTID`, `ACRES`, `OWN1`, `OWN2`, mailing fields, `APRLAND`, `APRBLDG`, `OBYVAL`, `ZONING`, `CLASS`, `TAXDIST`.
- **Verified counts:** `ACRES` 5–150 **7,847**; building zero/null in range **3,699**.
- **Sales companion:** tax/MapServer/54 deeds table, count **42,580**, `PRICE>0` **25,467**.

### 5. NC OneMap parcels — statewide fallback

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer:** 1 · Polygon · filter `cntyfips='069'` · **47,981** Franklin features · max record count **5,000**
- **Fields:** `parno`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`/`scity`, `gisacres`, `saledate`, `parval`/`landval`/`improvval`, `cntyfips`.
- **Verified counts:** `gisacres` 5–150 **7,785**; improvement zero/null in range **3,708**.
- **Notes:** No sale price; `siteadd` often empty; `parno` approximately matches county PIN. Alternate host: https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1

### 6. County Zoning polygons — unincorporated primary

- **REST:** https://www.franklincountymaps.net/arcgis/rest/services/OperationalLayers/MapServer/35
- **Layer:** 35 · Polygon · **848** features
- **Field:** `ZONING` → zoning.
- **Notes:** Franklin County Planning area / unincorporated coverage, not town zoning polygons. Pair with City Limits and parcel zoning for municipal routing.

### 7. Youngsville ParcelPolygons zoning — city-first

- **REST:** https://services1.arcgis.com/aT1T0pU1ZdpuDk1t/arcgis/rest/services/Youngsville_WFL1/FeatureServer/0
- **Layer:** 0 · Polygon · Youngsville-only · **6,759** features
- **Fields:** `PARID`, `PIN`, `PID`, `ZONING`, `COMPACRES`; `COMPACRES` 5–150 count **408**.
- **Notes:** CRS 3857. Prefer inside Youngsville. Viewer: https://experience.arcgis.com/experience/cd96cf06c7724708b7349a97be3beed7/

### 8. Wake Forest Zoning — Franklin tip

- **REST:** https://maps.wake.gov/arcgis/rest/services/Planning/Zoning/MapServer/25
- **Layer:** 25 · Polygon · Wake Forest city-only · **469** features
- **Fields:** `ZONECLASS`, `ZONELABEL`, `ZONEDEFINE`, `CLASS`.
- **Notes:** Wake County host. Clip to Franklin using City Limits `NAME=WAKE FOREST`; the YAML notes about 1,403 `TAXDIST=WKFS` parcels refer to the Franklin tip.

### 9. Parcel `ZONING` attribute — multi-jurisdiction stub

- **REST:** OperationalLayers/MapServer/0 (same as primary)
- **Fields:** `ZONING`, `TAXDIST`.
- **Notes:** Fast filter with about 119 distinct codes, including FCO and town codes. Spatial join to authoritative county, Youngsville, or Wake polygons remains recommended. Louisburg, Franklinton, and Bunn have no public zoning FeatureServer found in this pass.

### 10. Future Land Use — honest gap

- **REST:** none
- **Status:** gap. County Comprehensive Development Plan and town plans are PDF-only. Do not invent a polygon REST URL.

### 11. Address Points — situs join

- **REST:** https://www.franklincountymaps.net/arcgis/rest/services/OperationalLayers/MapServer/1
- **Layer:** 1 · Point · county-wide · **43,997** features
- **Fields:** `L_FullAddress`, `Add_Number`, `L_FullName`, `Post_Code`, `PIN`, `PID`.
- **Notes:** Join to parcel PIN/PID; preferred over sparse primary-layer situs components. tax/MapServer/50 is a secondary address-point source with PARID/ROAD fields.

### 12. City Limits

- **REST:** https://www.franklincountymaps.net/arcgis/rest/services/OperationalLayers/MapServer/6
- **Layer:** 6 · Polygon · **26** multipart polygons
- **Field:** `NAME` → municipality.
- **Values:** LOUISBURG, FRANKLINTON, YOUNGSVILLE, BUNN, WAKE FOREST. Centerville is dissolved and absent.

### 13. Extra Territorial Jurisdictions

- **REST:** https://www.franklincountymaps.net/arcgis/rest/services/OperationalLayers/MapServer/41
- **Layer:** 41 · Polygon · **11** features
- **Fields:** `ZONE_CO` → ETJ code; `ACRES_CO` → ETJ acres.
- **Notes:** ETJ1–ETJ5; pair with City Limits for planning-jurisdiction routing.

### 14. 2025 Qualified Sales

- **REST:** https://www.franklincountymaps.net/arcgis/rest/services/OperationalLayers/MapServer/55
- **Layer:** 55 · Polygon · sample · **1,409** features
- **Fields:** `PARID`, `PIN`, `PRICE`, `SALEDT`, `RECORDDT`, `SALEVAL`, `COMPACRES`.
- **Notes:** Qualified-sales subset. Companion years: 2024/54 (1,644), 2023/53, 2022/52, 2021/51. Primary parcel `PRICE`/`SALEDT` remains the general last-sale source.

## Jurisdiction routing

| Jurisdiction | Zoning source | FLU | Viewer / routing note |
|---|---|---|---|
| Unincorporated Franklin | County Zoning/35 + parcel `ZONING` | Gap | Franklin County Maps homepage |
| Youngsville | Youngsville_WFL1/0, city-first | Gap | Youngsville Experience viewer |
| Wake Forest (Franklin tip) | Wake Planning/Zoning/25, clipped to Franklin | Use Wake/local source outside this card | County City Limits + `TAXDIST=WKFS` QA |
| Louisburg | Parcel `ZONING` + City Limits; no public town zoning FS found | Gap | Franklin County Maps homepage |
| Franklinton | Parcel `ZONING` + City Limits; no public town zoning FS found | Gap | Franklin County Maps homepage |
| Bunn | Parcel `ZONING` + City Limits; no public town zoning FS found | Gap | Franklin County Maps homepage |

## Gaps and cautions

- No public FLU polygon REST; county and town plans are PDF-only.
- Louisburg / Franklinton / Bunn lack public zoning FeatureServers; use parcel zoning plus City Limits.
- Centerville dissolved; CTVF tax district remains but there is no city-limits polygon.
- Web View `ACRES` is string; use TaxZoning `ACRES` or tax `COMPACRES` for numeric filters.
- `TOT22` is null on REST; approximate market as `APRLAND + APRBLDG`.
- Parcel `ADR*` situs parts are often empty; join Address Points.
- Hosted/Planning_Opengov is token-required; NCSU Youngsville_File_MS had expired SSL on 2026-09-24.
- TaxZoning pagination is unreliable on some queries; page by OBJECTID or envelope.
- No multi-transfer sales history beyond last deed plus annual qualified-sales layers.
- No paid vendor data, phones/emails, AADT, or utilities dig.

## Hand-off notes

1. **Wire first:** OperationalLayers/0 for countywide polygons, owner, mailing, tax, last sale, parcel zoning and IDs.
2. **Acreage:** use TaxZoning/42 numeric `ACRES` or tax/51 `COMPACRES`; do not numeric-filter primary string `ACRES`.
3. **Owner / tax / sale:** owner `OWN1`/`OWN2`; land/building `APRLAND`/`APRBLDG`; last sale `PRICE`/`SALEDT`; qualified sales layer 55 for subset analysis.
4. **Situs:** join Address Points/1 to parcel `PIN` or `PID`.
5. **Zoning:** city-first routing via City Limits; Youngsville FS/0 and Wake Zoning/25 are local exceptions; otherwise county Zoning/35 plus parcel attribute.
6. **PA detail:** `https://lrcpwa.ncptscloud.com/franklin/parcel-detail/{PARID}`; search: https://lrcpwa.ncptscloud.com/franklin/parcel-search.
7. **Jurisdiction GIS viewer:** https://www.franklincountymaps.net/maps/.
8. **Auth:** no auth observed on listed public query endpoints; Franklin layer queries require a browser User-Agent.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live quick checks (2026-09-24 ET):** primary metadata/query HTTP 200, count **50,019**; owner `OWN1 IS NOT NULL` count **49,252**; tax/53 count **47,127**; qualified sales/55 count **1,409**; NCPTS search HTTP 200; sample PA detail `/parcel-detail/029893` HTTP 200; public GIS homepage HTTP 200.
- **Sample primary query:** `PARID=029893` returned owner, land/building values, `PRICE`, and `SALEDT`.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://www.franklincountymaps.net/arcgis/rest/services/OperationalLayers/MapServer/0 · id `PARID` · live count **50,019** · 5–150 ac **8,310** (`ACRES cast to number, 5–150 (client-side; field is string)`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='FRANKLIN'` gives **360** stations (211 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27FRANKLIN%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Franklin'` gives **361** stations (239 with AADT_2025, 216 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Franklin%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Franklin'` gives **362** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok-derive-total):** `APRLAND` non-zero **49,055**, `APRBLDG` non-zero **36,107**, `TOT22` non-zero **0**. TOT22 is 0 for every row (stale legacy field) — derive market = APRLAND + APRBLDG + OBYVAL.
- **Sale history (ok):** price `PRICE` >0 **29,721**; date `SALEDT` non-null **47,941**
- **Owner entity:** fields `OWN1`, `OWN2`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **1,573** of 8,310 (extended regex: 1,666).
- **PA deep link:** `https://lrcpwa.ncptscloud.com/franklin/parcel-detail/{PARID}`. Tested `016244` → HTTP **200** (text/html), content verified: False. NCPTS PWA returns HTTP 200 SPA shell for any path; parcel resolves client-side. Headless Chrome render from box showed app-level '404 Page Not Found' even for /{tenant}/parcel-search, so resolution is UNVERIFIED (may be headless/network gating). Manual browser check recommended.
- **Jurisdiction GIS viewer:** https://www.franklincountymaps.net/maps/ → HTTP **200** (Avineon Web Map Template)
- **Pass 2 gaps:** TOT22 all zero — market total must be derived; PA link is NCPTS SPA only — parcel resolution unverified
