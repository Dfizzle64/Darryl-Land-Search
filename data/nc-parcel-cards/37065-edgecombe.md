# Edgecombe County, NC — GIS County Card

## Summary

Edgecombe County (Rocky Mount / eastern RDU shed, FIPS **37065**, slug **edgecombe**) publishes strong **public** ArcGIS REST at `gis.edgecombecountync.gov`. Countywide **tax parcel polygons** (~**31,606**; ~**4,259** with `acreage` 5–150) carry ownership, mailing, situs (`location` on ~99.8%), last sale date/price, and full CAMA values on `webmap` MapServer/10. Prefer **`linkpin`** (12-digit, no hyphens) for Keystone PA `pKEY` and map `?PIN=`; display PIN is `{parcel}-{pinsuf}` (`####-##-####-##`). **Zoning is cities-first** on the county host: **Tarboro** (96, `ALPHA`), **Rocky Mount tip** (144, `ZONING` — Nash-side primary on Nash card Avineon_WebTemplate/72 ~2972), Sharpsburg, Leggett, Pinetops, Princeville, Macclesfield, Conetoe. Unincorporated **Zoning** (~175, `ALPHA`). **FLU:** Land Use Districts only **UA/UB** (2 polys) — coarse gap. **NC OneMap** (`cntyfips='065'`) is a solid fallback with situs on polys. No independent city ArcGIS REST (Rocky Mount ViewPro only). Markets: **Rocky Mount / RDU shed**.

## Portals

- **Map viewer (jurisdiction GIS URL)** — https://gis.edgecombecountync.gov/maps/default.htm
- **Viewer deep-link by parcel** — `https://gis.edgecombecountync.gov/maps/default.htm?PIN={linkpin}`
- **County ArcGIS REST root** — https://gis.edgecombecountync.gov/arcgis/rest/services
- **Tax / Property Search (Keystone WebPAAS)** — https://taxpa.edgecombecountync.gov/paas/?DEST=pSearch
- **PA deep-link (detail; POST `pKEY` preferred)** — `https://taxpa.edgecombecountync.gov/paas/?DEST=pDetail&pKEY={linkpin}` (search PIN format `####-##-####-##` = `{parcel}-{pinsuf}`)
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/edgecombe/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/edgecombe/parcel-detail/{parcel}` (also `{linkpin}`)
- **Tax Assessor** — https://www.edgecombecountync.gov/businesses/tax_assessor/
- **Tax Administration** — https://www.edgecombecountync.gov/departments/tax_administration/
- **Planning & Inspections / E-911** — https://www.edgecombecountync.gov/departments/planning_inspections_and_e-911/
- **Rocky Mount interactive zoning (ViewPro; no public city REST)** — https://map.viewprogis.com/vp/rockymount-nc
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Municipalities (first-class)

| Municipality | Local public GIS? | Zoning / FLU source |
|--------------|-------------------|---------------------|
| **Tarboro** (county seat) | County-host | Prefer `webmap/15` (96, `ALPHA`: HB, GR10, HI, GR3, O&I, NB, GR5, RD, …). FLU: UA/UB county only |
| **Rocky Mount** (tip) | County-host + ViewPro (no city ArcGIS REST) | Edgecombe `webmap/16` (144, `ZONING`) = **Edgecombe-side only**. Prefer **Nash** `Avineon_WebTemplate/72` (2972, `ZONING`) for Nash-side. ViewPro viewer |
| Sharpsburg | County-host | `/13` (167) `Zone` (R-10, B-1, R-6M, R-6, MHP, …). Spans Nash/Wilson — clip |
| Leggett | County-host | `/14` (82) `ALPHA` |
| Pinetops | County-host | `/17` (21) `ALPHA` |
| Princeville | County-host | `/18` (7) `ALPHA` (thin) |
| Macclesfield | County-host | `/19` (10) `ALPHA` |
| Conetoe | County-host | `/20` (12) `ALPHA` |
| Whitakers | City limits only | **No Edgecombe zoning layer** — prefer Nash Avineon_WebTemplate/75 for Nash-side tip |
| Speed | ETJ / overlay | Speed Community Overlay `/57` (1); no town zoning polygons |
| Unincorporated / ETJ | County | Zoning `/23` (175) + ETJ `/22` (7) + Land Use Districts `/45` (UA/UB) |

`city_limits` ALPHA names (9): TARBORO, SHARPSBURG, ROCKY MOUNT, PINETOPS, PRINCEVILLE, WHITAKERS, CONETOE, LEGGETT, MACCLESFIELD.

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `linkpin` (PA/map); `parcel` (hyphen display); `pin`; OneMap `parno`≈parcel / `altparno`≈pin | linkpin = 12-digit no hyphens |
| polygons | Yes | webmap/MapServer/10 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `acreage` | ~**4,259** in 5–150 |
| ownerName | Yes | `owner` / OneMap `ownname` | Public on REST — no phones/emails |
| mailing address | Yes | `address`,`city`,`st`,`zip` | |
| situs address | Yes | `location`; OneMap `siteadd`; Address Points spatial | ~31,540 location present |
| lastSale date/price | Yes | `deeddate`/`deeddatestr`,`salepr`,`bk_pg` | Last sale on parcel |
| tax values | Yes | `landval`,`bldgval`,`netval`,`deferred` | |
| zoning | Yes (cities-first) | Per-muni layers; parcel `zone` (~11.5k non-null, mixed/noisy) | Spatial join preferred |
| flu | Partial (coarse) | Land Use Districts `ALPHA` UA/UB only | **FLU gap** — no detailed FLUM |
| dorCode / land use | Partial | `pclass`,`propdescr` | Local |
| appraiser / viewer link | Yes | taxpa `pKEY={linkpin}`; map `?PIN={linkpin}`; NCPTS `{parcel}` | Tranche-3 OK |

## Layers (verified)

### 1. webmap Parcels — PRIMARY

- **Purpose:** parcels | tax | ownership | sales (last)
- **REST URL:** https://gis.edgecombecountync.gov/arcgis/rest/services/webmap/MapServer/10
- **Geometry:** Polygon | **CRS:** 102719 / 2264 | **MaxRecordCount:** 1000
- **Key fields → targets:** `linkpin`→parcelIdPa; `parcel`→parcelIdDisplay; `pin`/`pinsuf`→pin parts; `acreage`→acreage; `owner`→owner; `address`/`city`/`st`/`zip`→mailing; `location`→situs; `deeddate`/`deeddatestr`/`salepr`/`bk_pg`→lastSale; `landval`/`bldgval`/`netval`/`deferred`→tax; `zone`→zoning stub; `taxcodes`→taxDistricts; `account`→account; `altpin`→altId; `pclass`→propClass; `propdescr`→legalDescription
- **Verified:** count **31,606**; acreage 5–150 → **4,259**; salepr>0 → **14,564**; salepr>0 in 5–150 → **1,445**; bldgval=0/null in 5–150 → **2,559**; location present **31,540**; zone not null **11,504**
- **Notes:** PRIMARY. Paginate (max 1000). Sample: parcel `3747-72-3650` / pin `3747723650` / linkpin `374772365000` / account `168057` (ATKINS JUNE G, 120 E MAIN ST). Geo-check linkpin `374783367400` ≈ **-77.824, 35.870** (Rocky Mount tip). `webmap/FeatureServer` not queryable — use MapServer.

### 2. Address Points — situs spatial join

- **REST URL:** https://gis.edgecombecountync.gov/arcgis/rest/services/webmap/MapServer/5
- **Geometry:** Point | count **33,175**
- **Fields:** `FULLADD`,`ADDRESS`,`SNAME`,`STYPE`,`CITY`,`ZIP`, … — **no PIN/parcel join key**; spatial join only
- **Notes:** Prefer parcel `location` / OneMap `siteadd` when present

### 3. NC OneMap Parcels (fallback)

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='065'`
- **Alternate host:** `services.gis.nc.gov`
- **Verified:** count **31,591**; gisacres 5–150 → **4,249**
- **Notes:** `parno` tracks `parcel`; `altparno` tracks `pin`; has `siteadd` on polys; no sale price. MaxRecordCount 5000.

### 4. Tarboro Zoning — city-first PRIMARY (county seat)

- **REST URL:** https://gis.edgecombecountync.gov/arcgis/rest/services/webmap/MapServer/15
- **Count:** **96** | field `ALPHA`
- **Top codes:** HB 19, GR10 12, HI 12, GR3 11, O&I 11, NB 10, GR5 9, RD 6, LI 2, MHP 2, CBD 1, HO 1

### 5. Rocky Mount Zoning — city-first (Edgecombe tip)

- **REST URL:** https://gis.edgecombecountync.gov/arcgis/rest/services/webmap/MapServer/16
- **Count:** **144** | field `ZONING` (many split codes, e.g. `A-1 & R-10`)
- **Nash-side PRIMARY (prefer for Nash parcels):** https://gis.nashcountync.gov/nashmaps/rest/services/PUBLIC/Avineon_WebTemplate/MapServer/72 (2972, `ZONING`)
- **Viewer:** https://map.viewprogis.com/vp/rockymount-nc

### 6. Other municipal zoning (county-host, cities-first)

| Layer | Muni | Count | Field |
|-------|------|-------|-------|
| 13 | Sharpsburg | 167 | Zone |
| 14 | Leggett | 82 | ALPHA |
| 17 | Pinetops | 21 | ALPHA |
| 18 | Princeville | 7 | ALPHA |
| 19 | Macclesfield | 10 | ALPHA |
| 20 | Conetoe | 12 | ALPHA |

Base URL pattern: `https://gis.edgecombecountync.gov/arcgis/rest/services/webmap/MapServer/{id}`

### 7. County Zoning (unincorporated PRIMARY)

- **REST URL:** https://gis.edgecombecountync.gov/arcgis/rest/services/webmap/MapServer/23
- **Parent group:** County Zoning `/21` (sublayers ETJ/22 + Zoning/23)
- **Count:** **175** | field `ALPHA`
- **Top codes:** B-1 53, R-20 29, R-30 29, M-2 17, B-2 14, M-1 8, AR-30 6, R-10 6, O-I 4, TCO 3, …

### 8. Land Use Districts — county FLU (coarse only)

- **REST URL:** https://gis.edgecombecountync.gov/arcgis/rest/services/webmap/MapServer/45
- **Count:** **2** | field `ALPHA` → flu
- **Categories:** UA, UB only
- **Notes:** **Not a detailed FLUM** — treat as coarse urban-area overlay; no municipal FLU FeatureServers found

### 9. City Limits + ETJ + Speed overlay (routers)

- **City limits:** …/MapServer/35 | count **80** | `ALPHA`
- **ETJ:** …/MapServer/22 | count **7** | `ALPHA` = ROCKY MOUNT, TARBORO, LEGGETT, PINETOPS, SPEED, PRINCEVILLE, SHARPSBURG
- **Speed Community Overlay:** …/MapServer/57 | count **1** | `ALPHA`

### 10. Airport Zoning

- **REST URL:** …/MapServer/48 | count **0** (empty) — skip

## Gaps

- No independent Tarboro / Rocky Mount / town ArcGIS FeatureServers — county-host layers + Rocky Mount ViewPro only
- Rocky Mount Edgecombe tip (144) is incomplete vs Nash-side (2972) — always prefer Nash card Avineon_WebTemplate/72 inside Nash city limits
- Whitakers has city_limits but **no Edgecombe zoning layer** — use Nash Avineon_WebTemplate/75 for Nash-side
- **FLU gap:** Land Use Districts only UA/UB (2 polys); no detailed county/city FLUM REST
- Parcel `zone` attribute noisy/partial (~36% populated) — prefer spatial join to zoning layers
- Address Points lack PIN — spatial join only; prefer `location` / OneMap `siteadd`
- Keystone PA detail is **POST `pKEY={linkpin}`**; bare GET may show empty shell — search works with PIN `####-##-####-##`
- Last-sale only on parcel (no multi-transfer history layer)
- Sharpsburg / Whitakers / Rocky Mount span adjacent counties — clip to Edgecombe for this card
- MaxRecordCount **1000** — paginate; ParcelFabric/Hosted folders token-required (499); no phones/emails; no AADT/utilities; no paid vendors on this card

## License / verification

Edgecombe County public GIS + NC OneMap; public query endpoints; attribution recommended; no paid vendors. Shapefile downloads from Tax Assessor are fee-based — **not used** (REST is free).

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://gis.edgecombecountync.gov/arcgis/rest/services/webmap/MapServer/10 · id `linkpin` · live count **31,608** · 5–150 ac **4,257** (`acreage >= 5 AND acreage <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='EDGECOMBE'` gives **498** stations (56 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27EDGECOMBE%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Edgecombe'` gives **495** stations (401 with AADT_2025, 229 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Edgecombe%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `netval` non-zero **31,541**, `landval` non-zero **31,105**, `bldgval` non-zero **22,278**
- **Sale history (ok):** price `salepr` >0 **14,564**; date `deeddate` non-null **31,543**
- **Owner entity:** fields `owner`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **1,251** (all parcels: 6,623), using the SQL approximation on `owner`.
- **PA deep link:** `https://taxpa.edgecombecountync.gov/paas/?DEST=pDetail&pKEY={linkpin}`. Tested `374783367400` → HTTP **200** (text/html), content verified: False. GET returns 200 but an empty Keystone shell; POST pKEY={linkpin} to ?DEST=pDetail returns the owner (verified via curl POST). LSB: open via form POST, or fall back to NCPTS / map ?PIN=.
- **Jurisdiction GIS viewer:** https://gis.edgecombecountync.gov/maps/default.htm → HTTP **200** (Avineon Web Map Template)
- **Pass 2 gaps:** none
