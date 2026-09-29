# Brunswick County, NC — GIS County Card

## Summary

Brunswick County (Wilmington MSA, FIPS **37019**) publishes rich **public** ArcGIS REST at `bcgis.brunswickcountync.gov`: countywide **tax parcel polygons** with ownership, mailing, situs parts, GIS acreage, deed date/book/page, and a **parcel-level Zoning attribute** on `Layers/SeamlessParcels` and `Layers/TaxParcels` (plus `TaxCard` deep links on Seamless/DataViewer). **Tax market/land/improvement values** are **not** on those CAMA-style layers — join county-hosted `NC1MAP_SEAMLESSPARCELS` (`CNTYFIPS='37019'`) or **NC OneMap** (`cntyfips='019'`). **Zoning polygons** are county-hosted for all 19 municipalities on `Layers/MuniZoning` (and a unified `Layers/Zoning` with `CO-`/`LE-`/… prefixes). **FLU** is public countywide on `Layers/FutureLandUse` (`FLU`, `LAND_USE`, PIN). **No sale price** on public REST (deed date only; tax site Sales HTML). Prefer **most-local** municipal zoning layers for city parcels; county parcels remain the geometry source.

## Portals

- **GIS Data Viewer (Experience)** — https://experience.arcgis.com/experience/0201d27723244840aea67c9f85892953
- **GIS Data Viewer (Web AppBuilder, legacy)** — https://www.arcgis.com/apps/webappviewer/index.html?id=6df283e1aa634006baeedf6daac40d38
- **Open GIS Data Portal** — https://data-brunsco.opendata.arcgis.com/
- **GIS home / downloads** — https://gis.brunswickcountync.gov/ — also https://www.brunswickcountync.gov/321/Data-Download
- **County ArcGIS REST** — https://bcgis.brunswickcountync.gov/arcgis/rest/services
- **Tax Basic Search** — https://tax.brunsco.net/ITSNet/BasicSearch.aspx
- **Tax Real Estate Search** — https://tax.brunsco.net/ITSNet/RealEstate.aspx
- **Tax Sales Search (HTML)** — https://tax.brunsco.net/ITSNet/Sales.aspx
- **Appraisal / property record card** — `https://tax.brunsco.net/ITSNet/AppraisalCard.aspx?parcel={ParcelNumber}`
- **Town of Leland maps** — https://www.townofleland.com/planning-inspections/online-maps-and-gis — interactive AGOL maps; zoning also on county MuniZoning/8
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `ParcelNumber`, `PIN`; OneMap/NC1MAP `parno`/`PARNO`, `altparno`/`ALTPARNO` | `ParcelNumber`↔`parno`; `PIN`↔`altparno` |
| polygons | Yes | SeamlessParcels / TaxParcels | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALCAC`, `DeedAcreage`; NC1MAP `GISACRES` / OneMap `gisacres` | Seamless **7,610** / TaxParcels **7,549** / OneMap **7,020** / NC1MAP **7,575** in 5–150 |
| ownerName | Yes | `Name1`+`Name2` / `OWNNAME` / `ownname` | Public REST — do not scrape phones/emails |
| mailing address | Yes | `Address1`–`3`,`City`,`State`,`ZipCode` / `MAILADD`,`MCITY`… | |
| situs address | Yes | `HouseNumber`+`StreetName`+`StreetType`(+`StreetDirection`); OneMap `siteadd` | Also Addresses points (`ST_ADDR`) — no parcel id (spatial join) |
| lastSale date/price | Partial | `DeedDate` (+ book/page); tax Sales.aspx HTML | **No sale price** on REST; OneMap/NC1MAP `saledate` empty for Brunswick |
| tax values | Yes (join) | NC1MAP `PARVAL`,`LANDVAL`,`IMPROVVAL` / OneMap `parval`,`landval`,`improvval` | **Not** on Seamless/TaxParcels; DV2 Municipal FLU subset has TOTALMARKE (~6.4k only) |
| zoning | Yes | Parcel attr `Zoning`; polygons `ZCODE` (MuniZoning / Zoning / parcelZonings) | Prefer muni polygon for most-local; attr is convenient |
| flu | Yes | `FLU`,`LAND_USE` on FutureLandUse; PIN join or spatial | Countywide; categories LDR/MDR/HDR/COMMERCIAL/MIXED USE/… |
| appraiser / viewer link | Yes | AppraisalCard + BasicSearch + GIS viewer | Templates below |

## Layers (verified)

### 1. SeamlessParcels — parcels + ownership + situs + zoning attr + TaxCard (PRIMARY)

- **Purpose:** parcels | ownership | zoning (attr) | other (appraiser link)
- **REST URL:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/SeamlessParcels/FeatureServer/0
- **MapServer mirror:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/SeamlessParcels/MapServer/0
- **Layer name / id:** SeamlessParcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `ParcelNumber`, `PIN` → parcelId
  - `CALCAC`, `DeedAcreage` → acreage
  - `Name1`, `Name2` → ownerName
  - `Address1`, `Address2`, `Address3`, `City`, `State`, `ZipCode` → mailing
  - `HouseNumber`, `StreetName`, `StreetType`, `StreetDirection` → situsAddress
  - `Zoning` → zoning (attribute; ~165.8k non-empty)
  - `DeedDate`, `DeedBook`, `DeedPage` → lastSale.date / deed refs (**no price**)
  - `UseCode`, `LegalDescription`, `ActualYearBuilt` → other
  - `TaxCard` → appraiser deep link (all **174,258** populated)
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **174,258**; `CALCAC BETWEEN 5 AND 150` → **7,610**; TaxCard + Zoning samples OK
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000**. No market/assessed values — join NC1MAP. Pad/strip `HouseNumber` leading zeros when composing situs.

### 2. TaxParcels — same CAMA family (alternate primary)

- **Purpose:** parcels | ownership | zoning (attr)
- **REST URL:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/TaxParcels/FeatureServer/0
- **MapServer:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/TaxParcels/MapServer/0
- **Layer name / id:** Tax Parcels / 0
- **Geometry:** Polygon
- **Key fields:** Same as SeamlessParcels **except no `TaxCard`** (build from ParcelNumber template).
- **Verified:** yes — count **172,636**; CALCAC 5–150 → **7,549**; Zoning non-null **165,072**; HouseNumber **147,099**; DeedDate **171,289**
- **Notes:** Prefer SeamlessParcels for TaxCard. Construct `https://tax.brunsco.net/ITSNet/AppraisalCard.aspx?parcel={ParcelNumber}`.

### 3. Mapping/DataViewerLive Parcels — viewer backend + TaxCard

- **Purpose:** parcels | ownership | other (TaxCard)
- **REST URL:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Mapping/DataViewerLive/MapServer/26
- **Alternate:** DataViewer_V2/MapServer/50 (no TaxCard on V2 schema)
- **Geometry:** Polygon
- **Verified:** yes — count **165,508**; TaxCard template confirmed
- **Notes:** Slightly leaner field set; use SeamlessParcels for extract.

### 4. NC1MAP_SEAMLESSPARCELS (county host) — tax values + situs (PRIMARY tax join)

- **Purpose:** parcels | tax | ownership | situs
- **REST URL:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/NC1MAP_SEAMLESSPARCELS/FeatureServer/0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PARNO` → parcelId (= county `ParcelNumber`)
  - `ALTPARNO` → PIN
  - `OWNNAME`, `OWNNAME2` → ownerName
  - `MAILADD`,`MCITY`,`MSTATE`,`MZIP` → mailing
  - `SITEADD`,`SCITY`,`SZIP` → situs
  - `GISACRES` → acreage (~**7,575** in 5–150)
  - `PARVAL`,`LANDVAL`,`IMPROVVAL` → tax (**~171k** with PARVAL>0)
  - `SALEDATE`/`SALEDATEX` → empty for Brunswick
  - Filter: `CNTYFIPS='37019'` (5-digit; **not** `019`)
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — filter count **174,071**; sample PARNO=`13100038` aligns with county ParcelNumber + PIN/`ALTPARNO`
- **Notes:** Best in-county tax-value join. MaxRecordCount **2000**.

### 5. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Geometry:** Polygon
- **Key fields:** `parno`,`ownname`,`mailadd`,`mcity`,`mstate`,`mzip`,`siteadd`,`gisacres`,`parval`,`landval`,`improvval`; filter `cntyfips='019'`
- **Verified:** yes — count **151,753**; gisacres 5–150 → **7,020**; `parval>0` → **151,239**; **saledate empty**
- **Notes:** MaxRecordCount **5000**. May lag county CAMA. Prefer county NC1MAP_SEAMLESSPARCELS when available.

### 6. Layers/Zoning — unified county + municipal zoning polygons

- **Purpose:** zoning
- **REST URL:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/Zoning/MapServer/0
- **Alternate:** Mapping/AllZoning/MapServer/0 ; DataViewerLive/MapServer/37
- **Geometry:** Polygon
- **Key fields:** `ZCODE` (prefixed e.g. `CO-CLD`, `LE-R-6`, `SH-B-2`, `SP-BD`), `CaseNum`
- **Verified:** yes — count **11,505**
- **Notes:** Spatial join to parcels in 2264. Prefix encodes jurisdiction (CO=county, LE=Leland, SH=Shallotte, …). For most-local edits prefer MuniZoning layers.

### 7. Layers/MuniZoning — per-municipality zoning (PREFERRED local)

- **Purpose:** zoning (city-first)
- **REST URL:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/MuniZoning/MapServer/{0–18}
- **Field:** `ZCODE`, `CaseNum`
- **CRS:** 102719 / 2264
- **Verified counts:**

| ID | Municipality | Count | Sample ZCODE |
|----|--------------|------:|--------------|
| 0 | Bald Head Island | 91 | BH-PD-3C |
| 1 | Belville | 928 | BE-R10 |
| 2 | Boiling Spring Lakes | 431 | BS-R-2 |
| 3 | Bolivia | 56 | BO-R-15 |
| 4 | Calabash | 222 | CA-PUD |
| 5 | Carolina Shores | 71 | CS-R6 |
| 6 | Caswell Beach | 71 | CB-R20-MF |
| 7 | Holden Beach | 130 | HB-R-1 |
| 8 | Leland | 1,362 | LE-R-6 |
| 9 | Navassa | 296 | NA-R-15 |
| 10 | Northwest | 22 | NW-CI |
| 11 | Oak Island | 716 | OK-CB |
| 12 | Ocean Isle Beach | 104 | OI-R-1 |
| 13 | Sandy Creek | 17 | SC-R1 |
| 14 | Shallotte | 595 | SH-B-2 |
| 15 | Southport | 442 | SP-BD |
| 16 | St. James | 392 | SJ-EPUD |
| 17 | Sunset Beach | 320 | SB-MR-3 |
| 18 | Varnamtown | 10 | VA- |

- **Notes:** **Cities are first-class.** Route by Municipalities `TYPE` / situs city / parcel Zoning prefix, then spatial-join the matching layer. Unincorporated = county codes on Layers/Zoning / parcel attr (often without muni prefix on TaxParcels.Zoning, e.g. `RR`, `R75`, `CLD`).

### 8. parcelZonings — parcel∩zoning convenience join

- **Purpose:** zoning
- **REST URL:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/parcelZonings/FeatureServer/0
- **Key fields:** `PARCEL_ID` (= ParcelNumber), `ZCODE` (may be multi, comma-separated), `ZONE_LID_VALUE` (flood-like labels)
- **Verified:** yes — count **166,875**; ZCODE non-null **166,817**
- **Notes:** Attribute-join on ParcelNumber. Multi-zone parcels possible — prefer polygon spatial join for purity.

### 9. FutureLandUse — countywide FLU

- **Purpose:** flu
- **REST URL:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/FutureLandUse/MapServer/0
- **Key fields:** `FLU`, `LAND_USE`, `PIN`, `AMENDED`, `CASE_`, `DOCUMENT`
- **Verified:** yes — count **65,856**; FLU values include LDR (**31,909**), MDR (**18,253**), CONSERVATION (**6,958**), MIXED USE (**3,663**), COMMERCIAL (**2,887**), HDR (**910**), INDUSTRIAL (**848**), COMMUNITY COMMERCIAL (**386**), plus rare codes
- **Join:** attribute on cleaned `PIN` (strip `.000`) or **spatial join** in 2264
- **Notes:** Also DV2 group FutureLandUse: County layer 45 (`ALT3_FLU_UNION`, count 6,242) and Municipal layer 46 (FLU+tax subset, count 6,405 — **not** countywide tax). Prefer MapServer/0 for coverage.

### 10. Municipalities — jurisdiction polygons

- **Purpose:** other (municipality filter)
- **REST URL:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/Municipalities/FeatureServer/0
- **Fields:** `TYPE` (code), `STATUS` (`CITY`|`ETJ`)
- **Verified:** yes — count **26** (city + ETJ rings)
- **TYPE codes:** BHI, BEL, BSL, BOL(+BOLX ETJ), CAL(+CALX), CSH(+CSHX), CWB (Caswell Beach), HLB, LEL, NAV, NRW, OIB(+OIBX) Oak Island, OAK(+OAKX) Ocean Isle, SCR, SHL(+SHLX), SPT, STJ, SUN(+SUNX), VAR
- **Notes:** Use to route which MuniZoning layer to spatial-join.

### 11. Addresses — situs points (optional)

- **Purpose:** other (situs)
- **REST URL:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/Addresses/FeatureServer/0
- **Fields:** `ST_ADDR`,`ST_NUMB`,`ST_NAME`,`UNIT_NO`,`POSTAL`,`CITY`,`ZIPCODE`,`TAX_PRIMARY`
- **Verified:** yes — count **164,535**
- **Notes:** **No parcel id** — spatial join to parcels. Prefer situs fields already on SeamlessParcels / OneMap.

### 12. Parcelpoly / ParcelHistory — geometry-only archives

- **Parcelpoly:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/Parcelpoly/FeatureServer/0 — PIN/CALCAC/PARCEL_ID; count **168,927**; 5–150 → **7,663**
- **ParcelHistory Parcels2025:** …/Layers/ParcelHistory/FeatureServer/21 — same lean schema; historical years 0–20 also published
- **Notes:** Prefer Seamless/TaxParcels for attributes.

## Municipalities (first-class)

County parcels are countywide; **zoning authority is municipal inside city limits / ETJ**. Join pattern: start from SeamlessParcels (2264) → filter/route via Municipalities.`TYPE` or parcel `Zoning` prefix → spatial-join matching `MuniZoning` layer (or use unified Zoning / parcelZonings / parcel Zoning attr). **No separate municipal parcel REST** found for Leland/Shallotte/Southport/Oak Island — use county parcels + local zoning. Leland publishes interactive AGOL maps on town site; authoritative polygons for wire are on county `MuniZoning`.

### Town of Leland (LEL)

- **Zoning (preferred):** MuniZoning/MapServer/**8** — `ZCODE`; count **1,362**; CRS **2264**
- **Town maps:** https://www.townofleland.com/planning-inspections/online-maps-and-gis
- **FLU:** county FutureLandUse (spatial/PIN); no separate Leland FLU FeatureServer found
- **Join note:** town zoning + county SeamlessParcels (spatial, 2264)

### City of Southport (SPT)

- **Zoning:** MuniZoning/**15** — count **442**; sample `SP-BD`
- **FLU:** county FutureLandUse
- **Join note:** city zoning + county parcels

### Town of Shallotte (SHL / SHLX ETJ)

- **Zoning:** MuniZoning/**14** — count **595**; sample `SH-B-2`
- **Join note:** include ETJ ring when STATUS=ETJ

### Town of Oak Island (OIB / OIBX)

- **Zoning:** MuniZoning/**11** — count **716**; sample `OK-CB`
- **Join note:** city zoning + county parcels

### Town of Bolivia (BOL / BOLX) — county seat area

- **Zoning:** MuniZoning/**3** — count **56**; sample `BO-R-15`
- **Join note:** small footprint; ETJ separate

### Other municipalities (county-hosted zoning only)

Bald Head Island (0), Belville (1), Boiling Spring Lakes (2), Calabash (4), Carolina Shores (5), Caswell Beach (6), Holden Beach (7), Navassa (9), Northwest (10), Ocean Isle Beach (12), Sandy Creek (13), St. James (16), Sunset Beach (17), Varnamtown (18) — same join pattern: MuniZoning layer + county parcels. No independent public municipal FeatureServers verified beyond Leland’s viewer maps.

### Unincorporated Brunswick County

- Use Layers/Zoning (`CO-*` codes) and/or SeamlessParcels.`Zoning` attribute; FutureLandUse for FLU.

## Gaps

- **No lastSale.price on public ArcGIS REST** — only `DeedDate`/book/page; OneMap & county NC1MAP sale date fields empty; tax `Sales.aspx` is HTML (not FeatureServer).
- **Tax market values absent from SeamlessParcels/TaxParcels** — must join NC1MAP_SEAMLESSPARCELS or OneMap by ParcelNumber↔PARNO.
- **Addresses layer has no parcel key** — spatial join only; situs usually already on parcels.
- **Municipal FLU REST** beyond county FutureLandUse not found (Leland 2045 etc. = plan docs / viewers).
- **DV2 Municipal FLU layer 46** has TOTALMARKE but only ~6.4k features — do not treat as countywide tax.
- **MaxRecordCount 2000** on county layers (OneMap 5000) — paginate.
- **Owner phones/emails** not collected (do not scrape tax site PII beyond public REST).
- **No paid vendor data** used (CoreLogic/Regrid/ATTOM avoided).

## Hand-off notes for Land Search Builder

1. **Wire first:** `Layers/SeamlessParcels/FeatureServer/0` — polygons + owner, mailing, situs parts, acreage, Zoning attr, DeedDate, TaxCard. Filter `CALCAC BETWEEN 5 AND 150` (~7.6k).
2. **Tax values join:** `Layers/NC1MAP_SEAMLESSPARCELS/FeatureServer/0` on `PARNO`=`ParcelNumber` (or OneMap `parno` with `cntyfips='019'`). County NC1MAP filter `CNTYFIPS='37019'`.
3. **Zoning:** prefer parcel `Zoning` for quick attribute; for authoritative polygons spatial-join `MuniZoning/{id}` by municipality or unified `Layers/Zoning/MapServer/0` / `parcelZonings` on `PARCEL_ID`.
4. **FLU:** spatial or PIN-join `FutureLandUse/MapServer/0` (`FLU`).
5. **Fallback:** NC OneMap layer 1 with `cntyfips='019'`.
6. **Viewer / appraiser links:**
   - Appraisal card: `https://tax.brunsco.net/ITSNet/AppraisalCard.aspx?parcel={ParcelNumber}`
   - Basic Search: `https://tax.brunsco.net/ITSNet/BasicSearch.aspx`
   - Sales (HTML): `https://tax.brunsco.net/ITSNet/Sales.aspx`
   - GIS viewer: Experience Builder URL above
7. **Join keys:** `ParcelNumber`↔`PARNO`/`parno`; `PIN`↔`ALTPARNO`/`altparno`.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities are first-class:** never treat county zoning alone as full municipal coverage — use MuniZoning for Leland/Shallotte/Southport/Oak Island/etc.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/SeamlessParcels/FeatureServer/0 · id `ParcelNumber` · live count **174,258** · 5–150 ac **7,610** (`CALCAC >= 5 AND CALCAC <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='BRUNSWICK'` gives **380** stations (99 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27BRUNSWICK%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Brunswick'` gives **373** stations (239 with AADT_2025, 188 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Brunswick%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Brunswick'` gives **378** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok-alt-layer):** `PARVAL` non-zero **171,020**. SeamlessParcels has no value fields. Use county-host NC1MAP_SEAMLESSPARCELS FS/0 (PARVAL/LANDVAL/IMPROVVAL; join PARNO/ALTPARNO→ParcelNumber/PIN). Alt: https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/NC1MAP_SEAMLESSPARCELS/FeatureServer/0
- **Sale history (partial-date-only):** date `DeedDate` non-null **172,003**. DeedDate (string) on SeamlessParcels; no sale price on any public REST layer; NC1MAP SALEDATE empty. Price/date via AppraisalCard PDF 'SALES DATA' section (see paDeepLink).
- **Owner entity:** fields `Name1`, `Name2`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **2,899** of 7,610 (extended regex: 3,140).
- **PA deep link:** `https://tax.brunsco.net/ITSNet/AppraisalCard.aspx?id={ParcelNumber}`. Tested `15600067` → HTTP **200** (application/pdf), content verified: True. FIX: existing card template ?parcel= returns HTTP 500 ('Object reference not set'); ?id= returns 200 application/pdf appraisal card with parcel ID + SALES DATA. Existing appraiserSearchUrl ITSNet/BasicSearch.aspx now 404 — search home is https://tax.brunsco.net/ITSNet/ (200).
- **Jurisdiction GIS viewer:** https://experience.arcgis.com/experience/0201d27723244840aea67c9f85892953 → HTTP **200** (Experience)
- **Pass 2 gaps:** No sale price on public REST (PA PDF only); Tax values on companion NC1MAP_SEAMLESSPARCELS layer, not SeamlessParcels; Card-level appraisalCardTemplate (?parcel=) returns HTTP 500 — use ?id=; ITSNet/BasicSearch.aspx 404 (use /ITSNet/)
