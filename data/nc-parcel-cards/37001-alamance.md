# Alamance County, NC — GIS County Card

## Summary

Alamance County (Raleigh–Durham / Triad footprint, FIPS **37001**, slug **alamance**) publishes rich **public** ArcGIS REST at `apps.alamance-nc.com`: countywide **tax parcel polygons** with ownership, mailing, **situs on the polygon**, GIS/deed acreage, land/improvement/total FMV + ASV, and **last-sale amount** (`AMSLAM`) plus qualify codes on `Tax/AlamanceParcels`. **Zoning is city-first** via **ReGIS** (`maps.regisnc.org`) for **Burlington / Graham / Elon** and **Mebane AGOL** for Mebane current zoning + 2045 FLUM. **No public countywide base zoning REST** for unincorporated areas (CountyGISMap / GISWebsite omit zoning; watershed layer is WCA/BOW **overlay** only). Smaller towns (Haw River, Gibsonville, Green Level, Swepsonville, Ossipee, Village of Alamance) have **no public zoning/FLU REST** found. **NC OneMap** (`cntyfips='001'`) is a usable fallback with populated `gisacres` + `siteadd` (unlike Orange). Primary PA deep link: Spatialest by 6-digit `PIN`.

## Portals

- **County GIS interactive map** — https://apps.alamance-nc.com/CountyGISMap/default.aspx (also `/GISMap/`)
- **County ArcGIS REST** — https://apps.alamance-nc.com/arcgis/rest/services
- **GIS home** — https://gis.alamancecountync.gov/ — https://www.alamance-nc.com/newgis/
- **Open Data** — https://alamancecounty-alamancectygis.opendata.arcgis.com/
- **GIS FTP / downloads** — https://apps.alamance-nc.com/GISFTP/
- **Property Record Search (Spatialest)** — https://property.spatialest.com/nc/alamance/#/ — deep link `#/property/{PIN}`
- **Tax Department** — https://tax.alamancecountync.gov/ — tax pay https://property.spatialest.com/nc/alamance-tax/
- **Planning / Zoning (admin, not REST)** — https://planning.alamancecountync.gov/zoning/
- **ReGIS (Burlington / Graham / Elon)** — https://maps.regisnc.org/arcgis/rest/services — https://www.burlingtonnc.gov/181/ReGIS
- **Mebane GIS / CityMap** — https://cityofmebanenc.gov/gis-and-mapping/ — AGOL org services8…/pqfZyBvxpstAt1gO
- **NC OneMap** — https://www.nconemap.gov — `services.nconemap.gov` / `services.gis.nc.gov`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` (6-digit), `GPIN` (10-digit), `AKPAR_`, `PID`; OneMap `parno`≈GPIN | Prefer `PIN` for Spatialest; `GPIN` for statewide / address join |
| polygons | Yes | Tax/AlamanceParcels/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `ACRES`, `AKACRM`, `AKACRD`; OneMap `gisacres` / `recareano` | ACRES 5–150 → **8885**; gisacres 5–150 → **8871** |
| ownerName | Yes | `OWNAM1` / `OWNAM2`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `OWADR1`–`OWADR4`, `OWCITY`, `OWSTA`, `OWZIPA` | |
| situs address | Yes | `CAKPSAD` + components on parcels; Addresses `FULLADDRESS` join `PARENTGPIN`=`GPIN` | Situs **on** polygons (stronger than Orange) |
| lastSale date/price | Yes | `AMSLAM`, `AMDTSL`/`DateSold`/`DateSoldText`, `AMQFCD`/`XXQCDS` | AMSLAM>0 → **44481**; Sales_History FS for history |
| tax values | Yes | `JMTCTM`, `AKLCFM`, `AKICFM`, `XXTCAS`, `XXTXVL` | |
| zoning | Yes (split) | Burlington `DIST_IDW`; Graham `ZONEID`; Elon `ZONE_ID`; Mebane `Zoning` | **No** unincorporated base zoning REST |
| flu | Yes (partial) | Burlington `Future_Landuse`; Graham `FutureLU`; Elon `LU_CODE`; Mebane `PLACETYPE` | County FLU REST gap |
| appraiser / viewer link | Yes | Spatialest + CountyGISMap | Templates below |

## Layers (verified)

### 1. Tax/AlamanceParcels — parcels + CAMA + situs + sale + tax (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | situs
- **REST URL:** https://apps.alamance-nc.com/arcgis/rest/services/Tax/AlamanceParcels/FeatureServer/0
- **Layer name / id:** Alamance Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN`, `GPIN`, `AKPAR_`, `PID` → parcelId*
  - `ACRES`, `AKACRM`, `AKACRD` → acreage
  - `OWNAM1`, `OWNAM2` → ownerName
  - `OWADR*`, `OWCITY`, `OWSTA`, `OWZIPA` → mailing
  - `CAKPSAD`, `AKPST_*` → situs
  - `AMSLAM`, `AMDTSL`/`DateSoldText`, `AMQFCD` → lastSale
  - `JMTCTM`, `AKLCFM`, `AKICFM`, `XXTCAS`, `XXTXVL` → tax
  - `AKCYCD`/`XXCYDS` → municipality routing (not district zoning)
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **79,848**; `ACRES BETWEEN 5 AND 150` → **8,885**; sample sale/owner/situs OK; geo centroid of sale sample in Alamance (−79.52, 36.06)
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **9000**. No base zoning field.

### 2. Tax/Sales_History — sale history polygons

- **REST:** …/Tax/Sales_History/FeatureServer/0 (`SalesHistory_FC`) and `/1` (`SalesQuery`, count **247,828**)
- **Fields:** `PIN`, `GPIN`, `AMSLAM`, `AMQFCD`, `AMSALI`, owners, acres
- **Verified:** AMSLAM>0 count **44,481** (aligned with parcels)
- **Status:** usable

### 3. Addresses — situs / NG911 join

- **REST:** https://apps.alamance-nc.com/arcgis/rest/services/Addresses/FeatureServer/0
- **Geometry:** Point | count **113,342**
- **Join:** `PARENTGPIN` → parcels.`GPIN`
- **Fields:** `FULLADDRESS`, `NgFullAddress`, `Post_Comm`, `Post_Code`, `Inc_Muni`, `JURISDICTION`
- **Status:** usable

### 4. Burlington Zoning — ReGIS (city-first)

- **REST:** https://maps.regisnc.org/arcgis/rest/services/BurlZoningPublic/MapServer/3
- **Count:** **2,328** | `DIST_IDW` → zoning | `ZONECITYCODE`=12 only
- **Districts:** MDR, HDR, GB, OI, LI, NB, CB, CR, HI, RMH, CI, MI, MX, CBD, PD, LDR, *-LU
- **Status:** usable

### 5. Burlington Future Land Use

- **REST:** https://maps.regisnc.org/arcgis/rest/services/BURL_BASE/BurlFutureLU_Online/MapServer/2
- **Count:** **121** | `Future_Landuse` / `FLU_Code`
- **Status:** usable

### 6. Graham Zoning Districts — ReGIS

- **REST:** https://maps.regisnc.org/arcgis/rest/services/Graham/GrahZoningOnline/MapServer/5
- **Count:** **971** | `ZONEID` / `DIST_DESC` | CITYCODE=11
- **Twin:** GrahZoningCounty/MapServer/0
- **Status:** usable

### 7. Graham Future Land Use

- **REST:** https://maps.regisnc.org/arcgis/rest/services/Graham/GrahFutureLandUse/FeatureServer/1
- **Count:** **27** | `FutureLU` / `LU_Code`
- **Status:** usable

### 8. Elon Zoning — ReGIS

- **REST:** https://maps.regisnc.org/arcgis/rest/services/Elon_Base/ElonZoning/FeatureServer/3
- **Count:** **257** | `ZONE_ID` / `ZONE_DESC`
- **Status:** usable

### 9. Elon Land Use Districts (FLU-like)

- **REST:** https://maps.regisnc.org/arcgis/rest/services/Elon/ElonLandUseOnline/MapServer/3
- **Count:** **247** | `LU_CODE` / `LU_TYPE`
- **Status:** usable

### 10. Mebane Current Zoning — AGOL

- **REST:** https://services8.arcgis.com/pqfZyBvxpstAt1gO/arcgis/rest/services/Current_Zoning_Feature_Layer_(View)/FeatureServer/0
- **Count:** **7,446** | `Zoning` | join `PIN`≈`GPIN` | **CRS 3857**
- **Geo-verified:** sample centroid (−79.30, 36.07) in Mebane
- **Status:** usable

### 11. Mebane 2045 FLUM

- **REST:** …/Mebane_2045_Future_Land_Use_Map_WFL1/FeatureServer/8
- **Count:** **13,159** | `PLACETYPE` / `PT_CAT` | parcel-keyed | **CRS 3857**
- **Status:** usable

### 12. Watershed Overlay (NOT base zoning)

- **REST:** …/CountyWebsite/Combined/MapServer/86
- **Count:** **8,883** | `ZONINGTYPE` WCA=1848, BOW=7035
- **Status:** partial (overlay only)

### 13. NC OneMap Parcels — fallback

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='001'` | count **79,495**
- **Notes:** `gisacres` + `siteadd` populated for Alamance; no AMSLAM-quality price
- **Status:** partial

### 14. Municipalities + ETJ

- **Municipalities:** …/Municipalities/FeatureServer/0 — Burlington, Graham, Mebane, Elon, Gibsonville, Haw River, Green Level, Swepsonville, Ossipee, Village of Alamance, Whitsett
- **ETJ:** …/ETJ/FeatureServer/0
- **Status:** usable

## Municipalities (city-first routing)

| Municipality | Zoning REST | FLU REST | Notes |
|--------------|-------------|----------|-------|
| Burlington | ReGIS BurlZoningPublic/3 | BurlFutureLU_Online/2 | ReGIS member |
| Graham | GrahZoningOnline/5 | GrahFutureLandUse/1 | ReGIS member |
| Elon | Elon_Base/ElonZoning/3 | ElonLandUseOnline/3 | ReGIS member |
| Mebane | AGOL Current_Zoning View/0 | Mebane_2045 FLUM/8 | Spans Alamance+Orange; CRS 3857 |
| Gibsonville | gap | gap | No public FS found |
| Haw River | gap | gap | No public FS found |
| Green Level | gap | gap | No public FS found |
| Swepsonville | gap | gap | No public FS found |
| Ossipee / Village of Alamance | gap | gap | No public FS found |
| Unincorporated county | gap (base) | gap | Watershed WCA/BOW overlay only |

## Deep-link templates

- **Appraiser / property card:** `https://property.spatialest.com/nc/alamance/#/property/{PIN}` (6-digit `PIN`)
- **Viewer:** https://apps.alamance-nc.com/CountyGISMap/default.aspx
- **Open Data parcels:** https://alamancecounty-alamancectygis.opendata.arcgis.com/datasets/cedac0cddcd149fa874a2a7a22831604_0

## Gaps

- No public countywide **base** zoning FeatureServer for unincorporated Alamance
- `BurlingtonGIS` folder on county host requires token — use ReGIS public services
- Haw River / Gibsonville / Green Level / Swepsonville / Ossipee / Village of Alamance zoning/FLU REST gaps
- Watershed `ZONINGTYPE` is overlay only (easy to misread)
- Mebane CRS 3857 vs county 2264; Mebane crosses into Orange
- County comprehensive-plan FLU REST gap (Small Area Plan ≠ FLU place types)
- OneMap lacks county-quality sale price (`AMSLAM`)
- No phones/emails; no paid vendors; utilities + AADT out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- Live REST counts, field maps, sample attributes, and WGS84 centroids checked for county parcels, OneMap (`cntyfips='001'`), Burlington/Graham/Elon ReGIS, and Mebane AGOL.


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://apps.alamance-nc.com/arcgis/rest/services/Tax/AlamanceParcels/FeatureServer/0 polygons load (sample centroid [-79.541, 35.845]); `PIN` filled on 79,799 of 79,854; `ACRES` 5–150 ac **8,884**.
- **Attribute layer for Pass 2:** https://apps.alamance-nc.com/arcgis/rest/services/Tax/AlamanceParcels/FeatureServer/0 · id `PIN` · live count **79,854** · 5–150 ac **8,884** (`ACRES >= 5 AND ACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='ALAMANCE'` gives **890** stations (133 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27ALAMANCE%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Alamance'` gives **881** stations (772 with AADT_2025, 178 with AADT_2024, 860 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Alamance%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `JMTCTM` non-zero **78,849**, `XXTCAS` non-zero **78,597**
- **Sale history (ok):** price `AMSLAM` >0 **44,480**; date `DateSold` non-null **73,831**, `AMDTSL` non-null **73,831**. AMDTSL is a numeric yyyymmdd date; DateSold is the esri date version.
- **Owner entity:** field `OWNAM1`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **1,633** (all parcels: 12,001), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://property.spatialest.com/nc/alamance/#/property/{PIN}`. Tested `100412` (https://property.spatialest.com/nc/alamance/#/property/100412) → HTTP **200** (text/html; charset=UTF-8), content verified: False. Spatialest SPA (hash route): 200 shell, parcel content cannot be checked server-side.
- **Jurisdiction GIS viewer:** https://apps.alamance-nc.com/CountyGISMap/default.aspx → HTTP **200** (Alamance County, North Carolina GIS)
- **Pass 2 gaps:** PA content not verifiable (SPA)
