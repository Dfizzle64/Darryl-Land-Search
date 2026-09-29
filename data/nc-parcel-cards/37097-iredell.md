# Iredell County, NC — GIS County Card

## Summary

Iredell County (Charlotte MSA; Statesville / Mooresville / Lake Norman north) publishes a strong **public** ArcGIS REST stack on `maps.iredellcountync.gov`: countywide **TaxSQL_Parcels** polygons with ownership, mailing, situs parts, tax acres, assessed land/building/total values, last sale (date/price/qualified), parcel-attributed zoning, and tax account id. Authoritative **municipal zoning/FLU are first-class**: Mooresville publishes its own Town Zoning + FCLU on `gis.mooresvillenc.gov`; Statesville/Troutman/Harmony/Love Valley/Davidson-in-Iredell zoning is on the county Zoning MapServer as separate city layers (not optional). County **Horizon Plan 2030** is FLU for unincorporated land (municipal MPAs are stubs — use Mooresville FCLU inside Mooresville). A **Sales_2024** MapServer extracts 2024 sales as polygons. NC OneMap statewide parcels (`cntyfips=097`) are a solid fallback. Public MapGeo viewer and taxweb Property Access provide appraiser/viewer UX. Main gaps: no multi-year sale-history table (last sale + single-year 2024 extract only), `Market` is an adjustment **factor** not market value, town FLU detail missing, and no stable taxweb deep-link (search form only).

## Portals

- **Iredell County GIS Mapping** — https://iredellcountync.gov/554/GIS-Mapping — County GIS index (MapGeo, downloads, PDF maps).
- **MapGeo (tax / zoning map)** — https://iredellcountync.mapgeo.io/ — Interactive parcels/zoning/flood. Query UX: `https://iredellcountync.mapgeo.io/datasets/properties?query={PIN}` (strip trailing `.000` from REST `PIN` if needed).
- **Tax Administration Property Access** — https://taxweb.iredellcountync.gov/PublicAccess/BasicSearch.aspx — Owner / PIN / address / sales / zoning search; Property Record Card links from results.
- **Real Estate Search** — https://taxweb.iredellcountync.gov/PublicAccess/RealEstate.aspx — Advanced real-estate criteria (PIN parts, zoning, land size).
- **County Assessor Division** — https://www.iredellcountync.gov/390/County-Assessor-Division
- **maps.iredellcountync.gov ArcGIS REST** — https://maps.iredellcountync.gov/server/rest/services — Primary host (Data/, Tax/, Planning/). Prefer over legacy `icgis.co.iredell.nc.us` (MaxRecordCount 1000 vs 2000).
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels FeatureServer (`services.nconemap.gov` / `services.gis.nc.gov`).

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `ACCOUNT` (county); `parno` (NC OneMap) | REST `PIN` often `##########.###` (e.g. `4751155000.000`); strip `.000` for MapGeo/taxweb search |
| polygons | Yes | TaxSQL_Parcels | CRS **WKID 102719 / 2264** (NC State Plane ft) |
| acreage | Yes | `TaxAcres` / OneMap `gisacres` | ~**10,768** parcels in 5–150 ac on TaxSQL; OneMap ~10,771 |
| ownerName | Yes | `Jan1Own1`+`Jan1Own2`; display `Name` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `ADD1`,`ADD2`,`ADD3`,`CITY`,`STATE`,`ZIP` / OneMap `mailadd` | `CITY` is mailing city (can be out-of-county) |
| situs address | Yes (partial city) | `HouseNumber`+`SDIR`+`STREET`+`STYPE`(+`ST_SUFFIX`); `CityLocationDescription` for situs juris | No dedicated situs city/ZIP fields; mailing `CITY` ≠ always situs |
| lastSale date/price | Yes | `Sale_Date`,`Sales_Price`,`QualifiedCode`,`Sale_Is_Improved` | Last sale on parcel; `Q` = qualified. Enrich with Sales_2024 for that tax year |
| tax values | Yes (assessed) | `Land_Value`,`Bldg_Value`,`OBXF_Value`,`Total_Value` | **`Market` is a factor (e.g. 1.1), not market $** — treat as gap for `tax.marketValue` |
| zoning | Yes | Parcel `Zoning`; polygon `ZONING`/`ZDISPLAY` on Zoning MapServer layers | Parcel attr ~98% filled; use polygon layers for authority / overlays (CUD/PRD) |
| FLU | Yes (partial) | Horizon Plan `FUTURE_LANDUSE` | County plan; town MPAs are stubs — no detailed Mooresville/Statesville FLU here |
| appraiser / viewer link | Yes (search) | MapGeo query URL; taxweb BasicSearch | No verified stable `/pid/{id}` deep-link on taxweb |

## Layers (verified)

### 1. TaxSQL_Parcels — parcels + ownership + tax + last sale + zoning attr (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | zoning (attr)
- **REST URL:** https://maps.iredellcountync.gov/server/rest/services/Data/TaxSQL_Parcels/FeatureServer/0
- **Alternate (MapServer):** https://maps.iredellcountync.gov/server/rest/services/Data/TaxSQL_Parcels/MapServer/0
- **Legacy host:** https://icgis.co.iredell.nc.us/arcgis/rest/services/Data/TaxSQL_Parcels/FeatureServer/0 (MaxRecordCount **1000** — prefer maps host)
- **Layer name / id:** TaxSQL_Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId
  - `ACCOUNT` → tax account / alternate id
  - `TaxAcres` → acreage
  - `Jan1Own1`, `Jan1Own2`, `Name` → ownerName
  - `ADD1`, `ADD2`, `ADD3`, `CITY`, `STATE`, `ZIP` → mailingAddress
  - `HouseNumber`, `SDIR`, `STREET`, `STYPE`, `ST_SUFFIX` → situsAddress
  - `CityLocationCode`, `CityLocationDescription` → situs jurisdiction hint
  - `Sale_Date`, `Sales_Price`, `QualifiedCode`, `Sale_Is_Improved`, `Sale_Yr` → lastSale
  - `Land_Value`, `Bldg_Value`, `OBXF_Value`, `Def_Value`, `Total_Value` → tax (assessed)
  - `Zoning` → zoning (parcel attribute)
  - `Land_Use_Code`, `Building_Use`, `Township`, `DWBook`, `DWPage`, `DeedDate` → other
- **WKID / CRS:** 102719 (latest 2264)
- **Verified:** yes — `returnCountOnly` → **110,201**; `TaxAcres BETWEEN 5 AND 150` → **10,768**; sample returned owner/mail/situs parts/sale/tax/zoning
- **Notes:** Best single county layer for land-search attribute upgrade. MaxRecordCount **2000** — paginate. Do not treat `Market` as dollar market value.

### 2. Data/Zoning — Iredell County zoning (unincorporated)

- **Purpose:** zoning
- **REST URL:** https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/0
- **Layer name / id:** Iredell Zoning / 0
- **Geometry:** Polygon
- **Key fields → targets:** `ZONING`, `ZDISPLAY` → zoning; `JURISDIC`; `CUD`, `PRD`, `CASE_`; `Code_MUNIS`, `Descript_MUNIS`
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **961**
- **Notes:** County / unincorporated. Combine with town layers 1–6 for countywide coverage.

### 3. Data/Zoning — Statesville Zoning

- **Purpose:** zoning
- **REST URL:** https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/1
- **Layer name / id:** Statesville Zoning / 1
- **Geometry:** Polygon
- **Key fields → targets:** `ZONING`, `ZDISPLAY`, `JURISDIC`, `CUD`, `PRD`
- **Verified:** yes — count **363**

### 4. Data/Zoning — Troutman Zoning

- **Purpose:** zoning
- **REST URL:** https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/2
- **Layer name / id:** Troutman Zoning / 2
- **Geometry:** Polygon
- **Key fields → targets:** `ZONING`, `ZDISPLAY`, `JURISDIC`
- **Verified:** yes — count **200**

### 5. Data/Zoning — Mooresville Zoning

- **Purpose:** zoning
- **REST URL:** https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/3
- **Layer name / id:** Mooresville Zoning / 3
- **Geometry:** Polygon
- **Key fields → targets:** `ZONING`, `ZDISPLAY`, `JURISDIC`, `Conditions`
- **Verified:** yes — count **590**
- **Notes:** Largest town zoning set; sample `JURISDIC=MOORESVILLE`.

### 6. Data/Zoning — Harmony / Love Valley / Davidson (Iredell portion)

- **Purpose:** zoning
- **REST URLs:**
  - Harmony: https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/4 — count **14**
  - Love Valley: …/MapServer/5 — count **3**
  - Davidson (Iredell portion): …/MapServer/6 — count **3**
- **Geometry:** Polygon
- **Key fields → targets:** `ZONING`, `ZDISPLAY`, `JURISDIC`
- **Verified:** yes — counts above
- **Notes:** Small footprints; still required for complete municipal coverage.

### 7. Iredell Landuse Horizon Plan 2030 — FLU

- **Purpose:** FLU
- **REST URL:** https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/7
- **Layer name / id:** Iredell Landuse Horizon Plan 2030 / 7
- **Geometry:** Polygon
- **Key fields → targets:** `FUTURE_LANDUSE` → flu; `CASE_NO`, `DATE_CHANGED`
- **Verified:** yes — count **219**; distinct values include Agricultural Residential, Low/Medium/High-Density Residential, Employment Center types, Rural Conservation/Industrial/Commercial, Open Space/Park, plus municipal stubs (Statesville / Mooresville / Troutman / Harmony / Love Valley / Davidson Municipal Planning Area)
- **Notes:** Spatial-join to parcels. Town “Municipal Planning Area” polygons are **stubs** — detailed city FLU not on this service.

### 8. Tax/Sales_2024 — sales extract (year snapshot)

- **Purpose:** sales
- **REST URL:** https://maps.iredellcountync.gov/server/rest/services/Tax/Sales_2024/MapServer/0
- **Layer name / id:** Sales 2024 / 0
- **Geometry:** Polygon
- **Key fields → targets:** Same CAMA-style schema as TaxSQL_Parcels (`PIN`, `Sale_Date`, `Sales_Price`, `QualifiedCode`, owner/tax/zoning, etc.)
- **Verified:** yes — count **6,343** (all `Sale_Yr=2024` in spot check)
- **Notes:** Not a full multi-year history table. Use for 2024 comps; keep TaxSQL `Sale_Date`/`Sales_Price` as lastSale. Expect annual service renames/replacements.

### 9. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (last) | other
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1 *(layer 0 = points)*
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parno` → parcelId
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs
  - `gisacres` → acreage
  - `saledate`,`saledatetx` → lastSale date
  - `parval`,`landval`,`improvval` → tax values
  - `cntyfips`=`097`, `cntyname` → Iredell filter
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — `cntyfips='097'` count **109,254**; 5–150 ac **10,771**
- **Notes:** Excellent fallback / cross-county schema. May lag county CAMA. Prefer TaxSQL_Parcels when up. MaxRecordCount 5000.

### 10. Related / secondary (verified existence; optional)

- **Archived_Parcels** FeatureServer — yearly historic parcel snapshots 2002–2023: https://maps.iredellcountync.gov/server/rest/services/Data/Archived_Parcels/FeatureServer — not for current CAMA.
- **Farmland Districts / Buffer / Urban Study Areas** — Zoning MapServer layers 8–10 (counts 334 / 30 / 4) — planning overlays, not core schema.
- **Planning/Development_Activity_Countywide** — subdivision / project activity polygons (not ownership CAMA).


## Municipalities (first-class)

County **TaxSQL_Parcels** cover **all** of Iredell (incorporated + unincorporated) for ownership/tax/sale/acreage. **Zoning and FLU inside cities/towns are municipal authority** — do not assume county Horizon Plan or county Zoning/0 alone. Join pattern for every town below:

- **Parcels (county-wide):** `TaxSQL_Parcels` on `PIN` / geometry
- **Zoning/FLU (city-only):** municipal or county-hosted town layer → **spatial join** to parcel polygons
- **CRS:** all verified layers use **WKID 102719 / latest 2264** (NAD 1983 StatePlane NC Feet) — no reproject needed among county + Mooresville hosts
- **Attribute shortcut:** parcel `Zoning` is often filled (~98%) but prefer authoritative town polygon layers for CUD/overlays/case numbers
- **CityLimits helper:** https://maps.iredellcountync.gov/server/rest/services/Data/CityLimits/FeatureServer/0 — `NAME` in {STATESVILLE, MOORESVILLE, TROUTMAN, HARMONY, LOVE VALLEY, DAVIDSON}

### Mooresville (own GIS — preferred for town zoning + FLU)

- **Portal / REST root:** https://gis.mooresvillenc.gov/gisadmin/rest/services
- **Town Zoning (PRIMARY town):** https://gis.mooresvillenc.gov/gisadmin/rest/services/PlanningServices/MapServer/1  
  - Alternate duplicate: https://gis.mooresvillenc.gov/gisadmin/rest/services/ZoningMap/MooresvilleZoning/FeatureServer/3  
  - Fields: `ZDISPLAY` → zoning; `ZoningTax` → zoning (tax/CAMA code); `CaseNumber`, `ApprovalDate`, `OLDZONING`  
  - Verified count: **594** (vs county-hosted Mooresville Zoning layer count 590 — prefer town host)
- **Future Character / FCLU (FLU):**  
  - https://gis.mooresvillenc.gov/gisadmin/rest/services/Planning/FCLU/FeatureServer/0  
  - Same geometry also on PlanningServices/MapServer/25 (`Future Character`)  
  - Field: `F2019_LU_1` → flu (codes observed: DTC, DTE, EMC, FDCR, IND, MUC, MUD, MVIL, NRES, PRES, RRES, TR)  
  - Verified count: **15**
- **MooresvilleTomorrow (plan character overlays):** https://gis.mooresvillenc.gov/gisadmin/rest/services/Planning/MooresvilleTomorrow/MapServer — Intentional Growth Areas / CDM Activity Centers / **Conservation and Development** (`Name` e.g. Active Open Space, Single-Lot Residential) / Development Change and Intensity — secondary to FCLU
- **ETJ / limits:** TownETJ, Planning/MooresvilleTownLimits
- **Join note:** city-only zoning/FLU + county parcels; spatial join in 2264; optional filter parcels with `CityLocationDescription` / CityLimits `NAME='MOORESVILLE'` or `CityTaxDescription`

### Statesville

- **Independent city GIS REST:** **not found** (no public `gis.statesvillenc.*` FeatureServer verified this pass). Planning site points to Iredell County interactive zoning map.
- **Zoning (county-hosted, city jurisdiction):** https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/1 — `ZONING`/`ZDISPLAY`/`JURISDIC`; count **363**
- **FLU:** Statesville Land Development Plan **2045** is adopted as PDF/plan docs (https://www.statesvillenc.net/2021/09/28/8620/statesville-land-development-plan-2045) — **no public FLU FeatureServer verified** → gap for city FLU
- **Join note:** city-only zoning polygons + county TaxSQL parcels (spatial, 2264)

### Troutman

- **Independent town GIS REST:** **not found**
- **Zoning (county-hosted):** https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/2 — count **200**; fields `ZONING`/`ZDISPLAY`/`JURISDIC`
- **FLU:** no town FLU REST; Horizon Plan stubs “Troutman Municipal Planning Area” only → gap
- **Join note:** city-only zoning + county parcels (spatial, 2264)

### Harmony

- **Zoning (county-hosted):** https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/4 — count **14**
- **FLU:** gap (Horizon stub only)
- **Join note:** city-only zoning + county parcels

### Love Valley

- **Zoning (county-hosted):** https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/5 — count **3**
- **FLU:** gap (Horizon stub only)
- **Join note:** city-only zoning + county parcels

### Davidson (Iredell portion)

- Town straddles **Mecklenburg + Iredell**. Davidson GIS page points to Mecklenburg POLARIS / Open Mapping and Iredell MapGeo — **no standalone Davidson FeatureServer** verified.
- **Iredell-hosted Davidson Zoning tip:** https://maps.iredellcountync.gov/server/rest/services/Data/Zoning/MapServer/6 — count **3** only (Iredell footprint)
- **Mecklenburg town zoning (Davidson Planning Areas / zones):** https://meckgis.mecklenburgcountync.gov/server/rest/services/UnincorporatedCountyandTownsZoning/MapServer/0 filter `munic='DAVIDSON'` — count **76** (mostly Mecklenburg side; `zone_des`)
- **Parcels in Iredell tip:** still Iredell TaxSQL_Parcels; for Mecklenburg-side Davidson use Mecklenburg CAMA (see 37119 card)
- **FLU:** Davidson uses Planning Areas (zoning-equivalent); detailed Iredell-side FLU REST not verified → gap for Iredell tip
- **Join note:** Iredell parcels ↔ Iredell Zoning/6; do not assume Mecklenburg zoning polygons cover Iredell PIN parcels without a spatial test

## Gaps

- **No multi-year sale history FeatureServer** — only last-sale fields on TaxSQL_Parcels plus a single-year `Sales_2024` extract (expect yearly churn).
- **`Market` field is not market value ($)** — it is a numeric adjustment factor; no public dollar `tax.marketValue` observed on TaxSQL.
- **Situs city/ZIP incomplete** — assemble street from parts; mailing `CITY` may be out-of-county; use `CityLocationDescription` cautiously.
- **Zoning is split across 7 polygon layers** — parcel `Zoning` attr is convenient but may lag case/CUD detail; spatial-join polygons for authority.
- **Municipal FLU uneven:** Mooresville has public FCLU/Future Character REST; **Statesville / Troutman / Harmony / Love Valley / Davidson (Iredell tip) lack verified public FLU FeatureServers** (Statesville LDP 2045 is PDF-only this pass). County Horizon Plan stubs town MPAs — not a substitute for city FLU.
- **Statesville / Troutman / small towns lack independent GIS hosts** — zoning is county-hosted town layers (still first-class jurisdictionally; not “optional”). Prefer Mooresville’s own `gis.mooresvillenc.gov` Town Zoning over county mirror when both exist.
- **No verified stable taxweb deep-link** — BasicSearch / RealEstate are form-driven; MapGeo `?query={PIN}` is the practical viewer wire.
- **PIN formatting** — REST values often include trailing `.000`; normalize before joining to OneMap / MapGeo.
- **Owner phones/emails** not on these APIs (correct — do not scrape).
- **MaxRecordCount 2000** on maps host — pagination required; avoid legacy icgis (1000) for bulk pulls.
- **No paid vendor data** used or required.

## Hand-off notes for Land Search Builder

1. **Wire first:** `Data/TaxSQL_Parcels/FeatureServer/0` for polygons + attributes. Filter `TaxAcres BETWEEN 5 AND 150` (~10.8k features).
2. **Normalize PIN:** strip trailing `.000` for display / MapGeo / taxweb search; keep raw for REST equality if needed.
3. **Zoning:** treat municipalities as first-class — Mooresville Town Zoning (`gis.mooresvillenc.gov` PlanningServices/1); Statesville/Troutman/Harmony/Love Valley/Davidson from county Zoning MapServer 1–6; county Zoning/0 for unincorporated. Parcel `Zoning` is a fast filter only.
4. **FLU:** Mooresville → FCLU `F2019_LU_1`; unincorporated → Horizon Plan Zoning/7; other towns → FLU gap (do not invent from Horizon MPA stubs).
5. **Sales:** lastSale from TaxSQL; optional 2024 comps from `Tax/Sales_2024/MapServer/0` on `PIN`.
6. **Fallback:** NC OneMap layer 1 with `cntyfips='097'` if county host is down.
7. **Viewer link template:** `https://iredellcountync.mapgeo.io/datasets/properties?query={PIN}` plus taxweb search `https://taxweb.iredellcountync.gov/PublicAccess/BasicSearch.aspx`
8. **Join keys:** `PIN` primary; `ACCOUNT` secondary; OneMap `parno` needs PIN-format validation.
9. **Auth:** None observed on listed public query endpoints (`f=json`). Be polite with pagination.
10. **Tax dollars:** map `Land_Value`/`Bldg_Value`/`Total_Value` → assessed; leave `tax.marketValue` null/unknown unless a later source appears.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://maps.iredellcountync.gov/server/rest/services/Data/TaxSQL_Parcels/FeatureServer/0 · id `PIN` · live count **110,203** · 5–150 ac **10,768** (`TaxAcres >= 5 AND TaxAcres <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='IREDELL'` gives **819** stations (358 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27IREDELL%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Iredell'` gives **826** stations (491 with AADT_2025, 514 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Iredell%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Iredell'` gives **826** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `Total_Value` non-zero **107,802**, `Land_Value` non-zero **107,712**
- **Sale history (ok):** price `Sales_Price` >0 **83,028**; date `Sale_Date` non-null **107,921**
- **Owner entity:** fields `Jan1Own1`, `Jan1Own2`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **2,638** of 10,768 (extended regex: 2,921).
- **PA deep link:** `https://iredellcountync.mapgeo.io/datasets/properties?query={PIN}`. Tested `4851140068.000` → HTTP **200** (text/html), content verified: False. MapGeo SPA returns 200 shell; parcel resolves client-side (unverified). taxweb RealEstate.aspx?PIN= did not resolve the owner — no durable GET on PublicAccess.
- **Jurisdiction GIS viewer:** https://iredellcountync.mapgeo.io/ → HTTP **200** (MapGeo)
- **Pass 2 gaps:** No durable GET PA deep link — MapGeo SPA (?query={PIN}) unverified; taxweb PublicAccess requires search session; PIN trailing .000 normalization
