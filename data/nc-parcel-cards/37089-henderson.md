# Henderson County, NC — GIS County Card

## Summary

Henderson County (Asheville MSA, FIPS **37089**) publishes a strong public GIS stack at `gisweb.hendersoncountync.gov`. **Wire-first parcels:** `Parcels/FeatureServer/0` — **71,350** polygons with owner, mailing, situs, `CALCULATED_ACRES` / `ACREAGE`, land/bldg/total assessed values, package + land sale price/date, and `Zoning_aggregated`. **~6,272** parcels with `CALCULATED_ACRES` 5–150 (~**3,511** with `HEATED_AREA` null/0). **CRITICAL:** `Zoning_aggregated` is often stub **"Cities"** inside municipalities — prefer city zoning polygons. **Zoning stack (county-hosted, city-first):** Hendersonville (Primary/83 or city AGOL `COH_Zoning_Test`, **413**), Fletcher (/80, **42**), Mills River (/81, **32**), Flat Rock (/79, **34**), Laurel Park+ETJ (/82, **12**), County Zoning (/85, **384**). **FLU:** county Future Land Use Map 2024 (Planning_and_Development/88, **354**) + Hendersonville 2045 Comp Plan FLU (city AGOL `Future_Land_Use`/16, **13,778** PIN-keyed). Fletcher / Mills River / Flat Rock / Laurel Park have **no dedicated public FLU REST** — use county FLU as fallback. **NC OneMap** (`cntyfips='089'`) fallback: **75,373** polys; `gisacres` 5–150 → **8,137**. Appraiser: NCPTS Henderson by `PARCEL_PK`.

## Portals

- **GISWeb viewer** — https://gisweb.hendersoncountync.gov/gisweb/
- **GIS Data Catalog** — https://www.hendersoncountync.gov/gis-layers
- **Real Property Data Download** — https://www.hendersoncountync.gov/gis/page/real-property-data-download-page-excel-text-files-0
- **County ArcGIS REST** — https://gisweb.hendersoncountync.gov/arcgis/rest/services
- **Property search (NCPTS)** — https://lrcpwa.ncptscloud.com/henderson/parcel-search
- **Deep link** — `https://lrcpwa.ncptscloud.com/henderson/parcel-detail/{PARCEL_PK}` (also `PropertySummary.aspx?PARCELPK=`)
- **Spatialest mirror** — https://property.spatialest.com/nc/henderson/
- **City of Hendersonville Zoning Experience** — https://experience.arcgis.com/experience/06a21cbde3ff411ea59a6f594dab7e51
- **Hendersonville AGOL Hub** — https://gis-hendersonville.hub.arcgis.com/
- **NC OneMap** — https://www.nconemap.gov

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `REID`, `PARCEL_PK`; OneMap `parno` | PIN primary; PARCEL_PK for NCPTS deep link |
| polygons | Yes | Parcels FS/0 | CRS **102100 / 3857** |
| acreage | Yes | `CALCULATED_ACRES`, `ACREAGE` | **6,272** in 5–150 (both fields) |
| ownerName | Yes | `PROPERTY_OWNER`; OneMap `ownname` | Public on REST — no phones/emails |
| mailing address | Yes | `OWNER_MAIL_1` + `OWNER_MAIL_CITY`/`STATE`/`ZIP` | |
| situs address | Yes | `LOCATION_ADDR` / `PHYADDR_*` | On primary parcel layer |
| lastSale date/price | Yes (latest) | `PKG_SALE_DATE`/`PRICE`, `LAND_SALE_*`, `DEED_DATE` | Latest package/land only — no multi-xfer FS |
| tax values | Yes | `TOTAL_LAND_VALUE_ASSESSED`, `TOTAL_BLDG_VALUE_ASSESSED`, `TOTAL_PROP_VALUE`; OneMap land/improv split | |
| zoning | Yes (city-split) | City layers 79–83 / AGOL; County/85; attr `Zoning_aggregated` | Attr stub "Cities" inside munis — spatial join required |
| flu | Yes (city-split) | County FLU 2024 /88; HVL `Future_Land_Use`/16 | No dedicated FLU REST for Fletcher/Mills River/Flat Rock/Laurel Park |
| appraiser / viewer link | Yes | NCPTS parcel-detail by PARCEL_PK; GISWeb | Templates below |

## Municipalities (first-class)

| Municipality | Parcel CITY ≈ | Zoning REST (prefer) | FLU | Join notes |
|--------------|---------------|----------------------|-----|------------|
| **Hendersonville** | HENDERSONVILLE (~7,583) | AGOL `COH_Zoning_Test` FS/0 **or** Primary/83 (**413**) | City AGOL `Future_Land_Use`/16 (**13,778** PIN-keyed) | Prefer city AGOL zoning+FLU inside limits; county `Zoning_aggregated`="Cities" stub |
| **Fletcher** | FLETCHER (~3,735) | Primary/80 (**42**) | **Gap** — county FLU/88 fallback | No town AGOL REST found; county hosts zoning |
| **Mills River** | MILLS RIVER (~4,445) | Primary/81 (**32**); field `CLASSIFICA` | **Gap** — county FLU/88 fallback | County-hosted only |
| **Laurel Park** | LAUREL PARK (~1,859) | Primary/82 (**12**) incl. ETJ districts | **Gap** — county FLU/88 fallback | County-hosted; ETJ R-20/R-30/TC/MM/I-1 |
| **Flat Rock (Village)** | FLAT ROCK VH/BR/GR (~821/1,781/214) | Primary/79 (**34**); field `ZONING` | **Gap** — county FLU/88 fallback | CITY VH/BR/GR are tax subtypes — route via ETJ=`FLAT ROCK` or MUNICIPAL BOUNDARIES/96 |
| **Saluda tip** | SALUDA (~16) | Not inventoried (mostly Polk) | n/a | Edge tip only |
| Unincorporated | CITY null (~50,896) | County Zoning Primary/85 | County FLU/88 | `ZONE_CODE` ≠ Cities |

**Municipal boundaries:** Primary_GISWeb_Layers/96 (**312** polys) — CITY: HENDERSONVILLE, FLETCHER, MILLS RIVER, LAUREL PARK, FLAT ROCK, SALUDA.

## Layers (verified)

### 1. Parcels — parcels + ownership + tax + situs + sale + Zoning_aggregated (PRIMARY)

- **REST URL:** https://gisweb.hendersoncountync.gov/arcgis/rest/services/Parcels/FeatureServer/0
- **Mirror:** Primary_GISWeb_Layers MapServer/19 (and /39)
- **Geometry:** Polygon | **CRS:** 102100 / 3857 | **MaxRecordCount:** 2000
- **Key fields → targets:** `PIN`→parcelId; `REID`; `PARCEL_PK` (NCPTS); `CALCULATED_ACRES`/`ACREAGE`→acreage; `PROPERTY_OWNER`; `OWNER_MAIL_*`; `LOCATION_ADDR` / `PHYADDR_*`; `PKG_SALE_DATE`/`PRICE`, `LAND_SALE_*`, `DEED_*`; `TOTAL_LAND_VALUE_ASSESSED`, `TOTAL_BLDG_VALUE_ASSESSED`, `TOTAL_PROP_VALUE`; `Zoning_aggregated`; `CITY`; `ETJ`; `LAND_CLASS`; `HEATED_AREA`; `DEED_URL`
- **Verified:** count **71,350**; `CALCULATED_ACRES` 5–150 → **6,272**; `HEATED_AREA` null/0 in range → **3,511**
- **Notes:** PRIMARY. Paginate. `Zoning_aggregated` often "Cities" inside munis — spatial-join city zoning.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='089'`
- **Fields:** `parno`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`/`scity`, `gisacres`, `saledate`/`saledatetx`, `parval`/`landval`/`improvval`
- **Verified:** count **75,373**; `gisacres` 5–150 → **8,137**; `improvval`=0/null in range → **2,573**
- **Notes:** No sale price. Acre counts differ from county — prefer county `CALCULATED_ACRES` for site filter.

### 3. Zoning stack (city-first)

| Layer | URL | Count | Zoning field |
|-------|-----|-------|--------------|
| Hendersonville (AGOL, prefer) | `services1.arcgis.com/UTZTmZoX2rsa9yFA/.../COH_Zoning_Test/FeatureServer/0` | 413 | `Zoning`, `Zoning_Cla` |
| Hendersonville (county host) | Primary_GISWeb_Layers/83 | 413 | `Zoning`, `Zoning_Cla` |
| Fletcher | Primary_GISWeb_Layers/80 | 42 | `Zoning` |
| Mills River | Primary_GISWeb_Layers/81 | 32 | `CLASSIFICA` |
| Flat Rock | Primary_GISWeb_Layers/79 | 34 | `ZONING` |
| Laurel Park + ETJ | Primary_GISWeb_Layers/82 | 12 | `Zone` |
| County Zoning | Primary_GISWeb_Layers/85 | 384 | `ZONE_CODE`, `ZONING` |

MapMetrics mirrors: Tax/Data_for_MapMetrics/MapServer/22–27.

### 4. FLU

- **County Future Land Use Map (2024):** GISWeb/Planning_and_Development/MapServer/88 — fields `FLU`, `Land_Use`; count **354**. Codes: AR, TA, IA, OSC, EMP, NEIGHBORHOOD, COMMUNITY.
- **Hendersonville 2045 Comp Plan FLU:** `.../Future_Land_Use/FeatureServer/16` — `PIN`, `FLU`, `ACREAGE`; count **13,778**. Prefer inside city.
- **HendersonCountyLandUse FS/0:** existing-use / ML prediction on parcels (**70,637**) — **not** Comp Plan FLU; enrichment only.
- **Urban Growth Boundary:** Planning_and_Development/87 (**9** polys).

### 5. Sales

- Latest package/land sale on Parcels FS (`PKG_SALE_*`, `LAND_SALE_*`). No multi-transfer Sales FeatureServer verified. Optional county Sales TXT download (non-REST).

## Deep-link patterns

- NCPTS search: `https://lrcpwa.ncptscloud.com/henderson/parcel-search`
- NCPTS detail: `https://lrcpwa.ncptscloud.com/henderson/parcel-detail/{PARCEL_PK}`
- Alt: `https://lrcpwa.ncptscloud.com/henderson/PropertySummary.aspx?PARCELPK={PARCEL_PK}`
- GISWeb: https://gisweb.hendersoncountync.gov/gisweb/
- Deed: `DEED_URL` field on parcel (Courthouse Computer Systems)

## Gaps

- `Zoning_aggregated` "Cities" stub inside munis — must join city zoning polygons
- No dedicated public FLU REST for Fletcher, Mills River, Flat Rock, Laurel Park
- No multi-transfer sales FeatureServer
- OneMap vs county acre-count mismatch (prefer county)
- Flat Rock CITY VH/BR/GR tax subtypes — use ETJ / municipal boundary
- Saluda tip mostly Polk
- HendersonCountyLandUse ≠ Comp Plan FLU
- No paid vendor data; no phones/emails collected

## License / verification

- License: Henderson County IT/GIS public ArcGIS REST; City of Hendersonville AGOL; NC OneMap; NCGS disclaimer; attribution recommended
- **verifiedAt:** 2026-09-23
- **verifiedBy:** North Carolina Public Info Researcher
