# Mecklenburg County, NC — GIS County Card

## Summary

Mecklenburg County (Charlotte MSA) publishes unusually rich **public** ArcGIS REST layers: countywide parcel polygons with ownership, mailing/situs address, assessed/market values, and last-sale fields (`TaxParcel_camadata`), plus a separate multi-million-row **TaxParcelSales** history layer. Zoning is split — City of Charlotte vs towns (Cornelius, Davidson, Huntersville, Matthews, Mint Hill, Pineville, Stallings) — and parcel-joined zoning is available on `ParcelsZoningZipcode`. Future land use is available as Charlotte **2040 Policy Map Place Types** (ArcGIS Online FeatureServer) and an older county “Future Land Use” overlay. NC OneMap statewide parcels (`cntyfips=119`) are a solid fallback with owner/values/sale. Main gaps: no single countywide zoning layer (must merge Charlotte + towns), Charlotte 2040 Place Types cover city jurisdiction only (not all towns), and some “vacant land” CAMA flags are inconsistent for filtering.

## Portals

- **Mecklenburg County GIS** — https://gis.mecknc.gov/ — County GIS division; links to POLARIS, GeoPortal, downloads.
- **POLARIS (Property Ownership Land Records)** — https://polaris3g.mecklenburgcountync.gov/ — Interactive ownership/map viewer. Deep link: `https://polaris3g.mecklenburgcountync.gov/pid/{pid}` (8-char PID).
- **Open Mapping data catalog** — https://maps.mecklenburgcountync.gov/openmapping/data.html — Downloadable parcels/zoning CSVs and layer docs.
- **meckgis ArcGIS Server** — https://meckgis.mecklenburgcountync.gov/server/rest/services — Primary REST host for tax parcels, sales, zoning.
- **meckags ArcGIS Server** — https://meckags.mecklenburgcountync.gov/server/rest/services — Tax/ParcelsViewer, stormwater/FLU overlays.
- **City of Charlotte GIS** — https://gis.charlottenc.gov/arcgis/rest/services — CountyData parcels, PLN zoning / AllParcelData.
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels FeatureServer (also `services.gis.nc.gov`).
- **Charlotte Future 2040 Policy Map viewer** — https://charlotte.maps.arcgis.com/apps/webappviewer/index.html?id=4dc02a1a85974085af7b36c33474efe0

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `nc_pin`, `pid`, `parcelid` (county); `parno` (NC OneMap) | Prefer `nc_pin` as stable join; `pid` for POLARIS links |
| polygons | Yes | All parcel layers below | County CRS mostly **WKID 102719 / 2264** (NC State Plane ft) |
| acreage | Yes | `gisacres`, `legalacres`, `totalac` | ~33.5k parcels in 5–150 ac on TaxParcel_camadata |
| ownerName | Yes | `ownrlstnme`+`ownrfrstnme` (CAMA); `ownname` (NC OneMap) | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `mailaddr1`,`mailaddr2`,`zipcode`,`state` / OneMap `mailadd` | |
| situs address | Yes | `address` or `streetnumber`+`streetname`+`loccity` / OneMap `siteadd` | |
| lastSale date/price | Yes | `saledate`,`saleprice` on CAMA; full history on TaxParcelSales | CAMA = latest; Sales layer = multi-transfer |
| tax values | Yes | `totlandval`,`totalbldgval`,`totalvalue`,`totmarkval` / OneMap `landval`,`improvval`,`parval` | |
| zoning | Yes (split) | `zone_class` on ParcelsZoningZipcode; Charlotte `zoneclass`/`ZoneClass`; towns `zone_des` | Must combine Charlotte + towns layers |
| FLU | Yes (partial) | 2040 `PlaceTypeFullTxt`/`PlaceTypeCde`; older `PropLuseTx`/`LuDesc` | 2040 = Charlotte ETJ/city; towns may lack Place Types |
| appraiser / viewer link | Yes | `https://polaris3g.mecklenburgcountync.gov/pid/{pid}` | PID path param (not PIN) |

## Layers (verified)

### 1. TaxParcel_camadata — parcels + ownership + tax + last sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last)
- **REST URL:** https://meckgis.mecklenburgcountync.gov/server/rest/services/TaxParcel_camadata/FeatureServer/0 (switched 2026-09-28; the MapServer/0 twin `https://meckgis.mecklenburgcountync.gov/server/rest/services/TaxParcel_camadata/MapServer/0` returns null geometry on query)
- **Layer name / id:** TaxParcel_camadata / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `nc_pin` → id (NC PIN)
  - `pid` → parcelId / POLARIS key
  - `parcelid` → alternate parcel id (sales join)
  - `gisacres`, `legalacres`, `totalac` → acreage
  - `ownrlstnme`, `ownrfrstnme`, `ownr2lstnme`, `ownr2frstnme` → ownerName
  - `mailaddr1`, `mailaddr2`, `zipcode`, `state` → mailing address
  - `address`, `streetnumber`, `streetname`, `loccity`, `city` → situs address
  - `saledate`, `saleprice` → lastSale
  - `totlandval`, `totalbldgval`, `totalvalue`, `totmarkval`, `totalyardval` → tax values
  - `landuse_description`, `lusecode`, `vacorimprov`, `resunits`, `yearbuilt` → other (use filters carefully)
- **WKID / CRS:** 102719 (latest 2264) — NAD 1983 StatePlane NC Feet
- **Verified:** yes — `returnCountOnly` → **448,526**; sample query on 5–150 ac returned owner/tax/sale attrs
- **Notes:** Best single county layer for multifamily land search attribute upgrade. Zoning **not** on this layer — join `nc_pin`/`pid` to ParcelsZoningZipcode or spatial-join zoning polygons. MaxRecordCount 2000 — page queries.

### 2. Tax/ParcelsViewer — clean parcel polygons (geometry / PIN)

- **Purpose:** parcels
- **REST URL:** https://meckags.mecklenburgcountync.gov/server/rest/services/Tax/ParcelsViewer/MapServer/0
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `nc_pin` → id
  - `pid` → parcelId
  - `gisacres` → acreage
  - `map_book`,`map_page`,`map_block`,`lot_num` → assessor map refs
  - *(no owner, tax, sale, zoning)*
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **397,300**
- **Notes:** Geometry-focused; thinner attribute set than TaxParcel_camadata. Good for polygon-only sync.

### 3. CountyData/Parcels (City of Charlotte host) — thin polygons

- **Purpose:** parcels
- **REST URL:** https://gis.charlottenc.gov/arcgis/rest/services/CountyData/Parcels/MapServer/0
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:** `NC_PIN`, `PID` → id/parcelId; map book fields; **no owner/tax**
- **WKID / CRS:** **102100 / 3857** (Web Mercator) — different from county 2264
- **Verified:** yes — count **397,300**
- **Notes:** Prefer meckgis/meckags layers in State Plane unless you need 3857. Useful cross-check only.

### 4. PLN/AllParcelData — City-hosted CAMA join (alternate rich parcels)

- **Purpose:** parcels | tax | ownership | sales (last)
- **REST URL:** https://gis.charlottenc.gov/arcgis/rest/services/PLN/AllParcelData/MapServer/0
- **Layer name / id:** All Parcel Data / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parcelid`, `propertyid` → parcelId
  - `owner1lastname`,`owner1firstname` (+ owner2/3) → ownerName
  - `billingaddress`,`billingaddress2`,`zipcode`,`state` → mailing
  - `location_address`,`streetnumber`,`streetname`,`locationcity` → situs
  - `saleprice`,`saledate` → lastSale
  - `totallandvalue`,`totalbuildingvalue`,`totalvalue`,`totalmarketvalue` → tax
  - `legalacres`,`landsize` → acreage
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **429,007**; metadata confirmed
- **Notes:** Parallel to TaxParcel_camadata with slightly different field names. Prefer **TaxParcel_camadata** as county canonical unless city host is more reliable for you.

### 5. ParcelsZoningZipcode — parcels with joined zoning + ZIP

- **Purpose:** parcels | zoning | other (zip)
- **REST URL:** https://meckgis.mecklenburgcountync.gov/server/rest/services/ParcelsZoningZipcode/FeatureServer/0
- **Layer name / id:** ParcelZoningZipcode / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `nc_pin`, `pid` → id / parcelId
  - `gisacres` → acreage
  - `zone_class` (alias zone_des) → **zoning**
  - `zip`, `po_name` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **454,837**; sample showed `zone_class` like `N1-A`
- **Notes:** Fastest path to attach zoning to parcels without spatial join. Does not replace full zoning polygon attributes (overlays, petitions).

### 6. City of Charlotte Zoning

- **Purpose:** zoning
- **REST URL:** https://meckgis.mecklenburgcountync.gov/server/rest/services/CityofCharlotteZoning/MapServer/0
- **Alternate (city host):** https://gis.charlottenc.gov/arcgis/rest/services/PLN/Zoning/MapServer/0
- **Layer name / id:** City of Charlotte Zoning / Zoning / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `zoneclass` / `ZoneClass` → zoning (classification)
  - `zonedes` / `ZoneDes` → zoning code/label
  - `overlay` / `Overlay` → zoning overlay
  - `zonepetition`, `rezonedate`, `hyperlink` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **5,689** (both hosts)
- **Notes:** Charlotte + ETJ / planning area only. Towns are on a separate layer.

### 7. Unincorporated County and Towns Zoning

- **Purpose:** zoning
- **REST URL:** https://meckgis.mecklenburgcountync.gov/server/rest/services/UnincorporatedCountyandTownsZoning/MapServer/0
- **Layer name / id:** Unincorporated County and Towns Zoning / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `zone_des` → zoning
  - `munic` → jurisdiction (CORNELIUS, DAVIDSON, HUNTERSVILL, MATTHEWS, MINT HILL, PINEVILLE, STALLINGS)
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **977**; distinct `munic` values listed above (no null munic)
- **Notes:** Despite the name, verified munic list is **towns** (not a separate “unincorporated only” code). Combine with Charlotte zoning for countywide coverage. Spatial join to parcels or use ParcelsZoningZipcode for parcel-level zone.

### 8. TaxParcelSales — sale history

- **Purpose:** sales
- **REST URL:** https://meckgis.mecklenburgcountync.gov/server/rest/services/TaxParcelSales/FeatureServer/0
- **Layer name / id:** Tax Parcel Sales / 0
- **Geometry:** Polygon (parcel footprint per sale record)
- **Key fields → targets:**
  - `parcelid` → join to TaxParcel_camadata.`parcelid`
  - `saledate`, `saleprice` → lastSale / sale history
  - `grantor`, `grantee` → ownership transfer parties (often null on recent TEMP rows)
  - `salesvalidity`, `landuse`, `soldasvacantflag`, `deeddescription`, `legalreference` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **1,598,048**
- **Notes:** True multi-sale history. Filter `salesvalidity` for usable comps. Join key is `parcelid`, not always `nc_pin`.

### 9. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (last) | other
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1 *(layer 0 = points)*
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parno` → parcelId (Mecklenburg samples align with PID-style ids)
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs
  - `gisacres` → acreage
  - `saledate`,`saledatetx` → lastSale date
  - `parval`,`landval`,`improvval` → tax values
  - `parusecode`,`parusedesc` → other land use
  - `cntyfips`=`119`, `cntyname` → Mecklenburg filter
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — Mecklenburg filter count **442,287**; sample features returned owner/site/mail/values/sale
- **Notes:** Excellent fallback / cross-county schema. May lag county CAMA. Prefer local TaxParcel_camadata when present. MaxRecordCount 5000.

### 10. Charlotte Future 2040 Policy Map (Place Types) — FLU

- **Purpose:** FLU (future land use / Place Types)
- **REST URL:** https://services.arcgis.com/9Nl857LBlQVyzq54/arcgis/rest/services/Charlotte_Future_2040_Policy_Map/FeatureServer/0
- **Layer name / id:** Charlotte Future 2040 Policy Map / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PlaceTypeFullTxt`, `PlaceTypeCde` → FLU
  - `AdoptionType`, `AdoptionDate`, `CommunityPlanningArea` → other
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **5,640**
- **Notes:** Official Charlotte Place Types (Neighborhood 1/2, centers, employment, etc.). Spatial-join to parcels. City jurisdiction — not town-wide.

### 11. Revised Charlotte Future 2040 Policy Map — FLU (working/revision)

- **Purpose:** FLU
- **REST URL:** https://services.arcgis.com/9Nl857LBlQVyzq54/arcgis/rest/services/Revised_Charlotte_Future_2040_Policy_Map/FeatureServer/0
- **Layer name / id:** Revised Charlotte Future 2040 Policy Map / 0
- **Geometry:** Polygon
- **Key fields → targets:** `AdoptedPlaceTypeCde`/`AdoptedTypeFullTxt`, `RevisedPlaceTypeCde`/`RevisedPlaceTypeFullTxt` → FLU
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **12,092**
- **Notes:** Prefer **adopted** Policy Map (layer 10) for production unless product wants draft revisions.

### 12. County “Future Land Use” overlay (area plans) — FLU fallback

- **Purpose:** FLU
- **REST URL:** https://meckags.mecklenburgcountync.gov/server/rest/services/StormWater/FloodOverlaysTransparent/MapServer/1
- **Layer name / id:** Future Land Use / 1
- **Geometry:** Polygon
- **Key fields → targets:** `PropLuseTx`, `PropLuseCd`, `GenLuse`, `LuDesc`, `PlanName` → FLU
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **80,313**
- **Notes:** Older neighborhood/area-plan FLU (`PlanName` often `NP`). Use as secondary to 2040 Place Types; do not treat as current Charlotte policy alone.

## Gaps

- **No single countywide zoning FeatureServer** — must union Charlotte zoning + towns zoning, or use ParcelsZoningZipcode for parcel-level codes only.
- **Charlotte 2040 Place Types do not cover all towns** — town FLU may be missing or only in local plans; area-plan FLU overlay is incomplete/legacy.
- **True “unincorporated-only” zoning polygons** not cleanly separated in the towns layer munic list (towns only in verified distinct values).
- **Owner phones/emails** not on these APIs (correct — do not scrape).
- **TaxParcel_camadata `vacorimprov` vacant filter** returned 0 in a spot check — validate enum values before using as vacant-land filter; prefer land-use codes / building value / sales vacant flag.
- **NC OneMap lag / schema mapping** — `parno` vs `nc_pin`/`pid` needs careful join testing.
- **Rate limits / MaxRecordCount** — county layers typically 2000; OneMap 5000; must paginate (`resultOffset` / `resultRecordCount`).
- **No paid vendor data** used or required (CoreLogic/Regrid paid/ATTOM avoided).

## Hand-off notes for Land Search Builder

1. **Wire first:** `TaxParcel_camadata/FeatureServer/0` (not MapServer/0, which returns null geometry) for polygons + attributes (owner, mailing, situs, acreage, tax, last sale). Filter `gisacres BETWEEN 5 AND 150` (~33.5k features).
2. **Join zoning:** `ParcelsZoningZipcode` on `nc_pin` or `pid` → `zone_class`. Optionally enrich with Charlotte/towns zoning polygons for overlays.
3. **Sale history (optional enrich):** `TaxParcelSales` on `parcelid`; keep CAMA `saledate`/`saleprice` as lastSale.
4. **FLU:** Spatial join adopted Charlotte 2040 Policy Map Place Types; fall back to area-plan FLU layer outside coverage.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='119'` if county host is down.
6. **Viewer link template:** `https://polaris3g.mecklenburgcountync.gov/pid/{pid}`
7. **Join keys:** Prefer `nc_pin` (10-digit) across county layers; `pid` for POLARIS; `parcelid` for sales. Reproject only if mixing with Charlotte CountyData layer (3857).
8. **Auth:** None observed for listed public query endpoints (`f=json` / GeoJSON). Be polite with pagination; no scraping of POLARIS HTML for PII beyond these public fields.
9. **City vs county zoning split:** Charlotte (incl. planning area) vs towns listed above — never assume Charlotte zoning alone covers Mecklenburg.

## Enrichment — household income (2026-09-24)

```yaml
enrichment:
  householdIncome:
    defaultSource: "Census ACS B19013 tract medians (national join)"
    localException:
      name: "Charlotte Quality of Life Explorer — Household Income (NPA)"
      restUrl: "https://gis.charlottenc.gov/arcgis/rest/services/QOL/Quality_of_Life_Latest_Profile_Data/MapServer/17"
      layerId: 17
      geography: "Neighborhood Profile Area (NPA)"
      field: "Val_Norm"
      whyBetter: "Custom Charlotte NPA polygons with documented ACS-to-NPA median interpolation (QOL Explorer); not a republish of ACS tract/BG polygons."
      verifiedAt: "2026-09-24"
      verifiedBy: "Public Information Researcher"
```


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (fixed):** https://meckgis.mecklenburgcountync.gov/server/rest/services/TaxParcel_camadata/FeatureServer/0 polygons load (sample centroid [-80.6302, 35.2286]); `nc_pin` filled on 448,582 of 448,582; `gisacres` 5–150 ac **33,566**. TaxParcel_camadata/MapServer/0 answers counts and attributes but returns geometry=null on every query (json and geojson), so polygons do not load. The same service's FeatureServer/0 returns rings with identical fields and counts. Card primary switched to FeatureServer/0; MapServer/0 kept as an alternate. Row count 448,582 is CAMA rows; clean polygon count on Tax/ParcelsViewer/MapServer/0 is 397,384 (condo/multi-row parcels).
- **Attribute layer for Pass 2:** https://meckgis.mecklenburgcountync.gov/server/rest/services/TaxParcel_camadata/FeatureServer/0 · id `nc_pin` · live count **448,582** · 5–150 ac **33,566** (`gisacres >= 5 AND gisacres <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='MECKLENBURG'` gives **1969** stations (1793 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27MECKLENBURG%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Mecklenburg'` gives **1951** stations (434 with AADT_2025, 1816 with AADT_2024, 1833 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Mecklenburg%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `totalvalue` non-zero **432,952**, `totmarkval` non-zero **432,952** Counts are CAMA rows (448,582 total), not distinct polygons.
- **Sale history (ok):** price `saleprice` >0 **310,264**; date `saledate` non-null **447,317**. Full history on TaxParcelSales/FeatureServer/0 (join parcelid).
- **Owner entity:** field `ownrlstnme`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **18,762** (all parcels: 107,602), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://polaris3g.mecklenburgcountync.gov/pid/{pid}`. Tested `10511290` (https://polaris3g.mecklenburgcountync.gov/pid/10511290) → HTTP **200** (text/html), content verified: True. POLARIS page embeds parcel data in the server HTML (owner name and PID present in the response).
- **Jurisdiction GIS viewer:** https://polaris3g.mecklenburgcountync.gov/ → HTTP **200** (Polaris)
- **Municipal zoning/FLU layers re-checked:** 6 of 6 answer.
- **Pass 2 gaps:** pass1 fixed: MapServer/0 null geometry, switched to FeatureServer/0
