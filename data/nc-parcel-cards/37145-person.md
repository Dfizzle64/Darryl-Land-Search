# Person County, NC — GIS County Card

## Summary

Person County (Raleigh-Durham footprint, FIPS **37145**, slug **person**) publishes rich cadastral REST at `gis.personcountync.gov`. **Wire-first parcels:** **Tax/BitekParcelInfo** FeatureServer/1 — ~**28.5k** polygons with owner, postal mailing, **situs** (`Site_Address`), acreage, land/structure/other building values + assessed total, last sale price/date/code, and tax district. ~**6,018** with `Calculated_Area_in_Acres` 5–150 (~**3,627** with building area 0/null). **Cities-first:** only incorporated muni is **Roxboro** — zoning via **PlanZone/Zoning/1** (**686**, TYPE=City); unincorporated via **/2** (**126**, TYPE=County) + Conditional **/3** (**2**). **FLU:** county **FLUM** (**12** coarse polys). **NC OneMap** (`cntyfips='145'`) is a solid fallback. Markets: **Raleigh-Durham**.

## Portals

- **Public GIS viewer (jurisdiction homepage)** — https://gis.personcountync.gov/taxparcelviewer/
- **Viewer root (same WAB)** — https://gis.personcountync.gov/
- **GIS department portal** — https://www.personcountync.gov/gis
- **County ArcGIS REST** — https://gis.personcountync.gov/arcgis/rest/services
- **AGOL org** — https://persongis.maps.arcgis.com
- **PA / property search (NCPTS)** — https://lrcpwa.ncptscloud.com/person/parcel-search
- **PA deep-link** — `https://lrcpwa.ncptscloud.com/person/parcel-detail/{Record_Number}` (alt `{PIN}`)
- **CAMA / tax bill search (Tyler BT Taxpayer Portal)** — https://www.bttaxpayerportal.com/ITSPublicPR
- **Tax Office property records** — https://www.personcountync.gov/government/departments-i-z/tax/property-records-search
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)
- **City/town GIS:** no dedicated Roxboro city GIS host — use county viewer + PlanZone City of Roxboro layer

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `Record_Number`/`RECN`, `TaxMapParcel`; OneMap `parno` | Prefer **PIN** (####-##-##-####.###); Record_Number for NCPTS |
| polygons | Yes | Tax/BitekParcelInfo FS/1 | CRS **WKID 102100 / 3857** on FS |
| acreage | Yes | `Calculated_Area_in_Acres`, `Stated_Area` | ~**6,018** CALC 5–150 |
| ownerName | Yes | `Primary_Owner` (+ Secondary_Owner); OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `Postal_Address` + city/state/zip | Structured |
| situs address | Yes | `Site_Address` | **On primary parcel layer** (OneMap `scity` blank) |
| lastSale date/price | Yes (last) | `Sale_Price`, `Sale_Date`, `Sales_Code`, DeedBook/Page | Sale_Price>0 in ~2.9k of 5–150; Q≈qualified |
| tax values | Yes | `Current_Assessed_Value`, `Land_Value`, `Current_Structure_Value`, `Other_Building_Value` | Total ≈ land+structure+other |
| zoning | Yes | PlanZone Roxboro ZONECLASS; county Zoning ZONECLASS | Cities-first: Roxboro L1 inside city limits |
| flu | Yes (coarse) | FLUM `FLU` / `FLU_Code` | 12 countywide polys; no city FLU FS |
| appraiser / viewer link | Yes | NCPTS parcel-detail by Record_Number/PIN; Tax Parcel Viewer; BT portal | Templates below |

### Zoning inventory (verified)

| Layer | Count | TYPE | Notes |
|-------|-------|------|-------|
| City of Roxboro (FS/1) | **686** | City | **PRIMARY city-first** |
| County Zoning (FS/2) | **126** | County | Unincorporated |
| Conditional District (FS/3) | **2** | County | CD-RC, CD-GI |
| EnerGov ZoningDistrict (L9) | **812** | City 686 + County 126 | Combined mirror |

### Roxboro ZONECLASS (top)

| ZONECLASS | ZONEDESC | Count |
|-----------|----------|-------|
| R-6 | Residential District | 239 |
| R-12 | Residential Agricultural District | 164 |
| B-1 | Highway Business District | 137 |
| I-2 | Heavy Industrial District | 39 |
| I-1 | Light Industrial District | 31 |
| O/I | Office/Institutional District | 30 |
| B-2 | Neighborhood Business District | 16 |
| B-3 | Uptown Business District | 15 |
| R-8 / PUD / other | — | ≤5 each |

### County ZONECLASS

| ZONECLASS | ZONEDESC | Count |
|-----------|----------|-------|
| B1 | Highway Commercial Business District | 68 |
| GI | General Industrial District | 22 |
| RC | Rural Conservation | 16 |
| B2 | Neighborhood Shopping | 11 |
| R | Residential District | 8 |
| AP | Airport District | 1 |

### Tax_District_Description (municipality inventory)

| District | Parcels |
|----------|---------|
| COUNTY (unincorporated) | 23,763 |
| ROXBORO | 4,482 |
| (null) | 211 |

## Layers (verified)

### 1. Tax/BitekParcelInfo Tax Parcels — parcels + ownership + tax + situs + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | situs
- **REST URL (wire-first):** https://gis.personcountync.gov/arcgis/rest/services/Tax/BitekParcelInfo/FeatureServer/1
- **MapServer twin:** …/Tax/BitekParcelInfo/MapServer/1
- **Layer name / id:** Tax Parcels / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (joins OneMap `parno`)
  - `Record_Number` / `RECN` → NCPTS deep-link key (~28,245 non-null)
  - `TaxMapParcel` → alternate map/parcel label (e.g. `A69 53`)
  - `Calculated_Area_in_Acres`, `Stated_Area` → acreage
  - `Primary_Owner`, `Secondary_Owner` → ownerName
  - `Postal_Address`/`Postal_City`/`Postal_State`/`Postal_Zip` → mailing
  - `Site_Address` → situs
  - `Sale_Price`, `Sale_Date`, `Sales_Code`, `DeedBook`/`DeedPage` → lastSale
  - `Land_Value`, `Current_Structure_Value`, `Other_Building_Value`, `Current_Assessed_Value` → tax
  - `Assessing_Use_*`, `Property_Class_*` → local use / class
  - `Tax_District_Description` → COUNTY vs ROXBORO
- **WKID / CRS:** 102100 / 3857
- **Verified:** yes — count **28,456**; CALC 5–150 → **6,018**; BLDG area 0/null in range → **3,627**; Structure Value 0/null → **3,699**; Sale_Price>0 in range → **2,935**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. Geo-check sample PIN `0905-06-38-3375.000` centroid ≈ **-78.98854, 36.38306** (Roxboro / Person). EnerGov FS/8 is attribute twin (~28,245) — prefer BitekParcelInfo.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Key fields:** `parno`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`/`scity`, `gisacres`, `saledate`, `parval`/`landval`/`improvval`, `cntyfips`=`145`
- **Verified:** yes — filter count **28,272**; gisacres 5–150 → **5,990**; improvval=0/null in range → **2,939**
- **Notes:** Fallback when county host flaky. No sale price. `scity` blank for Person. MaxRecordCount **5000**. PIN join verified.

### 3. PlanZone City of Roxboro — city zoning (PRIMARY city-first)

- **Purpose:** zoning
- **REST URL:** https://gis.personcountync.gov/arcgis/rest/services/PlanZone/Zoning/FeatureServer/1
- **Fields:** `ZONECLASS`, `ZONEDESC`, `TYPE`, `LASTUPDATE`
- **WKID / CRS:** 102100 / 3857
- **Join to parcels:** spatial join (intersect/centroid) in 3857; gate with City Limits `Inc_Muni='Roxboro'` or Tax_District_Description=`ROXBORO`
- **Verified:** yes — **686**
- **Notes:** No separate Roxboro city GIS — this county layer **is** the public city zoning REST.

### 4. PlanZone Zoning — county / unincorporated

- **REST URL:** https://gis.personcountync.gov/arcgis/rest/services/PlanZone/Zoning/FeatureServer/2
- **Verified:** count **126** (TYPE=County)
- **Notes:** Use outside Roxboro city limits.

### 5. PlanZone Conditional District

- **REST URL:** https://gis.personcountync.gov/arcgis/rest/services/PlanZone/Zoning/FeatureServer/3
- **Verified:** count **2** (CD-RC, CD-GI)

### 6. EnerGov ZoningDistrict — combined mirror

- **REST URL:** https://gis.personcountync.gov/arcgis/rest/services/EnerGov/EnerGov/FeatureServer/9
- **Verified:** count **812** (City 686 + County 126)
- **Notes:** Optional single-stack alternative; prefer PlanZone split for city-first routing.

### 7. PlanZone FLUM — county FLU (PRIMARY)

- **Purpose:** flu
- **REST URL:** https://gis.personcountync.gov/arcgis/rest/services/PlanZone/FLUM/FeatureServer/0
- **Fields:** `FLU`, `FLU_Code`
- **Verified:** count **12**
- **Join:** spatial join in 3857
- **Notes:** Coarse policy polygons (ACA, C, CMP, GA, HLR, I, MLR, RA, RN, UC, UMU, UT). Covers city + county — no Roxboro city FLU FS.

### 8. AdminArea City Limits (Roxboro)

- **REST URL:** https://gis.personcountync.gov/arcgis/rest/services/AdminArea/CityLimits/FeatureServer/0
- **Fields:** `Inc_Muni`, `MUNITYP`, `MUNIAREA`
- **Verified:** 6 multipart polys, all Roxboro
- **Notes:** Only incorporated municipality in Person County.

## Cities / towns first-class routing

| Muni | Prefer for zoning | Prefer for FLU | Parcel host |
|------|-------------------|----------------|-------------|
| **Roxboro** | PlanZone Zoning FS/1 `TYPE='City'` (686) | County FLUM | Tax/BitekParcelInfo |
| Unincorporated / CDPs (Timberlake, Semora, etc.) | PlanZone Zoning FS/2 (+ Conditional FS/3) | County FLUM | Tax/BitekParcelInfo |

No dedicated public ArcGIS host for Roxboro city GIS — **county PlanZone/Zoning/1 is first-class for Roxboro**.

## Gaps

- **Only Roxboro is incorporated** — no other city FeatureServers.
- **No Roxboro city GIS host** — county PlanZone is the public city zoning REST.
- **FLUM coarse (12 polys)** — not parcel-grain; no municipal FLU FS.
- **~211 null tax district / missing Record_Number** — prefer PIN.
- **No multi-transfer sales history REST** — last sale on parcel only.
- **Sales_Code legend not fully published** — `Q` appears qualified; treat others as opaque.
- **OneMap `scity` blank** for Person — use `siteadd` / county `Site_Address`.
- **County FS CRS = 3857** — reproject before overlay on OneMap 2264.
- **personcountync.gov often 403** to automated fetchers — prefer `gis.personcountync.gov`.
- **Owner phones/emails** not collected (do not scrape NCPTS/BT PII beyond public REST fields).
- **MaxRecordCount 2000** on county layers — paginate.
- **No paid vendor data** used; **no AADT / utilities dig** in this card.

## Hand-off notes for Land Search Builder

1. **Wire first:** `Tax/BitekParcelInfo/FeatureServer/1` — polygons + owner, mailing, **situs**, acreage, land/structure/other tax, last sale. Filter `Calculated_Area_in_Acres BETWEEN 5 AND 150` (~6.0k). Optional vacant-ish: `Building_Area = 0 OR IS NULL` (~3.6k in range) or `Current_Structure_Value = 0 OR IS NULL` (~3.7k).
2. **Zoning (cities-first):** inside Roxboro → PlanZone FS/1; unincorporated → FS/2 (+ FS/3 CD overlay). Optional EnerGov L9 combined.
3. **FLU:** spatial join PlanZone FLUM (`FLU` / `FLU_Code`); expect coarse regions.
4. **Sales:** use `Sale_Price`/`Sale_Date`/`Sales_Code` on parcel; code `Q` ≈ qualified.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='145'` (PIN↔parno).
6. **Viewer / appraiser links:**
   - NCPTS detail: `https://lrcpwa.ncptscloud.com/person/parcel-detail/{Record_Number}`
   - Alt: `https://lrcpwa.ncptscloud.com/person/parcel-detail/{PIN}`
   - Search: `https://lrcpwa.ncptscloud.com/person/parcel-search`
   - BT Taxpayer / CAMA Basic Search: `https://www.bttaxpayerportal.com/ITSPublicPR`
   - GIS Viewer: `https://gis.personcountync.gov/taxparcelviewer/`
7. **Join keys:** `PIN` (preferred), `Record_Number`/`RECN`, `TaxMapParcel`, OneMap `parno`↔`PIN`.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities/towns are first-class:** Roxboro = PlanZone/Zoning/1; no separate city host.

verifiedAt: **2026-09-24** · verifiedBy: **North Carolina Public Info Researcher**

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='PERSON'`, field `AADT_2022` (string) — **335 stations live**, 129 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27PERSON%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27PERSON%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Person'`, `AADT_2025` (int) — 335 stations; 205 with 2025, 195 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://gis.personcountync.gov/arcgis/rest/services/Tax/BitekParcelInfo/FeatureServer/1` — total 28456, 5–150 ac 6018 (`Calculated_Area_in_Acres>=5 AND Calculated_Area_in_Acres<=150`).
- Non-zero county: `Land_Value` 28040, `Current_Structure_Value` 18027, `Current_Assessed_Value` 28040; in 5–150: `Current_Assessed_Value` 5822. **Status: ok.**
- Double fields; Current_Assessed_Value ≈ land+structure+other.

### 3. Sale history
- Price `Sale_Price`>0 16364 (5–150: 2935); date non-null `Sale_Date` 27219. **Status: ok.**
- Sale_Date STRING MM/DD/YYYY; Sale_Price double; Sales_Code 'Q' ≈ qualified. Last sale only.

### 4. Owner entity
- Owner fields: `Primary_Owner`, `Secondary_Owner`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 868** (of 5929 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: `https://lrcpwa.ncptscloud.com/person/parcel-detail/{Record_Number}`
- Tested `https://lrcpwa.ncptscloud.com/person/parcel-detail/10020` → **200**. HTTP 200; NCPTS PWA shell (content client-rendered; not server-verifiable). Alt BT CAMA: https://www.bttaxpayerportal.com/ITSPublicPR

### 6. Jurisdiction GIS viewer
- `https://gis.personcountync.gov/taxparcelviewer/` → **200**. Person County tax parcel viewer (ArcGIS Web App)

### Pass2 gaps
- AADT_2022 blank at 206 of 335 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- No multi-transfer sale history on primary layer (last sale only)
