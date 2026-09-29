# Camden County, NC — GIS County Card

## Summary

Camden County (Outer Banks / Eastern NC, FIPS **37029**, slug **camden**, `cntyfips='029'`) publishes public AGOL FeatureServers under org **`f8vjF7CsMeTPBIVC`** (`ccnc.maps.arcgis.com`). **Wire-first parcels (ArcGIS REST):** **Parcels** FeatureServer/1 — **~7,959** polygons with owner (`Name1`/`Name2`), mailing (`Address`/`CityStZip`), situs (`E911_Numbe`/`F911Street`), GIS/deed acres (`ACRES_GIS`/`ACRES_DEED`/`Acres`), **on-layer sale date + qualification** (`SaleDate`/`SaleQualified` Q/C/U/V), zoning attr (`Zoning`/`Zone`), and keys **`PIN`** + dotted **`ParcelID`**. **~1,997** with `ACRES_GIS` 5–150 (~**1,423** vacant-ish in band; **~164** SaleQualified=Q in band). **No sale price / no tax value fields** on public REST (OneMap `parval` also scrubbed to 0) — use **NCPTS** interactively for values/price. **Cities-first:** **no incorporated municipalities** — prefer **South Mills Small Area Plan** FLU PDF for South Mills township; else County Future Land Use Map + 2035 Comp Plan + DEQ CAMA LUP PDFs; zoning always countywide **Zoning FS/1** (224) + parcel attr. **PA:** NCPTS `parcel-detail/{PIN}` + Instant Sidebar `find={PIN}`. **jurisdictionGisUrl:** Experience Builder Property Information Map. Markets: **[Outer Banks, Eastern NC]**.

## Portals

- **Public GIS viewer (jurisdictionGisUrl)** — https://experience.arcgis.com/experience/60ecb9b737384e7dbd1ad3f1f20b27b2/
- **Instant Sidebar (alt Property Map)** — https://ccnc.maps.arcgis.com/apps/instant/sidebar/index.html?appid=0b5925a5657e45c5937aada475ca76a7
- **Tax Information Map (Experience)** — https://experience.arcgis.com/experience/bd5bdcafa3164d2faf02b74558510a12/
- **Tax Instant Sidebar** — https://ccnc.maps.arcgis.com/apps/instant/sidebar/index.html?appid=fd3d2f293e55460b903b39f54794468c
- **GIS Maps landing** — https://www.camdencountync.gov/260/GIS-Maps
- **County AGOL org** — https://ccnc.maps.arcgis.com/
- **County REST root** — https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services
- **Parcels (PRIMARY)** — https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services/Parcels/FeatureServer/1
- **Parcels_View twin** — https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services/Parcels_View/FeatureServer/1
- **Tax_Property_Information_view** — https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services/Tax_Property_Information_view/FeatureServer/0
- **Zoning** — https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services/Zoning/FeatureServer/1
- **Townships** — https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services/Townships/FeatureServer/1
- **NCPTS Camden hub** — https://lrcpwa.ncptscloud.com/camden/
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/camden/parcel-search
- **NCPTS deep-link (parcel)** — `https://lrcpwa.ncptscloud.com/camden/parcel-detail/{PIN}`
- **Viewer deep-link (Instant find)** — `https://ccnc.maps.arcgis.com/apps/instant/sidebar/index.html?appid=0b5925a5657e45c5937aada475ca76a7&find={PIN}`
- **Taxes** — https://www.camdencountync.gov/279/Taxes
- **Pay Taxes / Municipy** — https://www.camdencountync.gov/431/Pay-Taxes — https://payments.municipay.com/nc_camden/search
- **Register of Deeds** — https://us5.courthousecomputersystems.com/CamdenNC/
- **Planning & Building** — https://www.camdencountync.gov/229/Planning-Building
- **Land Use & Zoning** — https://www.camdencountync.gov/261/Land-Use-Zoning
- **UDO §151 page** — https://www.camdencountync.gov/271/Unified-Development-Ordinance-151
- **UDO Ch.151 PDF** — https://www.camdencountync.gov/DocumentCenter/View/454/Unified-Development-Ordinance-Chapter-151-PDF
- **Official Plans & Documents** — https://www.camdencountync.gov/268/Official-Plans-Documents
- **2035 Comprehensive Plan page** — https://www.camdencountync.gov/289/Comprehensive-Plan
- **2035 Comp Plan PDF** — https://www.camdencountync.gov/DocumentCenter/View/480/Comprehensive-Plan-Final-Document-October-1-2012-PDF
- **Future Land Use Map PDF** — https://www.camdencountync.gov/DocumentCenter/View/443/Camden-County-Future-Land-Use-Map-PDF
- **South Mills Small Area Plan PDF** — https://www.camdencountync.gov/DocumentCenter/View/449/South-Mills-Small-Area-Plan-PDF
- **US Hwy 17 Corridor Plan PDF** — https://www.camdencountync.gov/DocumentCenter/View/447/Camden-County-US-Hwy-17-Corridor-Plan-PDF
- **DEQ certified LUPs (Camden)** — https://www.deq.nc.gov/about/divisions/coastal-management/coastal-management-land-use-planning/certified-lups/camden-county
- **DEQ CAMA plan PDF** — https://www.deq.nc.gov/documents/pdf/land-use-plans/camdenplan/download
- **DEQ CAMA maps PDF** — https://www.deq.nc.gov/documents/pdf/land-use-plans/camdenmaps/download
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 — filter `cntyfips='029'`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` (PA/viewer); `ParcelID` dotted; OneMap `parno`≈PIN | Prefer **`PIN`** for NCPTS + Instant `find=` |
| polygons | Yes | Parcels/1; Parcels_View/1; OneMap | CRS **102719 / 2264**; MaxRecordCount **2000** |
| acreage | Yes | `ACRES_GIS`, `Acres`, `ACRES_DEED`; OneMap `gisacres`/`recareano` | **1,997** GIS 5–150 |
| ownerName | Yes | `Name1`/`Name2`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `Address`, `CityStZip` | Combined city/state/zip string |
| situs address | Yes | `E911_Numbe`, `F911Street`, `F911HouseNumber` | |
| lastSale date/price | Partial | `SaleDate`, `SaleQualified`; OneMap `saledate` | **Date + qual on layer; price REST gap** |
| tax values | Gap (REST) | — | Scrubbed on county + OneMap; use NCPTS interactive |
| zoning | Yes (countywide) | Zoning FS `ZONING`/`ZONE`; parcel `Zoning`/`Zone` | No city FS — county UDO everywhere |
| flu | Partial (PDF) | South Mills SAP + County FLU Map + Comp Plan + DEQ CAMA | **No FLU FeatureServer** |
| appraiser / viewer link | Yes | NCPTS `{PIN}`; Instant `find={PIN}`; Experience | TRANCHE-3 |

### Township parcel counts (Parcels/1 `TOWNSHIP`)

| TOWNSHIP | Count | Cities-first routing |
|---------:|------:|----------------------|
| South Mills | ~2,766 | **South Mills SAP** FLU PDF (cities-first) |
| Courthouse | ~2,686 | Camden seat / Courthouse — county FLU PDFs |
| Shiloh | ~2,477 | County FLU PDFs |
| CAMDEN | ~4 | Alias / odd labels |
| (blank) | ~26 | — |

## Layers (verified 2026-09-24)

### 1. Parcels/1 — PRIMARY CAMA (ArcGIS REST)

- **Purpose:** parcels | ownership | situs | sale date/qual | zoning attr
- **REST URL:** https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services/Parcels/FeatureServer/1
- **Twins:** Parcels_View/1; Tax_Property_Information_view/0 (same CAMA family; tax view drops some acre/sale-qual fields)
- **Geometry:** Polygon — CRS **102719 / 2264** (NAD 1983 StatePlane North Carolina Feet)
- **Key fields → targets:**
  - `PIN`, `ParcelID`, `MatchTablePIN` → parcelId
  - `ACRES_GIS`, `Acres`, `ACRES_DEED` → acreage
  - `Name1`, `Name2` → ownerName
  - `Address`, `CityStZip` → mailing
  - `E911_Numbe`, `F911Street`, `F911HouseNumber` → situsAddress
  - `SaleDate`, `SaleQualified`, `DeedBkPg`/`DeedBook`/`DeedPage` → lastSale (date/qual/deed; **no price**)
  - `Zoning`, `Zone` → zoning (attr backup)
  - `ExistingLa`, `TOWNSHIP` → existing use / community router
- **Verified:** count **7,959**; ACRES_GIS 5–150 → **1,997**; Name1 → **7,917**; SaleDate real → **2,642**; SaleQualified Q→**1,231** / C→**521** / U→**857** / V→**21**; Q+band → **164**; vacant-ish band → **1,423**; Zoning attr → **7,919**
- **Geo-check:** South Mills `PIN=017081006185220000` ≈ **-76.323, 36.501**; Courthouse `028938001023020000` ≈ **-76.174, 36.412**; Shiloh `038973000882760000` ≈ **-76.047, 36.293**
- **Notes:** PRIMARY wire-first. MaxRecordCount **2000**. Auth: **none**. Sale **date/qual on layer**; **sale price + tax values REST gap**. Prefer `PIN` for PA.

### 2. NC OneMap Parcels — statewide ArcGIS REST fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='029'`
- **Key fields:** `parno`(=PIN), `ownname`, mail/site, `gisacres`/`recareano`, `parval`/`landval`/`improvval` (all 0), `saledate` (epoch)
- **Verified:** count **7,955**; gisacres 5–150 → **1,999**; recareano 5–150 → **1,983**; ownname → **7,899**; parval>0 → **0**; saledate present; saledatetx empty
- **Join check:** parno `038973000882760000` ↔ county PIN
- **Notes:** Prefer county Parcels for SaleQualified + Zoning + ParcelID. Tax fields scrubbed.

### 3. Zoning/1 — countywide zoning

- **REST URL:** https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services/Zoning/FeatureServer/1
- **Fields:** `ZONE` (name), `ZONING` (code), `Acreage`, `Date_Chang`, `Approved`
- **Verified:** count **224**
- **Codes:** NR (102), WL (21), RR (17), SR (17), VR (17), HC (17), LI (10), MC (7), VC (5), PD (5), CC (3), HI (1), CP (1)
- **Notes:** County UDO applies countywide (no munis). Spatial-join parcels → `ZONING`. Parcel attr `Zoning`/`Zone` is backup (naming swapped vs FS).

### 4. Townships/1 — community router

- **REST URL:** https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services/Townships/FeatureServer/1
- **Verified:** count **3** — South Mills (01), Courthouse (02), Shiloh (03)
- **Notes:** Route cities-first FLU with parcel `TOWNSHIP` / spatial join.

### 5. FLU — PDF only (no FeatureServer)

- **South Mills SAP (cities-first):** https://www.camdencountync.gov/DocumentCenter/View/449/South-Mills-Small-Area-Plan-PDF
- **County Future Land Use Map:** https://www.camdencountync.gov/DocumentCenter/View/443/Camden-County-Future-Land-Use-Map-PDF
- **2035 Comp Plan:** https://www.camdencountync.gov/DocumentCenter/View/480/Comprehensive-Plan-Final-Document-October-1-2012-PDF
- **DEQ CAMA plan + maps:** https://www.deq.nc.gov/documents/pdf/land-use-plans/camdenplan/download ; …/camdenmaps/download
- **Status:** usable as PDF FLU guidance — **gap** for polygon FLU REST

## Municipalities / communities (first-class)

**No incorporated cities or towns.** Zoning authority is **countywide** under UDO §151. **Cities-first** here means prefer **South Mills Small Area Plan** FLU PDF inside South Mills township before county FLU/Comp Plan/DEQ PDFs; always keep county Zoning FS for district codes.

### South Mills (PRIMARY community)

- **FLU:** South Mills Small Area Plan PDF
- **Parcels:** TOWNSHIP='South Mills' — **~2,766**
- **Zoning:** county Zoning FS/1 (no town FS)

### Camden / Courthouse (county seat community)

- **FLU:** County FLU Map + 2035 Comp Plan + DEQ CAMA
- **Parcels:** TOWNSHIP='Courthouse' — **~2,686**
- **Zoning:** county Zoning FS/1

### Shiloh

- **FLU:** County FLU Map + DEQ CAMA
- **Parcels:** TOWNSHIP='Shiloh' — **~2,477**
- **Zoning:** county Zoning FS/1

### Elizabeth City (spill only)

- Primarily **Pasquotank** (see `37139-pasquotank`). Do not assume EC CityZoning polys apply to Camden PINs — prefer Camden county Zoning for Camden parcels.

## PA / viewer deep-links (TRANCHE-3)

| Template | Key | Status |
|----------|-----|--------|
| `https://lrcpwa.ncptscloud.com/camden/parcel-detail/{PIN}` | PIN | **Verified** SPA shell (200) |
| `https://ccnc.maps.arcgis.com/apps/instant/sidebar/index.html?appid=0b5925a5657e45c5937aada475ca76a7&find={PIN}` | PIN | **Verified** Instant find (PIN in searchFields) |
| `https://experience.arcgis.com/experience/60ecb9b737384e7dbd1ad3f1f20b27b2/` | — | Jurisdiction GIS viewer (Property Information Map) |
| https://lrcpwa.ncptscloud.com/camden/parcel-search | — | NCPTS search |
| https://payments.municipay.com/nc_camden/search | — | Tax bill pay search (not CAMA card) |

**Prefer `PIN`** (18-digit, e.g. `038973000882760000`) over dotted `ParcelID` for deep-links.

## Gaps

- **No sale price** on public Parcels / Tax view / OneMap REST — SaleDate + SaleQualified only
- **Tax market/assessed values scrubbed** from public REST (OneMap parval=0 countywide)
- **No FLU FeatureServer** — South Mills SAP + County FLU Map + Comp Plan + DEQ CAMA PDFs only
- **No incorporated municipalities** — no city zoning FeatureServers by definition
- **Reject** Camden NJ `Camden_Parcels` on org `tw1Lbqbml2quI9YZ` (wrong geography)
- **Reject** Spatialest / AGD PRC-print paths (404); utilities FS (Sewer/Water/Hydrants) excluded by scope
- Do **not** collect emails, phones, AADT, utilities, or paid-vendor data

## License / attribution

Camden County GIS / Tax; NC OneMap Integrated Cadastral. Public ArcGIS REST — attribution required. GIS maps are illustrative and not surveys.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- Live `returnCountOnly` + sample attribute/geometry queries against Parcels/1, Zoning/1, Townships/1, Tax_Property_Information_view/0, NC OneMap `cntyfips='029'`; Experience + Instant item/data configs; NCPTS + Instant `find=` deep-link HTTP 200; geo-check South Mills + Courthouse + Shiloh centroids; PDF HTTP 200 for FLU/UDO/Comp Plan/DEQ


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services/Parcels/FeatureServer/1 polygons load (sample centroid [-76.0227, 36.3126]); `PIN` filled on 7,959 of 7,959; `ACRES_GIS` 5–150 ac **1,997**.
- **Attribute layer for Pass 2:** https://services7.arcgis.com/f8vjF7CsMeTPBIVC/arcgis/rest/services/Parcels/FeatureServer/1 · id `PIN` · live count **7,959** · 5–150 ac **1,997** (`ACRES_GIS >= 5 AND ACRES_GIS <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='CAMDEN'` gives **102** stations (31 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CAMDEN%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Camden'` gives **99** stations (69 with AADT_2025, 58 with AADT_2024, 99 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Camden%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (gap):** none on the parcel layer. Fallback: Parcels/1 and Tax_Property_Information_view carry no value fields; NC OneMap parval>0 for cntyfips='029' = 0 of 7,955 (live 2026-09-28). Values only on NCPTS Camden parcel-detail (script-rendered).
- **Sale history (partial):** price not on REST; date `SaleDate` non-null **7,584**. SaleDate (string) on layer; no price on REST. Price only on NCPTS https://lrcpwa.ncptscloud.com/camden/parcel-detail/{PIN} (script-rendered SPA).
- **Owner entity:** field `Name1`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **360** (all parcels: 1,070), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://lrcpwa.ncptscloud.com/camden/parcel-detail/{PIN}`. Tested `038964009270040000` (https://lrcpwa.ncptscloud.com/camden/parcel-detail/038964009270040000) → HTTP **200** (text/html), content verified: False. NCPTS SPA shell (200, 496 B, client-rendered): parcel content cannot be checked server-side.
- **Jurisdiction GIS viewer:** https://experience.arcgis.com/experience/60ecb9b737384e7dbd1ad3f1f20b27b2/ → HTTP **200** (Experience); ArcGIS item access=public
- **Pass 2 gaps:** tax gap, sale partial, PA content not verifiable (SPA)
