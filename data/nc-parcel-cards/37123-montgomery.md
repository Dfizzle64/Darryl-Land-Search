# Montgomery County, NC — GIS County Card

## Summary

Montgomery County (Charlotte shed, FIPS **37123**, slug **montgomery**, `cntyfips='123'`) publishes public HandP **WebGIS** at **`www.webgis.net/nc/montgomery/`** with ArcGIS REST **`NC/Montgomery/MapServer`**. **Wire-first parcels + CAMA:** layer **1 Parcels** — ~**30,316** polys with `PIN`/`PinNoDash`, owner (`Name_1`–`3`), mailing, situs (`PhyAddress` / HouseNum+Str*), `Deed_Acre`/`ACRES`, land/imp/total **ASV** (`LandASVCur`,`ImpMajASVC`,`ImpMisASVC`,`TotASVCur`), last sale **`SalesAmt`+`TransDate`** (YYYYMMDD int) + deed book/page. Acreage 5–150: **Deed_Acre → 6,024**; Shape_Area/43560 → **~6,085**. SalesAmt>0 → **16,339** (in 5–150 → **2,531**). **Cities-first zoning:** **Troy** `/17` `New_Zoning` (**769**); **Biscoe** `/16` `Type` (**458**); county **Zoning** `/18` district polys (**274**). **PTRC** `MontgomeryCounty/Zoning` parcel-based Existing ETJs (**~30.8k**) carries county zone codes + `Zoning='City'` stubs for munis. **Mt Gilead / Candor / Star** — no dedicated public zoning REST (TaxDistDes routing only). **FLU:** County Land Use Plan **2010 PDF** + Mt Gilead Comp Plan **PDF**; no FLU FeatureServer. **PA deep-link:** `https://www.webgis.net/nc/montgomery/PropertyCard.php?pid={PinNoDash}&card=0` (+ NCPTS `{PinNoDash}`). **Jurisdiction GIS:** `https://www.webgis.net/nc/montgomery/`. **NC OneMap** `cntyfips='123'` geometry/owner/tax/saledatetx fallback (no sale price; saledate epoch empty). Markets: **[Charlotte]**.

## Portals

- **Jurisdiction GIS (WebGIS)** — https://www.webgis.net/nc/montgomery/ (alias `/nc/Montgomery/`)
- **County ArcGIS REST** — https://www.webgis.net/arcgis/rest/services/NC/Montgomery/MapServer
- **PA / PropertyCard (HandP)** — `https://www.webgis.net/nc/montgomery/PropertyCard.php?pid={PinNoDash}&card=0` (card=-1 returns link list)
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/montgomery/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/montgomery/parcel-detail/{PinNoDash}`
- **County website** — https://www.montgomerycountync.gov/
- **Tax Department** — https://www.montgomerycountync.gov/departments/tax-department
- **Planning / Zoning** — https://www.montgomerycountync.gov/departments/planning
- **County Comp Land Use Plan 2010 (PDF)** — https://nmcdn.io/e186d21f8c7946a19faed23c3da2f0da/9938771685204d8ea2bbc1353c6b7aed/files/departments/planning/Land-Use-Plan-2010--Adopted-.pdf
- **AGOL org / hub** — https://montnc.maps.arcgis.com/ — https://montnc-gis-Montnc.hub.arcgis.com (address/roads/PU; parcels shapefile download — not live FS CAMA)
- **PTRC Zoning MapServer** — https://maps.ptrc.org/arcgis/rest/services/MontgomeryCounty/Zoning/MapServer
- **Town of Troy** — https://townoftroy.org/
- **Town of Biscoe** — https://townofbiscoe.com/
- **Town of Mount Gilead** — https://mtgileadnc.com/ — Comp Plan PDF https://mtgileadnc.com/wp-content/uploads/2023/06/MtGileadCompPlan_Aug2021.pdf
- **Town of Star** — https://www.star-nc.com/
- **Town of Candor** — https://www.townofcandornc.com/
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='123'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` (spaced); `PinNoDash` (12-digit); OneMap `parno` | Prefer **PinNoDash** for PropertyCard/NCPTS; `PIN`↔OneMap `parno` |
| polygons | Yes | Montgomery/MapServer/1; OneMap | CRS **3632** (site also refs 2264) |
| acreage | Yes | `Deed_Acre`; `ACRES` (string); Shape_Area/43560; OneMap `gisacres` | Deed 5–150 → **6024**; shape → **6085**; OneMap → **6091** |
| ownerName | Yes | `Name_1`/`Name_2`/`Name_3`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `Addr_1`–`4`,`City`,`State`,`Zip` | |
| situs address | Yes | `PhyAddress`; HouseNum+StrName+StrType; Address Points `FULL_ADRS` | |
| lastSale date/price | Yes | `TransDate` (YYYYMMDD int), `SalesAmt`, `SalesInstr`, `QufiCode` | SalesAmt>0 → **16339**; in 5–150 → **2531** |
| tax values | Yes (ASV) | `LandASVCur`,`ImpMajASVC`,`ImpMisASVC`,`TotASVCur`; OneMap `parval`/`landval`/`improvval` | TotASVCur>0 → **30125**; no separate FMV field on REST |
| zoning | Yes (cities-first) | Troy `New_Zoning`; Biscoe `Type`; county Zoning `NAME`; PTRC Zoning | Mt Gilead/Candor/Star REST gap |
| flu | Gap | Comp LUP 2010 PDF; Mt Gilead Comp Plan PDF | No FLU FeatureServer |
| appraiser / viewer link | Yes | PropertyCard `{PinNoDash}`; NCPTS `{PinNoDash}`; WebGIS | TRANCHE-3 |

### TaxDistDes → municipality router

| TaxDistDes | Approx parcels | Jurisdiction | Zoning source (prefer) |
|------------|----------------|--------------|------------------------|
| TROY | **1,689** | Town of Troy | **Troy Zoning /17** `New_Zoning` |
| BISCOE | **988** | Town of Biscoe | **Biscoe Zoning /16** `Type` |
| MT GILEAD | **1,075** | Town of Mount Gilead | **Gap** — PTRC Zoning='City' stub only |
| STAR | **600** | Town of Star | **Gap** |
| CANDOR | **584** | Town of Candor | **Gap** |
| COUNTY ONLY / fire dists | **~25k** | Unincorporated (+ Lake Tillery / Badin Lake / Wadeville fire) | County Zoning /18 + PTRC Existing ETJs parcel Zoning |

## Layers (verified 2026-09-24)

### 1. NC/Montgomery Parcels — parcels + ownership + tax + sale (PRIMARY CAMA)

- **Purpose:** parcels | tax | ownership | sales
- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Montgomery/MapServer/1
- **Layer name / id:** Parcels / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN`, `PinNoDash` → parcelId
  - `OwnerID1` → parcelIdAccount
  - `Deed_Acre`, `ACRES` → acreage
  - `Name_1`, `Name_2`, `Name_3` → ownerName
  - `Addr_1`–`4`, `City`, `State`, `Zip` → mailing
  - `PhyAddress`, `HouseNum`, `StrName`, `StrType` → situs
  - `TransDate`, `SalesAmt`, `SalesInstr`, `QufiCode` → lastSale
  - `DeedBook`, `DeedPage`, `DeedYear` → deed
  - `LandASVCur`, `ImpMajASVC`, `ImpMisASVC`, `TotASVCur` → tax.assessed / presented value
  - `TaxDistDes`, `TownshipDs`, `VolFireDes`, `NeighDesc` → jurisdiction / fire
  - `ApprCode`/`ApprCdDesc`, `ClassCode`/`ClassCdDes` → use class
- **WKID / CRS:** **3632** (NAD83(NSRS2007) NC ftUS); viewer siteSettings also sets 2264
- **Verified:** yes — count **30,316**; Deed_Acre 5–150 → **6,024**; Shape_Area 217800–6534000 → **6,085**; SalesAmt>0 → **16,339**; SalesAmt>0 & Deed 5–150 → **2,531**; TotASVCur>0 → **30,125**; sample PIN `6570 00 99 7814` centroid ~**-80.07, 35.15** (Montgomery NC)
- **Notes:** **PRIMARY** for tax/owner/sale. MapServer only. MaxRecordCount **1000** — paginate. TransDate is integer YYYYMMDD (not epoch). PropertyCard + identify use `PinNoDash` (spaces stripped from PIN).

### 2. Address Points — situs join

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Montgomery/MapServer/0
- **AGOL twin:** https://services9.arcgis.com/omIyQysyaJipPNFR/arcgis/rest/services/Address_Points/FeatureServer
- **Geometry:** Point
- **Fields:** `FULL_ADRS`, `ADRS_NUMB`, `ST_NAME`, `CITY`, `ZIP`, `LATITUDE`, `LONGITUDE`
- **Verified:** count **20,726**
- **Notes:** No PIN — spatial/nearest join. Prefer `PhyAddress` on parcels when populated.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='123'`
- **Fields:** `parno`,`ownname`,`mailadd`/`mcity`/`mstate`/`mzip`,`siteadd`,`gisacres`,`parval`/`landval`/`improvval`,`saledatetx` (epoch `saledate` empty), `cntyfips`
- **Verified:** yes — **30,283**; gisacres 5–150 → **6,091**; parval>0 → **30,090**; saledate IS NOT NULL → **0**
- **Notes:** No sale price. Join `parno`↔`PIN` (spaced). Strong acreage/tax mirror.

### 4. Troy Zoning — PRIMARY Troy (city-first)

- **Purpose:** zoning (city-first)
- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Montgomery/MapServer/17
- **Fields:** `New_Zoning` (aap label ZONE_CODE in siteSettings — REST field is **New_Zoning**)
- **Verified:** yes — count **769**
- **New_Zoning (top):** SFR-3 (202), SFR-2 (168), CIV (100), AG (65), SFR-1 (65), C-24/27 (33), IND (29), RMST (28), VSR (24), MU-2 (23), MS (16), MU-1 (8), C-134 (8)
- **Notes:** Prefer inside Troy / TaxDistDes='TROY'. Spatial join parcels CRS 3632.

### 5. Biscoe Zoning — PRIMARY Biscoe (city-first)

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Montgomery/MapServer/16
- **Fields:** `Type`
- **Verified:** yes — count **458**
- **Type (top):** RMST (83), AG (78), CIV (61), C-24/27 (54), IND (42), SFR-2 (42), SFR-3 (26), C-220 (19), MU-2 (13), VSR (11), SFR-1 (10), MS (9), MU-1 (5); overlays HIO/MFO/SCO/TNDO/MHO (1 each)
- **Notes:** Prefer inside Biscoe / TaxDistDes='BISCOE'.

### 6. County Zoning — unincorporated district polygons

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Montgomery/MapServer/18
- **Fields:** `NAME`, `CITY`
- **Verified:** count **274**
- **NAME:** Commercial (112), Industrial (52), Residential 3 (48), Residential 2 (24), Residential 1 (15), Mobile Home Park (12), City (7), Campground (3), RV Park (1)
- **Notes:** Coarse county district polys — spatial join for unincorporated. `CITY` mostly blank.

### 7. PTRC Parcel Based Zoning_Existing ETJs — countywide parcel zoning attrs

- **REST URL:** https://maps.ptrc.org/arcgis/rest/services/MontgomeryCounty/Zoning/MapServer/5
- **Related:** /1 Proposed Troy ETJ (**30,860**); /4 Existing ETJ Boundaries (Troy/Biscoe/Star/Candor/Mt Gilead)
- **Fields:** `Zoning`, `PrevZoning`, `PIN`, `TaxDistDes`, `Deed_Acre`, owner/situs subset
- **Verified:** count **30,829**; Zoning populated **30,531**
- **Zoning:** City (**8153** — municipal stub), R-1 (7108), R-3 (6850), R-2 (5115), Campground (1587), RV Park (1096), I (355), C (188), MHP (79)
- **Notes:** Good unincorporated zone codes. Where `Zoning='City'`, prefer Troy/Biscoe native layers; Mt Gilead/Candor/Star still lack detailed district REST.

### 8. Towns — municipal boundaries

- **REST URL:** https://www.webgis.net/arcgis/rest/services/NC/Montgomery/MapServer/19
- **Verified:** count **5** — STAR, TROY, CANDOR, MT GILEAD, BISCOE

### 9. FLU — PDF only (gap)

- County Comp Land Use Plan 2010 (nmcdn PDF above)
- Mount Gilead Moving Ahead Comp Plan (2021): https://mtgileadnc.com/wp-content/uploads/2023/06/MtGileadCompPlan_Aug2021.pdf
- No public FLU FeatureServer (county or towns)

## Municipalities (cities-first)

| Municipality | Zoning source | Count | Own GIS? | FLU REST? | Notes |
|--------------|---------------|------:|:--------:|:---------:|-------|
| **Troy** | **Troy Zoning /17** `New_Zoning` | 769 | Town site; zoning on county WebGIS | No — county LUP PDF | County seat; TaxDistDes TROY ~1689 |
| **Biscoe** | **Biscoe Zoning /16** `Type` | 458 | Town site; zoning on county WebGIS | No | TaxDistDes BISCOE ~988 |
| **Mount Gilead** | — (PTRC City stub) | — | Town site + Comp Plan PDF | No — Comp Plan PDF has FLU map | TaxDistDes MT GILEAD ~1075; **zoning REST gap** |
| **Star** | — | — | Town site | No | TaxDistDes STAR ~600; **zoning REST gap** |
| **Candor** | — | — | Town site | No | TaxDistDes CANDOR ~584; **zoning REST gap** |
| Unincorporated | County Zoning /18 + PTRC /5 | 274 / ~22.7k non-City | County WebGIS | PDF only | R-1/R-2/R-3/C/I/Campground/RV/MHP |

## PA / deep-link templates

| Template | URL |
|----------|-----|
| **PropertyCard (preferred)** | `https://www.webgis.net/nc/montgomery/PropertyCard.php?pid={PinNoDash}&card=0` |
| PropertyCard link list | `https://www.webgis.net/nc/montgomery/PropertyCard.php?pid={PinNoDash}&card=-1` |
| NCPTS parcel-detail | `https://lrcpwa.ncptscloud.com/montgomery/parcel-detail/{PinNoDash}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/montgomery/parcel-search |
| Jurisdiction GIS | https://www.webgis.net/nc/montgomery/ |

WebGIS `siteCustom.js` strips spaces from `atts.PIN` then calls PropertyCard.php — use **PinNoDash**. Verified card HTML for PIN `657000997814` (LEAK JOHN W; TOTAL VALUE 37,700).

## Gaps / caveats

- Mt Gilead, Candor, Star — **no public zoning FeatureServer/MapServer districts** (only TaxDistDes + PTRC `Zoning='City'` stubs)
- FLU PDF-only (county 2010 + Mt Gilead Comp Plan) — no FLU REST
- Tax REST fields are **ASV** (`*ASVCur`); no separate market-value columns (PropertyCard TOTAL VALUE ≈ TotASVCur; OneMap `parval` aligns)
- CRS **3632** on MapServer (non-standard vs common 102719/2264) — project carefully when joining
- PTRC NFocus / MontgomeryCounty MapServers returned empty layer lists (2026-09-24) — use Zoning MapServer + WebGIS
- AGOL org has Address/Roads/PU + parcels **shapefile** download, not live CAMA FeatureServer
- Address points lack PIN
- MapServer MaxRecordCount 1000 — paginate
- Utilities / AADT / emails / phones / paid vendors excluded by design

## License / attribution

Montgomery County GIS / Tax Department (HandP WebGIS); PTRC Piedmont Triad Regional Council zoning services; Town of Troy / Biscoe zoning layers hosted on county stack; NC OneMap. Data prepared from county systems; independent verification recommended. Commercial resale subject to **NCGS 132-10**. Attribute Montgomery County GIS.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 9
- Live `returnCountOnly` + sample attribute/geometry queries against NC/Montgomery Parcels/Address/Troy Zoning/Biscoe Zoning/County Zoning/Towns, PTRC Zoning Existing ETJs + ETJ boundaries, PropertyCard.php by PinNoDash, NCPTS parcel-detail, montnc AGOL catalog, and NC OneMap `cntyfips='123'`.
