# Lenoir County, NC — GIS County Card

## Summary

Lenoir County (Greenville / Eastern NC, FIPS **37107**, slug **lenoir**, OneMap `cntyfips='107'`) publishes public cadastral + zoning REST via **LenoirCoGIS** AGOL (`services3.arcgis.com/bDx73HOFAO3oSeDq`). **PRIMARY parcels:** **Parcels_Zoning_Addressing** FS/6 — ~**36,474** polygons with owner (`Name1`/`Name2`), mailing, situs `PhysStrAdd`, GIS/Map/Deed acres, land/improve/total FMV, last sale (`SalesAmt`/`DateSold` + deed book/page/year), and Spatialest **`PRC`** deep-link by `Record_Num`. ~**5,326** with `GIS_ACRE` 5–150 (~**3,090** ImproveFMV 0/null; ~**1,225** SalesAmt>0). **OpenGov/2** twin adds parcel `ZONE` attr (~12.5k), qualify codes, and ASV/taxable. **Cities-first zoning:** **Kinston** FS/3 (~1,285), **Pink Hill** FS/7 (~39 + `Future_LU`), coarse **County_Zoning** FS/2 (8 polys incl. GTP-*), **Proposed_LenoirCo_Zoning_2023** OpenGov/23 (~35.8k parcel-class). **La Grange** zoning = **PDF only** (gap). **Grifton** straddles Pitt — prefer Pitt Grifton Zoning. **FLU:** Pink Hill `Future_LU` only; Kinston Comp Plan PDF; no countywide FLUM REST. **PA:** Spatialest `{Record_Num}` + NCPTS `{NC_PIN}`. Markets: **[Greenville/Eastern NC]**.

## Portals

- **Public GIS viewer (jurisdiction homepage)** — https://lenoirco.maps.arcgis.com/apps/webappviewer/index.html?id=68c0618065d04f1182fb86cb5b6647de
- **Experience Builder (lenoircountygis.com)** — https://experience.arcgis.com/experience/9f9e1c23a7124bd2961e83861c747b84/
- **County AGOL REST org** — https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services
- **Tax Department** — https://lenoircountync.gov/tax-department/
- **Planning & Inspections** — https://lenoircountync.gov/planning-inspections-department/
- **PA / Spatialest property (preferred deep-link)** — `https://property.spatialest.com/nc/lenoir/#/property/{Record_Num}`
- **PA Spatialest search** — https://property.spatialest.com/nc/lenoir/
- **PA Spatialest appeals** — https://appeals.spatialest.com/nc-lenoir/
- **PA / NCPTS parcel search** — https://lrcpwa.ncptscloud.com/lenoir/parcel-search
- **PA NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/lenoir/parcel-detail/{NC_PIN}`
- **Tax bills (Catalis)** — https://www.lenoircountytaxes.com/
- **Register of Deeds (Cott)** — http://cottweb.co.lenoir.nc.us/external/LandRecords/protected/v4/SrchName.aspx
- **City of Kinston Planning** — https://kinstonnc.gov/152/Planning-and-Development-Services
- **Kinston Comp Land Use Plan (PDF)** — https://www.kinstonnc.gov/DocumentCenter/View/777/Kinston-Comprehensive-Land-Use-Plan
- **La Grange Official Zoning Map (PDF, 2011)** — https://www.lagrangenc.com/DocumentCenter/View/104/LaGrange-Official-Zoning-Map-Revised-December-12-2011-PDF
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Municipalities (first-class)

| Municipality | Local public GIS? | Zoning / FLU source |
|--------------|-------------------|---------------------|
| **Kinston** (seat) | County AGOL host; city links county viewer | **Kinston_Zoning_Dec23** PZA/3 (**1,285**) `ZONING` — city-first PRIMARY. FLU = Comp Plan **PDF** (no REST) |
| **La Grange** | No REST; ConnectGIS `lenoir.connectgis.com` **504** | Official Zoning Map **PDF** (AR/R-18/R-12/R-10/R-5/HC/DD/LI) — **gap** |
| **Pink Hill** | County AGOL host | **PinkHill_Zoning** PZA/7 (**39**) `Zoning` + **`Future_LU`** |
| **Grifton** (tip; mainly Pitt) | Prefer **Pitt** card | Pitt PermitDisplayMap/23 Grifton Zoning (**104**); Lenoir tax dist ~156 parcels |
| Unincorporated / GTP / ETJ | County AGOL | County_Zoning PZA/2 (**8** coarse); Proposed OpenGov/23; ETJ Lenoir_Static/6 (Kinston, La Grange, Pink Hill, Grifton) |

Parcel `TaxDistDes` (PZA/6): COUNTY/CITY OF KINSTON **11,214** (+ MUNI SVC **309**); NORTH LENOIR FIRE **5,225**; SOUTHWOOD **2,724**; DEEP RUN **2,586**; HUGO **2,312**; MOSELEY HALL **2,306**; SANDY BOTTOM **2,243**; TOWN OF LAGRANGE **1,888**; … TOWN OF PINK HILL **387**; TOWN OF GRIFTON **156**; GLOBAL TRANSPARK **79**; COUNTY ONLY **662**.

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `NC_PIN`/`NCPIN` (preferred); `Record_Num` (Spatialest); OneMap `parno`/`altparno` | altparno↔Record_Num |
| polygons | Yes | PZA FS/6 / OpenGov/2 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `GIS_ACRE`/`MapAcres`; `DeedAcres`; OpenGov `MAP_ACRES`/`calculated_acreage` | ~**5,326** GIS 5–150 |
| ownerName | Yes | `Name1`/`Name2`; OpenGov `NAME_1`/`CURRENT_OWNER_NAME_*` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `Addr1`/`City`/`State`/`Zip`; OpenGov `TAYPAYER_ADDRESS_*` | |
| situs address | Yes | `PhysStrAdd`; AddrPts `COMPLETE_A`+`ZIP`; OneMap `siteadd` | On primary |
| lastSale date/price | Yes (last) | `SalesAmt`,`DateSold`,`DeedYear`,`DeedBook`/`DeedPage`; OpenGov `SALES_AMOUNT`+`QUALIFY_CODE*` | DateSold like `YYYYMMDD` |
| tax values | Yes | `LandFMVCur`,`ImproveFMV`,`TotalFMVCu`; OpenGov + `*_ASV_*`/`TAXABLE_VALUE` | FMV on PZA; ASV on OpenGov |
| zoning | Yes (cities-first) | Kinston/PinkHill layers + County coarse + parcel `ZONE` | Prefer city polygons inside munis |
| flu | Partial | Pink Hill `Future_LU`; Kinston Comp Plan PDF | **No countywide FLUM REST** |
| dorCode / land use | Partial | `LandUseCur` (N/Y present-use flag); OpenGov `LAND_CURRENT_USE*`/`BUILT_USE_DESC` | Not DOR codes |
| appraiser / viewer link | Yes | Spatialest `{Record_Num}`; NCPTS `{NC_PIN}`; PRC field | Templates below |

## Layers (verified)

### 1. Parcels_Zoning_Addressing / Parcels — PRIMARY (viewer wire-first)

- **Purpose:** parcels | tax | ownership | sales (last) | situs
- **REST URL:** https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services/Parcels_Zoning_Addressing/FeatureServer/6
- **Layer name / id:** Parcels / 6
- **Geometry:** Polygon | **CRS:** 102719 / 2264 | **MaxRecordCount:** 2000
- **Key fields → targets:** `NC_PIN`/`NCPIN`→parcelId; `Record_Num`→parcelIdAccount / Spatialest key; `ParcelNum`→parcelIdDisplay; `GIS_ACRE`/`MapAcres`/`DeedAcres`/`Calculated`→acreage; `Name1`/`Name2`→owner; `Addr1`/`City`/`State`/`Zip`→mailing; `PhysStrAdd`→situs; `SalesAmt`/`DateSold`/`DeedYear`/`DeedBook`/`DeedPage`→lastSale; `LandFMVCur`/`ImproveFMV`/`TotalFMVCu`/`LandLUVCur`→tax; `LandUseCur`; `TaxDistDes`; `Township`; `YearBuilt`/`FinishedAr`; **`PRC`**→appraiserSearchUrl
- **Verified:** count **36,474**; GIS_ACRE 5–150 → **5,326**; MapAcres 5–150 → **5,326**; DeedAcres 5–150 → **5,392**; ImproveFMV=0/null in band → **3,090**; SalesAmt>0 countywide → **10,286**; SalesAmt>0 in band → **1,225**; PhysStrAdd present → **36,115**
- **Geo-check:** NC_PIN `4525-31-5293` / Record_Num `5084` centroid ≈ **-77.581, 35.256** (Kinston Queen St)
- **Notes:** **PRIMARY** wire-first (WAB search source). `PRC` = `https://property.spatialest.com/nc/lenoir#/property/{Record_Num}` (slash before `#` also works). Paginate MRC 2000. Auth: none.

### 2. OpenGov / Parcels — CAMA enrichment twin

- **REST URL:** https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services/OpenGov/FeatureServer/2
- **Count:** **36,474** | **MaxRecordCount:** 1000
- **Extra fields:** `ZONE`/`ZONE_DESCRIPTION` (~**12,548** populated — mostly Kinston/town codes); `QUALIFY_CODE`/`QUALIFY_CODE_DESC`; `LAND_ASV_CUR`/`IMPROVE_ASV_CUR`/`TOTAL_ASV_CURRENT`/`TAXABLE_VALUE`; richer situs parts; `VACANT_IMPROVED_CODE`; `OWNER_ID`
- **ZONE top (non-null):** RA6 3517, RA5 3260, RA8 2545, B1 548, R10 451, I1 387, R18 373, R5 272, R12 263, …
- **Notes:** Same geometry footprint as PZA/6. Prefer for qualify/ASV/ZONE attr; still prefer **city zoning polygons** inside munis over parcel ZONE. Paginate MRC 1000.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='107'`
- **Key fields:** `parno`,`altparno`,`ownname`,`mailadd`/`mcity`/`mstate`/`mzip`,`siteadd`/`scity`,`gisacres`,`saledate`,`parval`/`landval`/`improvval`
- **Verified:** count **36,463**; gisacres 5–150 → **5,318**; improvval=0/null in band → **3,093**
- **Join:** `parno`↔`NC_PIN`; `altparno`↔`Record_Num`
- **Notes:** Situs on polys. No sale price. MaxRecordCount **5000**.

### 4. Address Points — situs ZIP join

- **REST URL:** https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services/Parcels_Zoning_Addressing/FeatureServer/9
- **Mirror:** FS/0 (adds `Hyperlink`)
- **Count:** **~41,413** | `COMPLETE_A`,`ZIP`,`COMMUNITY`,`MUNICIPALI`
- **Notes:** No PIN join key on AddrPts — spatial join; prefer parcel `PhysStrAdd` when present.

### 5. Kinston Zoning — city-first PRIMARY

- **REST URL:** https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services/Parcels_Zoning_Addressing/FeatureServer/3
- **OpenGov mirror:** OpenGov/4 (**1,301**)
- **Count:** **1,285** | field `ZONING`
- **Top codes:** RA-6 319, RA-5 263, B-1 180, RA-8 163, I-1 91, B-2 55, I-B 52, O&I 47, RA-20 38, RO 32, SC 16, RA-12 13, I-2 7, RA-7 5, CD variants
- **Notes:** Extent = City of Kinston (+ cases). Prefer over parcel ZONE / county coarse inside city.

### 6. Pink Hill Zoning + Future_LU — city-first

- **REST URL:** https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services/Parcels_Zoning_Addressing/FeatureServer/7
- **Count:** **39** | `Zoning` + **`Future_LU`**
- **Zoning:** HC 15, RA 12, R-10 8, RM 2, DC 2
- **Future_LU:** Residential 16, Commercial 13, Open Space/Recreation 8, Agricultural/Residential 2
- **Notes:** Only municipal FLU REST found in county.

### 7. County Zoning — unincorporated / GTP (coarse)

- **REST URL:** https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services/Parcels_Zoning_Addressing/FeatureServer/2
- **OpenGov mirrors:** OpenGov/19, OpenGov/3 (backup) — same **8**
- **Count:** **8** | field `Zoning`
- **Codes (1 each):** Agricultural, Commercial, Industrial, Residential, GTP-AR, GTP-C, GTP-I, GTP-RE
- **Notes:** Coarse category polygons (not fine district fabric). Use for unincorporated + Global TransPark overlay routing. Prefer city layers inside munis/ETJ.

### 8. Proposed Lenoir County Zoning 2023-10-05 — parcel-class proposed

- **REST URL:** https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services/OpenGov/FeatureServer/23
- **Count:** **35,841** | `Proposed_Z` (+ parcel CAMA attrs)
- **Classes:** Municipality 13876, Agricultural 11344, Residential 5257, ETJ 3781, GTP-AR 742, GTP-I 308, Commercial 254, GTP-RE 198, Industrial 41, GTP-C 37, Not County 3
- **Notes:** Proposed/adopted-status clarify with Planning — treat as **proposed county zoning class** on parcels, not a substitute for Kinston/Pink Hill district maps. Useful for unincorporated screening.

### 9. Boundaries / ETJ / jurisdictions (routers)

- **Municipal Areas:** https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services/Lenoir_County_Municipal_Areas/FeatureServer/0 — Grifton (multi), La Grange, Pink Hill, Kinston (`MUNNM`)
- **ETJ:** https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services/Lenoir_Static/FeatureServer/6 — **6** polys: Kinston, La Grange, Pink Hill, Grifton (`ETJMUNNM`/`ETJLABEL`)
- **OpenGov jurisdictions:** Grifton/12, Lagrange/13, PinkHill/14 (insp-district polys, count 1 each)
- **OpenGov Municipalities_Backup/6:** 4 features

### 10. Grifton zoning (cross-county) — prefer Pitt card

- **REST:** https://gis.pittcountync.gov/gis/rest/services/Permitting/PermitDisplayMap/MapServer/23 — count **104** `ZONE`
- **Notes:** Grifton straddles Lenoir/Pitt. For Lenoir-side parcels use spatial clip; full town zoning lives on Pitt host.

### 11. Do-not-wire / wrong geography

- **services2…/HfsHDBmkGwb1UtID/ParcelViewer_Layers** — **Norwalk CT** (wrong state) — never use
- **lenoir.connectgis.com** — HTTP **504** at verify time (La Grange community map unreachable)
- **Caldwell County City of Lenoir** zoning (Hickory shed) — different jurisdiction; see Caldwell card 37027

## Cities / towns first-class routing

1. Inside **Kinston** limits/ETJ → Kinston_Zoning_Dec23 (PZA/3)
2. Inside **Pink Hill** → PinkHill_Zoning (PZA/7); FLU from same layer `Future_LU`
3. Inside **La Grange** → **no REST** — PDF zoning map only (gap); parcel OpenGov `ZONE` sparse for town codes (R10/R18/R5/R12/HC/LI)
4. Inside **Grifton** (Lenoir tip) → Pitt Grifton Zoning /23; else parcel attrs
5. Else unincorporated → County_Zoning coarse (PZA/2) and/or Proposed_Z (OpenGov/23); GTP-* for Global TransPark

## Deep links (TRANCHE-3)

- **PA Spatialest (preferred):** `https://property.spatialest.com/nc/lenoir/#/property/{Record_Num}`
- **PA field on layer:** `PRC` already stores Spatialest URL
- **PA NCPTS:** `https://lrcpwa.ncptscloud.com/lenoir/parcel-detail/{NC_PIN}`
- **Jurisdiction GIS:** https://lenoirco.maps.arcgis.com/apps/webappviewer/index.html?id=68c0618065d04f1182fb86cb5b6647de
- **Experience alt:** https://experience.arcgis.com/experience/9f9e1c23a7124bd2961e83861c747b84/

## Gaps

- **La Grange zoning REST gap** — Official Zoning Map PDF only; ConnectGIS 504
- **Kinston / countywide FLU REST gap** — Comp Plan PDF; only Pink Hill `Future_LU` on REST
- **County_Zoning only 8 coarse polys** — not a fine unincorporated district fabric; Proposed_Z is parcel-class proposed
- Parcel OpenGov `ZONE` ~34% populated — prefer spatial join to city zoning layers
- AddrPts lack PIN — spatial join; prefer `PhysStrAdd`
- Last-sale only on parcel (no multi-transfer history FeatureServer)
- Grifton / Seven Springs fire-dist parcels may fall outside municipal zoning REST
- Alternate FS `nJbIFHiSnaX0z0hS/LenoirNC_Parcels_Zoning_Addressing` (~35.8k) — older/partial mirror; prefer LenoirCoGIS `bDx73HOFAO3oSeDq`
- No phones/emails; no AADT/utilities; no paid vendors on this card

## License / verification

Lenoir County / LenoirCoGIS public AGOL + NC OneMap; public query endpoints; attribution recommended; no paid vendors.

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **method:** Live ArcGIS REST counts + field samples + WGS84 geo-check; Spatialest PRC + NCPTS SPA shells; OneMap `cntyfips='107'`; municipal PDF/homepage GIS absence check; wrong-org Norwalk reject
