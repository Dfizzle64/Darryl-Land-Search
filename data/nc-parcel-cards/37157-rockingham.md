# Rockingham County, NC — GIS County Card

## Summary

Rockingham County (Winston-Salem / Triad footprint, FIPS **37157**, slug **rockingham**) publishes public **Hurt & Proffitt WebGIS** (`webgis.net/nc/rockingham`) plus **rockcogis** ArcGIS Online (`services2.arcgis.com/6ceReeeoWYqSyV5I`). **PRIMARY CAMA:** `Tax_gdb/FeatureServer/2` Expanded parcels — ~**56,392** polygons with owner, mailing, **situs PhysLoc***, calculated/map/deed acres, land/improve FMV, **SalesAmount / DateSold / QualifyCode**. Wire twin **`NC/Rockingham/MapServer/8`** (~**56,391**, CRS **102719/2264**) adds parcel **Zoning** attr + tax/sale but **no situs**. **Cities-first zoning:** City of **Reidsville** publishes independent `Zoning_Districts` (**8,285**; field `ZONING`). Eden / Mayodan / Madison / Stoneville / Wentworth use **county Zoning** (`MapServer/30` / `Planning_gdb/1`, ~**58.4k**) routed by Cities/ETJ; parcel `Zoning` codes often carry muni suffixes (**ED / RD / MY / MD / ST**). **FLU proxy:** `Planning_gdb/Land_Classification` (**55** polys; CLASS DEVELOPED / RURAL / ECONOMIC DEVELOPMENT / RURAL|URBAN TRANSITION). **NC OneMap** `cntyfips='157'` (~**56,362**) is a solid FeatureServer fallback (no sale price). **PA:** PropertyCard `?pid={ParcelNumber}` + ustaxdata `account.cfm?account={ParcelNumber}` (HTML verified). Tranche-3 tax/sale/owner + PA deep-link + jurisdiction GIS URL satisfied.

## Portals

- **Rockingham Co NC WebGIS (jurisdiction GIS)** — https://www.webgis.net/nc/rockingham/
- **County Maps page** — https://www.rockinghamcountync.gov/21117/Maps
- **GIS department** — https://www.rockinghamcountync.gov/21346/GIS
- **Data Hub** — https://data-hub-rock-co-gis.hub.arcgis.com/
- **Tax Experience (AGOL)** — https://experience.arcgis.com/experience/ea0b9b0d72b045508eecb769a7fec091
- **WebGIS MapServer REST** — https://www.webgis.net/arcgis/rest/services/NC/Rockingham/MapServer
- **County AGOL REST** — https://services2.arcgis.com/6ceReeeoWYqSyV5I/arcgis/rest/services
- **Property Card (PA deep-link)** — `https://www.webgis.net/nc/Rockingham/PropertyCard.php?pid={ParcelNumber}`
- **ustaxdata account (PA)** — `https://www.ustaxdata.com/nc/rockingham/account.cfm?account={ParcelNumber}`
- **ustaxdata search** — https://www.ustaxdata.com/nc/rockingham/rockinghamtaxsearch.cfm
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/rockingham/parcel-search — detail `/parcel-detail/{ParcelNumber}` or `{PIN}` (SPA)
- **Tax bill search page** — https://www.rockinghamcountync.gov/21344/Tax-Bill-Search
- **Reidsville Public Zoning Map** — https://reidsville-nc.maps.arcgis.com/apps/instant/sidebar/index.html?appid=b591ac3e34c74a3e8ee5885db75e5d76
- **Reidsville GIS page** — https://www.reidsvillenc.gov/planning-and-community-development/page/geographic-information-system-gis
- **NC OneMap** — https://www.nconemap.gov — filter `cntyfips='157'`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `ParcelNumber`, `OwnerID`; OneMap `parno`≈PIN | Prefer `PIN` join; `ParcelNumber` for PA |
| polygons | Yes | Tax_gdb/2; MapServer/8 | AGOL **3857**; WebGIS **2264** |
| acreage | Yes | `CALCULATED_ACREAGE`, `MapAcres`, `DeedAcres`; OneMap `gisacres` | CALC 5–150 → **9915**; Deed/Map → **10301**; gisacres → **10337** |
| ownerName | Yes | `Name1` (+ Name2/3); OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `TaxpayAddress*`, `TaxpayCity/State/ZIP` | |
| situs address | Yes | Expanded `PhysLoc*`; Structures `ADDRESS`; OneMap `siteadd` | MapServer/8 **lacks** situs |
| lastSale date/price | Yes | `SalesAmount`, `DateSold`, `QualifyCode`, deed book/page | SalesAmount>0 → **23257**; QualifyCode often blank |
| tax values | Yes | `LandFMVCUR`, `ImproveFMVCUR`, MapServer `LandValue`/`ImprovmentValue`/`TotalValue` | Improve=0 in acre range → **~3474** |
| zoning | Yes (cities-first) | Reidsville `ZONING`; county `ZONE_CODE`; parcel `Zoning` | Reidsville independent FS; others county |
| flu | Partial | Land_Classification `CLASS` | Coarse plan categories — not parcel FLUM |
| appraiser / viewer link | Yes | PropertyCard + ustaxdata account by ParcelNumber | Templates below |

## Layers (verified)

### 1. Tax_gdb Expanded parcels — CAMA + situs + sale + tax (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | situs
- **REST URL:** https://services2.arcgis.com/6ceReeeoWYqSyV5I/arcgis/rest/services/Tax_gdb/FeatureServer/2
- **Layer name / id:** Expanded_Parcels_Tax_View_Long / 2
- **Geometry:** Polygon | CRS **102100 / 3857** | MaxRecordCount **2000**
- **Key fields → targets:** `PIN`, `ParcelNumber`, `OwnerID` → parcelId*; `CALCULATED_ACREAGE` / `MapAcres` / `DeedAcres` → acreage; `Name1`–`3` → owner; `Taxpay*` → mailing; `PhysLoc*` → situs; `SalesAmount`/`DateSold`/`QualifyCode` → lastSale; `LandFMVCUR`/`ImproveFMVCUR`/`LandLUVCUR` → tax; `CityCode` → municipality hint
- **Verified:** yes — count **56,392**; CALCULATED_ACREAGE 5–150 → **9,915**; SalesAmount>0 → **23,257**; PhysLocStNAME present → **56,044**; improve FMV 0/null in range → **3,474**; sample centroid **(−80.02, 36.49)**
- **Notes:** **PRIMARY** wire-first for tranche-3 tax/sale/owner/situs. **No Zoning field** — join Tax_gdb/10 or MapServer/8 by PIN.

### 2. NC/Rockingham MapServer/8 Parcels — wire twin + Zoning attr

- **REST:** https://www.webgis.net/arcgis/rest/services/NC/Rockingham/MapServer/8
- **CRS:** **102719 / 2264** | count **56,391** | DeedAcres 5–150 → **10,302** | Zoning present → **56,070** | SalesAmount>0 → **23,236**
- **Notes:** Prefer for StatePlane geometry + parcel Zoning string. Lacks PhysLoc situs. No FeatureServer on WebGIS host.

### 3. Tax_gdb/10 Rockingham_County_Parcel_Data — Zoning + Property_Card URL

- **REST:** https://services2.arcgis.com/6ceReeeoWYqSyV5I/arcgis/rest/services/Tax_gdb/FeatureServer/10 — count **56,507**
- **Fields:** `Zoning`, `Property_Card` (= `https://www.webgis.net/nc/Rockingham/PropertyCard.php?pid={ParcelNumber}`), land/improve/total, SalesAmount
- **Notes:** Best source for embedded PA URL + Zoning attr to join onto Expanded.

### 4. NC OneMap Parcels — fallback

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 | filter `cntyfips='157'` | count **56,362** | gisacres 5–150 → **10,337**
- **Notes:** PIN↔parno verified. **No sale price.** Alternate `services.gis.nc.gov`.

### 5. Reidsville Zoning_Districts — CITY-FIRST

- **REST:** https://services6.arcgis.com/F05wl398YvOrLJax/arcgis/rest/services/Reidsville_Public_Zoning_Map_WFL1/FeatureServer/2
- **Count:** **8,285** | field `ZONING` (R-6, R-12, R-20, RA-20, RS-12, HB, GB, O & I, I-1/2/3, CB, NB, …)
- **Viewer:** Instant Sidebar appid `b591ac3e34c74a3e8ee5885db75e5d76`
- **Geo-verified:** (−79.66, 36.39)

### 6. County Zoning — MapServer/30 + Planning_gdb/1

- **MapServer:** https://www.webgis.net/arcgis/rest/services/NC/Rockingham/MapServer/30 — **58,387** | `ZONE_CODE`
- **AGOL:** https://services2.arcgis.com/6ceReeeoWYqSyV5I/arcgis/rest/services/Planning_gdb/FeatureServer/1 — **58,435** | `ZONE_CODE`
- **Notes:** Single stack covers county + munis without their own FS. Spatial-join Cities/ETJ for authority routing.

### 7. Land_Classification — FLU proxy

- **REST:** https://services2.arcgis.com/6ceReeeoWYqSyV5I/arcgis/rest/services/Planning_gdb/FeatureServer/5 — **55** | `CLASS` / `ACRES`
- **Classes:** DEVELOPED, ECONOMIC DEVELOPMENT, RURAL, RURAL TRANSITION, URBAN TRANSITION
- **Status:** partial (coarse plan classification)

### 8. Cities / ETJ / Addressed Structures

- **Cities /27:** EDEN, MADISON, MAYODAN, REIDSVILLE, STONEVILLE, WENTWORTH (**6**)
- **ETJ /28:** same six jurisdictions (**22** polys)
- **Addressed Structures /1:** **54,513** points — CITY codes REID **21,598**, EDEN **13,112**, MAD, STON, MAY, …

## Municipalities (cities-first routing)

| Municipality | Zoning REST | FLU | Notes |
|--------------|-------------|-----|-------|
| Reidsville | **WFL1/2 Zoning_Districts** (city-first) | Land_Classification/5 | Independent city AGOL |
| Eden | MapServer/30 + parcel `*ED` | Land_Classification/5 | No city FS |
| Mayodan | MapServer/30 + parcel `*MY` | Land_Classification/5 | No city FS |
| Madison | MapServer/30 + parcel `*MD` | Land_Classification/5 | No city FS |
| Stoneville | MapServer/30 + parcel `*ST` | Land_Classification/5 | No city FS |
| Wentworth | MapServer/30 | Land_Classification/5 | County seat; no city FS |
| Unincorporated | MapServer/30 / Planning_gdb/1 | Land_Classification/5 | RA / RP dominant |

## Deep-link templates

- **Property Card (preferred PA):** `https://www.webgis.net/nc/Rockingham/PropertyCard.php?pid={ParcelNumber}`
- **ustaxdata account:** `https://www.ustaxdata.com/nc/rockingham/account.cfm?account={ParcelNumber}`
- **ustaxdata search:** https://www.ustaxdata.com/nc/rockingham/rockinghamtaxsearch.cfm
- **NCPTS detail:** `https://lrcpwa.ncptscloud.com/rockingham/parcel-detail/{ParcelNumber}` (alt `{PIN}` — SPA)
- **Jurisdiction GIS:** https://www.webgis.net/nc/rockingham/
- **Reidsville zoning viewer:** https://reidsville-nc.maps.arcgis.com/apps/instant/sidebar/index.html?appid=b591ac3e34c74a3e8ee5885db75e5d76

## Gaps

- Eden / Mayodan / Madison / Stoneville / Wentworth — no independent public zoning FeatureServer
- No parcel-keyed Future Land Use FeatureServer — Land_Classification only (coarse)
- Expanded Tax view lacks Zoning — join required
- MapServer parcels lack situs PhysLoc* — use Expanded / Structures / OneMap
- Property Sales points lack PIN
- CRS mismatch AGOL 3857 vs WebGIS 2264
- NCPTS deep-link is SPA — prefer PropertyCard + ustaxdata HTML
- QualifyCode sparse; OneMap has no sale price
- Utilities MapServer and AADT intentionally out of scope; no phones/emails; no paid vendors

## Hand-off notes for Land Search Builder

1. **Wire first:** Tax_gdb/FeatureServer/2 — filter `CALCULATED_ACREAGE BETWEEN 5 AND 150` (~9.9k); optional vacant-ish `ImproveFMVCUR=0` (~3.5k in range).
2. **Join Zoning:** by PIN to Tax_gdb/10 or MapServer/8 `Zoning`, else spatial-join MapServer/30; **inside Reidsville** prefer city Zoning_Districts.
3. **FLU:** spatial-join Planning_gdb/5 `CLASS` (coarse).
4. **Sales:** parcel `SalesAmount` when >0; else deed date only; ignore Sales points layer for attribution.
5. **Fallback:** OneMap layer 1 `cntyfips='157'`.
6. **PA / viewer:** PropertyCard + ustaxdata by `ParcelNumber`; jurisdiction GIS WebGIS homepage.
7. **Join keys:** `PIN` ↔ OneMap `parno`; `ParcelNumber` for PA.
8. **Auth:** none on listed public endpoints.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- Live REST counts, field maps, sample attributes, WGS84 centroids, PropertyCard/ustaxdata HTML, Reidsville Zoning_Districts, and NC OneMap (`cntyfips='157'`) checked 2026-09-24.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services2.arcgis.com/6ceReeeoWYqSyV5I/arcgis/rest/services/Tax_gdb/FeatureServer/2 · id `ParcelNumber` · live count **56,392** · 5–150 ac **9,915** (`CALCULATED_ACREAGE >= 5 AND CALCULATED_ACREAGE <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='ROCKINGHAM'` gives **740** stations (299 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27ROCKINGHAM%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Rockingham'` gives **738** stations (422 with AADT_2025, 467 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Rockingham%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Rockingham'` gives **738** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok-derive-total):** `LandFMVCUR` non-zero **55,885**, `ImproveFMVCUR` non-zero **43,523**. No total FMV field on Tax_gdb/2 — derive market = LandFMVCUR + ImproveFMVCUR (+ImproveFMVCUR2); LandLUVCUR = PUV.
- **Sale history (ok):** price `SalesAmount` >0 **23,257**; date `DateSold` non-null **56,034**
- **Owner entity:** fields `Name1`, `Name2`, `Name3`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **1,158** of 9,915 (extended regex: 1,604).
- **PA deep link:** `https://www.webgis.net/nc/Rockingham/PropertyCard.php?pid={ParcelNumber}`. Tested `169650` → HTTP **200** (text/html), content verified: True. Parcel id found in the response body.
- **Jurisdiction GIS viewer:** https://www.webgis.net/nc/rockingham/ → HTTP **200** (Rockingham Co NC WebGIS)
- **Pass 2 gaps:** No total value field — derive
