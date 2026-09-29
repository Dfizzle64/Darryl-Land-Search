# Pasquotank County, NC — GIS County Card

## Summary

Pasquotank County (Outer Banks / Eastern NC, FIPS **37139**, slug **pasquotank**, `cntyfips='139'`) publishes public cadastral + CAMA on county AGOL org **`0sC2n3LxYOcxBOg0`** (`pasquotankcounty.maps.arcgis.com`). **Wire-first parcels (ArcGIS REST):** **PasquotankCountyNC_20260101** FeatureServer/0 — **~22,788** polygons (as-of **2026-01-01**) with owner, mailing, situs (`LOCATION`), tax acres, full value split (`CURLAND`/`CURBLDG`/`CURTOTAL`/`TOTASSD`), deed book/page/date, and PA keys **`PID`** + **`PPN_2`**. **~2,814** with `TAXACRES` 5–150 (~**3,145** `Shape_Area` 5–150 = GIS acres, matches OneMap). **Sale price** is not on the primary CAMA layer — join **sales2025** (`SALE_PRICE`/`SALE_DATE_`, **1,201**) or **Sales_2024** (`SalePric`/`Date`, **2,146**) on `PARCEL_ID`. **Cities-first zoning:** **Elizabeth City** `CityZoning` FeatureServer/0 (**329** polys, `ZONING`) preferred over twin `Elizabeth_City_Zoning` (**317**); unincorporated → **County_Zoning_2026** (**778**, codes A-1/C-1/R-15/…). **FLU:** 2023 Future Land Use Plan PDF + joint CAMA Advanced Core LUP / DEQ certified LUP — **no public FLU FeatureServer**. **PA deep-link:** `https://link.co.pasquotank.nc.us/taxcard/taxcard.cfm?PP2={PPN_2}` (verified; **do not** pass `PID` as `PP2`). **jurisdictionGisUrl:** Instant Basic viewer. Markets: **[Outer Banks, Eastern NC]**.

## Portals

- **Public GIS viewer (jurisdictionGisUrl)** — https://pasquotankcounty.maps.arcgis.com/apps/instant/basic/index.html?appid=38fc8f0292b04ba0a300f801f17ae902
- **Classic Viewer (alt)** — https://pasquotankcounty.maps.arcgis.com/apps/Viewer/index.html?appid=7155a34043534443aaaa3fed8f8a492e
- **Zoning Map webappviewer** — https://pasquotankcounty.maps.arcgis.com/apps/webappviewer/index.html?id=7c28d4e794d64a329c826a61575d0559
- **Planning & Inspections viewer** — https://pasquotankcounty.maps.arcgis.com/apps/webappviewer/index.html?id=8ef50e079f984cabbef43edf27a5d953
- **County AGOL REST root** — https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services
- **Parcel Information Search (TCS)** — https://www.pasquotankcountync.org/tcs (data as of 2026-01-01)
- **PA Tax Card deep-link** — `https://link.co.pasquotank.nc.us/taxcard/taxcard.cfm?PP2={PPN_2}`
- **PA search forms** — `https://link.co.pasquotank.nc.us/taxcard/DisplayTax.cfm?SEARCH=PIN` (also `SEARCH=PID|ADDRESS|MAP|Owner|DEED`)
- **NCPTS PWA** — https://lrcpwa.ncptscloud.com/pasquotank/
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/pasquotank/parcel-detail/{PIN}`
- **Tax Office** — https://www.pasquotankcountync.org/tax-office
- **GIS Office** — https://www.pasquotankcountync.org/gis-office
- **Planning** — https://www.pasquotankcountync.org/planning
- **Official plans & documents** — https://www.pasquotankcountync.org/official-plans-and-documents
- **County Zoning Ordinance PDF** — https://www.pasquotankcountync.org/s/Official-Zoning-Ordinance-adopted-June-21-2021-amended-Jan20th2026.pdf
- **2023 Future Land Use Plan PDF** — https://www.pasquotankcountync.org/s/Pasquotank_LUP_draftF7_FINAL_20230831.pdf
- **2004/2012 CAMA Advanced Core LUP PDF** — https://www.pasquotankcountync.org/s/Feb-82012-revised-LUP-ecac.pdf
- **DEQ certified LUP (Pasquotank/Elizabeth City)** — https://www.deq.nc.gov/about/divisions/coastal-management/coastal-management-land-use-planning/certified-lups/pasquotank-county
- **DEQ plan PDF download** — https://www.deq.nc.gov/documents/pdf/land-use-plans/pasquotankplan/download
- **Draft County UDO (WSC Konveio)** — https://wsc.konveio.com/pasquotank-county-udo
- **Elizabeth City Development Services** — https://elizabethcitync.gov/development-services
- **Elizabeth City UDO (zoning articles)** — https://elizabethcitync.gov/index.asp?SEC=FBC83C29-03EF-4FA1-9177-AE938C78FEF2&DE=2E73BB9B-E239-4C0C-8AC0-846E26B19469
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 — filter `cntyfips='139'`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PARCEL_ID`/`PIN`; `PID`; `PPN_2`; OneMap `parno`/`altparno` | Prefer **`PARCEL_ID`/`PIN`** for joins; **`PPN_2`** for taxcard `PP2=`; `PID` shown on card |
| polygons | Yes | PasquotankCountyNC_20260101 FS/0; OneMap | CRS **102100/3857**; MaxRecordCount **2000** |
| acreage | Yes | `TAXACRES`, `DEED_ACRE`, `Shape_Area` (GIS); OneMap `gisacres`/`recareano` | TAXACRES 5–150 → **2814**; Shape_Area/gisacres → **3145** |
| ownerName | Yes | `OWNER1`/`OWNER2`; OneMap `ownname` | Public on REST — no phones/emails |
| mailing address | Yes | `MAILING1`/`MAILING2`,`CITY`,`STATE`,`ZIP` | |
| situs address | Yes | `LOCATION`; OneMap `siteadd` | |
| lastSale date/price | Yes (join) | sales2025 `SALE_PRICE`/`SALE_DATE_`; Sales_2024 `SalePric`/`Date`; parcel `DEEDDATE` (YYYYMMDD, date-only) | **No sale price on primary CAMA** |
| tax values | Yes | `CURTOTAL`,`CURLAND`,`CURBLDG`,`TOTASSD`,`PRLAND`/`PRBLDG`/`PRTOTAL` | CURTOTAL>0 → **22661** |
| zoning | Yes (cities-first) | CityZoning `ZONING`; County_Zoning_2026 `ZONING` | Spatial-join; EC first |
| flu | Partial (PDF) | 2023 FLU Plan + CAMA/DEQ LUP | **No FLU FeatureServer** |
| appraiser / viewer link | Yes | taxcard `PP2={PPN_2}`; NCPTS `{PIN}`; Instant Basic GIS | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. PasquotankCountyNC_20260101 — PRIMARY CAMA parcels (ArcGIS REST)

- **Purpose:** parcels | ownership | tax | situs | deed date
- **REST URL:** https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/PasquotankCountyNC_20260101/FeatureServer/0
- **Geometry:** Polygon — CRS **102100 / 3857**
- **Key fields → targets:**
  - `PARCEL_ID` / `PIN` → parcelId (map/PIN key; space-padded 12-char form e.g. `7959  112410` or compact `891311763298`)
  - `PID` → parcelIdAlt (shown on tax card; **not** the `PP2` URL key)
  - `PPN_2` → appraiserDeepLinkKey (`PP2=` on taxcard.cfm)
  - `ACCOUNT` → accountNumber
  - `OWNER1`, `OWNER2` → ownerName
  - `MAILING1`, `MAILING2`, `CITY`, `STATE`, `ZIP` → mailing
  - `LOCATION` → situsAddress
  - `TAXACRES`, `DEED_ACRE`, `Shape_Area` → acreage (tax / deed / GIS)
  - `CURLAND`, `CURBLDG`, `CURTOTAL`, `TOTASSD` → tax (current); `PRLAND`/`PRBLDG`/`PRTOTAL` prior
  - `DEEDBOOK`, `DEEDPAGE`, `DEEDDATE` → deed (DEEDDATE YYYYMMDD; **16,626** >0 — date only, no price)
  - `CLASS` → use class (R≈20349 / C≈1323 / E≈966)
  - `MAP` / `MAPNUM` → map reference
  - `Photo` → local image path (not public URL)
- **Verified:** count **22,788**; TAXACRES 5–150 → **2,814**; Shape_Area 5–150 → **3,145**; CURTOTAL>0 → **22,661**; OWNER1 nonempty → **22,664**; PPN_2>0 → **22,665**
- **Geo-check:** PARCEL_ID `7959  112410` / PID `2859` / PPN_2 `65021` (Tadmore Rd) ≈ **-76.446, 36.447**; taxcard `PP2=64277` → PIN `7968  063483` / PID `2044` (1304 Newland Rd); `PP2=72145` → PIN `891311763298` / PID `11249` (406 Roanoke Ave)
- **Notes:** PRIMARY wire-first (matches TCS “Data as of January 1, 2026” + OneMap count). MaxRecordCount **2000**. Auth: **none**. Sale price via sales FS join (below). Prefer over Parcels_2024 / Parcels_Current / 20230101 twins.

### 2. Parcels_2024 — CAMA twin (slightly stale)

- **REST URL:** https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/Parcels_2024/FeatureServer/0
- **Verified:** count **22,575**; same CAMA field family (`OWNER1`…`CURTOTAL`, `PID`, `PPN_2`)
- **Notes:** Prefer 20260101. Useful historical snapshot only.

### 3. Parcels_Current — geometry-lean twin (no CAMA)

- **REST URL:** https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/Parcels_Current/FeatureServer/0
- **Fields:** `PARCEL_ID`, `MAPNUM`, `DEED_ACRE`, dims — **no owner/tax**
- **Verified:** count **22,530**
- **Notes:** Geometry-only fallback; do not use as primary.

### 4. NC OneMap Parcels — statewide ArcGIS REST fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='139'`
- **Key fields:** `parno`(=PIN), `altparno`, `ownname`, mail/site, `gisacres`, `parval`/`landval`/`improvval`, `saledate`/`saledatetx`
- **Verified:** count **22,788**; gisacres 5–150 → **3,145**; parval>0 → **22,661**; saledate **0**; saledatetx nonempty **0**; recareano 5–150 → **2,814**
- **Notes:** Aligns with county 20260101. Prefer county layer for deed date + `PPN_2`. OneMap sale fields empty for this county — use county sales FS.

### 5. sales2025 — sale price polygons (PRIMARY sale join)

- **REST URL:** https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/sales2025/FeatureServer/0
- **Fields:** `PARCEL_ID`, `MAPNUM`, `OWNER1`, `SALE_DATE_` (YYYYMMDD), `SALE_TYPE_`, `SALE_PRICE`, `Type`
- **Verified:** count **1,201**; SALE_PRICE>0 → **1,201**
- **Join:** `sales2025.PARCEL_ID` = `PasquotankCountyNC_20260101.PARCEL_ID` (verified e.g. `8829  096574`)
- **Notes:** Current-year sales layer. Also historical: Sales_2024 (**2146**), Sales_2022, Sales_in_2021, Sales_in_2019, sales_2023, Sales_2017, sales_2016, 2018_Sales, 2014_Sales.

### 6. Sales_2024 — prior-year sale polygons

- **REST URL:** https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/Sales_2024/FeatureServer/0
- **Fields:** `PARCEL_ID`, `SalePric`, `Date`, `Type`, `OWNER1` (some columns oddly aliased `F20250905`/`F100`)
- **Verified:** count **2,146**; SalePric>0 → **2,146**

### 7. CityZoning — Elizabeth City zoning (CITIES-FIRST PRIMARY)

- **REST URL:** https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/CityZoning/FeatureServer/0
- **Twin:** https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/Elizabeth_City_Zoning/FeatureServer/0 (**317**; older CUD naming)
- **Field:** `ZONING`
- **Verified:** count **329**; codes include GB (91), R-15 (35), O&I (34), I-2 (24), AD (21), R-8 (19), RMH (18), R-10 (17), HB (14), R-6 (13), CB (12), I-1 (8), NB (7), PUD-PDR (4), CMU (3), *-CZ conditionals
- **Route:** spatial-join parcels inside CityZoning / City_of_Elizabeth_City annex polys → use city `ZONING`; else County_Zoning_2026

### 8. County_Zoning_2026 — unincorporated / county zoning

- **REST URL:** https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/County_Zoning_2026/FeatureServer/0
- **Legacy twin:** County_Zoning (**772**)
- **Field:** `ZONING`; township `NAME`
- **Verified:** count **778**; codes A-1 (209), C-1 (125), R-15 (109), R-25 (101), I-1 (41), RMH-15 (34), EC (30), R-35A (29), A-2 (24), R-15A (16), I-2 (15), O&I/RMH-25/P-1…
- **Notes:** Prefer 2026 layer. Draft UDO proposes consolidating residential districts (see Konveio) — monitor for remap.

### 9. City_of_Elizabeth_City — annexation / city limits polys

- **REST URL:** https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/City_of_Elizabeth_City/FeatureServer/0
- **Verified:** count **74** annexation polygons (`IN_OUT`, `YEAR`, `LABEL`)
- **Notes:** Router for cities-first zoning — **not** a zoning district layer.

### 10. FLU — PDF only (no FeatureServer)

- **2023 Future Land Use Plan:** https://www.pasquotankcountync.org/s/Pasquotank_LUP_draftF7_FINAL_20230831.pdf
- **CAMA Advanced Core LUP (joint EC/Pasquotank):** https://www.pasquotankcountync.org/s/Feb-82012-revised-LUP-ecac.pdf
- **DEQ certified LUP page:** https://www.deq.nc.gov/about/divisions/coastal-management/coastal-management-land-use-planning/certified-lups/pasquotank-county
- **Status:** usable as PDF FLU guidance — **gap** for polygon FLU REST

## Municipalities (first-class)

County parcels are countywide. **Zoning authority is municipal inside Elizabeth City (+ ETJ per UDO notes); county zoning applies in unincorporated areas.** Only incorporated city substantially in Pasquotank is Elizabeth City (small portion also in Camden — Camden card separate). Unincorporated places (Weeksville, Nixonton, Newland Twp, etc.) use county zoning.

### Elizabeth City (PRIMARY city — county seat)

- **Zoning:** CityZoning FS/0 — **329** (`ZONING`); twin Elizabeth_City_Zoning **317**
- **City limits router:** City_of_Elizabeth_City FS/0 — **74**
- **FLU:** Joint CAMA LUP + city Development Services / UDO Article 9 Zoning PDFs — no city FLU FeatureServer
- **Planning / UDO:** https://elizabethcitync.gov/development-services ; UDO https://elizabethcitync.gov/index.asp?SEC=FBC83C29-03EF-4FA1-9177-AE938C78FEF2&DE=2E73BB9B-E239-4C0C-8AC0-846E26B19469
- **Notes:** Cities-first — always prefer CityZoning over County_Zoning inside city/ETJ.

### Unincorporated Pasquotank (Weeksville, Nixonton, Newland, Salem, Providence, …)

- **Zoning:** County_Zoning_2026
- **FLU:** 2023 County Future Land Use Plan PDF + CAMA/DEQ LUP
- **Ordinance:** County Zoning Ordinance PDF (amended Jan 20, 2026); draft UDO on Konveio

## PA / viewer deep-links (TRANCHE-3)

| Template | Key | Status |
|----------|-----|--------|
| `https://link.co.pasquotank.nc.us/taxcard/taxcard.cfm?PP2={PPN_2}` | PPN_2 | **Verified** HTML tax card (owner/values/sales) — e.g. PP2=72145, 64277 |
| `https://link.co.pasquotank.nc.us/taxcard/DisplayTax.cfm?SEARCH=PIN` | — | Parcel search by PIN (TCS embeds) |
| `https://lrcpwa.ncptscloud.com/pasquotank/parcel-detail/{PIN}` | PIN / PARCEL_ID | NCPTS SPA shell (200) |
| https://www.pasquotankcountync.org/tcs | — | County Parcel Information Search |
| https://pasquotankcounty.maps.arcgis.com/apps/instant/basic/index.html?appid=38fc8f0292b04ba0a300f801f17ae902 | — | Jurisdiction GIS viewer |

**Critical:** `PP2` URL parameter = layer field **`PPN_2`**, **not** `PID`. Passing `PID` as `PP2` returns ColdFusion error page.

## Gaps

- **No public FLU FeatureServer** — 2023 FLU Plan + CAMA/DEQ LUP PDFs only
- **Sale price** absent on primary CAMA — must join sales2025 / Sales_2024 (or read sales table on taxcard HTML)
- **OneMap** `saledate` / `saledatetx` empty for `cntyfips='139'`
- **Paid $200** GIS parcel download offered on GIS Office page — **do not use**; free AGOL CAMA is public
- **zoning_toh** / Hertford Town Limits on this AGOL org are **Perquimans County (Town of Hertford)** — wrong geography; reject
- **Utilities / water / sewer / hydrant** FeatureServers exist on org — **excluded** per full-suite scope (no utilities)
- No AADT, emails, phones, or paid-vendor scrapers collected
- Elizabeth City also spills into **Camden** — do not assume all EC zoning polys are Pasquotank FIPS

## License / attribution

Pasquotank County GIS / Tax; NC OneMap Integrated Cadastral; Elizabeth City Development Services. Public ArcGIS REST — attribution required. Parcel layer download fee does not apply to published FeatureServer queries.

verifiedAt: 2026-09-24
verifiedBy: North Carolina Public Info Researcher


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/PasquotankCountyNC_20260101/FeatureServer/0 · id `PARCEL_ID` · live count **22,788** · 5–150 ac **2,814** (`TAXACRES >= 5 AND TAXACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='PASQUOTANK'` gives **213** stations (112 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27PASQUOTANK%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Pasquotank'` gives **202** stations (134 with AADT_2025, 122 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Pasquotank%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `CURTOTAL` non-zero **22,661**, `TOTASSD` non-zero **22,660**
- **Sale history (partial):** price not on REST; date `DEEDDATE` non-null **16,626**. Price not on REST; Pasquotank taxcard.cfm?PP2= page is the public sale source.
- **Owner entity:** fields `OWNER1`, `OWNER2`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **520** (all parcels: 3,254), using the SQL approximation on `OWNER1`.
- **PA deep link:** `https://link.co.pasquotank.nc.us/taxcard/taxcard.cfm?PP2={PPN_2}`. Tested `65022` → HTTP **200** (text/html;charset=UTF-8), content verified: True. Owner and parcel id verified in the response.
- **Jurisdiction GIS viewer:** https://pasquotankcounty.maps.arcgis.com/apps/instant/basic/index.html?appid=38fc8f0292b04ba0a300f801f17ae902 → HTTP **200** (Basic); ArcGIS item access=public
- **Pass 2 gaps:** sale partial
