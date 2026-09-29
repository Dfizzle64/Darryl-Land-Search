# Halifax County, NC — GIS County Card

## Summary

Halifax County (Rocky Mount / RDU shed, FIPS **37083**, slug **halifax**) has **no county-hosted ArcGIS REST root**. Wire-first **countywide tax parcels** from Roanoke Rapids AGOL **`OpenGov_RR_Layers/FeatureServer/22` — Halifax_County_Parcels** (~**39,355**; ~**6,461** with `ACREAGE` 5–150) with owner, mailing, situs (`PARCEL_ADD`), last sale price/date, and assessed values. Prefer **`PARID`** (e.g. `0106888`) for NCPTS / qPublic `KeyValue`; display PIN **`PIN83`/`APN`** (`####-##-##-####`). **Zoning is cities-first:** **Roanoke Rapids** dedicated FS `Roanoke_Rapids_Zoning2_(2)/0` (~**9,083**, `ZONE`) plus overlays (Entertainment, Historic, Cross Creek PUD, ETJ). Weldon / Enfield / Scotland Neck / Town of Halifax / Littleton / Hobgood — **no municipal zoning REST**. County unincorporated Official Zoning Map exists (ordinance) but **no public FeatureServer**. **FLU:** Comp Land Use & Recreation Plan PDF/in-progress only — **gap**. **NC OneMap** (`cntyfips='083'`, ~**39,403**) is a solid geometry/owner fallback (prefer OpenGov for sale/tax splits). Markets: **Rocky Mount / RDU shed**.

## Portals

- **Map viewer (jurisdiction GIS URL / qPublic)** — https://qpublic.schneidercorp.com/Application.aspx?AppID=872&LayerID=16488&PageTypeID=1&PageID=7289
- **Property search (qPublic)** — https://qpublic.schneidercorp.com/Application.aspx?AppID=872&LayerID=16488&PageTypeID=2&PageID=7290
- **PA deep-link (qPublic detail)** — `https://qpublic.schneidercorp.com/Application.aspx?AppID=872&LayerID=16488&PageTypeID=4&PageID=7291&KeyValue={PARID}` (alt `{PIN83}`)
- **qPublic gateway** — http://qpublic.net/nc/halifax/ → halifaxnctax.com
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/halifax/parcel-search
- **NCPTS deep-link (preferred PA)** — `https://lrcpwa.ncptscloud.com/halifax/parcel-detail/{PARID}`
- **County GIS downloads / Tax Admin GIS** — https://halifaxnctax.com/geographic-information-system/
- **Tax Administration** — https://www.halifaxnc.com/226/Tax-Administration
- **Tax portal** — https://halifaxnctax.com/
- **Planning & Zoning** — https://www.halifaxnc.com/152/Planning-Zoning
- **Comp Land Use & Recreation Plan** — https://www.halifaxnc.com/449/Halifax-County-Comprehensive-Land-Use-an
- **Roanoke Rapids Planning** — https://roanokerapidsnc.gov/roanoke-rapids-city-departments/planning-and-development.html
- **Roanoke Rapids Zoning Map** — https://roanokerapidsnc.gov/zoning-map.html
- **County / RR ArcGIS REST (AGOL)** — https://services8.arcgis.com/0zS9csrI5fS6Bcym/arcgis/rest/services
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='083'`; alt `services.gis.nc.gov`)

## Municipalities (first-class)

| Municipality | Local public GIS? | Zoning / FLU source |
|--------------|-------------------|---------------------|
| **Roanoke Rapids** (largest) | City AGOL (PlanningRR27870) | **CITY-FIRST PRIMARY** `Roanoke_Rapids_Zoning2_(2)/0` (9083, `ZONE`). Alt OpenGov/14. Overlays Entertainment/12, Historic, Cross Creek PUD/11, ETJ/19. FLU: none on REST |
| Weldon | None found | **Zoning REST gap** |
| Enfield | None found | **Zoning REST gap** |
| Scotland Neck | None found | **Zoning REST gap** |
| Halifax (town / seat) | None found | **Zoning REST gap** |
| Littleton | None found | **Zoning REST gap** |
| Hobgood | None found | **Zoning REST gap** |
| Whitakers (tip) | Prefer Nash/Edgecombe | Nash Avineon/75; Edgecombe city_limits — clip |
| Unincorporated | County Planning | Official Zoning Map (ordinance) — **no public FS**; FLU Comp Plan PDF gap |

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PARID` (PA); `PIN83`/`APN`; OneMap `parno`↔PARID / `altparno`↔PIN83 | Prefer PARID |
| polygons | Yes | OpenGov/22; OneMap FS/1 | AGOL **102100/3857**; OneMap **102719/2264** |
| acreage | Yes | `ACREAGE` (prefer); `CALC_ACRE`; OneMap `gisacres`/`recareano` | ~**6,461** in 5–150 |
| ownerName | Yes | `CURRENT_OW` / OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `CURRENT_AD`/`CURRENT_CI`/`CURRENT_ST`/`CURRENT_ZI` | |
| situs address | Yes | `PARCEL_ADD`; OneMap `siteadd`; RR `LOCATION` | |
| lastSale date/price | Yes | `SALE_PRICE`,`DATE_RECOR`,`BK_PG` | OneMap sale empty — prefer OpenGov |
| tax values | Yes | `ASSESSED_V`,`TOTAL_TAX_`,`LAND_TAX_D`; OneMap `parval` | OneMap landval/improvval empty |
| zoning | Yes (cities-first RR) | RR `ZONE`; county map gap | Spatial join inside RR limits |
| flu | Gap | Comp Plan PDF | No FLUM FS |
| dorCode / land use | Partial | RR `LUC`; `PARCEL_CLA`/`USE_DESC` | Local |
| appraiser / viewer link | Yes | NCPTS `{PARID}`; qPublic `KeyValue={PARID}` | Tranche-3 OK |

## Layers (verified)

### 1. OpenGov Halifax_County_Parcels — PRIMARY

- **Purpose:** parcels | tax | ownership | sales (last)
- **REST URL:** https://services8.arcgis.com/0zS9csrI5fS6Bcym/arcgis/rest/services/OpenGov_RR_Layers/FeatureServer/22
- **Geometry:** Polygon | **CRS:** 102100 / 3857 | **MaxRecordCount:** 2000
- **Key fields → targets:** `PARID`→parcelId; `PIN83`/`APN`→PIN; `ACREAGE`→acreage; `CURRENT_OW`→owner; `CURRENT_*`→mailing; `PARCEL_ADD`→situs; `SALE_PRICE`/`DATE_RECOR`/`BK_PG`→lastSale; `ASSESSED_V`/`TOTAL_TAX_`/`LAND_TAX_D`→tax; `PARCEL_CLA`→propClass
- **Verified:** count **39,355**; ACREAGE 5–150 → **6,461**; SALE_PRICE>0 → **14,325**; sale in band → **1,763**; APPRAISED blank in band (vacantish proxy) → **4,438**; CURRENT_OW **39,103**; PARCEL_ADD **39,094**
- **Notes:** PRIMARY. Paginate (max 2000). Sample: PARID `0106888` / PIN83 `2898-00-99-7502` ≈ **-77.984, 36.190**. RR-only mirrors: layers 21/23 (~8.8k).

### 2. NC OneMap Parcels (fallback)

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='083'`
- **Alternate host:** `services.gis.nc.gov`
- **Verified:** count **39,403**; gisacres 5–150 → **6,332**; recareano 5–150 → **6,489**; ownname **39,403**; parval>0 **39,176**; siteadd **39,166**
- **Notes:** `parno`↔PARID; `altparno`↔PIN83. No sale price/date; landval/improvval empty — join OpenGov for CAMA sale/tax splits. MaxRecordCount 5000.

### 3. Roanoke Rapids Zoning2 — city-first PRIMARY

- **REST URL:** https://services8.arcgis.com/0zS9csrI5fS6Bcym/arcgis/rest/services/Roanoke_Rapids_Zoning2_(2)/FeatureServer/0
- **Count:** **9,083** | field `ZONE` | CALC_ACRE 5–150 → **242** | SALE_PRICE>0 → **3,978**
- **Top codes:** R-8 2618, R-6 2391, R-12 1137, R-20 843, B-4 689, B-1 261, R-40 258, B-3 221, R-3 220, B-2 156, R-5 82, I-2 67, I-1 10, B-5 7
- **Also carries:** owner/sale/tax/LUC on parcelized polygons — usable CAMA inside RR
- **Alternate:** OpenGov `RR_Current_Zoning` /14 (9079)

### 4. RR overlays + limits (routers)

| Layer | REST | Count |
|-------|------|-------|
| Entertainment Overlay | OpenGov/12 (also standalone Entertainment_Overlay_District) | ~68 / 66 |
| Historic District | Roanoke_Rapids_Historic_District/0 | 1 |
| Cross Creek PUD | OpenGov/11 | 128 |
| City Limits | OpenGov/18 | 6 |
| ETJ | OpenGov/19 | 3 |
| City+ETJ | OpenGov/20 | 1 |

### 5. County zoning + FLU — gaps

- **County Official Zoning Map:** ordinance applies to designated unincorporated areas only — **no public FeatureServer**
- **FLU:** https://www.halifaxnc.com/449/Halifax-County-Comprehensive-Land-Use-an — Steering Committee PDF DocumentCenter/View/5026 (2025-09-25); **no FLUM REST**
- **Shapefile downloads (offline):** https://halifaxnctax.com/geographic-information-system/ — 2025 final / 2026 interim Tax Parcels (+ Excel assessment); free; Cloudflare may block bots

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS map | https://qpublic.schneidercorp.com/Application.aspx?AppID=872&LayerID=16488&PageTypeID=1&PageID=7289 |
| qPublic search | https://qpublic.schneidercorp.com/Application.aspx?AppID=872&LayerID=16488&PageTypeID=2&PageID=7290 |
| qPublic detail | `…PageTypeID=4&PageID=7291&KeyValue={PARID}` (alt `{PIN83}`) |
| NCPTS detail (preferred) | `https://lrcpwa.ncptscloud.com/halifax/parcel-detail/{PARID}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/halifax/parcel-search |

Example: PARID `0106888` → https://lrcpwa.ncptscloud.com/halifax/parcel-detail/0106888 (SPA HTTP 200 verified).

## Gaps

- No Halifax County ArcGIS Server root — depend on RR AGOL + OneMap + qPublic
- Unincorporated Official Zoning Map — **REST gap** (ordinance only)
- Weldon / Enfield / Scotland Neck / Halifax / Littleton / Hobgood — **zoning REST gaps**
- **FLU gap** — Comp Plan PDF/in-progress; no FLUM FeatureServer
- OneMap sale + land/improvement value fields weak for Halifax — prefer OpenGov/22
- qPublic / halifaxnctax.com Cloudflare-challenged from automated clients
- Last-sale only on parcel (no multi-transfer history layer)
- MaxRecordCount **2000** — paginate; no phones/emails; no AADT/utilities; no paid vendors

## License / verification

Halifax County + City of Roanoke Rapids public GIS + NC OneMap; free shapefile downloads; attribution recommended; no paid vendors.

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** OpenGov/22 count 39355 + ACREAGE band + SALE_PRICE; RR Zoning2/0 ZONE histogram; OneMap `cntyfips='083'` 39403; NCPTS search/detail SPA 200; qPublic AppID=872 URLs documented; Planning/Tax portals 200; geo-check PARID 0106888 ≈ -77.984, 36.190
