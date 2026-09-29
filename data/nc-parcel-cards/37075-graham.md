# Graham County, NC — GIS County Card

## Summary

Graham County (Asheville / Western NC, FIPS **37075**, slug **graham**, `cntyfips='075'`) publishes CAMA parcels on AGD-hosted **GrahamAGOL** FeatureServer (**Parcels** layer **6**, twins **15**/**16**) — ~**9,459** polys with owner (`OWNER_NAME`), mailing (`ADDR_*`/`CITY`/`STATE`/`ZIP`), situs (`HOUSE_NUMB`+`STREET_NM`/`ADDRESS`), `calcacres`/`totalacres`/`ACREAGE` (text), full tax (`LAND_VALU`/`BUILD_VALU`/`XFOB_VALUE`/`TOTAL_VALU`), **`SALEPRICE`** + `DEED_DATE` (YYYYMMDD), and embedded **`PRC_link`**. ~**1,963** with `calcacres` 5–150; **4,457** with `SALEPRICE>0`. County org `Tax_View` / `grahamconc` Tax Map WABs require token or report **subscription canceled** — do not wire. **Zoning is cities-first:** Town of **Lake Santeetlah** only (Zoning Ordinance + Land Use Plan **PDFs**; **no public zoning FeatureServer**). **Robbinsville** (seat) and **Fontana Dam** have **no zoning REST** (Robbinsville 2022 CPNI workshop recommended *considering* zoning). Unincorporated Graham is **largely unzoned** on public REST. **FLU:** Lake Santeetlah Land Use Plan PDF only — no FLU FeatureServer. **PA deep-link:** `https://bttaxpayerportal.com/itspublicgr/AppraisalCard.aspx?parcel={PARNUM}`. **Jurisdiction GIS:** https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=561a20cc33894cb98ff18aa6925af254. Markets: **[Asheville]**.

## Portals

- **Jurisdiction GIS (AGD Web AppBuilder)** — https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=561a20cc33894cb98ff18aa6925af254
- **GrahamAGOL FeatureServer** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GrahamAGOL/FeatureServer
- **County Mapping & GIS page** — https://www.grahamcounty.org/mapping.html ( intermittently 5xx/406 from some egress )
- **Tax Assessor** — https://www.grahamcounty.org/tax_assessor.html
- **ITSPublicGR Appraisal Card (PA deep-link)** — `https://bttaxpayerportal.com/itspublicgr/AppraisalCard.aspx?parcel={PARNUM}`
- **ITSPublicGR Basic / Real Estate / Sales** — https://bttaxpayerportal.com/itspublicgr/BasicSearch.aspx ; RealEstate.aspx ; Sales.aspx
- **Register of Deeds (Cott)** — https://cotthosting.com/ncgraham/LandRecords/protected/v4/SrchName.aspx
- **NCPTS parcel detail** — `https://lrcpwa.ncptscloud.com/graham/parcel-detail/{pin}`
- **NCPTS search** — https://lrcpwa.ncptscloud.com/graham/parcel-search
- **Town of Lake Santeetlah Zoning** — https://www.townoflakesanteetlah.org/zoning.html
- **Lake Santeetlah Land Use Plan PDF** — https://www.townoflakesanteetlah.org/uploads/6/9/3/2/69322769/land_use_plan.pdf
- **Lake Santeetlah Zoning Ordinance PDF** — https://www.townoflakesanteetlah.org/uploads/6/9/3/2/69322769/amended_zoning_ordinance_4_14_26.pdf
- **Lake Santeetlah town map PDF** — https://www.townoflakesanteetlah.org/uploads/6/9/3/2/69322769/town_of_lake_santeetlah.pdf
- **NCDOT Graham CTP (transportation, not FLU)** — https://connect.ncdot.gov/projects/planning/Pages/CTP-Details.aspx?study_id=Graham+County
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='075'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PARNUM`/`parno` (PA); `pin` (OneMap); `ACCT_NO` | OneMap `parno` ↔ county **`pin`** (not PARNUM) |
| polygons | Yes | GrahamAGOL/6; /15; /16; OneMap | CRS **102719 / 2264** |
| acreage | Yes | `calcacres`; `totalacres`; `ACREAGE` (text `…AC`); OneMap `gisacres` | ~**1,963** calc 5–150; totalacres 5–150 → **2,172** |
| ownerName | Yes | `OWNER_NAME`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `ADDR_1`/`ADDR_2`/`ADDR_3`,`CITY`,`STATE`,`ZIP` | |
| situs address | Yes | `HOUSE_NUMB`+`STREET_NM`/`STREET_TYP`/`DIRECTION`; `ADDRESS`; OneMap `siteadd` | Some rows fold road into STREET_NM |
| lastSale date/price | Yes | `SALEPRICE`; `DEED_DATE` (YYYYMMDD) | ~**4,457** SALEPRICE>0; OneMap saledatetx **empty** |
| tax values | Yes | `LAND_VALU`,`BUILD_VALU`,`XFOB_VALUE`,`TOTAL_VALU` | TOTAL_VALU>0 → **9,117** |
| zoning | Cities-first PDF | Lake Santeetlah ordinance PDF | **No zoning FeatureServer**; Robbinsville/Fontana Dam/unincorp unzoned on REST |
| flu | Gap / PDF | Lake Santeetlah Land Use Plan PDF; NCDOT CTP ≠ FLU | No FLU FeatureServer |
| appraiser / viewer link | Yes | `PRC_link` `{PARNUM}`; AGD viewer; NCPTS `{pin}` | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. GrahamAGOL Parcels — parcels + ownership + tax + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | situs
- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GrahamAGOL/FeatureServer/6
- **Layer name / id:** Parcels / 6
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PARNUM`, `parno`, `PIN_1` → parcelId (tax / AppraisalCard `parcel=`)
  - `pin` → parcelIdOneMap / NCPTS (joins OneMap `parno`)
  - `ACCT_NO` → parcelIdAccount
  - `calcacres`, `totalacres`, `ACREAGE` → acreage
  - `OWNER_NAME`, `NAME` → ownerName
  - `ADDR_1`, `ADDR_2`, `ADDR_3`, `CITY`, `STATE`, `ZIP` → mailing
  - `HOUSE_NUMB`, `DIRECTION`, `STREET_NM`, `STREET_TYP`/`STREET_SUF`, `ADDRESS` → situs
  - `LEGAL_1`, `LEGAL_2` → legal
  - `SALEPRICE`, `DEED_DATE`, `STAMPS` → lastSale
  - `DEEDBOOK`, `DEEDPAGE`, `BOOK_PAGE`, `PLATBOOK`, `PLATPAGE` → deed / plat
  - `LAND_VALU`, `BUILD_VALU`, `XFOB_VALUE`, `TOTAL_VALU` → tax
  - `PRC_link` → appraiser deep-link (full AppraisalCard URL)
  - `Online_Records_Link` → ROD search (Cott; not parcel-id deep-link)
- **WKID / CRS:** 102719 (latest 2264)
- **Verified:** yes — count **9,459**; `calcacres` 5–150 → **1,963**; `totalacres` 5–150 → **2,172**; `SALEPRICE>0` → **4,457**; `TOTAL_VALU>0` → **9,117**; `OWNER_NAME IS NOT NULL` → **9,119**; `PRC_link` populated → **9,459**; sample `PARNUM=553800010002` / `pin=5508816230` OWNER **GIBSON CLAUDINE**, SALEPRICE **150000**, TOTAL_VALU **137770**, calcacres **18.54**, centroid ≈ **-83.997, 35.243** (Graham / Robbinsville area); AppraisalCard HTTP 200 with parcel text for `parcel=553800010002`
- **Notes:** PRIMARY wire-first. MaxRecordCount **1000** — paginate. Auth **none**. Prefer `calcacres` (numeric) over text `ACREAGE`. Twins `/15` Parcels_AGOL and `/16` Parcels_append same schema/count.

### 2. GrahamAGOL Parcels_AGOL / Parcels_append — twins

- **REST URLs:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GrahamAGOL/FeatureServer/15 ; …/FeatureServer/16
- **Verified:** count **9,459** each; same CAMA fields as /6
- **Notes:** Prefer /6 as labeled primary in AGD webmap (“Parcels PIN” / “Parcels Owner Name”).

### 3. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership (no usable sale date/price)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='075'`
- **Key fields:** `parno`↔county **`pin`**, `ownname`, `mailadd`, `siteadd`, `gisacres`, `parval`/`landval`/`improvval`, `saledatetx` (empty)
- **Verified:** count **9,840**; `gisacres` 5–150 → **1,968**; `parval>0` → **9,105**; join verified OneMap `parno='5538864002'` ↔ county `pin` / OWNER **RENNER MICHAEL L** / TOTAL_VALU **455160**; OneMap `parno='5528228998'` ↔ county `pin` / STITH WILLIAM TRUST
- **Notes:** OneMap has **more** polys than GrahamAGOL (~9840 vs 9459) — geometry-only / sync lag possible. Prefer county `SALEPRICE`. `saledatetx` all empty strings. MaxRecordCount **5000**.

### 4. Municipal Boundaries (routing)

- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GrahamAGOL/FeatureServer/14
- **Verified:** count **3** — Robbinsville (Town, pop 597), Fontana Dam (Town, 13), Lake Santeetlah (Town, 38)
- **Notes:** Use for cities-first routing; not zoning.

### 5. Zoning — cities-first Lake Santeetlah (PDF only; no FeatureServer)

| Municipality | Source | REST? | Notes |
|--------------|--------|:-----:|-------|
| **Lake Santeetlah** | Zoning Ordinance PDF (amended); Land Use Plan PDF; town map PDF | **No** | Only municipality with published zoning/FLU docs |
| **Robbinsville** (seat) | — | No | CPNI 2022 recommended considering zoning; no ordinance/REST found |
| **Fontana Dam** | — | No | No zoning REST found |
| Unincorporated | — | No | Mountain-county **unzoned** on public REST |

- **Do not wire** REGIS `GrahZoning*` / `Graham/GrahZoning*` — those are **City of Graham (Alamance County)**, not Graham County.

### 6. FLU — PDF only (no public FeatureServer)

- **Lake Santeetlah Land Use Plan:** https://www.townoflakesanteetlah.org/uploads/6/9/3/2/69322769/land_use_plan.pdf
- **NCDOT Graham CTP:** https://connect.ncdot.gov/projects/planning/Pages/CTP-Details.aspx?study_id=Graham+County — transportation, **not** FLU
- **Notes:** No countywide or municipal FLU FeatureServer verified.

### 7. Blocked / retired (do not wire)

- **Tax_View** FeatureServer (`services1…/IaS5ebgfIHqc2kcL/…/Tax_View`) — **Token Required**
- **grahamconc** Tax Parcel Viewer / Tax Map WAB items — **Subscription canceled (403)**
- County org Layers / CityLimits FeatureServers — token-gated

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS REST? | FLU REST? | Notes |
|--------------|---------------|------:|:-------------:|:---------:|-------|
| **Robbinsville** | *(none)* | — | County AGOL host | No | County seat; unzoned on REST |
| **Lake Santeetlah** | Ordinance + LUP PDFs | — | No zoning FS | No (PDF) | Cities-first PDF only |
| **Fontana Dam** | *(none)* | — | County | No | Tiny town; unzoned on REST |
| Unincorporated | — | — | County | No | **Largely unzoned** |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| ITSPublicGR Appraisal Card (preferred) | `https://bttaxpayerportal.com/itspublicgr/AppraisalCard.aspx?parcel={PARNUM}` |
| Encoding | Use `PARNUM` (also `parno` / value embedded in `PRC_link`) — **not** OneMap/`pin` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/graham/parcel-detail/{pin}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/graham/parcel-search |
| Jurisdiction GIS | https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=561a20cc33894cb98ff18aa6925af254 |

Verified AppraisalCard for `parcel=553800010002`: owner **GIBSON CLAUDINE**, market/assessed building detail present (HTTP 200).

## Gaps / caveats

- **No public zoning FeatureServer** — Lake Santeetlah PDF/ordinance only; Robbinsville + Fontana Dam + unincorporated **unzoned** on REST
- **No public FLU FeatureServer** — Santeetlah Land Use Plan PDF; NCDOT CTP ≠ FLU
- County **Tax_View** / **grahamconc** Tax Map apps **token / subscription canceled** — use GrahamAGOL + AGD viewer
- `ACREAGE` is text (`19.6000AC`) — use numeric `calcacres`/`totalacres` for range filters
- OneMap `parno` joins county **`pin`**, not `PARNUM` (easy remap trap)
- OneMap `saledatetx` empty county-wide — prefer county `SALEPRICE` + `DEED_DATE`
- OneMap parcel count (~9840) > GrahamAGOL (~9459)
- **Reject** REGIS City-of-Graham (Alamance) zoning services mislabeled “Grah*”
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Graham County GIS / Tax Assessor / Land Records. Cadastral maps from recorded deeds/plats/public records; not survey quality; County disclaims warranties (see Mapping page disclaimer). Commercial resale subject to **NCGS 132-10**. Attribute Graham County GIS (and Town of Lake Santeetlah where municipal zoning/FLU PDFs used). AGD Online hosts the public viewer/FeatureServer.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 8+
- **tranche:** 3 (tax/sale/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- Live `returnCountOnly` + sample attribute/geo queries against GrahamAGOL/6,/14,/15,/16; NC OneMap `cntyfips='075'`; ITSPublicGR AppraisalCard HTTP cross-check; AGD webappviewer; Lake Santeetlah PDF HEAD/GET; centroid geo-check in Graham (Robbinsville / Little Snowbird).


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GrahamAGOL/FeatureServer/6 · id `PARNUM` · live count **9,459** · 5–150 ac **1,963** (`calcacres >= 5 AND calcacres <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='GRAHAM'` gives **104** stations (74 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27GRAHAM%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Graham'` gives **103** stations (64 with AADT_2025, 64 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Graham%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `TOTAL_VALU` non-zero **9,117**, `LAND_VALU` non-zero **9,113**
- **Sale history (ok):** price `SALEPRICE` >0 **4,457**, `STAMPS` >0 **866**; date `DEED_DATE` non-null **9,021**
- **Owner entity:** fields `OWNER_NAME`, `NAME`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **232** (all parcels: 1,085), using the SQL approximation on `OWNER_NAME`.
- **PA deep link:** `https://bttaxpayerportal.com/itspublicgr/AppraisalCard.aspx?parcel={PARNUM}`. Tested `5538000028120` → HTTP **200** (text/html; charset=utf-8), content verified: True. Owner and parcel id verified in the response.
- **Jurisdiction GIS viewer:** https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=561a20cc33894cb98ff18aa6925af254 → HTTP **200** (ArcGIS Web Application); ArcGIS item access=public
- **Pass 2 gaps:** none
