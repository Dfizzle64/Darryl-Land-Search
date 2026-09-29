# Carteret County, NC — GIS County Card

## Summary

Carteret County (Eastern NC / Crystal Coast, FIPS **37031**, slug **carteret**, `cntyfips='031'`) publishes public ArcGIS REST at `arcgisweb.carteretcountync.gov`. **Wire-first parcels:** **Layers/Parceldata** FeatureServer/0 — **64,284** polygons with owner, mailing, situs, GIS/deeded/legal acres, last sale price/date + qualified flag, and full EMV split (land/structure/other/total). **~3,466** with `GISacres` 5–150 (~**2,253** structure 0/null; ~**931** `SALE_PRICE>0`; ~**426** `IsQualified=1`). **Cities-first zoning:** Morehead City AGOL Zoning FS (**8,584**), county-hosted Newport (**205**) + Emerald Isle (**8** district polys), county Zoning (**466**) for unincorporated. **FLU:** Morehead City Future_Land_Use FS (**10,393**, join on `PIN15`); county CAMA LUP / Map 8.1B **PDF only**. Beaufort + Atlantic Beach / Pine Knoll Shores / Indian Beach / Cape Carteret / Cedar Point / Bogue / Peletier — **no public zoning FeatureServer** (Beaufort PDF map). **PA:** BI-Tek ITSPublicCE AppraisalCard PDF `{PIN15}` + BasicSearch + NCPTS `{PIN15}`. Markets: **[Eastern NC, Crystal Coast]**.

## Portals

- **Public GIS viewer (jurisdictionGisUrl)** — https://arcgisweb.carteretcountync.gov/maps/
- **Open GIS data** — https://gisdata-cc-gis.opendata.arcgis.com/
- **GIS Services (county)** — https://www.carteretcountync.gov/469/GIS-Services
- **Mapping / GIS Data** — https://www.carteretcountync.gov/2405/Mapping-GIS-Data
- **County ArcGIS REST** — https://arcgisweb.carteretcountync.gov/arcgis/rest/services
- **Tax Administration** — https://www.carteretcountync.gov/158/Tax-Administration
- **2025 Reappraisal** — https://www.carteretcountync.gov/1150/2025-General-Reappraisal
- **PA Basic Search (ITSPublicCE)** — https://bttaxpayerportal.com/ITSPublicCE/BasicSearch
- **PA deep-link (PIN15)** — `https://bttaxpayerportal.com/ITSPublicCE/BasicSearch/Parcel?id={PIN15}`
- **Appraisal card PDF** — `https://bttaxpayerportal.com/ITSPublicCE/AppraisalCard.aspx?id={PIN15}`
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/carteret/
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/carteret/parcel-detail/{PIN15}`
- **Morehead City Maps** — https://moreheadcitync.gov/225/Maps
- **Morehead City Zoning Experience** — https://experience.arcgis.com/experience/97c1a63a2169477c9541581a4045342a
- **Morehead City NPA / FLU Experience** — https://experience.arcgis.com/experience/cbe053a9adbe4dfc81acf1ff328f2576
- **Town of Beaufort Zoning Map** — https://www.beaufortnc.org/planninginspections/page/town-beaufort-zoning-map
- **County CAMA LUP FLU map (PDF)** — https://www.carteretcountync.gov/DocumentCenter/View/137/MAP-81B-62207
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`) filter `cntyfips='031'`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN15`; `GISPIN`; OneMap `parno` | Prefer **PIN15** (15-digit); PA AppraisalCard uses same |
| polygons | Yes | Layers/Parceldata FS/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `GISacres`, `DeededAcres`, `LegalAcres`, `CalculatedLandUnits` | **3,466** GIS 5–150 |
| ownerName | Yes | `OWNER` / `OWNER2`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `MAIL_ADDRESS1`/`2`, `MAIL_CITY`, `MAIL_STATE`, `MAIL_ZI5`; `FullMailingAddress` | |
| situs address | Yes | `PropertyAddress`; `SITE_HOUSE`+`SITE_ST`+`SITE_STTYP`+`SITE_CITY` | |
| lastSale date/price | Yes | `SALE_PRICE`, `SaleDate`, `IsQualified`, `SaleImprovedOrVacant`; deed `DBOOK`/`DPAGE`/`DeedDate_2` | **931** sale>0 in 5–150; **426** qualified in band |
| tax values | Yes | `Total_EMV`, `LAND_VALUE`, `STRUC_VAL`, `OTHER_VAL` | On PRIMARY FS; OneMap `parval`/`landval`/`improvval` |
| zoning | Yes (cities-first) | MHC `ZONING`; Newport `ZONE`; EI `Zone`; county `Zone` | Beaufort+beach towns REST gap |
| flu | Partial | MHC `FLU`/`F_LandUse` on PIN15; county CAMA PDF | County FLU FeatureServer **gap** |
| appraiser / viewer link | Yes | AppraisalCard `{PIN15}`; BasicSearch; NCPTS; GIS maps | TRANCHE-3 |

### MUNICIPALITY parcel counts (Parceldata)

| MUNICIPALITY | Count | Zoning source |
|--------------|------:|---------------|
| *(null / blank)* | ~23,493 | County `Layers/Zoning` (unincorp) |
| Emerald Isle | 7,516 | County `Emerald_Isle_Zoning` (coarse, 8 polys) |
| Morehead City | 6,716 | **MHC AGOL Zoning** (city-first) |
| Morehead City ETJ | 3,755 | MHC Zoning / county |
| Atlantic Beach | 5,108 | **REST gap** |
| Beaufort | 4,422 | **REST gap** (town zoning map page) |
| Beaufort ETJ | 865 | gap / county |
| Pine Knoll Shores | 2,445 | REST gap |
| Newport | 1,985 | County `Newport_Zoning` (city-first) |
| Newport ETJ | 2,261 | Newport / county |
| Cape Carteret | 1,619 | REST gap |
| Cedar Point | 1,510 | REST gap |
| Indian Beach | 1,241 | REST gap |
| Peletier | 748 | REST gap |
| Bogue | 494 | REST gap |

## Layers (verified 2026-09-24)

### 1. Layers/Parceldata — PRIMARY CAMA parcels

- **Purpose:** parcels | ownership | tax | sales | situs
- **REST URL:** https://arcgisweb.carteretcountync.gov/arcgis/rest/services/Layers/Parceldata/FeatureServer/0
- **MapServer twin:** …/Layers/Parceldata/MapServer/0
- **Also:** Website/Parcel_Map_Beta/FeatureServer/0 (same ~64,284 schema)
- **Geometry:** Polygon — CRS **102719 / 2264**
- **Key fields → targets:**
  - `PIN15` → parcelId (PA key)
  - `GISPIN` → parcelIdAlt
  - `GISacres` / `DeededAcres` / `LegalAcres` → acreage
  - `OWNER`, `OWNER2` → ownerName
  - `MAIL_ADDRESS1`, `MAIL_CITY`, `MAIL_STATE`, `MAIL_ZI5` → mailing
  - `PropertyAddress`, `SITE_*` → situsAddress
  - `SALE_PRICE`, `SaleDate`, `IsQualified`, `SaleImprovedOrVacant` → lastSale
  - `Total_EMV`, `LAND_VALUE`, `STRUC_VAL`, `OTHER_VAL` → tax
  - `MUNICIPALITY` → jurisdiction router
  - `DBOOK`, `DPAGE`, `DeedDate_2` → deed refs
- **Verified:** count **64,284**; GISacres 5–150 → **3,466**; SALE_PRICE>0 → **31,794** (band **931**); Total_EMV>0 → **62,455**; OWNER → **63,648**; vacant-ish STRUC_VAL 0/null in band → **2,253**; IsQualified=1 in band → **426**
- **Geo-check:** PIN15 `535701477729000` (Stella) ≈ **-77.152, 34.774**; `635605195721000` (Morehead City) ≈ **-76.831, 34.747**; `639500992754000` (Beaufort) ≈ **-76.672, 34.717**
- **Notes:** MaxRecordCount **10000**. PRIMARY wire-first. Auth: none.

### 2. NC OneMap Parcels — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='031'`
- **Key fields:** `parno`(=PIN15), `altparno`, `ownname`, mail/site, `gisacres`, `parval`/`landval`/`improvval`, `saledate` (empty here)
- **Verified:** count **64,151**; gisacres 5–150 → **3,722**; parval>0 → **62,389**; saledate null for Carteret
- **Notes:** Prefer county Parceldata for sale price + CAMA. MaxRecordCount **5000**.

### 3. Morehead City Zoning (city-first PRIMARY)

- **REST URL:** https://services1.arcgis.com/S43FtmdNwd7ad0P0/arcgis/rest/services/Zoning/FeatureServer/0
- **Alternate:** …/Morehead_City_Zoning/FeatureServer/0 (count **8,582**)
- **Fields:** `ZONING`, `ZONE_NAME_`, `ORDINANCE_`, `YEAR`, `PREVIOUSZO`
- **Verified:** count **8,584**
- **Codes (sample):** R5/R5S/R7/R10/R15/R15M/R15SM/R20/RMF, CD/CH/CM/CN/DB, FP, I/IC, MA, OP, PD, PM (+ `-CZ` variants)
- **Notes:** Route `MUNICIPALITY IN ('Morehead City','Morehead City ETJ')` → spatial-join MHC Zoning.

### 4. Newport Zoning (city-first)

- **REST URL:** https://arcgisweb.carteretcountync.gov/arcgis/rest/services/Layers/Newport_Zoning/FeatureServer/0
- **Field:** `ZONE`
- **Verified:** count **205**
- **Codes:** R-8/R-10/R-15/R-15D/R-20/R-20A/R-20MH, RO, NB-1, CD, CH, IW, LI, PUD (+ `-CD` variants)

### 5. Emerald Isle Zoning (city-first, coarse)

- **REST URL:** https://arcgisweb.carteretcountync.gov/arcgis/rest/services/Layers/Emerald_Isle_Zoning/FeatureServer/0
- **Field:** `Zone`
- **Verified:** count **8** (B, G, MH1, MV, R2, RMF, VE, VW)
- **Notes:** District-level only — not parcel-grain.

### 6. County Zoning (unincorporated)

- **REST URL:** https://arcgisweb.carteretcountync.gov/arcgis/rest/services/Layers/Zoning/FeatureServer/0
- **Open Data:** https://gisdata-cc-gis.opendata.arcgis.com/datasets/CC-GIS::carteret-county-zoning
- **Fields:** `Zone`, `Zone_Description`
- **Verified:** count **466**
- **Codes:** RA, R5W, R10, R15, R15M, R20, RB, RR CU, B1/B1A/B2/B3, OP, IW, LIW, PI, MC, RCP, + CU/CZ variants

### 7. Morehead City Future Land Use (FLU)

- **REST URL:** https://services1.arcgis.com/S43FtmdNwd7ad0P0/arcgis/rest/services/Future_Land_Use/FeatureServer/0
- **Fields:** `PIN15`, `FLU`, `F_LandUse`, `PreviousLU`, `DateChange`
- **Verified:** count **10,393**
- **Codes:** NR, CR, RR, DR, DT, DC, COM, MUC, PMU, IND, CIV, ESA
- **Join:** attribute on `PIN15` (preferred) or spatial
- **Notes:** MHC-only. Countywide FLU = CAMA LUP PDF — **no county FLU FeatureServer**.

### 8. City Limit / ETJ Boundaries (router)

- **REST URL:** https://arcgisweb.carteretcountync.gov/arcgis/rest/services/Layers/City_ETJ_Limits/FeatureServer/0
- **Fields:** `FEATURE`, `INCORP_MUN`, `UNINCORP_MUN`, `Rel_Key`
- **Verified:** count **24**

## Municipalities (first-class)

County parcels are countywide; **zoning authority is municipal inside city limits / ETJ**. Join: Parceldata → route via `MUNICIPALITY` / City_ETJ_Limits → spatial-join matching city zoning → else county Zoning. **No separate municipal parcel REST.**

### Morehead City (PRIMARY city)

- **Zoning:** AGOL Zoning FS/0 — `ZONING`; **8,584**
- **FLU:** Future_Land_Use FS/0 — `FLU`/`F_LandUse`; **10,393**
- **Maps:** https://moreheadcitync.gov/225/Maps
- **Parcels:** `MUNICIPALITY='Morehead City'` — **6,716** (+ ETJ **3,755**)

### Beaufort (county seat)

- **Zoning REST:** **gap** — https://www.beaufortnc.org/planninginspections/page/town-beaufort-zoning-map
- **Districts (ordinance):** B-1, B-W, CS-MU, H-BD, H-WBD, I-W, L-I, OS, PUD, R-20, R-8, R-8A, R-8MH, RC-5, RS-5, TCA, TR
- **Parcels:** **4,422** (+ ETJ **865**)

### Newport

- **Zoning:** county `Newport_Zoning` — **205** (city-first)
- **Parcels:** **1,985** (+ ETJ **2,261**)

### Emerald Isle

- **Zoning:** county `Emerald_Isle_Zoning` — **8** coarse districts
- **Parcels:** **7,516**

### Atlantic Beach / Pine Knoll Shores / Indian Beach / Cape Carteret / Cedar Point / Bogue / Peletier

- **Zoning REST:** **gap** — parcels on county Parceldata via `MUNICIPALITY`

## PA / viewer deep-links (TRANCHE-3)

| Template | Key | Status |
|----------|-----|--------|
| `https://bttaxpayerportal.com/ITSPublicCE/AppraisalCard.aspx?id={PIN15}` | PIN15 | **Verified** PDF (`application/pdf`) |
| `https://bttaxpayerportal.com/ITSPublicCE/BasicSearch/Parcel?id={PIN15}` | PIN15 | Verified HTML shell |
| `https://lrcpwa.ncptscloud.com/carteret/parcel-detail/{PIN15}` | PIN15 | NCPTS PWA |
| https://arcgisweb.carteretcountync.gov/maps/ | — | Jurisdiction GIS viewer |

## Gaps

1. **Beaufort zoning FeatureServer** — map page/PDF only; no public polygon REST found.
2. **Atlantic Beach, Pine Knoll Shores, Indian Beach, Cape Carteret, Cedar Point, Bogue, Peletier** — no public zoning FeatureServer.
3. **Countywide FLU FeatureServer** — CAMA LUP / Map 8.1B PDF only; MHC FLU FS covers city only.
4. **Emerald Isle zoning** — only **8** coarse district polygons (not parcel-grain).
5. **OneMap `saledate`** empty for Carteret — use county `SaleDate`/`SALE_PRICE`.
6. No AADT / utilities / emails / phones / paid vendors collected (per ask).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **tranche:** 3 (tax/sale/owner + PA deep-link `{PIN15}` + jurisdictionGisUrl)
