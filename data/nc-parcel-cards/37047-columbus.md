# Columbus County, NC — GIS County Card

## Summary

Columbus County (Wilmington MSA, FIPS **37047**, slug **columbus**) has **no county-hosted ArcGIS FeatureServer**. Wire parcels from **NC OneMap** (`cntyfips='047'`, ~**51,709** polys) joined to the county **taxdata.xls** CAMA export (~**53,516** rows) on `parno`=`GPIN`. OneMap **`gisacres` is broken** here — use `Shape__Area/43560` (~**12,081** in 5–150 ac) or prefer taxdata **`GACRE`** (~**12,238** in 5–150). Tax/sale/owner are strong on taxdata (`GTOTVL`, `GSLAMT`/`GSLDTE`, `GNAME`). **Zoning is cities-first** on MangoMap (`jurisdicti` + `zoning`, ~**1,619** polys) — Whiteville, Tabor City, etc. **FLU** is CLUP PDF only (REST gap). **PA deep-link:** `https://www2.columbusco.org/prc/pid{GSEQ:06d}.pdf`. **Jurisdiction GIS:** MangoMap Land Records.

## Portals

- **County GIS** — https://www.columbusco.org/gis
- **Land Records viewer (jurisdictionGisUrl)** — https://mangomap.com/columbusmis/maps/16952/land-records-
- **Zoning viewer** — https://mangomap.com/columbusmis/maps/20702/zoning
- **Maps portal** — https://mangomap.com/columbusmis/maps
- **Tax data export** — https://www2.columbusco.org/gisdata/taxdata.xls
- **Tax Office** — https://www.columbusco.org/tax-office
- **Planning** — https://www.columbusco.org/planning-department
- **Land Use Regulation Ordinance (PDF)** — https://www.columbusco.org/sites/default/files/uploads/planning/land-use-regulation-ordinance.pdf
- **CLUP (FLU PDF)** — https://www.columbusco.org/sites/default/files/uploads/planning/clup.pdf
- **NC OneMap ArcGIS REST** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='047'`)
- **PRC deep-link** — `https://www2.columbusco.org/prc/pid{GSEQ:06d}.pdf`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | OneMap `parno` / taxdata `GPIN`; prop `altparno`/`GSEQ` | Same PIN format e.g. `0263.00-95-7227.000` |
| polygons | Yes | OneMap FS/1 | CRS **102719 / 2264** |
| acreage | Yes | taxdata `GACRE` (prefer); OneMap `Shape__Area/43560` | Do **not** use OneMap `gisacres` |
| ownerName | Yes | `GNAME` / `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `GADD*`/`GCTYST`/`GZIPCD`; OneMap `mailadd`/`mcity`… | |
| situs address | Yes | `TXSADD`/`TXSCTY`/`TXSZIP`; OneMap `siteadd` | |
| lastSale date/price | Yes | `GSLDTE`/`GSLAMT` | OneMap has date only (no price) |
| tax values | Yes | `GTOTVL`/`TVLAND`/`GTLUVL`; OneMap `landval`/`improvval` | Prefer taxdata for market total |
| zoning | Yes (viewer) | MangoMap `zoning` + `jurisdicti` | Cities-first; no ArcGIS FS |
| flu | Gap | CLUP PDF | No FeatureServer |
| appraiser / viewer link | Yes | PRC `{GSEQ:06d}`; MangoMap Land Records | TRANCHE-3 |

### CITY codes (taxdata GCICOD → zoning router)

| GCICOD | Municipality | Approx parcels | Zoning source |
|--------|--------------|----------------|---------------|
| *(blank)* | Unincorporated | 40,172 | MangoMap `jurisdicti` Columbus County / General Use |
| WH | **Whiteville** | 4,047 | MangoMap `jurisdicti=Whiteville` (city-first) |
| SW | **Tabor City** | 2,691 | `jurisdicti=Tabor City` |
| WA | **Lake Waccamaw** | 2,026 | `jurisdicti=Lake Waccamaw` |
| CH | **Chadbourn** | 1,660 | `jurisdicti=Chadbourn` |
| FB | **Fair Bluff** | 973 | `jurisdicti=Fair Bluff` |
| BO | **Bolton** | 622 | `jurisdicti=Bolton` |
| SF | **Sandyfield** | 517 | `jurisdicti=SandyField` |
| BR | **Brunswick** (town) | 352 | `jurisdicti=Brunswick` |
| BD | **Boardman** | 243 | `jurisdicti=Boardman` |
| CG | **Cerro Gordo** | 213 | `jurisdicti=Cerro Gordo` |

## Layers (verified 2026-09-24)

### 1. NC OneMap Parcels — PRIMARY ArcGIS REST geometry

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='047'`
- **Alternate:** `services.gis.nc.gov` same path; MapServer/1
- **Key fields:** `parno`→parcelId; `altparno`→GSEQ/prop id; `ownname`; mail/site; `landval`/`improvval`/`parval`; `saledate`; **acreage = Shape__Area/43560**
- **Verified:** count **51,709**; Shape__Area 5–150 → **12,081**; landval>0 **51,080**; ownname **51,091**
- **Notes:** `gisacres` unusable for Columbus. Join to taxdata on `parno`=`GPIN`.

### 2. taxdata.xls — PRIMARY CAMA (tax / sale / owner)

- **URL:** https://www2.columbusco.org/gisdata/taxdata.xls (TABLE format despite .xls)
- **Key fields:** `GPIN`, `GSEQ`, `GACCT`, `GNAME`, `GACRE`, `GTOTVL`, `TVLAND`, `GSLAMT`, `GSLDTE`, `GCICOD`, `GPURL`, `GDURL`, `GSURL`, situs `TXS*`
- **Verified:** **53,516** rows; GACRE 5–150 → **12,238**; GSLAMT>0 → **19,025**; GTOTVL>0 → **53,478**

### 3. MangoMap Land Records — jurisdiction GIS viewer

- **URL:** https://mangomap.com/columbusmis/maps/16952/land-records-
- **Parcels layer id:** `83a6893c-d6aa-11e7-af3f-06765ea3034e` — count **57,075**
- **Notes:** Identify popup exposes propid/owner/acres/gpurl. Not a FeatureServer.

### 4. MangoMap Zoning — cities-first

- **URL:** https://mangomap.com/columbusmis/maps/20702/zoning
- **Fields:** `jurisdicti`, `zoning`
- **Verified:** count **1,619**

### 5. City / Town Limits

- **URL:** https://mangomap.com/columbusmis/maps/22030/cities-and-districts
- **Verified:** count **28**

### 6. FLU — gap (CLUP PDF)

- https://www.columbusco.org/sites/default/files/uploads/planning/clup.pdf

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS viewer | https://mangomap.com/columbusmis/maps/16952/land-records- |
| Property card by prop id | `https://www2.columbusco.org/prc/pid{GSEQ:06d}.pdf` (OneMap `altparno`) |
| Tax statement | `https://www2.columbusco.org/statements/{GACCT compact}.txt` |
| County GIS hub | https://www.columbusco.org/gis |

Example: GSEQ `102` → https://www2.columbusco.org/prc/pid000102.pdf (HTTP 200 PDF verified).

## Gaps

- No county ArcGIS FeatureServer for parcels or zoning
- OneMap `gisacres` broken; `parval` incomplete; no sale price on OneMap
- FLU FeatureServer gap (CLUP PDF only)
- No separate Whiteville/town zoning or FLU FeatureServers
- MangoMap per-feature GeoJSON only (no bulk REST)
- Utilities / AADT intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** OneMap `cntyfips='047'` counts + Shape__Area acreage + GPIN/altparno join sample; full taxdata.xls parse (53516); MangoMap map_config + feature counts; PRC PDF 200; GIS/planning portals 200


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 · id `altparno` · live count **51,709** · 5–150 ac **12,081** (`Shape__Area BETWEEN 217800 AND 6534000`) · county filter `cntyfips='047'`
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='COLUMBUS'` gives **589** stations (325 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27COLUMBUS%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Columbus'` gives **596** stations (404 with AADT_2025, 316 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Columbus%27&outFields=LocationID,Located_On,Crossroad,County,AADT_2025,AADT_2024,Latitude,Longitude&returnGeometry=true&outSR=4326&f=json
- **AADT 2024 stations service:** `County='Columbus'` gives **592** stations, all with AADT_2024. Use AADT_2025 → AADT_2024 → AADT_2022.
- **Tax values (ok-via-download):** `parval` non-zero **18,709**, `landval` non-zero **51,080**, `improvval` non-zero **24,914**. OneMap parval only partial (landval near-complete). Authoritative values in county taxdata export (DIF format despite .xls): GTOTVL>0 53482 / TVLAND; join GPIN↔OneMap parno. Alt: https://www2.columbusco.org/gisdata/taxdata.xls
- **Sale history (ok-via-download):** date `saledate` non-null **51,709**. Not on REST except OneMap saledate (populated but unreliable as sale). Use taxdata export GSLAMT (price) / GSLDTE (date MM/DD/YYYY): GSLAMT>0 19027, GSLDTE non-blank 53520. Deed image GDURL.
- **Owner entity:** fields `ownname`, `ownname2`. Rule: uppercase + trim, regex `\b(LLC|INC|CORP|LP|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on 5–150 ac parcels **1,826** of 12,081 (extended regex: 2,028).
- **PA deep link:** `https://www2.columbusco.org/prc/pid{GSEQ6}.pdf`. Tested `099803` → HTTP **200** (application/pdf), content verified: True. Returns application/pdf property/appraisal card; parcel verified in PDF text. {GSEQ6} = taxdata GSEQ (≈ OneMap altparno) zero-padded to 6.
- **Jurisdiction GIS viewer:** https://mangomap.com/columbusmis/maps/16952/land-records- → HTTP **200** (Land Records  - Interactive Web Map)
- **Pass 2 gaps:** Parcel REST is NC OneMap only (gisacres broken → Shape__Area/43560); sale price and full values from taxdata DIF export, not REST
