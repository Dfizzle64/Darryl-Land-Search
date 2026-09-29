# Durham County, NC — GIS County Card

## Summary

Durham County (Raleigh–Durham MSA / Research Triangle, FIPS **37063**) publishes rich **public** ArcGIS REST at `webgis2.durhamnc.gov` (City–County shared stack) and AGOL org `G5vR3cOjh6g2Ed8E`. Countywide **tax parcel polygons** carry ownership, mailing, **situs**, GIS/deeded acreage, assessed values, last package/land sale date+price, and a joined **ZONING** string on `PublicServices/Property/MapServer/4` (mirror: AGOL `Parcels_NEW`). Prefer **`REID`** (Parcel ID) over **`PIN`** — Durham Tax Office warns PIN values are recalculated on boundary edits and are unstable. **Zoning / FLU are city-first for tips:** Durham City + unincorporated share the joint City–County UDO zoning + Comprehensive Plan **Place Type** FLU; **Chapel Hill**, **Morrisville**, **Raleigh**, and tiny **Cary** tips inside Durham County need their own municipal zoning REST (spatial join). **NC OneMap** (`cntyfips='063'`) is a solid fallback. Main gaps: tip-muni FLU polygons (Chapel Hill ImageServer-only; Wake tips none found for Durham footprint); ~5.2k parcels with empty `ZONING` attribute; last-sale only (no multi-transfer sales layer); do not use PIN as stable id.

## Portals

- **Durham Maps (City + County viewer)** — https://maps.durhamnc.gov/
- **Open Data Hub** — https://live-durhamnc.opendata.arcgis.com/
- **Planning Hub** — https://planning-durhamnc.hub.arcgis.com/
- **County/City ArcGIS REST** — https://webgis2.durhamnc.gov/server/rest/services
- **AGOL org (Durham)** — https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/arcgis/rest/services
- **Tax / Real Property Search (CAMA)** — https://taxcama.dconc.gov/camapwa/
- **Property Summary deep-link** — `https://taxcama.dconc.gov/camapwa/PropertySummary.aspx?PARCELPK={PARCEL_PK}` or `?REID={REID}`
- **Land Record / GIS (Tax Admin)** — https://dconc.gov/Tax-Administration/Real-Property/Real-Property-Database/Land-Record-GIS
- **Chapel Hill GIS REST** — https://gis-portal.townofchapelhill.org/server/rest/services
- **Wake / Raleigh regional zoning REST** — https://maps.raleighnc.gov/arcgis/rest/services/Planning/Zoning/MapServer (also https://maps.wake.gov/…)
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `REID`, `PARCEL_PK`; OneMap `parno`≈PIN | **Prefer REID**; PIN unstable (2022 algorithm rewrite) |
| polygons | Yes | Property/MapServer/4 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `ACREAGE`, `CALCULATED_ACRES`, `DEEDED_ACRES` | ~**4,940** with ACREAGE 5–150 |
| ownerName | Yes | `PROPERTY_OWNER` / OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `OWNER_MAIL_1`–`3`, `OWNER_MAIL_CITY/STATE/ZIP` | |
| situs address | Yes | `LOCATION_ADDR`; `PHYADDR_*`; OneMap `siteadd` | On primary polygon layer (rare win) |
| lastSale date/price | Yes | `PKG_SALE_DATE`/`PKG_SALE_PRICE`; `LAND_SALE_*` | Prefer package sale; also `DEED_DATE`/`DEED_BOOK`/`DEED_PAGE` |
| tax values | Yes | `TOTAL_PROP_VALUE`, `TOTAL_LAND_VALUE_ASSESSED`, `TOTAL_BLDG_VALUE_ASSESSED`, `TOTAL_OBLDG_VALUE` | Doubles on REST |
| zoning | Yes (split) | Parcel `ZONING`; poly `ZONE_CODE`/`UDO_LABEL`; tip munis | Spatial join preferred for tips / nulls |
| flu | Yes (partial) | Place Type `PlaceType`/`PlaceTypeName` | Durham Comp Plan Place Types; tip FLU gap |
| dorCode / land use | Yes | `LAND_CLASS` | Local land-class string (not NC DOR code) |
| appraiser / viewer link | Yes | taxcama PropertySummary + maps.durhamnc.gov | Templates below |

## Layers (verified)

### 1. PublicServices/Property Parcels — PRIMARY (parcels + owner + situs + tax + sale + zoning attr)

- **Purpose:** parcels | tax | ownership | sales | other (situs) | zoning (attribute)
- **REST URL:** https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Property/MapServer/4
- **Layer name / id:** Parcels / 4
- **Geometry:** Polygon
- **Key fields → targets:**
  - `REID` → parcelId (**preferred**)
  - `PARCEL_PK` → appraiser deep-link key
  - `PIN` → unstable alternate (do not treat as durable id)
  - `ACREAGE`, `CALCULATED_ACRES`, `DEEDED_ACRES` → acreage
  - `PROPERTY_OWNER` → ownerName
  - `OWNER_MAIL_1`–`3`, `OWNER_MAIL_CITY`, `OWNER_MAIL_STATE`, `OWNER_MAIL_ZIP` → mailing
  - `LOCATION_ADDR`, `PHYADDR_STR_NUM`+`PHYADDR_DIR_PFX`+`PHYADDR_STR`+`PHYADDR_STR_TYPE`+`PHYADDR_STR_SFX`, `PHYADDR_CITY`, `PHYADDR_ZIP` → situs
  - `PKG_SALE_DATE`, `PKG_SALE_PRICE`, `LAND_SALE_DATE`, `LAND_SALE_PRICE` → lastSale
  - `TOTAL_PROP_VALUE`, `TOTAL_LAND_VALUE_ASSESSED`, `TOTAL_BLDG_VALUE_ASSESSED`, `TOTAL_OBLDG_VALUE` → tax
  - `ZONING` → zoning (attribute join; may be null / tip-mixed)
  - `CITY`, `ETJ` → municipality / planning jurisdiction
  - `LAND_CLASS` → local land-use class
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **133,548**; `ACREAGE BETWEEN 5 AND 150` → **4,940**; `CALCULATED_ACRES` 5–150 → **4,939**; sample owner/situs/tax/sale OK
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000**. Epoch ms dates. Filter empty/`null` REID if any. ~**5,231** null/empty `ZONING`. LOCATION_ADDR present on all sampled (0 empty). Do **not** harvest phones/emails from CAMA HTML.

### 2. AGOL Parcels_NEW — FeatureServer mirror (same CAMA family)

- **Purpose:** parcels | tax | ownership | sales | situs | zoning (attribute)
- **REST URL:** https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/arcgis/rest/services/Parcels_NEW/FeatureServer/0
- **Layer name / id:** Parcels_NEW / 0
- **Geometry:** Polygon
- **Verified:** yes — count **133,548**; ACREAGE 5–150 → **4,940**
- **Notes:** Slightly richer schema (`VALUE_APPROACH`, `CITY_CODE`, etc.). Same CRS 2264. Prefer county host Property/4 for ops; AGOL fine for downloads/Hub.

### 3. Property Address Points — situs supplement

- **Purpose:** other (situs)
- **REST URL:** https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Property/MapServer/0
- **Layer name / id:** Address Points / 0
- **Geometry:** Point
- **Key fields:** `SITE_ADDRE`, `HOUSENUM`, `STREETNAME`, `STREETTYPE`, `CITY`, `ZIPCODE`, `PARCEL_ID`, `PIN`
- **Verified:** yes — count **196,410**
- **Notes:** Many-to-one vs parcels. Primary situs already on parcel polygons via `LOCATION_ADDR`; use points for unit-level or missing PHYADDR.

### 4. PublicServices/Planning Zoning — Durham City–County UDO polygons

- **Purpose:** zoning
- **REST URL:** https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Planning/MapServer/12
- **AGOL mirror:** https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/arcgis/rest/services/Planning/FeatureServer/12
- **Layer name / id:** Zoning / 12
- **Geometry:** Polygon
- **Key fields → targets:** `ZONE_CODE`, `UDO_LABEL`, `UDO_LEGEND`, `ZONE_GEN`, `PDR`, `PDR_DENSIT`, `CASE_NO`
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **2,525** (both hosts)
- **Join to parcels:** **spatial join** (intersect/centroid) in 2264. Covers **Durham City + Durham County unincorporated** UDO. Does **not** replace Chapel Hill / Morrisville / Raleigh / Cary tip zoning.
- **Notes:** Prefer `UDO_LABEL` or `ZONE_CODE` as zoning display. Parcel attribute `ZONING` is a convenience join — refresh via spatial join when null/stale.

### 5. Place Type — Comprehensive Plan FLU (PRIMARY FLU)

- **Purpose:** flu
- **REST URL:** https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Planning/MapServer/25
- **AGOL mirror:** https://services2.arcgis.com/G5vR3cOjh6g2Ed8E/arcgis/rest/services/Planning/FeatureServer/25
- **Layer name / id:** Place Type / 25
- **Geometry:** Polygon
- **Key fields → targets:** `PlaceType` → flu; `PlaceTypeName` → fluLabel
- **Verified:** yes — count **10,288**; distinct types include ATH, CI, DT, EC, ER, GI, HC, IC, ME, MR, MUN, NS, PSN, RAR, RC, RE, ROS, SC, TOA, UPW
- **WKID / CRS:** 102719 / 2264 (extent spans Durham County)
- **Notes:** Durham Comprehensive Plan place-type map — treat as FLU for City + County planning area. Spatial join to parcels. **Not** Chapel Hill / Wake tip FLU.

### 6. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parno` → parcelId (aligns with Durham **PIN**, not REID)
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs
  - `gisacres` → acreage (~**4,934** in 5–150)
  - `saledate`,`saledatetx` → lastSale.date (**no sale price**)
  - `parval`,`landval`,`improvval` → tax
  - `cntyfips`=`063`, `cntyname` → Durham filter
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — filter count **133,075**; sample owner/mail/values OK
- **Notes:** Join to county parcels via PIN↔`parno`, then carry **REID**. May lag CAMA. MaxRecordCount **5000**.

### 7. Administrative — City of Durham boundary

- **Purpose:** other (municipality filter)
- **REST URL:** https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Administrative/MapServer/1
- **Field:** `LOCALGOV`
- **Verified:** yes — count **1**
- **Notes:** Route Durham City vs unincorporated. Tip cities: use parcel `CITY` / `ETJ` (DURHAM, CHAPEL HILL, RALEIGH, MORRISVILLE, CARY).

### 8. Future Growth Areas / Development Tiers (secondary planning)

- **Future Growth Areas:** https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Planning/MapServer/16 — count **8**; field `NAME`
- **Development Tiers:** https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Planning/MapServer/5 — count **14**; fields `NAME`,`TYPE` (URBAN, DOWNTOWN, CN, …)
- **Notes:** Supplementary to Place Type; not a substitute FLU.

## Municipalities (first-class)

County parcels are countywide; **zoning and FLU for tip cities are municipal**. Durham City + unincorporated share joint City–County Planning UDO + Place Type. Join pattern: start from Property Parcels (2264) → route by `CITY`/`ETJ` → spatial join matching zoning (and FLU when available).

Parcel `CITY` counts (all parcels): DURHAM **110,776**; null/unincorporated **20,272**; CHAPEL HILL **1,319**; RALEIGH **1,111**; MORRISVILLE **65**; CARY **2**; mixed labels rare.

### City of Durham (+ Durham County unincorporated UDO)

- **Zoning (joint City–County):** Planning/MapServer/12 — `ZONE_CODE`/`UDO_LABEL`/`ZONE_GEN`; count **2,525**; CRS **2264**
- **FLU — Place Type:** Planning/MapServer/25 — `PlaceType`/`PlaceTypeName`; count **10,288**; CRS **2264**
- **City boundary:** Administrative/MapServer/1
- **Join note:** spatial join zoning + Place Type to county parcels in 2264. Parcel `ZONING` often already populated for Durham City/County — still prefer polygon overlay when attribute null. Unincorporated uses same UDO (ETJ=`DURHAM COUNTY`).

### Town of Chapel Hill (Durham County tip; mostly Orange)

- **Zoning:** https://gis-portal.townofchapelhill.org/server/rest/services/OpenData/Zoning_Districts/FeatureServer/0 — `ZONING`,`NAME`; count **313**; CRS **2264**
- **MapServer twin:** …/OpenData/Zoning_Districts/MapServer/0
- **FLU:** https://gis-portal.townofchapelhill.org/server/rest/services/Future_Land_Uses/ImageServer — **raster only** (no queryable polygon FLU found) → **gap**
- **Join note:** filter Durham parcels with `CITY='CHAPEL HILL'` or `ETJ` like `CHAPEL-HILL` (~1.3k parcels; ~17 in 5–150 ac). Spatial join Chapel Hill zoning polygons (2264). Do **not** assume Durham Place Type / UDO zoning alone.

### Town of Morrisville (Durham tip; mostly Wake)

- **Zoning (Wake host):** https://maps.wake.gov/arcgis/rest/services/Planning/Zoning/MapServer/22 — `CLASS`,`COND_USE`; count **32**; CRS **2264**
- **Zoning (Raleigh regional host):** https://maps.raleighnc.gov/arcgis/rest/services/Planning/Zoning/MapServer/9 — `CLASS`; count **29**; CRS **2264**
- **FLU:** no public polygon FLU found for Morrisville tip in Durham → **gap**
- **Join note:** ~**65** Durham parcels with `CITY='MORRISVILLE'` (~3 in 5–150). Spatial join Morrisville zoning; parcel `ZONING` attrs mix Morrisville codes (e.g. HDR) and Durham-style labels — verify with polygons.

### City of Raleigh (Durham tip)

- **Zoning:** https://maps.raleighnc.gov/arcgis/rest/services/Planning/Zoning/MapServer/0 — `ZONING`,`ZONE_TYPE`,`ZONE_TYPE_DECODE`; count **3,592**; CRS **2264**
- **FLU:** no Durham-footprint FLU REST verified → **gap** (use Raleigh Comp Plan layers only if separately confirmed for this tip)
- **Join note:** ~**1,111** Durham parcels `CITY='RALEIGH'` (~7 in 5–150). Spatial join Raleigh Zoning; filter to Durham county parcels / `cntyfips=063`.

### Town of Cary (tiny Durham tip)

- **Zoning:** https://maps.raleighnc.gov/arcgis/rest/services/Planning/Zoning/MapServer/3 — count **2,736**; CRS **2264**
- **FLU:** gap
- **Join note:** only **2** Durham parcels — verify before investing in join pipeline.

## Gaps

- **Tip-municipality FLU** — Chapel Hill Future_Land_Uses is **ImageServer** (not queryable polygons); Morrisville / Raleigh / Cary tip FLU REST not verified for Durham footprint.
- **Parcel `ZONING` incomplete / tip-mixed** — ~5.2k null/empty; tip cities may carry foreign or annotated codes — spatial-join municipal zoning polygons.
- **PIN unstable** — Durham Tax Office: do not use PIN as parcel reference; use **REID** (Parcel ID). OneMap `parno` tracks PIN.
- **Last-sale only** — `PKG_SALE_*` / `LAND_SALE_*` on parcels; no multi-transfer public sales FeatureServer found.
- **CachedServices/Future_Land_Use** — tile cache only (no feature layers); use **Place Type** instead.
- **MaxRecordCount 2000** on county layers; OneMap 5000 — paginate.
- **Owner phones/emails** not collected (do not scrape taxcama / maps beyond public REST fields).
- **No paid vendor data** used (CoreLogic/Regrid/ATTOM/Spatialest avoided as primary sources; Spatialest URL exists but official CAMA is taxcama.dconc.gov).

## Hand-off notes for Land Search Builder

1. **Wire first:** `PublicServices/Property/MapServer/4` — polygons + REID, owner, mailing, situs, acreage, tax, last sale, CITY/ETJ, attribute ZONING. Filter `ACREAGE BETWEEN 5 AND 150` (~4.9k). Prefer `REID` as parcelId.
2. **Appraiser link:** `https://taxcama.dconc.gov/camapwa/PropertySummary.aspx?PARCELPK={PARCEL_PK}` or `?REID={REID}`. Viewer: https://maps.durhamnc.gov/
3. **Zoning:** For DURHAM CITY / DURHAM COUNTY → spatial join Planning Zoning `/12` (or trust non-null parcel `ZONING`). For CHAPEL HILL / MORRISVILLE / RALEIGH / CARY → spatial join that muni’s zoning layer; do not use Durham UDO alone.
4. **FLU:** spatial join Place Type `/25` for Durham planning area; leave null (or Chapel Hill ImageServer identify-only) for tips.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='063'`; map `parno`→PIN then resolve REID from county parcels.
6. **Join keys:** `REID` (preferred), `PARCEL_PK` (CAMA), cleaned `PIN`↔OneMap `parno` (unstable).
7. **Auth:** none observed on listed public query endpoints.
8. **Cities are first-class:** never treat Durham UDO zoning / Place Type as covering Chapel Hill / Morrisville / Raleigh / Cary tips.


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Property/MapServer/4 polygons load (sample centroid [-78.913, 36.0034]); `REID` filled on 133,548 of 133,548; `ACREAGE` 5–150 ac **4,940**.
- **Attribute layer for Pass 2:** https://webgis2.durhamnc.gov/server/rest/services/PublicServices/Property/MapServer/4 · id `REID` · live count **133,548** · 5–150 ac **4,940** (`ACREAGE >= 5 AND ACREAGE <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='DURHAM'` gives **946** stations (111 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27DURHAM%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Durham'` gives **954** stations (867 with AADT_2025, 189 with AADT_2024, 872 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Durham%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `TOTAL_PROP_VALUE` non-zero **131,203**, `TOTAL_LAND_VALUE_ASSESSED` non-zero **126,888**
- **Sale history (ok):** price `PKG_SALE_PRICE` >0 **56,637**; date `PKG_SALE_DATE` non-null **69,913**
- **Owner entity:** field `PROPERTY_OWNER`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **2,441** (all parcels: 33,569), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://taxcama.dconc.gov/camapwa/PropertySummary.aspx?REID={REID}`. Tested `100805` (https://taxcama.dconc.gov/camapwa/PropertySummary.aspx?REID=100805) → HTTP **200** (text/html; charset=utf-8), content verified: True. Server-rendered CAMA PropertySummary; owner and REID verified.
- **Jurisdiction GIS viewer:** https://maps.durhamnc.gov/ → HTTP **200** (Durham Maps | City of Durham and Durham County)
- **Municipal zoning/FLU layers re-checked:** 10 of 11 answer. Not answering: https://maps.wake.gov/arcgis/rest/services/Planning/Zoning/MapServer/22. maps.wake.gov Planning/Zoning/MapServer/22 (Morrisville): https TLS EOF from this box, plain http answers (count 32). Morrisville is also on maps.raleighnc.gov Zoning/MapServer/9 (29).
- **Pass 2 gaps:** none
