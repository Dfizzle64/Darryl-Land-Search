# Pamlico County, NC — GIS County Card

## Summary

Pamlico County (markets **[Eastern NC]**, FIPS **37137**, slug **pamlico**, `cntyfips='137'`) publishes public AGOL FeatureServers under AGD org **`nJbIFHiSnaX0z0hS`** (`services3.arcgis.com`, same stack as Chowan/Beaufort neighbors). **Wire-first parcels:** **Pamlico_ParcelService/FeatureServer/5** Parcel_Poly — ~**17,106** polys with owner (`OWNER_NAME`), mailing, situs (`SITUS_ADDR`), `CALACRES`/`CALC_ACRES`/`DEED_ACRES`, **SALE_AMT** + `SALEDATE`/`DEED_YR`, tax `LAND_VAL`/`BLDG_VAL`/`TOTAL_VAL`, parcel ids `PIN`/`MAPID`/`ACCOUNT`, and embedded **PRC** / **Print_** deep-links. ~**3,155** with `CALACRES` 5–150 (~**2,103** vacant/no bldg in band; ~**979** with sale price in band). **Cities-first zoning:** **Oriental** Growth Management Map + GMO ordinance **PDFs** (no zoning FS) — PRIMARY; Bayboro / Alliance / Arapahoe / Grantsboro / Mesic / Minnesott Beach / Stonewall / Vandemere / unincorporated — **no public base-zoning FeatureServer** (VolAgDist overlay only). **FLU:** County CAMA LUP 2004 + Future LU Map A/B + Existing LU PDFs — **no FLU FS**. **PA:** AGD PRC `http://dl.agd.cc/prc/nc/pamlico/{MAPID}.pdf` + print `?MAPID={MAPID}` + NCPTS + jurisdiction `webapp.agdmaps.com/nc/pamlico/`.

## Portals

- **County GIS Mapping Service** — https://www.pamlicocounty.org/online_services/gis_mapping_service.php
- **Jurisdiction GIS viewer (AGD webapp)** — https://webapp.agdmaps.com/nc/pamlico/
- **AGOL webappviewer (same web map)** — https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=f98ff9fb5be845b3bd35a4e97d9cbc55
- **County ArcGIS REST (AGOL)** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services
- **GDB download** — https://dl.agd.cc/pamlico/Pamlico20260609.gdb.zip
- **Tax CSV download** — https://dl.agd.cc/pamlico/Tax20260609.csv
- **Tax Department** — https://www.pamlicocounty.org/departments/tax/
- **Pay taxes online** — https://ccpaymentservice.com/PamlicoTax/
- **Tax bill lookup** — https://vdsinc.com/bill-lookup/?instance-id=pamlico-tax
- **NCPTS Pamlico hub** — https://lrcpwa.ncptscloud.com/Pamlico/
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/Pamlico/parcel-search
- **NCPTS deep-link (reid query)** — `https://lrcpwa.ncptscloud.com/Pamlico/parcel-detail?reid={PIN}`
- **NCPTS deep-link (path)** — `https://lrcpwa.ncptscloud.com/Pamlico/parcel-detail/{PIN}`
- **AGD property record card (PRIMARY PA)** — `http://dl.agd.cc/prc/nc/pamlico/{MAPID}.pdf`
- **AGD print / property card** — `http://apps.agdmaps.com/print/nc/pamlico/index.html?MAPID={MAPID}`
- **Register of Deeds (Cott)** — https://cotthosting.com/ncpamlicoexternal/LandRecords/protected/v4/SrchName.aspx
- **Deed records hub** — https://pamlicocountync.gov/online_services/deed_records_search.php
- **Ordinances and Plans** — https://pamlicocountync.gov/county_government/ordinances_and_plans.php
- **NC OneMap parcels** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='137'`)
- **Oriental GMO hub** — https://townoforiental.com/?SEC=7457091A-1C21-4FC1-9F4B-0EDF4DFF52EA
- **Oriental Town Maps** — https://townoforiental.com/maps
- **Oriental GMO Map PDF** — https://townoforiental.com/vertical/sites/%7B8227B748-6F08-4124-B0ED-02789B9A2F82%7D/uploads/6-20-23_Oriental_GMO_map.pdf
- **Oriental GMO Ordinance PDF** — https://townoforiental.com/vertical/sites/%7B8227B748-6F08-4124-B0ED-02789B9A2F82%7D/uploads/Growth_Management_Ordinance_with_160D_update.pdf
- **County CAMA LUP PDF** — https://pamlicocountync.gov/Documents/County%20Government/Plan/pamlico%20land%20use%20plan%202004.pdf
- **Future Land Use Map-A** — https://pamlicocountync.gov/Documents/County%20Government/Plan/future%20lu%20mapa.pdf
- **Future Land Use Map-B** — https://pamlicocountync.gov/Documents/County%20Government/Plan/future%20lu%20mapb.pdf
- **Existing Land Use Map** — https://pamlicocountync.gov/Documents/County%20Government/Plan/existing%20lu%20final.pdf
- **DEQ LUP hub** — https://www.deq.nc.gov/about/divisions/coastal-management/coastal-management-land-use-planning/certified-lups/pamlico-county
- **DEQ LUP PDF** — https://www.deq.nc.gov/documents/pdf/land-use-plans/pamlico-land-use-plan/download

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`; OneMap `parno`; `MAPID`; `ACCOUNT` | Trim rare leading space on PIN |
| polygons | Yes | Pamlico_ParcelService/5; OneMap FS/1 | CRS **102719 / 2264** |
| acreage | Yes | `CALACRES` (prefer); `CALC_ACRES`/`DEED_ACRES`; OneMap `gisacres`/`recareano` | ~17 polys CALACRES<<DEED — fall back |
| ownerName | Yes | `OWNER_NAME`/`OWNER_NAME2`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `OWNER_ADDR`/`OWNER_CITY`/`OWNER_STATE`/`OWNER_ZIP` | OWNER_CITY = mailing, not situs muni |
| situs address | Yes | `SITUS_ADDR`; OneMap `siteadd` | |
| lastSale date/price | Yes | **price** `SALE_AMT`; **date** `SALEDATE`/`DEED_YR`; OneMap `saledate`/`saledatetx`; QS Pamlico_Sales | QS Sale_Amount>0 → 801 |
| tax values | Yes | `LAND_VAL`/`BLDG_VAL`/`TOTAL_VAL`; OneMap `parval`/`landval`/`improvval` | Strong on both |
| zoning | Gap (PDF cities-first) | Oriental GMO Map PDF | Other munis + unincorp REST gap |
| flu | Gap (PDF) | CAMA LUP + FLU Map A/B PDFs | No FLU FS |
| appraiser / viewer link | Yes | AGD PRC `{MAPID}`; print `?MAPID=`; NCPTS `{PIN}`; webapp | TRANCHE-3 |

### Municipality router (Town Boundry NAME → city-first zoning)

| NAME | Municipality | Zoning source |
|------|--------------|---------------|
| ORIENTAL | **Oriental** | GMO Map + Ordinance PDFs (city-first PRIMARY) — no FS |
| BAYBORO | **Bayboro** (county seat) | No public zoning FS (Joint Resolution on Document Center) |
| ALLIANCE | **Alliance** | No public zoning FS |
| ARAPAHOE | **Arapahoe** | No public zoning FS (reject CO Arapahoe Zoning) |
| GRANTSBORO | **Grantsboro** | No public zoning FS |
| MESIC | **Mesic** | No public zoning FS |
| MINNESOTT | **Minnesott Beach** | No public zoning FS |
| STONEWALL | **Stonewall** | No public zoning FS |
| VANDEMERE | **Vandemere** | No public zoning FS |
| *(outside limits)* | Unincorporated | No countywide base zoning FS (VolAgDist overlay only) |

**Note:** Parcel `OWNER_CITY` is **mailing** city — do **not** use as situs municipality; spatial-join Town Boundry / Motorola City_Code.

## Layers (verified 2026-09-24)

### 1. Pamlico_ParcelService/Parcel_Poly — PRIMARY county AGOL CAMA + sale

- **Purpose:** parcels | tax | ownership | sales | situs
- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Pamlico_ParcelService/FeatureServer/5
- **Also:** Motorola_AGOL/7 twin (~17,114); Tax table FeatureServer/7 (~17,109); GDB + Tax CSV downloads
- **Key fields → targets:** `PIN`→parcelId; `MAPID`→parcelIdMap; `ACCOUNT`→accountNumber; `OWNER_NAME`/`OWNER_NAME2`→ownerName; `OWNER_ADDR`/`CITY`/`STATE`/`ZIP`→mailing; `SITUS_ADDR`→situs; `CALACRES`→acreage; `SALE_AMT`→lastSale.price; `SALEDATE`/`DEED_YR`→lastSale.date; `LAND_VAL`/`BLDG_VAL`/`TOTAL_VAL`→tax; `PRC`→appraiserDeepLink; `Print_`→agdPrintUrl; `deed_link`→deedImageUrl
- **WKID / CRS:** 102719 / 2264
- **Verified:** count **17,106**; CALACRES 5–150 → **3,155**; SALE_AMT>0 → **7,155**; sale+band → **979**; TOTAL_VAL>0 → **17,004**; LAND_VAL>0 → **15,721**; vacant band → **2,103**; owner ~**17,047**; PRC ~**17,101**
- **Notes:** **PRIMARY** wire-first. MaxRecordCount **1000** — paginate. Geo-check MAPID `D08-65` ≈ **-76.915, 35.068** (Bayboro). Auth: none (public).

### 2. NC OneMap Parcels — statewide REST + tax/sale backup

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='137'`
- **Key fields:** `parno`, `ownname`, mail/site, `gisacres`, `recareano`, `landval`/`improvval`/`parval`, `saledate`, `saledatetx`
- **Verified:** count **17,110**; gisacres 5–150 → **3,154**; recareano 5–150 → **3,220**; ownname **17,110**; parval>0 **17,012**; landval>0 **15,729**; saledate non-null **17,110**; saledatetx **17,052**
- **Notes:** Join `TRIM(parno)`=`TRIM(PIN)`. Prefer county layer for **SALE_AMT** + PRC/MAPID. MaxRecordCount **5000**.

### 3. Pamlico_Sales — Qualified Sales 2026 Reval (QS supplement)

- **REST:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Pamlico_Sales/FeatureServer/0
- **Table:** FeatureServer/3 QSalesData_ (**814**)
- **Fields:** `PIN`, `MAPID`, `Parcel_ID`, `Sale_Date`, `Sale_Amount`, `Mapped_Acres`, `Year_Blt`, `Heated_SqFt`
- **Verified:** Sale_Amount>0 → **801**; Sale_Amount>0 + Mapped_Acres 5–150 → **104**
- **Notes:** Prefer for QS join; countywide last-sale still on Parcel_Poly `SALE_AMT`/`SALEDATE`.

### 4. HistoricSales — vintage supplement

- **REST:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Pamlico_Static/FeatureServer/5
- **Verified:** **3,665** (Year 2009–2017 + null)
- **Notes:** Historic only; prefer Parcel_Poly for current sale.

### 5. Oriental zoning — city-first PRIMARY (PDF gap)

- **GMO Map PDF:** https://townoforiental.com/vertical/sites/%7B8227B748-6F08-4124-B0ED-02789B9A2F82%7D/uploads/6-20-23_Oriental_GMO_map.pdf (HTTP 200)
- **GMO Ordinance PDF:** https://townoforiental.com/vertical/sites/%7B8227B748-6F08-4124-B0ED-02789B9A2F82%7D/uploads/Growth_Management_Ordinance_with_160D_update.pdf (HTTP 200)
- **Notes:** No public zoning FeatureServer. Spatial-join Town Boundry `NAME=ORIENTAL`.

### 6. Town Boundry + VolAgDist

- **Town Boundry:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Pamlico_Static/FeatureServer/8 — **9** munis
- **VolAgDist:** Pamlico_ParcelService/4 — **14** (overlay only — not base zoning)

### 7. FLU — gap (PDF / plan docs)

- County CAMA LUP 2004 + Future LU Map A/B + Existing LU (Document Center) — all HTTP 200
- DEQ + NCDOT mirrors
- No public FLU FeatureServer found 2026-09-24

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS viewer | https://webapp.agdmaps.com/nc/pamlico/ |
| AGD PRC PDF (PRIMARY) | `http://dl.agd.cc/prc/nc/pamlico/{MAPID}.pdf` |
| AGD print / property card | `http://apps.agdmaps.com/print/nc/pamlico/index.html?MAPID={MAPID}` |
| NCPTS parcel detail (reid query) | `https://lrcpwa.ncptscloud.com/Pamlico/parcel-detail?reid={PIN}` |
| NCPTS parcel detail (path) | `https://lrcpwa.ncptscloud.com/Pamlico/parcel-detail/{PIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/Pamlico/parcel-search |
| County GIS hub | https://www.pamlicocounty.org/online_services/gis_mapping_service.php |

Example: MAPID `C07-10` / PIN `6417693661000` → http://dl.agd.cc/prc/nc/pamlico/C07-10.pdf (HTTP 200 application/pdf); http://apps.agdmaps.com/print/nc/pamlico/index.html?MAPID=C07-10 (HTTP 200). Field `PRC` on the parcel layer already stores the AGD MAPID PDF URL.

## Gaps

- No public zoning FeatureServer for Oriental (cities-first PRIMARY = GMO Map + Ordinance PDFs only)
- No public zoning FeatureServer for Bayboro, Alliance, Arapahoe, Grantsboro, Mesic, Minnesott Beach, Stonewall, Vandemere
- Unincorporated Pamlico: no countywide base-zoning FS (VolAgDist overlay only)
- FLU FeatureServer gap (CAMA LUP 2004 + Future LU Map A/B + Existing LU PDFs only)
- OWNER_CITY is mailing city — situs municipality requires Town Boundry spatial join
- Rare PIN leading-space (1) and CALACRES<<DEED mismatches (~17) — TRIM(PIN); prefer CALC_ACRES/DEED_ACRES when CALACRES anomalous
- NCPTS parcel-detail is SPA (HTTP 200 shell) — primary PA deep-link is AGD PRC PDF by MAPID
- Utilities / AADT / emails / phones / paid vendors intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** Pamlico_ParcelService/5 count/acres/sale/tax/owner + geo sample; OneMap `cntyfips='137'` counts; Pamlico_Sales QS 801; HistoricSales 3665; Town Boundry 9; VolAgDist 14; AGD PRC/print MAPID + webapp + GDB/CSV 200; Oriental GMO Map+Ordinance PDFs 200; county FLU/CAMA PDFs 200; NCPTS hub/search 200; rejected utilities + CO Arapahoe Zoning


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Pamlico_ParcelService/FeatureServer/5 · id `PIN` · live count **17,106** · 5–150 ac **3,155** (`CALACRES >= 5 AND CALACRES <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='PAMLICO'` gives **117** stations (77 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27PAMLICO%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Pamlico'` gives **116** stations (70 with AADT_2025, 76 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Pamlico%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `TOTAL_VAL` non-zero **17,004**, `LAND_VAL` non-zero **15,721**
- **Sale history (ok):** price `SALE_AMT` >0 **7,155**; date `SALEDATE` non-null **17,047**
- **Owner entity:** fields `OWNER_NAME`, `OWNER_NAME2`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **750** (all parcels: 2,935), using the SQL approximation on `OWNER_NAME`.
- **PA deep link:** `http://dl.agd.cc/prc/nc/pamlico/{MAPID}.pdf`. Tested `C08-1-32` → HTTP **200** (application/pdf), content verified: True. Owner and parcel id verified in the response.
- **Jurisdiction GIS viewer:** https://webapp.agdmaps.com/nc/pamlico/ → HTTP **200** (ArcGIS Web Application)
- **Pass 2 gaps:** none
