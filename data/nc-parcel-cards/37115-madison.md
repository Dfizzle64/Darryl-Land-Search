# Madison County, NC — GIS County Card

## Summary

Madison County (Asheville MSA, FIPS **37115**, slug **madison**, `cntyfips='115'`) publishes an ArcGIS Online stack under org **NwIC4HArqo0JlKGT** (`gis_madcotax`) with Experience Builder jurisdiction GIS. **Wire-first parcels (TRANCHE-3):** **2025_Parcels FeatureServer/19** — ~**21,753** polys with `PIN`/`REID`, `OWNER`, mailing (`ADDRESS`/`CITY`/`STATE`/`ZIP`), parcel `ZONING` attr, `TACRES`/`CACRES`, deed `DB`/`DP`. ~**7,134** with `CACRES` 5–150 (~**7,426** `TACRES`). **Tax values:** join **NC OneMap** `parval`/`landval`/`improvval` (`cntyfips='115'`, ~**21,381**; `parval>0` → **19,810**). **Sale price/date REST gap** on county + OneMap (`saledate` null); NCPTS Property Card carries Package/Land Sale + appraised values. **Zoning is cities-first:** **Mars Hill** `Mars_Hill_Zoning` (**39**), **Marshall** `Marshall_Zoning2023v2` CLASSIFICA (**82**), then county `CtyZoningWO_MH_Marsh` (~**20,167**, excludes MH/Marshall). **Hot Springs** zoning REST gap (town Planning & Zoning page). **FLU:** Comp Plan + Map 3 Zoning/Land Use **PDF** only — no FLU FeatureServer. **PA deep-link:** NCPTS `PropertySummary.aspx?PARCELPK={PARCEL_PK}` (also `?PIN={PIN_DASHED}` / `?REID={REID}`); PIN format `####-##-####` from 10-digit `PIN`. **Jurisdiction GIS:** https://experience.arcgis.com/experience/2333843dc4584e648a98fb9542dc75fe. Markets: **[Asheville]**.

## Portals

- **Jurisdiction GIS (Experience Builder)** — https://experience.arcgis.com/experience/2333843dc4584e648a98fb9542dc75fe
- **Open Data Hub** — https://madison-county-nc-open-data-madcotax.hub.arcgis.com/
- **County AGOL org REST** — https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services
- **Tax Services** — https://www.madisoncountync.gov/tax-services.html
- **Tax Administration** — https://www.madisoncountync.gov/tax-administration.html
- **Planning and Zoning** — https://www.madisoncountync.gov/planning-and-zoning.html
- **Land Use Ordinance (PDF)** — https://www.madisoncountync.gov/uploads/5/9/7/0/59701963/mc_land_use_ordinance_revised_6.29.21__1_.pdf
- **Comp Plan 2022 (PDF)** — https://www.madisoncountync.gov/uploads/5/9/7/0/59701963/comprehensive_plan_2022.pdf
- **Map 3 Current Zoning & Land Use (PDF)** — https://www.madisoncountync.gov/uploads/5/9/7/0/59701963/map_3_-_current_zoning___land_use.pdf
- **NCPTS Property Cards (search)** — http://lrcpwa.ncptscloud.com/Madison
- **NCPTS PA deep-link (preferred)** — `https://lrcpwa.ncptscloud.com/Madison/PropertySummary.aspx?PARCELPK={PARCEL_PK}`
- **NCPTS by PIN (dashed)** — `https://lrcpwa.ncptscloud.com/Madison/PropertySummary.aspx?PIN={PIN_DASHED}`
- **Mars Hill Planning & Zoning** — https://townofmarshill.org/_services/planning_zoning/index.php
- **Mars Hill Zoning Map page** — https://townofmarshill.org/_services/planning_zoning/zoning_map.php
- **Mars Hill Zoning Ordinance (PDF)** — https://townofmarshill.org/Documents/Services/ZONING%20ORDINANCE%20-%20Town%20of%20Mars%20Hill%20-%202021.pdf
- **Hot Springs Planning & Zoning** — https://townofhotsprings.org/zoning/
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='115'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`; OneMap `parno`; `REID` | 10-digit no dashes ↔ NCPTS `####-##-####` |
| polygons | Yes | 2025_Parcels/19; OneMap/1 | CRS **6543** (county AGOL); OneMap statewide |
| acreage | Yes | `CACRES`/`TACRES`; OneMap `gisacres` | 2025 ~**7,134** CACRES 5–150 |
| ownerName | Yes | `OWNER`; OneMap `ownname` | ~**20,081** OWNER not null |
| mailing address | Yes | `ADDRESS`+`CITY`+`STATE`+`ZIP`; OneMap `mailadd`/`mcity`/`mstate`/`mzip` | ADDRESS is mailing |
| situs address | Partial | OneMap `siteadd`; Addresses/32 `FullAddress` | Spatial or OneMap join; parcel ADDRESS ≠ situs |
| lastSale date/price | Partial / PA | NCPTS Package/Land Sale; deed `DB`/`DP` | **Sale price/date REST gap** county+OneMap |
| tax values | Yes (join) | OneMap `parval`/`landval`/`improvval`; NCPTS appraised | County parcel REST has no value fields |
| zoning | Yes (cities-first + county) | MH `ZoningCode`; Marshall `CLASSIFICA`; county `Zoning` / parcel `ZONING` | Hot Springs REST gap |
| flu | PDF only | Comp Plan 2022 + Map 3 | No FLU FeatureServer |
| appraiser / viewer link | Yes | NCPTS `{PARCEL_PK}` / `{PIN_DASHED}` / `{REID}` | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. 2025_Parcels — parcels + ownership + zoning attr (PRIMARY)

- **Purpose:** parcels | ownership | zoning-attr | acres | deed ref
- **REST URL:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/2025_Parcels/FeatureServer/19
- **Layer name / id:** 2025 Parcels / 19
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (10-digit; e.g. `9834383846` ↔ dashed `9834-38-3846`)
  - `REID` → parcelIdAlt / NCPTS REID
  - `CACRES`, `TACRES` → acreage
  - `OWNER` → ownerName
  - `ADDRESS`, `CITY`, `STATE`, `ZIP` → mailing
  - `ZONING` → zoning (county/muni text; normalize)
  - `DB`, `DP` → deed book/page (not sale price)
  - `TSHIP`, `FD` → township / fire district
- **WKID / CRS:** 6543 (NAD 1983 (2011) StatePlane NC Feet)
- **Verified:** yes — count **21,753**; `CACRES BETWEEN 5 AND 150` → **7,134**; `TACRES` 5–150 → **7,426**; `OWNER IS NOT NULL` → **20,081**; sample `PIN=9834383846` SHELTON centroid ≈ **-82.61, 36.03** (Madison); join OneMap `parno` OK
- **Notes:** PRIMARY wire-first (newest annual publish). MaxRecordCount **2000** — paginate. Auth **none**. No sale price / assessed-value fields on this layer — join OneMap for tax; NCPTS for sale.

### 2. ParcelCAMAInfo / 2025 Tax Parcel Update — CAMA mirror

- **REST URL:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/ParcelCAMAInfo/FeatureServer/9
- **Also:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/2025_Madison_County_Tax_Parcel_Update/FeatureServer/9
- **Same schema** as 2025_Parcels (REID/PIN/OWNER/ADDRESS/ZONING/CACRES/…)
- **Verified:** count **21,549**
- **Notes:** Slightly behind 2025_Parcels count; use as alternate extract.

### 3. 2023_Madison_County_Tax_Parcels — prior-year mirror

- **REST URL:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/2023_Madison_County_Tax_Parcels/FeatureServer/0
- **Verified:** count **21,535** — same field family; prefer 2025_Parcels.

### 4. 2025_Tax_Layer Tax — cadastral/zoning geometry

- **REST URL:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/2025_Tax_Layer/FeatureServer/43
- **Fields:** `PIN`, `CACRES`/`TOTALACRES`, `Zoning`, plat attrs (no OWNER/values)
- **Verified:** count **21,756**
- **Notes:** Geometry + zoning maintenance layer; not primary CAMA.

### 5. NC OneMap Parcels (polys) — tax values + statewide fallback

- **Purpose:** parcels | tax | ownership | acres (sale date empty for Madison)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='115'`
- **Key fields:** `parno`↔`PIN`, `ownname`, `mailadd`/`mcity`/`mstate`/`mzip`, `siteadd`, `gisacres`, `parval`/`landval`/`improvval`, `saledate`/`saledatetx` (empty), `sourceref` (deed book/page text)
- **Verified:** count **21,381**; `gisacres` 5–150 → **7,157**; `parval>0` → **19,810**; `landval>0` → **19,793**; `improvval>0` → **12,115**; `saledate IS NOT NULL` → **0**; join `parno='9834383846'`
- **Notes:** **PRIMARY for tax values**. No sale price. Prefer county `CACRES` for acres when present. MaxRecordCount **5000**.

### 6. Mars_Hill_Zoning — cities-first (Mars Hill)

- **REST URL:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/Mars_Hill_Zoning/FeatureServer/0
- **Fields:** `ZoningCode`
- **Verified:** count **39**
- **Codes:** R1 (3), R2 (6), R2A (7), R3 (6), R4 (1), C1 (2), C2 (8), Industrial (4), Institutional (1), T (1)
- **ETJ:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/MarsHillETJ/FeatureServer/0 (count **1**)
- **Notes:** Cities-first PRIMARY inside Mars Hill. Ordinance PDF on town site. Spatial join → parcels; route by Town_Limits `NAME='Mars Hill'`.

### 7. Marshall_Zoning2023v2 — cities-first (Marshall)

- **REST URL:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/Marshall_Zoning2023v2/FeatureServer/0
- **Zoning field:** `CLASSIFICA` (parcel CAMA columns present but **blank/zero** on this publish — treat as zoning polygons only)
- **Verified:** count **82**
- **CLASSIFICA:** R2 (26), HB (13), MU (13), CB (10), OSR (7), R1 (7), I (4), R3 (2)
- **Notes:** County seat. Cities-first PRIMARY inside Marshall. Route by Town_Limits `NAME='Marshall'`.

### 8. CtyZoningWO_MH_Marsh — county zoning (outside MH/Marshall)

- **REST URL:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/CtyZoningWO_MH_Marsh/FeatureServer/0
- **Fields:** `Zoning`, `PIN`, `CACRES`/`TOTALACRES`
- **Verified:** count **20,167**
- **Codes:** R-A (**17,856**), R-2 (**1,731**), blank (354), R-B (181), MHP (27), I-D (14), C (3), LNDF (1)
- **Notes:** County-wide zoning minus Mars Hill/Marshall footprints (layer name). Prefer municipal layers inside those towns. Parcel `ZONING` text attr on 2025_Parcels is a useful county-wide hint (RA/R-2/Residential-Agriculture District/…).

### 9. Town_Limits / TownLimits81021 — municipal routing

- **Town_Limits:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/Town_Limits/FeatureServer/0 — **3** (Mars Hill, Hot Springs, Marshall)
- **TownLimits81021:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/TownLimits81021/FeatureServer/0 — **7** (includes stub polys)
- **Notes:** Use for cities-first spatial routing.

### 10. 2025_Addresses SiteStructureAddressPoints — situs supplement

- **REST URL:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/2025_Addresses/FeatureServer/32
- **Fields:** `FullAddress`, `Inc_Muni`, `Post_Code`, … (no PIN — spatial join)
- **Verified:** count **18,612**
- **Notes:** Prefer OneMap `siteadd` when joining by `parno`; Addresses for map labels / spatial situs.

### 11. FLU — PDF only (no public FeatureServer)

- **Comp Plan 2022:** https://www.madisoncountync.gov/uploads/5/9/7/0/59701963/comprehensive_plan_2022.pdf
- **Legacy Comp Plan:** https://www.madisoncountync.gov/uploads/5/9/7/0/59701963/madison_county_comprehensive_plan.pdf
- **Map 3 Current Zoning & Land Use:** https://www.madisoncountync.gov/uploads/5/9/7/0/59701963/map_3_-_current_zoning___land_use.pdf
- **Notes:** Parcel `ZONING` / Land Use Ordinance districts are **zoning**, not future land use. No FLU FeatureServer verified.

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS REST? | FLU REST? | Notes |
|--------------|---------------|------:|:-------------:|:---------:|-------|
| **Marshall** | Marshall_Zoning2023v2 `CLASSIFICA` | 82 | County-hosted AGOL | No | County seat; R1/R2/R3/HB/MU/CB/OSR/I |
| **Mars Hill** | Mars_Hill_Zoning `ZoningCode` | 39 | County-hosted + ETJ | No | Ordinance + zoning_map.php |
| **Hot Springs** | *(none)* | — | Town page only | No | **Zoning REST gap**; Planning & Zoning page |
| Unincorporated | CtyZoningWO_MH_Marsh + parcel `ZONING` | ~20k | County | No | County-wide zoning since 1970s |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| NCPTS Property Summary (preferred) | `https://lrcpwa.ncptscloud.com/Madison/PropertySummary.aspx?PARCELPK={PARCEL_PK}` |
| NCPTS by PIN | `https://lrcpwa.ncptscloud.com/Madison/PropertySummary.aspx?PIN={PIN_DASHED}` |
| NCPTS by REID | `https://lrcpwa.ncptscloud.com/Madison/PropertySummary.aspx?REID={REID}` |
| PIN encoding | 10-digit `PIN` → `####-##-####` (`9834383846` → `9834-38-3846`) |
| NCPTS search | http://lrcpwa.ncptscloud.com/Madison |
| Jurisdiction GIS | https://experience.arcgis.com/experience/2333843dc4584e648a98fb9542dc75fe |
| Experience select (OBJECTID) | `…/2333843dc4584e648a98fb9542dc75fe#data_s=id:dataSource_5-1993dec94ed-layer-29:{OBJECTID}` |

Indexed NCPTS card for `PARCELPK=23301` (PIN `8754-96-2857`, REID `663139`): Package Sale 11/06/2024 @ **$1,200,000**, land/bldg appraised — confirms tax/sale on PA when REST lacks sale.

## Gaps / caveats

- **Sale price/date REST gap** — county AGOL parcels and OneMap Madison have no usable `saledate`/`Sale_Price`; use NCPTS PA for sale
- **Tax values not on county parcel REST** — join OneMap `parval`/`landval`/`improvval` by `PIN`=`parno`
- **Hot Springs zoning REST gap** — town maintains Planning & Zoning page; no public FeatureServer
- **Marshall_Zoning2023v2** CAMA value/sale columns are empty stubs — use only `CLASSIFICA` for zoning
- **Situs** — parcel `ADDRESS` is mailing; use OneMap `siteadd` or Addresses spatial join
- **FLU REST gap** — Comp Plan / Map 3 PDF only
- Hub historical parcel layers (2018–2021) are stale — prefer 2025_Parcels
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Madison County Tax / GIS / Planning (`gis_madcotax`). Maps compiled from recorded deeds/plats/public records; consult primary sources; not survey quality. Commercial resale subject to **NCGS 132-10**. Attribute Madison County GIS (and Town of Mars Hill / Marshall / Hot Springs where municipal sources used). NC OneMap / NC Geographic Information Coordinating Council for statewide parcels.

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 12+
- **tranche:** 3 (tax via OneMap+NCPTS; sale via NCPTS PA; owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- Live `returnCountOnly` + sample attribute/geo queries against 2025_Parcels, ParcelCAMAInfo, 2023 Tax Parcels, 2025_Tax_Layer, Mars_Hill_Zoning, Marshall_Zoning2023v2, CtyZoningWO_MH_Marsh, Town_Limits, 2025_Addresses, NC OneMap `cntyfips='115'`; Experience Builder data-source inventory; NCPTS indexed PropertySummary cross-check; centroid geo-check in Madison.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/2025_Parcels/FeatureServer/19 · id `PIN` · live count **21,753** · 5–150 ac **7,134** (`CACRES >= 5 AND CACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='MADISON'` gives **205** stations (136 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27MADISON%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Madison'` gives **198** stations (75 with AADT_2025, 118 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Madison%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (gap):** none on the parcel layer. Fallback: {"source": "NC OneMap parcels (join altparno/parno to PIN)", "restUrl": "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1", "where": "cntyfips='115' AND parval>0", "liveCount": 19810, "fields": ["parval", "landval", "improvval"], "pa": "NCPTS Madison PropertySummary (appraised values)"}
- **Sale history (gap):** price not on REST; date not on REST. No sale price/date on county REST or NC OneMap (saledate null). NCPTS Madison PropertySummary carries Package/Land Sale.
- **Owner entity:** fields `OWNER`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **986** (all parcels: 3,414), using the SQL approximation on `OWNER`.
- **PA deep link:** `https://lrcpwa.ncptscloud.com/Madison/PropertySummary.aspx?PIN={PIN}`. Tested `9834-28-4018` → HTTP **200** (text/html), content verified: False. NCPTS SPA shell (200, 496 B, client-rendered): parcel content cannot be checked server-side. Card-preferred form ?PARCELPK={PARCEL_PK} needs a key that is not on the REST layer; ?PIN={PIN dashed ####-##-####} was tested.
- **Jurisdiction GIS viewer:** https://experience.arcgis.com/experience/2333843dc4584e648a98fb9542dc75fe → HTTP **200** (Experience); ArcGIS item access=public
- **Pass 2 gaps:** tax gap, sale gap
