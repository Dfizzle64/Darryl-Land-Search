# Gaston County, NC — GIS County Card

## Summary

Gaston County (Charlotte MSA, FIPS **37071**) publishes a strong **public** ArcGIS REST stack at `gis.gastoncountync.gov/publicgis`: countywide **parcel polygons + DevNet CAMA** (owner, mailing/situs, acreage, fair-market/tax values, last-sale date/amount) on `PublicGIS/Parcels` layer **11**, plus a multi-municipality **Zoning** MapServer that hosts **city-first zoning polygons** for Belmont, Bessemer City, Cherryville, Cramerton, Dallas, Gastonia, Kings Mountain, Lowell, McAdenville, Mount Holly, Ranlo, Stanley, and unincorporated **Gaston County UDO** (with overlays). City of **Gastonia** also exposes its own `cogserver.gastonianc.gov` Zoning_UDO and a county-parcel mirror (CRS **6543**, not 2264). City of **Mount Holly** publishes an independent AGOL `Zoning_Auth` FeatureServer. **NC OneMap** (`cntyfips='071'`) is a solid statewide fallback. Main gaps: **no public FLU FeatureServer** (Envision Gaston 2050 / city comps are PDF), and **High Shoals / Spencer Mountain / Dellview** have municipal polygons but **no** zoning layer on the county Zoning service.

## Portals

- **Gaston County GIS home** — https://gis.gastoncountync.gov/
- **Interactive map** — https://gis.gastoncountync.gov/Map/Index — Deep link: `https://gis.gastoncountync.gov/Map/Default.aspx?AKPAR={AKPAR}` or `https://gis.gastoncountync.gov/Map/Index/{AKPAR}`
- **Data / search app** — https://gis.gastoncountync.gov/Search/Index
- **PublicGIS REST** — https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS
- **wEdge Property Tax Inquiry** — https://gastonnc.devnetwedge.com/ — Deep link: `https://gastonnc.devnetwedge.com/parcel/view/{AKPAR}`
- **Tax Mapping / GIS (county page)** — https://www.gastongov.com/677/Tax-Mapping-GIS
- **City of Gastonia GIS REST** — https://cogserver.gastonianc.gov/serverweb/rest/services
- **City of Mount Holly GIS Hub** — https://city-of-mount-holly-gis-mapping-comh.hub.arcgis.com/
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels FeatureServer (`services.nconemap.gov` / `services.gis.nc.gov`)
- **Envision Gaston 2050 (FLU policy PDF, not REST)** — https://engagegaston.com/envision-gaston

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `AKPAR` (account), `PIN` (NC PIN), `PID` | Prefer `AKPAR` for map/wEdge links; `PIN` for statewide joins |
| polygons | Yes | PublicGIS Parcels /11 | County CRS **WKID 102719 / 2264** |
| acreage | Yes | `CALCAC` (GIS), `DEEDAC` | ~**6,818** parcels in 5–150 ac |
| ownerName | Yes | `CURR_NAME1`+`CURR_NAME2` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `CURR_ADDR1`,`CURR_ADDR2`,`CURR_CITY`,`CURR_STATE`,`CURR_ZIPCODE` | ZIP often 9-digit string |
| situs address | Yes | `WHOLE_ADDRESS`,`POSTAL`,`STATE`,`ZIP` / `PHYSSTRADD` | Some null / "NO ASSIGNED ADDRESS" |
| lastSale date/price | Yes (partial) | `SALEDATE`,`SALESAMT`; deed qual `DEEDQUAL_CODEDESC` | ~2.5k of 5–150 ac have `SALESAMT>0`; OneMap has date only |
| tax values | Yes | `FMV_LAND`,`FMV_IMPRV`,`FMV_TOTAL`,`TOTVAL` | FMV = fair market; TOTVAL = taxable/total (0 on many exempt) |
| zoning | Yes (split by city) | County Zoning MapServer per-muni layers; Gastonia `ZONING`; MH `Zone_Abbv` | **Spatial join** — not on parcel CAMA. See Municipalities |
| FLU | **No (gap)** | n/a on public REST | Envision Gaston 2050 / Belmont Comp Plan = PDF only |
| appraiser / viewer link | Yes | wEdge + county map by `AKPAR` | Templates below |

## Layers (verified)

### 1. PublicGIS/Parcels — parcels + ownership + tax + last sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales (last)
- **REST URL:** https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Parcels/MapServer/11
- **FeatureServer (same layer):** https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Parcels/FeatureServer/11
- **Layer name / id:** Parcels / 11
- **Geometry:** Polygon
- **Key fields → targets:**
  - `AKPAR` → parcelId (tax account; map/wEdge key)
  - `PIN` → id (NC PIN, e.g. `3546-64-0119`)
  - `PID` → alternate parcel id (often = AKPAR)
  - `CALCAC`, `DEEDAC` → acreage
  - `CURR_NAME1`, `CURR_NAME2` → ownerName
  - `CURR_ADDR1`, `CURR_ADDR2`, `CURR_CITY`, `CURR_STATE`, `CURR_ZIPCODE` → mailing
  - `WHOLE_ADDRESS`, `POSTAL`, `STATE`, `ZIP` → situs
  - `SALEDATE`, `SALESAMT` → lastSale
  - `FMV_LAND`, `FMV_IMPRV`, `FMV_TOTAL`, `TOTVAL` → tax values
  - `property_use`, `VacantImpro` (`Vacant`|`Improved`), `DEED_BOOK`/`DEED_PAGE`, `DEEDQUAL_CODEDESC` → other
- **WKID / CRS:** 102719 (latest 2264) — NAD 1983 StatePlane NC Feet
- **Verified:** yes — `returnCountOnly` → **118,045**; `CALCAC BETWEEN 5 AND 150` → **6,818**; `SALESAMT>0` in range → **2,457**; sample attrs returned
- **Notes:** Best single county layer for land search. **No zoning field** — spatial-join municipal zoning. MaxRecordCount **10000**. License: attribution to Gaston County; NCGS 132-10 commercial resale limits apply. Prefer FeatureServer for GeoJSON extract.

### 2. City of Gastonia — GastonCountyParcels mirror (alternate host / CRS)

- **Purpose:** parcels | tax | ownership | sales
- **REST URL:** https://cogserver.gastonianc.gov/serverweb/rest/services/Parcels/GastonCountyParcels/MapServer/0
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:** Same CAMA family (`AKPAR`,`PIN`,`CALCAC`,`CURR_NAME*`,`SALESAMT`,`FMV_*`,`TOTVAL`,…)
- **WKID / CRS:** **103122 / 6543** (NAD 1983 **2011** StatePlane NC Feet) — **not** county 2264
- **Verified:** yes — count **115,066**
- **Notes:** City-hosted county parcel mirror; slightly fewer features than PublicGIS. **Reproject** before overlaying with county Zoning (2264). Prefer PublicGIS/Parcels/11 as canonical.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date only)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate host:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Layer name / id:** Parcels (polys) / 1 *(layer 0 = points)*
- **Geometry:** Polygon
- **Key fields → targets:**
  - `parno` → parcelId (aligns with county `PIN` style in samples)
  - `ownname` → ownerName
  - `mailadd`,`mcity`,`mstate`,`mzip` → mailing
  - `siteadd`,`scity` → situs
  - `gisacres` → acreage (~**6,819** in 5–150)
  - `saledate`,`saledatetx` → lastSale.date (**no sale price**)
  - `parval`,`landval`,`improvval` → tax
  - `cntyfips`=`071`, `cntyname` → Gaston filter
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — filter count **117,252**; sample features OK
- **Notes:** Excellent fallback. May lag county CAMA. Join `parno`↔`PIN` carefully vs `AKPAR`.

### 4. PublicGIS/Zoning — municipal + county zoning (city-first)

- **Purpose:** zoning (by municipality)
- **REST URL:** https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Zoning/MapServer
- **Geometry:** Polygon (all listed layers)
- **WKID / CRS:** 102719 / 2264
- **MaxRecordCount:** 2000
- **Join to parcels:** **spatial join** (intersect/centroid) — no shared parcel id on zoning layers. Use county parcels CRS 2264. Optionally pre-filter parcels by tax district / situs city, then overlay the matching muni layer.
- **Verified layers (count + zoning field):**

| Id | Layer | Count | Zoning field(s) | Jurisdiction |
|----|-------|------:|-----------------|--------------|
| 1 | Gaston County UDO | 2057 | `TYPE` (code), `NAME` | Unincorporated / county UDO |
| 0 | Gaston County UDO Overlays | 38 | `TYPE`,`NAME` | County overlays |
| 2 | Gastonia Zoning | 801 | `ZONING` / `ZONE_`,`MODIFIER` | City of Gastonia |
| 11 | Belmont Zoning | 677 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | Belmont |
| 3 | Belmont Overlays | 3 | `TYPE`,`NAME` | Belmont |
| 7 | Bessemer City Land Development Code | 346 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | Bessemer City |
| 4 | Bessemer City Overlays | 10 | `TYPE`,`NAME` | Bessemer City |
| 13 | Cherryville Zoning | 519 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | Cherryville |
| 14 | Cramerton Zoning | 225 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | Cramerton |
| 18 | Cramerton Overlays | 3 | `TYPE`,`NAME` | Cramerton |
| 15 | Dallas Zoning | 257 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | Dallas |
| 19 | Kings Mountain Zoning | 88 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | Kings Mountain (Gaston portion) |
| 9 | Lowell Land Use Code | 249 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | Lowell |
| 10 | McAdenville UDO | 64 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | McAdenville |
| 16 | Mount Holly Zoning | 461 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | Mount Holly |
| 5 | Mount Holly Overlays | 2 | `NAME` | Mount Holly |
| 20 | Ranlo Zoning | 210 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | Ranlo |
| 17 | Stanley Zoning | 244 | `TYPE`,`NAME`,`JURISDICTION`,`ETJ` | Stanley |

- **Notes:** This is the **primary city zoning catalog** for Gaston — most towns do **not** run a separate public FeatureServer; they publish through the county Zoning MapServer. Belmont sample codes: `G-R`, `R-C`, `R-R`. Gastonia sample: `C-1`, `AP`, etc.

### 5. City of Gastonia Zoning_UDO (city-native)

- **Purpose:** zoning (Gastonia-only)
- **REST URL:** https://cogserver.gastonianc.gov/serverweb/rest/services/Planning/Zoning_UDO/MapServer/0
- **Layer name / id:** Zoning Code and Definition / 0
- **Geometry:** Polygon
- **Key fields → targets:** `ZONING` / `ZONE_` → zoning; `MODIFIER`; `ACRES`; `APPR_DATE`
- **WKID / CRS:** **103122 / 6543**
- **Verified:** yes — count **801** (matches county Gastonia Zoning layer)
- **Notes:** Prefer for Gastonia-only apps on city CRS; for countywide joins prefer county Zoning/2 in **2264** to match PublicGIS parcels.

### 6. City of Mount Holly Zoning_Auth (city-native AGOL)

- **Purpose:** zoning (Mount Holly-only)
- **REST URL:** https://services7.arcgis.com/R3hvotzf6HmfdzVd/arcgis/rest/services/Zoning_Auth/FeatureServer/0
- **Layer name / id:** Zoning / 0
- **Geometry:** Polygon
- **Key fields → targets:** `Zone_Abbv` → zoning; `Zone_Name` → label; dimensional attrs (`Min_Lot_Area`, etc.)
- **WKID / CRS:** 102719 / 2264
- **Verified:** yes — count **387**
- **Notes:** Richer attribute dictionary than county MH layer 16 (461 polys). Cross-check both; county layer may include ETJ. Hub: https://city-of-mount-holly-gis-mapping-comh.hub.arcgis.com/

### 7. PublicGIS/Municipalities — city limit polygons (join aid)

- **Purpose:** other (jurisdiction boundaries)
- **REST URL:** https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Municipalities/MapServer/18
- **Geometry:** Polygon
- **Fields:** `NAME`, `AREANAME`, `ACRES`, `SQMILES`
- **Verified:** yes — distinct `NAME`: BELMONT, BESSEMER CITY, CHERRYVILLE, CRAMERTON, DALLAS, DELLVIEW, GASTONIA, HIGH SHOALS, KINGS MTN, LOWELL, MCADENVILLE, MT HOLLY, RANLO, SPENCER MTN, STANLEY
- **Notes:** Use to pick which zoning layer to query. **DELLVIEW, HIGH SHOALS, SPENCER MTN** appear here but **lack** dedicated Zoning MapServer layers.

### 8. PublicGIS/DevelopmentArea — developments (not FLU)

- **Purpose:** other (approved/proposed developments)
- **REST URL:** https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/DevelopmentArea/FeatureServer/4
- **Geometry:** Polygon
- **Fields:** `NAME`,`STATUS`,`JURISDICTION`,`ACREAGE`,`TOTALSFUNITS`,`TOTALMFUNITS`,`DEV_TYPE`,…
- **Verified:** yes — count **219**
- **Notes:** Useful context for pipeline supply; **do not** treat as future land use policy map.

## Municipalities (first-class)

County parcels are **county-wide** (all cities + unincorporated). **Zoning is city/ETJ-specific** — always select the municipal zoning layer (or county UDO) that covers the parcel. Join pattern: **county parcel polygons (2264) ∩ zoning polygons (2264)**; key attributes stay on parcels (`AKPAR`/`PIN`).

| Municipality | Zoning REST (preferred) | Field → zoning | Own GIS? | FLU REST? | Notes |
|--------------|-------------------------|----------------|----------|-----------|-------|
| Unincorporated Gaston | …/Zoning/MapServer/**1** (+ overlays **0**) | `TYPE` | County PublicGIS | No | County UDO |
| Gastonia | County …/Zoning/**2** **or** cogserver Zoning_UDO/0 | `ZONING` | Yes — cogserver | No | City CRS 6543 on cogserver |
| Belmont | …/Zoning/**11** (+ **3**) | `TYPE` | Defers to county GIS | No (Comp Plan PDF) | cityofbelmont.org plans |
| Bessemer City | …/Zoning/**7** (+ **4**) | `TYPE` | Via county | No | LDC layer |
| Cherryville | …/Zoning/**13** | `TYPE` | Via county | No | |
| Cramerton | …/Zoning/**14** (+ **18**) | `TYPE` | Via county | No | |
| Dallas | …/Zoning/**15** | `TYPE` | Via county | No | |
| Kings Mountain | …/Zoning/**19** | `TYPE` | Via county (Gaston side) | No | City also in Cleveland Co. |
| Lowell | …/Zoning/**9** | `TYPE` | Via county | No | "Land Use Code" = zoning |
| McAdenville | …/Zoning/**10** | `TYPE` | Via county | No | |
| Mount Holly | County …/Zoning/**16** **or** AGOL Zoning_Auth/0 | `TYPE` / `Zone_Abbv` | Yes — AGOL hub | No | Prefer AGOL for attrs |
| Ranlo | …/Zoning/**20** | `TYPE` | Via county | No | |
| Stanley | …/Zoning/**17** | `TYPE` | Via county | No | |
| High Shoals | **gap** | n/a | No public zoning REST found | No | Boundary only |
| Spencer Mountain | **gap** | n/a | No public zoning REST found | No | Boundary only |
| Dellview | **gap** | n/a | No public zoning REST found | No | Boundary only |

**City-only zoning / county parcels join checklist**

1. Query parcels from PublicGIS/Parcels/11 (`AKPAR`, geometry, CAMA attrs), filter `CALCAC BETWEEN 5 AND 150`.
2. Determine jurisdiction (Municipalities/18 spatial join, or situs/`DIST_TWN`/`TAX_DISTRI` hints).
3. Spatial-join the matching Zoning layer in **WKID 2264**. If using Gastonia cogserver Zoning_UDO, **reproject 6543 → 2264** (or reproject parcels to 6543) before intersect.
4. Write `TYPE`/`ZONING`/`Zone_Abbv` → `zoning`. Keep overlays as separate attributes.
5. Do **not** expect zoning on the parcel FeatureServer itself.

## Gaps

- **No public FLU / comprehensive-plan FeatureServer** countywide — Envision Gaston 2050 and city plans (e.g. Belmont Comp Plan) are PDF/policy only; DevelopmentArea ≠ FLU.
- **High Shoals, Spencer Mountain, Dellview** — municipal boundaries present; **no** zoning polygons on PublicGIS/Zoning.
- **Sale price sparsity** — many deeds show `SALESAMT=0`; use `DEEDQUAL_CODEDESC` / filter `SALESAMT>0`; OneMap has **no** sale price.
- **No parcel-joined zoning attribute** — must spatial join (unlike Mecklenburg ParcelsZoningZipcode).
- **CRS split** — county PublicGIS **2264** vs Gastonia cogserver **6543**.
- **Kings Mountain** straddles Cleveland County — Gaston Zoning/19 is Gaston-side only.
- **Owner phones/emails** not on these APIs (correct — do not scrape).
- **MaxRecordCount** — parcels 10000; zoning 2000 — paginate zoning queries.
- **NCGS 132-10** — county license restricts commercial resale of GIS data; attribution required.
- **No paid vendor data** used (CoreLogic/Regrid/ATTOM avoided).

## Hand-off notes for Land Search Builder

1. **Wire first:** `https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Parcels/MapServer/11` (or FeatureServer/11) — polygons + owner/mail/situs/acreage/tax/sale. Filter `CALCAC BETWEEN 5 AND 150` (~6.8k).
2. **Zoning (required for cities):** spatial join from `PublicGIS/Zoning/MapServer/{id}` per municipality table above; Gastonia may use cogserver Zoning_UDO with CRS care; Mount Holly may use Zoning_Auth.
3. **FLU:** **gap** — no wireable public REST; track Envision Gaston 2050 PDF until a FeatureServer appears.
4. **Fallback parcels:** NC OneMap layer 1 with `cntyfips='071'`.
5. **Viewer templates:** `https://gastonnc.devnetwedge.com/parcel/view/{AKPAR}` and `https://gis.gastoncountync.gov/Map/Default.aspx?AKPAR={AKPAR}`
6. **Join keys:** `AKPAR` (appraiser/map), `PIN` (NC PIN / OneMap `parno`), geometry for zoning.
7. **Auth:** None observed on listed public query endpoints.

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='GASTON'`, field `AADT_2022` (string) — **905 stations live**, 873 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27GASTON%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27GASTON%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Gaston'`, `AADT_2025` (int) — 900 stations; 114 with 2025, 824 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Parcels/MapServer/11` — total 118056, 5–150 ac 6820 (`CALCAC>=5 AND CALCAC<=150`).
- Non-zero county: `FMV_LAND` 112727, `FMV_IMPRV` 95717, `FMV_TOTAL` 114236, `TOTVAL` 111020; in 5–150: `TOTVAL` 5915. **Status: ok.**
- Numeric Double fields; FMV_* = market, TOTVAL = taxable.

### 3. Sale history
- Price `SALESAMT`>0 69395 (5–150: 2461); date non-null `SALEDATE` 113342. **Status: ok.**
- SALEDATE esriDate (epoch ms); SALESAMT numeric; DEEDQUAL_CODEDESC = qualified flag. Last sale only.

### 4. Owner entity
- Owner fields: `CURR_NAME1`, `CURR_NAME2`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 1869** (of 6820 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: `https://gastonnc.devnetwedge.com/parcel/view/{AKPAR}`
- Tested `https://gastonnc.devnetwedge.com/parcel/view/100066` → **200**. HTTP 200 → redirects to /parcel/view/100066/2027; parcel id present in server HTML.

### 6. Jurisdiction GIS viewer
- `https://gis.gastoncountync.gov/Map/Index` → **200**. Gaston County public GIS map

### Pass2 gaps
- AADT_2022 blank at 32 of 905 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- No multi-transfer sale history on primary layer (last sale only)
