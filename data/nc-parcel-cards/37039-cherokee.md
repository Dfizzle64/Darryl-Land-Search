# Cherokee County, NC — GIS County Card

## Summary

Cherokee County (Asheville / Western NC, FIPS **37039**, slug **cherokee**, `cntyfips='039'`) publishes CAMA parcels on county ArcGIS **OfficeView/MapServer/1** (~**35,749** polys) with owner (`Name1`/`Name2`), mailing, situs, `TOTAL_CALCULATED_ACRES`, full tax split (`ParcelLandValue`/`ParcelBuildingValue`/`TotalAssessedValue`), **`SalePrice`** + `SaleMonth`/`SaleYear`, and embedded **`TaxCardLink`**. ~**6,510** with acres 5–150; **20,249** with `SalePrice>0`. AGOL **Parcels** FeatureServer is a truncated-name mirror (~**35,746**) with the same CAMA + `TaxCard` URL. **Zoning is cities-first:** Town of **Murphy** (MurphyNCZoning, **36**) and Town of **Andrews** (AndrewsNCZoning, **21**); unincorporated Cherokee is **largely unzoned** on public REST. **FLU:** no public FeatureServer (ordinance / CTP PDFs only). **PA deep-link:** `http://www.cherokeecounty-nc.gov:8080/TaxNet/AppraisalCard.aspx?idP={ParcelID}&Action=Auto`. **Jurisdiction GIS:** https://maps.cherokeecounty-nc.gov/GISweb/GISviewer/. Markets: **[Asheville]**.

## Portals

- **Jurisdiction GIS (GISviewer)** — https://maps.cherokeecounty-nc.gov/GISweb/GISviewer/
- **Interactive Map Viewer (disclaimer gate)** — https://www.cherokeecounty-nc.gov/197/Interactive-Map-Viewer
- **GIS Data & Application Gateway** — https://www.cherokeecounty-nc.gov/194/GIS-Data-and-Application-Gateway
- **Open Data Hub** — https://cherokeecounty-nc-gis-ccncgis.opendata.arcgis.com/
- **County ArcGIS REST** — https://maps.cherokeecounty-nc.gov/ccgis/rest/services
- **AGOL org services** — https://services5.arcgis.com/UmQCfTNQbyTzAV5N/arcgis/rest/services
- **TaxNet Basic Search** — http://www.cherokeecounty-nc.gov:8080/TaxNet/BasicSearch.aspx
- **TaxNet Appraisal Card (PA deep-link)** — `http://www.cherokeecounty-nc.gov:8080/TaxNet/AppraisalCard.aspx?idP={ParcelID}&Action=Auto`
- **NCPTS parcel detail** — `https://lrcpwa.ncptscloud.com/cherokee/parcel-detail/{NEWPIN}`
- **NCPTS search** — https://lrcpwa.ncptscloud.com/cherokee/parcel-search
- **Murphy zoning instant app** — https://ccncgis.maps.arcgis.com/apps/instant/minimalist/index.html?appid=d488231337ce4dcc94c31b97b78c9ce3
- **Andrews zoning instant app** — https://ccncgis.maps.arcgis.com/apps/instant/minimalist/index.html?appid=656ca34590a049f888743876372772fb
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='039'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `NEWPIN`; `ParcelID` (TaxNet); OneMap `parno` | e.g. `555618308588000` ↔ idP `4598268` |
| polygons | Yes | OfficeView/1; AGOL Parcels/0; Land_Records/17 | CRS **102719 / 2264** |
| acreage | Yes | `TOTAL_CALCULATED_ACRES`; `POLY_ACRES`; OneMap `gisacres` | ~**6,510** in 5–150 |
| ownerName | Yes | `Name1`+`Name2`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `Address1`/`Address2`,`City`,`State`,`ZipCode` | |
| situs address | Yes | `HouseNumber`+`StreetDirection`+`StreetName`+`StreetType`; OneMap `siteadd` | |
| lastSale date/price | Yes | `SalePrice`,`SaleMonth`,`SaleYear`; AGOL/QualifiedSales | ~**20,249** SalePrice>0; date = month/year |
| tax values | Yes | `ParcelLandValue`,`ParcelBuildingValue`,`ParcelObxfValue`,`TotalAssessedValue` | |
| zoning | Yes (cities-first) | Murphy/Andrews `ZoneType`/`ZoneDesc` | Unincorp **unzoned** on REST |
| flu | Gap / PDF | Murphy AmLegal code; Andrews Zoning Ordinance PDF; NCDOT CTP | No FLU FeatureServer |
| appraiser / viewer link | Yes | TaxCardLink `{ParcelID}`; NCPTS `{NEWPIN}`; GISviewer | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. OfficeView — parcels + ownership + tax + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | situs
- **REST URL:** https://maps.cherokeecounty-nc.gov/ccgis/rest/services/OfficeView/MapServer/1
- **Layer name / id:** OfficeView / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `NEWPIN` → parcelId
  - `ParcelID` → parcelIdInternal / TaxNet `idP`
  - `AccountNumber` → parcelIdAccount
  - `TOTAL_CALCULATED_ACRES`, `POLY_ACRES`, `LegalLandUnits` → acreage
  - `Name1`, `Name2` → ownerName
  - `Address1`, `Address2`, `City`, `State`, `ZipCode` → mailing
  - `HouseNumber`, `StreetDirection`, `StreetName`, `StreetType` → situs
  - `LegalDescription` → legal
  - `SalePrice`, `SaleMonth`, `SaleYear`, `VacantOrImproved` → lastSale
  - `DeedBook`, `DeedPage`, `PlatBook`, `PlatPage` → deed / plat
  - `ParcelLandValue`, `ParcelBuildingValue`, `ParcelObxfValue`, `ParcelSpecialLandValue`, `ParcelDeferredValue`, `TotalAssessedValue` → tax
  - `TaxCardLink` → appraiser deep-link (full URL with `idP`)
- **WKID / CRS:** 102719 (latest 2264)
- **Verified:** yes — count **35,749**; `TOTAL_CALCULATED_ACRES BETWEEN 5 AND 150` → **6,510**; `SalePrice>0` → **20,249**; `TotalAssessedValue>0` → **35,728**; `TaxCardLink IS NOT NULL` → **35,749**; sample `NEWPIN=555618308588000` FC ENCORE ANDREWS LLC centroid ≈ **-83.843, 35.194** (Andrews); join OneMap `parno` OK; AppraisalCard HTTP 200 with owner text for `idP=4598268`
- **Notes:** PRIMARY wire-first. MaxRecordCount **2000** — paginate. Auth **none**. Legacy `Dynamic/MapServer/2` / `SalesData` referenced by old webmaps are **404** (retired) — do not wire.

### 2. AGOL Parcels — CAMA mirror (truncated field names)

- **Purpose:** parcels | tax | ownership | sales
- **REST URL:** https://services5.arcgis.com/UmQCfTNQbyTzAV5N/arcgis/rest/services/Parcels/FeatureServer/0
- **Key fields:** `NEWPIN`, `TOTAL_CALC`, `LegalLandU`, `AccountNum`, `Name1`/`Name2`, address/situs truncations, `ParcelLand`/`ParcelBuil`/`TotalAsses`, `SalePrice`/`SaleMonth`/`SaleYear`, **`TaxCard`** (full AppraisalCard URL)
- **Verified:** count **35,746**; acres 5–150 → **6,512**; SalePrice>0 → **20,264**
- **Notes:** Prefer when AGOL egress is easier; field names truncated vs OfficeView. Same TaxNet `idP` in `TaxCard`.

### 3. Land_Records parcel_polygons — geometry twin

- **Purpose:** parcels (geometry + PIN)
- **REST URL:** https://maps.cherokeecounty-nc.gov/ccgis/rest/services/Land_Records/MapServer/17
- **Fields:** `PIN`, `NEWPIN`, `POLY_ACRES`, `TOTAL_CALCULATED_ACRES` (no owner/tax/sale)
- **Verified:** count **35,701**
- **Notes:** Join to OfficeView on `NEWPIN` if geometry-only extract needed.

### 4. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date text)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='039'`
- **Key fields:** `parno`↔`NEWPIN`, `ownname`, `mailadd`, `siteadd`, `gisacres`, `saledatetx`, `parval`/`landval`/`improvval`
- **Verified:** count **35,669**; `gisacres` 5–150 → **6,507**; join verified `parno='555618308588000'`; `saledatetx` populated county-wide (~35,669) but **no sale price**
- **Notes:** Prefer county `SalePrice`. MaxRecordCount **5000**.

### 5. Zoning — cities-first Murphy + Andrews (PRIMARY routing)

| Municipality | REST | Count | Zone field |
|--------------|------|------:|------------|
| **Murphy** (seat) | https://services5.arcgis.com/UmQCfTNQbyTzAV5N/arcgis/rest/services/MurphyNCZoning/FeatureServer/0 | **36** | `ZoneType` / `ZoneDesc` (A-T, F-W, G-B, H-B, I-H-C, R-1, R-2) |
| **Andrews** | https://services5.arcgis.com/UmQCfTNQbyTzAV5N/arcgis/rest/services/AndrewsNCZoning/FeatureServer/0 | **21** | `ZoneType` / `ZoneDesc` (CB, GR, HB, HC-I, SF) |

- **Viewers:** Murphy instant app `appid=d488231337ce4dcc94c31b97b78c9ce3`; Andrews `appid=656ca34590a049f888743876372772fb`
- **Join:** spatial join zoning → parcels; route by Municipalities `MB_NAME` (Murphy / Andrews)
- **Notes:** Legacy county `MurphyZoning`/`AndrewsZoning` MapServers are **404**. Unincorporated (Marble, Brasstown, Topton, Peachtree, …) — **unzoned** on public REST (mountain-county pattern). Voluntary Agriculture / Bear Paw service districts are **not** zoning.

### 6. Municipal Boundaries / Communities

- **Municipalities FS/0:** https://services5.arcgis.com/UmQCfTNQbyTzAV5N/arcgis/rest/services/Municipalities/FeatureServer/0 — **2**: Andrews, Murphy
- **Communities FS/0:** https://services5.arcgis.com/UmQCfTNQbyTzAV5N/arcgis/rest/services/Communities/FeatureServer/0 — **49** community polys (Marble, Brasstown, Topton, Peachtree, Hiwassee Dam, …) — place-name routing only, not zoning

### 7. Sales overlays (optional)

- **QualifiedSales FS/0:** https://services5.arcgis.com/UmQCfTNQbyTzAV5N/arcgis/rest/services/QualifiedSales/FeatureServer/0 — **4,354** points
- **MergeSales FS/0:** https://services5.arcgis.com/UmQCfTNQbyTzAV5N/arcgis/rest/services/MergeSales/FeatureServer/0 — **6,785** points
- **Notes:** Prefer parcel-layer `SalePrice` for wire-first; overlays for qualified-sale enrichment.

### 8. FLU — PDF / ordinance only (no public FeatureServer)

- **Murphy Code of Ordinances (AmLegal):** https://codelibrary.amlegal.com/codes/murphy/latest/murphpy_nc/0-0-0-1
- **Murphy Zoning Map (media):** https://www.townofmurphync.com/media/5261
- **Andrews Zoning Ordinance PDF:** https://www.andrewsnc.org/download/17/
- **Andrews Planning & Zoning:** https://www.andrewsnc.org/planning-zoning-dept/
- **NCDOT Cherokee CTP (transportation, not FLU):** https://connect.ncdot.gov/projects/planning/Pages/CTP-Details.aspx?study_id=Cherokee+County
- **Notes:** No countywide or municipal FLU FeatureServer verified. Do not treat CTP as future land use.

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS REST? | FLU REST? | Notes |
|--------------|---------------|------:|:-------------:|:---------:|-------|
| **Murphy** | MurphyNCZoning/0 | 36 | County AGOL host | No | County seat; AmLegal code + zoning map PDF |
| **Andrews** | AndrewsNCZoning/0 | 21 | County AGOL host | No | Zoning Ordinance PDF |
| Marble / Brasstown / Topton / Peachtree / … | *(none)* | — | Communities polys | No | Unincorporated CDPs — **unzoned** |
| Unincorporated (other) | — | — | County | No | **Largely unzoned** |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| TaxNet Appraisal Card (preferred) | `http://www.cherokeecounty-nc.gov:8080/TaxNet/AppraisalCard.aspx?idP={ParcelID}&Action=Auto` |
| Encoding | Use integer `ParcelID` from OfficeView (also embedded in `TaxCardLink` / AGOL `TaxCard`) — **not** NEWPIN |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/cherokee/parcel-detail/{NEWPIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/cherokee/parcel-search |
| Jurisdiction GIS | https://maps.cherokeecounty-nc.gov/GISweb/GISviewer/ |

Verified AppraisalCard for `idP=4598268`: owner **FC ENCORE ANDREWS LLC**, NEWPIN `555618308588000`, SalePrice **$6,866,370**, TotalAssessedValue **$6,726,750**.

## Gaps / caveats

- **Countywide / municipal FLU REST gap** — ordinance PDFs + NCDOT CTP only; no FLU FeatureServer
- **Unincorporated zoning REST gap** — only Murphy + Andrews publish zoning polys; remainder unzoned on public REST
- Legacy **Dynamic / SalesData / MurphyZoning / AndrewsZoning MapServers** return **404** after server upgrade (webmaps still reference them) — use OfficeView + AGOL instead
- Sale **date** is month/year integers (`SaleMonth`/`SaleYear`), not a full timestamp
- TaxNet AppraisalCard is **HTTP :8080** (HTTPS on that port fails); prefer field `TaxCardLink` as stored
- Spatialest `/nc/cherokee` returns generic Spatialest shell — **not** used as PA deep-link
- OneMap has no sale **price**; prefer county `SalePrice`
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Cherokee County GIS / Tax Assessor / Land Records. Cadastral maps from recorded deeds/plats/public records; not survey quality; County disclaims warranties (see Interactive Map Viewer disclaimer). Commercial resale subject to **NCGS 132-10**. Attribute Cherokee County GIS (and Town of Murphy / Town of Andrews where municipal zoning used).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 10+
- **tranche:** 3 (tax/sale/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- Live `returnCountOnly` + sample attribute/geo queries against OfficeView, Land_Records/17, AGOL Parcels/MurphyNCZoning/AndrewsNCZoning/Municipalities/Communities/QualifiedSales/MergeSales, NC OneMap `cntyfips='039'`; TaxNet AppraisalCard HTTP cross-check; GISviewer; centroid geo-check in Cherokee (Andrews / Murphy).
