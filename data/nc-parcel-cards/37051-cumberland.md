# Cumberland County, NC — GIS County Card

## Summary

Cumberland County (Fayetteville MSA, FIPS **37051**, slug **cumberland**, `cntyfips='051'`) publishes public ArcGIS REST at `gis.co.cumberland.nc.us`. **Wire-first parcels:** **Tax/Parcels** MapServer/0 — ~**140,670** polygon rows (multi-building CAMA; dedupe by `PIN`/`REID`/`FEATURE_KEY`) with owner, mailing, situs (`LOCATION_ADDR`), acreage, last package/land sale price+date, deed refs, full assessed tax split, and parcel-level `Zoning` stub. ACREAGE 5–150 → **8,665** rows (~**4,496** bldg 0/null; ~**887** `PKG_SALE_PRICE`>0). **Cities-first zoning:** **Fayetteville** dedicated layer CCZoning/0 (**4,693**, `ZNTYPE`); towns via CCZoning/1 `Jurisdiction` — Hope Mills (**189**), Spring Lake (**137**), Eastover (**101**), Wade (**40**), Stedman (**28**), Linden (**24**), Falcon (**23**), Godwin (**17**); blank/`COUNTY` = unincorporated county districts (**~1,964**). **FLU:** Planning/CCFutureLandUse2025 (**738**, `Land_Use`) + All/2024 (**870**). **PA:** camapwa `PropertySummary.aspx?REID={REID}` (+ `PARCELPK={PARCEL_PK}`); NCPTS `{PIN}` secondary. **Do not use** shared ITSPublicDL (Duplin-branded). Markets: **[Fayetteville]**.

## Portals

- **Public GIS viewer (DataViewer)** — https://gis.co.cumberland.nc.us/DataViewer/ → https://cumberlandgis.maps.arcgis.com/apps/webappviewer/index.html?id=a6ea68995c2349e9a177366288589be7
- **County resources map** — https://cumberlandgis.maps.arcgis.com/apps/webappviewer/index.html?id=18540dd767dc4004899d6b31aa6c18f1
- **GIS Maps & Apps** — https://www.cumberlandcountync.gov/departments/is-technology-group/innovation-and-technology-services/organized/geospatial-information-services/gis
- **Featured apps gallery** — https://cumberlandgis.maps.arcgis.com/apps/instant/filtergallery/index.html?appid=f93f7ce90df84e54907857c38672bd6c
- **County ArcGIS REST** — https://gis.co.cumberland.nc.us/server/rest/services
- **Tax / Real Estate & GIS Mapping** — https://www.cumberlandcountync.gov/departments/tax-group/tax/real-estate-gis-mapping
- **Tax Administration** — https://www.cumberlandcountync.gov/departments/tax-group/tax
- **PA / CAMA Property Search** — https://taxpwa.co.cumberland.nc.us/camapwa/
- **PA deep-link (REID)** — `https://taxpwa.co.cumberland.nc.us/camapwa/PropertySummary.aspx?REID={REID}`
- **PA deep-link (PARCEL_PK)** — `https://taxpwa.co.cumberland.nc.us/camapwa/PropertySummary.aspx?PARCELPK={PARCEL_PK}`
- **Tax bill search** — https://taxpwa.co.cumberland.nc.us/publicwebaccess/
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/cumberland/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/cumberland/parcel-detail/{PIN}`
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`); filter `cntyfips='051'`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` / `NAD83_PIN`; `REID`; `PARCEL_PK`; OneMap weak `parno` | Prefer **PIN** (####-##-####); PA uses **REID** |
| polygons | Yes | Tax/Parcels MS/0 | CRS **WKID 102719 / 2264**; dedupe multi-bldg rows |
| acreage | Yes | `ACREAGE`; OneMap `recareano` (not `gisacres`) | 5–150 → **8,665** rows |
| ownerName | Yes | `OWNER`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `ADDRESS`, `CITY`, `STATE`, `ZIP` | |
| situs address | Yes | `LOCATION_ADDR`; PHYADDR_*; E911/MMLayers AddressPts | |
| lastSale date/price | Yes (last pkg + land) | `PKG_SALE_PRICE`/`PKG_SALE_DATE`; `LAND_SALE_*`; deed book/page/date | Also Tax/ParcelSales category layers |
| tax values | Yes | `TOTAL_PROP_VALUE`, `TOTAL_LAND_VALUE_ASSESSED`, `TOTAL_BLDG_VALUE_ASSESSED`, `TOTAL_OBLDG_VALUE`, deferred/use fields | On PRIMARY layer |
| zoning | Yes (cities-first) | Fay `ZNTYPE`; county/towns `Zone_Class`+`Jurisdiction`; parcel `Zoning` stub | Prefer most local |
| flu | Yes | CCFutureLandUse2025 `Land_Use` (+ Plan_Nam_2) | Area plans (Hope Mills Area, Spring Lake Area, etc.) |
| appraiser / viewer link | Yes | camapwa `{REID}` / `{PARCEL_PK}`; NCPTS `{PIN}`; DataViewer | Templates below |

### Zoning inventory (verified)

| Layer | Count | Field | Scope |
|-------|-------|-------|-------|
| Fayetteville Zoning (CCZoning/0) | **4,693** | `ZNTYPE` | City-first PRIMARY |
| Cumberland County Zoning (CCZoning/1) | **2,523** | `Zone_Class` + `Jurisdiction` | County + towns |
| — Hope Mills (Jurisdiction) | **189** | `Zone_Class` | City-first |
| — Spring Lake | **137** | `Zone_Class` | City-first |
| — Eastover | **101** | `Zone_Class` | City-first |
| — Wade / Stedman / Linden / Falcon / Godwin | 40/28/24/23/17 | `Zone_Class` | City-first |
| — blank + COUNTY | ~1,964 | `Zone_Class` | Unincorporated |
| Overlay Districts | **12** | `Zone_Class` | Overlays |

### Fayetteville ZNTYPE (top)

| ZNTYPE | Count |
|--------|-------|
| SF-10 | 1417 |
| SF-6 | 746 |
| MR-5 | 459 |
| CC | 438 |
| LC | 344 |
| SF-15 | 234 |
| OI | 225 |
| AR | 153 |
| HI | 145 |
| NC | 102 |

### County / town Zone_Class (top overall)

| Zone_Class | Count |
|------------|-------|
| RR | 409 |
| C(P) | 275 |
| R40A | 188 |
| R6A | 176 |
| R10 | 170 |
| R40 | 164 |
| C3 | 137 |
| A1 | 132 |

### Municipal / City_Limits inventory (parcels attribute)

Fayetteville (~76k rows), unincorporated/blank (~50k), Hope Mills (~7.0k), Spring Lake (~2.8k), Eastover (~2.5k), Stedman, Wade, Falcon, Godwin, Linden. **AdminBoundaries/CityLimits** polygons for same set.

## Layers (verified)

### 1. Tax/Parcels — parcels + ownership + tax + situs + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | situs | zoning stub
- **REST URL (wire-first):** https://gis.co.cumberland.nc.us/server/rest/services/Tax/Parcels/MapServer/0
- **Also:** MMLayers/MapServer/7 Parcels mirror; FeatureServer SOE **not** enabled (500)
- **Layer name / id:** Tax Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` / `NAD83_PIN` → parcelId
  - `REID` → parcelIdPaKey (camapwa)
  - `PARCEL_PK` → parcelIdAlt / PARCELPK
  - `ACREAGE` → acreage
  - `OWNER` → ownerName
  - `ADDRESS`/`CITY`/`STATE`/`ZIP` → mailing
  - `LOCATION_ADDR` → situs
  - `PKG_SALE_PRICE`, `PKG_SALE_DATE`, `LAND_SALE_PRICE`, `LAND_SALE_DATE`, `DEED_*` → lastSale
  - `TOTAL_PROP_VALUE`, `TOTAL_LAND_VALUE_ASSESSED`, `TOTAL_BLDG_VALUE_ASSESSED`, `TOTAL_OBLDG_VALUE`, deferred/use → tax
  - `Zoning`, `City_Limits`, `ETJ` → zoning/muni hints
  - `YEAR_BUILT`, `HEATED_AREA`, `NEIGHBORHOOD`, `BLDG_PK`, `FEATURE_KEY` → other / dedupe
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **140,670** rows; ACREAGE 5–150 → **8,665**; bldg 0/null in band → **4,496**; PKG_SALE_PRICE>0 in band → **887**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. **Multi-building:** same PIN/REID can have multiple rows (`BLDG_PK` differs; `FEATURE_KEY` shared) — dissolve/dedupe for polygon ingest. Geo-check REID `0414581081000` / PIN `0414-58-1081` ≈ **-78.949, 34.981** (Hope Mills). Auth: none.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | situs (acreage weak)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='051'`
- **Key fields:** `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`, `recareano` (prefer over broken `gisacres`), `saledate`, `parval`/`landval`/`improvval`, `nparno`
- **Verified:** yes — count **140,513**; `parno` often **blank**; `gisacres` near-zero/unusable — use **`recareano`** or county `ACREAGE`
- **Notes:** No reliable PIN string join via `parno` — prefer spatial join to Tax/Parcels. MaxRecordCount **5000**.

### 3. Fayetteville Zoning — city-first (PRIMARY for Fayetteville)

- **REST:** https://gis.co.cumberland.nc.us/server/rest/services/Planning/CCZoning/MapServer/0
- **Field:** `ZNTYPE` (+ `CAMA_CODE`)
- **Count:** **4,693** | CRS 2264
- **Join:** spatial; gate with City_Limits=`FAYETTEVILLE` / AdminBoundaries CityLimits
- **Notes:** Mirror MMLayers FayZoning (17). Prefer over parcel `Zoning` stub inside city.

### 4. Cumberland County Zoning — county + towns (Jurisdiction)

- **REST:** https://gis.co.cumberland.nc.us/server/rest/services/Planning/CCZoning/MapServer/1
- **Fields:** `Zone_Class`, `Jurisdiction`, `CAMA_CODE`, `CondU`, `CASE_NO`
- **Count:** **2,523**
- **Join:** spatial; for towns filter `Jurisdiction` ∈ {Hope Mills, Spring Lake, Eastover, Wade, Stedman, Linden, Falcon, Godwin}; blank/`COUNTY` = unincorporated
- **Notes:** Cities-first for non-Fayetteville munis. Mirror MMLayers CC_Zoning (16).

### 5. Overlay Districts

- **REST:** https://gis.co.cumberland.nc.us/server/rest/services/Planning/OverlayDists/MapServer/0
- **Count:** **12** — `Zone_Class`, `Jurisdicti`

### 6. CCFutureLandUse2025 — FLU (PRIMARY)

- **REST:** https://gis.co.cumberland.nc.us/server/rest/services/Planning/CCFutureLandUse2025/MapServer/0
- **Fields:** `Land_Use`, `Plan_Nam_2`, `Adopt_Date`, `Acre`, `Flex_Area_Label`
- **Count:** **738**
- **Notes:** Area plans include Hope Mills Area, Spring Lake Area, Northeast/North Central/South Central, Eastover, Stedman, etc. Alternate: CCFutureLandUseAll/0 (**870**, 2024 merge) and CCFutureLUPs2021.

### 7. Tax/ParcelSales — supplemental sale history (by category/year)

- **REST root:** https://gis.co.cumberland.nc.us/server/rest/services/Tax/ParcelSales/MapServer
- **Layers:** Residential / Commercial / Apartment / Vacant Land (+ yearly children e.g. Vacant Land Sales 2025 **1,324**; Vacant Land Sales 2026 **1,336**)
- **Fields:** same CAMA schema as Tax/Parcels including `PKG_SALE_*` / `LAND_SALE_*`
- **Notes:** Use for sale enrichment beyond last-sale-on-parcel; not a substitute for PRIMARY parcels.

### 8. AdminBoundaries/CityLimits — municipality filter

- **REST:** https://gis.co.cumberland.nc.us/server/rest/services/AdminBoundaries/CityLimits/MapServer/0
- **Field:** `CITY_NAME`
- **Notes:** Fayetteville, Hope Mills, Spring Lake, Eastover, Wade, Stedman, Falcon, Godwin, Linden (multi-part polygons).

### 9. Address points — situs join

- **MMLayers AddressPts:** https://gis.co.cumberland.nc.us/server/rest/services/Tax/MMLayers/MapServer/0 — count **138,449**
- **Also:** E911/Addresses service folder

## Municipalities (first-class)

County parcels are countywide. **Zoning:** Fayetteville uses dedicated layer; other towns use CCZoning/1 filtered by `Jurisdiction`. Prefer **most local** zoning. FLU area plans cover Hope Mills / Spring Lake / Eastover / etc. via `Plan_Nam_2`.

### City of Fayetteville (MSA core)

- **Zoning:** CCZoning/0 — `ZNTYPE`; **4,693** (city-first PRIMARY)
- **FLU:** county CCFutureLandUse2025 (area plans overlapping city) — no separate city FLU FS verified
- **Join:** spatial + City_Limits / CityLimits

### Town of Hope Mills

- **Zoning:** CCZoning/1 where `Jurisdiction='Hope Mills'` — **189** (`Zone_Class` C(P)/O&I(P)/C1(P)/R10/…)
- **FLU:** Plan_Nam_2 ≈ Hope Mills Area (**102** polys in 2025 FLU)
- **Join:** Jurisdiction filter + CityLimits Hope Mills

### Town of Spring Lake

- **Zoning:** CCZoning/1 `Jurisdiction='Spring Lake'` — **137**
- **FLU:** Spring Lake Area (**75**)

### Town of Eastover

- **Zoning:** CCZoning/1 `Jurisdiction='Eastover'` — **101**
- **FLU:** Eastover / Eastover Area

### Wade / Stedman / Linden / Falcon / Godwin

- **Zoning:** CCZoning/1 by matching `Jurisdiction` (40 / 28 / 24 / 23 / 17)
- **FLU:** Stedman / regional plans where present

### Unincorporated Cumberland

- **Zoning:** CCZoning/1 where `Jurisdiction` blank or `COUNTY` (~1,964) — county districts (RR, A1, R40A, …)
- **FLU:** Northeast / North Central / South Central / Southeast / Southwest / Vander / Bethany plans

## Gaps

- **Tax/Parcels FeatureServer** not enabled — MapServer only.
- **OneMap `parno` blank / `gisacres` broken** for Cumberland — weak PIN join; use `recareano` or county ACREAGE; prefer county PRIMARY.
- **Multi-building duplicate polygons** on Tax/Parcels — dedupe by PIN/REID/FEATURE_KEY.
- **No separate Fayetteville city FLU FeatureServer** — county area-plan FLU only.
- **Sale history** last-sale on parcel + category ParcelSales layers (not full deed chain API).
- **ITSPublicDL** shared host is **Duplin** — do not wire for Cumberland.
- **camapwa `?PIN=`** alone does not populate PropertySummary — use **REID** or **PARCELPK**.

## PA / deep-link templates

| Purpose | Template |
|---------|----------|
| CAMA Property Summary (REID) | `https://taxpwa.co.cumberland.nc.us/camapwa/PropertySummary.aspx?REID={REID}` |
| CAMA Property Summary (PARCEL_PK) | `https://taxpwa.co.cumberland.nc.us/camapwa/PropertySummary.aspx?PARCELPK={PARCEL_PK}` |
| CAMA search | https://taxpwa.co.cumberland.nc.us/camapwa/ |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/cumberland/parcel-detail/{PIN}` |
| GIS DataViewer | https://gis.co.cumberland.nc.us/DataViewer/ |

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **tranche:** 3 (tax/sale/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- **Excluded:** AADT, utilities, emails/phones, paid vendors


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://gis.co.cumberland.nc.us/server/rest/services/Tax/Parcels/MapServer/0 polygons load (sample centroid [-78.9073, 34.842]); `PIN` filled on 140,601 of 140,666; `ACREAGE` 5–150 ac **8,663**. 140,666 rows but 139,383 distinct PIN (multi-REID rows share a PIN polygon).
- **Attribute layer for Pass 2:** https://gis.co.cumberland.nc.us/server/rest/services/Tax/Parcels/MapServer/0 · id `PIN` · live count **140,666** · 5–150 ac **8,663** (`ACREAGE >= 5 AND ACREAGE <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='CUMBERLAND'` gives **1113** stations (1029 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CUMBERLAND%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Cumberland'` gives **1078** stations (165 with AADT_2025, 979 with AADT_2024, 992 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Cumberland%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `TOTAL_PROP_VALUE` non-zero **134,909**, `TOTAL_LAND_VALUE_ASSESSED` non-zero **139,847**
- **Sale history (ok):** price `PKG_SALE_PRICE` >0 **60,871**; date `PKG_SALE_DATE` non-null **76,972**. PKG_SALE_DATE is a string.
- **Owner entity:** field `OWNER`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **2,643** (all parcels: 24,315), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://taxpwa.co.cumberland.nc.us/camapwa/PropertySummary.aspx?REID={REID}`. Tested `0553447758000` (https://taxpwa.co.cumberland.nc.us/camapwa/PropertySummary.aspx?REID=0553447758000) → HTTP **200** (text/html; charset=utf-8), content verified: True. Server-rendered CAMA PropertySummary; owner and REID verified.
- **Jurisdiction GIS viewer:** https://gis.co.cumberland.nc.us/DataViewer/ → HTTP **200** (ArcGIS Web Application); redirects to https://www.arcgis.com/apps/webappviewer/index.html?id=a6ea68995c2349e9a177366288589be7
- **Pass 2 gaps:** none
