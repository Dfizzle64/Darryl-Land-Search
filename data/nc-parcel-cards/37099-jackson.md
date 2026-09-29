# Jackson County, NC — GIS County Card

## Summary

Jackson County (Asheville MSA, FIPS **37099**, slug **jackson**, `cntyfips='099'`) publishes a strong public ArcGIS stack at `gis.jacksonnc.org`. **Wire-first parcels (TRANCHE-3):** **Tax_Admin/Parcels FeatureServer/0** — **41,438** polys with `PIN` / `No_Dash`, owner (`CurrentOwner1`/`CurrentOwner2`), mailing, situs (`PropAddr`), `AssessedAcres` (string — CAST for range), full tax split (`TotLandValue`/`TotBldgValue`/`TaxableValue`), **`SaleDate`/`SalePrice`**, and embedded **`Prc_Url`**. ~**6,754** with CAST acres 5–150; **22,006** with `SalePrice>0`. **Tax_Admin/Appraisal/0** twin adds **`MktValue`** + **`VldSale`**. **Zoning is cities-first:** Sylva, Dillsboro, Forest Hills, Webster (+ county Cullowhee / Cashiers / US-441 corridor districts). Prefer per-muni Planning FeatureServers; **Energov/OperationalLayers Zoning** (55) is the combined wire. **FLU:** Small Area Plan PDFs only (Cashiers / Cullowhee / US-441) — **no FLU FeatureServer**. **PA deep-link:** `https://gis.jacksonnc.org/PRC/PRC/{No_Dash}.pdf`. **Jurisdiction GIS:** https://gis.jacksonnc.org/rpv/. Markets: **[Asheville]**.

## Portals

- **Jurisdiction GIS (Real Property Viewer / RPV)** — https://gis.jacksonnc.org/rpv/
- **Experience Builder Property Viewer 2.0** — https://experience.arcgis.com/experience/dbad85f79dc0429d852bdd63c31aa2b9
- **County ArcGIS REST** — https://gis.jacksonnc.org/jcgis/rest/services
- **Open Data Hub** — https://data-jacksonnc.opendata.arcgis.com/
- **Land Records** — https://www.jacksonnc.org/336/Land-Records
- **Tax Administration** — https://www.jacksonnc.org/174/Tax-Administration
- **Planning** — https://www.jacksonnc.org/179/Planning
- **Ordinances & Maps** — https://www.jacksonnc.org/391/Ordinances-and-Maps
- **PRC / PA deep-link (preferred)** — `https://gis.jacksonnc.org/PRC/PRC/{No_Dash}.pdf` (strip hyphens from `PIN`)
- **NCPTS parcel detail** — `https://lrcpwa.ncptscloud.com/jackson/parcel-detail/{PIN}`
- **NCPTS search** — https://lrcpwa.ncptscloud.com/jackson/parcel-search
- **BT Taxpayer Portal** (mailing address change) — https://bttaxpayerportal.com/taxpayerportalja/
- **NC OneMap** — https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1 (`cntyfips='099'`)

## Target attribute coverage (Land Search Builder schema)

| Target | Present? | Best source field(s) | Notes |
|--------|----------|----------------------|-------|
| id / parcelId | Yes | `PIN`; `No_Dash`; OneMap `parno` | e.g. `7572-43-7478` ↔ PRC `7572437478` |
| polygons | Yes | Tax_Admin/Parcels FS/0; OpLayers/46 | CRS **102100 / 3857** (outSR 2264 OK) |
| acreage | Yes | `AssessedAcres` (string); OneMap `gisacres` | CAST for BETWEEN; ~**6,754** in 5–150 |
| ownerName | Yes | `CurrentOwner1`+`CurrentOwner2`; OneMap `ownname` | Public — no phones/emails |
| mailing address | Yes | `MailingAddress1`/`2`,`MailingCityState`,`MailingZip` | |
| situs address | Yes | `PropAddr`; OneMap `siteadd` | |
| lastSale date/price | Yes | `SaleDate`,`SalePrice`; Appraisal `VldSale` | ~**22,006** SalePrice>0; OneMap saledate weak |
| tax values | Yes | `TotLandValue`,`TotBldgValue`,`TaxableValue`; Appraisal `MktValue` | |
| zoning | Yes (cities-first + county districts) | Planning muni layers / Energov `Name` | Outside Cullowhee/Cashiers/441 largely **unzoned** |
| flu | Partial / PDF | Cashiers / Cullowhee / US-441 Small Area Plans | No FLU FeatureServer |
| appraiser / viewer link | Yes | PRC `{No_Dash}.pdf`; NCPTS `{PIN}`; RPV | TRANCHE-3 |

## Layers (verified 2026-09-24)

### 1. Tax_Admin/Parcels — parcels + ownership + tax + sale (PRIMARY)

- **Purpose:** parcels | tax | ownership | sales | situs
- **REST URL:** https://gis.jacksonnc.org/jcgis/rest/services/Tax_Admin/Parcels/FeatureServer/0
- **MapServer mirror:** https://gis.jacksonnc.org/jcgis/rest/services/Tax_Admin/Parcels/MapServer/0
- **OpLayers mirror:** https://gis.jacksonnc.org/jcgis/rest/services/OperationalLayers/MapServer/46
- **Layer name / id:** Parcels / 0
- **Geometry:** Polygon
- **Key fields → targets:**
  - `PIN` → parcelId (e.g. `7572-43-7478`)
  - `No_Dash` → parcelIdNoDash / PRC key
  - `CurrOwnerAcct` → parcelIdAccount
  - `AssessedAcres` → acreage (string — CAST AS FLOAT for filters)
  - `CurrentOwner1`, `CurrentOwner2` → ownerName
  - `MailingAddress1`, `MailingAddress2`, `MailingCityState`, `MailingZip` → mailing
  - `PropAddr`, `PropDesc` → situs / legal
  - `SaleDate`, `SalePrice` → lastSale
  - `TotLandValue`, `TotBldgValue`, `TaxableValue` → tax
  - `Prc_Url` → appraiser deep-link (full URL)
  - `Township`, `TownCode`, `NbrhdName`, `FireDist`, `TransferringRef`, `PlatRef` → other
- **WKID / CRS:** 102100 (latest 3857)
- **Verified:** yes — count **41,438**; `CAST(AssessedAcres AS FLOAT) BETWEEN 5 AND 150` → **6,754**; `SalePrice>0` → **22,006**; `TaxableValue>0` → **39,731**; sample `PIN=7572-43-7478` STUDDARD centroid ≈ **-83.10, 35.12** (Cashiers / Jackson); join OneMap `parno` OK; PRC PDF 200 for `7572437478`
- **Notes:** PRIMARY wire-first. MaxRecordCount **60000**. Auth **none**. Cached MapServer also Query-capable.

### 2. Tax_Admin/Appraisal — CAMA twin (market value + sale qualifier)

- **Purpose:** tax | ownership | sales
- **REST URL:** https://gis.jacksonnc.org/jcgis/rest/services/Tax_Admin/Appraisal/FeatureServer/0
- **Also:** Building View /1; Land View /2
- **Extra fields vs Parcels:** `MktValue`, `VldSale`, `SalesRatio`, `UseValCde`, `ZoneCode`/`ZoneDesc` (mostly empty), `TotDefValue`
- **Verified:** count **41,438**; `MktValue>0` → **40,747**; `VldSale LIKE 'Q%'` → **9,387**
- **Notes:** Prefer for market value / qualified-sale flag; Parcels for `Prc_Url` + geometry extract.

### 3. NC OneMap Parcels (polys) — statewide fallback

- **Purpose:** parcels | tax | ownership | sales (date)
- **REST URL:** https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Alternate:** https://services.gis.nc.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1
- **Filter:** `cntyfips='099'`
- **Key fields:** `parno`↔`PIN`, `ownname`, `mailadd`, `siteadd`, `gisacres`, `saledate`/`saledatetx`, `parval`/`landval`/`improvval`
- **Verified:** count **41,375**; `gisacres` 5–150 → **6,743**; join verified `parno='7572-43-7478'`
- **Notes:** Sale **price** absent / saledatetx often blank — prefer county `SalePrice`. MaxRecordCount **5000**.

### 4. Zoning — cities-first + county planning districts (PRIMARY routing)

Prefer discrete Planning FeatureServers for city-first routing; Energov/OpLayers Zoning (55) is the combined county+muni wire.

| Municipality / area | REST | Count | Jurisdiction field |
|---------------------|------|------:|--------------------|
| **Sylva** (seat) | Planning/Sylva_Zoning/FeatureServer/3 (+ overlays /1, limits /0) | **11** (+19 overlay) | Town of Sylva |
| **Dillsboro** | Planning/Dillsboro_Zoning/FeatureServer/0 | **9** | Town of Dillsboro |
| **Forest Hills** | Planning/Forest_Hills_Zoning_Districts/FeatureServer/0 | **8** | Town of Forest Hills |
| **Webster** | Planning/Webster_Zoning_Districts/FeatureServer/0 | **3** | Town of Webster (+ ETJ poly in Energov → 4) |
| **Cullowhee** (unincorp CPA) | Planning/Cullowhee_Zoning_District_Cached/FeatureServer/0 | **8** | County |
| **Cashiers** Commercial | Planning/Cashiers_Commercial_District/FeatureServer/0 | **2** | County |
| **US-441 Corridor** | Planning/US_441_Corridor/FeatureServer/0 | **11** | County |
| Combined wire | Energov/MapServer/6 ≡ OperationalLayers/MapServer/2 | **55** | Jurisdiction + ZoningArea + Name |
| ETJ | Planning/ETJ_Cropped/FeatureServer/0 | **3** | Forest Hills / Sylva / Webster |

- **Fields:** `Name` (district), `ZoningArea`, `Jurisdiction`
- **Join:** spatial join zoning → parcels; route by municipality / ETJ / ZoningArea
- **Notes:** Outside Cullowhee CPA, Cashiers CD, US-441 corridor, Scotts Creek WQPD, and municipal limits — **unincorporated Jackson is largely unzoned** on public REST (mountain-county pattern). Highlands tip appears in Cities_Poly but zoning is Macon-hosted.

### 5. Municipal Boundaries / Cities

- **GIS/Cities_Poly/FeatureServer/0:** https://gis.jacksonnc.org/jcgis/rest/services/GIS/Cities_Poly/FeatureServer/0 — **5** names: SYLVA, DILLSBORO, FOREST HILLS, WEBSTER, HIGHLANDS (tip)
- **OperationalLayers/8 Municipalities** — same set (multi-part polys)
- **ETJ_Cropped** — Forest Hills, Sylva, Webster

### 6. FLU — PDF / Small Area Plans only (no public FeatureServer)

- **Cashiers Small Area Plan (adopted 2019):** https://www.jacksonnc.org/DocumentCenter/View/628/Cashiers-Small-Area-Plan-Adopted-March-19-2019-PDF
- **Cashiers Area Zoning Map PDF:** https://www.jacksonnc.org/DocumentCenter/View/540/Cashiers-Area-Zoning-Map-PDF
- **Cullowhee Small Area Plan:** https://www.jacksonnc.org/DocumentCenter/View/635/Cullowhee-Small-Area-Plan-PDF
- **Cullowhee CPA Zoning Map PDF:** https://www.jacksonnc.org/DocumentCenter/View/548/Cullowhee-Community-Planning-Area-Zoning-Map-PDF
- **US-441 Small Area Plan (2008):** https://www.jacksonnc.org/DocumentCenter/View/1346/US-441-Small-Area-Plan-Adopted-04-21-2008-PDF
- **US-441 Gateway Corridor Zoning Map:** https://www.jacksonnc.org/DocumentCenter/View/711/US-441-Gateway-Corridor-Zoning-Map-PDF
- **Headwaters / District 4 Conservation Plan (2025):** https://www.jacksonnc.org/DocumentCenter/View/1556/Jackson-County-Headwaters-District-Conservation-Plan-2025
- **Notes:** No countywide FLU FeatureServer verified. Parcel use codes are existing-use CAMA — **not** future land use.

## Municipalities (city-first zoning)

| Municipality | Zoning source | Count | Own GIS REST? | FLU REST? | Notes |
|--------------|---------------|------:|:-------------:|:---------:|-------|
| **Sylva** | Planning/Sylva_Zoning/3 | 11 | No (county host) | No | County seat; overlays + ETJ |
| **Dillsboro** | Planning/Dillsboro_Zoning/0 | 9 | No | No | |
| **Forest Hills** | Planning/Forest_Hills_Zoning_Districts/0 | 8 | No | No | Village; ETJ polys |
| **Webster** | Planning/Webster_Zoning_Districts/0 | 3 | No | No | Energov includes Webster ETJ (4) |
| **Cullowhee** | Cullowhee_Zoning_District_Cached/0 | 8 | County CPA | SAP PDF | Unincorporated; WCU area |
| **Cashiers** | Cashiers_Commercial_District/0 | 2 | County CD | SAP PDF | Unincorporated commercial core |
| **US-441 corridor** | US_441_Corridor/0 | 11 | County | SAP PDF | Gateway / Cherokee approach |
| Highlands (tip) | *(none on Jackson REST)* | — | Macon | — | Cities_Poly only — zoning gap |
| Unincorporated (other) | Scotts Creek WQPD + sparse | — | County | No | **Largely unzoned** |

## Appraiser / PA deep-links (TRANCHE-3)

| Purpose | Template |
|---------|----------|
| Property Record Card PDF (preferred) | `https://gis.jacksonnc.org/PRC/PRC/{No_Dash}.pdf` |
| Encoding | Strip hyphens from `PIN` (`7572-43-7478` → `7572437478`); also field `Prc_Url` |
| NCPTS detail | `https://lrcpwa.ncptscloud.com/jackson/parcel-detail/{PIN}` |
| NCPTS search | https://lrcpwa.ncptscloud.com/jackson/parcel-search |
| Jurisdiction GIS | https://gis.jacksonnc.org/rpv/ |
| Experience Builder | https://experience.arcgis.com/experience/dbad85f79dc0429d852bdd63c31aa2b9 |

Verified PRC PDF for id `7572437478`: owner **STUDDARD, BOBBY J TRUSTEE**, PIN `7572-43-7478`, SalePrice **$350,000**, TaxableValue **$587,388**.

## Gaps / caveats

- **Countywide FLU REST gap** — Small Area Plan / zoning-map PDFs only for Cashiers, Cullowhee, US-441
- **Unincorporated zoning REST gap** outside Cullowhee CPA, Cashiers CD, US-441 corridor, and Scotts Creek WQPD — mountain-county unzoned pattern
- **Highlands tip** in Cities_Poly but no Jackson-hosted zoning (Macon County)
- `AssessedAcres` is **string** — use `CAST(AssessedAcres AS FLOAT)` for acreage filters
- OneMap saledatetx often blank; prefer county `SaleDate`/`SalePrice`
- Spatialest `/nc/jackson` **404** — not used
- BT Taxpayer Portal is address-change, not PRC deep-link
- DocumentCenter PDFs may 403 from some egress — URLs verified via Planning HTML
- Utilities / AADT / emails / phones / paid vendors intentionally excluded

## License / attribution

Jackson County GIS / Land Records / Tax Administration / Planning. Cadastral maps from recorded deeds/plats/public records; not survey quality; County disclaims warranties. Commercial resale subject to **NCGS 132-10**. Attribute Jackson County GIS (and Town of Sylva / Dillsboro / Forest Hills / Webster where municipal districts used).

## Verification

- **verifiedAt:** 2026-09-24
- **verifiedBy:** North Carolina Public Info Researcher
- **verifiedLayerCount:** 14+
- **tranche:** 3 (tax/sale/owner public on parcels; PA deep-link with parcel ID; jurisdiction GIS URL; parcels + zoning + FLU suite)
- Live `returnCountOnly` + sample attribute/geo queries against Tax_Admin Parcels/Appraisal, OperationalLayers, Energov Zoning, Planning Sylva/Dillsboro/Forest Hills/Webster/Cullowhee/Cashiers/US-441/ETJ, GIS Cities_Poly, NC OneMap `cntyfips='099'`; PRC PDF cross-check; RPV config; centroid geo-check in Jackson.


## PASS 2 full-suite upgrade (rural OZ), verified 2026-09-28

_Pass 2 block, added 2026-09-28 by North Carolina Public Info Researcher. The same content is under the `pass2` key in the .yaml and .json. Earlier sections, including the cities-first municipality sections, are unchanged._

- **Parcel layer:** https://gis.jacksonnc.org/jcgis/rest/services/Tax_Admin/Parcels/FeatureServer/0 · id `PIN` · live count **41,439** · 5–150 ac **6,754** (`CAST(AssessedAcres AS FLOAT) >= 5 AND CAST(AssessedAcres AS FLOAT) <= 150`)
- **AADT 2022 (baseline):** NCDOT_AADT_Stations/0 `COUNTY='JACKSON'` gives **269** stations (157 with AADT_2022). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query?where=COUNTY%3D%27JACKSON%27&outFields=LocationID%2CROUTE%2CLOCATION%2CCOUNTY%2CAADT_2022&returnGeometry=true&outSR=4326&f=json
- **AADT 2025 (newer, preferred):** NCDOT_2025_AADTandTrafficSegments_gdb/1 `County='Jackson'` gives **269** stations (181 with AADT_2025, 160 with AADT_2024; data edited 2026-09-23). Query: https://services.arcgis.com/NuWFvHYDMVmmxMeM/arcgis/rest/services/NCDOT_2025_AADTandTrafficSegments_gdb/FeatureServer/1/query?where=County%3D%27Jackson%27&outFields=LocationID%2CRouteID%2CLocated_On%2CCounty%2CAADT_2024%2CAADT_2025&returnGeometry=true&outSR=4326&f=json
- **Tax values (ok):** `TaxableValue` non-zero **39,730**, `TotLandValue` non-zero **40,676**
- **Sale history (ok):** price `SalePrice` >0 **22,013**; date `SaleDate` non-null **41,126**
- **Owner entity:** fields `CurrentOwner1`, `CurrentOwner2`. Rule: uppercase and trim the name, then regex `\b(LLC|L\.L\.C\.?|INC\.?|CORP(ORATION)?|LP|L\.P\.|LLP|LTD|TRUST|CHURCH|COMPANY|PARTNERSHIP|HOLDINGS|PROPERTIES)\b|^(CITY|COUNTY|STATE|TOWN) OF\b`. Live entity count on the 5–150 ac parcels is **1,879** (all parcels: 11,590), using the SQL approximation on `CurrentOwner1`.
- **PA deep link:** `https://gis.jacksonnc.org/PRC/PRC/{No_Dash}.pdf`. Tested `7650426623` → HTTP **200** (application/pdf), content verified: True. Owner and parcel id verified in the response.
- **Jurisdiction GIS viewer:** https://gis.jacksonnc.org/rpv/ → HTTP **200** (ArcGIS Web Application)
- **acreageNote:** The acreage field is a string, so filters need CAST(... AS FLOAT).
- **Pass 2 gaps:** none
