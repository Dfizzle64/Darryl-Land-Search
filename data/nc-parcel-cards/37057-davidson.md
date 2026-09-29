# Davidson County, NC — GIS County Card

## Summary

Davidson County (**Winston-Salem MSA**, FIPS **37057** — North Carolina, **not** Tennessee) publishes rich **public** ArcGIS REST at `webgis.co.davidson.nc.us`. Countywide **tax parcel polygons** (`OpenGov/OpenGov/MapServer/6` TaxParcels) carry ownership, mailing, **situs** (`PropertyAddress` / house+street parts), legal acreage, assessed/market values, **LandZoning**, and **up to five** deed sales (month/year/price/qualified). ~**99,204** parcels; **LegalLandType='AC' AND LegalLandUnits BETWEEN 5 AND 150** → **12,102**. **Zoning is city-first**: unincorporated county districts on OpenGov/EconDev/webGIS Zoning layers; **Lexington** has city AGOL parcel-keyed zoning; **Thomasville** has PTRC zoning polygons; **Wallburg** has PTRC LDP FLU + zoning clip; Midway/Denton/High Point (edge) rely mainly on parcel `LandZoning` + county placeholders. **FLU** public REST found for **Wallburg** only. **NC OneMap** (`cntyfips='057'`) is a usable fallback with situs/owner/values but **no saledate** and can lag CAMA. Main gaps: no countywide FLU; Midway/Denton/High Point lack dedicated public zoning FeatureServers; OneMap sale date empty.

## Portals

- **Davidson WebGIS** — https://webgis.co.davidson.nc.us/DavidsonGIS/ — Interactive parcels, zoning, qualified sales, addresses.
- **County ArcGIS REST** — https://webgis.co.davidson.nc.us/arcgis/rest/services — OpenGov, Lexington, FrameworkData, webGIS, EconDev, Parcels.
- **Tax Real Estate Search** — https://taxsearch.co.davidson.nc.us/RealEstateSearch — Also Basic Search root https://taxsearch.co.davidson.nc.us/
- **GIS Downloads** — https://dcnet.co.davidson.nc.us/GIS/Web_GISDownloads.aspx — Parcels, addresses, CountyZoning shapefiles.
- **Tax Database Downloads** — https://co.davidson.nc.us/866/Tax-Database-Downloads — CSV/TXT CAMA extracts.
- **Lexington Hub** — https://lexingtonnc-cityoflexington.hub.arcgis.com/ — City zoning app + FeatureServer.
- **Lexington Zoning & Land Use app** — https://cityoflexington.maps.arcgis.com/apps/webappviewer/index.html?id=e81ad2a083634782a0bd4f17328ff950
- **PTRC (Piedmont Triad) maps** — https://maps.ptrc.org/arcgis/rest/services — Thomasville, Wallburg LDP, Lexington CityLimits.
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`).

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` / `PinNumber`, `PARCEL_ID`, `AccountNumber`; OneMap `parno` | Prefer dashed PIN (`6843-04-80-0128`); `PARCEL_ID` is tax parcel number |
| polygons | Yes | OpenGov TaxParcels /6 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `LegalLandUnits`+`LegalLandType`=`AC`; Shape.STArea()/43560 | ~**12,102** AC 5–150; GIS area ~**11,781** in 5–150 |
| ownerName | Yes | `Name1`+`Name2` / OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `Address1`–`3`,`City`,`State`,`ZipCode` | Mailing, not situs |
| situs address | Yes | `PropertyAddress`; `HouseNumber`+`StreetName`+`StreetType`(+dir/suf/unit); OneMap `siteadd` | On **same** polygon layer (unlike Cabarrus) |
| lastSale date/price | Yes | `SaleYear1`+`SaleMonth1`,`SalePrice1`,`QualifiedCode1` (+ slots 2–5) | Compose date; filter QualifiedCode; also Qualified Sales layer |
| tax values | Yes | `TotalMarketValue`,`TotalAssessedValue`,`ParcelLandValue`,`ParcelBuildingValue`,`ParcelObxfValue` | Doubles on OpenGov |
| zoning | Yes (split) | Parcel `LandZoning`; Lexington `ZoningDistrict`; Thomasville `ZONING`; county `ZONE_CODE` | Prefer muni polygons where available; else LandZoning |
| flu | Yes (partial) | Wallburg `FLU` | Wallburg LDP only on public REST |
| appraiser / viewer link | Yes | WebGIS + taxsearch | Templates below |

## Layers (verified)

### 1. OpenGov/TaxParcels — parcels + ownership + situs + tax + sales + LandZoning (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | zoning (attr) | situs
- **REST URL:** https://webgis.co.davidson.nc.us/arcgis/rest/services/OpenGov/OpenGov/MapServer/6
- **Layer name / id:** TaxParcels / 6
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN`, `PinNumber`, `PARCEL_ID`, `AccountNumber` → parcelId
  - `LegalLandUnits`, `LegalLandType` → acreage (`AC`|`FF`|`LT`|`SF`|`UN`|`UT`)
  - `Name1`, `Name2` → ownerName
  - `Address1`, `Address2`, `Address3`, `City`, `State`, `ZipCode` → mailing
  - `PropertyAddress`, `HouseNumber`, `StreetName`, `StreetType`, `StreetDirection`, `StreetSuffix`, `UnitNumber` → situs
  - `SaleYear1`–`5`, `SaleMonth1`–`5`, `SalePrice1`–`5`, `QualifiedCode1`–`5`, `VacantOrImproved1`–`5` → lastSale (+ history)
  - `TotalMarketValue`, `TotalAssessedValue`, `ParcelLandValue`, `ParcelBuildingValue`, `ParcelObxfValue`, `ParcelDeferredValue` → tax
  - `LandZoning`, `CityCode`, `TownshipCode`, `Neighborhood`, `DeedBook`/`DeedPage`/`DeedDate` → zoning / jurisdiction / other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **99,204**; `LegalLandType='AC' AND LegalLandUnits BETWEEN 5 AND 150` → **12,102**; Shape area 5–150 ≈ **11,781**; sample owner/mail/situs/tax/sale OK
- **Notes:** **PRIMARY** wire-first. Situs on polygon. `LandZoning` non-empty **98,736**. `SalePrice1>0` **65,675**. MaxRecordCount **2000**. Prefer `LegalLandType='AC'` for acreage filter. `CityCode`: `07` Lexington, `28` Thomasville, `32` Midway, `33` Denton, `34` Wallburg, `39` High Point, null ≈ unincorporated (~69k).

### 2. Lexington/LexingtonService Parcels — countywide mirror (same schema)

- **Purpose:** parcels | tax | ownership | sales
- **REST URL:** https://webgis.co.davidson.nc.us/arcgis/rest/services/Lexington/LexingtonService/FeatureServer/2
- **Alternate MapServer:** https://webgis.co.davidson.nc.us/arcgis/rest/services/Lexington/LexingtonService/MapServer/2
- **Geometry:** Polygon
- **Verified:** yes — count **99,204**; AC 5–150 → **12,102** (same as OpenGov)
- **Notes:** Folder name is “Lexington” but layer is **countywide**. Prefer OpenGov TaxParcels as primary name; this FeatureServer is useful if MapServer query quirks appear.

### 3. Lexington Site Address Points — situs points

- **Purpose:** other (situs)
- **REST URL:** https://webgis.co.davidson.nc.us/arcgis/rest/services/Lexington/LexingtonService/FeatureServer/0
- **Geometry:** Point
- **Key fields:** `FAddress`, `Add_Number`, `St_Name`, `St_PosTyp`, `Inc_Muni`, `Post_Comm`, `Post_Code`, `Uninc_Comm`
- **Verified:** yes — count **99,503**; `Inc_Muni` values: Archdale, Denton, High Point, Lexington, Midway, Thomasville, Unincorporated, Wallburg
- **Notes:** No PIN on address points — spatial join to parcels. Prefer parcel `PropertyAddress` when present. Do not harvest contact PII.

### 4. Parcels/MapServer + FrameworkData Parcels — mirrors

- **Purpose:** parcels
- **REST URLs:**
  - https://webgis.co.davidson.nc.us/arcgis/rest/services/Parcels/MapServer/0 (count **99,204**)
  - https://webgis.co.davidson.nc.us/arcgis/rest/services/FrameworkData/FrameworkLayers/FeatureServer/3 (count **99,200**)
- **Verified:** yes
- **Notes:** Same CAMA family as OpenGov; prefer OpenGov/6 for OpenGov documentation path.

### 5. County Zoning polygons — unincorporated (+ placeholders)

- **Purpose:** zoning
- **REST URLs:**
  - https://webgis.co.davidson.nc.us/arcgis/rest/services/OpenGov/OpenGov/MapServer/10 — count **1,304** (district codes only; no CITY ZONING placeholders)
  - https://webgis.co.davidson.nc.us/arcgis/rest/services/webGIS/DC_webGIS/MapServer/29 — count **1,806**
  - https://webgis.co.davidson.nc.us/arcgis/rest/services/EconDev/EconDev/MapServer/18 — count **1,806**
- **Fields:** `ZONE_CODE` (EconDev/webGIS also encode `LEXINGTON CITY ZONING`, `THOMASVILLE CITY ZONING`, `DENTON TOWN ZONING`, `CITY OF HIGH POINT`, `DENTON ETJ`, etc. as **placeholders** — not detailed city codes)
- **WKID / CRS:** 102719 / 2264
- **Join:** spatial join to TaxParcels; for city interiors prefer municipal layers / `LandZoning`
- **Verified:** yes — OpenGov distinct districts include CS, HC, HI, LI, O/I, RA-*, RC, RM-*, RS, PD-*, MX-R, CU-*, etc.
- **Notes:** OpenGov/10 is cleaner for **unincorporated** district polygons. Filter out placeholder labels when using EconDev/webGIS.

### 6. Municipal Boundary / city routing

- **Purpose:** other (municipality filter)
- **REST URLs:**
  - https://webgis.co.davidson.nc.us/arcgis/rest/services/EconDev/EconDev/MapServer/20 — `CITY_NAME`
  - https://webgis.co.davidson.nc.us/arcgis/rest/services/OpenGov/OpenGov/MapServer/4 — `CITY_NAME`
  - https://webgis.co.davidson.nc.us/arcgis/rest/services/FrameworkData/FrameworkLayers/FeatureServer/4
- **Verified values:** DENTON, HIGH POINT, LEXINGTON, MIDWAY, THOMASVILLE, WALLBURG
- **Notes:** Multi-part polygons per city. Also `CityCode` on TaxParcels and `Inc_Muni` on addresses. OpenGov `bnd_planning_zones` (layer 9) mixes COUNTY regions + municipalities.

### 7. Qualified Property Sales (since 2022) — comps layer

- **Purpose:** sales
- **REST URL:** https://webgis.co.davidson.nc.us/arcgis/rest/services/webGIS/DC_webGIS/MapServer/76
- **Geometry:** Polygon
- **Key fields:** `PIN`, `PARCEL_ID`, `SalePropertyReal_SalePrice`, `SalePropertyReal_DeedDate`, `SalePropertyReal_IsQualified`, `SalePropertyReal_IsImproved`, `TotalMarketValue`, `LandZoning`, `LegalLandUnits`
- **Verified:** yes — count **12,136**
- **Notes:** Use for qualified comps; still keep Sale*1–5 on TaxParcels for last-transfer history.

### 8. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Key fields → targets:** `parno` → parcelId; `ownname` → owner; `mailadd`/`mcity`/`mstate`/`mzip` → mailing; `siteadd`/`scity` → situs; `gisacres` → acreage; `parval`/`landval`/`improvval` → tax; `cntyfips`=`057`
- **Verified:** yes — filter count **98,799**; gisacres 5–150 → **11,767**; ownname non-empty **98,542**; siteadd non-empty **98,512**; **saledate non-null = 0** for Davidson
- **Notes:** Good situs/owner fallback. **No usable sale date/price** here for this county. May lag county CAMA. MaxRecordCount **5000**.

### 9. Thomasville Zoning (PTRC) — city zoning polygons

- **Purpose:** zoning
- **REST URL:** https://maps.ptrc.org/arcgis/rest/services/Thomasville/Thomasville/MapServer/14
- **Field:** `ZONING` — C1–C4, M1–M2, OI, R6/R8/R10/R15/R10M (+ -CZ variants)
- **Verified:** yes — count **249**; CRS **2264**
- **Notes:** Prefer over county placeholder `THOMASVILLE CITY ZONING`. Spatial join to county TaxParcels (`CityCode='28'` or CITY_NAME THOMASVILLE).

### 10. Thomasville Parcels (PTRC) — city subset (optional)

- **Purpose:** parcels | tax | ownership (city)
- **REST URL:** https://maps.ptrc.org/arcgis/rest/services/Thomasville/Thomasville/MapServer/4
- **Verified:** yes — count **13,267**; fields include `PIN`, `PropertyOwner`, mailing, `PropertyAd`, `Tax_Acres`/`AcresCalc`, values; `Zoning` often null on sample
- **Notes:** Mostly small lots (AcresCalc 5–150 ≈ **2**). Prefer county TaxParcels for land search; use for Thomasville-local enrichment only.

### 11. Lexington CITY ZONING DISTRICTS (city AGOL) — preferred city zoning

- **Purpose:** zoning
- **REST URL:** https://services3.arcgis.com/Z7ioXMhIaRIEQx1O/arcgis/rest/services/CITY_ZONING_DISTRICTS_view/FeatureServer/0
- **Fields:** `ZoningDistrict`, `ZoningDistrictName`, `PIN`, `PARCEL_ID`
- **Verified:** yes — count **9,283**; CRS **2264**; districts B, DD, I, MH, MU, PD, SN, TN, U (+ CONDITIONAL variants)
- **Notes:** **Parcel-keyed** — attribute join on `PIN`/`PARCEL_ID` to TaxParcels (`CityCode='07'`). Prefer over county `LEXINGTON CITY ZONING` placeholder.

### 12. Wallburg LDP 2026 (PTRC) — FLU + zoning clip

- **Purpose:** flu | zoning
- **REST base:** https://maps.ptrc.org/arcgis/rest/services/Wallburg/Wallburg_LDP_2026/MapServer
  - Layer **1** Future Land Use — `FLU` (AG, COM, IND, LDR, MDR, MIX, PI, REC); count **36**
  - Layer **2** Existing Land Use — `ExLU`; count **120**
  - Layer **3** Zoning (Wallburg Clip) — `ZONE_CODE`; count **34**
  - Layer **4** Zoning (County) — countywide mirror; count **1,795**
- **Verified:** yes — CRS **2264**
- **Notes:** Best public **FLU** for Davidson munis. Spatial join to TaxParcels (`CityCode='34'` / WALLBURG).

## Municipalities (first-class)

County parcels are countywide; **zoning/FLU are municipal**. Join pattern: start from OpenGov TaxParcels (2264) → route by `CityCode` / Municipal Boundary `CITY_NAME` / `Inc_Muni` → attribute or spatial join the matching city layer. All listed city hosts use **2264** (no Concord-style CRS fight).

### City of Lexington (`CityCode` **07**, ~10,147 parcels)

- **Zoning (city AGOL, preferred):** https://services3.arcgis.com/Z7ioXMhIaRIEQx1O/arcgis/rest/services/CITY_ZONING_DISTRICTS_view/FeatureServer/0 — `ZoningDistrict`/`ZoningDistrictName`; count **9,283**; join by `PIN`/`PARCEL_ID`
- **Viewer:** https://cityoflexington.maps.arcgis.com/apps/webappviewer/index.html?id=e81ad2a083634782a0bd4f17328ff950
- **Hub:** https://lexingtonnc-cityoflexington.hub.arcgis.com/
- **PTRC CityLimits:** https://maps.ptrc.org/arcgis/rest/services/Lexington/CityLimits/MapServer
- **FLU:** no public FLU FeatureServer found (gap — zoning/land-use web app only)
- **Join note:** attribute join city zoning → county TaxParcels on PIN; or spatial. County layer marks area as `LEXINGTON CITY ZONING` placeholder only.

### City of Thomasville (`CityCode` **28**, ~11,896 parcels)

- **Zoning (PTRC, preferred):** https://maps.ptrc.org/arcgis/rest/services/Thomasville/Thomasville/MapServer/14 — `ZONING`; count **249**
- **ETJ (county):** OpenGov TV-ETJ MapServer/11 (count **11**) + county `THOMASVILLE ZONING - ETJ` placeholder
- **City parcels optional:** Thomasville/MapServer/4 — prefer county TaxParcels for 5–150 acre search
- **FLU:** PDF Land Development Plan on city site; **no public FLU REST** found
- **Join note:** spatial join PTRC zoning → county parcels (`CityCode='28'`). Zoning field on PTRC parcels often null — use layer 14.

### Town of Midway (`CityCode` **32**, ~1,159 parcels)

- **Zoning:** no dedicated public FeatureServer found; use TaxParcels `LandZoning` (R20, R15, MUD, NB, HB, RA1, …)
- **FLU:** gap
- **Join note:** attribute `LandZoning` + Municipal Boundary MIDWAY. County zoning polygons do not expand Midway’s detailed codes.

### Town of Denton (`CityCode` **33**, ~1,660 parcels)

- **Zoning:** no dedicated public FeatureServer; county placeholders `DENTON TOWN ZONING` / `DENTON ETJ`; parcel `LandZoning` (RA1–RA3, RS, RC, CS, HC, LI, …)
- **PTRC:** Denton/Denton_Stormwater only (not zoning)
- **FLU:** gap
- **Join note:** prefer `LandZoning` on TaxParcels; spatial-filter with CITY_NAME DENTON / CityCode 33.

### Town of Wallburg (`CityCode` **34**, ~2,427 parcels)

- **Zoning clip:** Wallburg_LDP_2026/MapServer/3 — `ZONE_CODE`; count **34**
- **FLU (preferred):** Wallburg_LDP_2026/MapServer/1 — `FLU`; count **36** (AG/COM/IND/LDR/MDR/MIX/PI/REC)
- **Join note:** spatial join FLU/zoning clip → county TaxParcels. Wallburg largely uses **county** zoning districts.

### City of High Point (Davidson edge, `CityCode` **39**, ~2,621 parcels)

- **Zoning:** no Davidson-hosted or verified public High Point REST found this pass; use TaxParcels `LandZoning` (RM*, R3/R5, PDR, …) and county placeholder `CITY OF HIGH POINT`
- **FLU:** gap on Davidson stack
- **Join note:** filter Municipal Boundary HIGH POINT / CityCode 39; do not assume county RA districts apply inside HP.

### Archdale (address `Inc_Muni` only)

- Tiny/edge presence via address points; no separate zoning inventory here — verify against Municipal Boundary (may be absent).

## Gaps

- **No countywide FLU FeatureServer** — Wallburg LDP only; Lexington/Thomasville/Midway/Denton/High Point FLU = gap or PDF/web-app only.
- **Midway / Denton / High Point** lack dedicated public zoning polygon REST — rely on parcel `LandZoning` or county placeholders.
- **County Zoning layers** use **CITY ZONING** placeholders that do not carry city district codes — never treat as city coverage.
- **OneMap** Davidson: **saledate always null**; prefer county Sale* fields.
- **LexingtonService** folder name is misleading (countywide parcels) — document carefully.
- **Thomasville PTRC parcels** are small-lot oriented and weak on Zoning/acres for land search — use county TaxParcels.
- **MaxRecordCount 2000** on county layers; OneMap 5000 — paginate.
- **Owner phones/emails** not collected (do not scrape taxsearch/WebGIS PII beyond public REST fields).
- **No paid vendor data** used (CoreLogic/Regrid/ATTOM avoided).

## Hand-off notes for Land Search Builder

1. **Wire first:** `OpenGov/OpenGov/MapServer/6` TaxParcels — polygons + owner, mailing, situs, acreage, tax, LandZoning, sales 1–5. Filter `LegalLandType='AC' AND LegalLandUnits BETWEEN 5 AND 150` (~12.1k).
2. **Situs:** use `PropertyAddress` (or compose HouseNumber+Street*); fallback OneMap `siteadd` or address-point spatial join.
3. **Zoning:** (a) attribute `LandZoning` for quick coverage; (b) spatial/attribute join Lexington AGOL + Thomasville PTRC + Wallburg clip; (c) county OpenGov/Zoning for unincorporated — exclude city placeholders.
4. **FLU:** spatial join Wallburg layer 1 only; leave null elsewhere.
5. **Sales/comps:** TaxParcels Sale*1 (latest) + slots 2–5; Qualified Sales MapServer/76 for post-2022 qualified comps.
6. **Fallback:** NC OneMap layer 1 with `cntyfips='057'` (no sale date).
7. **Viewer / appraiser links:**
   - WebGIS: `https://webgis.co.davidson.nc.us/DavidsonGIS/` (search PIN / Parcel ID / owner / address)
   - Tax search: `https://taxsearch.co.davidson.nc.us/RealEstateSearch` / Basic `https://taxsearch.co.davidson.nc.us/`
8. **Join keys:** `PIN`/`PinNumber` (preferred), `PARCEL_ID`, `AccountNumber`, OneMap `parno`↔`PIN`.
9. **Auth:** none observed on listed public query endpoints.
10. **Cities are first-class:** never treat county zoning polygons as countywide detailed coverage.

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='DAVIDSON'`, field `AADT_2022` (string) — **961 stations live**, 437 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27DAVIDSON%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27DAVIDSON%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Davidson'`, `AADT_2025` (int) — 973 stations; 647 with 2025, 434 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://webgis.co.davidson.nc.us/arcgis/rest/services/OpenGov/OpenGov/MapServer/6` — total 99264, 5–150 ac 12102 (`LegalLandType='AC' AND LegalLandUnits>=5 AND LegalLandUnits<=150`).
- Non-zero county: `ParcelLandValue` 98006, `ParcelBuildingValue` 73256, `TotalMarketValue` 98008, `TotalAssessedValue` 98008; in 5–150: `TotalAssessedValue` 12059. **Status: ok.**
- Double fields; TotalMarketValue/TotalAssessedValue + Parcel* components.

### 3. Sale history
- Price `SalePrice1`>0 65676 (5–150: 6016); date non-null `SaleYear1` 96820, `SaleMonth1` 96820. **Status: ok.**
- No full sale date on parcel: SaleYear1 + SaleMonth1; SalePrice1; QualifiedCode1. Full deed dates on Qualified Sales since 2022 layer webGIS/DC_webGIS/MapServer/76 (SalePropertyReal_DeedDate).

### 4. Owner entity
- Owner fields: `Name1`, `Name2`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 2472** (of 12102 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: **none (gap)**
- Tested `https://taxsearch.co.davidson.nc.us/RealEstateSearch` → **200**. GAP: no GET deep link. Detail view is AJAX POST RealEstateSearch/ViewParcel (JSON parcelNumber/taxYear) — returned 500 for PIN/PARCEL_ID/Account tests; not usable as a link. Use search page with PIN placeholder.

### 6. Jurisdiction GIS viewer
- `https://webgis.co.davidson.nc.us/DavidsonGIS/` → **200**. Davidson WebGIS (Avineon template)

### Pass2 gaps
- PA deep link: no GET URL with parcel id (search page only) — no GET deep link. Detail view is AJAX POST RealEstateSearch/ViewParcel (JSON parcelNumber/taxYear) — returned 500 for PIN/PARCEL_ID/Account tests; not usable as
- Sale date is year+month only on parcel layer (no day)
- AADT_2022 blank at 524 of 961 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- Last sale on primary layer; separate sales layer documented in saleHistory.notes
