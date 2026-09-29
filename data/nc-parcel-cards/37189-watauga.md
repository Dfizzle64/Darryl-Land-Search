# Watauga County, NC — GIS County Card

## Summary

Watauga County (Boone / Asheville shed, FIPS **37189**, slug **watauga**, `cntyfips='189'`) publishes a strong public **Avineon** GIS + Patriot/Schneider CAMA stack at **`gissvr.watgov.org`** / **`tax.watgov.org`**. **Wire-first parcels + CAMA:** `TaxParcels/parcelsdbf/FeatureServer/0` — ~**47,364** polys with `PIN`/`PID`/`PARCELID`, owner, mailing, situs, `TX_ACREAGE`, land/bldg/total tax + appraisal values, **`SALEPRICE`/`DATERECORD`**, deed book/page, and attributed `ZONE` (muni-prefixed). ~**7,413** with acres 5–150 (~**2,817** with `SALEPRICE>0` in range). **Cities-first zoning:** prefer **Town of Boone** native `planning/Zoning_Mobile` / `Boone_Zoning` (`ZONE_TYPE`); Blowing Rock / Beech Mountain / Seven Devils via parcel `ZONE` prefixes (`BR*`/`BM*`/`SD*`) + county `Zoned Municipalities`; Foscoe–Grandfather Corridor (`FC-*`) is county zoning. **FLU:** no public REST — **2025 Comprehensive Plan PDF** gap. **PA deep-link:** `https://tax.watgov.org/WataugaNC/datalets/datalet.aspx?mode=summary&UseSearch=no&pin={PID}&jur=095&taxyr=2026` (unhyphenated PID). **Jurisdiction GIS:** `https://gissvr.watgov.org/maps/`. **NC OneMap** `cntyfips='189'` geometry/owner/tax/saledate fallback (no sale price). Markets: **[Boone, Asheville]**.

## Portals

- **Jurisdiction GIS (Avineon Web Map)** — https://gissvr.watgov.org/maps/
- **Tax Search (same viewer #1)** — https://gissvr.watgov.org/maps/#1
- **Legacy Patriot map** — https://tax.watgov.org/WataugaNC/maps/mapadv.aspx
- **County ArcGIS REST** — https://gissvr.watgov.org/arcgis/rest/services
- **PA / Datalet Property Summary** — https://tax.watgov.org/WataugaNC/datalets/datalet.aspx — Deep link: `https://tax.watgov.org/WataugaNC/datalets/datalet.aspx?mode=summary&UseSearch=no&pin={PID}&jur=095&taxyr=2026`
- **PA Sales tab** — `https://tax.watgov.org/WataugaNC/datalets/datalet.aspx?mode=sales&UseSearch=no&pin={PID}&jur=095&taxyr=2026`
- **PA search (disclaimer → commonsearch)** — https://tax.watgov.org/WataugaNC/Search/Disclaimer.aspx?FromUrl=../search/commonsearch.aspx?mode=owner
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/watauga/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/watauga/parcel-detail/{PIN}`
- **Tax Administration / Land Records** — https://www.wataugacounty.org/App_Pages/Dept/Tax/landrecords.aspx
- **Planning and Inspections** — https://www.wataugacounty.org/App_Pages/Dept/Planning/home.aspx
- **2025 Comprehensive Plan (Citizen Plan PDF)** — https://www.wataugacounty.org/App_Pages/Dept/Planning/comprehensiveplan.aspx → `Forms/WataugaCitizenPlan.pdf`
- **Gateway corridor plans** — https://www.wataugacounty.org/App_Pages/Dept/Planning/gatewayplan.aspx
- **Town of Boone GIS Viewer** — https://gisviewer.boonenc.gov/maps/default.htm (alt host `gisviewer.townofboone.net`)
- **Boone ArcGIS REST** — https://gisviewer.townofboone.net/arcgis/rest/services
- **Boone GIS department** — https://www.townofboone.net/190/Geographic-Information-Systems-GIS
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='189'`)
- **High Country COG (corridor / Seven Devils limits)** — https://services1.arcgis.com/vj28eVZMB2OMIUh5/arcgis/rest/services

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`/`PARCELID`; `PID` (no hyphens); OneMap `parno`/`altparno` | Prefer **PIN** for map/OneMap; **PID** for Datalet PA |
| polygons | Yes | parcelsdbf FS/0; SalesComp Tax Parcels; OneMap | CRS **102719 / 2264** |
| acreage | Yes | `TX_ACREAGE`; OneMap `gisacres` | ~**7,413** in 5–150 |
| ownerName | Yes | `TXACCTNAME`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `TXADDRESS`/`TXADDRESS2`/`TXCITYST`/`TXZIP` | |
| situs address | Yes | `PROPADDRES`; OneMap `siteadd` | ~**29,507** non-empty situs |
| lastSale date/price | Yes | `DATERECORD`/`SALEPRICE`; SalesComp sales layer | ~**23,593** with `SALEPRICE>0` |
| tax values | Yes | `TAXTOTAL`/`TAXLAND`/`TAXBLDG`; `APTOTALVAL`/`APLANDVAL`/`APBLDGVAL` | Typed ints |
| zoning | Yes (cities-first) | Boone `ZONE_TYPE`; parcel `ZONE` prefixes; FC corridor | ~**12,222** parcels with ZONE |
| flu | Partial / gap | Comp Plan PDF only | No public FLU FeatureServer |
| appraiser / viewer link | Yes | Datalet `{PID}`; NCPTS `{PIN}`; GIS maps/ | TRANCHE-3 |

### ZONE prefix → municipality (parcelsdbf attributed zoning)

| Prefix | Approx parcels | Zoning source (prefer) |
|--------|----------------|------------------------|
| **BM-*** | **4,356** | Beech Mountain (parcel attr; town zoning map retired/PDF) |
| **BO*** (BOR1/BOB3/…) | **3,792** | **Boone native** Zoning_Mobile/5 or Boone_Zoning/12 |
| **BR*** / BRR15 | **1,894** | Blowing Rock (parcel attr; Caldwell fringe OpenGov/11 = 17 polys only) |
| **E2*** | **1,881** | Boone ETJ (parcel attr; Boone ETJ polygons on county Zoned Municipalities) |
| **FC-*** | **292** | County Foscoe–Grandfather Corridor zoning |
| **SD-*** | **1** | Seven Devils (thin attr — gap; town limits via HCCOG) |
| *(blank)* | ~**35,142** | Unincorporated / verify spatially — often unzoned outside corridors |

## Layers (verified 2026-09-24)

### 1. TaxParcels/parcelsdbf — parcels + ownership + tax + sale (PRIMARY CAMA)

- **Purpose:** parcels | tax | ownership | sales | zoning attr
- **REST URL:** https://gissvr.watgov.org/arcgis/rest/services/TaxParcels/parcelsdbf/FeatureServer/0
- **MapServer twin:** …/TaxParcels/parcelsdbf/MapServer/0
- **Layer name / id:** parcelsdbf / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN`, `PARCELID` → parcelId
  - `PID` → parcelIdAlt / PA key (unhyphenated)
  - `TX_ACREAGE`, `ANNO_AREA` → acreage
  - `TXACCTNAME` → ownerName
  - `TXADDRESS`, `TXADDRESS2`, `TXCITYST`, `TXZIP` → mailing
  - `PROPADDRES` → situs
  - `DATERECORD`, `SALEPRICE`, `INSTRTYP` → lastSale
  - `DEEDBOOK`, `DEEDPAGE`, `DEED` → deed
  - `TAXLAND`, `TAXBLDG`, `TAXTOTAL` → tax (assessed)
  - `APLANDVAL`, `APBLDGVAL`, `APTOTALVAL` → tax (appraisal)
  - `ZONE`, `PCLCLASS`, `LANDUSE` → zoning / land-use hints
  - `TX_DIST`, `TWP`, `NBRHCODE`/`NBRHDESC` → district / neighborhood
  - `TXACCOUNT` → account number
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **47,364**; `TX_ACREAGE` 5–150 → **7,413**; `SALEPRICE>0` → **23,593** (in-range **2,817**); `TAXTOTAL>0` → **46,401**; `ZONE` non-empty → **12,222**
- **Notes:** **PRIMARY** for tax/sale/owner. MaxRecordCount **1000** — paginate. SSL on gissvr may need client trust; queries succeed with standard TLS.

### 2. SalesComp/ParcelSales — Tax Parcels twin + recent sales subset

- **REST root:** https://gissvr.watgov.org/arcgis/rest/services/SalesComp/ParcelSales/MapServer
- **Layer 1 Tax Parcels:** ~**48,002** — same CAMA family + embedded **`taxcard`** URL template with `{pid}`
- **Layer 0 Parcel Sales 2020-2021:** ~**3,592** sales subset with `saleprice`/`daterecorded` + dwelling attrs
- **taxcard pattern (from layer 1):** `https://tax.watgov.org/WataugaNC/Datalets/Datalet.aspx?mode=&UseSearch=no&pin={pid}&jur=095&taxyr=2022` — prefer **taxyr=2026** and `mode=summary` (verified live)
- **Notes:** Useful join/verify; prefer parcelsdbf for typed numeric sale/tax fields

### 3. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='189'`
- **Fields:** `parno`,`altparno`,`ownname`,`mailadd`/`mcity`/`mstate`/`mzip`,`siteadd`,`gisacres`,`parval`/`landval`/`improvval`,`saledate` (deed/sale date — populated), `cntyfips`
- **Verified:** yes — **47,388**; `gisacres` 5–150 → **7,474**; `parval>0` → **46,591**; `saledate IS NOT NULL` → **47,388**; **no saleprice field**
- **Notes:** Join `parno`↔`PIN`. Use county parcelsdbf for sale **price**.

### 4. Town of Boone — native zoning (prefer inside Boone)

- **Zoning Districts (PRIMARY):** https://gisviewer.townofboone.net/arcgis/rest/services/planning/Zoning_Mobile/MapServer/5 — `ZONE_TYPE`, `DESCRIPTION`, `DISTRICT`, `ALPHA`; count **407**
- **Boone_Zoning/12:** https://gisviewer.townofboone.net/arcgis/rest/services/gisviewer/Boone_Zoning/MapServer/12 — `ALPHA`, `DISTRICT`; count **407**
- **County mirror:** GIS_Map_Search_PRD/MapServer/36 Boone_Zoning — count **325** (prefer town host)
- **ZONE_TYPE codes (sample):** B3, R1, R3, OI, B1DI, R1A, RA, B1DC, B2, U1, M1, R2, R1C, B1, R1S, R5, E1/E2/E4, MH, PD, R4, WD
- **Overlays:** Conditional Use/Conditional/Corridor District/Watersheds/Viewshed on Zoning_Mobile 0–4 and Boone_Zoning
- **Join note:** Prefer Boone host where parcel `ZONE` starts with `BO` or situs in Boone limits; ETJ `E2*` also routes to Boone ETJ

### 5. County GIS_Map_Search_PRD — jurisdiction boundaries + Boone zoning mirror

- **REST URL:** https://gissvr.watgov.org/arcgis/rest/services/GIS_Map_Search_PRD/MapServer
- **Zoned Municipalities /13:** Boone City Limits, Boone ETJ, Town of Blowing Rock, Blowing Rock ETJ, Town of Beech Mtn, Town of Seven Devils, V.C. (Valle Crucis) Region/Historic, F.G.C. (Foscoe Grandfather Corridor) Highway/Rural/Industrial/Rural Residential
- **Zoned Boundaries /14:** same inventory (~70 polys)
- **Parcel Map /0:** geometry keyed by `ALPHA` (thin attrs — use parcelsdbf for CAMA)
- **Protected Ridges /23:** ridge overlay constraints (not zoning)

### 6. Boone MasterV2 / Parcels — CAMA mirror inside Boone fire/town context

- **MasterV2 Parcel Labels /23:** https://gisviewer.townofboone.net/arcgis/rest/services/gisviewer/MasterV2/MapServer/23 — countywide-ish CAMA attrs (~**47,216**); includes `ZONE`, `SALEPRICE`, tax fields
- **Parcels/1:** Boone-focused parcel boundaries (~**13,159**) with `ZONING_DIST` helper
- **Notes:** Prefer county parcelsdbf for countywide wire; Boone layers for city-context labels

### 7. High Country COG — corridor studies / Seven Devils limits (secondary)

- **SevenDevils_TownLimits:** https://services1.arcgis.com/vj28eVZMB2OMIUh5/arcgis/rest/services/SevenDevils_TownLimits/FeatureServer
- **GrandfatherCorridor_Data / DeepGapCorridor_Data / BlowingRockGatewayCorridor_VectorData:** study-area parcels & buffers — **not** substitute zoning/FLU layers

## Municipalities (cities-first)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| **Boone** | **Zoning_Mobile/5** (prefer) or Boone_Zoning/12 | 407 | **Yes** — gisviewer.boonenc.gov | No | County seat; BO* + E2* ETJ on parcels |
| **Blowing Rock** | Parcel `BR*` / BRR15; Caldwell OpenGov/11 fringe | ~1894 / 17 | Limited | No | Straddles Watauga/Caldwell; no Watauga BR polygon FS |
| **Beech Mountain** | Parcel `BM-*`; town zoning map retired | ~4356 | Partial (links to county) | No | Also Avery County; contact Planning for official zone |
| **Seven Devils** | HCCOG town limits; parcel `SD-*` thin | 1 attr | No public FS | No | Also Avery; zoning ordinance/PDF gap |
| Unincorporated / corridors | FC-* + Valle Crucis historic + gateway plans | 292 FC | County | Comp Plan PDF | Large unzoned remainder outside corridors |

## Gaps / caveats

- **FLU REST gap** — 2025 Comprehensive Plan / Citizen Plan is PDF-only; no county FLU FeatureServer
- Blowing Rock / Beech Mountain / Seven Devils lack public Watauga-hosted zoning polygons — use parcel `ZONE` prefixes + muni PDFs/ordinances; Caldwell hosts tiny BR fringe (17)
- Seven Devils `SD-*` attribution almost empty on parcelsdbf — verify spatially against HCCOG town limits
- Large share of parcels (~35k) have blank `ZONE` (unzoned unincorporated outside corridor/muni)
- OneMap has **saledate** but **no saleprice** — use parcelsdbf `SALEPRICE`
- Datalet HTML may show a maintenance banner while still returning parcel summary (verified owner/values for sample PID)
- Avineon viewer deep-link by PIN querystring not confirmed (SPA); open GIS then search, or use Datalet/NCPTS
- NCPTS is SPA — `parcel-detail/{PIN}` pattern matches other NC counties; Datalet `{PID}` is authoritative PA
- Utilities and AADT intentionally excluded; no emails/phones/paid vendors

## License / attribution

Watauga County Tax Administration / Land Records / GIS; Town of Boone GIS; High Country COG where used. Data for tax/reference — not a survey. Commercial resale subject to **NCGS 132-10**. Attribute Watauga County GIS / Tax.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 12+
- Live `returnCountOnly` + sample attribute queries against TaxParcels/parcelsdbf FS/0, SalesComp ParcelSales 0/1, GIS_Map_Search_PRD (Zoned Municipalities/Boone_Zoning), Boone Zoning_Mobile/5 + Boone_Zoning/12 + MasterV2/23, NC OneMap `cntyfips='189'`, and Datalet `?pin=`/`taxyr=2026` deep-link (owner GRULKE / values match).
