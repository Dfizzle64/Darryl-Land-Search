# Haywood County, NC — GIS County Card

## Summary

Haywood County (Asheville MSA, FIPS **37087**, slug **haywood**, `cntyfips='087'`) publishes a strong public ArcGIS stack at `maps.haywoodcountync.gov`. **Wire-first parcels (TRANCHE-3):** **SmartGov/SmartGovTaxView FeatureServer/0** — ~**53,187** polys with `ALPHA` PIN, owner, mailing (`Addr_*`+`CSZ`), situs (`Prop_Addr`+`ParcelZIP`), `Calc_Acres`, full tax split (`Mkt_Value`/`Assd_Value`/`Land_Value`/`Bldg_Value`/`Defer_Value`), **`Sale_Date`/`Sale_Price`/`VALID_SALE_CODE`**. ~**7,115** with acres 5–150. **Open_Data/Parcels/3** (~**50,525**) and **Public_Access/1** (~**51,290**) are CAMA mirrors (Open_Data MaxRecordCount **100000** — prefer for bulk extract when count catches up; Land Records notes a software transition). **Zoning is cities-first** on county-hosted Zoning (`Open_Data/9`, **140** polys) via `MAPNAME`: Waynesville (~**81**), Maggie Valley (**32**), Canton (**15**), Clyde (**8**) — **no unincorporated county zoning REST**. **FLU:** Waynesville 2035 Land Use Map **PDF**; Canton Comp Plan page; Maggie/Clyde/county **no FLU REST**. **PA deep-link:** `AppraisalCard.aspx?id={ALPHA_NO_DASHES}` (hyphens stripped). **Jurisdiction GIS:** https://maps.haywoodcountync.gov/gisweb/default.htm. Markets: **[Asheville]**.

## Portals

- **Jurisdiction GIS (Map Viewer)** — https://maps.haywoodcountync.gov/gisweb/default.htm
- **GIS home / terms** — https://maps.haywoodcountync.gov/
- **Open Data Hub** — https://opendata-hayco.hub.arcgis.com/
- **GIS Downloads** — https://maps.haywoodcountync.gov/downloads/default.aspx
- **County ArcGIS REST** — https://maps.haywoodcountync.gov/arcgis/rest/services
- **Land Records / GIS dept** — https://www.haywoodcountync.gov/203/Land-Records-Geographic-Information-Serv
- **Maps page** — https://www.haywoodcountync.gov/204/Maps
- **Appraisal card (PA deep-link, preferred)** — `https://taxes.haywoodcountync.gov/ITSPublic/AppraisalCard.aspx?id={ALPHA_NO_DASHES}`
- **Spatialest Real Property portal** — https://community.spatialest.com/nc/haywood/ — Deep link: `https://community.spatialest.com/nc/haywood/#/property/{ALPHA}`
- **NCPTS parcel detail** — `https://lrcpwa.ncptscloud.com/haywood/parcel-detail/{ALPHA}`
- **NCPTS search** — https://lrcpwa.ncptscloud.com/haywood/parcel-search
- **Tax Bill Search** — https://taxes.haywoodcountync.gov/ITSPublic/TaxBillSearch
- **Public Tax System Access (login portal)** — https://www.haywoodcountync.gov/922/Public-Tax-System-Access/ → https://taxes.haywoodcountync.gov/ITSForPublic
- **Waynesville Planning Maps** — https://www.waynesvillenc.gov/departments/development-services/planning-documents-maps
- **Waynesville 2035 Comp Plan (PDF)** — https://www.waynesvillenc.gov/sites/default/files/WaynesvilleCompPlan_11_11_2020_Rev_reduced.pdf
- **Waynesville FLU Map (PDF)** — https://www.waynesvillenc.gov/sites/default/files/Lettersize_FLU_2020_07_14_ForPackage.pdf
- **Waynesville Zoning Map (PDF)** — https://www.waynesvillenc.gov/sites/default/files/New%20Zoning%20Map%20February%2024%2C%202026.pdf
- **Canton Comp Plan / Zoning Updates** — https://www.cantonnc.com/build-a-better-canton-a-blueprint-for-recovery-renewal/
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='087'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `ALPHA` (PIN); OneMap `parno`; `Acct_Nbr` alt | e.g. `7688-23-9094` ↔ OneMap `parno` |
| polygons | Yes | SmartGov FS/0; Open_Data/3; PA/1 | CRS **102719 / 2264** |
| acreage | Yes | `Calc_Acres`; OneMap `gisacres` | SmartGov ~**7,115** in 5–150 |
| ownerName | Yes | `Owner_1`+`Owner_2`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `Addr_1`–`3`,`CSZ`; OneMap `mailadd` | |
| situs address | Yes | `Prop_Addr`; SmartGov `ParcelZIP`; OneMap `siteadd` | |
| lastSale date/price | Yes | `Sale_Date`/`Sale_Date_String`,`Sale_Price`,`VALID_SALE_CODE` | ~**28,814** Sale_Price>0 on Open_Data; OneMap has saledate |
| tax values | Yes | `Mkt_Value`,`Assd_Value`,`Land_Value`,`Bldg_Value`,`Defer_Value` | Typed doubles |
| zoning | Yes (cities-first) | Zoning `ZONING`/`ZONING_DEF` by `MAPNAME` | Unincorporated **unzoned** (REST gap) |
| flu | Partial / PDF | Waynesville FLU PDF; Canton Comp Plan | No FLU FeatureServer |
| appraiser / viewer link | Yes | AppraisalCard `{ALPHA_NO_DASHES}`; Spatialest `{ALPHA}`; NCPTS `{ALPHA}` | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. SmartGov TAX_VIEW_SmartGov — parcels + ownership + tax + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | situs
- **REST URL:** https://maps.haywoodcountync.gov/arcgis/rest/services/SmartGov/SmartGovTaxView/FeatureServer/0
- **MapServer mirror:** https://maps.haywoodcountync.gov/arcgis/rest/services/SmartGov/SmartGovTaxView/MapServer/0
- **Layer name / id:** TAX_VIEW_SmartGov / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `ALPHA` → parcelId (PIN; e.g. `7688-23-9094`)
  - `Acct_Nbr` → parcelIdAccount
  - `Calc_Acres` → acreage
  - `Owner_1`, `Owner_2` → ownerName
  - `Addr_1`, `Addr_2`, `CSZ` → mailing
  - `Prop_Addr`, `ParcelZIP` → situs
  - `Sale_Date`, `Sale_Date_String`, `Sale_Price`, `VALID_SALE_CODE` → lastSale
  - `Mkt_Value`, `Assd_Value`, `Land_Value`, `Bldg_Value`, `Defer_Value` → tax
  - `LAND_USE_CODE`, `Land_Desc`, `Bldg_Use_Desc`, `Occupancy_Desc` → land-use hints
  - `Township`, `Tax_Codes`, `Map`, `LegalRef_*` → other
- **WKID / CRS:** 102719 (latest 2264)
- **Verified:** yes — count **53,187**; `Calc_Acres BETWEEN 5 AND 150` → **7,115**; sample `ALPHA=7688-23-9094` CATALOOCHEE RANCH PROPERTIES LLC centroid ≈ **-83.09, 35.56** (Haywood); join `parno` OneMap OK
- **Notes:** PRIMARY wire-first (count aligns with OneMap ~53,178). MaxRecordCount **1000** — paginate. Auth **none**. Prefer over Open_Data during software transition.

### 2. Land_Records/Open_Data Parcels — open-data CAMA mirror

- **Purpose:** parcels | tax | ownership | sales
- **REST URL:** https://maps.haywoodcountync.gov/arcgis/rest/services/Land_Records/Open_Data/MapServer/3
- **Same attrs as SmartGov** (+ `Addr_3`; no `ParcelZIP`)
- **Verified:** count **50,525**; acres 5–150 → **6,207**; `Sale_Price>0` → **28,814**; `Mkt_Value>0` → **49,975**; Bldg_Value 0/null in range → **2,579**
- **Notes:** MaxRecordCount **100000** — best bulk extract when count matches SmartGov. Hub: https://opendata-hayco.hub.arcgis.com/. Downloads: Parcels.zip.

### 3. Public_Access Parcels + ParcelWebMap5 Parcel — viewer mirrors

- **Public_Access/1:** https://maps.haywoodcountync.gov/arcgis/rest/services/Land_Records/Public_Access/MapServer/1 — count **51,290**
- **ParcelWebMap5/21:** https://maps.haywoodcountync.gov/arcgis/rest/services/Land_Records/ParcelWebMap5/MapServer/21 — count **50,525** (powers gisweb viewer)
- **Qualified_Sales/2 Parcels:** same CAMA schema; count **51,290**
- **Notes:** Viewer (`haywood.js`) identifies ParcelWebMap5 Parcel by `ALPHA`.

### 4. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='087'`
- **Key fields:** `parno`↔`ALPHA`, `ownname`, `mailadd`, `siteadd`, `gisacres`, `saledate`/`saledatetx`, `parval`/`landval`/`improvval`
- **Verified:** count **53,178**; `gisacres` 5–150 → **7,104**; `gisacres>0` → **53,148**; `parval>0` → **52,849**; `saledate IS NOT NULL` → **53,178**; join verified `parno='7688-23-9094'`
- **Notes:** No sale **price**. Prefer county `Calc_Acres` / CAMA for values. MaxRecordCount **5000**.

### 5. Zoning — municipal districts (cities-first PRIMARY)

- **REST URL:** https://maps.haywoodcountync.gov/arcgis/rest/services/Land_Records/Open_Data/MapServer/9
- **Mirrors:** Public_Access/MapServer/48; ParcelWebMap5/MapServer/11; Map2/MapServer/12
- **Fields:** `MAPNAME`, `ALPHA`, `ZONING`, `ZONING_DEF`
- **Verified:** total **140**
- **Cities-first routing by `MAPNAME` (normalized):**

| Municipality | MAPNAME pattern | Count | Notes |
|--------------|-----------------|------:|-------|
| **Waynesville** | `WAYZON.UC` (+ case variants) | **81** | County seat; district names are long text labels |
| **Maggie Valley** | `MAGGIEZO.GCH` | **32** | Codes C-1…C-3, MU-1/2/4, R-1…R-4 |
| **Canton** | `CANTON.GCH` | **15** | C-1/2/3, GB, GR, H1, H-BD, I-1/2, R-1/2, SF, EX, … |
| **Clyde** | `CLYDEZON.GCH` | **8** | C-1/2, O&I, R-1/R-1A/R-2 |
| (blank / overlay) | blank / Hazelwood RR Overlay | 4 | Thin; treat as Waynesville-adjacent overlay |

- **Join:** spatial join Zoning → parcels; route by municipality / ETJ (`Municipalities` ALPHA: `WAY CITY`/`WAY ETJ`, `CANTON CITY`/`CANTON ETJ`, `CLYDE CITY`/`CLYDE ETJ`, `MAGGIE CITY`).
- **Notes:** **Unincorporated Haywood has no county zoning polygons** on this service — honest gap (mountain county pattern). Prefer town PDFs for ordinance text; REST polygons are wire for map join.

### 6. Municipal Boundaries / Municipalities

- **Open_Data/5:** https://maps.haywoodcountync.gov/arcgis/rest/services/Land_Records/Open_Data/MapServer/5 — count **16**
- **Public_Access/42:** Municipal Boundaries — same `ALPHA` labels
- **Codes:** WAY CITY, WAY ETJ, CANTON CITY, CANTON ETJ, CLYDE CITY, CLYDE ETJ, MAGGIE CITY (+ EXEMPT stubs)

### 7. Qualified Sales points (sale history supplement)

- **REST URL:** https://maps.haywoodcountync.gov/arcgis/rest/services/Land_Records/Qualified_Sales/MapServer/0
- **Geometry:** Point
- **Fields:** `ParcelNumberFormatted`, `SalePrice`, `DeedDate`, assessed values, `MarketAcreage`, building attrs
- **Verified:** count **4,839** (sales 2018–2020 window)
- **Notes:** Supplement to parcel `Sale_*`; ParcelWebMap5 also has Parcel Sales 2019/2020 layers (22/23).

### 8. FLU — PDF only (no public FeatureServer)

- **Waynesville Land Use Map (2035 Comp Plan):** https://www.waynesvillenc.gov/sites/default/files/Lettersize_FLU_2020_07_14_ForPackage.pdf
- **Waynesville Comp Plan:** https://www.waynesvillenc.gov/sites/default/files/WaynesvilleCompPlan_11_11_2020_Rev_reduced.pdf
- **Canton Comp Plan / Zoning Updates:** https://www.cantonnc.com/build-a-better-canton-a-blueprint-for-recovery-renewal/
- **County / Maggie / Clyde:** no dedicated public FLU REST verified
- **Notes:** Parcel `LAND_USE_CODE` is existing-use CAMA — **not** future land use.

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS REST? | FLU REST? | Notes |
|--------------|---------------|------:|:-------------:|:---------:|-------|
| **Waynesville** | Open_Data Zoning `WAYZON.UC` | 81 | No (county host) | **PDF** | Seat; Official Zoning Map PDF Feb 2026 |
| **Maggie Valley** | Open_Data Zoning `MAGGIEZO.GCH` | 32 | No | No | Defers to county GIS |
| **Canton** | Open_Data Zoning `CANTON.GCH` | 15 | No | Comp Plan page | Post-Helene recovery plan |
| **Clyde** | Open_Data Zoning `CLYDEZON.GCH` | 8 | No | No | |
| Unincorporated | *(none)* | — | County | No | **Unzoned** on public REST |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| Appraisal card PDF (preferred) | `https://taxes.haywoodcountync.gov/ITSPublic/AppraisalCard.aspx?id={ALPHA_NO_DASHES}` |
| Encoding | Strip hyphens from `ALPHA` (`7688-23-9094` → `7688239094`) |
| Spatialest property | `https://community.spatialest.com/nc/haywood/#/property/{ALPHA}` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/haywood/parcel-detail/{ALPHA}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/haywood/parcel-search |
| Tax Bill Search | https://taxes.haywoodcountync.gov/ITSPublic/TaxBillSearch |
| Jurisdiction GIS | https://maps.haywoodcountync.gov/gisweb/default.htm |

Verified AppraisalCard PDF for id `7688239094`: owner **CATALOOCHEE RANCH PROPERTIES LLC**, PIN `7688-23-9094`, sale 03/30/2020 @ $2,644,000, land appraised $163,400.

## Gaps / caveats

- **Unincorporated zoning REST gap** — only municipal zoning polygons published
- **FLU REST gap** — Waynesville/Canton PDF/plan only; no county or town FLU FeatureServer
- Open_Data parcel count (~50.5k) lags SmartGov/OneMap (~53.2k) during Land Records software transition — prefer SmartGov for completeness; Open_Data for high MaxRecordCount extract when synced
- Spatialest `#/property/{ALPHA}` is SPA deep-link (shell loads; search UI also works)
- ITSForPublic CAMA login is separate (credentials posted on county Public Tax System Access page) — prefer AppraisalCard PDF deep-link (no login)
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Haywood County Land Records / GIS. Maps compiled from recorded deeds/plats/public records; consult primary sources; not survey quality; County disclaims warranties (see maps.haywoodcountync.gov terms). Commercial resale subject to **NCGS 132-10**. Attribute Haywood County GIS (and Town of Waynesville / Canton / Maggie Valley / Clyde where municipal PDFs used).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 12+
- **tranche:** 3 (tax/sale/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- Live `returnCountOnly` + sample attribute/geo queries against SmartGov, Open_Data Parcels/Zoning/Municipalities, Public_Access, ParcelWebMap5, Qualified_Sales, NC OneMap `cntyfips='087'`; AppraisalCard PDF cross-check; haywood.js viewer wiring; centroid geo-check in Haywood.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://maps.haywoodcountync.gov/arcgis/rest/services/SmartGov/SmartGovTaxView/FeatureServer/0 · id `ALPHA` · live count **51,574** · 5–150 ac **5,765** (`Calc_Acres >= 5 AND Calc_Acres <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='HAYWOOD'` gives **344** stations (305 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27HAYWOOD%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Haywood'` gives **343** stations (45 with AADT_2025, 278 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Haywood%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `Mkt_Value` non-zero **44,838**, `Assd_Value` non-zero **44,838**
- **Sale history (ok):** price `Sale_Price` >0 **26,040**; date `Sale_Date` non-null **45,326**
- **Owner entity:** fields `Owner_1`, `Owner_2`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **748** (all parcels: 5,369), using the SQL approximation on `Owner_1`.
- **PA deep link:** `https://taxes.haywoodcountync.gov/ITSPublic/AppraisalCard.aspx?id={ALPHA}`. Tested `7695442942` → HTTP **200** (application/pdf), content verified: True. Owner and parcel id verified in the response.
- **Jurisdiction GIS viewer:** https://maps.haywoodcountync.gov/gisweb/default.htm → HTTP **200** (Haywood County GIS)
- **Pass 2 gaps:** none
