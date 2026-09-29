# Buncombe County, NC — GIS County Card

## Summary

Buncombe County (Asheville MSA, FIPS **37021**) publishes countywide cadastral + CAMA attributes on **`gis.buncombecounty.org`** / **`gis.buncombenc.gov`** **opendata** FeatureServer. **Wire-first parcels:** `opendata/FeatureServer/1` (**Property**) — ~**135.3k** polygons with `PIN`, owner, mailing, **situs components**, `Acreage`, land/building/total values (strings), `DeedDate`/`SalePrice`, `City` municipality code, and Spatialest **PropCard** deep link. ~**10,526** with `Acreage` 5–150 (~**4,405** with `Improved` blank/N in range). **Zoning is municipality-split:** county zoning covers unincorporated only (`opendata/FeatureServer/5`, **623**); **City of Asheville** publishes its own ZoningDistricts + FLU; **Woodfin / Black Mountain / Montreat** zoning layers are hosted on county map services; **Weaverville** has public AGOL zoning; **Biltmore Forest** zoning is PDF-only (honest gap). **FLU:** Asheville `FutureLandUseOverlay` (**24** coarse `commtype` polygons); county **Growth, Equity and Conservation (GEC)** map is FLU-adjacent (**202**); no countywide parcel-level FLU REST. **NC OneMap** (`cntyfips='021'`) has geometry + owner/tax for ~135k but **`gisacres` is all 0** — use county Property for acreage.

## Portals

- **Buncombe County GIS / BuncoMap** — https://gis.buncombenc.gov/buncomap/ (was buncomap_new/, 404 on 2026-09-28) (alias `gis.buncombecounty.org`)
- **County GIS department** — https://www.buncombecounty.org/Governing/Depts/GIS/Default.aspx
- **Property card (Spatialest)** — https://prc-buncombe.spatialest.com/ — Deep link: `https://prc-buncombe.spatialest.com/#/property/{PIN}`
- **County ArcGIS REST** — https://gis.buncombecounty.org/arcgis/rest/services
- **City of Asheville GIS REST** — https://gis.ashevillenc.gov/server/rest/services
- **Weaverville Zoning Experience** — https://experience.arcgis.com/experience/4ffdfb01bf9b4116aeebf73518db946d
- **Black Mountain web map** — https://bmt.maps.arcgis.com/apps/webappviewer/index.html?id=524a665910c5480881fa7fefbc6abe63 (viewer; zoning polygons via county host)
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`; OneMap `parno`; `AccountNumber` alt | 15-digit PIN (e.g. `963470749800000`) |
| polygons | Yes | opendata Property FS/1 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `Acreage` | ~**10,526** in 5–150; OneMap `gisacres` **unusable (all 0)** |
| ownerName | Yes | `Owner`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `Address` + `CityName` + `State` + `Zipcode` (+ `CareOf`) | `Address` is **mailing**, not always situs |
| situs address | Yes (compose) | `HouseNumber`,`NumberSuffix`,`StreetPrefix`,`StreetName`,`StreetType`,`StreetPostDirection` | Compose situs; do not use `Address` alone |
| lastSale date/price | Partial | `DeedDate`, `SalePrice`, `Stamps`, `DeedBook`/`DeedPage` | `SalePrice` string; ~**28,305** non-zero — **validate** vs Spatialest (values often look stamp-like / low) |
| tax values | Yes | `TotalMarketValue`,`AppraisedValue`,`TaxValue`,`LandValue`,`BuildingValue` | All **strings** — cast; land/improve split present |
| zoning | Yes (split) | Spatial join by municipality — see Municipalities | No zoning attr on primary parcel layer |
| flu | Partial | Asheville `commtype`; county GEC `Name` | City FLU coarse; county GEC not full FLU; munis mostly gap |
| appraiser / viewer link | Yes | `PropCard` → Spatialest by PIN | Template below |

### City / DistCode municipality codes (parcel `City` / Incorporated Areas)

| Code | Jurisdiction | Parcel count (approx) | Zoning source |
|------|----------------|----------------------|---------------|
| CAS | City of Asheville | **39,800** | City ZoningDistricts FS/11 (**prefer**) |
| CBF | Town of Biltmore Forest | **759** | **PDF only** — no public zoning REST |
| CBM | Town of Black Mountain | **5,175** | County `bcmapimage2_B/31` |
| CMT | Town of Montreat | **925** | County `Montreat_Map` FS/0 |
| CWO | Town of Woodfin | **4,370** | County `bcmapimage2_B/30` |
| CWV | Town of Weaverville | **2,920** | Town AGOL Zoning (**prefer**) |
| *(blank)* | Unincorporated Buncombe | **~81,338** | County Zoning FS/5 |

## Layers (verified)

### 1. opendata Property — parcels + ownership + tax + situs + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (attr) | situs
- **REST URL (wire-first):** https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/1
- **MapServer mirror:** https://gis.buncombecounty.org/arcgis/rest/services/opendata/MapServer/1
- **Layer name / id:** Property / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId
  - `AccountNumber` → parcelIdAlt
  - `Acreage` → acreage
  - `Owner` → ownerName
  - `Address`,`CityName`,`State`,`Zipcode`,`CareOf` → mailing
  - `HouseNumber`,`NumberSuffix`,`StreetPrefix`,`StreetName`,`StreetType`,`StreetPostDirection` → situs (compose)
  - `DeedDate`,`SalePrice`,`Stamps`,`DeedBook`,`DeedPage`,`Instrument` → lastSale
  - `TotalMarketValue`,`AppraisedValue`,`TaxValue` → tax.market / assessed
  - `LandValue`,`BuildingValue` → tax.land / improvement
  - `City` → municipalityCode (CAS/CBF/CBM/CMT/CWO/CWV)
  - `Class`,`Improved`,`LandUse`,`NeighborhoodCode` → land-use hints
  - `PropCard` → appraiserSearchUrl (Spatialest)
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **135,287**; `Acreage` 5–150 → **10,526**; `Improved` blank/N in 5–150 → **4,405**; `SalePrice` non-zero → **28,305**; sample owner/mail/situs/tax/PropCard OK
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **2000** — paginate. Values are strings — cast. `Address`≠situs. Prefer Spatialest for sale-price QA.

### 2. NC OneMap Parcels (polys) — statewide fallback (partial for Buncombe)

- **Purpose:** parcels | tax | ownership | situs (geometry)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Geometry:** Polygon (verified rings present)
- **Key fields → targets:**
  - `parno` → parcelId (aligns with `PIN`)
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs
  - `gisacres` → acreage — **ALL 0 for cntyfips=021** (do not filter 5–150 here)
  - `saledate`,`saledatetx` → lastSale.date (**no sale price**)
  - `parval`,`landval`,`improvval` → tax (~**116,307** with `parval>0`)
  - `cntyfips`=`021`, `cntyname` → Buncombe filter
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — filter count **134,741**; `gisacres>0` → **0**; `parval>0` → **116,307**
- **Notes:** Geometry + owner/tax OK; **acreage gap** — always join/prefer county `Acreage`. MaxRecordCount **5000**.

### 3. Buncombe County Zoning — unincorporated only (PRIMARY for UNINC)

- **Purpose:** zoning
- **REST URL:** https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/5
- **MapServer mirrors:** opendata/MapServer/5; bcmapimage2_B/MapServer/32 (`ZONING_CODE`)
- **Fields:** `ZoningCode`, `Resolution`, `DateZoned`, `Comment`
- **WKID / CRS:** 102719 / 2264
- **Join to parcels:** spatial join where `City` blank / outside incorporated areas
- **Verified:** yes — count **623**; codes: AI, BDM, CR, CS, EMP, NS, OU, PS, R-1, R-2, R-3, R-LD
- **Notes:** Does **not** cover Asheville / towns — city-split zoning required.

### 4. County Zoning Overlay

- **REST URL:** https://gis.buncombecounty.org/arcgis/rest/services/bcmapimage2_B/MapServer/33
- **Fields:** `type`, `PARKWAY`, `ID`, `GRIDCODE`
- **Verified:** yes — count **30,171**
- **Notes:** Overlay (e.g. Parkway) — not base districts; spatial join as secondary constraint.

### 5. City of Asheville Zoning Districts — prefer most local (CAS)

- **Purpose:** zoning
- **REST URL:** https://gis.ashevillenc.gov/server/rest/services/Districts/ZoningDistricts/FeatureServer/11
- **MapServer:** …/ZoningDistricts/MapServer/11
- **County stub (mirror):** bcmapimage2_B/MapServer/29 (`DISTRICTS`) — count **738**
- **Fields:** `districts`, `ordinance`, `hyperlink`, `overlay_type`, `status`, `type`, `notes`, `acreage`
- **Verified:** yes — count **738**; **46** distinct district codes (CBD, RM16, RS8, IND, UV, …)
- **Notes:** Prefer city host inside Asheville limits. Overlays: `Planning/ZoningOverlays` (Historic, PUD, Parkway, MH-O, etc.).

### 6. Asheville Property Zoning Categories — parcel-attributed zoning (CAS)

- **Purpose:** zoning (parcel polygons with district)
- **REST URL:** https://gis.ashevillenc.gov/server/rest/services/Planning/PropertyZoningCategories/FeatureServer/79
- **Fields:** `pin`,`pinnum`,`address`,`tax_acreage`,`districts`,`review`,`design`,`parking`,`sevenf`
- **Verified:** yes — count **39,803** (≈ CAS parcel count)
- **Notes:** Attribute-friendly join `pinnum`↔`PIN`; still cross-check spatial ZoningDistricts for authority.

### 7. Asheville Future Land Use — FLU (CAS)

- **Purpose:** flu
- **REST URL:** https://gis.ashevillenc.gov/server/rest/services/Planning/FutureLandUseOverlay/FeatureServer/67
- **Fields:** `commtype`, `edit_date`, `edit_by`
- **Verified:** yes — count **24** (coarse community types)
- **`commtype` values:** Downtown, Town Center, Urban Center, Urban Corridor, Traditional Corridor, Traditional Neighborhood, Residential Neighborhood, Neighborhood Centers, Employment / Anchor Institution, Industrial / Manufacturing, Parks and Open Space, Regional Corridor
- **Notes:** Spatial join only (no PIN). Coarse — not parcel-level FLU.

### 8. Growth, Equity and Conservation Map — county FLU-adjacent

- **Purpose:** other / FLU-adjacent
- **REST URL:** https://gis.buncombecounty.org/arcgis/rest/services/bcmap_vt/MapServer/57
- **Fields:** `Name`
- **Verified:** yes — count **202**; names: CWL, INST, MU1, MU2, MUN, MUNIC, PPL, RC, WDC
- **Notes:** Comprehensive-plan place categories — **not** a full substitute for municipal FLU. County Comp Land Use Plan 2013 is primarily map/PDF on GIS dept page.

### 9. Incorporated Areas

- **REST URL:** https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/4
- **Fields:** `DistCode`, `Description` (CAS, CBF, CBM, CMT, CWV, CWO)
- **Notes:** Use with parcel `City` for municipality routing.

## Municipalities (first-class)

County parcels are countywide; **zoning authority is municipal** (or county for unincorporated). Join pattern: Property FS/1 (2264) → route by `City` / Incorporated Areas → spatial join most-local zoning → FLU where published.

### City of Asheville (CAS) — prefer most local

- **Parcels:** county Property where `City='CAS'` (~**39,800**)
- **Zoning (city host):** Districts/ZoningDistricts/FeatureServer/11 — `districts`; **738**
- **Zoning (parcel attr):** PropertyZoningCategories/79 — `districts` on `pinnum`; **39,803**
- **FLU:** FutureLandUseOverlay/67 — `commtype`; **24**
- **Overlays:** Planning/ZoningOverlays FeatureServer
- **Join note:** Prefer city zoning + FLU inside city limits; county Zoning FS/5 does **not** apply in CAS.

### Town of Weaverville (CWV) — prefer most local

- **Parcels:** county Property `City='CWV'` (~**2,920**)
- **Zoning (town AGOL — prefer):** https://services5.arcgis.com/lA7fMEY4qaPiZF6g/arcgis/rest/services/Zoning_ForApp/FeatureServer/0 — `Code`; **55** (codes C-1, C-2, CZD, I-1, R-1, R-12, R-2, R-3)
- **Zoning (town polygons):** TOW_Zoning_WFL1_view/FeatureServer/2 — `Code`; **145**
- **Zoning by parcels:** Zoning_ByParcels/FeatureServer/0 — `WVL_Zoning`/`Code` + CAMA attrs; **2,887**
- **Viewer:** https://experience.arcgis.com/experience/4ffdfb01bf9b4116aeebf73518db946d
- **FLU:** no dedicated public FLU FeatureServer verified (CLUP/growth areas in town docs / Experience — treat as gap for REST FLU)
- **Join note:** Prefer town AGOL zoning; county map services do **not** list a Weaverville zoning layer (town provided layer to county — not yet on bcmapimage2_B).

### Town of Black Mountain (CBM)

- **Parcels:** `City='CBM'` (~**5,175**)
- **Zoning (county host):** https://gis.buncombecounty.org/arcgis/rest/services/bcmapimage2_B/MapServer/31 — `ZoneCode`; **12** (CB, CR-1, HB-8, HI-0, ICD, LI-8, NMU-8, OI-6, SR-2, TND, TR-4, UR-8)
- **Alt:** bcmap_vt/MapServer/61
- **Viewer:** https://bmt.maps.arcgis.com/apps/webappviewer/index.html?id=524a665910c5480881fa7fefbc6abe63
- **FLU:** no public FLU REST verified
- **Join note:** County-hosted town zoning is the public wire; no separate town FeatureServer found.

### Town of Woodfin (CWO)

- **Parcels:** `City='CWO'` (~**4,370**)
- **Zoning (county host):** https://gis.buncombecounty.org/arcgis/rest/services/bcmapimage2_B/MapServer/30 — `ZoneCode`; **9** (Community Shopping, Heavy/Light Industrial, Mountain Village, R-7/10/21/43, Transitional District)
- **Alt:** bcmap_vt/MapServer/59
- **FLU:** no public FLU REST verified
- **Join note:** County stub is the public zoning source (Edgewood-style where town doesn’t publish its own FS).

### Town of Montreat (CMT)

- **Parcels:** `City='CMT'` (~**925**)
- **Zoning:** https://gis.buncombecounty.org/arcgis/rest/services/Montreat_Map/FeatureServer/0 — `Zoning`; **8** (Conservation, Institutional, Institutional Residential, R-1, R-1 CZ, R-2, R-3, Woodland)
- **Alt:** bcmap_vt/MapServer/66
- **FLU:** no public FLU REST verified

### Town of Biltmore Forest (CBF) — zoning gap

- **Parcels:** `City='CBF'` (~**759**)
- **Zoning:** **no public ArcGIS REST** verified — town publishes zoning **PDF** only (biltmoreforest.org planning-zoning/maps)
- **FLU:** no public FLU REST
- **Join note:** County parcels usable; zoning must be PDF / manual / future REST — honest gap (do not invent county Zoning for CBF).

### Buncombe County unincorporated

- **Parcels:** `City` blank (~**81,338**)
- **Zoning:** opendata/FeatureServer/5 — **623**
- **FLU-adjacent:** GEC Map bcmap_vt/57; Comp Land Use Plan 2013 (map/PDF)
- **Overlays:** County Zoning Overlay (Parkway etc.)

## Gaps

- **No zoning attribute on primary Property layer** — must spatial-join by municipality
- **Zoning is city-split** — county FS/5 is unincorporated only; never treat as countywide
- **Biltmore Forest zoning REST missing** — PDF only
- **Weaverville / Black Mountain / Woodfin / Montreat FLU** — no dedicated public FLU FeatureServers verified
- **County FLU** — GEC is coarse place categories; 2013 Comp Plan not a queryable parcel FLU REST
- **Asheville FLU** only **24** coarse `commtype` polygons
- **NC OneMap `gisacres` all 0** for Buncombe — do not use for 5–150 filter
- **`SalePrice` reliability** — present as string (~28k non-zero) but sample values often look stamp-like / low vs market; validate via Spatialest PropCard; `Stamps` + `DeedDate` also available
- **Tax/value fields are strings** — cast to number
- **Situs must be composed** from HouseNumber/Street* — `Address` is mailing
- **MaxRecordCount 2000** on county opendata — paginate
- **No paid vendor data**; no phones/emails collected
- **landuse MapServer** is slope/flood constraints — not FLU

## Hand-off notes for Land Search Builder

1. **Wire first:** `opendata/FeatureServer/1` — polygons + PIN, Owner, mailing, situs components, Acreage, land/building/total values, DeedDate/SalePrice, City, PropCard. Filter `Acreage BETWEEN 5 AND 150` (~10.5k). Optional vacant-ish: `Improved` blank/N (~4.4k in range).
2. **Zoning:** route by `City` / Incorporated Areas → Asheville city FS/11 (or PropertyZoningCategories/79); Weaverville AGOL; Black Mountain / Woodfin / Montreat county-hosted layers; county FS/5 for unincorporated; **CBF gap**.
3. **FLU:** Asheville FutureLandUseOverlay/67 spatial join; county GEC/57 as secondary; other munis = gap / plan PDFs.
4. **Sales:** use `DeedDate` + validate `SalePrice` against Spatialest; no separate sales FeatureServer verified.
5. **Fallback:** NC OneMap layer 1 `cntyfips='021'` for geometry/owner/tax — **not** acreage.
6. **Viewer / appraiser links:**
   - Spatialest: `https://prc-buncombe.spatialest.com/#/property/{PIN}`
   - BuncoMap: `https://gis.buncombenc.gov/buncomap/` (was buncomap_new/, which returned 404 on 2026-09-28)
7. **Join keys:** `PIN` (preferred), `AccountNumber`, OneMap `parno`↔`PIN`, Asheville `pinnum`↔`PIN`
8. **Auth:** none observed on listed public query endpoints
9. **Cities/towns are first-class:** never treat county Zoning alone as countywide coverage

## Verification

- **verifiedAt:** 2026-09-23
- **verifiedBy:** North Carolina Public Info Researcher
- Live query checks: Property count/acreage/SalePrice/City distinct; County Zoning codes; Asheville ZoningDistricts + FLU + PropertyZoningCategories; Woodfin/Black Mountain/Montreat zoning counts; Weaverville AGOL Zoning_ForApp / TOW_Zoning / Zoning_ByParcels; OneMap cntyfips=021 gisacres=0 / parval>0; GEC names; Incorporated Areas DistCodes.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/1 · id `PIN` · live count **135,323** · 5–150 ac **10,526** (`Acreage >= 5 AND Acreage <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='BUNCOMBE'` gives **879** stations (823 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27BUNCOMBE%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Buncombe'` gives **878** stations (155 with AADT_2025, 673 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Buncombe%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `TotalMarketValue` non-zero **130,873**, `TaxValue` non-zero **130,872** Value fields are strings: use CAST(field AS FLOAT) > 0.
- **Sale history (ok):** price `SalePrice` >0 **28,302**; date `DeedDate` non-null **135,323**. SalePrice and DeedDate are strings; CAST SalePrice AS FLOAT.
- **Owner entity:** fields `Owner`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **3,102** (all parcels: 31,255), using the SQL approximation on `Owner`.
- **PA deep link:** `https://prc-buncombe.spatialest.com/#/property/{PIN}`. Tested `878064941500000` → HTTP **200** (text/html; charset=UTF-8), content verified: False. Spatialest SPA (hash route): 200 shell, parcel content cannot be checked server-side.
- **Jurisdiction GIS viewer:** https://gis.buncombenc.gov/buncomap/ → HTTP **200** (Buncombe County GIS). Card URL https://gis.buncombenc.gov/buncomap_new/ now returns 404 (http too); use /buncomap/ (200, ArcGIS JS viewer).
- **Pass 2 gaps:** jurisdictionGisUrl buncomap_new 404, replaced with /buncomap/
