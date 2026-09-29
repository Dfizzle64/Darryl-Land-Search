# Perquimans County, NC — GIS County Card

## Summary

Perquimans County (markets **[Outer Banks / Eastern NC]**, FIPS **37143**, slug **perquimans**, `cntyfips='143'`) publishes public AGOL FeatureServers under org owner **tpenegar** / **agdonline.maps.arcgis.com** (`services3.arcgis.com/nJbIFHiSnaX0z0hS`). **Wire-first parcels:** **Perquimans_Service/FeatureServer/2** Parcels_2017 (legacy name; live CAMA twin **/15** Parcels_append) — ~**15,071** polys with owner (`NAME`), mailing (`ADDRESS_1`/`ADDRESS_2`/`ADDRESS_3`), `dacre`/`DEED_ACRE`, tax `TAX_VAL`/`LAND_USE_V`, sale-date `DATE_SOLD` (MMYYYY.; **no SALE_PRICE**), deed `DEED_BK_1`/`DEED_PG_1`, parcel id `parcel_id`/`pin`/`ACCT`, township `TOWNSHIP`, and **PRC** property-search deep-link. ~**2,912** with `dacre` 5–150 (~**3,008** by Shape acres). **Cities-first zoning:** **Town of Hertford** Zoning Map + ordinance PDFs PRIMARY (RA/R10/R8/R6/TR/C1–C6/O/1/M1; no town FS); **Winfall** Town Limits carve-out on county layer (no town FS); **PERQ_ZONING** FS/4 (**108** polys) for county unincorporated districts + Hertford ETJ / Winfall Town Limits carve-outs. **FLU:** joint Perquimans–Hertford–Winfall CAMA LUP (recertified 2018) PDF — **no FLU FeatureServer**. **PA:** `https://www.perquimanscountync.com/search?for={parcel_id}` + NCPTS `parcel-detail?reid={pin}` + jurisdiction `perquimans.agdmaps.com` / webappviewer Parcel App.

## Portals

- **Jurisdiction GIS (AGD Parcel App alias)** — http://perquimans.agdmaps.com/
- **Jurisdiction GIS (webappviewer)** — https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=559506e85ee046a194333eb12e80710f
- **Property Cards / GIS Tax Maps hub** — https://www.perquimanscountync.gov/property-cards-and-gistax-maps
- **Property Cards search (PA deep-link)** — `https://www.perquimanscountync.com/search?for={parcel_id}`
- **Property Cards home** — https://www.perquimanscountync.com/
- **County ArcGIS REST (AGOL)** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services
- **Perquimans_Service** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Perquimans_Service/FeatureServer
- **NCPTS Perquimans hub** — https://lrcpwa.ncptscloud.com/Perquimans/
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/Perquimans/parcel-search
- **NCPTS deep-link (reid query)** — `https://lrcpwa.ncptscloud.com/Perquimans/parcel-detail?reid={pin}`
- **NCPTS deep-link (path)** — `https://lrcpwa.ncptscloud.com/Perquimans/parcel-detail/{pin}`
- **NCPTS deep-link alt (parcel_id)** — `https://lrcpwa.ncptscloud.com/Perquimans/parcel-detail?reid={parcel_id}`
- **Tax pay (WebTaxPay)** — http://perquimans.webtaxpay.com/
- **Register of Deeds hub** — https://www.perquimanscountync.gov/register-of-deeds
- **NC OneMap parcels** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='143'`)
- **Planning & Zoning** — https://www.perquimanscountync.gov/planning-and-zoning
- **DEQ certified LUP hub** — https://www.deq.nc.gov/about/divisions/coastal-management/coastal-management-land-use-planning/certified-lups/perquimans-county
- **Joint CAMA LUP PDF (Perquimans–Hertford–Winfall)** — https://www.deq.nc.gov/documents/pdf/land-use-plans/perquimanshertwinf-certlupamend2-030518-combined/download
- **DEQ implementation report PDF** — https://www.deq.nc.gov/documents/pdf/land-use-plans/implementation-reports/perqimplementreport-030818/download
- **Town of Hertford Planning & Zoning** — https://townofhertfordnc.com/planning_and_zoning
- **Hertford Zoning Map PDF** — https://townofhertfordnc.com/vertical/sites/%7B143CFF3A-672B-44D4-B23C-E6364EF3CC86%7D/uploads/Zoning_Map(1).pdf
- **Hertford Use District List PDF** — https://townofhertfordnc.com/vertical/sites/%7B143CFF3A-672B-44D4-B23C-E6364EF3CC86%7D/uploads/Use_District_List.pdf
- **Hertford Zoning Ord. Art. 3 PDF** — https://townofhertfordnc.com/vertical/sites/%7B143CFF3A-672B-44D4-B23C-E6364EF3CC86%7D/uploads/Article-3-Zoning-Ord.pdf
- **Hertford Zoning Ordinances hub** — https://townofhertfordnc.com/index.asp?DE=33161E70-D28B-4EA4-A26F-A05DE3DA87FF&SEC=38436A8D-77D3-4C75-B1CA-DCE512D081EC

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `parcel_id`; `pin`; OneMap `parno`/`altparno`; `ACCT` | e.g. `2-D085-F097-SH` / `7855-97-7194` |
| polygons | Yes | Perquimans_Service/2 (/15 twin); OneMap FS/1 | CRS **3359 / 3404** |
| acreage | Yes | `dacre` (prefer); `DEED_ACRE`; OneMap `gisacres` | ~**2,912** in 5–150 |
| ownerName | Yes | `NAME`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `ADDRESS_1`/`ADDRESS_2`/`ADDRESS_3` | Mailing city ≠ situs muni |
| situs address | Partial | SiteAddressPoints/10 `label`; property-card Location | Parcel ADDRESS_* is mailing; OneMap `siteadd` empty |
| lastSale date/price | Partial | `DATE_SOLD` (MMYYYY.); OneMap `saledatetx` | **No SALE_PRICE** on REST |
| tax values | Yes | `TAX_VAL`; OneMap `parval`/`landval`/`improvval`; card Land/Bldg/Out | Strong |
| zoning | Yes (cities-first) | Hertford Zoning Map PDF PRIMARY + PERQ_ZONING/4 county | Winfall FS gap |
| flu | Gap (PDF) | Joint CAMA LUP PDF (DEQ) | No FLU FeatureServer |
| appraiser / viewer link | Yes | PRC `search?for={parcel_id}`; NCPTS; perquimans.agdmaps.com | TRANCHE-3 |

### Municipality router (cities-first)

| Source | Municipality | Zoning source |
|--------|--------------|---------------|
| Hertford (seat) | **Hertford** | Zoning Map + Use District List + Art. 3 ordinance PDFs PRIMARY (RA/R10/R8/R6/TR/C1–C6/O/1/M1); PERQ_ZONING `Hertford ETJ` carve-out (~4,700 ac) |
| Winfall | **Winfall** | PERQ_ZONING `Winfall Town Limits` carve-out (3 polys, ~1,482 ac); **no town zoning FS** found 2026-09-24 |
| *(outside carve-outs)* | Unincorporated | PERQ_ZONING FS/4 district polys (RA/RA-15/25/32/43, CH/CN/CR, HA, IH/IL, CZD) |

**Townships (FS/8 / parcel TOWNSHIP):** Belvidere, Parkville, Hertford, New Hope, Bethel — do **not** treat as incorporated munis; spatial-join carve-outs / town PDFs for city-first.

**Note:** Parcel `ADDRESS_2` often embeds mailing city (HERTFORD, VA Beach, …) — mailing only.

### PERQ_ZONING districts (zone / count)

| zone | ~Count | zone_des |
|------|--------|----------|
| RA-43 | 24 | Residential and Agricultural District |
| CR | 21 | Rural Commercial District |
| RA-25 | 19 | Residential and Agricultural District |
| RA | 18 | Rural Agriculture District |
| RA-15 | 5 | Residential and Agricultural District |
| CH | 5 | Highway Commercial District |
| CZD | 4 | Conditional Zoning District |
| Winfall Town Limits | 3 | *(muni carve-out)* |
| RA-32 | 2 | Residential and Agricultural District |
| HA | 2 | Historic Agriculture District |
| CN | 2 | Neighborhood Commercial District |
| Hertford ETJ | 1 | *(muni carve-out)* |
| IH | 1 | Heavy Industrial District |
| IL | 1 | Light Industrial District |

## Layers (verified 2026-09-24)

### 1. Perquimans_Service/Parcels_2017 — PRIMARY county AGOL CAMA (+ PRC)

- **Purpose:** parcels | tax | ownership | sale-date | situs-mail | PA
- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Perquimans_Service/FeatureServer/2
- **Twin:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Perquimans_Service/FeatureServer/15 (Parcels_append; numeric `TAX_VAL`)
- **Key fields → targets:** `parcel_id`→parcelId; `pin`→parcelIdAlt; `ACCT`→accountNumber; `NAME`→ownerName; `ADDRESS_1`/`ADDRESS_2`/`ADDRESS_3`→mailing; `dacre`→acreage; `DEED_ACRE`→acreageDeed; `TAX_VAL`→tax; `LAND_USE_V`→landUseValue; `DATE_SOLD`→lastSale.date (MMYYYY.); `DEED_BK_1`/`DEED_PG_1`→deed; `TOWNSHIP`→township; `PRC`→appraiserDeepLink
- **WKID / CRS:** 3359 / 3404
- **Verified:** count **15,071**; dacre 5–150 → **2,912**; Shape acres 5–150 → **3,008**; TAX_VAL nonempty → **14,874**; NAME → **14,904**; DATE_SOLD ≠ `000000.` → **14,142**; PRC → **15,071**
- **Notes:** **PRIMARY** wire-first (web map uses /2). MaxRecordCount **1000** — paginate. **No SALE_PRICE**. Geo-check `3-0068-00009` / `7826-64-4372` centroid ≈ **-76.541, 36.102**. Auth: none (public).

### 2. NC OneMap Parcels — statewide REST fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='143'`
- **Key fields:** `parno`(=pin), `altparno`(=parcel_id), `ownname`, `mailadd`, `gisacres`, `parval`/`landval`/`improvval`, `saledatetx` (no `saledate`)
- **Verified:** count **15,019**; gisacres 5–150 → **3,005**; ownname **14,830**; parval>0 **14,800**; landval>0 **1,929**; **saledate 0**; saledatetx nonempty **13,695**; **siteadd 0**
- **Notes:** Prefer county for PRC/`DATE_SOLD`/`dacre`. saledatetx is not sale price.

### 3. PERQ_ZONING + overlays — county zoning (+ muni carve-outs)

- **PERQ_ZONING:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Perquimans_Service/FeatureServer/4 — **108** polys; fields `zone`/`zone_des`
- **Overlay CTCOD:** FS/3 (**2**; layer titled WTOD_and_HCOD but data = Communications Tower Corridor Overlay)
- **SUP/CUP:** FS/5 and twin FS/14 (**63**)

### 4. Zoning — cities-first Hertford PDF (+ Winfall carve-out)

- **PRIMARY (Hertford):** Zoning Map PDF + Use District List + Art. 3 (town limits + ETJ)
- **Winfall:** limits carve-out only — **no district FeatureServer** found 2026-09-24
- **Unincorporated:** PERQ_ZONING district polys

### 5. FLU — gap (CAMA LUP PDF)

- DEQ joint LUP PDF (HTTP 200, ~33.6 MB) + county Planning hub listing “2016 Joint CAMA Land Use Plan Update - Recertified 3-5-2018”
- **No public labeled FLU FeatureServer** found 2026-09-24

### 6. Supporting layers

- Townships/8, County_outline/6, Address Points/10 (~9,658; situs labels — do not harvest phones), Centerlines/1|/11, Soft_Lines/13, Parcel_Lines/12, Flood PerquimansFloodZones, soils/7

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS (agdmaps) | http://perquimans.agdmaps.com/ |
| Jurisdiction GIS (webappviewer) | https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=559506e85ee046a194333eb12e80710f |
| Property search / PRC (parcel_id) | `https://www.perquimanscountync.com/search?for={parcel_id}` |
| NCPTS parcel detail (reid / pin) | `https://lrcpwa.ncptscloud.com/Perquimans/parcel-detail?reid={pin}` |
| NCPTS parcel detail (path) | `https://lrcpwa.ncptscloud.com/Perquimans/parcel-detail/{pin}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/Perquimans/parcel-search |
| Tax pay | http://perquimans.webtaxpay.com/ |
| County GIS/cards hub | https://www.perquimanscountync.gov/property-cards-and-gistax-maps |

Example: parcel_id `2-D085-F097-SH` → https://www.perquimanscountync.com/search?for=2-D085-F097-SH (HTTP 200; owner/tax summary + `/prc/4986` card). Field `PRC` on the parcel layer already stores the search URL. NCPTS reid/path HTTP 200 (SPA shell).

## Gaps

- **Sale price REST gap** — no `SALE_PRICE`; `DATE_SOLD` / OneMap `saledatetx` are month-year text only
- Situs not on parcel polygons (mailing only) — join address points or property-card Location
- Hertford zoning FeatureServer gap (PDF map + ordinance)
- Winfall zoning FeatureServer gap (limits carve-out only)
- FLU FeatureServer gap (joint CAMA LUP PDF)
- `dl.agd.cc/prc/nc/perquimans` **404** and `apps.agdmaps.com/print/nc/perquimans` **404**
- Experience `268c396e…` is statewide OneMap — not county jurisdiction GIS
- Layer title `Parcels_2017` is legacy naming
- Address-points layer contains phone fields — intentionally out of scope
- Utilities / AADT / emails / phones / paid vendors intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** Perquimans_Service/2 count/acres/tax/owner/DATE_SOLD/PRC + Hertford geo sample; /15 twin; /4 PERQ_ZONING 108 + zone legend; /3 CTCOD overlay; /5 SUP 63; /8 townships; /10 address points; OneMap `cntyfips='143'` counts (saledate empty; saledatetx text-only); PRC search + NCPTS + agdmaps/webappviewer 200; Hertford Zoning Map + Use District List + Art. 3 PDF 200; DEQ joint CAMA LUP PDF 200; rejected dl.agd.cc/prc + AGD print 404; rejected Experience 268c… as county GIS


## PASS 2 full-suite upgrade (NC non-OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Pass 1 re-verify (verified):** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Perquimans_Service/FeatureServer/2 polygons load (sample centroid [-76.5222, 36.1033]); `parcel_id` filled on 15,059 of 15,071; `dacre` 5–150 ac **2,912**.
- **Attribute layer for Pass 2:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Perquimans_Service/FeatureServer/2 · id `parcel_id` · live count **15,071** · 5–150 ac **2,912** (`dacre >= 5 AND dacre <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='PERQUIMANS'` gives **151** stations (80 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27PERQUIMANS%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Perquimans'` gives **149** stations (86 with AADT_2025, 74 with AADT_2024, 142 with either; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Perquimans%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json. Use AADT_2025, then AADT_2024, then AADT_2022, whichever is filled first.
- **Tax values (ok):** `TAX_VAL` non-zero **14,874** TAX_VAL is a string: CAST(TAX_VAL AS FLOAT) > 0.
- **Sale history (partial):** price not on REST; date `DATE_SOLD` non-null **14,904**. DATE_SOLD (string) on layer; no price on REST or on the county search summary page. Price only via the property card linked from that page ([View Property Card] /prc/{opaque id}).
- **Owner entity:** field `NAME`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **276** (all parcels: 1,527), using the SQL approximation (runs slightly high).
- **PA deep link:** `https://www.perquimanscountync.com/search?for={parcel_id}`. Tested `2-0085-0005I` (https://www.perquimanscountync.com/search?for=2-0085-0005I) → HTTP **200** (text/html; charset=utf-8), content verified: True. County search page returns an owner/value summary with the map number; the summary shows Taxable Value $0 for a parcel with land and building value.
- **Jurisdiction GIS viewer:** http://perquimans.agdmaps.com/ → HTTP **200** (ArcGIS Web Application); redirects to https://agdonline.maps.arcgis.com/apps/webappviewer/index.html?id=559506e85ee046a194333eb12e80710f
- **Pass 2 gaps:** sale partial
