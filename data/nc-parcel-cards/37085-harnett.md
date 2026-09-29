# Harnett County, NC — GIS County Card

## Summary

Harnett County (Raleigh-Durham footprint, FIPS **37085**, slug **harnett**) publishes rich cadastral REST at `gis.harnett.org`. **Wire-first parcels:** **Tax/Parcels** MapServer/0 — ~**85.7k** polygons with owner, mailing parts, **situs** (PhysicalAddress + Par*), acreage, land/bldg market/assessed split, last sale, zoning attribute + `ZoningJurisdiction`, and tax account id. ~**11,663** with `CalculatedLandArea` 5–150 (~**7,659** with building value 0/null). **Zoning:** county **Planning/ZoningDistricts** (~9.4k, jurisdiction-coded) is the public REST for **Dunn, Lillington, Angier, Erwin, Coats** (no separate city FeatureServers found) plus unincorporated. **FLU:** county **Future LandUse** (~718). **NC OneMap** (`cntyfips='085'`) is a solid fallback. Markets: **Raleigh-Durham**.

## Portals

- **Public GIS viewer (jurisdiction homepage)** — https://gis.harnett.org/gisviewer/
- **GIS department portal** — https://www.harnett.org/gis/default.asp
- **County ArcGIS REST** — https://gis.harnett.org/arcgis/rest/services
- **Web apps / map gallery** — https://www.harnett.org/gis/gis-viewer-and-other-webapps.asp · https://gis.harnett.org/projects/
- **PA / property search (NCPTS)** — https://lrcpwa.ncptscloud.com/harnett/parcel-search
- **PA deep-link** — `https://lrcpwa.ncptscloud.com/harnett/parcel-detail/{AccountNumber}` (alt `{PIN}`)
- **CAMA Basic Search (Tyler ITS)** — https://cama.harnett.org/ITSPublicHT/
- **Development Services** — https://www.harnett.org/devsvc/
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)
- **City/town GIS:** no dedicated public city GIS hosts for Dunn / Lillington / Angier / Erwin / Coats — use county viewer + ZoningDistricts

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `AccountNumber`, `ParcelID`, `PID`; OneMap `parno` | Prefer `PIN` (####-##-####.###); `AccountNumber` for NCPTS deep link |
| polygons | Yes | Tax/Parcels MS/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CalculatedLandArea`, `LegalLandUnits` (when `LegalLandType=AC`) | ~**11,663** CALC 5–150; ~**11,240** Legal AC |
| ownerName | Yes | `Owners` / `Owner1` (+ Owner2); OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `OwnerAddress1` + city/state/zip; `MailingAddress` combined | Structured preferred |
| situs address | Yes | `PhysicalAddress` / `ParAddress` / `ParCity` / `ParZipCode` / street parts | **On primary parcel layer** |
| lastSale date/price | Yes (last) | `SalePrice`, `SaleYear`/`SaleMonth`, `DeedDate`, `QualifiedCode` | SalePrice>0 in ~4.7k of 5–150; Sales MS + QualifiedSales complement |
| tax values | Yes | `TotalMarketValue`, `TotalAssessedValue`, `ParcelLandValue`, `ParcelBuildingValue` | **Has land/improve split** on primary |
| zoning | Yes | Parcel `Zoning`+`ZoningJurisdiction`; ZoningDistricts `ZoneClass`+`Jurisdiction` | Prefer Jurisdiction filter inside towns |
| flu | Yes (partial) | County `FLU`; overlays Jetport/Military | No city FLU FS; Municipal/ETJ placeholder in towns |
| appraiser / viewer link | Yes | NCPTS parcel-detail by AccountNumber; GIS Viewer; CAMA search | Templates below |

### ZoningDistricts JURISDICTION (verified counts)

| Jurisdiction | Zoning polygons | Notes |
|--------------|-----------------|-------|
| Dunn | **5,880** | No city REST — county stack primary |
| Lillington | **2,330** | County stack primary (county seat) |
| Harnett County | **634** | Unincorporated |
| Coats | **338** | County stack primary |
| Erwin | **106** | Prefer over AGOL 2005 town layer (28) |
| Angier | **97** | **Sparse** vs ~5.2k Angier parcels — use parcel Zoning attr |
| Broadway | **2** | Lee County tip |
| Fuquay_Varina | **1** | Wake tip |
| Benson | **1** | Johnston tip |

### Parcel ZoningJurisdiction (municipality inventory)

| ZoningJurisdiction | Approx parcels |
|--------------------|----------------|
| Harnett County | 62,132 |
| Dunn | 6,429 |
| Angier | 5,245 |
| Lillington | 5,190 |
| Erwin | 4,291 |
| Coats | 1,783 |
| Harnett County, Lillington (multi) | 240 |
| Other multi / Broadway / Fuquay tips | <200 each |

### CityTaxDistrict (incorporated tax)

| District | Parcels |
|----------|---------|
| (null / unincorporated) | 67,526 |
| Dunn | 5,310 |
| Lillington | 4,576 |
| Angier | 4,372 |
| Erwin | 2,697 |
| Coats | 1,249 |
| Broadway / Benson tips | ≤5 |

## Layers (verified)

### 1. Tax/Parcels — parcels + ownership + tax + situs + sale + zoning attr (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | situs | zoning (attr)
- **REST URL (wire-first):** https://gis.harnett.org/arcgis/rest/services/Tax/Parcels/MapServer/0
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (joins OneMap `parno`)
  - `AccountNumber` → NCPTS deep-link key
  - `ParcelID` / `PID` → alternate ids
  - `CalculatedLandArea`, `LegalLandUnits`+`LegalLandType` → acreage
  - `Owners`, `Owner1`, `Owner2` → ownerName
  - `OwnerAddress1`…`OwnerZipCode`, `MailingAddress` → mailing
  - `PhysicalAddress`, `ParAddress`/`ParCity`/`ParZipCode`, street parts → situs
  - `SalePrice`, `SaleYear`/`SaleMonth`, `DeedDate`, `DeedBook`/`DeedPage`, `QualifiedCode` → lastSale
  - `TotalMarketValue`, `TotalAssessedValue`, `ParcelLandValue`, `ParcelBuildingValue` → tax
  - `Zoning`, `ZoningJurisdiction` → zoning (attribute; often includes acreage split text)
  - `UseCode`, `Class` → local use / class
  - `Latitude`/`Longitude` → WGS84 centroid hints
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **85,736**; `CalculatedLandArea` 5–150 → **11,663**; Legal AC 5–150 → **11,240**; BLDG=0/null in range → **7,659**; SalePrice>0 in range → **4,710**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. **MapServer only** (FeatureServer SOE not installed). `REID` often `"Retired"` — ignore. Geo-check sample PIN `0518-52-7425.000` centroid ≈ **-78.947, 35.351** (Harnett).

### 2. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Key fields:** `parno`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`/`scity`, `gisacres`, `saledate`, `parval`/`landval`/`improvval`, `cntyfips`=`085`
- **Verified:** yes — filter count **84,508**; gisacres 5–150 → **11,657**; improvval=0/null in range → **5,686**
- **Notes:** Fallback when county host flaky. No sale price. MaxRecordCount **5000**. PIN join verified.

### 3. Planning ZoningDistricts — multi-jurisdiction zoning (PRIMARY zoning stack)

- **Purpose:** zoning
- **REST URL:** https://gis.harnett.org/arcgis/rest/services/Planning/Zoning/MapServer/1
- **Fields:** `ZoneClass`, `ZoneDescription`, `ZoneDefinition`, `Jurisdiction`, `EffectiveDate`, `Ordinance`, `BookPage`, `Conditions`, `Source`
- **WKID / CRS:** 102719 / 2264
- **Join to parcels:** spatial join (intersect/centroid) in 2264; route by `Jurisdiction` or parcel `ZoningJurisdiction` / City Limits `CITY`
- **Verified:** yes — total **9,389** (see jurisdiction table)
- **Notes:** This is the public zoning REST for **all Harnett munis** (no city hosts found). Overlay parcel `Zoning` for QA. **Angier** polygon coverage sparse — lean on parcel attr. `Source` URL field is QA-noisy.

### 4. Planning ETJ

- **REST URL:** https://gis.harnett.org/arcgis/rest/services/Planning/Zoning/MapServer/0
- **Fields:** `Jurisdiction`
- **Verified:** count **8** (Angier, Benson, Broadway, Coats, Dunn, Erwin, Fuquay_Varina, Lillington)

### 5. Erwin Town Zoning Map (AGOL alternate — partial)

- **REST URL:** https://services2.arcgis.com/qO6xd1V1VbSyViir/arcgis/rest/services/Erwin_Town_Zoning_Map/FeatureServer/3
- **Fields:** `ZONING`, `ZONE_DESC`, `ACRES_`
- **Verified:** count **28** (2005 vintage)
- **CRS:** 102716 / 2261 — reproject
- **Notes:** Prefer county ZoningDistricts `Jurisdiction='Erwin'` (**106**).

### 6. Wake Angier Zoning (edge)

- **REST URL:** https://maps.wake.gov/arcgis/rest/services/Planning/Zoning/MapServer/15
- **Verified:** count **96** (Wake card)
- **Notes:** Wake-side Angier only. Harnett-side → county ZoningDistricts + parcel attr.

### 7. Planning Future LandUse — county FLU (PRIMARY)

- **Purpose:** flu
- **REST URL:** https://gis.harnett.org/arcgis/rest/services/Planning/Planning/MapServer/9
- **Fields:** `FLU`
- **Verified:** count **718**
- **Join:** spatial join in 2264
- **Notes:** Top classes Rural/Agriculture, Low Density Residential, Municipal/ETJ, Conservation, Medium Density Residential, Employment. No Dunn/Lillington/Angier/Erwin/Coats city FLU FeatureServers found.

### 8. Future LandUse Overlay + corridor overlays

- **FLU Overlay:** https://gis.harnett.org/arcgis/rest/services/Planning/Planning/MapServer/10 — `OverlayName`, `SafetyZone` (Jetport HRJ AZ-*, Military Overlay Buffer); count **6**
- **Also on Planning MapServer:** Highway Corridor Overlay (2), Military Corridor Overlay (3), Agri Districts (4)

### 9. Sales complements

- **Tax/Sales:** https://gis.harnett.org/arcgis/rest/services/Tax/Sales/MapServer/0 — count **20,199** (sale-subset polygons)
- **QualifiedSales_2024_2025:** …/Tax/QualifiedSales_2024_2025/MapServer/0 — count **9,140**
- Prefer last-sale fields on Tax/Parcels for general use.

### 10. City Limits

- **REST URL:** https://gis.harnett.org/arcgis/rest/services/Boundaries/HC_Boundaries/MapServer/0
- **Fields:** `CITY`, `TAXCODE`
- **Verified:** Angier, Benson, Broadway, Coats, Dunn, Erwin, Fuquay Varina, Lillington
- **Mirror:** Hosted/CITY_LIMITS FeatureServer/0 (CRS 3857)

## Cities / towns first-class routing

| Muni | Prefer for zoning | Prefer for FLU | Parcel host |
|------|-------------------|----------------|-------------|
| Dunn | ZoningDistricts `Jurisdiction='Dunn'` (+ parcel Zoning) | County FLU (Municipal/ETJ inside) | Tax/Parcels |
| Lillington | ZoningDistricts `Lillington` | County FLU | Tax/Parcels |
| Angier (Harnett) | Parcel `Zoning` attr + ZoningDistricts `Angier` (sparse) | County FLU | Tax/Parcels |
| Angier (Wake edge) | Wake Zoning MapServer/15 | Wake / Angier local if any | Wake or Harnett by side |
| Erwin | ZoningDistricts `Erwin` (not AGOL 2005) | County FLU | Tax/Parcels |
| Coats | ZoningDistricts `Coats` | County FLU | Tax/Parcels |
| Broadway tip | Lee County / Broadway card | — | tip only |
| Benson tip | Johnston card | — | tip only |
| Fuquay-Varina tip | Wake / Fuquay-Varina card | Wake FLU | tip only |
| Unincorporated | ZoningDistricts `Harnett County` | County Future LandUse | Tax/Parcels |

No dedicated public ArcGIS hosts found for Dunn, Lillington, Angier, Erwin, or Coats city GIS — **county Planning/Zoning is first-class for those munis**.

## Gaps

- **No city FeatureServers** for Dunn / Lillington / Angier / Coats — county ZoningDistricts only.
- **Angier ZoningDistricts sparse (97)** — rely on parcel `Zoning` attribute.
- **Erwin AGOL town zoning = 2005 / 28 polys** — prefer county stack.
- **No municipal FLU REST** — county FLU uses `Municipal / ETJ` placeholder inside towns.
- **Trakit parcels layer** advertises deep-link + FutureLandUse fields but **queries fail (400)** — do not wire.
- **Tax/Parcels MapServer-only** — no FeatureServer.
- **`REID` retired** — do not join on REID.
- **No multi-transfer sales history REST** — last sale on parcel + Sales / QualifiedSales subsets.
- **Zoning `Source` URL field noisy** — route by `Jurisdiction`.
- **Broadway / Benson / Fuquay tips** — edge fragments; prefer home-county cards.
- **Owner phones/emails** not collected (do not scrape NCPTS/CAMA PII beyond public REST fields).
- **MaxRecordCount 2000** on county layers — paginate.
- **No paid vendor data** used; **no AADT / utilities dig** in this card.

## Hand-off notes for Land Search Builder

1. **Wire first:** `Tax/Parcels/MapServer/0` — polygons + owner, mailing, **situs**, acreage, land/bldg tax, last sale, Zoning + ZoningJurisdiction. Filter `CalculatedLandArea BETWEEN 5 AND 150` (~11.7k). Optional vacant-ish: `ParcelBuildingValue = 0 OR IS NULL` (~7.7k in range).
2. **Zoning:** parcel `Zoning` for fast attr; authoritative spatial join **ZoningDistricts** by `Jurisdiction`. Inside Dunn/Lillington/Erwin/Coats → same layer filtered. Angier → prefer parcel attr. Wake-side Angier → Wake MapServer/15.
3. **FLU:** spatial join county Future LandUse (`FLU`); note Municipal/ETJ inside towns. Optional Jetport/Military overlays.
4. **Sales:** use `SalePrice`/`SaleYear`/`DeedDate` on parcel; QualifiedSales_2024_2025 for recent qualified window.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='085'` (PIN↔parno).
6. **Viewer / appraiser links:**
   - NCPTS detail: `https://lrcpwa.ncptscloud.com/harnett/parcel-detail/{AccountNumber}`
   - Search: `https://lrcpwa.ncptscloud.com/harnett/parcel-search`
   - CAMA Basic Search: `https://cama.harnett.org/ITSPublicHT/`
   - GIS Viewer: `https://gis.harnett.org/gisviewer/`
7. **Join keys:** `PIN` (preferred), `AccountNumber`, `ParcelID`, OneMap `parno`↔`PIN`.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities/towns are first-class:** treat ZoningDistricts Jurisdiction filters as the muni zoning sources (no separate city hosts).

verifiedAt: **2026-09-24** · verifiedBy: **North Carolina Public Info Researcher**


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://gis.harnett.org/arcgis/rest/services/Tax/Parcels/MapServer/0 · id `AccountNumber` · live count **85,776** · 5–150 ac **11,661** (`CalculatedLandArea >= 5 AND CalculatedLandArea <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='HARNETT'` gives **510** stations (174 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27HARNETT%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Harnett'` gives **510** stations (328 with AADT_2025, 294 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Harnett%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Harnett'` gives **510** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `TotalMarketValue` non-zero **80,682**, `TotalAssessedValue` non-zero **80,682**
- **Sale history (ok):** price `SalePrice` >0 **52,332**; date `DeedDate` non-null **82,408**
- **Owner entity:** fields `Owner1`, `Owner2`, `Owners`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **2,130** of 11,661 (extended regex: 2,905).
- **PA deep link:** `https://cama.harnett.org/ITSPublicHT/RealEstateSearch/Parcel/{AccountNumber}`. Tested `1500007930` → HTTP **200** (text/html), content verified: True. ITSPublic RealEstateSearch/Parcel 200 with ID in page. NCPTS parcel-detail/{AccountNumber} 200 SPA shell only (headless shows app 404) — keep as alt, unverified.
- **Jurisdiction GIS viewer:** https://gis.harnett.org/gisviewer/ → HTTP **200** (Harnett County GIS Viewer)
- **Pass 2 gaps:** none
