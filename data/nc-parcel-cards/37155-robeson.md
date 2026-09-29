# Robeson County, NC — GIS County Card

## Summary

Robeson County (Fayetteville MSA shed, FIPS **37155**, slug **robeson**, `cntyfips='155'`) publishes **ROKMAPS** jurisdiction GIS plus a county **AGOL** CAMA FeatureServer. **Wire-first parcels:** **AGOL Robeson_County_Parcels** FS/0 — ~**76,928** polys with owner, mailing, situs, acres (`MAPACRE`), land/imp assessed values, and `DATESOLD` (no sale-price field). **Cities-first zoning** on ROKMAPS `ZONE_CODE` prefixes (**Lmbr** Lumberton, **Pmbr** Pembroke, **Rdsp** Red Springs, **Frmt** Fairmont, **Mxtn** Maxton, **Stpl** St. Pauls, **Rlnd** Rowland, **Prkt** Parkton, **Lbrg** Lumber Bridge, plus **Cnty*** county districts) — ~**1,148** polys. **FLU:** Comprehensive Plan **PDF only**. **PA deep-link:** `https://www.ustaxdata.com/nc/robeson/account.cfm?parcelID={MAPNO}`. **Jurisdiction GIS:** https://maps2.roktech.net/ROKMAPS_Robeson/. Markets: **[Fayetteville]**.

## Portals

- **Jurisdiction GIS (ROKMAPS)** — https://maps2.roktech.net/ROKMAPS_Robeson/
- **ROKMAPS deep-link** — `https://maps2.roktech.net/ROKMAPS_Robeson/?mapno={MAPNO}`
- **County ArcGIS REST (Roktech)** — https://arcgis4.roktech.net/arcgis/rest/services/robeson/ROKMAPS_v2/MapServer
- **County AGOL parcels** — https://services7.arcgis.com/miWUVbMhSUq6a8y1/arcgis/rest/services/Robeson_County_Parcels/FeatureServer/0
- **County AGOL zoning** — https://services7.arcgis.com/miWUVbMhSUq6a8y1/arcgis/rest/services/Robeson_County_Zoning/FeatureServer/0
- **Property search (ustaxdata)** — https://www.ustaxdata.com/nc/robeson/robesonsearch.cfm
- **PA deep-link** — `https://www.ustaxdata.com/nc/robeson/account.cfm?parcelID={MAPNO}`
- **Tax bill search** — https://www.ustaxdata.com/nc/robeson/robesontaxSearch.cfm
- **NCPTS parcel search** — https://lrcpwa.ncptscloud.com/robeson/parcel-search
- **NCPTS deep-link** — `https://lrcpwa.ncptscloud.com/robeson/parcel-detail/{PIN_NUMBER}`
- **Tax Office** — https://www.robesoncountync.gov/tax
- **Community Development / Planning** — https://www.robesoncountync.gov/communitydev
- **Comprehensive Plan (FLU PDF)** — https://www.robesoncountync.gov/_files/ugd/269399_9170f96cf6d04acd883408c282a990a9.pdf
- **Ordinances** — https://www.robesoncountync.gov/ordinances
- **Online services** — https://www.robesoncountync.gov/online-services
- **Register of Deeds** — http://robeson.bislandrecords.com/
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='155'`)
- **Lumberton Planning** — https://www.lumbertonnc.gov/197/Planning-Neighborhood-Services

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | AGOL `PIN_NUMBER`; `MAPNO`; OneMap `parno`/`altparno` | Prefer **PIN**; PA uses **MAPNO** |
| polygons | Yes | AGOL FS/0; RokMaps/15; OneMap | AGOL CAMA; RokMaps/OneMap fresher count |
| acreage | Yes | `MAPACRE` / `DEEDACRE`; OneMap `recareano` | Do **not** use OneMap `gisacres` |
| ownerName | Yes | `OWNAM1`; OneMap `ownname` | Public — no phones/emails collected |
| mailing address | Yes | `OWADR*`/`OWCITY`/`OWZIP`; OneMap `mailadd`… | |
| situs address | Yes | `PHYSTRADR` / ST*; OneMap `siteadd`; Address pts | |
| lastSale date/price | Partial | `DATESOLD` (date); price HTML only | **Sale price REST gap** |
| tax values | Yes | `LNDASVCUR`+`IMPASVCUR`; OneMap `landval`/`improvval`/`parval` | Market ≈ land+imp |
| zoning | Yes (cities-first) | RokMaps `ZONE_CODE` prefixes | County + munis on one layer |
| flu | Gap | Comprehensive Plan PDF | No FeatureServer |
| appraiser / viewer link | Yes | ustaxdata `{MAPNO}`; ROKMAPS `?mapno=`; NCPTS `{PIN}` | TRANCHE-3 |

### CITYCODE → municipality (AGOL parcels)

| CITYCODE | Municipality | Approx parcels | Zoning prefix |
|----------|--------------|----------------|---------------|
| *(blank)* | Unincorporated | 68,593 | `Cnty*` / null |
| LUMB | **Lumberton** | 2,902 | `Lmbr*` |
| PEMB | **Pembroke** | 1,249 | `Pmbr*` |
| MAXT | **Maxton** | 973 | `Mxtn*` |
| FAIR | **Fairmont** | 738 | `Frmt*` |
| STPL | **St. Pauls** | 564 | `Stpl*` |
| ROWL | **Rowland** | 542 | `Rlnd*` |
| REDS | **Red Springs** | 456 | `Rdsp*` |
| SHAN | Shannon | 312 | (no prefix) |
| ORRM | Orrum | 215 | `Orrm*` stub |
| PARK | **Parkton** | 203 | `Prkt*` |
| LBRG | **Lumber Bridge** | 144 | `Lbrg*` |
| RENN | Rennert | 26 | (limits only) |
| PROC | Proctorville | 9 | `Prtv*` stub |
| MARE | Marietta | 2 | (limits only) |

### Zoning inventory (ROKMAPS/9 verified)

| Prefix / scope | Approx polys | Notes |
|----------------|--------------|-------|
| Lmbr* (Lumberton) | **405** | City-first PRIMARY |
| Cnty* (county) | **274** | County districts C1/H1/I2/R1/R2/RA/OS |
| (null ZONE_CODE) | **188** | |
| Frmt* (Fairmont) | **67** | |
| Pmbr* (Pembroke) | **63** | |
| Stpl* (St. Pauls) | **49** | |
| Mxtn* (Maxton) | **42** | |
| Rdsp* (Red Springs) | **23** | |
| Rlnd* (Rowland) | **22** | |
| Prkt* / Lbrg* / stubs | **~13** | Parkton, Lumber Bridge, Orrum, Proctorville |

## Layers (verified 2026-09-24)

### 1. AGOL Robeson_County_Parcels — PRIMARY CAMA

- **REST:** https://services7.arcgis.com/miWUVbMhSUq6a8y1/arcgis/rest/services/Robeson_County_Parcels/FeatureServer/0
- **Key fields:** `PIN_NUMBER`, `MAPNO`, `OWNERID`, `OWNAM1`, mail/site, `MAPACRE`/`DEEDACRE`, `LNDASVCUR`/`IMPASVCUR`, `DATESOLD`, deed refs, `CITYCODE`
- **Verified:** count **76,928**; MAPACRE 5–150 → **14,307**; LNDASVCUR>0 **76,887**; IMPASVCUR>0 **45,376**; vacant-ish in band **8,282**
- **Notes:** No `SALEAMT`. CRS **102100/3857**. MaxRecordCount **1000**.

### 2. ROKMAPS_v2 /15 Parcels — geometry twin

- **REST:** https://arcgis4.roktech.net/arcgis/rest/services/robeson/ROKMAPS_v2/MapServer/15
- **Verified:** count **80,343**; DEEDEDACRES 5–150 → **13,616**
- **Notes:** CAMA attrs **NULL** on public MapServer — geometry only. Prefer AGOL for attributes.

### 3. NC OneMap Parcels — statewide fallback

- **REST:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='155'`
- **Verified:** count **80,391**; recareano 5–150 → **13,122**; Shape__Area 5–150 → **12,749**; landval/parval>0 **78,345**
- **Notes:** `gisacres` broken. No saledate. Join `parno`=`PIN_NUMBER`; `altparno`=`MAPNO`.

### 4. ROKMAPS Zoning /9 — cities-first PRIMARY

- **REST:** …/ROKMAPS_v2/MapServer/9 — `ZONE_CODE`; count **1,148**

### 5. AGOL Zoning /0 — mirror

- Count **720** — prefer RokMaps/9

### 6. Zoning ETJ /10

- Count **7** (`ZONINGCODE=ETJ`)

### 7. City Limits /1 + Address Points /30

- Limits **85**; Addresses **75,105**

### 8. FLU — gap (Comprehensive Plan PDF)

- https://www.robesoncountync.gov/_files/ugd/269399_9170f96cf6d04acd883408c282a990a9.pdf

## Appraiser / PA deep-links (TRANCHE-3)

| Use | URL |
|-----|-----|
| Jurisdiction GIS viewer | https://maps2.roktech.net/ROKMAPS_Robeson/ |
| GIS by map number | `https://maps2.roktech.net/ROKMAPS_Robeson/?mapno={MAPNO}` |
| Property account (PA) | `https://www.ustaxdata.com/nc/robeson/account.cfm?parcelID={MAPNO}` |
| Account + owner | `https://www.ustaxdata.com/nc/robeson/account.cfm?ownerID={OWNERID}&parcelID={MAPNO}&groupParcel=` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/robeson/parcel-detail/{PIN_NUMBER}` |
| Real property search | https://www.ustaxdata.com/nc/robeson/robesonsearch.cfm |

Example: MAPNO `02200100703` → https://www.ustaxdata.com/nc/robeson/account.cfm?parcelID=02200100703 (HTTP 200 Account Information verified).

## Gaps

- Sale **price** not on public ArcGIS REST — ustaxdata HTML only
- RokMaps/15 CAMA schema fields NULL publicly
- OneMap `gisacres` broken
- FLU FeatureServer gap (Comprehensive Plan PDF)
- AGOL count lags RokMaps/OneMap (~77k vs ~80k)
- Shannon / Rennert / McDonald / Raynham / Marietta thin zoning
- Orrum / Proctorville UNKNOWN stubs only
- Utilities / AADT / emails / phones / paid vendors out of scope

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **tranche:** 3 (tax/owner on AGOL+OneMap; sale date on DATESOLD; sale price HTML; PA `{MAPNO}`; jurisdiction GIS ROKMAPS; parcels + cities-first zoning; FLU PDF gap)
- **Live checks:** AGOL counts + geo centroids; RokMaps layer inventory + zoning prefix stats; OneMap `cntyfips='155'`; ustaxdata account.cfm 200; ROKMAPS/?mapno= 200; Comprehensive Plan PDF 200; portals 200
- **Excluded:** AADT, utilities, emails/phones, paid vendors
