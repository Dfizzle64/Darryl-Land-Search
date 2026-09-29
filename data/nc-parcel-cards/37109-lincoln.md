# Lincoln County, NC — GIS County Card

## Summary

Lincoln County (Charlotte MSA, FIPS **37109**) publishes a strong **public** ArcGIS REST stack at `arcgisserver.lincolncountync.gov`: countywide **parcel polygons + CAMA** (owner, mailing/situs, deed/mapped acres, land/improvement/total values, last sale date/price/qualified code, and a parcel-joined `ZONING` string) on `Server_OperationalSP` / `Server_TaxParcelViewerSP` layer **Parcels / TaxParcelPublishing**. **Zoning is city-first** — separate **City of Lincolnton** and **County (unincorporated)** polygon layers, plus a combined `RevalLayers/Zoning Districts` that also tags a tiny **Maiden** footprint. **FLU** is public: county **LandUsePlan2022** (Blueprint 2043) and **LincolntonLandUsePlan**. **NC OneMap** (`cntyfips='109'`) is a solid fallback. Main gaps: **Maiden** zoning/FLU almost absent on Lincoln REST (town is mostly Catawba); parcel `ZONING` strings are multi-code concatenations (prefer spatial join for clean codes); no independent City of Lincolnton FeatureServer (defers to county host).

## Portals

- **Tax Parcel Viewer** — https://arcgisserver.lincolncountync.gov/taxparcelviewer/ — Interactive parcels/sales. Property card: `https://arcgisserver.lincolncountync.gov/taxparcelviewer/PropertyReport.aspx?akpar={AKPAR_}&vacinity=false`
- **County ArcGIS REST** — https://arcgisserver.lincolncountync.gov/arcgis/rest/services
- **GIS Download Page** — https://www.lincolncountync.gov/470/GIS-Download-Page — Shapefiles (parcels, zoning for county/Lincolnton/Maiden, addresses, jurisdictions) + Excel parceldata/sales/improvements
- **Planning / Land Use Plan (Blueprint 2043)** — https://www.lincolncountync.gov/387/Land-Use-Plan
- **Development Services / Planning** — https://lincolncountync.gov/104/Planning-and-Inspections
- **City of Lincolnton** — https://www.lincolntonnc.org/ (no separate public ArcGIS host found; zoning/FLU via county REST)
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` (10-digit NC PIN), `PARCELID`/`AKPAR_` (account) | Prefer `PIN` for statewide joins; `AKPAR_` for PropertyReport |
| polygons | Yes | Server_OperationalSP/6 or TaxParcelViewerSP/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `MAPPEDACRE` (GIS), `ACRE` (deed) | ~**6,564** parcels with `MAPPEDACRE` 5–150; ~**5,109** with `ACRE` 5–150 |
| ownerName | Yes | `NAME1`+`NAME2` / OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `ADDRESS1`,`ADDRESS2`,`CITY`,`STATE`,`ZIP` | |
| situs address | Yes | `PHYSICALADDR` / `STREETNUM`+`STREETNAME` / OneMap `siteadd` | Also Structures/SiteAddressPoint if needed |
| lastSale date/price | Yes | `SDATE`,`SALEPRICE`,`QUALIFIEDCODE`; history on TaxParcelViewer Sales | Filter `QUALIFIEDCODE` / `SALEPRICE>0` for comps |
| tax values | Yes | `LANDVALUE`,`IMPROVALUE`,`TOTALVALUE`,`LANDASSESSED` | Tax year on `TAXYEAR` |
| zoning | Yes (split) | Parcel `ZONING` (joined string) **or** City/County/Reval polygon `ZONECODE` | Cities first-class — see Municipalities |
| flu | Yes | County `LUP_2022`; Lincolnton `LANDUSECODE`/`LANDUSEDESC` | Maiden FLU gap |
| appraiser / viewer link | Yes | PropertyReport by `AKPAR_` | Template below |

## Layers (verified)

### 1. Server_OperationalSP Parcels — parcels + ownership + tax + sale + zoning string (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | zoning (joined string)
- **REST URL:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/6
- **Mirror (same schema):** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_TaxParcelViewerSP/MapServer/0 (TaxParcelPublishing); also layers 1–2
- **Layer name / id:** Parcels / 6
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (10-digit NC PIN)
  - `PARCELID`, `AKPAR_` → tax account / PropertyReport key
  - `MAPPEDACRE`, `ACRE` → acreage (prefer GIS `MAPPEDACRE` for 5–150 filter)
  - `NAME1`, `NAME2` → ownerName
  - `ADDRESS1`, `ADDRESS2`, `CITY`, `STATE`, `ZIP` → mailing
  - `PHYSICALADDR`, `STREETNUM`, `STREETNAME` → situs
  - `SDATE`, `SALEPRICE`, `QUALIFIEDCODE` → lastSale
  - `LANDVALUE`, `IMPROVALUE`, `TOTALVALUE`, `LANDASSESSED` → tax
  - `ZONING` → zoning (may be multi-code / overlay-prefixed, e.g. `ELDD B-G & R-SF`)
  - `VACANT` (`YES`|`NO`), `DISTRICT`, `TOWNSHIP`, `DEEDBK`/`DEEDPG` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **56,998**; `MAPPEDACRE BETWEEN 5 AND 150` → **6,564**; `SALEPRICE>0` in range → **2,131**; non-null `ZONING` → **54,039**; sample owner/mail/situs/tax/sale OK
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2500**. Parcel `ZONING` is convenient but concatenated — for clean single codes spatial-join City/County Zoning. `VACANT='YES'` → **14,748** total / **3,241** in 5–150.

### 2. ComDevData MAININFOLIVE_VIEW_FC — same CAMA view (alternate)

- **Purpose:** parcels | tax | ownership | sales
- **REST URL:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/ComDevData/MapServer/25
- **Verified:** yes — count **56,998**; same field family; MaxRecordCount **1000**
- **Notes:** Prefer OperationalSP/6 for higher page size.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parno` → parcelId (aligns with county `PIN`)
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs
  - `gisacres` → acreage (~**6,543** in 5–150)
  - `saledate`,`saledatetx` → lastSale.date (**no sale price**)
  - `parval`,`landval`,`improvval` → tax
  - `cntyfips`=`109`, `cntyname` → Lincoln filter
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — filter count **56,862**; sample OK
- **Notes:** Excellent fallback. May lag county CAMA. MaxRecordCount **5000**.

### 4. City Zoning Districts — Lincolnton zoning (city-first)

- **Purpose:** zoning (Lincolnton)
- **REST URL:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/23
- **Mirrors:** ComDev/MapServer/28; TRACKiT/MapServer/28
- **Geometry:** Polygon
- **Key fields → targets:** `ZONECODE` → zoning; `CUSE` → conditional use; `JURISDICTION` (`LINCOLNTON`/`CITY`)
- **Verified:** yes — count **779** (LINCOLNTON **776** + CITY **3**)
- **Sample codes:** C-B, CBT, CC, G-B, GMC, H-C, N-B, O-I, P-B, PRD, R-8/10/15/25, R-O, RMF, TID
- **Notes:** **City-only zoning + county parcels** — spatial join in 2264. Also City Conditional Use Districts layer **22** (count **780**).

### 5. County Zoning Districts — unincorporated zoning

- **Purpose:** zoning (unincorporated Lincoln)
- **REST URL:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/25
- **Mirrors:** ComDev/MapServer/29
- **Geometry:** Polygon
- **Key fields → targets:** `ZONECODE` → zoning; `CUSE`; `JURISDICTION` (`COUNTY`/`LINCOLN`)
- **Verified:** yes — count **2,272**
- **Sample codes:** B-G, B-N, I-G, I-L, N-Z, O-R, PD-C/I/MU/R, R-14/20/CR/MF/MR/R/S/SF/T
- **Notes:** Unincorporated only — **not** Lincolnton. County Conditional Use Districts layer **24** (count **215**). Overlays (ELDD, SAP, etc.) on layer **19** (count **8**).

### 6. RevalLayers Zoning Districts — combined county + city + Maiden tag

- **Purpose:** zoning (combined)
- **REST URL:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/RevalLayers/MapServer/59
- **Mirror:** ComDevData/MapServer/13 (count **3,114**)
- **Geometry:** Polygon
- **Key fields → targets:** `ZONECODE`, `JURISDICTION`, `CUSE`
- **Verified:** yes — count **3,114**; JURISDICTION counts: COUNTY **2267**, LINCOLNTON **776**, MAIDEN **1**, LINCOLN **5**, CITY **3**
- **Notes:** Convenient single layer. **Maiden = 1 polygon only** on this REST — treat Maiden as gap for full town zoning (Catawba).

### 7. LandReport ZoningReport — parcel∩zoning join (convenience)

- **Purpose:** parcels | zoning
- **REST URL:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/LandReport/MapServer/0
- **Key fields:** `PARCELID`,`PIN`,`ZONECLASS`,`ZONEDESC`,`JURISDICTION`,`CONDITIONAL_USE`,`ACREAGE`
- **Verified:** yes — count **55,999**; non-null `ZONECLASS` **55,625**; JURISDICTION LINCOLNTON **8,266**, COUNTY **47,159**, MAIDEN **9**
- **Notes:** Parcel-level zone class from spatial join. Prefer for attribute join on `PARCELID`/`PIN` when polygon zoning is heavy. Some empty PIN stubs.

### 8. LandUsePlan2022 — county FLU (Blueprint 2043)

- **Purpose:** flu
- **REST URL:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/35
- **Mirror:** RevalLayers/MapServer/60
- **Geometry:** Polygon
- **Key fields → targets:** `LUP_2022` / `Label` → flu
- **Verified:** yes — count **48,745**
- **Codes (counts):** LLR 15911, SFN 14942, RL 14136, SC 1070, IC 904, MFN 869, WC 253, SD 204, RC 190, OS 159, WN 96, SO 10
- **Notes:** County future land use / place types. Spatial join to parcels (or already near parcel density). Policy PDF: Blueprint 2043 / FLUM on county Land Use Plan page.

### 9. LincolntonLandUsePlan — city FLU

- **Purpose:** flu (Lincolnton)
- **REST URL:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/38
- **Related (older/alt):** ComDevData/MapServer/11 Proposed Land Use (count **251**)
- **Geometry:** Polygon
- **Key fields → targets:** `LANDUSECODE`,`LANDUSEDESC` → flu; optional `PARCELID` join
- **Verified:** yes — count **137**
- **Codes include:** CB, CBT, GB, IND, IO, MURC, NB, NBC, PB, RHD, ROS, RR, RS, TSF
- **Notes:** **City-only FLU + county parcels** — spatial join in 2264 (or attribute join when `PARCELID` present).

### 10. Qualified Sales / TaxParcelViewer Sales — sale history

- **Purpose:** sales
- **REST URLs:**
  - https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/11 — Qualified Sales (count **50,333**)
  - https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_TaxParcelViewerSP/MapServer/3 — Sales (count **1,416,245**)
  - Table: Server_Tables/MapServer/4 Sales (count **315,655**, no geometry)
- **Key fields:** `PIN`,`AKPAR_`,`AMDTSL` (sale date int), `AMSLAM` (amount), `AMQFCD` (qualified), `VACANT`, acreage fields
- **Verified:** yes — sample AMSLAM/AMDTSL returned
- **Notes:** Use for multi-sale history; keep parcel `SDATE`/`SALEPRICE` as lastSale. Join on `PIN`/`AKPAR_`.

### 11. Municipal Boundaries — jurisdiction aid

- **Purpose:** other (municipality / township filter)
- **REST URL:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/16
- **Fields:** `NAME`, `TYPE` (`City`|`Township`)
- **Verified:** yes — count **22**; City names include **Lincolnton**, **Lincolnton ETJ**, **Maiden**; townships: Catawba Springs, Howards Creek, Ironton, North Brook, Lincolnton
- **Notes:** Denver / East Lincoln / etc. appear as **tax DISTRICTs** on parcels, not incorporated cities. Use `TYPE='City'` for municipal routing.

### 12. Address points (optional situs enrich)

- **Structures:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/0 — `FullAddress` / `LST_FullAddress`
- **SiteAddressPoint:** https://arcgisserver.lincolncountync.gov/arcgis/rest/services/ComDevData/MapServer/2 — count **46,685**; `FULLADDR`,`MUNICIPALITY`,`ZIP`
- **Notes:** Primary parcels already carry `PHYSICALADDR`; use points when situs null.

## Municipalities (first-class)

County parcels are **county-wide**. **Zoning and city FLU are municipal** — Lincolnton owns city zoning/FLU; unincorporated uses county UDO zoning + county LandUsePlan2022; Maiden’s Lincoln footprint is tiny on public REST.

| Municipality | Zoning REST (preferred) | Field → zoning | FLU REST? | Own GIS? | Notes |
|--------------|-------------------------|----------------|-----------|----------|-------|
| Unincorporated Lincoln | …/Server_OperationalSP/**25** (+ CUD **24**, overlays **19**) | `ZONECODE` | Yes — LandUsePlan2022 /35 | County host | Includes Denver CDP & rural areas |
| City of Lincolnton | …/Server_OperationalSP/**23** (+ CUD **22**) | `ZONECODE` | Yes — LincolntonLandUsePlan /38 | Defers to county REST | City site lincolntonnc.org; ETJ on Municipal Boundaries |
| Town of Maiden (Lincoln edge) | RevalLayers/**59** filter `JURISDICTION='MAIDEN'` | `ZONECODE` | **No** (gap) | No Lincoln-side host | **1** zoning poly / **9** ZoningReport rows — most of Maiden is **Catawba County** |

**Combined zoning shortcut:** RevalLayers/59 or ComDevData/13 (`ZONECODE` + `JURISDICTION`) or LandReport ZoningReport (`ZONECLASS` by `PARCELID`).

**City-only zoning / county parcels join checklist**

1. Query parcels from OperationalSP/6 (`PIN`,`AKPAR_`, geometry, CAMA), filter `MAPPEDACRE BETWEEN 5 AND 150`.
2. Route jurisdiction: Municipal Boundaries/16 (`TYPE='City'`) or parcel `DISTRICT` / situs, or use combined ZoningReport / Reval `JURISDICTION`.
3. Spatial-join matching zoning layer in **WKID 2264** (or use parcel `ZONING` / ZoningReport `ZONECLASS` for attribute path).
4. FLU: spatial-join LandUsePlan2022 countywide; overlay LincolntonLandUsePlan inside city/ETJ; leave Maiden null or resolve via Catawba.
5. Do **not** treat county Zoning/25 alone as countywide coverage.

## Gaps

- **Maiden zoning/FLU nearly absent on Lincoln REST** — 1 Reval polygon / 9 ZoningReport; town primarily Catawba; no public Maiden FLU REST found.
- **Parcel `ZONING` is multi-value / overlay-prefixed** — good for display; prefer polygon `ZONECODE` or ZoningReport `ZONECLASS` for analytics.
- **No independent City of Lincolnton ArcGIS host** — city layers published through county server only.
- **Denver / East Lincoln / Alexis / etc.** are communities/tax districts, not incorporated municipalities with separate zoning REST.
- **OneMap has no sale price** — use county `SALEPRICE` / Sales layers.
- **Owner phones/emails** not on these APIs (correct — do not scrape).
- **MaxRecordCount** 1000–2500 on most layers; OneMap 5000 — paginate.
- **No paid vendor data** used (CoreLogic/Regrid/ATTOM avoided).

## Hand-off notes for Land Search Builder

1. **Wire first:** `https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/6` — polygons + owner/mail/situs/acreage/tax/sale/zoning-string. Filter `MAPPEDACRE BETWEEN 5 AND 150` (~6.6k).
2. **Zoning (cities first-class):** spatial join City Zoning/23 for Lincolnton and County Zoning/25 for unincorporated; or RevalLayers/59 / LandReport ZoningReport by `PARCELID`. Do not assume county zoning covers Lincolnton.
3. **FLU:** spatial join LandUsePlan2022/35; add LincolntonLandUsePlan/38 inside city; Maiden = gap.
4. **Sale history (optional):** TaxParcelViewerSP/3 or OperationalSP/11 on `PIN`/`AKPAR_`.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='109'`.
6. **Viewer / appraiser:** `https://arcgisserver.lincolncountync.gov/taxparcelviewer/PropertyReport.aspx?akpar={AKPAR_}&vacinity=false` and map https://arcgisserver.lincolncountync.gov/taxparcelviewer/
7. **Join keys:** `PIN` (NC PIN / OneMap `parno`), `PARCELID`/`AKPAR_` (PropertyReport), geometry for zoning/FLU.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities are first-class:** never treat county Zoning Districts alone as countywide coverage.

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='LINCOLN'`, field `AADT_2022` (string) — **399 stations live**, 135 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27LINCOLN%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27LINCOLN%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Lincoln'`, `AADT_2025` (int) — 394 stations; 239 with 2025, 243 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/6` — total 57019, 5–150 ac 6567 (`MAPPEDACRE>=5 AND MAPPEDACRE<=150`).
- Non-zero county: `LANDVALUE` 53602, `IMPROVALUE` 44340, `TOTALVALUE` 56542, `LANDASSESSED` 53602; in 5–150: `LANDASSESSED` 6509. **Status: ok.**
- Integer fields LANDVALUE/IMPROVALUE/TOTALVALUE/LANDASSESSED.

### 3. Sale history
- Price `SALEPRICE`>0 27613 (5–150: 2138); date non-null `SDATE` 56016. **Status: ok.**
- SDATE STRING MM/DD/YYYY; SALEPRICE integer. Multi-sale history also on Server_TaxParcelViewerSP/MapServer/3 (AMSLAM price, AMDTSL date int).

### 4. Owner entity
- Owner fields: `NAME1`, `NAME2`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 958** (of 6537 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: `https://arcgisserver.lincolncountync.gov/taxparcelviewer/PropertyReport.aspx?akpar={AKPAR_}&vacinity=false`
- Tested `https://arcgisserver.lincolncountync.gov/taxparcelviewer/PropertyReport.aspx?akpar=53288&vacinity=false` → **200**. HTTP 200; report page populates via JS (owner not in server HTML).

### 6. Jurisdiction GIS viewer
- `https://arcgisserver.lincolncountync.gov/taxparcelviewer/` → **200**. Lincoln County GIS tax parcel viewer

### Pass2 gaps
- AADT_2022 blank at 264 of 399 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- Last sale on primary layer; separate sales layer documented in saleHistory.notes
