# Cabarrus County, NC — GIS County Card

## Summary

Cabarrus County (Charlotte MSA, FIPS **37025**) publishes rich **public** ArcGIS REST at `location.cabarruscounty.us`: countywide **tax parcel polygons** with ownership, mailing, assessed/market values, last-sale year/month/price, and GIS acreage on `OpenData/Tax_Parcels` (and mirrors on `landrecords_view`, `DataExplorerSearch`, `AA`). **Situs is not on the primary parcel polygon layer** — join address points (`AA/ParcelAddresses` or Map Cabarrus property join) by `PIN`/`PIN14`. **Zoning is city-first** (county unincorporated + Concord, Kannapolis, Harrisburg, Midland, Mount Pleasant, Locust). **FLU** is public for **Concord 2030 Land Use Plan** (AGOL Geocortex) and Kannapolis **Character Areas**; other towns lack public FLU REST. **NC OneMap** (`cntyfips='025'`) is a solid fallback with situs + values. Main gaps: no situs on primary parcels; no countywide FLU; zoning split across municipalities (spatial join); legacy `Tax_Parcels_Full` service **not started**.

## Portals

- **Map Cabarrus** — https://location.cabarruscounty.us/mapcabarrus/ — Interactive parcels/zoning. Search by address, owner, or parcel/PIN.
- **Open Data (ArcGIS Hub)** — https://gis-cabarrus.opendata.arcgis.com/ — Downloadable parcels, zoning, addresses.
- **data.cabarruscounty.us** — https://data.cabarruscounty.us/
- **County ArcGIS REST** — https://location.cabarruscounty.us/arcgisservices/rest/services
- **County ArcGIS Host** — https://location.cabarruscounty.us/arcgishost/rest/services — Map Cabarrus joins, HarrisburgParcels, AA Accela layers.
- **Tax Real Estate Search** — https://tax.cabarruscounty.us/RealEstate.aspx — Also Basic Search / Sales Search.
- **CLaRIS (Land Records)** — https://claris.cabarruscounty.us/ — PIN / Real ID / owner / address search; links to Map Cabarrus & appraisal cards.
- **City of Concord GIS / Planning maps** — https://concordnc.gov/Departments/Planning-Development-Services/GIS — VertiGIS/Geocortex apps; AGOL org `0esqB0FgvL32hAbY`.
- **Concord maps2 REST** — https://maps2.concordnc.gov/server/rest/services
- **City of Kannapolis GIS REST** — https://maps.kannapolisnc.gov/arcgis/rest/services
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`).

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN14`, `PIN`, `PARCEL`, `PropertyReal_ID`; OneMap `parno` | Prefer `PIN14` (14-digit); strip `.00000000` from `PIN` |
| polygons | Yes | OpenData Tax_Parcels /1 | County CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALCULATED_ACREAGE`, `LandUnits`+`UnitsType`=`AC` | ~**7,144** parcels with GIS acres 5–150; ~**7,351** with LandUnits AC 5–150 |
| ownerName | Yes | `AcctName1`+`AcctName2` / OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `MailAddr1`–`3`,`MailCity`,`MailState`,`MailZipCode` | |
| situs address | Yes (join) | Address `Full_con_cat` / `addressnum`+`road_*`+`City`+`Zip`; OneMap `siteadd` | **Not** on Tax_Parcels polygons — join by PIN |
| lastSale date/price | Yes | `SaleYear`+`SaleMonth`,`SalePrice`,`QualifiedCode` | Compose date from year/month; filter `QualifiedCode` for comps |
| tax values | Yes | `MarketValue`,`AssessedValue`,`LandValue`,`BuildingValue`,`ObxfValue` | Often **strings** on OpenData MapServer; doubles on DataExplorer/WebParcels |
| zoning | Yes (split) | Per-muni `ZONINGCODE`; MapCabarrus join `zoningcode` | Spatial join preferred; see Municipalities |
| flu | Yes (partial) | Concord `Category`/`Code`; Kannapolis `Char_Dist`/`LabelName` | Concord + Kannapolis only on public REST |
| appraiser / viewer link | Yes | Map Cabarrus + tax + CLaRIS | Templates below |

## Layers (verified)

### 1. OpenData/Tax_Parcels — parcels + ownership + tax + last sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last)
- **REST URL:** https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/Tax_Parcels/MapServer/1
- **Alternate (same schema):** https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/Tax_Parcel/MapServer/0
- **Layer name / id:** Tax Parcels / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN14`, `PIN`, `PARCEL` → parcelId
  - `PropertyReal_ID` → TMP / Real ID style
  - `CALCULATED_ACREAGE`, `LandUnits`, `UnitsType` → acreage (`AC`|`LT`|`FF`|`UT`)
  - `AcctName1`, `AcctName2` → ownerName
  - `MailAddr1`, `MailAddr2`, `MailAddr3`, `MailCity`, `MailState`, `MailZipCode` → mailing
  - `SaleYear`, `SaleMonth`, `SalePrice`, `QualifiedCode` → lastSale
  - `MarketValue`, `AssessedValue`, `LandValue`, `BuildingValue`, `ObxfValue` → tax
  - `VacantOrImproved` (`V`|`I`), `DeedBook`/`DeedPage`, `LegalDesc` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **107,662**; `CALCULATED_ACREAGE BETWEEN 5 AND 150` → **7,144**; sample owner/tax/sale attrs OK
- **Notes:** **PRIMARY** wire-first. No situs, no zoning. Filter null/`0.00000000` PIN stubs. MaxRecordCount **2000**. Prefer `UnitsType='AC'` when using `LandUnits`. Value fields are strings on this host — cast to number.

### 2. views/landrecords_view Parcels + PIN Tax View — Map Cabarrus backend mirrors

- **Purpose:** parcels | tax | ownership | sales
- **REST URLs:**
  - https://location.cabarruscounty.us/arcgisservices/rest/services/views/landrecords_view/MapServer/4 (Parcels)
  - https://location.cabarruscounty.us/arcgisservices/rest/services/views/landrecords_view/MapServer/3 (PIN Tax View - Owner)
- **Geometry:** Polygon
- **Verified:** yes — both count **107,662**; same field family as OpenData Tax_Parcels
- **Notes:** MaxRecordCount **1000**. Prefer OpenData/Tax_Parcels for higher page size.

### 3. DataExplorerSearch/WebParcels — numeric tax values

- **Purpose:** parcels | tax | ownership
- **REST URL:** https://location.cabarruscounty.us/arcgisservices/rest/services/DataExplorerSearch/FeatureServer/2
- **Layer name / id:** WebParcels / 2
- **Geometry:** Polygon
- **Key fields:** Same ownership/mail/tax names; `MarketValue`/`AssessedValue`/etc. are **doubles** (cleaner than OpenData strings). **No sale fields** on this layer.
- **Verified:** yes — count **107,662**
- **Notes:** Good for typed tax values; still no situs/zoning/sale.

### 4. AA/ParcelAddresses — situs + CAMA join (PRIMARY situs)

- **Purpose:** other (situs) | tax | ownership (point)
- **REST URL:** https://location.cabarruscounty.us/arcgishost/rest/services/AA/MapServer/1
- **Alternate:** OpenData Addresses (points, no PIN) https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/Addresses/MapServer/0
- **Layer name / id:** ParcelAddresses / 1
- **Geometry:** Point
- **Key fields → targets:**
  - `PIN`, `PIN14` → join to Tax_Parcels
  - `Full_con_cat` / `FullHouse`+`FullStreetName` / `addressnum`+`road_pre`+`road_name`+`road_type`+`road_suf` → situsAddress
  - `City`, `Zip`, `State` → situsCity / situsZip
  - Also carries CAMA mail/tax fields (often sparse on sample points)
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — metadata + sample `Full_con_cat` returned; OpenData Addresses count **125,593**
- **Notes:** Many-to-one (multiple addresses per parcel). Pick primary / lowest unit or concatenate carefully. Do **not** use `InspContactInfo` / phone-like fields.

### 5. MapCabarrusPropertyData12_NEW — parcel∩address∩zoning join (convenience)

- **Purpose:** parcels | zoning | other (situs)
- **REST URL:** https://location.cabarruscounty.us/arcgishost/rest/services/Hosted/MapCabarrusPropertyData12_NEW/FeatureServer/0
- **Alternate:** https://location.cabarruscounty.us/arcgishost/rest/services/Hosted/Map_Cabarrus/FeatureServer/0
- **Geometry:** Polygon (explode on multi-address joins)
- **Key fields → targets:** `pin14` → parcelId; `acctname1` → owner; `mailaddr*` → mailing; `landunits`/`unitstype` → acreage; `saleyear`/`saleprice` → lastSale; `marketvalue`/`landvalue`/`buildingvalue` → tax; `zoningcode` → zoning; `full_con_cat` → situs
- **Verified:** yes — count **163,395** (address-inflated); non-empty `zoningcode` **154,682**; non-null `full_con_cat` **99,589**
- **Notes:** Convenient single table but **not 1:1 with parcels**. Deduplicate by `pin14` for land search. Empty `zoningcode` still occurs — fall back to municipal zoning polygons. Do not harvest phone fields if present on related joins.

### 6. County + municipal zoning (county host) — Zoning MapServer

- **Purpose:** zoning
- **REST URL:** https://location.cabarruscounty.us/arcgisservices/rest/services/Zoning/MapServer
- **OpenData mirrors:** `OpenData/Cabarrus_County_Zoning`, `OpenData/Zoning_By_Municipalities`
- **WKID / CRS:** 102719 / 2264
- **Join to parcels:** **spatial join** (intersect/centroid) in 2264. Optionally filter parcels by `MunicipalDistrict.DISTRICT` first.
- **Verified layers:**

| Layer | URL | Count | Zoning field |
|-------|-----|-------|--------------|
| Cabarrus County Zoning | Zoning/MapServer/7 or OpenData/Cabarrus_County_Zoning/0 | **295** | `ZONINGCODE`, `ZONING_GEN`, `District`/`Intent` (joined desc) |
| Concord Zoning | Zoning/MapServer/6 or Zoning_By_Municipalities/0 | **826** | `ZONINGCODE`, `OLDZONING`, `ETJ` |
| Kannapolis Zoning | Zoning/MapServer/4 or Zoning_By_Municipalities/3 | **1,837** | `ZONINGCODE`, `BASE_DISTR` |
| Harrisburg Zoning | Zoning/MapServer/5 or Zoning_By_Municipalities/2 | **193** | `ZONINGCODE` |
| Midland Zoning | Zoning/MapServer/2 or Zoning_By_Municipalities/5 | **110** | `ZONINGCODE`, `Zoning_Typ` |
| Mt Pleasant Zoning | Zoning/MapServer/1 or Zoning_By_Municipalities/6 | **174** | `ZONINGCODE` |
| Locust Zoning | Zoning/MapServer/3 or Zoning_By_Municipalities/4 | **8** | `ZONINGCODE`, `ZONING` |

- **Notes:** County layer = **unincorporated**. Cities/towns are first-class — never assume county zoning alone covers Concord/Kannapolis/etc. `landrecords_view` layers 20–26 duplicate these with simpler field names.

### 7. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parno` → parcelId (samples align with `PIN14`)
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs
  - `gisacres` → acreage (~**7,516** in 5–150)
  - `saledate`,`saledatetx` → lastSale.date (**no sale price**)
  - `parval`,`landval`,`improvval` → tax
  - `cntyfips`=`025`, `cntyname` → Cabarrus filter
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — filter count **110,009**; sample features with owner/mail/values
- **Notes:** Best situs-on-polygon fallback. May lag county CAMA. MaxRecordCount **5000**. Filter empty `parno`/`ownname` stubs.

### 8. MunicipalDistrict — jurisdiction polygons

- **Purpose:** other (municipality filter)
- **REST URL:** https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/MunicipalDistrict/MapServer/0
- **Field:** `DISTRICT` — verified values include CITY OF CONCORD, CITY OF KANNAPOLIS, CITY OF LOCUST, TOWN OF HARRISBURG, TOWN OF MIDLAND, TOWN OF MOUNT PLEASANT, TOWN OF HUNTERSVILLE (edge)
- **Verified:** yes — sample attributes returned
- **Notes:** Use to route which zoning/FLU layer to spatial-join.

## Municipalities (first-class)

County parcels are countywide; **zoning and FLU are municipal**. Join pattern: start from county Tax_Parcels (2264) → spatial join the matching city zoning (and FLU when available). Concord city-hosted layers use **103122 / 6543** (NAD 1983 **2011** StatePlane NC ft) or **3857** — reproject before overlay with county 2264.

### City of Concord

- **Zoning (city AGOL, preferred for Concord):** https://services2.arcgis.com/0esqB0FgvL32hAbY/arcgis/rest/services/GeocortexZoningStaff_WFL1/FeatureServer/60 — `ZONINGCODE`, `ETJ`, `OLDZONING`; count **828**; CRS **103122 / 6543**
- **Zoning (AGOL Web Mercator):** https://services2.arcgis.com/0esqB0FgvL32hAbY/arcgis/rest/services/Zoning/FeatureServer/10 — count **814**; CRS **3857**
- **Zoning (county host mirror):** Zoning/MapServer/6 — count **826**; CRS **2264** (easiest join to county parcels)
- **FLU — Land Use Plan 2030:** https://services2.arcgis.com/0esqB0FgvL32hAbY/arcgis/rest/services/GeocortexZoningStaff_WFL1/FeatureServer/63 — fields `Code`,`Category`,`ApplicableZoning`; count **307**; CRS **6543**. Categories include Suburban Neighborhood, Urban Neighborhood, Village Center, Mixed-Use Activity Center, Industrial-Employment, Commercial, Civic-Institutional, Rural, Open Space, Amusements - Motor Sports.
- **FLU legacy 2015:** same service layer **64** — `LANDUSE`; count **155**
- **City parcels (optional):** GeocortexZoningStaff_WFL1/FeatureServer/9 — count **100,901**; CRS **6543**; rich CAMA-like fields (`PIN`,`AcctName_concat`, sale, values). Prefer county Tax_Parcels for countywide consistency; use city layer only inside Concord.
- **Join note:** city-only zoning/FLU + **county parcels** — spatial join in a common CRS (reproject 6543↔2264). Join key if attribute-joining city parcels: `PIN` / `PINDash` ↔ county `PIN`/`PIN14`.

### City of Kannapolis (Cabarrus + Rowan)

- **Official zoning (city host):** https://maps.kannapolisnc.gov/arcgis/rest/services/Official_City_Zoning/MapServer/0 — `ZONINGCODE`,`newzoning`,`RezoneCase`,`Link`; count **1,735**; CRS **102719 / 2264**
- **Zoning (county host mirror):** Zoning/MapServer/4 — count **1,837**; CRS **2264**
- **FLU / character areas:** https://services6.arcgis.com/U9SsvkRoA6RuruHj/arcgis/rest/services/CharacterUses/FeatureServer/0 — `Char_Dist`,`LabelName`; count **34**; CRS **2264** (Downtown Center, Cluster Residential, etc.)
- **Join note:** city zoning/Character Areas + county parcels (2264). Kannapolis also has land in **Rowan** — filter Cabarrus with county parcels / `cntyfips=025` / MunicipalDistrict.

### Town of Harrisburg

- **Zoning:** Zoning/MapServer/5 or OpenData Zoning_By_Municipalities/2 — `ZONINGCODE`; count **193**; CRS **2264**
- **Parcels subset (hosted):** https://location.cabarruscounty.us/arcgishost/rest/services/Hosted/HarrisburgParcels/FeatureServer/0 — count **11,280**; owner/mail/tax; **no sale fields**
- **FLU:** no public REST found (gap)
- **Join note:** town zoning + county Tax_Parcels (spatial, 2264)

### Town of Midland

- **Zoning:** Zoning/MapServer/2 — `ZONINGCODE`,`Zoning_Typ`; count **110**; CRS **2264**
- **FLU:** no public REST found (gap)
- **Join note:** town zoning + county parcels

### Town of Mount Pleasant

- **Zoning:** Zoning/MapServer/1 — `ZONINGCODE`; count **174**; CRS **2264**
- **FLU:** no public REST found (gap)
- **Join note:** town zoning + county parcels

### City of Locust (mostly Stanly; Cabarrus edge)

- **Zoning:** Zoning/MapServer/3 — `ZONINGCODE`; count **8**; CRS **2264**
- **FLU:** no public REST found (gap)
- **Join note:** tiny Cabarrus footprint — verify with MunicipalDistrict

## Gaps

- **Situs missing on primary Tax_Parcels polygons** — must join address points or use OneMap / MapCabarrus join (dedupe).
- **No countywide FLU FeatureServer** — Concord 2030 + Kannapolis Character Areas only; Harrisburg/Midland/Mt Pleasant/Locust FLU = gap or PDF plans only.
- **Zoning split by municipality** — must union/route layers; MapCabarrus `zoningcode` join is inflated/imperfect.
- **`Tax_Parcels_Full` MapServer not started** (HTTP 500) — use OpenData/Tax_Parcels.
- **Sale history** is last-sale only on parcels (year/month); no multi-transfer sales FeatureServer found on public REST.
- **Concord CRS mismatch** (6543/3857 vs county 2264) — transform before spatial join.
- **Owner phones/emails** not collected (do not scrape Map Cabarrus / CLaRIS PII beyond public REST fields).
- **MaxRecordCount** 1000–2000 on county layers; OneMap 5000 — paginate.
- **No paid vendor data** used (CoreLogic/Regrid/ATTOM avoided).

## Hand-off notes for Land Search Builder

1. **Wire first:** `OpenData/Tax_Parcels/MapServer/1` — polygons + owner, mailing, acreage, tax, last sale. Filter `CALCULATED_ACREAGE BETWEEN 5 AND 150` (~7.1k) or `UnitsType='AC' AND LandUnits BETWEEN 5 AND 150` (~7.4k). Exclude `PIN` null/`0.00000000`.
2. **Situs join:** `AA/MapServer/1` ParcelAddresses on `PIN14`/`PIN`, or OneMap `siteadd`, or deduped MapCabarrusPropertyData `full_con_cat`.
3. **Zoning:** spatial join municipal layer by jurisdiction (`MunicipalDistrict.DISTRICT` or situs city). Prefer county-host Zoning/MapServer/* for CRS match; Concord may use city Geocortex after reproject.
4. **FLU:** spatial join Concord Land Use Plan 2030 (layer 63) and Kannapolis CharacterUses; leave null elsewhere.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='025'`.
6. **Viewer / appraiser links:**
   - Map Cabarrus: `https://location.cabarruscounty.us/mapcabarrus/` (search PIN)
   - Tax search: `https://tax.cabarruscounty.us/BasicSearch.aspx` / `RealEstate.aspx`
   - CLaRIS: `https://claris.cabarruscounty.us/` (10-digit PIN)
7. **Join keys:** `PIN14` (preferred), cleaned `PIN` (10-digit), `PropertyReal_ID`, OneMap `parno`↔`PIN14`.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities are first-class:** never treat county zoning as countywide coverage.

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='CABARRUS'`, field `AADT_2022` (string) — **642 stations live**, 609 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CABARRUS%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CABARRUS%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Cabarrus'`, `AADT_2025` (int) — 636 stations; 30 with 2025, 595 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/Tax_Parcels/MapServer/1` — total 107661, 5–150 ac 7144 (`CALCULATED_ACREAGE>=5 AND CALCULATED_ACREAGE<=150`).
- Non-zero county: `LandValue` 98023, `BuildingValue` 83815, `MarketValue` 98211, `AssessedValue` 98211; in 5–150: `AssessedValue` 6791. **Status: ok.**
- LandValue/BuildingValue/MarketValue/AssessedValue are STRING integers (e.g. '13149960') — cast to number.

### 3. Sale history
- Price `SalePrice`>0 65422 (5–150: 3135); date non-null `SaleYear` 93246, `SaleMonth` 93246. **Status: ok.**
- No full sale date: SaleYear + SaleMonth integers only; SalePrice double (0 = non-arms-length/no price); QualifiedCode.

### 4. Owner entity
- Owner fields: `AcctName1`, `AcctName2`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 2082** (of 7106 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: **none (gap)**
- Tested `https://tax.cabarruscounty.us/BasicSearch.aspx` → **200**. GAP: no GET deep link. Tax site is ASP.NET WebForms; parcel search + Property Record Card only via postback (GET params ?PIN= ignored, tested). Use search page + PIN14 split into Sheet/Block/Parcel/Interest (e.g. 4589-46-8277-0000). CLaRIS https://claris.cabarruscounty.us/ (200) also search-only.

### 6. Jurisdiction GIS viewer
- `https://location.cabarruscounty.us/mapcabarrus/` → **200**. Map Cabarrus

### Pass2 gaps
- PA deep link: no GET URL with parcel id (search page only) — no GET deep link. Tax site is ASP.NET WebForms; parcel search + Property Record Card only via postback (GET params ?PIN= ignored, tested). Use search page + PIN
- Sale date is year+month only on parcel layer (no day)
- AADT_2022 blank at 33 of 642 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- No multi-transfer sale history on primary layer (last sale only)
