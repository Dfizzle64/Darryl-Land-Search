# Duplin County, NC — GIS County Card

## Summary

Duplin County (Wilmington MSA footprint, FIPS **37061**, slug **duplin**, `cntyfips='061'`) publishes public ArcGIS REST at `gis.duplinnc.gov`. **Wire-first parcels:** **TaxMapping/Parcels** FeatureServer/0 — ~**43,733** polygons with owner, mailing, situs (`FormattedPropertyAddress`), calc/total acres, last sale price/date/deed refs, and full tax value split (land/bldg/obxf/deferred/market/assessed). ~**12,300** with `CALCULATED_ACRES` 5–150 (~**9,707** building 0/null; ~**5,297** `SalePrice`≠0). **Cities-first zoning** on county host `GISDB/PublicAccessMainGISDB`: **Kenansville** (789), **Warsaw** (240), **Beulaville** (115), **Calypso** (97), **Faison** (36, attrs thin). **Unincorporated Duplin is officially unzoned** (county Planning). **FLU:** Land Use Plan **PDF only** — no FLU FeatureServer. **Wallace / Rose Hill / Magnolia / Greenevers / Teachey** lack public zoning REST. **PA:** BI-Tek ITSPublicDL `{PIN}` / AppraisalCard `{ParcelNumber}` + NCPTS `{PIN}`. Markets: **[Wilmington]**.

## Portals

- **Public GIS viewer** — https://gis.duplinnc.gov/maps/default.htm
- **GIS landing / disclaimer** — https://gis.duplinnc.gov/
- **GIS beta (Avineon)** — https://gis.duplinnc.gov/avineonbeta
- **County ArcGIS REST** — https://gis.duplinnc.gov/server/rest/services
- **Tax GIS / department** — https://www.duplinnc.gov/277/GIS
- **Tax Administration** — https://www.duplinnc.gov/215/Tax-Administration
- **Planning (UDO / unzoned policy)** — https://www.duplinnc.gov/206/Planning
- **UDO PDF** — https://www.duplinnc.gov/DocumentCenter/View/688/Duplin-County-Unified-Development-Ordinance-PDF
- **Land Use Plan PDF** — https://www.duplinnc.gov/DocumentCenter/View/292/Duplin-County-Land-Use-Plan-PDF
- **PA / Real Estate Search (ITSPublicDL)** — https://www.bttaxpayerportal.com/ITSPublicDL/RealEstateSearch
- **PA deep-link (PIN)** — `https://www.bttaxpayerportal.com/ITSPublicDL/RealEstateSearch/Parcel/{PIN}`
- **Appraisal card PDF** — `https://www.bttaxpayerportal.com/ITSPublicDL/AppraisalCard.aspx?id={ParcelNumber}`
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/duplin/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/duplin/parcel-detail/{PIN}`
- **Tax pay (ITSPublicDL)** — https://www.bttaxpayerportal.com/ITSPublicDL
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)
- **Town planning (Wallace)** — https://www.wallacenc.gov/planning — map https://www.wallacenc.gov/map (no public zoning FS)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` / `PinNumber`; `ParcelNumber`; `AccountNumber`; OneMap `parno` | Prefer **PIN** (12-digit); PA AppraisalCard uses `ParcelNumber` |
| polygons | Yes | TaxMapping/Parcels FS/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALCULATED_ACRES`, `TOTAL_ACRES`, `LegalLandUnits` | ~**12,300** CALC 5–150 |
| ownerName | Yes | `Name1` / `Name2`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `Address1`–`3`, `City`, `State`, `ZipCode` | |
| situs address | Yes (partial) | `FormattedPropertyAddress`; 911 `FullAddress`; OneMap `siteadd` | Often thin on acreage — join 911 |
| lastSale date/price | Yes (last) | `SalePrice`, `DeedDate`, `DeedBook`/`DeedPage` | Strings; SalePrice≠0 in 5–150 → **5,297** |
| tax values | Yes | `TotalMarketValue`, `TotalAssessedValue`, `ParcelLandValue`, `ParcelBuildingValue`, `ParcelObxfValue`, `ParcelDeferredValue` | On PRIMARY FS |
| zoning | Yes (cities-first) | Kenansville `Zoning`; Warsaw `ZONING`; Beulaville/Calypso `Zone` | Unincorp **unzoned**; Wallace+ towns gap |
| flu | Gap | Land Use Plan PDF | No FLU FeatureServer |
| appraiser / viewer link | Yes | ITSPublicDL `{PIN}` / AppraisalCard `{ParcelNumber}`; NCPTS; GIS viewer | Templates below |

### Zoning inventory (verified)

| Layer | Count | Field | Scope |
|-------|-------|-------|-------|
| Kenansville Zoning Districts (Main/50) | **789** | `Zoning` | City-first PRIMARY |
| Warsaw Zoning Districts (Main/51) | **240** | `ZONING` | City-first PRIMARY |
| Beulaville Zoning (Main/47) | **115** | `Zone` | City-first |
| Calypso Zoning Districts (Main/48) | **97** | `Zone` | City-first |
| Faison Zoning (Main/49) | **36** | (none) | Geometry only — partial |
| County unincorporated | n/a | — | **Officially unzoned** |

### Kenansville Zoning (top)

| Zoning | Count |
|--------|-------|
| R15 | 260 |
| R10 | 176 |
| GC | 135 |
| (blank) | 104 |
| OI | 75 |
| CB | 16 |
| I | 11 |
| AG | 8 |

### Warsaw ZONING (top)

| ZONING | Count |
|--------|-------|
| R-8 | 60 |
| HB | 41 |
| R-10 | 40 |
| R-6 | 33 |
| R-20 | 28 |
| CB | 16 |
| I | 13 |
| L1 | 6 |

### Municipal / ETJ inventory

**TownLimits / City Limits:** Beulaville, Calypso, Faison, Greenevers, Harrells (edge), Kenansville, Magnolia, Mount Olive (edge/Wayne), Rose Hill, Teachey, Wallace, Warsaw. **ETJ (Aux/21):** Mt Olive, Calypso, Kenansville, Magnolia, Rose Hill, Warsaw, Faison, Beulaville, Wallace.

## Layers (verified)

### 1. TaxMapping/Parcels — parcels + ownership + tax + situs + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | situs
- **REST URL (wire-first):** https://gis.duplinnc.gov/server/rest/services/TaxMapping/Parcels/FeatureServer/0
- **Also:** MapServer twin; viewer mirror `PublicAccess/ParcelAccessMainFGDB/MapServer/37`
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` / `PinNumber` → parcelId
  - `ParcelNumber`, `AccountNumber`, `CYPAR_NEW` → alt / PA keys
  - `CALCULATED_ACRES`, `TOTAL_ACRES`, `LegalLandUnits` → acreage
  - `Name1`, `Name2` → ownerName
  - `Address1`–`3`, `City`, `State`, `ZipCode` → mailing
  - `FormattedPropertyAddress` → situs
  - `SalePrice`, `DeedDate`, `DeedBook`, `DeedPage` → lastSale
  - `TotalMarketValue`, `TotalAssessedValue`, `ParcelLandValue`, `ParcelBuildingValue`, `ParcelObxfValue`, `ParcelDeferredValue` → tax
  - `ActualYearBuilt`, `HeatedAreaCard`, `Neighborhood`/`NeighborhoodName` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **43,733**; CALC 5–150 → **12,300**; TOTAL 5–150 → **13,204**; bldg 0/null in band → **9,707**; SalePrice≠0 in band → **5,297**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. Value/sale fields are **strings**. Geo-check PIN `248600627091` ≈ **-78.042, 35.011**; `246600208100` ≈ **-78.125, 35.011** (Warsaw). Auth: none.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='061'`
- **Key fields:** `parno`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`/`scity`, `gisacres`, `saledate`, `parval`/`landval`/`improvval`
- **Verified:** yes — count **43,612**; gisacres 5–150 → **12,297**; PIN↔parno (`247500941899`)
- **Notes:** No sale price. `scity`/`mcity` often blank. MaxRecordCount **5000**.

### 3. Kenansville Zoning Districts — city-first (PRIMARY for Kenansville)

- **REST:** https://gis.duplinnc.gov/server/rest/services/GISDB/PublicAccessMainGISDB/MapServer/50
- **Field:** `Zoning` (+ parcel-style attrs `PARNO`, `OWNNAME`, `SITEADD`)
- **Count:** **789** | CRS 2264
- **Join:** spatial / `PARNO`↔`PIN`; gate with TownLimits / City Limits / ETJ Kenansville
- **Notes:** Mirror `ParcelAccessMainFGDB/MapServer/51`

### 4. Warsaw Zoning Districts — city-first

- **REST:** …/PublicAccessMainGISDB/MapServer/51 — `ZONING`; count **240**
- **Join:** spatial / `PIN`; gate Warsaw limits/ETJ
- **Notes:** Mirror ParcelAccessMainFGDB/52

### 5. Beulaville Zoning — city-first

- **REST:** …/MapServer/47 — `Zone`; count **115**

### 6. Calypso Zoning Districts — city-first

- **REST:** …/MapServer/48 — `Zone`; count **97** (legacy numeric codes)

### 7. Faison Zoning — partial

- **REST:** …/MapServer/49 — count **36**; **no Zone field** (Id only) — status **partial**

### 8. TownLimits / City Limits — municipality filter

- **TownLimits FS:** https://gis.duplinnc.gov/server/rest/services/TaxMapping/TownLimits/FeatureServer/0 — count **21**
- **City Limits (Aux):** https://gis.duplinnc.gov/server/rest/services/PublicAccessAux/MapServer/23 — count **21**
- **Field:** `MUNICIPALITY_NAME`, `TOWN_TYPE`
- **Notes:** Many parts have null name — map `TOWN_TYPE`: 0 Beulaville, 1 Calypso, 2 Faison, 3 Greenevers, 4 Harrells, 5 Kenansville, 6 Magnolia, 8 Rose Hill, 9 Teachey, 10 Wallace, 11 Warsaw, 12 Mount Olive

### 9. ETJ (Shaded)

- **REST:** https://gis.duplinnc.gov/server/rest/services/PublicAccessAux/MapServer/21
- **Field:** `SOURCETHM` | count **9**
- **Notes:** Route ETJ parcels to matching town zoning when layer exists

### 10. 911 Address Points — situs join

- **REST:** https://gis.duplinnc.gov/server/rest/services/TaxMapping/911AddressPoints/FeatureServer/0
- **Count:** **34,036** | `FullAddress`, `Post_Comm`, `Post_Code`

### 11. FLU — gap (PDF only)

- **Land Use Plan PDF:** https://www.duplinnc.gov/DocumentCenter/View/292/Duplin-County-Land-Use-Plan-PDF
- **No** public Future Land Use FeatureServer verified on county REST / AGOL search for official county FLU

## Municipalities (first-class)

County parcels are countywide. **Zoning inside towns is municipal** where a layer exists. Join pattern: TaxMapping parcels (2264) → TownLimits / Aux City Limits / ETJ → spatial join matching town zoning; else leave zoning **null** for unincorporated (do not invent county districts — county is unzoned). Prefer **most local** zoning.

### Town of Kenansville (county seat)

- **Zoning:** MainGISDB/50 — `Zoning`; **789**
- **FLU:** no town REST (gap)
- **Join:** town zoning + county parcels (spatial / PARNO)

### Town of Wallace (largest; Duplin + Pender edge)

- **Zoning REST:** **none** on county host (gap). Town planning maintains Zoning Map/Ordinance — https://www.wallacenc.gov/planning
- **Boundary:** TownLimits / Aux + Wallace ETJ
- **Join note:** cannot wire municipal zoning; leave null or cite ordinance offline. Prefer Duplin parcels for 37061 Wallace; Pender card for Pender-side edge

### Town of Warsaw

- **Zoning:** MainGISDB/51 — `ZONING`; **240**
- **FLU:** gap

### Town of Beulaville

- **Zoning:** MainGISDB/47 — `Zone`; **115**

### Town of Calypso

- **Zoning:** MainGISDB/48 — `Zone`; **97**

### Town of Faison

- **Zoning:** MainGISDB/49 — **36** polys, **no code field** (partial)

### Rose Hill / Magnolia / Greenevers / Teachey

- **Zoning REST:** none (gap)
- **Boundary:** TownLimits + ETJ (where listed)

### Harrells / Mount Olive (edge)

- Prefer **Sampson** (Harrells) / **Wayne** (Mount Olive) cards for primary town GIS; Duplin holds edge polygons + Mt Olive ETJ only

## Gaps

- **Unincorporated: no zoning districts** — official county policy; UDO ≠ zoning map.
- **No FLU FeatureServer** — Land Use Plan PDF only.
- **Wallace, Rose Hill, Magnolia, Greenevers, Teachey** — no public zoning FeatureServer.
- **Faison** zoning geometry without Zone codes.
- **Sale history** last-sale only; SalePrice stored as string.
- **Situs** often weak on vacant/large tracts — join 911 / OneMap.
- **TownLimits names** incomplete — use `TOWN_TYPE` / Aux City Limits.

## PA / deep-link templates

| Purpose | Template |
|---------|----------|
| Real Estate Search (PIN) | `https://www.bttaxpayerportal.com/ITSPublicDL/RealEstateSearch/Parcel/{PIN}` |
| Appraisal card PDF | `https://www.bttaxpayerportal.com/ITSPublicDL/AppraisalCard.aspx?id={ParcelNumber}` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/duplin/parcel-detail/{PIN}` |
| GIS viewer | https://gis.duplinnc.gov/maps/default.htm |

Viewer SearchConfig wires AppraisalCard to `ParcelNumber` on the Parcels layer.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **tranche:** 3 (tax/sale/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning suite; FLU gap documented)
- **Excluded:** AADT, utilities, emails/phones, paid vendors


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://gis.duplinnc.gov/server/rest/services/TaxMapping/Parcels/FeatureServer/0 · id `PIN` · live count **43,735** · 5–150 ac **12,301** (`CALCULATED_ACRES >= 5 AND CALCULATED_ACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='DUPLIN'` gives **584** stations (345 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27DUPLIN%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Duplin'` gives **564** stations (334 with AADT_2025, 348 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Duplin%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Duplin'` gives **564** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `TotalMarketValue` non-zero **43,203**, `TotalAssessedValue` non-zero **43,201**
- **Sale history (ok):** price `SalePrice` >0 **21,482**; date `DeedDate` non-null **37,874**
- **Owner entity:** fields `Name1`, `Name2`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **1,859** of 12,301 (extended regex: 2,427).
- **PA deep link:** `https://www.bttaxpayerportal.com/ITSPublicDL/RealEstateSearch/Parcel/{PIN}`. Tested `348200398658` → HTTP **200** (text/html), content verified: True. Parcel id found in the response body.
- **Jurisdiction GIS viewer:** https://gis.duplinnc.gov/maps/default.htm → HTTP **200**
- **Pass 2 gaps:** none
