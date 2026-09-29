# Granville County, NC — GIS County Card

## Summary

Granville County (Raleigh–Durham market, FIPS **37077**, slug **granville**) publishes public ArcGIS Online services under org `services8.arcgis.com/dT3Tew5pivPd2bWH` (owner `sandy.woody`): countywide **parcel polygons** with ownership, mailing, **situs on the polygon**, GIS acreage, land/improvement/market/assessed values, and **SalePrice** on `Granville_Service/Parcels_Polygon` (layer **8**). **Zoning is city-first** on `Granville_Static` for **Oxford / Butner / Creedmoor / Stovall**, plus county **GC_ZONING** for unincorporated districts (with municipal planning-area stubs). **Stem** has **no dedicated zoning FeatureServer** (stub only). Countywide **FLU** on `Granville_FLU/11`. **NC OneMap** (`cntyfips='077'`) is a usable fallback without sale price. PA: ITSPublic Real Estate Search with durable GET `…/RealEstateSearch/Parcel/{Parcel}` (12-digit `Parcel`).

## Portals

- **County GIS Experience map** — https://experience.arcgis.com/experience/9fb947310691479b8a2468d86316e8de
- **County GIS department page** — https://www.granvillecounty.org/259/GIS-Geographic-Information-System
- **GIS Hub** — https://granville-county-granvillecounty.hub.arcgis.com/
- **County AGOL REST** — https://services8.arcgis.com/dT3Tew5pivPd2bWH/arcgis/rest/services
- **Planning and Zoning web app** — https://granvillecounty.maps.arcgis.com/apps/webappviewer/index.html?id=badbfc05611d4bea954520ffb5401ff2
- **Real Estate Search (ITSPublic / PA)** — https://tax.granvillecounty.org/ITSPublic/RealEstateSearch — deep link `/Parcel/{Parcel}`
- **Tax Bill Search** — https://tax.granvillecounty.org/ITSPublic/TaxBillSearch — deep link `/Parcel/{Parcel}`
- **Tax Administration** — https://www.granvillecounty.org/238/Tax-Administration
- **Tax Database Downloads (CSV)** — https://www.granvillecounty.org/898/Tax-Database-Downloads
- **Planning / Zoning (admin)** — https://www.granvillecounty.org/335/Planning-Zoning
- **City parcel viewers** — Oxford / Butner / Creedmoor / Stem / Stovall Experience apps (see JSON portals)
- **NC OneMap** — https://www.nconemap.gov — `services.nconemap.gov` / `services.gis.nc.gov`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `Parcel` (12-digit), `PIN` (hyphenated), `PRODNO`, `RECN`; OneMap `parno`≈Parcel | Prefer `Parcel` for ITSPublic |
| polygons | Yes | Granville_Service/8 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `Cal_Acres`, `LandUnits`; OneMap `gisacres` | Cal_Acres 5–150 → **7186**; gisacres 5–150 → **7161** |
| ownerName | Yes | `OwnerName1` / `OwnerName2`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `AddressLine1`–`3`, `City`, `State`, `Zip` | |
| situs address | Yes | `FormattedPropertyAddress` on parcels; AddressPoints `SITUSADRS` | Situs **on** polygons |
| lastSale date/price | Yes | `SalePrice`, `DeedDate`, `DeedBookPage` | SalePrice>0 → **20969** |
| tax values | Yes | `MarketValue`, `LandValue`, `BuildingValue`, `ObxfValue`, `AssessedValue`, `DeferredValue` | |
| zoning | Yes (split) | Oxford `Zoning`; Creedmoor `Zoning_Typ`; Butner `NewZone`; Stovall `NAME`; county `ZONECODE` | **Stem gap**; parcel.Zoning empty |
| flu | Yes | `FLU` on Granville_FLU/11 | Countywide; no city FLU FS |
| appraiser / viewer link | Yes | ITSPublic + Experience map | Templates below |

## Layers (verified)

### 1. Granville_Service/Parcels_Polygon — parcels + CAMA + situs + sale + tax (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | situs
- **REST URL:** https://services8.arcgis.com/dT3Tew5pivPd2bWH/arcgis/rest/services/Granville_Service/FeatureServer/8
- **Layer name / id:** Parcels_Polygon / 8
- **Geometry:** Polygon
- **Key fields → targets:**
  - `Parcel`, `PIN`, `PRODNO`, `RECN` → parcelId*
  - `Cal_Acres`, `LandUnits` → acreage
  - `OwnerName1`, `OwnerName2` → ownerName
  - `AddressLine*`, `City`, `State`, `Zip` → mailing
  - `FormattedPropertyAddress` → situs
  - `SalePrice`, `DeedDate`, `DeedBookPage` → lastSale
  - `MarketValue`, `LandValue`, `BuildingValue`, `AssessedValue`, `DeferredValue`, `ObxfValue` → tax
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **34,898**; `Cal_Acres BETWEEN 5 AND 150` → **7,186**; SalePrice>0 → **20,969**; geo centroid sample in Granville (−78.56, 36.45)
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **1000**. Parcel `Zoning` field empty — join district layers. Do **not** use layer 9 (Townships) for parcels.

### 2. AddressPoints — situs / NG911

- **REST:** …/Granville_Service/FeatureServer/0
- **Geometry:** Point | count **30,228**
- **Fields:** `SITUSADRS`, `IncMuni`, `City`, `Zip`, street components
- **Status:** usable

### 3. GC_ZONING — county base + muni stubs

- **REST:** …/Granville_Static/FeatureServer/26
- **Count:** **177** | `ZONECODE` → zoning
- **Districts:** AR-40, AR-80, ASE-CZ, HB, I-1, I-2, MHPD, NB, O-I, R-25 + BUTNER/CREEDMOOR/OXFORD/STEM/STOVALL PLANNING AND ZONING AREA stubs
- **Status:** usable (prefer city layers inside stubs)

### 4. Oxford Zoning 2024 — city-first

- **REST:** …/Granville_Static/FeatureServer/45
- **Count:** **6,857** | `Zoning` populated **5,434** | parcel-keyed
- **Districts:** CBD, GR10, GR3, GR5, HB, HI, IPD, LI, NB, OI, PUD, RA
- **Geo-verified:** (−78.59, 36.30)
- **Status:** usable

### 5. Creedmoor Zoning — city-first

- **REST:** …/Granville_Static/FeatureServer/24
- **Count:** **75** | `Zoning_Typ` | overlay `/47` count **6**
- **Types:** AG, C-15, C-56, CIV, CZ, IND, MS, MSP, OSP, R/MST, SFR
- **Status:** usable

### 6. Butner Zoning — city-first

- **REST:** …/Granville_Static/FeatureServer/43
- **Count:** **228** | `NewZone`
- **Geo-verified:** (−78.74, 36.19)
- **Status:** usable

### 7. Stovall Zoning — city-first

- **REST:** …/Granville_Static/FeatureServer/50
- **Count:** **42** | `NAME` / `NAME_ABB`
- **Status:** usable

### 8. Granville Future Land Use (FLU)

- **REST:** …/Granville_FLU/FeatureServer/11
- **Count:** **109** | `FLU` / `ACRES`
- **Categories:** COM, CON-RES, IND, MED-RES, MIX-USE, MXU, PARK, R-COM, R-RES, STATE, SUB-RES, SUBRES, WATER BODY
- **Status:** usable

### 9. NC OneMap Parcels — fallback

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='077'` | count **34,602**
- **Notes:** `gisacres` + `siteadd` + values populated; **no** sale price
- **Status:** partial

### 10. City_Limits + ETJ + VAD

- **City_Limits /42:** BUTNER, CREEDMOOR, OXFORD, STEM, STOVALL
- **ETJ2025 /38** (+ ButnerETJ /41, Creedmoor /23, Oxford /39)
- **VAD:** Granville_VAD/0 (overlay)
- **Status:** usable

## Municipalities (city-first routing)

| Municipality | Zoning REST | FLU REST | Notes |
|--------------|-------------|----------|-------|
| Oxford | Granville_Static/45 | Granville_FLU/11 | Parcel-keyed zoning 2024 |
| Butner | Granville_Static/43 | Granville_FLU/11 | NewZone districts |
| Creedmoor | Granville_Static/24 (+ overlay /47) | Granville_FLU/11 | Zoning_Typ |
| Stovall | Granville_Static/50 | Granville_FLU/11 | NAME districts |
| Stem | **gap** | Granville_FLU/11 | GC_ZONING stub only |
| Unincorporated county | GC_ZONING /26 | Granville_FLU/11 | AR-40 / AR-80 / etc. |

## Deep-link templates

- **Appraiser / real estate search:** `https://tax.granvillecounty.org/ITSPublic/RealEstateSearch/Parcel/{Parcel}` (12-digit `Parcel`)
- **Tax bill search:** `https://tax.granvillecounty.org/ITSPublic/TaxBillSearch/Parcel/{Parcel}`
- **Viewer:** https://experience.arcgis.com/experience/9fb947310691479b8a2468d86316e8de
- **Public GIS page:** https://www.granvillecounty.org/259/GIS-Geographic-Information-System

## Gaps

- Stem — no dedicated public zoning FeatureServer
- Parcel `Zoning` attribute empty on live REST — spatial-join district layers
- No independent municipal ArcGIS hosts (city layers on county AGOL)
- No city-specific FLU FeatureServers — county FLU only
- ITSPublic ViewParcel card is AJAX/POST — use GET `/Parcel/{Parcel}` templates
- Web maps mislabel parcels as layer 9 (Townships) — use layer **8**
- MaxRecordCount 1000 on county AGOL — paginate
- OneMap lacks `SalePrice`
- No phones/emails; no paid vendors; utilities + AADT out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- Live REST counts, field maps, sample attributes, and WGS84 centroids checked for county parcels, GC_ZONING, Oxford/Butner/Creedmoor/Stovall zoning, FLU, and NC OneMap (`cntyfips='077'`).


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services8.arcgis.com/dT3Tew5pivPd2bWH/arcgis/rest/services/Granville_Service/FeatureServer/8 · id `Parcel` · live count **34,898** · 5–150 ac **7,186** (`Cal_Acres >= 5 AND Cal_Acres <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='GRANVILLE'` gives **399** stations (222 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27GRANVILLE%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Granville'` gives **397** stations (288 with AADT_2025, 221 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Granville%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Granville'` gives **397** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok):** `MarketValue` non-zero **34,790**, `AssessedValue` non-zero **34,790**
- **Sale history (ok):** price `SalePrice` >0 **20,969**; date `DeedDate` non-null **33,094**
- **Owner entity:** fields `OwnerName1`, `OwnerName2`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **1,066** of 7,186 (extended regex: 1,260).
- **PA deep link:** `https://tax.granvillecounty.org/ITSPublic/RealEstateSearch/Parcel/{Parcel}`. Tested `183400314774` → HTTP **200** (text/html), content verified: True. Parcel id found in the response body.
- **Jurisdiction GIS viewer:** https://experience.arcgis.com/experience/9fb947310691479b8a2468d86316e8de → HTTP **200** (Experience)
- **Pass 2 gaps:** none
