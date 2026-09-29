# Forsyth County, NC — GIS County Card

## Summary

Forsyth County (Winston-Salem MSA, FIPS **37067**) shares **MapForsyth** / Winston-Salem–Forsyth Planning GIS at `maps.co.forsyth.nc.us` (mirror `terraweb.co.forsyth.nc.us`). **Wire-first parcels:** AGOL **Parcels_Hosted** (same schema as county `CAD/CAD_Parcels`) — ~**167.5k** polygons with owner, mailing, **situs**, acreage, assessed total, last qualified sale price, **PRZONING** attribute, and NCPTS deep link by `PARCEL_PK`. ~**8,135** with `CALCULATEDACREAGE` 5–150 (~**3,795** with `RESCOMSQFT=0`). **Zoning** is municipality-coded on one countywide layer (`ZONING_JURISDICTION`: WS, FC, KE, CL, LE, WA, HP tip, KI edge, rare KV). **FLU:** county Proposed Residential Land Use (~16.8k; PIN-joinable) + Growth Mgmt Areas 2045; Kernersville has local Land Use Plan; High Point tip uses city Place Types. **NC OneMap** (`cntyfips='067'`) is a solid fallback with land/improve split. Prefer AGOL hosted URLs when county TLS is flaky. Main gaps: no land/building value split on primary parcels; sale price often 0 (use SalesApp); Clemmons/small towns FLU mostly via county Proposed LU (category caveats); High Point county zoning polygons sparse (8).

## Portals

- **MapForsyth Hub** — https://www.mapforsyth.org/ — City-County GIS hub / data download
- **Tax Parcel Viewer** — https://MapF.maps.arcgis.com/apps/webappviewer/index.html?id=53620a0b6458437aa82bd5e91d8cc47b
- **Property search (NCPTS)** — https://lrcpwa.ncptscloud.com/forsyth/parcel-search — Deep link: `https://lrcpwa.ncptscloud.com/forsyth/parcel-detail/{PARCEL_PK}`
- **Forsyth Tax Administration** — https://forsyth.cc/tax/
- **County ArcGIS REST** — https://maps.co.forsyth.nc.us/arcgis/rest/services (alt: `terraweb.co.forsyth.nc.us`)
- **MapForsyth AGOL org** — https://services1.arcgis.com/5Yf8nIJWE7cxpd3N/arcgis/rest/services
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)
- **Town of Kernersville GIS** — https://gis.toknc.com/server/rest/services — Zoning + Land_Use_Plan
- **City of High Point GIS** — https://gisentapp01.highpointnc.gov/server/rest/services — Zoning + Place Types (Forsyth tip)
- **Clemmons OpenGov map stack** — https://maps.co.forsyth.nc.us/arcgis/rest/services/ClemmonsVillage/Clemmons_OpenGov/MapServer (zoning mirrors county)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `TAXPIN`/`PIN`, `PARCEL_PK`, `REID`; OneMap `parno` | Prefer `TAXPIN`/`PIN` (####-##-####.##); `PARCEL_PK` for NCPTS deep link; `REID` also present |
| polygons | Yes | Parcels_Hosted FS/0 / CAD_Parcels FS/0 | CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALCULATEDACREAGE`, `ACREAGE` | ~**8,135** CALC 5–150; ~**8,146** ACREAGE 5–150 |
| ownerName | Yes | `CURRENTOWNERNAME1` (+ `CURRENTOWNERNAME2`); OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `CURRENTOWNERADDRESS` + `CURRENTOWNERCITYSTZIP` | Parse city/state/zip from combined line |
| situs address | Yes | `PROPERTYADDRESS` / OneMap `siteadd`,`scity` | **On primary parcel layer** |
| lastSale date/price | Partial | `CURRENTDEEDDATE`, `LASTQUALIFIEDSALEPRICE`; SalesApp `XFER_*` | Many LQSP=0; SalesApp has multi-transfer points with price + qual codes |
| tax values | Partial | `TOTALVALUE` (string); OneMap `parval`,`landval`,`improvval` | No land/improve split on primary; cast TOTALVALUE |
| zoning | Yes | Parcel `PRZONING`; polygon `ZONING_DISTRICT` + `ZONING_JURISDICTION` | Prefer spatial zoning for authority; PRZONING nearly complete (~89 null) |
| flu | Yes (partial) | `ProposedLU`/`CommonProposedLU`; KE `PROP_LU`; HP `PlaceTypes`; GMA 2045 | Clemmons/Kernersville categories differ per layer docs |
| appraiser / viewer link | Yes | NCPTS parcel-detail by PARCEL_PK; Tax Parcel Viewer | Templates below |

### ZONING_JURISDICTION / MUNICIPALITY codes

| Code | Jurisdiction | Zoning layer notes (verified counts) |
|------|----------------|--------------------------------------|
| WS | Winston-Salem | County Zoning **2,249** |
| FC | Forsyth County (unincorporated) | County Zoning **777**; covers Rural Hall / Tobaccoville / Bethania where not separately zoned |
| KE | Kernersville | County Zoning **530**; town host Zoning/14 **446** (prefer town for KE) |
| CL | Clemmons | County Zoning **237**; ClemmonsVillage MapServer/4 mirrors county schema |
| LE | Lewisville | County Zoning **138** |
| WA | Walkertown | County Zoning **121** |
| HP | High Point (Forsyth tip) | County Zoning only **8** — use High Point city Zoning for tip |
| KI | King (Stokes edge) | County Zoning **5** |
| KV | (rare code) | **1** polygon — treat as anomaly / verify |
| BE | Bethania | Corporate Limits only — zoning typically **FC** |
| RH | Rural Hall | Corporate Limits only — zoning typically **FC** |
| TO | Tobaccoville | Corporate Limits only — zoning typically **FC** |

## Layers (verified)

### 1. Parcels_Hosted / CAD_Parcels — parcels + ownership + tax + situs + sale + PRZONING (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last qualified) | situs | zoning (attr)
- **REST URL (wire-first):** https://services1.arcgis.com/5Yf8nIJWE7cxpd3N/arcgis/rest/services/Parcels_Hosted/FeatureServer/0
- **County host:** https://maps.co.forsyth.nc.us/arcgis/rest/services/CAD/CAD_Parcels/FeatureServer/0
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `TAXPIN` / `PIN` → parcelId (NC-style PIN ####-##-####.##)
  - `PARCEL_PK` → NCPTS deep-link key
  - `REID` / `REID_1` → alternate account id
  - `CALCULATEDACREAGE`, `ACREAGE` → acreage
  - `CURRENTOWNERNAME1`, `CURRENTOWNERNAME2` → ownerName
  - `CURRENTOWNERADDRESS`, `CURRENTOWNERCITYSTZIP` → mailing
  - `PROPERTYADDRESS` → situs
  - `CURRENTDEEDDATE`, `LASTQUALIFIEDSALEPRICE`, `CURRENTDEEDBKPG`, `CURRENTDEEDSTAMPS` → lastSale
  - `TOTALVALUE` → tax.assessedValue (string — cast to number)
  - `PRZONING` → zoning (attribute; may be multi e.g. `GI; RS9`)
  - `Detailed_Property_Info_Link` → appraiser URL
  - `RESCOMSQFT`, `RESCOMYRBLT` → improvement hints
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **167,520**; `CALCULATEDACREAGE` 5–150 → **8,135**; `ACREAGE` 5–150 → **8,146**; `RESCOMSQFT=0` in 5–150 → **3,795**; sample owner/mail/situs/tax/zoning OK
- **Notes:** **PRIMARY** wire-first (AGOL). MaxRecordCount **2000** (AGOL) / **50000** (CAD host). Prefer `CALCULATEDACREAGE` for GIS acres. Spatial zoning join still recommended for jurisdiction-aware districts.

### 2. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date) | situs
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parno` → parcelId (aligns with TAXPIN/PIN)
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs
  - `gisacres` → acreage (~**8,134** in 5–150)
  - `saledate`,`saledatetx` → lastSale.date (**no sale price**)
  - `parval`,`landval`,`improvval` → tax (**has land/improve split**)
  - `cntyfips`=`067`, `cntyname` → Forsyth filter
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — filter count **166,755**; gisacres 5–150 → **8,134**; improvval=0 in range → **3,896**
- **Notes:** Best source for land/improve values. May lag county CAMA. MaxRecordCount **5000**.

### 3. Planning_Inspection Zoning — municipal + county zoning (PRIMARY zoning stack)

- **Purpose:** zoning
- **REST URL (wire-first AGOL):** https://services1.arcgis.com/5Yf8nIJWE7cxpd3N/arcgis/rest/services/Zoning_Hosted/FeatureServer/0
- **County host:** https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Planning_Inspection/FeatureServer/1
- **Fields:** `ZONING_DISTRICT`, `ZONING_JURISDICTION`, `ACRES`
- **WKID / CRS:** 102719 / 2264
- **Join to parcels:** spatial join (intersect/centroid) in 2264; route by `ZONING_JURISDICTION` or Corporate Limits `MUNICIPALITY`
- **Verified:** yes — total **4,066**; by juris: WS **2249**, FC **777**, KE **530**, CL **237**, LE **138**, WA **121**, HP **8**, KI **5**, KV **1**
- **Notes:** Single layer covers all Forsyth munis with separate zoning authority. High Point tip → city host. Overlay with parcel `PRZONING` for QA.

### 4. Zoning Jurisdiction + Corporate Limits

- **Zoning Jurisdiction:** https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Planning_Inspection/FeatureServer/2 — field `ZONING_JURISDICTION`
- **Corporate Limits:** …/FeatureServer/0 — `MUNICIPALITY`, `JURISDICTION`, `COUNTY` (includes BE, RH, TO, UNINC, WS, KE, CL, LE, WA, HP, KI)
- **Verified:** yes — domains include Bethania, Rural Hall, Tobaccoville (corporate) even where zoning collapses to FC

### 5. Proposed Residential Land Use — FLU (PRIMARY county FLU)

- **Purpose:** flu
- **REST URL:** https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/LandUse_PotentialResidentialGrowth/FeatureServer/0
- **Fields:** `PIN`, `ProposedLU`, `CommonProposedLU`, `ExistLU`, `CommonExistingLU`, `AreaPlan`, `AdoptYear`, `Acres`, `GrowthManagementArea`, `Address`
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **16,754**
- **Notes:** Parcel-like features — **attribute join on PIN↔TAXPIN** preferred. Docs: Clemmons & Kernersville area plans use different categories — prefer town FLU for KE; treat CL carefully.

### 6. Growth Mgmt Areas 2045 — FLU-adjacent

- **Purpose:** other / FLU-adjacent
- **REST URL:** https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Planning_Inspection/FeatureServer/15
- **Fields:** `GROWTHMANAGEMENTAREA` (1=City/Town Center … 5=Rural Area), `ACRES`
- **Notes:** Legacy comprehensive-plan GMAs; not a substitute for ProposedLU place types.

### 7. SalesApp_Hosted — transfer / sale history

- **Purpose:** sales
- **REST URL:** https://services1.arcgis.com/5Yf8nIJWE7cxpd3N/arcgis/rest/services/SalesApp_Hosted/FeatureServer/0
- **County host:** https://maps.co.forsyth.nc.us/arcgis/rest/services/Tax/SalesApp/FeatureServer/0
- **Geometry:** Point
- **Fields:** `XFER_PIN`, `XFER_XFERDATE`, `XFER_SALEPRICE`, `XFER_QUALCODE`, `XFER_DQCODE`, `XFER_DQDESC`, `XFER_ADDRESS`, `XFER_CURVAL`, `TOTACREAGE`, `PRZONINGS`, …
- **Verified:** yes — count **79,991**
- **Notes:** Join on `XFER_PIN`↔`TAXPIN` for multi-sale history / qualified prices when `LASTQUALIFIEDSALEPRICE` is 0.

### 8. MapMetrics TaxPolygon — geometry + keys only

- **REST URL:** https://maps.co.forsyth.nc.us/arcgis/rest/services/MapMetrics/MapMetrics/FeatureServer/1
- **Fields:** `TAXPIN`, `REID`, `PARCEL_PK`, `CALCULATEDACREAGE` — **no owner/tax**
- **Status:** partial — prefer Parcels_Hosted

### 9. Tax/Beltway Tax Parcels Jan 2016 — STALE

- **REST URL:** https://maps.co.forsyth.nc.us/arcgis/rest/services/Tax/Beltway/FeatureServer/1
- **Notes:** Snapshot **2016-01-01** — do not use as primary. Owner fields present but outdated.

## Municipalities (first-class)

County parcels are countywide; **zoning authority is municipal** (or FC). Join pattern: start from Parcels_Hosted (2264) → use `PRZONING` quickly → spatial join Zoning_Hosted filtered by `ZONING_JURISDICTION` → FLU via PIN join to ProposedLU or town FLU.

### City of Winston-Salem (WS)

- **Zoning:** Zoning_Hosted / county FS/1 where `ZONING_JURISDICTION='WS'` — count **2,249**; field `ZONING_DISTRICT`
- **FLU:** Proposed Residential Land Use (county) — PIN join; plus GMA 2045
- **Join note:** City-County Planning shares MapForsyth — no separate city parcel REST needed. Viewer: Tax Parcel Viewer / NCPTS.

### Town of Kernersville (KE) — prefer most local

- **Zoning (town host):** https://gis.toknc.com/server/rest/services/CommunityDevelopment/Zoning/FeatureServer/14 — `ZONING`, `DOCKET`, `Acreage`; count **446**; CRS **2264**
- **Zoning (county host):** filter KE — count **530** (includes ETJ / smoother county sync)
- **FLU — Land Use Plan:** https://gis.toknc.com/server/rest/services/CommunityDevelopment/Land_Use_Plan/FeatureServer/2 — `PROP_LU` (e.g. SCHOOL, …); count **203**; CRS **2264**
- **Join note:** Prefer town Zoning + Land_Use_Plan for KE parcels; county ProposedLU notes different categories for Kernersville.

### Village of Clemmons (CL)

- **Zoning:** county Zoning filter CL (**237**) or ClemmonsVillage/Clemmons_OpenGov/MapServer/4 (same `ZONING_DISTRICT` / `ZONING_JURISDICTION` schema)
- **FLU:** county ProposedLU with AreaPlan caveat (Clemmons categories differ) — no separate Clemmons FLU FeatureServer verified
- **Join note:** Spatial zoning join; FLU via ProposedLU or plan PDFs if categories mismatch

### Town of Lewisville (LE)

- **Zoning:** county Zoning filter LE — **138**
- **FLU:** county ProposedLU / GMA
- **Local GIS:** no separate public REST verified beyond MapForsyth

### Town of Walkertown (WA)

- **Zoning:** county Zoning filter WA — **121**
- **FLU:** county ProposedLU / GMA

### Town of Rural Hall (RH) / Village of Tobaccoville (TO) / Town of Bethania (BE)

- **Corporate Limits:** yes (MUNICIPALITY codes RH, TO, BE)
- **Zoning:** typically under **FC** (Forsyth County) on Zoning layer — no separate RH/TO/BE `ZONING_JURISDICTION` codes
- **FLU:** county ProposedLU / GMA / area plans (e.g. Rural Hall Area Plan — check ProposedLU `AreaPlan`)

### City of High Point — Forsyth tip (HP)

- **Zoning (county):** only **8** polygons — incomplete for tip
- **Zoning (city host — prefer):** https://gisentapp01.highpointnc.gov/server/rest/services/Zoning/MapServer/0 — `ZONE` / `DIST`; count **781** (citywide Guilford+Forsyth)
- **FLU — Place Types:** https://gisentapp01.highpointnc.gov/server/rest/services/Planning/MapServer/29 — `PlaceTypes` / `PT_All`; count **68**; CRS check before overlay
- **Join note:** Clip/filter to Forsyth side (FIPS 37067 / county boundary) when using citywide HP layers

### Town of King (KI) — Stokes edge

- **Zoning:** county Zoning **5** — edge only; Stokes County GIS out of scope unless needed

### Forsyth County unincorporated (FC)

- **Zoning:** filter `ZONING_JURISDICTION='FC'` — **777**
- **FLU:** ProposedLU + GMA 2045

## Gaps

- **No land/building assessed split on primary parcels** — `TOTALVALUE` only (string); use OneMap `landval`/`improvval` or NCPTS HTML for detail.
- **LASTQUALIFIEDSALEPRICE often 0** — enrich from SalesApp_Hosted transfers; `CURRENTDEEDDATE` is deed date not always sale.
- **Clemmons / small-town FLU** — no dedicated public FLU REST for Clemmons, Lewisville, Walkertown, Rural Hall, Tobaccoville, Bethania beyond county ProposedLU (category caveats for Clemmons).
- **High Point tip zoning sparse on county layer (8)** — must use city Zoning MapServer.
- **Kernersville town GIS TLS** — some clients need insecure/alternate; county Zoning KE filter is reliable fallback.
- **Tax/Beltway 2016 parcels are stale** — do not wire.
- **maps.co.forsyth.nc.us TLS** can fail from some environments — prefer AGOL Parcels_Hosted / Zoning_Hosted / SalesApp_Hosted.
- **Owner phones/emails** not collected (do not scrape NCPTS PII beyond public REST fields).
- **MaxRecordCount** 2000 on AGOL parcels/zoning — paginate; CAD host allows 50000.
- **No paid vendor data** used (CoreLogic/Regrid/ATTOM avoided).

## Hand-off notes for Land Search Builder

1. **Wire first:** `Parcels_Hosted/FeatureServer/0` — polygons + owner, mailing, **situs**, acreage, TOTALVALUE, PRZONING, LASTQUALIFIEDSALEPRICE, CURRENTDEEDDATE. Filter `CALCULATEDACREAGE BETWEEN 5 AND 150` (~8.1k). Optional vacant-ish: `RESCOMSQFT = 0` (~3.8k in range).
2. **Zoning:** use parcel `PRZONING` for fast attr; authoritative spatial join `Zoning_Hosted` (or county FS/1) by jurisdiction. For KE prefer `gis.toknc.com` Zoning/14; for HP tip prefer High Point Zoning/0.
3. **FLU:** attribute-join ProposedLU on `PIN`↔`TAXPIN`; KE use town Land_Use_Plan/`PROP_LU`; HP tip PlaceTypes; GMA 2045 as secondary.
4. **Sales:** SalesApp_Hosted on `XFER_PIN` when qualified price missing.
5. **Fallback:** NC OneMap layer 1 with `cntyfips='067'` (also supplies land/improve values).
6. **Viewer / appraiser links:**
   - NCPTS detail: `https://lrcpwa.ncptscloud.com/forsyth/parcel-detail/{PARCEL_PK}`
   - Search: `https://lrcpwa.ncptscloud.com/forsyth/parcel-search`
   - Tax Parcel Viewer: `https://MapF.maps.arcgis.com/apps/webappviewer/index.html?id=53620a0b6458437aa82bd5e91d8cc47b`
7. **Join keys:** `TAXPIN`/`PIN` (preferred), `PARCEL_PK`, `REID`, OneMap `parno`↔`TAXPIN`.
8. **Auth:** none observed on listed public query endpoints.
9. **Cities/towns are first-class:** never treat FC Zoning alone as countywide coverage.


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://services1.arcgis.com/5Yf8nIJWE7cxpd3N/arcgis/rest/services/Parcels_Hosted/FeatureServer/0 polygons load (sample centroid [-80.5069, 36.0736]); `TAXPIN` filled on 167,568 of 167,568; `CALCULATEDACREAGE` 5–150 ac **8,172**.
- **Attribute layer for Pass 2:** https://services1.arcgis.com/5Yf8nIJWE7cxpd3N/arcgis/rest/services/Parcels_Hosted/FeatureServer/0 · id `TAXPIN` · live count **167,568** · 5–150 ac **8,172** (`CALCULATEDACREAGE >= 5 AND CALCULATEDACREAGE <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='FORSYTH'` gives **1611** stations (233 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27FORSYTH%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Forsyth'` gives **1603** stations (1482 with AADT_2025, 305 with AADT_2024, 1513 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Forsyth%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `TOTALVALUE` non-zero **160,239** TOTALVALUE is a string and CAST(TOTALVALUE AS FLOAT/INT) returns 400 on this hosted layer; count used TOTALVALUE IS NOT NULL AND TOTALVALUE <> '' AND TOTALVALUE <> '0'.
- **Sale history (ok):** price `LASTQUALIFIEDSALEPRICE` >0 **90,597**; date `CURRENTDEEDDATE` non-null **167,473**. LASTQUALIFIEDSALEPRICE is the last qualified sale only; CURRENTDEEDDATE is the current deed date.
- **Owner entity:** field `CURRENTOWNERNAME1`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **2,540** (all parcels: 34,014), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://lrcpwa.ncptscloud.com/forsyth/parcel-detail/{PARCEL_PK}`. Tested `1251` (https://lrcpwa.ncptscloud.com/forsyth/parcel-detail/1251) → HTTP **200** (text/html), content verified: False. NCPTS SPA shell (200, 496 B, client-rendered): parcel content cannot be checked server-side. Same URL is stored per parcel in Detailed_Property_Info_Link.
- **Jurisdiction GIS viewer:** https://MapF.maps.arcgis.com/apps/webappviewer/index.html?id=53620a0b6458437aa82bd5e91d8cc47b → HTTP **200** (ArcGIS Web Application); ArcGIS item access=public
- **Municipal zoning/FLU layers re-checked:** 6 of 15 answer. Not answering: https://maps.co.forsyth.nc.us/arcgis/rest/services/ClemmonsVillage/Clemmons_OpenGov/MapServer/4; https://maps.co.forsyth.nc.us/arcgis/rest/services/MapMetrics/MapMetrics/FeatureServer/1; https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/LandUse_PotentialResidentialGrowth/FeatureServer/0; https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Planning_Inspection/FeatureServer/0; https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Planning_Inspection/FeatureServer/1; https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Planning_Inspection/FeatureServer/15; https://maps.co.forsyth.nc.us/arcgis/rest/services/Planning_Inspection/Planning_Inspection/FeatureServer/2; https://maps.co.forsyth.nc.us/arcgis/rest/services/Tax/Beltway/FeatureServer/1; https://maps.co.forsyth.nc.us/arcgis/rest/services/Tax/SalesApp/FeatureServer/0. Every maps.co.forsyth.nc.us layer fails from this box: https ends in TLS EOF and plain http 301-redirects to https (the terraweb mirror fails the same way). The AGOL mirrors (Zoning_Hosted, SalesApp_Hosted) and the Kernersville/High Point layers answer. Blocker is network/TLS from this computer, not proof the layers are gone.
- **Pass 2 gaps:** PA content not verifiable (SPA), county host maps.co.forsyth.nc.us unreachable from this box (TLS)
