# Onslow County, NC — GIS County Card

## Summary

Onslow County (Wilmington MSA, FIPS **37133**) publishes public ArcGIS REST at `maps.onslowcountync.gov` (alias `gismaps.onslowcountync.gov`): countywide **tax parcel polygons + CAMA** (`WEB_PUBLICATIONS/County_Map_Layers` layer **0**, ~**96,840**) with owner, mailing, situs, `GISACRES`, last sale (`SALEDATE`/`SALEPRICE`), tax values (`TAXMARKETVALUE`, land/bldg, deferred), and CAMA `ZONING`. ~**6,770** polygons have `GISACRES` 5–150 (~**3,464** with `FINALFULLBUILDINGVALUE=0` in that range). **Zoning is cities-first**: Jacksonville has a dedicated UDO polygon layer; Holly Ridge, Swansboro, North Topsail Beach, Richlands, and Surf City districts live on the county **County Zoning** polygons (`DATA` = town name). **FLU**: detailed county Future Land Use (~3,336) plus Horizon 2040 broad categories (11). **NC OneMap** (`cntyfips='133'`) fallback ~**95,297** / ~**6,765** in 5–150 (no sale price). Prefer most-local zoning joined onto county parcels.

## Portals

- **Onslow County GIS** — https://www.onslowcountync.gov/148/GIS
- **Public GIS viewer** — https://gismaps.onslowcountync.gov/maps/
- **Planning Maps (Zoning / FLU)** — https://www.onslowcountync.gov/1109/Maps
- **ArcGIS REST** — https://maps.onslowcountync.gov/arcgis/rest/services — Primary
- **gismaps alias** — https://gismaps.onslowcountync.gov/arcgis/rest/services
- **Tax / PA Basic Search (ITSPublicON)** — https://tax.onslowcountync.gov/ITSPublicON
- **Tax bill deep-link** — `https://tax.onslowcountync.gov/ITSPublicON/TaxBillSearch/Parcel/{PARID}`
- **Tax Administration** — https://www.onslowcountync.gov/165/Tax-Administration
- **Jacksonville Online Mapping (UI)** — https://jacksonvillenc.gov/379/Online-Mapping-Program
- **NC OneMap** — https://www.nconemap.gov — Statewide parcels (`services.nconemap.gov` / `services.gis.nc.gov`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`; `PARID` (tax account); OneMap `parno` | PIN ~12-digit; PARID for ITSPublicON |
| polygons | Yes | County_Map_Layers/0 | CRS **102719 / 2264** |
| acreage | Yes | `GISACRES` (prefer); `LEGALACRES`/`ADJACRES` | ~**6,770** GISACRES 5–150 |
| ownerName | Yes | `OWNER1` / `OWNER2`; OneMap `ownname` | Public on REST — do not scrape phones/emails |
| mailing address | Yes | `ADDRLINE1–3` + `MAILCITY`/`MAILSTATE`/`MAILZIP` | |
| situs address | Yes | `PHYSICALADDRESS` / `ADRNO`+`ADRSTR` + `PHYSICALCITY`/`ZIP` | |
| lastSale date/price | Yes | `SALEDATE`, `SALEPRICE`, `SALECODE` | Last sale; SALECODE e.g. Unqualified |
| tax values | Yes | `TAXMARKETVALUE`, `FINALFULLLANDVALUE`, `FINALFULLBUILDINGVALUE`, `TOTALTAXABLEVALUE`, `DEFERREDVALUE` | Also MUNIS* mirrors |
| zoning | Yes (split) | Polygon `ZONECODE` + Jax `UDO_Zone`; CAMA `ZONING` stub | Route by `CITY` / zoning `DATA` |
| flu | Yes | Future Land Use `DISTRICT`; Horizon 2040 `Category` | Prefer /20 for parcel join |
| appraiser / viewer link | Yes | ITSPublicON search + TaxBillSearch/{PARID}; GIS viewer | See templates below |

### CITY codes (parcel attribute → zoning router)

| CITY | Approx parcels | Zoning source |
|------|----------------|---------------|
| UNINCORPORATED ONSLOW | 68,399 | County Zoning (`DATA` COUNTY/PHASE I–VII) |
| JACKSONVILLE | 16,099 | **City of Jacksonville** UDO layer (city-first) |
| NORTH TOPSAIL BEACH | 4,099 | County Zoning `DATA=NORTH TOPSAIL BEACH` |
| HOLLY RIDGE | 3,422 | County Zoning `DATA=HOLLY RIDGE` |
| SWANSBORO | 2,316 | County Zoning `DATA=SWANSBORO` |
| RICHLANDS | 1,301 | County Zoning `DATA=RICHLANDS` |
| SURF CITY | 909 | County Zoning `DATA=SURF CITY` (also Pender) |

City Limits layer confirms the same six municipalities.

## Layers (verified 2026-09-24)

### 1. Parcels - Full Data — PRIMARY geometry + CAMA

- **Purpose:** parcels | acreage | ownership | situs | sales | tax | zoning (attribute)
- **REST URL:** https://maps.onslowcountync.gov/arcgis/rest/services/WEB_PUBLICATIONS/County_Map_Layers/MapServer/0
- **Mirrors:** EnerGov/Parcels/MapServer/10; GISWebsite/GISWebsiteLayers/MapServer/7 (same ~96,840)
- **Geometry:** Polygon | **WKID:** 102719 / 2264 | **MaxRecordCount:** 2000
- **Key fields → targets:** `PIN`→parcelId; `PARID`→parcelIdAccount; `GISACRES`→acreage; `OWNER1`→ownerName; `ADDRLINE*`+`MAIL*`→mailing; `PHYSICALADDRESS`/`PHYSICALCITY`→situs; `SALEDATE`/`SALEPRICE`→lastSale; `TAXMARKETVALUE`/`FINALFULLLANDVALUE`/`FINALFULLBUILDINGVALUE`/`TOTALTAXABLEVALUE`/`DEFERREDVALUE`→tax; `ZONING`→zoning stub; `CITY`→municipality router
- **Verified:** count **96,840**; GISACRES 5–150 → **6,770**; SALEPRICE>0 → **61,975**; TAXMARKETVALUE>0 → **95,818**; geo sample PIN `542001284955` ≈ **-77.258, 34.861** (Onslow)
- **Notes:** Full CAMA on polygon — no separate IASTAX join required. Prefer over OneMap for sale price.

### 2. NC OneMap Parcels — statewide fallback

- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='133'`
- **Verified:** count **95,297**; gisacres 5–150 → **6,765**
- **Notes:** Owner/mail/site/tax present; **no sale price**. May lag county.

### 3. County Zoning (County & Towns)

- **REST URL:** https://maps.onslowcountync.gov/arcgis/rest/services/WEB_PUBLICATIONS/County_Map_Layers/MapServer/3
- **Also:** EnerGov/Parcels/16; GISWebsite/32 (count 1563 — prefer WEB_PUB/3 at **1792**)
- **Fields:** `ZONECODE`→zoning; `DATA`→jurisdiction; `URL`
- **Verified:** count **1,792**; jurisdictions include COUNTY/PHASE I–VII + all six towns + JACKSONVILLE + CAMP LEJEUNE
- **Join:** spatial in 2264; inside Jacksonville prefer city UDO layer

### 4. Zoning (City of Jacksonville) — city-first

- **REST URL:** https://maps.onslowcountync.gov/arcgis/rest/services/GISWebsite/GISWebsiteLayers/MapServer/33
- **Fields:** `UDO_Zone`→zoning; `HTE_CODE` (legacy); `ORDINANCE`
- **Verified:** count **1,147**; ~76 distinct UDO/HTE pairs
- **Notes:** `supportsAdvancedQueries: false` — query carefully. Most local inside city limits.

### 5. Future Land Use — county detailed (PRIMARY FLU)

- **REST URL:** https://maps.onslowcountync.gov/arcgis/rest/services/WEB_PUBLICATIONS/County_Map_Layers/MapServer/20
- **Fields:** `DISTRICT`→flu; `District_FullName`; `ACRES`
- **Verified:** count **3,336**; districts A/F, AWCAC, CG, CGAC, Conservation, HDR, Industrial, LCAC, MDR, Military, RR, Non Participating, plus HOLLY RIDGE / RICHLANDS placeholders
- **Notes:** Prefer over Horizon 2040 for parcel joins

### 6. Horizon 2040 Future Land Use — broad policy

- **REST URL:** https://maps.onslowcountync.gov/arcgis/rest/services/GISWebsite/GISWebsiteLayers/MapServer/34
- **Fields:** `Category`→flu
- **Verified:** count **11** (Urban Growth, Conservation Lands, Economic Development, Municipality, …)
- **Status:** partial (not parcel-grain)

### 7. City Limits / PlanningJurisdiction

- **City Limits:** GISWebsite/66 (also WEB_PUB/9, EnerGov/18) — 6 munis
- **PlanningJurisdiction:** EnerGov/25 — town + ETJ labels (Holly Ridge ETJ, Richlands ETJ, Swansboro ETJ, …)

### 8. NTB-only parcels subset

- **REST URL:** County_Map_Layers/MapServer/24 — count **4,099** (optional filter extract)

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Public GIS viewer | https://gismaps.onslowcountync.gov/maps/ |
| PA Basic Search | https://tax.onslowcountync.gov/ITSPublicON |
| Tax bill by parcel | `https://tax.onslowcountync.gov/ITSPublicON/TaxBillSearch/Parcel/{PARID}` (PIN also accepted) |

Search modes on ITSPublicON: Property Owner Name, Parcel Id (`PARID`), Property Address, Alternate Parcel ID. **No public GET AppraisalCard/Datalet** verified (aspx → 500/404); `BasicSearch/ViewParcel` is **POST-only** after grid click (`parcelNumber`+`taxYear`).

## Gaps

- Jacksonville city FLU FeatureServer gap (use county FLU / Horizon 2040)
- Town FLU beyond county placeholders (Holly Ridge / Richlands labels) not published as separate FS
- Surf City dual-county (Onslow + Pender)
- Camp Lejeune / military largely non-participating
- OneMap lacks sale price
- Utilities and AADT intentionally out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **Live checks:** county parcel/zoning/FLU counts + OneMap `cntyfips='133'` + sample WGS84 centroid in Onslow + ITSPublicON TaxBillSearch GET + GIS viewer 200

## PASS2 — full-suite upgrade (rural OZ) · verifiedAt 2026-09-28

_Added by North Carolina Public Info Researcher. Existing sections above (incl. cities-first municipality routing) unchanged._

### 1. AADT / screening
- NCDOT_AADT_Stations FS/0, `COUNTY='ONSLOW'`, field `AADT_2022` (string) — **423 stations live**, 232 with a non-blank 2022 count.
- Count: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27ONSLOW%27&returnCountOnly=true&f=json`
- Features: `https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27ONSLOW%27&outFields=LocationID%2CROUTE%2CLOCATION%2CAADT_2021%2CAADT_2022&outSR=4326&f=geojson&resultOffset=0&resultRecordCount=1000`
- **Newer year:** NCDOT_2025_AADTandTrafficSegments_gdb FS/1, `County='Onslow'`, `AADT_2025` (int) — 426 stations; 205 with 2025, 275 with 2024. Segments FS/0 has 2025 AADT + AADTT. 2024 stations svc also public.

### 2. Tax values
- Layer `https://maps.onslowcountync.gov/arcgis/rest/services/WEB_PUBLICATIONS/County_Map_Layers/MapServer/0` — total 96843, 5–150 ac 6771 (`GISACRES>=5 AND GISACRES<=150`).
- Non-zero county: `FINALFULLLANDVALUE` 93576, `FINALFULLBUILDINGVALUE` 76784, `TAXMARKETVALUE` 95821, `TOTALTAXABLEVALUE` 95823; in 5–150: `TOTALTAXABLEVALUE` 6748. **Status: ok.**
- Double fields; TAXMARKETVALUE market, TOTALTAXABLEVALUE taxable.

### 3. Sale history
- Price `SALEPRICE`>0 61965 (5–150: 2662); date non-null `SALEDATE` 96527. **Status: ok.**
- SALEDATE STRING DD-MON-YY (e.g. 28-FEB-25); SALEPRICE double; SALECODE qualified code.

### 4. Owner entity
- Owner fields: `OWNER1`, `OWNER2`. Rule: uppercase/trim, flag if matches regex `(?i)(\bL\.?\s?L\.?\s?C\b|\bINC\b|\bCORP|\bL\.?\s?P\b|\bLLP\b|\bLLLP\b|\bLTD\b|TRUST|CHURCH|MINISTR|\bCOMPANY\b|PARTNERSHIP|PRTNRSHP|HOLDINGS|PROPERTIES|INVESTMENT|ASSOCIATION|\bHOA\b|FOUNDATION|AUTHORITY|\bDEVELOPMENT|BOARD OF EDUCATION|^(CITY|COUNTY|STATE|TOWN|VILLAGE) OF\b|^UNITED STATES|^NORTH CAROLINA\b|\bCOUNTY$)`.
- **Live entity-pattern parcels 5–150 ac: 1589** (of 6771 with owner). Server-side SQL = range AND OR-list of LIKE tokens (see YAML `pass2.ownerEntity.sqlLikeTokens`).
- Caveats: TRUST/TRUSTEE also flags family/revocable living trusts (still non-individual title holders); "% COUNTY" suffix catches e.g. "PERSON COUNTY"; bare "CO" and "ESTATE" intentionally excluded (too many false positives). Some owner strings carry trailing spaces (Wake) or mixed case (Yadkin) — normalize first.

### 5. PA deep link
- Template: `https://tax.onslowcountync.gov/ITSPublicON/TaxBillSearch/Parcel/{PARID}`
- Tested `https://tax.onslowcountync.gov/ITSPublicON/TaxBillSearch/Parcel/036798` → **200**. HTTP 200; PARID present in server HTML.

### 6. Jurisdiction GIS viewer
- `https://gismaps.onslowcountync.gov/maps/` → **200**. Onslow County GIS map viewer

### Pass2 gaps
- AADT_2022 blank at 191 of 423 stations on the 2022 layer (NCDOT counts on a cycle) — prefer 2025 layer / latest non-blank year
- No multi-transfer sale history on primary layer (last sale only)
