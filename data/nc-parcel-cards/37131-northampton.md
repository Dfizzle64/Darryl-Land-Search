# Northampton County, NC — GIS County Card

## Summary

Northampton County (Eastern NC / Rocky Mount shed, FIPS **37131**, slug **northampton**, `cntyfips='131'`) outsources public mapping to **AGD Maps** (`webapp.agdmaps.com/nc/northampton/`). **Wire-first parcels (TRANCHE-3):** **NorthamptonService/FeatureServer/8** — ~**20,561** polys with `PIN` (e.g. `5032-41-4749`), `PARCELNBR` (`0302029`), owner, mailing, situs (`Parcel_Address`), `Acreage`, **`Sale_Price`** + `Date_Recorded`, and `Tax_Value`, plus embedded **`PRC`** PDF deep-link. ~**4,886** with acres 5–150 (~**1,423** with `Sale_Price>0` in range). **Zoning is cities-first:** **Rich Square** UCPCOG **Official Zoning** (`Town_of_Rich_Square_WFL1/4` + twin `Zoning/0`, ~**25**, `Type`) and **Land Use FLU** (`Land_Use/0`, ~**830**). **Jackson** (seat) / Gaston / Conway / Seaboard / Woodland / Severn / Lasker / Garysburg — **zoning REST gaps**. County zoning ordinance + Comp Plan are **PDF only** (no countywide zoning/FLUM FeatureServer). **NC OneMap** (`cntyfips='131'`, ~**20,504**) is a strong geometry/owner/situs/tax fallback (prefer AGD for **sale price**). **Reject** `gis.northamptoncounty.org` / `northampton.maps.arcgis.com` — those are **Pennsylvania**. Markets: **[Eastern NC, Rocky Mount]**.

## Portals

- **Map viewer (jurisdiction GIS URL)** — https://webapp.agdmaps.com/nc/northampton/
- **Viewer find-by-PIN** — `https://webapp.agdmaps.com/nc/northampton/?find={PIN}`
- **County GIS Maps page** — https://www.northamptonnc.com/213/GIS-Maps (embeds AGD viewer)
- **Internet Maps** — https://www.northamptonnc.com/232/Internet-Maps
- **AGD / NorthamptonService REST** — https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/NorthamptonService/FeatureServer
- **PA deep-link (PRC PDF; preferred)** — `https://dl.agd.cc/prc/nc/northampton/pin{PIN}.pdf`
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/northampton/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/northampton/parcel-detail/{PARCELNBR}` (alt `{PIN}`)
- **Tax Department** — https://www.northamptonnc.com/179/Tax-Department
- **Online tax payment forms** — https://www.northamptonnc.com/214/Online-Tax-Payment-Forms
- **Planning & Zoning** — https://www.northamptonnc.com/167/Planning-Zoning
- **Zoning Ordinance PDF** — https://www.northamptonnc.com/DocumentCenter/View/330/Zoning-Ordinance-12-20-16-PDF
- **Comprehensive Plan (Adopted PDF)** — https://www.northamptonnc.com/DocumentCenter/View/135/Northampton-County-Comprehensive-Plan-Adopted-PDF
- **Comp Plan Executive Summary** — https://www.northamptonnc.com/DocumentCenter/View/134/Northampton-County-Comprehensive-Plan-Executive-Summary-PDF
- **GIS howto PDF** — https://www.northamptonnc.com/DocumentCenter/View/559/How-to-access-the-Northampton-County-GIS-Data
- **Annual sales spreadsheets (zip)** — https://dl.agd.cc/northampton/nhsales.zip
- **CitizenServe permits portal** — https://citizenserve.com/Portal/PortalController?Action=showHomePage&ctzPagePrefix=Portal_&installationID=northamptonnc
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='131'`; alt `services.gis.nc.gov`)

## Municipalities (first-class)

| Municipality | Local public GIS? | Zoning / FLU source |
|--------------|-------------------|---------------------|
| **Rich Square** | UCPCOG AGOL | **CITY-FIRST PRIMARY** `Town_of_Rich_Square_WFL1/4` Official Zoning (25, `Type`) + twin `Zoning/0`. **FLU** `Land_Use/0` (830, `Land_Use` 01–12/14). Exclude utility layers 0–3 |
| **Jackson** (county seat) | Limits only | **Zoning REST gap** — City_Polygon `JACKSON`; county ordinance may apply |
| Gaston | Limits only | **Zoning REST gap** (near Halifax / Roanoke Rapids) |
| Conway | Limits only | **Zoning REST gap** |
| Seaboard | Limits only | **Zoning REST gap** |
| Woodland | Limits only | **Zoning REST gap** |
| Severn | Limits only | **Zoning REST gap** |
| Lasker | Limits only | **Zoning REST gap** |
| Garysburg | Limits only | **Zoning REST gap** |
| Unincorporated | County Planning | Zoning Ordinance PDF + Official Zoning Map (no public FS); Comp Plan PDF — **FLU REST gap** |

`City_Polygon` NAME values (9): SEVERN, GASTON, SEABOARD, GARYSBURG, CONWAY, JACKSON, LASKER, WOODLAND, RICH SQUARE.

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN` (PRC/map); `PARCELNBR` (NCPTS); OneMap `parno`↔PIN / `altparno`↔PARCELNBR | Prefer PIN for PRC |
| polygons | Yes | NorthamptonService/8; OneMap FS/1 | CRS **102719 / 2264** |
| acreage | Yes | `Acreage`; OneMap `gisacres` | ~**4,886** in 5–150 |
| ownerName | Yes | `Owner` / OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `Billing_Address`/`Billing_City_ST`/`Billing_Zip`; OneMap `mailadd` | |
| situs address | Partial→Yes | `Parcel_Address` (~53%); **prefer** OneMap `siteadd` (full) | Join on PIN |
| lastSale date/price | Yes | `Sale_Price`,`Date_Recorded`,`Deed_Reference` | OneMap has saledate, **no price** |
| tax values | Yes | `Tax_Value`; OneMap `parval`/`landval` | improvval often empty |
| zoning | Yes (cities-first RS) | Rich Square `Type` | Spatial join inside RS limits |
| flu | Yes (RS only) | Rich Square `Land_Use` | County Comp Plan PDF gap |
| dorCode / land use | Partial | OneMap `parusecode` | Local |
| appraiser / viewer link | Yes | PRC `pin{PIN}.pdf`; NCPTS `{PARCELNBR}`; viewer `?find={PIN}` | Tranche-3 OK |

## Layers (verified)

### 1. NorthamptonService Parcels — PRIMARY

- **Purpose:** parcels | tax | ownership | sales (last)
- **REST URL:** https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/NorthamptonService/FeatureServer/8
- **Geometry:** Polygon | **CRS:** 102719 / 2264 | **MaxRecordCount:** 1000
- **Key fields → targets:** `PIN`→parcelId; `PARCELNBR`→account; `Acreage`→acreage; `Owner`→owner; `Billing_*`→mailing; `Parcel_Address`→situs; `Sale_Price`/`Date_Recorded`/`Deed_Reference`→lastSale; `Tax_Value`→tax; `PRC`→appraisalCardUrl; `Account`→accountId
- **Verified:** count **20,561**; Acreage 5–150 → **4,886**; Sale_Price>0 → **6,719**; sale in band → **1,423**; Owner **20,370**; Parcel_Address **10,809**; Tax_Value>0 **20,338**; PRC **20,538**
- **Notes:** PRIMARY. Paginate (max 1000). Sample: PIN `5032-41-4749` / PARCELNBR `0302029` / Account `135453` ≈ **-77.185, 36.541**. Band sample: PIN `5012-91-4563` / PARCELNBR `0903166` Sale_Price 100000.

### 2. NC OneMap Parcels (fallback)

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='131'`
- **Alternate host:** `services.gis.nc.gov`
- **Verified:** count **20,504**; gisacres 5–150 → **4,874**; parval>0 **20,256**; ownname/siteadd **20,504**; saledate populated (no sale price field)
- **Notes:** `parno`↔PIN; `altparno`↔PARCELNBR. Prefer for situs fill; join AGD for Sale_Price. MaxRecordCount 5000.

### 3. Rich Square Official Zoning — city-first PRIMARY

- **REST URL:** https://services8.arcgis.com/eJ9GuQwMsO1iIOw1/arcgis/rest/services/Town_of_Rich_Square_WFL1/FeatureServer/4
- **Count:** **25** | field `Type` (+ `Description`)
- **Top codes:** R-20 5, C-1 4, A-0 4, C-2 3, R-10 3, R-40 2, I-1 2, R-MH 2
- **Alternate twin:** https://services8.arcgis.com/eJ9GuQwMsO1iIOw1/arcgis/rest/services/Zoning/FeatureServer/0 (Official_Zoning_ExportFeatures; parcel-aligned 02.14.25)
- **Notes:** Do **not** ingest WFL1 layers 0–3 (water/sewer utilities — excluded)

### 4. Rich Square Land Use — city-first FLU

- **REST URL:** https://services8.arcgis.com/eJ9GuQwMsO1iIOw1/arcgis/rest/services/Land_Use/FeatureServer/0
- **Count:** **830** | field `Land_Use` | CNTYFIPS=`131`
- **Codes:** 01 Large-tract MH, 02 Agricultural, 03 Commercial, 04 Industrial, 05 Inst-Other, 06 Inst-Public, 07 Multi-Family, 08 MH, 09 SFR, 10 Two-Family, 11 Utilities, 12 Vacant/Undeveloped, 14 Unclassified
- **Top:** 09 → 466, 12 → 236, 03 → 56

### 5. City limits + ETJ (routers)

- **City_Polygon:** …/NorthamptonStatic/FeatureServer/4 | count **9** | `NAME`
- **ETJ:** …/NorthamptonStatic2/FeatureServer/1 | count **2** | no muni name — spatial only
- **Townships:** …/NorthamptonStatic2/FeatureServer/3 | `twnship`

### 6. County zoning + county FLU — gaps

- **County Zoning Ordinance:** DocumentCenter/View/330 — districts AR / R-15 / R-10 / HB / NB / LI / HI + watershed variants — **no public FeatureServer**
- **Comp Plan:** DocumentCenter/View/135 (Adopted) + View/134 (Exec Summary) — **no FLUM REST**
- **Legacy MapJournal** “Northampton County Zoning” (wcreed) — nested webmap **inaccessible**

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS map | https://webapp.agdmaps.com/nc/northampton/ |
| Viewer find | `https://webapp.agdmaps.com/nc/northampton/?find={PIN}` |
| PRC PDF (preferred PA) | `https://dl.agd.cc/prc/nc/northampton/pin{PIN}.pdf` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/northampton/parcel-detail/{PARCELNBR}` (alt `{PIN}`) |
| NCPTS search | https://lrcpwa.ncptscloud.com/northampton/parcel-search |

Example: PIN `5032-41-4749` → https://dl.agd.cc/prc/nc/northampton/pin5032-41-4749.pdf (PDF HTTP 200 verified). PARCELNBR `0302029` → NCPTS parcel-detail SPA 200.

## Gaps

- No Northampton County ArcGIS Server root — depend on AGD AGOL + OneMap + UCPCOG Rich Square
- County Official Zoning Map / ordinance — **REST gap** (PDF only)
- Jackson / Gaston / Conway / Seaboard / Woodland / Severn / Lasker / Garysburg — **zoning REST gaps**
- **County FLU gap** — Comp Plan PDF; Rich Square Land_Use only
- OneMap sale **price** absent — prefer AGD `Sale_Price`
- AGD situs `Parcel_Address` partial — prefer OneMap `siteadd`
- `apps.agdmaps.com/print/nc/northampton` **404** — use PRC PDF
- **Reject PA** hosts `gis.northamptoncounty.org` and `northampton.maps.arcgis.com`
- Rich Square utility layers excluded; last-sale only on parcel; MaxRecordCount **1000** — paginate; no phones/emails; no AADT/utilities; no paid vendors

## License / verification

Northampton County NC public GIS (AGD Maps) + Town of Rich Square / UCPCOG + NC OneMap; free public query endpoints; attribution recommended; NCGS 132-10 for commercial resale; no paid vendors.

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** NorthamptonService/8 counts + Sale_Price band; Rich Square Zoning/4+Zoning/0 Type histogram; Land_Use/0 830; OneMap `cntyfips='131'` 20504; PRC PDFs 200; NCPTS search/detail SPA 200; Comp Plan + Zoning Ordinance PDFs 200; geo-check PIN 5032-41-4749 ≈ -77.185, 36.541; rejected PA Northampton REST
