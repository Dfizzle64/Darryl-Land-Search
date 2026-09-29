# Mitchell County, NC — GIS County Card

## Summary

Mitchell County (Asheville shed, FIPS **37121**, slug **mitchell**, `cntyfips='121'`) publishes public ArcGIS REST at **`mapping.mitchellcountync.gov`**. **Wire-first parcels + CAMA (TRANCHE-3):** **WebMapNew/MapServer/12 Parcels** — ~**17,664** polys with `PIN`/`GISPIN`/`LRSN`/`TaxAcct`, `Owner1`/`Owner2`, mailing + situs, `LegalAc`/`StatedArea`, tax **`Land`/`Dwelling`/`Total`**, deed `Deed_Date`/`DeedBook`/`DeedPage` (**no sale price on primary parcels**). `LegalAc` 5–150 → **~4,221**; vacant (Dwelling 0/null) in-range → **~1,844**. **Sale price:** partial **WebMap/18 Sales** (`sale_price`/`sale_date`, ~**397**, ~2021 window only) — join by `PIN`; else PA. **Cities-first zoning:** **Town of Spruce Pine** — prefer HCCOG **`Spruce_Pine_Zoning`** `ZoneCode`/`ZoneDesc` (**244**); county host twin **WebMapNew/8** `Zoning_11` (**242**); Energov **Zoning/3** coarse (**13**). County states **no zoning outside Spruce Pine** — **Bakersville** limits only (**zoning REST gap / unzoned**). **FLU:** Spruce Pine 2023 Comprehensive Land Use Plan referenced on town site — **no FLU FeatureServer** (PDF/page gap). **PA deep-link:** NCPTS `https://lrcpwa.ncptscloud.com/mitchell/parcel-detail/{GISPIN}` (+ esearch / publicaccessnow search). **Jurisdiction GIS:** https://mapping.mitchellcountync.gov/maps/. **NC OneMap** `cntyfips='121'` geometry/owner/tax fallback (no sale price; `saledate` null). Markets: **[Asheville]**.

## Portals

- **Jurisdiction GIS (Avineon maps)** — https://mapping.mitchellcountync.gov/maps/
- **County ArcGIS REST** — https://mapping.mitchellcountync.gov/arcgis/rest/services
- **WebMapNew (primary operational)** — https://mapping.mitchellcountync.gov/arcgis/rest/services/WebMapNew/MapServer
- **Mapping / Land Records** — https://www.mitchellcountync.gov/departments/mapping-land-records/
- **Tax Assessor** — https://www.mitchellcountync.gov/departments/tax-assessor/
- **NCPTS PA deep-link (preferred)** — `https://lrcpwa.ncptscloud.com/mitchell/parcel-detail/{GISPIN}`
- **NCPTS search** — https://lrcpwa.ncptscloud.com/mitchell/parcel-search
- **Mitchell Tax Property Search (BIS esearch)** — https://esearch.mitchellcounty.tax/
- **Aumentum / publicaccessnow Property Search** — https://nc-mitchell.publicaccessnow.com/Assessor/PropertySearch.aspx
- **Town of Spruce Pine** — https://www.sprucepine-nc.gov/
- **Spruce Pine Building, Planning & Zoning** — https://www.sprucepine-nc.gov/buildingplanningzoning
- **Spruce Pine Municipal Data Viewer (HCCOG)** — https://hccog.maps.arcgis.com/apps/instant/sidebar/index.html?appid=c1b54e0fc019490d9d89b7f04b7ca6ec
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='121'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `GISPIN` / `PIN`; `LRSN`; `TaxAcct`; OneMap `parno` | Prefer trimmed **GISPIN** (`####-##-##-####`) for PA/OneMap |
| polygons | Yes | WebMapNew/12; OneMap/1 | CRS **102719 / 2264** |
| acreage | Yes | `LegalAc`; `StatedArea`; OneMap `gisacres` | LegalAc 5–150 → **4221**; OneMap 5–150 → **3853** |
| ownerName | Yes | `Owner1`/`Owner2`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `MailAddr`/`MailCity`/`MailState`/`MailZip` | |
| situs address | Yes | `LocAddr`/`LocCity`/`LocState`; OneMap `siteadd`; Addresses/1 | LocCity often blank/padded |
| lastSale date/price | Partial | `Deed_Date` (date); WebMap Sales `sale_price`/`sale_date` (~397); PA | **Sale price countywide REST gap** outside Sales layer |
| tax values | Yes | `Land`, `Dwelling`, `Total`; OneMap `parval`/`landval`/`improvval` | Total>0 → **~17,621** |
| zoning | Yes (cities-first) | HCCOG `ZoneCode`; county `Zoning_11` | Unincorp + Bakersville **unzoned** per county |
| flu | Gap | Spruce Pine Comp Land Use Plan (2023) page refs | No FLU FeatureServer |
| appraiser / viewer link | Yes | NCPTS `{GISPIN}`; esearch; maps GIS | TRANCHE-3 |

### CorpId → municipality hint (parcel tax corp; verify spatially)

| CorpId | Approx parcels | Jurisdiction | Zoning source (prefer) |
|--------|----------------|--------------|------------------------|
| 03 | **~1,381** | Town of Spruce Pine | **HCCOG Spruce_Pine_Zoning** (+ county WebMapNew/8) |
| 02 | **~274** | Town of Bakersville (seat) | **Unzoned** — limits only; no zoning REST |
| 01 | **~15,493** | Unincorporated Mitchell | Unzoned (county policy) |
| blank/other | ~small | — | Spatial-check City Limits |

## Layers (verified 2026-09-24)

### 1. WebMapNew Parcels — parcels + ownership + tax + deed date (PRIMARY CAMA)

- **Purpose:** parcels | tax | ownership | sales (date via deed)
- **REST URL:** https://mapping.mitchellcountync.gov/arcgis/rest/services/WebMapNew/MapServer/12
- **Layer name / id:** Parcels / 12
- **Geometry:** Polygon
- **Key fields → targets:**
  - `GISPIN`, `PIN`, `Name` → parcelId (trim trailing spaces on `PIN`)
  - `LRSN` → parcelIdAlt / internal
  - `TaxAcct` → parcelIdAccount (esearch Property ID)
  - `LegalAc`, `StatedArea` → acreage
  - `Owner1`, `Owner2` → ownerName
  - `MailAddr`, `MailCity`, `MailState`, `MailZip` → mailing
  - `LocAddr`, `LocCity`, `LocState` → situs
  - `Deed_Date`, `DeedBook`, `DeedPage`, `Deed_Ref`, `Grantor` → lastSale.date / deed
  - `Land`, `Dwelling`, `Total` → tax.market split / total
  - `PropClas`, `Neighborhood`, `JurNum`, `CorpId`, `DistNum` → class / routing hints
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **17,664**; `LegalAc BETWEEN 5 AND 150` → **4,221**; `Total>0` → **17,621**; `Land>0` → **17,619**; `Deed_Date IS NOT NULL` → **17,352**; `Owner1 IS NOT NULL` → **17,634**; vacant in 5–150 → **1,844**; sample `GISPIN=0856-00-20-1077` HOPSON JACK Total **492600** centroid ≈ **-82.21, 36.07** (Mitchell)
- **Notes:** **PRIMARY** wire-first. MapServer (also mirrored on WebMapNew2023/12, EnergovWebMap2/1, WebMap/24 — same CAMA family). MaxRecordCount **1000** — paginate. Auth **none**. No `SalePrice` on this layer — use Sales/18 join or PA for price.

### 2. WebMap Sales — partial sale price overlay

- **REST URL:** https://mapping.mitchellcountync.gov/arcgis/rest/services/WebMap/MapServer/18
- **Fields:** `PIN`, `sale_date`, `sale_price` (string e.g. `$100,000.00`)
- **Verified:** count **397**; date window ~**2021-02 → 2021-12** (epoch min/max)
- **Notes:** **Partial** — not countywide current sales. Join trim(`PIN`)↔`GISPIN`. Prefer for price when present; else PA.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='121'`
- **Fields:** `parno`↔`GISPIN`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`, `gisacres`, `parval`/`landval`/`improvval`, `saledate`/`saledatetx` (empty/weak), `sourceref`
- **Verified:** count **17,671**; `gisacres` 5–150 → **3,853**; `parval>0` → **17,496**; `landval>0` → **17,494**; `improvval>0` → **9,318**; `saledate IS NOT NULL` → **0**; join `parno='0856-00-20-1077'`
- **Notes:** Strong tax/owner mirror. No sale price. Prefer county `LegalAc` when present. MaxRecordCount **5000**.

### 4. HCCOG Spruce_Pine_Zoning — cities-first PRIMARY (Spruce Pine)

- **Purpose:** zoning (city-first)
- **REST URL:** https://services1.arcgis.com/vj28eVZMB2OMIUh5/arcgis/rest/services/Spruce_Pine_Zoning/FeatureServer/0
- **Fields:** `ZoneCode`, `ZoneDesc`, `RezoningDate`, `PreviousZone`, `AnnexationDate`, `AONumber`
- **Verified:** count **244**
- **ZoneCode (top):** R-2 (61), C-3 (58), R-1 (38), C-1 (20), C-1A (16), I (12), C-2 (11), R-3 (11), M-1 (7), I-1 (4), I-2 (2), Not Zoned (2), PS-1 (1), T-1 (1)
- **Notes:** Prefer HCCOG (has `ZoneDesc`) inside Spruce Pine. Town Instant app + Building/Planning/Zoning page. Spatial join → parcels; route by City Limits `CityName='Spruce Pine'` or CorpId≈03.

### 5. WebMapNew Spruce Pine Zoning — county host twin

- **REST URL:** https://mapping.mitchellcountync.gov/arcgis/rest/services/WebMapNew/MapServer/8
- **Also:** WebMap/20, WebMapNew2023/8
- **Fields:** `Zoning_11`, `ACREAGE`
- **Verified:** count **242**
- **Notes:** Same districts as HCCOG without descriptions. Use when staying on county host.

### 6. EnergovWebMap2 Zoning — coarse district polys

- **REST URL:** https://mapping.mitchellcountync.gov/arcgis/rest/services/EnergovWebMap2/MapServer/3
- **Fields:** `ZONE_CODE`
- **Verified:** count **13** (one poly per code family)
- **Notes:** Coarse — prefer HCCOG / WebMapNew/8 for parcel joins.

### 7. City Limits — municipal routing

- **REST URL:** https://mapping.mitchellcountync.gov/arcgis/rest/services/WebMapNew/MapServer/7
- **Fields:** `CityName`, `AnnexName`, `DateAnnexed`
- **Verified:** count **3** — **Bakersville**, **Spruce Pine**, plus tiny unnamed annex stub
- **HCCOG twin:** https://services1.arcgis.com/vj28eVZMB2OMIUh5/arcgis/rest/services/Spruce_Pine_Town_Limits/FeatureServer/0 (count **1**)

### 8. Addresses — situs supplement

- **REST URL:** https://mapping.mitchellcountync.gov/arcgis/rest/services/WebMapNew/MapServer/1
- **Fields:** `FullAddress`, `Add_Number`, `MSAGComm`, …
- **Verified:** count **11,582**
- **Notes:** No PIN — spatial join; prefer OneMap `siteadd` when joining by `parno`.

### 9. HCCOG Mitchell_County_Parcels — Spruce Pine–area extract (secondary)

- **REST URL:** https://services1.arcgis.com/vj28eVZMB2OMIUh5/arcgis/rest/services/Mitchell_County_Parcels/FeatureServer/0
- **Verified:** count **4,557** (not countywide)
- **Notes:** OneMap-schema extract for Instant app — **do not prefer** over WebMapNew/12 for countywide CAMA.

### 10. FLU — PDF / page gap (no public FeatureServer)

- Spruce Pine Building, Planning & Zoning references Comprehensive Land Use Plan / Zoning Ordinance rewrite (HCCOG-supported) — https://www.sprucepine-nc.gov/buildingplanningzoning
- County Mapping FAQ: **no zoning outside Spruce Pine** — no county FLU REST
- No FLU FeatureServer verified (county or HCCOG)

## Municipalities (cities-first)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| **Spruce Pine** | **HCCOG Spruce_Pine_Zoning** (prefer) + WebMapNew/8 | 244 / 242 | **Yes** — sprucepine-nc.gov + HCCOG Instant | No — Comp Plan page gap | Cities-first PRIMARY; CorpId≈03 |
| **Bakersville** | — | — | County seat; no town GIS found | No | City Limits only; **zoning REST gap / unzoned** (county FAQ) |
| Unincorporated Mitchell | — | — | County maps | No | **Unzoned** outside Spruce Pine per Mapping/Land Records |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| NCPTS parcel detail (preferred PA) | `https://lrcpwa.ncptscloud.com/mitchell/parcel-detail/{GISPIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/mitchell/parcel-search |
| BIS esearch (Geographic ID / Property ID) | https://esearch.mitchellcounty.tax/ — Geographic ID=`{GISPIN}`; Property ID=`{TaxAcct}` |
| publicaccessnow Property Search | https://nc-mitchell.publicaccessnow.com/Assessor/PropertySearch.aspx (Parcel ID with dashes) |
| Jurisdiction GIS | https://mapping.mitchellcountync.gov/maps/ |
| Spruce Pine municipal viewer | https://hccog.maps.arcgis.com/apps/instant/sidebar/index.html?appid=c1b54e0fc019490d9d89b7f04b7ca6ec |

PIN encoding: use trimmed `GISPIN` / `PIN` as `####-##-##-####` (e.g. `0856-00-20-1077`). **Do not use** `bttaxpayerportal.com/ITSPublicMT` — HTML branding resolves to Martin County; empty AppraisalCard shells.

## Gaps / caveats

- **Sale price** not on primary Parcels REST — only partial WebMap Sales (~397, ~2021); use PA for current price QA
- **Bakersville + unincorporated zoning** — none on public REST (county policy: zoning only in Spruce Pine)
- **FLU FeatureServer gap** — Spruce Pine Comp Land Use Plan referenced; no downloadable FLU layer verified
- OneMap `saledate` empty for Mitchell — use county `Deed_Date` or Sales `sale_date`
- `PIN` field is space-padded — trim before joins; prefer `GISPIN`
- LocCity often blank — compose situs carefully; OneMap `siteadd` helps
- MapServer MaxRecordCount 1000 — paginate
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Mitchell County Mapping/Land Records / Tax Assessor (Avineon GIS); Town of Spruce Pine / High Country Council of Governments (HCCOG) for municipal zoning viewer; NC OneMap. Data for tax/reference — not a survey. Commercial resale subject to **NCGS 132-10**. Attribute Mitchell County GIS (+ Town of Spruce Pine / HCCOG where municipal sources used).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 10+
- **tranche:** 3 (tax/owner public on parcels; sale date on Deed_Date + partial sale price Sales/18; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + cities-first zoning suite; FLU/Bakersville/unzoned gaps documented)
- Live `returnCountOnly` + sample attribute/geo queries against WebMapNew Parcels/12, Sales/18, Spruce Pine Zoning/8, Energov Zoning/3, City Limits/7, Addresses/1, HCCOG Spruce_Pine_Zoning + Town_Limits + Mitchell_County_Parcels extract, NC OneMap `cntyfips='121'`; NCPTS/esearch/publicaccessnow portal checks; centroid geo-check in Mitchell.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://mapping.mitchellcountync.gov/arcgis/rest/services/WebMapNew/MapServer/12 · id `GISPIN` · live count **17,664** · 5–150 ac **4,221** (`LegalAc >= 5 AND LegalAc <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='MITCHELL'` gives **123** stations (78 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27MITCHELL%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Mitchell'` gives **121** stations (37 with AADT_2025, 76 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Mitchell%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `Total` non-zero **17,621**, `Land` non-zero **17,619**
- **Sale history (partial):** price not on REST; date `Deed_Date` non-null **17,352**. Price not on REST; NCPTS Mitchell parcel-detail page is the public source.
- **Owner entity:** fields `Owner1`, `Owner2`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **753** (all parcels: 3,391), using the SQL approximation on `Owner1`.
- **PA deep link:** `https://lrcpwa.ncptscloud.com/mitchell/parcel-detail/{GISPIN}`. Tested `0856-00-20-0431` → HTTP **200** (text/html), content verified: False. NCPTS SPA shell (200, 496 B, client-rendered): parcel content cannot be checked server-side.
- **Jurisdiction GIS viewer:** https://mapping.mitchellcountync.gov/maps/ → HTTP **200** (Avineon Web Map Template)
- **Pass 2 gaps:** sale partial
