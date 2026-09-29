# Bladen County, NC — GIS County Card

## Summary

Bladen County (Fayetteville / Wilmington shed, FIPS **37017**, slug **bladen**, `cntyfips='017'`) publishes public ArcGIS REST at `gis.bladenco.org`. **Wire-first parcels:** **BladenCounty/MapServer/1 TaxParcels** — ~**33,335** polygons with owner, mailing, situs street name, **`MapAcres`**, assessed/FMV tax (`TotalASVCu` / `TotalFMV_1`), and **`SalesAmoun`** + deed year/book/page. **Cities-first:** gate with **MunicipalBoundaries**/8 + parcel **`TaxDistric` TOWN OF *** (Elizabethtown, Bladenboro, White Lake, Clarkton, East Arcadia, Dublin, Tar Heel) — **no town zoning FeatureServers**; unincorporated use **County_Zoning**/2 (RA/CON/I/C/R multipolygons) + parcel `ZONING` attr. **FLU:** Future Land Use Plan **2014–2030 PDF only**. **PA:** ustaxdata `account.cfm?ownerID={OwnerId:07d}&parcelID={ParcelId:07d}&groupParcel={PIN}` (zero-pad required). **Jurisdiction GIS:** https://gis.bladenco.org/bladenmap/. Markets: **[Fayetteville, Wilmington]**.

## Portals

- **Jurisdiction GIS viewer (Avineon)** — https://gis.bladenco.org/bladenmap/
- **GIS deep-link (PIN)** — `https://gis.bladenco.org/bladenmap/?PIN={PIN}`
- **County GIS hub / maps** — https://gis.bladenco.org/ · https://gis.bladenco.org/maps/
- **County ArcGIS REST** — https://gis.bladenco.org/server/rest/services/BladenCounty/MapServer
- **County GIS Services page** — https://bladennc.govoffice3.com/?SEC=F9F2178F-3B79-4E70-AE2F-A58F58890D5C
- **PA / tax search (ustaxdata)** — https://bladen.ustaxdata.com/Search.cfm
- **PA deep-link** — `https://bladen.ustaxdata.com/account.cfm?ownerID={OwnerId:07d}&parcelID={ParcelId:07d}&groupParcel={PIN}`
- **Tax bill search** — https://bladen.ustaxdata.com/TaxSearch.cfm
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/bladen/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/bladen/parcel-detail/{PIN}`
- **Zoning ordinance (Municode)** — https://library.municode.com/nc/bladen_county/codes/code_of_ordinances
- **FLU Plan PDF (2014–2030)** — https://bladennc.govoffice3.com/vertical/sites/%7B3428E8B4-BA8D-4BCE-9B92-0A719CB4C4FB%7D/uploads/Combined_Document_-_7-25-14_-_Bladen_Co_Future_Land_Use_Plan_.pdf
- **Elizabethtown Planning** — https://elizabethtownnc.org/planning-development/
- **Bladenboro Planning** — https://bladenboronc.org/planning
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 — filter `cntyfips='017'`

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`; `PID`/`ParcelId`; OneMap `parno`/`altparno` | Prefer **PIN**; PA needs padded OwnerId+ParcelId |
| polygons | Yes | TaxParcels MS/1 | CRS **102719 / 2264** |
| acreage | Yes | `MapAcres` / `DeedAcres`; OneMap `recareano` | Do **not** use `calcacre` or OneMap `gisacres` |
| ownerName | Yes | `Name1` / `CurrOwnNam`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `OwnerAddre`/`OwnerCity`/`OwnerState`/`OwnerZip` | |
| situs address | Partial | `PhysicalSt` (+ Addresses/0) | `PhysStreet` often blank |
| lastSale date/price | Yes | `SalesAmoun` + `DeedYear`/`DeedBook`/`DeedPage` | OneMap year text only / no price |
| tax values | Yes | `TotalFMV_1` / `TotalASVCu` / land+imp splits | Prefer FMV for market total |
| zoning | Yes (cities-first gate) | County_Zoning; parcel `ZONING`; muni limits | Town FS gap — UNK inside towns |
| flu | Gap | FLU Plan PDF | No FeatureServer |
| appraiser / viewer link | Yes | ustaxdata padded IDs; bladenmap `?PIN=`; NCPTS | TRANCHE-3 |

### Cities-first municipality inventory

| Place | TownCode | TaxDistric parcels | Limits acres (approx) | Zoning source |
|-------|----------|--------------------|-----------------------|---------------|
| **Elizabethtown** | 0615 | **2,389** | ~2,817 | City-limits gate; town ordinance / planning — **no FS** |
| **Bladenboro** | 0603 | **1,233** | ~1,392 | Same — ETJ on MS/9 |
| **White Lake** | 0647 | **1,506** | ~1,732 | Same — ETJ |
| **Clarkton** | 0609 | **520** | ~808 | Same — ETJ |
| **East Arcadia** | — | **438** | ~1,414 | Limits only; no TownCode |
| **Dublin** | 0612 | **245** | ~284 | Limits only |
| **Tar Heel** | 0648 | **168** | ~132 | Limits only |
| Unincorporated | — | ~26,836 | — | **County_Zoning** RA/CON/I/C/R + parcel `ZONING` |

### County_Zoning district footprints (MS/2)

| ZONING | Approx acres | Role |
|--------|--------------|------|
| RA | **~502,078** | Residential Agricultural (primary unincorp) |
| CON | **~39,363** | Conservation |
| I | **~3,712** | Industrial |
| C | **~988** | Commercial |
| R | **~466** | Residential |

### Parcel ZONING attribute (MS/1)

| ZONING | Count |
|--------|-------|
| RA | **22,945** |
| UNK | **8,270** (mostly town TaxDistric) |
| R | **951** |
| (blank) | **901** |
| C | **180** |
| I | **55** |
| CON | **24** |

## Layers (verified 2026-09-24)

### 1. TaxParcels — parcels + ownership + tax + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | situs | zoning attr
- **REST URL:** https://gis.bladenco.org/server/rest/services/BladenCounty/MapServer/1
- **Key fields → targets:** `PIN`→parcelId; `PID`/`ParcelId`→account; `OwnerId`→PA; `Name1`/`CurrOwnNam`→owner; mail `Owner*`; situs `PhysicalSt`; `MapAcres`→acreage; `TotalFMV_1`/`TotalASVCu`→tax; `SalesAmoun`/`DeedYear`→sale; `ZONING`/`TaxDistric`
- **Verified:** count **33,335**; MapAcres 5–150 → **9,242**; SalesAmoun>0 → **4,138**; TotalFMV_1>0 → **29,667**
- **Notes:** Prefer MapAcres over calcacre. No FeatureServer twin.

### 2. NC OneMap Parcels — geometry + CAMA mirror

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='017'`
- **Verified:** count **34,161**; recareano 5–150 → **9,258**; gisacres **all 0**; saledate **null**
- **Join:** `parno`=`PIN`; `altparno`=`PID`

### 3. County_Zoning — unincorporated districts

- **REST URL:** https://gis.bladenco.org/server/rest/services/BladenCounty/MapServer/2
- **Verified:** **5** multipolygon districts (see table)

### 4. MunicipalBoundaries + ETJ — cities-first gate

- **Boundaries:** https://gis.bladenco.org/server/rest/services/BladenCounty/MapServer/8 — **7** munis
- **ETJ:** …/MapServer/9 — Elizabethtown, Bladenboro, White Lake, Clarkton

### 5. Addresses — situs enrich

- **REST URL:** https://gis.bladenco.org/server/rest/services/BladenCounty/MapServer/0 — **~23,799** points

### 6. FLU — gap (PDF)

- https://bladennc.govoffice3.com/vertical/sites/%7B3428E8B4-BA8D-4BCE-9B92-0A719CB4C4FB%7D/uploads/Combined_Document_-_7-25-14_-_Bladen_Co_Future_Land_Use_Plan_.pdf

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS viewer | https://gis.bladenco.org/bladenmap/ |
| GIS by PIN | `https://gis.bladenco.org/bladenmap/?PIN={PIN}` |
| Property account (PA) | `https://bladen.ustaxdata.com/account.cfm?ownerID={OwnerId:07d}&parcelID={ParcelId:07d}&groupParcel={PIN}` |
| Name search list | `https://bladen.ustaxdata.com/list.cfm?lastName={OWN_LAST}` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/bladen/parcel-detail/{PIN}` |
| County GIS hub | https://gis.bladenco.org/ |

Example: OwnerId `539346`, ParcelId `18189`, PIN `033900353470` → https://bladen.ustaxdata.com/account.cfm?ownerID=0539346&parcelID=0018189&groupParcel=033900353470 (HTTP 200 Account Information; sale history $26,000 verified).

## Gaps

- No municipal zoning FeatureServers (Elizabethtown et al.) — cities-first limits + ordinance only
- County_Zoning coarse (5 district multipolygons); town parcel ZONING mostly UNK
- FLU FeatureServer gap (2014–2030 PDF only)
- calcacre / OneMap gisacres broken
- OneMap no sale price / saledate null
- PhysStreet sparse — join Addresses
- ustaxdata requires 7-digit zero-padded OwnerId+ParcelId
- Legacy ConnectGIS timed out — use Avineon bladenmap
- Utilities / AADT intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **tranche:** 3 (tax/sale/owner on TaxParcels; PA padded OwnerId+ParcelId+PIN; jurisdictionGis bladenmap; parcels + County_Zoning + cities-first limits; FLU PDF gap)
- **Live checks:** TaxParcels counts + MapAcres/SalesAmoun/FMV; County_Zoning acres; MunicipalBoundaries+ETJ; OneMap `cntyfips='017'`; ustaxdata account.cfm 200 with sale history; bladenmap/FLU PDF/municode 200; ConnectGIS timeout
