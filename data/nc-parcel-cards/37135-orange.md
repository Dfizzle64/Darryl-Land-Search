# Orange County, NC — GIS County Card

## Summary

Orange County (Raleigh–Durham MSA / Triangle, FIPS **37135**) publishes rich **public** ArcGIS REST at `gis.orangecountync.gov`: countywide **tax parcel polygons** with ownership, mailing, GIS/deed acreage, land/building/total valuation, last-sale date, and tax-stamp–derived sale value on `WebParcelService` (and CAMA-rich mirrors on `WebIdentifyService*` / Chapel Hill OpenData `OrangeCountyParcels`). **Situs is not on the parcel polygon** — join address points by `PIN`. **Zoning is city-first**: county `WebZoningService` has real district codes only for **unincorporated** County (`Zoning` e.g. AR/R1/EC5); for Chapel Hill / Carrboro / Hillsborough the county layer is **jurisdiction placeholders** (`CH`/`CA`/`HI`) — use **municipal** zoning REST. **FLU** is public for **county Land Use Element**, **Chapel Hill Future Land Use Map 2050**, and **Hillsborough Land Use**; **Carrboro FLU REST = gap** (zoning REST is strong). **NC OneMap** (`cntyfips='135'`) is a usable fallback for owner/mail/values/sale date + `recareano` acres (`gisacres` and `siteadd` are empty for Orange). Main gaps: no situs on parcels; municipal zoning must be spatial-joined; Carrboro FLU; OneMap acreage/situs thin; last sale price is stamp-derived not deed consideration.

## Portals

- **Interactive GIS (ARIES / Highland Mapping)** — https://gis.orangecountync.gov/orangencgis/default.htm — Search PIN, owner, address, account; Tax Card deep link from parcel.
- **County ArcGIS REST** — https://gis.orangecountync.gov/arcgis/rest/services
- **Download GIS Data** — https://www.orangecountync.gov/2057/Download-GIS-Data — also https://web.orangecountync.gov/gisdownloads/ (Parcels.zip, Zoning_and_Overlays.zip, Addresses.zip, MunicipalGDB.gdb, Jan1_2026 parcels).
- **PIN / ownership history** — https://web.orangecountync.gov/pinmanagementweb/ — deep link `?pin={PIN}` (10-digit).
- **Property Record Portal (Spatialest)** — https://property.spatialest.com/nc/orange/#/ — deep link `#/property/{PIN}`.
- **Tax bill search** — https://web.co.orange.nc.us/publicwebaccess/
- **Register of Deeds** — https://rod.orangecountync.gov/orangenc/
- **Town of Chapel Hill GIS OpenData** — https://gis-portal.townofchapelhill.org/server/rest/services/OpenData
- **Chapel Hill gisweb** — https://gisweb.townofchapelhill.org/arcgis/rest/services
- **Town of Carrboro GIS** — https://gis.carrboronc.gov/server/rest/services — https://www.townofcarrboro.org/142/Geographic-Information-Systems-GIS
- **Town of Hillsborough zoning (AGOL)** — https://services5.arcgis.com/m711BZ7Df3seMOYp/arcgis/rest/services/ZoningLayersII/FeatureServer
- **NC OneMap** — https://www.nconemap.gov — statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`).

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`, `PINLINK`, `ACCOUNT`; OneMap `parno` | Prefer 10-digit `PIN` |
| polygons | Yes | WebParcelService/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALC_ACRES`, `SIZE`+`UOM`=`A`; OneMap `recareano` | ~**9,375** CALC_ACRES 5–150; ~**9,505** SIZE A 5–150 |
| ownerName | Yes | `OWNER1` / `OWNER1_LAST`+`OWNER1_FIRST` (+ OWNER2*) | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `ADDRESS1`,`ADDRESS2`,`CITY`,`STATE`,`ZIPCODE` | On parcels = **mailing** (often PO Box / owner city) |
| situs address | Yes (join) | Address `Add_St` / `NG_FullAddress`; `MailingCity`,`ZipCode`; OneMap `siteadd` empty | **Not** on parcel polygons — join by `PIN` |
| lastSale date/price | Yes (partial) | `DATESOLD`/`DATESOLDTXT`; `STAMPVALUE`/`TAXSTAMPS` | Stamp value ≈ consideration proxy (e.g. stamps×500); not full deed price |
| tax values | Yes | `VALUATION`,`LANDVALUE`,`BLDGVALUE`,`USEVALUE` | |
| zoning | Yes (split) | County `Zoning`; CH `ZONING`; Carrboro `ZONING`; Hillsborough `ZoningType`; parcel `Zonings` **County-only** | Spatial join by municipality — see Municipalities |
| flu | Yes (partial) | County `Legend`; CH `LANDUSE`; Hillsborough `MH_LU` | Carrboro FLU REST gap |
| appraiser / viewer link | Yes | Spatialest + PIN app + GIS viewer | Templates below |

## Layers (verified)

### 1. WebParcelService Parcels — parcels + ownership + tax + last sale + zoning admin (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last) | zoning hint
- **REST URL:** https://gis.orangecountync.gov/arcgis/rest/services/WebParcelService/MapServer/0
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN`, `PINLINK` → parcelId
  - `ACCOUNT` → tax account
  - `CALC_ACRES`, `SIZE`, `UOM` (`A`=acres) → acreage
  - `OWNER1`, `OWNER1_LAST`+`OWNER1_FIRST`, `OWNER2*` → ownerName
  - `ADDRESS1`,`ADDRESS2`,`CITY`,`STATE`,`ZIPCODE` → mailing
  - `DATESOLD`,`DATESOLDTXT` → lastSale.date
  - `STAMPVALUE`,`TAXSTAMPS` → lastSale.price (stamp proxy)
  - `VALUATION`,`LANDVALUE`,`BLDGVALUE`,`USEVALUE` → tax
  - `Zonings` → zoning (**populated for County only**)
  - `Zoning_Admin` → routing key (Chapel Hill / Carrboro / Hillsborough / County / Mebane / Durham)
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **59,643**; `CALC_ACRES BETWEEN 5 AND 150` → **9,375**; `UOM='A' AND SIZE BETWEEN 5 AND 150` → **9,505**; sample owner/tax/sale OK
- **Notes:** **PRIMARY** wire-first. No situs. `Zonings` empty for municipal admins — spatial-join city zoning. MaxRecordCount **2000**. Prefer `CALC_ACRES` for GIS filter; `SIZE`+`UOM='A'` for deeded acres.

### 2. WebIdentifyServiceAnalysis Parcels — CAMA mirror (slightly larger count)

- **Purpose:** parcels | tax | ownership | sales
- **REST URL:** https://gis.orangecountync.gov/arcgis/rest/services/WebIdentifyServiceAnalysis/MapServer/0
- **Alternate same schema:** https://gis.orangecountync.gov/arcgis/rest/services/WebIdentifyService/MapServer/6
- **Geometry:** Polygon
- **Key fields:** Same CAMA family as WebParcelService (PIN, owners, ADDRESS*, SIZE/UOM/CALC_ACRES, LANDVALUE/BLDGVALUE/VALUATION, DATESOLD/STAMPVALUE) — **no** `Zonings`/`PINLINK`/`ACCOUNT` on Identify layer
- **Verified:** yes — count **60,449**; `CALC_ACRES` 5–150 → **9,953**
- **Notes:** Use when needing max parcel count; prefer WebParcelService for zoning admin + PINLINK + ACCOUNT.

### 3. Addresses — situs join (PRIMARY situs)

- **Purpose:** other (situs)
- **REST URL:** https://gis.orangecountync.gov/arcgis/rest/services/WebIdentifyServiceAnalysis/MapServer/1
- **Alternates:** https://gis.orangecountync.gov/arcgis/rest/services/LRCAMA/WebCamaAddresses/MapServer/0 (count **86,431**); WebMainService/29
- **Layer name / id:** Addresses / 1
- **Geometry:** Point
- **Key fields → targets:**
  - `PIN` → join to parcels
  - `Add_St`, `NG_FullAddress`, `LSt_FullAddress` → situsAddress
  - `MailingCity`, `ZipCode`, `State` → situsCity / situsZip (postal city on point layer)
  - `HouseNum`,`DirPrefix`,`Name`,`Type`,`DirSuffix`,`UnitNum` → situs parts
  - `PrimaryFlag`, `Inc_Muni`, `TaxJuris` → prefer primary / route municipality
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — Analysis count **81,837**; sample `Add_St`+`PIN` OK
- **Notes:** Many-to-one vs parcels. Prefer `PrimaryFlag` when set. Do **not** harvest contact/phone-like fields if present elsewhere.

### 4. WebZoningService Zoning — countywide zoning polygons (County districts + muni jurisdiction shells)

- **Purpose:** zoning
- **REST URL:** https://gis.orangecountync.gov/arcgis/rest/services/WebZoningService/MapServer/22
- **Alternates:** WebMainService/51; WebIdentifyServiceAnalysis/21; TJCOG mirror https://services9.arcgis.com/B3YuzcpeophF9xOv/arcgis/rest/services/Orange_County_2025_Zoning/FeatureServer/0 (3857)
- **Geometry:** Polygon
- **Key fields:** `Zoning`, `Zoning_Def`, `Label`, `Jur`, `Zoning_Admin`, `City_Jur`, `Name`, `Acres`
- **Verified:** yes — count **362**
  - Jur=County **295** (real districts: AR, R1–R8, EC5, …)
  - Jur=Chapel Hill **6**, Carrboro **6**, Hillsborough **28**, Mebane **24**, Durham **3** — these are **limits/ETJ shells** (`Zoning`=`CH`/`CA`/`HI`/`ME`), **not** district codes
- **Join to parcels:** spatial join (intersect/centroid) in **2264**. Filter `Zoning_Admin` / `Jur`=`County` for unincorporated district codes; for municipalities use municipal layers below.
- **Notes:** Parcel attribute `Zonings` only filled when Zoning_Admin is County (~**25,714**). Never treat county shell polys as Chapel Hill/Carrboro/Hillsborough district zoning.

### 5. Future_Land_Use_Map — county FLU (Land Use Element)

- **Purpose:** flu
- **REST URL:** https://gis.orangecountync.gov/arcgis/rest/services/Future_Land_Use_Map/MapServer/12
- **Same content mirror:** layer **5** City Jurisdictions (same Legend schema)
- **Geometry:** Polygon
- **Key fields:** `Legend` → flu; `Acres`
- **Verified:** yes — count **143**; Legend values include Agricultural Residential, Rural Residential, Rural Buffer, Commercial Node, Commercial Industrial Node, Rural Community/Neighborhood/Industrial Node, Chapel Hill/Carrboro/Hillsborough/Mebane/Eno **10/20 Year Transition**, Economic Development Transition, City Limits, ETJ
- **Notes:** County comprehensive-plan FLU / transition framework — **not** a substitute for Chapel Hill 2050 or Hillsborough MH_LU inside towns.

### 6. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parno` → parcelId (aligns with county PIN)
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs (**empty for Orange** in current feed)
  - `recareano` → acreage (~**9,502** in 5–150); **`gisacres` all 0** for Orange
  - `saledate`,`saledatetx` → lastSale.date (**no sale price**)
  - `parval`,`landval`,`improvval` → tax
  - `cntyfips`=`135`
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — filter count **59,366**; sample owner/mail/values OK
- **Notes:** Prefer county WebParcelService. Use OneMap when county host down. MaxRecordCount **5000**. Filter empty `parno`.

### 7. Municipal Boundary — jurisdiction polygons

- **Purpose:** other (municipality filter)
- **REST URL:** https://gis.orangecountync.gov/arcgis/rest/services/WebMainService/MapServer/52
- **Field:** `NAME` / `CITYCODE` — CHAPEL HILL (CH), HILLSBOROUGH (HI), CARRBORO (verify), DURHAM (DU), MEBANE, etc.
- **Verified:** yes — count **84** (multipart annexation pieces)
- **Notes:** Use with parcel `Zoning_Admin` to route which zoning/FLU layer to spatial-join.

## Municipalities (first-class)

County parcels are countywide; **district zoning and FLU are municipal** inside towns. Join pattern: start from county WebParcelService (2264) → route by `Zoning_Admin` / Municipal Boundary → spatial join matching city zoning (and FLU). Chapel Hill FLU 2050 is **3857** — reproject before overlay with county **2264**.

### Town of Chapel Hill

- **Zoning (OpenData, preferred):** https://gis-portal.townofchapelhill.org/server/rest/services/OpenData/Zoning_Districts/FeatureServer/0 — `ZONING`, `NAME`, `OLD_ZONING`; count **313**; CRS **2264**. Codes include R*, CC, NC, IND, MU-V, MU-R-1, MU-OI-1, HR-*, LI-CZD, etc.
- **Overlay zoning:** https://gis-portal.townofchapelhill.org/server/rest/services/OpenData/Overlay_Zoning_Districts/FeatureServer/0 — count **18**; CRS **2264**
- **OpenGov mirror:** https://gisweb.townofchapelhill.org/arcgis/rest/services/OpenGov/OpenGovLayers/MapServer/21
- **FLU — Future Land Use Map 2050:** https://services2.arcgis.com/7KRXAKALbBGlCW77/arcgis/rest/services/Future_Land_Use_Map_2050/FeatureServer/8 — `LANDUSE`, `DU_S`, `Description`; count **408**; CRS **3857**. Categories: Rural Residential, Low/Medium/High/Very Low Residential, Mixed Use, Mixed Use/Office, Town/Village Center, Commercial, Office, Institutional, University, Parks/Open Space, Rural Buffer, Landfill, Ld-5, Carrboro (edge)
- **Existing land use (not FLU):** https://gisweb.townofchapelhill.org/arcgis/rest/services/MapServices/Existing_Land_Use/FeatureServer/0 — `LANDUSE`; count **1484**; CRS **2264**
- **City parcel mirrors (optional):** OpenData/OrangeCountyParcels (countywide attrs, count ~60k); OpenData/AllParcels (sparse PIN/Owner, inflated count)
- **Join note:** city zoning (2264) + county parcels (2264) spatial join. FLU 2050 → reproject **3857→2264**. Attribute join key: `PIN`. County `Zonings` is empty for Chapel Hill — do not rely on parcel attribute.

### Town of Carrboro

- **Zoning base (PRIMARY for Carrboro):** https://gis.carrboronc.gov/server/rest/services/SP/ZoningSP/MapServer/30 — `ZONING`, `DEFINITION`, `WEBPAGE`; count **81**; CRS **2264**. Districts include RR, R-*, B*, VMU, etc.
- **Conditional / PUD:** https://gis.carrboronc.gov/server/rest/services/SP/ZoningSP/MapServer/20 — `ZONING`, `PINs`, `ZoneType`; count **18**; may attribute-join via `PINs`
- **Overlay:** https://gis.carrboronc.gov/server/rest/services/SP/ZoningSP/MapServer/10 — `ZONING`, `DEFINITION`; count **6** (EAT, JLWP, NPD, …)
- **Downloads:** shapefile packages via https://www.townofcarrboro.org/142/Geographic-Information-Systems-GIS
- **FLU:** **no public FeatureServer found** (gap) — PDF/plan only
- **Join note:** Carrboro ZoningSP + county parcels (both **2264**). Ignore Chapel Hill-hosted `Carrboro_Data` “Zoning Jurisdiction” (boundary only, 4 polys, no district codes). County layer Jur=Carrboro is ETJ/limits shell only.

### Town of Hillsborough

- **Zoning districts (PRIMARY for Hillsborough):** https://services5.arcgis.com/m711BZ7Df3seMOYp/arcgis/rest/services/ZoningLayersII/FeatureServer/3 — `ZoningType`, `ZoningCategory`; count **207**; CRS **2264**. Types: AR, R10/R15/R20/R40, MF, MHP, OI, NB, CC, GC, HIC, GI, LI, EDD, BP, ALN, ARU, LO, RSU, CCSU, ESU, MFSU, NBSU, …
- **Overlays:** ZoningLayersII/FeatureServer/2 — count **3** (HD Overlay, PO, …)
- **FLU — Hillsborough Land Use:** https://services5.arcgis.com/m711BZ7Df3seMOYp/arcgis/rest/services/HillsboroughLandUseII/FeatureServer/3 — `MH_LU`; count **31**; CRS **2264**. Values: Attached Residential, Education, Employment, Light Industrial, Medium-Density Residential, Mixed Residential Neighborhood, Mixed Use, Neighborhood Mixed Use, Permanent Open Space, Retail Services, Rural Living, Small Lot Residential, Suburban Office, Town Center, Urban Neighborhood, Working Farm
- **Interactive web map:** https://www.arcgis.com/apps/mapviewer/index.html?webmap=3271f6d72ba74dd9b49a1f8c2de78cdf
- **Join note:** Hillsborough zoning/FLU + county parcels (2264). County Jur=Hillsborough polys are limits/ETJ only.

### City of Mebane (Alamance + Orange edge)

- County zoning layer has Jur=Mebane shells only (`Zoning`=`ME`). No Orange-hosted Mebane district FeatureServer verified here — treat as **edge / gap** for district codes inside Orange; filter with MunicipalBoundary / `Zoning_Admin`.

### City of Durham (edge)

- Tiny Orange footprint (`Zoning_Admin`≈20 parcels). Prefer Durham County GIS for district zoning if needed; county Orange layer only has Durham shells.

## Gaps

- **Situs missing on primary parcel polygons** — must join Addresses by `PIN` (OneMap `siteadd` empty for Orange).
- **Municipal district zoning not on county Zoning layer** — CH/CA/HI are jurisdiction placeholders; use Chapel Hill / Carrboro / Hillsborough REST.
- **Parcel `Zonings` attribute County-only** — empty for Chapel Hill (~17.8k), Carrboro (~6.7k), Hillsborough (~5.5k).
- **Carrboro FLU** — no public REST FeatureServer found.
- **Sale price** is tax-stamp–derived (`STAMPVALUE`), not full multi-transfer deed history.
- **OneMap** `gisacres`=0 and `siteadd` empty for Orange — use `recareano` + county situs join.
- **Chapel Hill FLU CRS** 3857 vs county 2264 — transform before spatial join.
- **MaxRecordCount** 2000 on county layers; OneMap 5000 — paginate.
- **Owner phones/emails** not collected (do not scrape Spatialest / PIN app PII beyond public REST fields).
- **No paid vendor data** used (CoreLogic/Regrid/ATTOM avoided).
- **Mebane / Durham edge** district zoning not wire-first from Orange hosts.

## Hand-off notes for Land Search Builder

1. **Wire first:** `WebParcelService/MapServer/0` — polygons + owner, mailing, acreage, tax, last sale date/stamp value, Zoning_Admin. Filter `CALC_ACRES BETWEEN 5 AND 150` (~9.4k) or `UOM='A' AND SIZE BETWEEN 5 AND 150` (~9.5k).
2. **Situs join:** Addresses (`WebIdentifyServiceAnalysis/1` or `LRCAMA/WebCamaAddresses/0`) on `PIN` → `Add_St` / `NG_FullAddress`.
3. **Zoning:** route by `Zoning_Admin` / Municipal Boundary:
   - County → WebZoningService/22 where `Jur='County'` (or parcel `Zonings`)
   - Chapel Hill → OpenData Zoning_Districts/0 (+ overlays)
   - Carrboro → ZoningSP/30 (+ /20, /10)
   - Hillsborough → ZoningLayersII/3 (+ overlays /2)
4. **FLU:** spatial join county Future_Land_Use_Map/12; Chapel Hill FLU 2050/8 (reproject); Hillsborough LandUseII/3; leave null for Carrboro.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='135'` (use `recareano` for acres).
6. **Viewer / appraiser links:**
   - Spatialest: `https://property.spatialest.com/nc/orange/#/property/{PIN}`
   - PIN app: `https://web.orangecountync.gov/pinmanagementweb/?pin={PIN}`
   - GIS viewer: `https://gis.orangecountync.gov/orangencgis/default.htm`
   - Tax bills: `https://web.co.orange.nc.us/publicwebaccess/`
7. **Join keys:** `PIN` (10-digit preferred), `ACCOUNT`, OneMap `parno`↔`PIN`.
8. **Auth:** none observed on listed public query endpoints (Chapel Hill portal may require browser User-Agent; no token on OpenData FeatureServers tested).
9. **Cities are first-class:** never treat county Zoning MapServer alone as countywide district coverage.


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://gis.orangecountync.gov/arcgis/rest/services/WebParcelService/MapServer/0 polygons load (sample centroid [-78.9993, 35.9615]); `PIN` filled on 59,643 of 59,643; `CALC_ACRES` 5–150 ac **9,374**.
- **Attribute layer for Pass 2:** https://gis.orangecountync.gov/arcgis/rest/services/WebParcelService/MapServer/0 · id `PIN` · live count **59,643** · 5–150 ac **9,374** (`CALC_ACRES >= 5 AND CALC_ACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='ORANGE'` gives **521** stations (173 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27ORANGE%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Orange'` gives **518** stations (407 with AADT_2025, 172 with AADT_2024, 498 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Orange%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `VALUATION` non-zero **58,623**, `LANDVALUE` non-zero **54,470**
- **Sale history (ok):** price `STAMPVALUE` >0 **32,609**; date `DATESOLD` non-null **59,208**. STAMPVALUE is the price implied by excise stamps (TAXSTAMPS × 500), not a recorded price.
- **Owner entity:** field `OWNER1`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **2,002** (all parcels: 12,679), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://property.spatialest.com/nc/orange/#/property/{PIN}`. Tested `0800062560` (https://property.spatialest.com/nc/orange/#/property/0800062560) → HTTP **200** (text/html; charset=UTF-8), content verified: False. Spatialest SPA (hash route): 200 shell, parcel content cannot be checked server-side. Alt: https://web.orangecountync.gov/pinmanagementweb/?pin={PIN}.
- **Jurisdiction GIS viewer:** https://gis.orangecountync.gov/orangencgis/default.htm → HTTP **200** ()
- **Municipal zoning/FLU layers re-checked:** 14 of 14 answer.
- **Pass 2 gaps:** PA content not verifiable (SPA)
