# New Hanover County, NC — GIS County Card

## Summary

New Hanover County (Wilmington MSA, FIPS **37129**) publishes public ArcGIS REST at `gis.nhcgov.com`: countywide **tax parcel polygons** (`Layers/Parcels` / `Layers/IASTAX` layer 0, ~**103,967**) with GIS `ACRES`, plus a related **IASTAX attribute table** and **PropertyOwners** points carrying ownership, mailing, situs, assessed values, last sale, CAMA `ZONING`, and `MUNI`. ~**2,286** polygons have `ACRES` 5–150 (~**1,247** with `APRBLDG=0` in that range on the IASTAX table). **Zoning is municipality-first**: county `Layers/Zoning` covers unincorporated (with `CITY`/`WB`/`CB` punch-outs); City of Wilmington, Carolina Beach, and Wrightsville Beach publish their own zoning REST; **Kure Beach has no public zoning FeatureServer** (attribute `ZONING` on CAMA only). **FLU**: PlanNHC Place Types for unincorporated; Wilmington public layer is **existing** land use (not Create Wilmington Growth Strategies FLU — portfolio app only). **NC OneMap** (`cntyfips='129'`) is a solid fallback (~103.5k / ~2,281 in 5–150). Prefer most-local zoning/FLU joined onto county parcels.

## Portals

- **NHC GIS / Maps & Data** — https://www.nhcgov.com/844/GIS-Maps-Data
- **More Maps (parcel & thematic viewers)** — https://www.nhcgov.com/896/More-Maps
- **NHC ArcGIS REST** — https://gis.nhcgov.com/server/rest/services — Primary
- **NHC ArcGIS Portal** — https://gis.nhcgov.com/portal/home/
- **Parcel web app** — https://nhcgov.maps.arcgis.com/apps/webappviewer/index.html?id=bf12527f385b4d2e8420d892863b31dd
- **eTax / Property search** — https://etax.nhcgov.com/ — Parcel ID search (accept disclaimer): `https://etax.nhcgov.com/pt/search/commonsearch.aspx?mode=parid`
- **City of Wilmington GIS REST** — https://gis.wilmingtonnc.gov/arcgis/rest/services — Zoning + LandUse + ParcelOwners
- **Create Wilmington Growth Strategies (FLU-ish app, not FS)** — https://wilmingtonnc.maps.arcgis.com/apps/instant/portfolio/index.html?appid=b473d4b465d8439f8346aa132f435553
- **Carolina Beach GIS** — https://cw.carolinabeach.org/arcgis/rest/services — `GISViewer/CB_Parcels` + `GIS_Viewer` Zoning
- **Carolina Beach GIS page** — https://www.carolinabeach.org/175/Maps-GIS
- **Wrightsville Beach Zoning (AGOL)** — https://services3.arcgis.com/XyPkMiF0OxEhc77I/arcgis/rest/services/WrightsvilleBeachZoning/FeatureServer
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PID`/`PARID`; `PIN`/`MAPID`; OneMap `parno` | Prefer `PARID`/`PID` (eTax key); `MAPIDKEY` join key |
| polygons | Yes | Layers/Parcels FS/0 or IASTAX FS/0 | CRS **WKID 103122 / 6543** |
| acreage | Yes | `ACRES` (polygon); OneMap `gisacres` | ~**2,286** ACRES 5–150; OneMap ~**2,281** |
| ownerName | Yes | IASTAX/PropertyOwners `OWN1` / OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `OWNER_NUM`+`OWNER_STREET`+`OWNER_STREETTYPE`, `OWNER_CITY`/`STATE`/`ZIP`; or `OWNER_ADDR1–3` | ADDR lines often null — build from parts |
| situs address | Yes | `ADRNO`+`ADRSTR`+`ADRSUF`+`ADRDIR`, `CITYNAME` | On ownership table/points; not on bare Parcels polys |
| lastSale date/price | Yes | `SALE_DATE`, `SALE_PRICE` | Last sale only; price often `0` / non-qualified |
| tax values | Yes | `APRLAND`, `APRBLDG`, `APRTOT` / OneMap `landval`,`improvval`,`parval` | Assessed (IAS World); no separate market field |
| zoning | Yes (split) | CAMA `ZONING` + municipal polygon layers | Route by `MUNI`; spatial join for authoritative district polys |
| flu | Partial | PlanNHC `PlaceType`; Wilmington `LandUse` (existing) | City FLU / beach FLU = gap or app/PDF |
| appraiser / viewer link | Yes | eTax by PARID; NHC parcel web app | Templates below |

### MUNI codes (IASTAX / PropertyOwners → zoning router)

| Code | Jurisdiction | Notes |
|------|----------------|-------|
| FD | New Hanover unincorporated | Largest 5–150 count (~1,550); postal city often Wilmington |
| WM | City of Wilmington | ~684 in 5–150 |
| CB | Carolina Beach | ~17 in 5–150 |
| WB | Wrightsville Beach | ~13 in 5–150 |
| KB | Kure Beach | ~3 in 5–150 |
| BD | Wilmington (downtown/condo-style accounts) | Rare; treat zoning as Wilmington |
| NULL | Unknown / unset | Rare |

Corporate limits also on `Layers/MuniLimits` (`CITY`, `JURIS`: WM/CB/WB/KB/NHC).

## Layers (verified)

### 1. Layers/Parcels + IASTAX polygons — cadastral geometry (PRIMARY geometry)

- **Purpose:** parcels | acreage
- **REST URL:** https://gis.nhcgov.com/server/rest/services/Layers/Parcels/FeatureServer/0
- **IASTAX mirror:** https://gis.nhcgov.com/server/rest/services/Layers/IASTAX/FeatureServer/0 (`Parcel_Polygon`) — same count/fields
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PID` → parcelId (aligns with IASTAX `PARID`)
  - `PIN`, `MAPID` → NC map id / PIN
  - `MAPIDKEY` → join key to IASTAX table / PropertyOwners
  - `ACRES` → acreage
- **WKID / CRS:** 103122 / 6543 (NAD 1983 (2011) StatePlane NC ft)
- **Verified:** yes — count **103,967**; `ACRES BETWEEN 5 AND 150` → **2,286**
- **Notes:** Geometry + acres only (no owner). Service description on MapServer notes parcels alone do not convey owner info. **Join** to IASTAX table or PropertyOwners on `MAPIDKEY` (or `PID`=`PARID`). MaxRecordCount **10000**.

### 2. Layers/IASTAX table — ownership + tax + situs + sale + CAMA zoning (PRIMARY attributes)

- **Purpose:** tax | ownership | sales (last) | situs | zoning (attribute)
- **REST URL:** https://gis.nhcgov.com/server/rest/services/Layers/IASTAX/FeatureServer/1
- **Layer name / id:** IASTAX / 1 (Table — no geometry)
- **Geometry:** none
- **Key fields → targets:**
  - `PARID` → parcelId
  - `MAPID`, `MAPIDKEY` → join to polygons
  - `OWN1` → ownerName
  - `OWNER_NUM`,`OWNER_STREET`,`OWNER_STREETTYPE`,`OWNER_DIR`,`OWNER_UNITNO` + `OWNER_CITY`,`OWNER_STATE`,`OWNER_ZIP` → mailing (prefer over often-null `OWNER_ADDR1–3`)
  - `ADRNO`,`ADRADD`,`ADRSTR`,`ADRSUF`,`ADRDIR`,`CITYNAME` → situs
  - `ACRES` → acreage (table; prefer polygon `ACRES` for GIS acres)
  - `SALE_DATE`, `SALE_PRICE` → lastSale
  - `APRLAND`, `APRBLDG`, `APRTOT`, `OBYVAL` → tax
  - `ZONING` → zoning (CAMA; jurisdiction-specific codes)
  - `MUNI` → zoning/FLU router
  - `LUC`, `CLASS` → dorCode / land-use class
- **Verified:** yes — count **115,876**; `ACRES BETWEEN 5 AND 150` → **2,285**; `APRBLDG=0` in 5–150 → **1,247**; join `MAPIDKEY` poly→table verified
- **Notes:** More rows than polygons (multi-interest / condos). Deduplicate by `PARID`/`MAPIDKEY` for site search. MaxRecordCount **10000**. REST relationships array empty — **manual attribute join**.

### 3. Layers/PropertyOwners — ownership points (attribute alternate)

- **Purpose:** tax | ownership | sales | situs | zoning (attribute)
- **REST URL:** https://gis.nhcgov.com/server/rest/services/Layers/PropertyOwners/FeatureServer/0
- **Geometry:** Point (parsed from MAPID/ALTID)
- **Fields:** same CAMA schema as IASTAX table (`OWN1`, mailing parts, situs, `ACRES`, `ZONING`, `MUNI`, `APR*`, `SALE_*`)
- **Verified:** yes — count **115,876**; `ACRES` 5–150 → **2,285**
- **Notes:** Good for identify/popups; for outlines join to Parcels polygons on `MAPIDKEY`. MaxRecordCount **2000**.

### 4. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parno` → parcelId (aligns with `PIN` / map id)
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs
  - `gisacres` → acreage (~**2,281** in 5–150)
  - `saledate`,`saledatetx` → lastSale.date (**no sale price**)
  - `parval`,`landval`,`improvval` → tax
  - `cntyfips`=`129`, `cntyname` → New Hanover filter
- **WKID / CRS:** 102719 / 2264 (OneMap statewide; reproject vs county 6543)
- **Verified:** yes — filter count **103,489**; sample owner/mail/site/values OK
- **Notes:** Excellent fallback. May lag county CAMA. MaxRecordCount **5000**.

### 5. Layers/Zoning — county zoning polygons (unincorporated PRIMARY)

- **Purpose:** zoning
- **REST URL:** https://gis.nhcgov.com/server/rest/services/Layers/Zoning/FeatureServer/1
- **Also:** MapServer/1; `Zoning_base` FeatureServer/3 (same schema/count); PlanNHC_Zoning/2; LandDevChar/12
- **Conditional zoning:** FeatureServer/0 (cases / CZD)
- **Geometry:** Polygon
- **Key fields:** `ZONING`, `ZONINGTXT`, `CDFLAG`, `CDCASE`, `WEBSITE`, `SUP`
- **Verified:** yes — count **1,832**; distinct districts include R-5/7/10/15/20, B-1/B-2, I-1/I-2, AR, RA, PD, RFMU, UMXZ, EDZD, plus placeholders **`CITY`**, **`WB`**, **`CB`**
- **WKID / CRS:** 103122 / 6543
- **Join:** spatial join to parcels in 6543; **do not** use as countywide coverage inside municipalities
- **Notes:** Website points to NHC Current Planning. MaxRecordCount **1000**.

### 6. Thematic/PlanNHC_FLUM — PlanNHC Place Types (unincorporated FLU)

- **Purpose:** flu
- **REST URL:** https://gis.nhcgov.com/server/rest/services/Thematic/PlanNHC_FLUM/FeatureServer/8
- **Layer name / id:** Place Types / 8
- **Geometry:** Polygon
- **Key fields:** `PlaceType` → flu (GENERAL RESIDENTIAL, RURAL RESIDENTIAL, COMMUNITY MIXED USE, URBAN MIXED USE, COMMERCE ZONE, EMPLOYMENT CENTER, CONSERVATION, …); `Acres`; `URL` (PDF sheet name)
- **Related:** Growth Nodes /0 (3), MU nodes /4–6; roads layers not FLU
- **Verified:** yes — Place Types count **88**; distinct PlaceType labels verified
- **Notes:** Unincorporated PlanNHC comprehensive plan — **not** a substitute for Wilmington Create Wilmington Growth Strategies.

### 7. Layers/MuniLimits — municipal boundaries

- **Purpose:** other (municipality filter)
- **REST URL:** https://gis.nhcgov.com/server/rest/services/Layers/MuniLimits/FeatureServer/0
- **Fields:** `CITY`, `JURIS`, `POSTAL`
- **Verified:** yes — WILMINGTON/WM, CAROLINA BEACH/CB, WRIGHTSVILLE BEACH/WB, KURE BEACH/KB, UNINCORPORATED/NHC
- **Notes:** Route zoning/FLU with parcel `MUNI` and/or spatial intersect.

### 8. Layers/Landuse2014 + CAMALandUse — legacy / CAMA land classes (not FLU)

- **LandUse2014:** https://gis.nhcgov.com/server/rest/services/Layers/Landuse2014/FeatureServer/0 — `LANDUSE`,`LUCLASS`,`LUCODE`; count **119** (aggregated 2014)
- **CAMALandUse:** https://gis.nhcgov.com/server/rest/services/Thematic/CAMALandUse/FeatureServer/3 — `camaclass`,`CL_LABEL`; count **2,600**
- **Notes:** Existing/CAMA classification — use PlanNHC Place Types for future policy in unincorporated areas.

### 9. Thematic/TaxPublic — eTax map support

- **REST URL:** https://gis.nhcgov.com/server/rest/services/Thematic/TaxPublic/MapServer
- **Layers:** Addressing (2), Parcels (3)
- **Notes:** Backs public tax viewer; prefer FeatureServers above for queries.

## Municipalities (first-class)

County parcels are countywide; **zoning polygons and FLU are municipal** (except PlanNHC for unincorporated). Join pattern: start from county Parcels/IASTAX (6543) → filter/route by `MUNI` → spatial join matching city zoning (and FLU when available). Prefer municipal hosts for CRS match where noted.

### City of Wilmington

- **Zoning (city host — PRIMARY for WM):** https://gis.wilmingtonnc.gov/arcgis/rest/services/Planning/Zoning/FeatureServer/0 — `Zoning` (CB, CBD, CS, HD, HDMU, HDR, IND, LI, MD-10/17, MF-H, MH, MX, O&I, R-3/5/7/10/15/20, RB, RO, UMX, …); count **328** dissolved; CRS **6543**; also layers 1 Zoning Cases, 2 Historic District Overlay
- **Existing land use (not FLU):** https://gis.wilmingtonnc.gov/arcgis/rest/services/Planning/LandUse/MapServer/0 — `LandUse` (Single Family, Vacant, Commercial, …); count **44,000**; parcel-attributed; CRS **6543**
- **Create Wilmington Growth Strategies:** Instant portfolio app only (no verified public FeatureServer for FLU/place types) — **FLU gap for REST**
- **City ParcelOwners (enrichment):** https://gis.wilmingtonnc.gov/arcgis/rest/services/BaseLayers/ParcelOwners/FeatureServer/0 — polygons + CAMA-like attrs countywide (~115.9k); **multi-owner rows** per PID; acreage via `Shape__Area`/43560 (inflated vs county `ACRES` 5–150 counts) — prefer county ACRES for site filters
- **City Parcels:** https://gis.wilmingtonnc.gov/arcgis/rest/services/BaseLayers/Parcels/FeatureServer/0 — geometry (~103.9k); CRS **6543**
- **Join note:** city Zoning/0 + county parcels spatial join in 6543 for `MUNI='WM'` (and BD). Attribute `ZONING` on IASTAX usable as fallback.

### Town of Carolina Beach

- **Parcels (town host, rich join):** https://cw.carolinabeach.org/arcgis/rest/services/GISViewer/CB_Parcels/FeatureServer/2 — polygons + full CAMA fields (`OWN1`, `ZONING`, `ACRES`, sale/tax, `CB_Address`); count **8,100**; `ACRES` 5–150 → **21**; CRS **6543**
- **Zoning (town host — PRIMARY for CB):** https://cw.carolinabeach.org/arcgis/rest/services/GISViewer/GIS_Viewer/FeatureServer/21 — `ZONE` (R-1, R-1B, T-1, CBD, MX, NB, …) + dimensional attrs; count **29**; OverlayDistrict /20 (4)
- **FLU:** no public REST found (gap)
- **Join note:** Prefer town Zoning/21 spatial join for CB; parcel attribute `ZONING` also present on CB_Parcels and county IASTAX.

### Town of Wrightsville Beach

- **Zoning (town AGOL — PRIMARY for WB):** https://services3.arcgis.com/XyPkMiF0OxEhc77I/arcgis/rest/services/WrightsvilleBeachZoning/FeatureServer/0 — `Name` (e.g. `R-1 Zoning District`, C-1…C-5, G-1, P-1, P-C, S-1); count **256**; CRS **3857** — **reproject** before overlay with county 6543
- **EnergovWB:** https://services3.arcgis.com/XyPkMiF0OxEhc77I/arcgis/rest/services/EnergovWB/FeatureServer — Zoning/0, TownLimits/1, Address/2, Parcels/3 (permitting support)
- **Unofficial zoning map app:** https://townofwb.maps.arcgis.com/apps/webappviewer/index.html?id=f8650616a5bb4f2287a95d61b2a14c3b
- **FLU:** no public REST found (gap)
- **Join note:** Spatial join with transform, or rely on IASTAX `ZONING` for WB codes (C-1…, R-1/2/3, …).

### Town of Kure Beach

- **Zoning polygons:** **no public REST FeatureServer found** (gap) — town site offers zoning map PDF/viewer only
- **Attribute zoning:** IASTAX/PropertyOwners `ZONING` for `MUNI='KB'` (RA-*, B-1…B-4, RB-1, …)
- **FLU:** no public REST found (gap)
- **Join note:** Use county parcels + CAMA `ZONING` until a town FeatureServer appears.

### New Hanover County unincorporated (FD / NHC)

- **Zoning:** Layers/Zoning/FeatureServer/1 (and mirrors)
- **FLU:** PlanNHC_FLUM Place Types /8
- **Join note:** Filter `MUNI='FD'` or outside municipal limits.

## Gaps

- **Wilmington Create Wilmington FLU / Growth Strategies** — portfolio web app only; no verified queryable FeatureServer (biggest planning gap for the MSA core city).
- **Kure Beach zoning polygons** — no public REST; CAMA attribute only.
- **Carolina Beach / Wrightsville Beach / Kure Beach FLU** — no public REST found.
- **County Zoning is not countywide** — `CITY`/`WB`/`CB` placeholders; must route municipal layers.
- **Bare Parcels layer lacks owner/tax/situs** — must join IASTAX table or PropertyOwners (`MAPIDKEY` / `PID`↔`PARID`).
- **IASTAX/PropertyOwners row count > parcel polygons** — condo/multi-interest; dedupe for site search.
- **Wilmington city ParcelOwners** multi-owner + Shape__Area acreage ≠ county `ACRES` filter counts — do not use as primary acreage source.
- **Sale history** last-sale only; many `SALE_PRICE=0`.
- **Tax values are assessed** (`APRTOT`) — no separate market value on county layers.
- **OneMap CRS 2264 vs county 6543** — transform when mixing.
- **Wrightsville Beach zoning in Web Mercator (3857)** — transform or attribute-join.
- **geohub.wilmingtonnc.gov** hosting endpoint TLS/unavailable at verification — use `gis.wilmingtonnc.gov` instead.
- **Owner phones/emails** not collected.
- **No paid vendor data** used (CoreLogic/Regrid/ATTOM avoided).
- **MaxRecordCount** varies (1000–10000) — paginate.

## Hand-off notes for Land Search Builder

1. **Wire first:** `Layers/Parcels/FeatureServer/0` (or IASTAX/0) polygons + attribute join `Layers/IASTAX/FeatureServer/1` on `MAPIDKEY` (or `PID`=`PARID`). Filter `ACRES BETWEEN 5 AND 150` (~2.3k). Optional vacant-ish: `APRBLDG = 0` (~1.2k in range on table).
2. **Alternate attribute source:** PropertyOwners/0 points joined on `MAPIDKEY`.
3. **Zoning:** route by `MUNI` — FD→county Zoning/1; WM/BD→Wilmington Planning/Zoning/0; CB→Carolina Beach GIS_Viewer/21; WB→WrightsvilleBeachZoning/0 (3857); KB→CAMA `ZONING` only.
4. **FLU:** FD→PlanNHC Place Types/8; WM→existing LandUse MapServer/0 only (label as existing LU, not FLU) or leave FLU null; beaches→null.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='129'` (reproject 2264↔6543).
6. **Viewer / appraiser links:**
   - eTax search: `https://etax.nhcgov.com/pt/search/commonsearch.aspx?mode=parid` (search `{PARID}`)
   - Parcel viewer: `https://nhcgov.maps.arcgis.com/apps/webappviewer/index.html?id=bf12527f385b4d2e8420d892863b31dd`
7. **Join keys:** `MAPIDKEY`, `PARID`/`PID`, `PIN`/`MAPID`, OneMap `parno`↔`PIN`.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities are first-class:** never treat County Zoning as countywide coverage.


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://gis.nhcgov.com/server/rest/services/Layers/Parcels/FeatureServer/0 polygons load (sample centroid [-77.9125, 34.3669]); `PID` filled on 103,952 of 103,969; `ACRES` 5–150 ac **2,286**. Polygon layer Layers/Parcels/FeatureServer/0 (PID filled 103,952 of 103,969; ACRES 5-150 = 2,286). Owner/tax/sale live on the IASTAX/FeatureServer/1 table (no geometry; join MAPIDKEY or PID=PARID); pass2 counts below use that table (115,880 rows; ACRES 5-150 = 2,285).
- **Attribute layer for Pass 2:** https://gis.nhcgov.com/server/rest/services/Layers/IASTAX/FeatureServer/1 · id `PARID` · live count **115,880** · 5–150 ac **2,285** (`ACRES >= 5 AND ACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='NEW HANOVER'` gives **488** stations (37 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27NEW+HANOVER%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='New Hanover'` gives **498** stations (421 with AADT_2025, 61 with AADT_2024, 434 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27New+Hanover%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `APRTOT` non-zero **111,800**, `APRLAND` non-zero **99,589**
- **Sale history (ok):** price `SALE_PRICE` >0 **70,649**; date `SALE_DATE` non-null **114,763**. SALE_PRICE and SALE_DATE are strings on the IASTAX table: CAST(SALE_PRICE AS FLOAT) > 0.
- **Owner entity:** field `OWN1`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **1,323** (all parcels: 28,346), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://etax.nhcgov.com/pt/Datalets/Datalet.aspx?mode=profileall&UseSearch=no&pin={PARID}`. Tested `R06013-016-003-000` (https://etax.nhcgov.com/pt/Datalets/Datalet.aspx?mode=profileall&UseSearch=no&pin=R06013-016-003-000) → HTTP **200** (text/html; charset=utf-8), content verified: True. iasWorld Datalet GET works without the disclaimer step (owner, PARID, acres, zoning shown). New template; the card previously listed only the mode=parid search page.
- **Jurisdiction GIS viewer:** https://nhcgov.maps.arcgis.com/apps/webappviewer/index.html?id=bf12527f385b4d2e8420d892863b31dd → HTTP **200** (ArcGIS Web Application); ArcGIS item access=public
- **Municipal zoning/FLU layers re-checked:** 12 of 12 answer.
- **Pass 2 gaps:** none
