# Alleghany County, NC — GIS County Card

## Summary

Alleghany County (Boone / Winston-Salem shed, FIPS **37005**, slug **alleghany**, `cntyfips='005'`) publishes public HandP **WebGIS** at **`www.webgis.net/nc/alleghany/`** with ArcGIS REST **`NC/Alleghany/MapServer`**. **Wire-first parcels:** **MapServer/11 Parcels** — ~**14,808** polys with 10-digit `PIN`, `OWNER`/`OWNER2`, `TOTAL_CALCULATED`/`DEEDED_ACREAGE`, deed book/page/date — **no tax or sale price on REST**. ~**3,628** with acres 5–150. **Tax join (TRANCHE-3):** **NC OneMap** `cntyfips='005'` — `parval`/`landval`/`improvval` (+ mailing/situs); `parval>0` → **14,591**; join `PIN`=`parno`. **Sale price REST gap** — deed/`saledatetx` dates only; Bitek **Sales Date & Price** UI + AppraisalCard sales section. **Zoning is cities-first:** only incorporated muni is **Sparta** (county seat) — traditional districts (RA/R-20/R-12/R-8/R-MF/OI/CB/NB/LI) via AmLegal + LUP PDF map; **zoning REST gap** (route via Sparta Limits/16 + ETJ/17). **Unincorporated** = county **Open District** (non-Euclidean Land Development Ordinance) — no cadastral zone polys. **FLU:** WebGIS **Land Classifications/26** (`CLASSIFICA`: Urban/Developed, Urban Transition, Rural Community; **19** polys) — ACLDP coarse proxy. **PA deep-link:** `https://www.bttaxpayerportal.com/ITSPublicAL/AppraisalCard.aspx?id={PIN}` (verified PDF). **Jurisdiction GIS:** https://www.webgis.net/nc/alleghany/. **Reject** AGOL `Alleghany_Zoning_2022` and GeoDecisions Alleghany/Public — **Virginia**. Markets: **[Boone, Winston-Salem]**.

## Portals

- **Jurisdiction GIS (WebGIS)** — https://www.webgis.net/nc/alleghany/ (alias `/nc/Alleghany/`; legacy `arcims.webgis.net/nc/alleghany/default.asp`)
- **Viewer deep-link** — `https://www.webgis.net/nc/alleghany/?id=Parcels|PIN|{PIN}` (modCmdLine `id=Layer|Field|Value`)
- **County ArcGIS REST** — https://www.webgis.net/arcgis/rest/services/NC/Alleghany/MapServer
- **PA / AppraisalCard PDF** — `https://www.bttaxpayerportal.com/ITSPublicAL/AppraisalCard.aspx?id={PIN}`
- **PA Basic Search (Bitek)** — https://www.bttaxpayerportal.com/ITSPublicAL/ (includes Sales Date & Price search)
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/alleghany/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/alleghany/parcel-detail/{PIN}`
- **County GIS dept** — https://alleghanycounty-nc.gov/gis/
- **Tax Office** — https://alleghanycounty-nc.gov/tax-office/
- **County Planning** — https://alleghanycounty-nc.gov/planning/
- **County Land Development Ordinance (PDF)** — https://alleghanycounty-nc.gov/ordinances/1-324.pdf
- **Register of Deeds (deed image)** — `https://alleghanync.courthousecomputersystems.com/Image/ShowDocImage?BookType=DEED&BookNum={DEED_BOOK}&PageNum={DEED_PAGE}`
- **Town of Sparta** — https://www.townofsparta.org/
- **Sparta Land Use Plan (zoning map PDF)** — https://www.townofsparta.org/wp-content/uploads/2022/06/Sparta-Land-Use-Plan-Final.pdf
- **Sparta Zoning Ordinance (AmLegal)** — https://codelibrary.amlegal.com/codes/spartanc/latest/sparta_nc/0-0-0-3521
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='005'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`; OneMap `parno` | Prefer **PIN** for AppraisalCard / NCPTS / viewer `?id=` |
| polygons | Yes | WebGIS/11; OneMap | CRS **102719 / 2264** |
| acreage | Yes | `TOTAL_CALCULATED`; `DEEDED_ACREAGE`; OneMap `gisacres` | ~**3,628** in 5–150 |
| ownerName | Yes | `OWNER`/`OWNER2`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes (OneMap join) | `mailadd`/`mcity`/`mstate`/`mzip` | Not on WebGIS parcels |
| situs address | Yes (OneMap join) | `siteadd` | Not on WebGIS parcels |
| lastSale date/price | Partial (date) | `DEED_DATE`; `saledatetx` | **Sale price REST gap** — Bitek Sales UI / AppraisalCard |
| tax values | Yes (OneMap join) | `parval`/`landval`/`improvval` | WebGIS has no tax fields |
| zoning | Gap (cities-first intent) | Sparta Limits/ETJ routing + ordinance/PDF | No public zoning FS |
| flu | Partial | Land Classifications `CLASSIFICA` | 19 coarse ACLDP polys |
| appraiser / viewer link | Yes | AppraisalCard `{PIN}`; WebGIS `?id=`; NCPTS | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. NC/Alleghany Parcels — geometry + ownership + deed (PRIMARY polygons)

- **Purpose:** parcels | ownership | deed date
- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Alleghany/MapServer/11
- **Layer name / id:** Parcels / 11
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (10-digit; PA / NCPTS / viewer key)
  - `TOTAL_CALCULATED`, `DEEDED_ACREAGE` → acreage
  - `OWNER`, `OWNER2` → ownerName
  - `DEED_BOOK`, `DEED_PAGE`, `DEED_DATE` → deed / lastSale.date
  - `PLAT_BOOK`, `PLAT_PAGE`, `SUBDIVISION`, `VOLUNTARY_AGRICULTURAL_DISTRICT` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **14,808**; `TOTAL_CALCULATED` 5–150 → **3,628**; owner non-empty → **14,777**; deed date non-empty → **14,729**; sample PIN `3030369596` = CHURCH, DIANE JONES (LIFE ESTATE), acres ~**43.84**, deed 130/8 / 07-02-1985, centroid ≈ **-81.262, 36.495** (Alleghany)
- **Notes:** Best county geometry/owner layer. **No tax or sale price.** MaxRecordCount **1000**. Auth **none**. Hydro/ROW stubs exist (e.g. PIN `NEW RIVER`).

### 2. NC OneMap Parcels (polys) — tax + mailing + situs (PRIMARY tax)

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='005'`
- **Key fields:** `parno`↔`PIN`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`, `gisacres`, `parval`/`landval`/`improvval`, `saledatetx`
- **Verified:** yes — count **14,795**; `gisacres` 5–150 → **3,628**; `ownname` non-empty → **14,764**; `parval>0` → **14,591**; `saledate IS NOT NULL` → **0**; `saledatetx` non-empty → **14,714**
- **Notes:** **PRIMARY for tax** + mailing/situs. No sale price. Join verified `parno='3030369596'` ↔ WebGIS PIN; `parval` **200,600** matches AppraisalCard TOTAL APPRAISED VALUE.

### 3. Land Classifications — FLU proxy (ACLDP)

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Alleghany/MapServer/26
- **Verified:** count **19** — `CLASSIFICA` values: **Urban/Developed**, **Urban Transition**, **Rural Community**
- **Notes:** Coarse countywide FLU from Land Development Plan framework — not parcel-level FLUM. Prefer for unincorporated context; Sparta also has LUP PDF map.

### 4. Sparta Limits + ETJ — municipality routing

| Layer | Name | Count | Notes |
|------:|------|------:|-------|
| 16 | Sparta Limits | **1** | `MB_NAME` town limit |
| 17 | Sparta ETJ | **1** | Extra-territorial jurisdiction boundary |

- County LDP jurisdiction **excepts** Sparta town limits + ETJ (Sparta zoning ordinance applies inside).

### 5. Sparta zoning — cities-first intent (REST gap)

- **Ordinance districts:** RA, R-20, R-12, R-8, R-MF, OI, CB, NB, LI (AmLegal Ch. 156)
- **Map:** Sparta Land Use Plan Final PDF (zoning map pages)
- **No public FeatureServer** — HCCOG has Ashe/Avery/etc. zoning but **no Alleghany/Sparta zoning service**
- **Reject:** `Alleghany_Zoning_2022` (Virginia; centroid ≈ -80.05, 37.65); GeoDecisions `Alleghany/Public` (Virginia)

## Municipalities (cities-first)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| **Sparta** | Ordinance + LUP PDF (REST **gap**) | Limits/ETJ 1+1 | townofsparta.org | LUP PDF | Only incorporated muni; county seat |
| Unincorporated Alleghany | Open District (LDP) — no zone polys | — | County WebGIS | Land Classifications/26 | Non-Euclidean conditional-use system |
| CDPs / communities (Laurel Springs, Roaring Gap, Piney Creek, Glade Creek, Ennice, …) | Unincorporated | — | — | Land Classifications | Fire tax districts on WebGIS — not zoning |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| Property Record Card PDF (preferred) | `https://www.bttaxpayerportal.com/ITSPublicAL/AppraisalCard.aspx?id={PIN}` |
| Encoding | `PIN` = 10-digit string (e.g. `3030369596`). siteCustom also uses `itspublical//` double-slash. |
| Viewer deep-link | `https://www.webgis.net/nc/alleghany/?id=Parcels\|PIN\|{PIN}` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/alleghany/parcel-detail/{PIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/alleghany/parcel-search |
| Bitek Basic Search | https://www.bttaxpayerportal.com/ITSPublicAL/ |
| Jurisdiction GIS | https://www.webgis.net/nc/alleghany/ |

WebGIS `scripts/siteCustom.js` `parcelDetail()` wires **View Property Card** → `AppraisalCard.aspx?id=` + PIN. Verified PDF for `3030369596` returns **CHURCH DIANE JONES (LIFE TENANT)** / Parcel ID **3030369596** / Account **84750** / 43.94 AC / TOTAL APPRAISED **200,600**.

## Gaps / caveats

- **Sale price REST gap** — neither WebGIS nor OneMap publish sale price; Bitek Basic Search includes Sales Date & Price; AppraisalCard sales block shows price when present
- **Sparta zoning REST gap** — traditional zoning exists; no public FeatureServer (use Limits/ETJ + ordinance/PDF)
- **Unincorporated zoning REST gap** — Open District LDP (not Euclidean cadastral zones)
- WebGIS parcels lack tax/mailing/situs — **must join OneMap** `cntyfips='005'` on `PIN`=`parno`
- OneMap `saledate` empty; `saledatetx` text date only; **no sale price**
- County / Town PDF URLs often return bot-challenge HTML from datacenter egress — URLs are the published public links
- **Do not wire** Virginia `Alleghany_Zoning_2022` or GeoDecisions Alleghany/Public
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Alleghany County GIS / Tax Office (Hurt & Proffitt WebGIS); Town of Sparta (zoning ordinance / LUP); NC OneMap Integrated Cadastral Data Exchange. Map data compiled from recorded deeds/plats/public records; consult primary sources; not survey quality. Commercial resale subject to **NCGS 132-10**. Attribute Alleghany County GIS (and Town of Sparta where zoning applies).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 6
- **tranche:** 3 (tax/owner public via OneMap+WebGIS; sale price REST gap documented; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + FLU proxy + cities-first Sparta zoning suite with REST gap noted)
- Live `returnCountOnly` + sample attribute/geometry queries against NC/Alleghany Parcels/11, Land Classifications/26, Sparta Limits/16, Sparta ETJ/17, NC OneMap `cntyfips='005'`; AppraisalCard PDF `?id={PIN}` cross-check; siteCustom.js + modCmdLine.js deep-link wiring; rejected VA Alleghany_Zoning_2022; geo-check centroid in Alleghany.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://www.webgis.net/arcgis/rest/services/NC/Alleghany/MapServer/11 · id `PIN` · live count **14,808** · 5–150 ac **3,628** (`TOTAL_CALCULATED >= 5 AND TOTAL_CALCULATED <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='ALLEGHANY'` gives **173** stations (119 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27ALLEGHANY%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Alleghany'` gives **174** stations (97 with AADT_2025, 109 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Alleghany%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (gap):** none on the parcel layer. Fallback: {"source": "NC OneMap parcels (join to PIN)", "restUrl": "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1", "where": "cntyfips='005' AND parval>0", "liveCount": 14591, "fields": ["parval", "landval", "improvval"], "pa": "ITSPublicAL AppraisalCard PDF (values + sales grid)"}
- **Sale history (partial):** price not on REST; date `DEED_DATE` non-null **14,729**. DEED_DATE (string) only; price on ITSPublicAL AppraisalCard PDF SALES DATA grid.
- **Owner entity:** fields `OWNER`, `OWNER2`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **677** (all parcels: 2,722), using the SQL approximation on `OWNER`.
- **PA deep link:** `https://www.bttaxpayerportal.com/ITSPublicAL/AppraisalCard.aspx?id={PIN}`. Tested `3030369596` → HTTP **200** (application/pdf), content verified: True. Owner and parcel id verified in the response.
- **Jurisdiction GIS viewer:** https://www.webgis.net/nc/alleghany/ → HTTP **200** (Alleghany County NC WebGIS)
- **Pass 2 gaps:** tax gap, sale partial
