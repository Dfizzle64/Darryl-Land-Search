# Caswell County, NC — GIS County Card

## Summary

Caswell County (RDU / Greensboro shed, FIPS **37033**, slug **caswell**, `cntyfips='033'`) publishes public HandP **WebGIS** at **`www.webgis.net/nc/caswell/`** with ArcGIS REST **`NC/Caswell/MapServer`**. **Wire-first parcels + CAMA (TRANCHE-3):** layer **9 Parcels** — ~**17,222** polys with 12-digit `PIN`, 16-digit `Account`/`P_PIN` (PA + OneMap `parno`), owner (`N_NAME`/`N_NAME2`), mailing, situs (`AA_*`), `AV_ACRES`/`Calculated`/`P_DEEDED_A`, land/imp FMV (`AV_FMV_LAN`/`AV_FMV_IMP`), deed book/page. Acreage 5–150: **AV_ACRES → 5,921** (matches OneMap `gisacres`). **No sale price / sale date on public REST** (`P_YEAR` is tax-status year, not deed date). **Zoning is cities-first** (county Planning FAQ: only **Yanceyville**, **Milton**, and **Hyco Lake** are zoned): **City Zoning** `/21` (**125** — Yanceyville districts RR8/HB/RA/R12/OI/B1/M1/…); **Milton Zoning** `/22` (**11**); **Hyco Lake Zoning** `/10` (**16** RR/RB/IP). **Unincorporated remainder unzoned** (watershed overlays only). **FLU:** Caswell Comprehensive Plan / PTRC LDP **PDF** — no FLU FeatureServer. **PA deep-link:** `https://www.bttaxpayerportal.com/ITSPublicCS/AppraisalCard.aspx?id={P_PIN}` (WebGIS SiteCustom.js; verified PDF). **Jurisdiction GIS:** `https://www.webgis.net/nc/caswell/`. **NC OneMap** `cntyfips='033'` geometry/owner/tax fallback (`parno`=`Account`; `nparno`=`37033_{PIN}`; no sale). Markets: **[Raleigh-Durham, Greensboro]**.

## Portals

- **Jurisdiction GIS (WebGIS)** — https://www.webgis.net/nc/caswell/ (alias `/nc/Caswell/`)
- **County ArcGIS REST** — https://www.webgis.net/arcgis/rest/services/NC/Caswell/MapServer
- **County website** — https://www.caswellcountync.gov/
- **GIS department page** — https://www.caswellcountync.gov/department-directory/gis-website
- **Planning** — https://www.caswellcountync.gov/planning
- **Municode ordinances** — https://library.municode.com/nc/caswell_county/codes/code_of_ordinances
- **UDO (revised 2-17-25)** — https://www.caswellcountync.gov/_files/ugd/66d4ec_e209de7b0b19440ca9ed8f98c4028220.pdf
- **Comprehensive Plan PDF (FLU)** — https://www.caswellcountync.gov/_files/ugd/ddda14_ce9da4d25a0f4c6798ac6e05e25318e5.pdf
- **PTRC Caswell LDP site** — http://www.ptrc.org/caswellldp
- **Hyco Lake Zoning Map PDF** — https://www.caswellcountync.gov/_files/ugd/2463ad_0e4f0caa56ec4919976cbcfc5e0aa86f.pdf
- **Zoning FAQ** — https://www.caswellcountync.gov/_files/ugd/2463ad_44c722d353be40fd97db38e9af48a609.pdf
- **PA / AppraisalCard (ITSPublicCS)** — https://www.bttaxpayerportal.com/ITSPublicCS/ — Deep link: `https://www.bttaxpayerportal.com/ITSPublicCS/AppraisalCard.aspx?id={P_PIN}`
- **PA Basic Search** — https://www.bttaxpayerportal.com/ITSPublicCS/BasicSearch
- **Tax Bill Search** — https://www.bttaxpayerportal.com/ITSPublicCS/TaxBillSearch — also `/TaxBillSearch/Parcel/{PIN}` or `{P_PIN}`
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/caswell/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/caswell/parcel-detail/{PIN}` (SPA shell; prefer AppraisalCard for PA)
- **Town of Yanceyville** — https://yanceyvillenc.gov/
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='033'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` (12-digit map); `Account`/`P_PIN` (PA + OneMap `parno`); `NewNumber`; `TID`; OneMap `nparno`=`37033_{PIN}` | Prefer **PIN** for map; **P_PIN/Account** for AppraisalCard |
| polygons | Yes | NC/Caswell/MapServer/9; OneMap | CRS **102719 / 2264** |
| acreage | Yes | `AV_ACRES`; `Calculated`; `P_DEEDED_A`; OneMap `gisacres` | 5–150 → **5,921** |
| ownerName | Yes | `N_NAME` / `N_NAME2`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `N_HOUSE_NR`+`N_STREET`+`N_ADDR2`/`N_ADDR3`+`N_CITY`/`N_STATE`/`N_ZIP_FIRS` | |
| situs address | Yes | `AA_HOUSE_N`+`AA_STREET`+`AA_CITY` (+ `P_STREET_T`) | |
| lastSale date/price | Gap | Deed `P_BOOK`/`P_PAGE` only; `P_YEAR` ≠ sale year | **Sale price/date REST gap** — PA card for QA |
| tax values | Yes | `AV_FMV_LAN` + `AV_FMV_IMP` (= market; sample 32122+83338=115460) | land>0 → **17,122**; imp>0 → **11,541** |
| zoning | Yes (cities-first) | Yanceyville `/21` `ZONE_`/`ZONENAME`; Milton `/22` `MiltonZoning`; Hyco `/10` `Zone` | Unincorp unzoned |
| flu | Gap | Comp Plan + PTRC LDP PDF | No FLU FeatureServer |
| appraiser / viewer link | Yes | ITSPublicCS AppraisalCard `{P_PIN}`; TaxBillSearch; WebGIS; NCPTS | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. NC/Caswell Parcels — parcels + ownership + tax (PRIMARY CAMA)

- **Purpose:** parcels | tax | ownership
- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Caswell/MapServer/9
- **Layer name / id:** Parcels / 9
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (12-digit map key)
  - `Account`, `P_PIN` → parcelIdAccount / PA key (16-digit; identical)
  - `NewNumber` → parcelIdDashed (`0106.01.00.0012.0000`)
  - `TID` → parcelIdAlt
  - `AV_ACRES`, `Calculated`, `P_DEEDED_A` → acreage
  - `N_NAME`, `N_NAME2` → ownerName
  - `N_HOUSE_NR`, `N_STREET`, `N_ADDR2`, `N_ADDR3`, `N_CITY`, `N_STATE`, `N_ZIP_FIRS` → mailing
  - `AA_HOUSE_N`, `AA_STREET`, `AA_CITY`, `P_STREET_T` → situs
  - `AV_FMV_LAN`, `AV_FMV_IMP` → tax.land / tax.improvement (sum ≈ market)
  - `P_BOOK`, `P_PAGE`, `P_BOOK2`/`P_PAGE2`, `P_BOOK3`/`P_PAGE3` → deed
  - `P_YEAR`, `P_STATUS_Y` → tax year / status (not sale date)
  - `AV_USE_TYP`, `P_DISTRICT`, `P_TOWNSHIP` → use / district / township
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **17,222**; `AV_ACRES` 5–150 → **5,921**; `Calculated` 5–150 → **5,639**; `AV_FMV_LAN>0` → **17,122**; `N_NAME` non-empty → **17,147**; sample PIN `903100158901` / P_PIN `0106010000120000` = BERTIE LANCE JR & DONNA JONES, acres **5.57**, FMV land+imp **115,460**, situs RIVER BEND / MILTON, centroid ≈ **-79.29, 36.54** (Caswell)
- **Notes:** **PRIMARY** wire-first. MapServer only (no FeatureServer twin). MaxRecordCount **1000** — paginate. **No SalePrice / SaleDate fields.** WebGIS identify wires AppraisalCard to `atts.P_PIN`. Auth **none**.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='033'`
- **Key fields:** `parno`↔`Account`/`P_PIN`; `nparno`=`37033_{PIN}`; `altparno`↔`TID`; `ownname`; `mailadd`…; `siteadd`; `gisacres`; `parval`/`landval`/`improvval`
- **Verified:** yes — count **17,222**; `gisacres` 5–150 → **5,921**; `ownname` → **17,222**; `parval>0` → **17,124**; `saledate`/`saledatetx` → **0**
- **Notes:** Join verified `parno='0106010000120000'` ↔ county Account (gisacres 5.57). Prefer county /9 for current CAMA; OneMap has **no sale**.

### 3. City Zoning — Yanceyville (cities-first)

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Caswell/MapServer/21
- **Count:** **125**
- **Fields:** `ZONE_` → zoning code; `ZONENAME` → description
- **Districts:** RR8 (37), HB (22), RA (16), R12 (14), OI (10), B1 (8), M1 (8), R8 (6), R-MH (1), …
- **Names:** RESTRICTED RESIDENTIAL, HIGHWAY BUSINESS, RESIDENTIAL AGRICULTURAL, OFFICE & INSTITUTIONAL, CENTRAL BUSINESS, RESTRICTED MANUFACTURING, RESIDENTIAL, MOBILE HOME PARK
- **Notes:** Layer titled “City Zoning”; only Yanceyville + Milton have city limits (`/4`). Milton has dedicated `/22` — treat `/21` as **Yanceyville**.
- **Status:** usable

### 4. Milton Zoning (cities-first)

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Caswell/MapServer/22
- **Count:** **11**
- **Fields:** `MiltonZoning`; `HistoricDistrict` (YES/PARTIAL/NO)
- **Districts:** R-2, R-2*, C-1/MU, O&I, R-1, mixed splits
- **Status:** usable

### 5. Hyco Lake Zoning (special district)

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Caswell/MapServer/10
- **Count:** **16**
- **Fields:** `Zone` / `Descriptio`; optional `PIN`
- **Districts:** RR Resort Residential (11), RB Recreation Business (4), IP Industrial Park (1)
- **Notes:** County-administered lake area zoning (not a municipality). PDF map on Planning site.
- **Status:** usable

### 6. City Limits — municipality routing

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Caswell/MapServer/4
- **Count:** **2** — `FCODE` = **YANCEYVILLE**, **MILTON**
- **Status:** usable

### 7. Watershed overlays (NOT base zoning)

- Haw River `/11`, Jordan Lake `/12`, Stoney Creek `/13`, Dan River Critical `/14`, Dan River Protected `/15`, Watershed `/31`
- **Status:** partial (overlay / environmental only)

### 8. Address Points (situs join aid)

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Caswell/MapServer/1
- **Geometry:** Point
- **Status:** usable (secondary to parcel AA_* situs)

## Municipalities (city-first routing)

| Municipality / area | Zoning REST | FLU REST | Notes |
|---------------------|-------------|----------|-------|
| Yanceyville (county seat) | City Zoning `/21` `ZONE_` | Comp Plan PDF | Cities-first primary |
| Milton | Milton Zoning `/22` `MiltonZoning` | Comp Plan PDF | HistoricDistrict flag |
| Hyco Lake (unzoned town; special district) | Hyco Lake Zoning `/10` `Zone` | — | County lake zoning |
| Unincorporated county | gap (unzoned) | Comp Plan PDF | Watershed overlays only |
| CDPs (Providence, Semora, Pelham, Blanch, Leasburg, …) | gap | — | Unincorporated |

## Deep-link templates

| Role | Template |
|------|----------|
| **Appraisal card (PRIMARY PA)** | `https://www.bttaxpayerportal.com/ITSPublicCS/AppraisalCard.aspx?id={P_PIN}` |
| Tax bill by parcel | `https://www.bttaxpayerportal.com/ITSPublicCS/TaxBillSearch/Parcel/{PIN}` (also accepts `{P_PIN}`) |
| PA Basic Search | https://www.bttaxpayerportal.com/ITSPublicCS/BasicSearch |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/caswell/parcel-detail/{PIN}` |
| Jurisdiction GIS | https://www.webgis.net/nc/caswell/ |
| WebGIS mailable (in-app) | `?id=Parcels\|P_PIN\|{P_PIN}` |

**PA key note:** `P_PIN` / `Account` (16-digit, e.g. `0106010000120000`) — **not** 12-digit `PIN`. SiteCustom.js: `AppraisalCard.aspx?id=` + `feat.attributes["P_PIN"]`. Verified PDF for sample Account returns owner/market/acres matching REST.

## Gaps

- **Sale price and sale date** not on public parcel REST (`P_YEAR` is tax year; use AppraisalCard / Register of Deeds for sale QA)
- No public countywide **base** zoning — only Yanceyville / Milton / Hyco Lake (by design per Planning FAQ)
- **FLU FeatureServer gap** — Comprehensive Plan + PTRC LDP PDF only
- OneMap `saledate`/`saledatetx` empty for Caswell
- NCPTS deep-link is SPA shell (no server-rendered CAMA); prefer ITSPublicCS AppraisalCard
- No phones/emails; no paid vendors; utilities + AADT out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- Live `returnCountOnly` + sample attributes + WGS84 centroids for NC/Caswell/MapServer Parcels/9, City Zoning/21, Milton/22, Hyco/10, City Limits/4; NC OneMap `cntyfips='033'` join `parno`↔`P_PIN`; ITSPublicCS AppraisalCard `?id={P_PIN}` PDF; WebGIS SiteCustom.js PA wiring.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://www.webgis.net/arcgis/rest/services/NC/Caswell/MapServer/9 · id `PIN` · live count **17,222** · 5–150 ac **5,921** (`AV_ACRES >= 5 AND AV_ACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='CASWELL'` gives **244** stations (75 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27CASWELL%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Caswell'` gives **242** stations (155 with AADT_2025, 153 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Caswell%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `AV_FMV_LAN` non-zero **17,122**, `AV_FMV_IMP` non-zero **11,541**
- **Sale history (gap):** price not on REST; date not on REST. No sale price/date on REST (P_BOOK/P_PAGE deed refs only; NC OneMap saledatetx empty). ITSPublicCS AppraisalCard PDF has Sales grid (Sale Date / Sale Price).
- **Owner entity:** fields `N_NAME`, `N_NAME2`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **588** (all parcels: 1,481), using the SQL approximation on `N_NAME`.
- **PA deep link:** `https://www.bttaxpayerportal.com/ITSPublicCS/AppraisalCard.aspx?id={P_PIN}`. Tested `0106010000150000` → HTTP **200** (application/pdf), content verified: True. Owner and parcel id verified in the response.
- **Jurisdiction GIS viewer:** https://www.webgis.net/nc/caswell/ → HTTP **200** (Caswell Co WebGIS)
- **Pass 2 gaps:** sale gap
