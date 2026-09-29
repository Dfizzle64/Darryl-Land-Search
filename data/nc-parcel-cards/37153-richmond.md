# Richmond County, NC — GIS County Card

## Summary

Richmond County (Fayetteville / Charlotte shed, FIPS **37153**, slug **richmond**, `cntyfips='153'`) publishes public ArcGIS Enterprise at **`gis.richmondnc.com`** (portal + `server/rest`). **Wire-first parcels:** **GISWebsite/ParcelViewer** MapServer/**12** — **~32,662** polys with owner (`Name`), mailing, tax values (`TaxValue` / `LandValue` / `BuildingValue`), `SaleDate`, deed refs, `CalculatedAcres` / `AssessedAcreage`. **~5,403** with `CalculatedAcres` 5–150 (~**3,552** building 0/null). **Sale price REST gap** — price lives on ITSPublic **AppraisalCard** PDF (verified, e.g. PIN `747416748126` deed sale **$89,000**). **Cities-first zoning intent:** Rockingham / Hamlet / Ellerbe / Hoffman / Norman / Dobbins Heights administer municipal zoning (building-permit checklist) but **no public muni zoning FeatureServer** found — use **City Limits** + **City_ETJ** for routing; **County Zoning** MapServer/**14** (**69** polys; `DistrictCode` A-R / C-C / C-R / H-C / H-I / L-I / R-R / V-R) for unincorporated. **FLU:** Strategic Land Use Plan **PDF only** (adopted 2022). **PA deep-link:** `https://gis.richmondnc.com/ITSPublic/AppraisalCard.aspx?id={PIN}` (PDF verified). **Jurisdiction GIS:** https://gis.richmondnc.com/maps/. **NC OneMap** `cntyfips='153'`. Markets: **[Fayetteville, Charlotte]**.

## Portals

- **Jurisdiction GIS (Parcel Viewer)** — https://gis.richmondnc.com/maps/
- **County ArcGIS REST (Enterprise)** — https://gis.richmondnc.com/server/rest/services
- **ParcelViewer MapServer** — https://gis.richmondnc.com/server/rest/services/GISWebsite/ParcelViewer/MapServer
- **Portal** — https://gis.richmondnc.com/portal/
- **PA Basic Search (ITSPublic)** — https://gis.richmondnc.com/ITSPublic/
- **Real Estate Search** — https://gis.richmondnc.com/ITSPublic/RealEstateSearch
- **Tax Bill Search** — https://gis.richmondnc.com/ITSPublic/TaxBillSearch
- **PA AppraisalCard deep-link (PIN)** — `https://gis.richmondnc.com/ITSPublic/AppraisalCard.aspx?id={PIN}`
- **Tax Bill deep-link (PIN)** — `https://gis.richmondnc.com/ITSPublic/TaxBillSearch/Parcel/{PIN}`
- **GIS Department** — https://www.richmondnc.com/165/GIS
- **Land Records / Mapping** — https://www.richmondnc.com/187/Land-Records-and-Mapping
- **Tax Department** — https://www.richmondnc.com/176/Tax-Department
- **Planning & Zoning** — https://www.richmondnc.com/175/Planning-Zoning
- **Richmond County UDO (PDF)** — https://www.richmondnc.com/DocumentCenter/View/7580/RICHMOND-COUNTY-UDO
- **Strategic Land Use Plan (FLU PDF, 2022)** — https://www.richmondnc.com/DocumentCenter/View/6377
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='153'`)
- **Legacy GIS host (gis3)** — https://gis3.richmondnc.com/arcgis/rest/services — TLS handshake fails from some research egress; prefer `gis.richmondnc.com`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | ParcelViewer `PIN`; OneMap `parno` | 12-digit PIN; AppraisalCard / TaxBill use same |
| polygons | Yes | ParcelViewer/12; OneMap | CRS **102100/3857** on ParcelViewer |
| acreage | Yes | `CalculatedAcres`; parse `AssessedAcreage` (`"18.100 AC"`); OneMap `gisacres` | Prefer CalculatedAcres / gisacres for 5–150 band |
| ownerName | Yes | `Name`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `MailingAddress`,`City`,`State`,`ZipCode` | |
| situs address | Yes (join) | AddressPoints `FullAddress` / `PARCELNUM`→`PIN`; AppraisalCard | Not on parcel polygon attrs |
| lastSale date/price | Partial | `SaleDate` (epoch ms); price on AppraisalCard | **Sale price REST gap** |
| tax values | Yes | `TaxValue`,`LandValue`,`BuildingValue`; OneMap `parval`/`landval`/`improvval` | |
| zoning | Partial | County Zoning `DistrictCode`/`DistrictName` | Unincorp only; **muni zoning REST gap** |
| flu | Gap | Strategic Land Use Plan PDF | No FeatureServer |
| appraiser / viewer link | Yes | AppraisalCard `{PIN}`; maps/; TaxBillSearch/Parcel/{PIN} | TRANCHE-3 |

### Municipalities (City Limits / Address Inc_Muni)

| Municipality | Role | Addr pts (Inc_Muni) | Zoning REST |
|--------------|------|---------------------|-------------|
| **Rockingham** | city-first intent / **gap** | ~4,559 | No public FS — city limits + ETJ only |
| **Hamlet** | city-first intent / **gap** | ~3,012 | No public FS — city limits + ETJ only |
| Ellerbe | gap | ~554 | No public FS |
| Hoffman | gap | ~306 | No public FS |
| Dobbins Heights | gap | ~567 | No public FS |
| Norman | gap | ~100 | No public FS |
| Unincorporated | county zoning | ~17,487 (Inc_Muni=County) | County Zoning/14 |

## Layers (verified 2026-09-24)

### 1. GISWebsite/ParcelViewer Parcels — PRIMARY CAMA

- **REST:** https://gis.richmondnc.com/server/rest/services/GISWebsite/ParcelViewer/MapServer/12
- **Geometry:** Polygon — CRS **102100 / 3857**
- **Key fields → targets:** `PIN` → parcelId; `Name` → ownerName; `MailingAddress`/`City`/`State`/`ZipCode` → mailing; `CalculatedAcres` → acreage; `AssessedAcreage` → acreage (text); `SaleDate` → lastSale.date; `DeedBook`/`DeedPage` → other; `TaxValue`/`LandValue`/`BuildingValue` → tax; `FireDistrict`/`Township` → other
- **Verified:** count **32,662**; CalculatedAcres 5–150 → **5,403**; TaxValue>0 → **32,605**; LandValue>0 → **32,540**; BuildingValue>0 → **17,402**; SaleDate not null → **32,302**; owner Name → **32,538**; mailing → **31,910**; building=0 in band → **3,552**
- **Notes:** **PRIMARY** wire-first. Auth **none**. MaxRecordCount **2000** — paginate. **No SalePrice field.** Geo-check PIN `747416748126` ≈ **-79.74 / 34.97** (Rockingham). Mirror twin on legacy `gis3` Public/RichmondParcelViewer/12 (TLS fragile).

### 2. NC OneMap Parcels — statewide fallback

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='153'`
- **Verified:** count **32,625**; gisacres 5–150 → **5,392**; landval>0 → **32,491**; parval>0 → **32,556**; improvval>0 → **17,372**; ownname → **32,513**; saledatetx populated (saledate epoch null); **siteadd empty**
- **Notes:** Join `parno`=`PIN`. `sourceagnt`=Richmond County GIS. No sale price. Prefer county ParcelViewer for CAMA; OneMap solid geometry/owner/value fallback.

### 3. County Zoning — unincorporated PRIMARY

- **REST:** …/ParcelViewer/MapServer/14 (Shield twin: ParcelviewerShield/13)
- **Fields:** `Jurisdiction`, `DistrictCode`, `DistrictName` (**do not collect** `PhoneNumber`)
- **Verified:** count **69**; codes **A-R, C-C, C-R, H-C, H-I, L-I, R-R, V-R** (Jurisdiction mostly `Richmond County`)
- **Notes:** Spatial-join parcels outside City Limits. Not a substitute for municipal zoning inside Rockingham/Hamlet/etc.

### 4. Highway Commercial Overlay

- **REST:** …/ParcelViewer/MapServer/13 — count **10** (geometry overlay; thin attrs)

### 5. City Limits + City_ETJ — muni routing

- **City Limits:** …/MapServer/11 — count **14** (NAME: Rockingham, Hamlet, Ellerbe, Hoffman, Norman, Dobbins Heights; multi-part)
- **City_ETJ:** …/MapServer/25 — count **8** (`JURISDICTION` City of Rockingham / City of Hamlet)

### 6. AddressPoints — situs join

- **REST:** …/MapServer/3 — count **26,585**; `PARCELNUM` non-null → **25,644**
- **Join:** `PARCELNUM` = `PIN`; situs = `FullAddress` (+ `Post_Comm`/`Post_Code`/`Inc_Muni`)
- **Notes:** Layer also carries `PHONE` / `AREACODE` — **exclude** (no phones). Auth none.

### 7. FLU — gap (Strategic Land Use Plan PDF)

- https://www.richmondnc.com/DocumentCenter/View/6377 — Richmond County Strategic Land Use Plan, adopted **2022** (PDF verified)
- UDO: https://www.richmondnc.com/DocumentCenter/View/7580/RICHMOND-COUNTY-UDO
- No FLU FeatureServer on county Enterprise host

### 8. ParcelviewerShield — companion (no parcels layer)

- https://gis.richmondnc.com/server/rest/services/ParcelviewerShield/MapServer — CRS **102719/2264**; zoning/limits/addresses/overlays; **no Parcels layer** — use GISWebsite/ParcelViewer for CAMA

## PA / viewer deep-links (TRANCHE-3)

| Template | Key | Verified |
|----------|-----|----------|
| `https://gis.richmondnc.com/ITSPublic/AppraisalCard.aspx?id={PIN}` | PIN | **Yes** — PDF (`application/pdf`) with owner, situs, deed sale price/date, tax values |
| `https://gis.richmondnc.com/ITSPublic/TaxBillSearch/Parcel/{PIN}` | PIN | **Yes** — ParcelNumber input prefilled |
| https://gis.richmondnc.com/ITSPublic/RealEstateSearch | — | Search UI; ViewParcel is AJAX POST (no durable GET `/Parcel/{PIN}` — 404) |
| https://gis.richmondnc.com/maps/ | — | Jurisdiction GIS homepage |

NCPTS `lrcpwa.ncptscloud.com/richmond` returns **IsValidTenant=false** — do not wire as primary PA.

## Wire order (Land Search Builder)

1. **Parcels:** ParcelViewer/12 (3857) → fieldMap above; paginate 2000
2. **Acres filter:** `CalculatedAcres BETWEEN 5 AND 150` (or OneMap `gisacres`)
3. **Situs:** left-join AddressPoints on `PARCELNUM`=`PIN` (drop phone fields)
4. **Zoning:** if centroid in City Limits → **muni zoning gap** (flag jurisdiction); else spatial-join County Zoning/14 `DistrictCode`
5. **FLU:** PDF policy only — no polygon join
6. **PA / viewer:** AppraisalCard `{PIN}`; jurisdiction maps/
7. **Sale price QA:** AppraisalCard / deed line when REST price needed
8. **Join keys:** `PIN` ↔ OneMap `parno`

## Gaps

- Sale **price** not on public REST (SaleDate + AppraisalCard only)
- **Municipal zoning REST gap** for Rockingham, Hamlet, Ellerbe, Hoffman, Norman, Dobbins Heights (cities-first intent; county County Zoning for unincorp only)
- FLU PDF-only — no FeatureServer
- Parcel situs not on polygon layer — AddressPoints join required
- OneMap `siteadd` empty; `saledate` epoch null (use `saledatetx` / county SaleDate)
- Legacy `gis3.richmondnc.com` TLS unreliable from some networks
- NCPTS richmond tenant invalid
- RealEstateSearch durable GET `/Parcel/{PIN}` 404 (use AppraisalCard)
- Utilities / AADT / emails / phones / paid vendors excluded by design

## License / attribution

Richmond County GIS / Tax / Land Records; NC OneMap. NCGS 132-10 commercial resale limits on redistributed cadastral downloads. Attribute Richmond County GIS (+ NC OneMap where used).

verifiedAt: 2026-09-24  
verifiedBy: North Carolina Public Info Researcher
