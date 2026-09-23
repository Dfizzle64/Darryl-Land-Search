# Darryl Land Search — Orlando shed + seven-market rural OZ 2.0

Interactive map for multifamily site selection across the **Orlando ~90-minute county shed** (Brevard, Lake, Marion, Orange, Osceola, Polk, Seminole, Sumter, Volusia), plus **seven-market rural-eligible OZ 2.0 tract overlays**. Filter parcels by acreage, land-use mode, Opportunity Zones, ACS income, and FDOT AADT where data exists. Ranked sites + parcel drawer show owner/LLC (when public), sale, tax, mailing, and appraiser links.

Public GIS only — no paid parcel vendors, no scraped emails or phones. Zoning/FLU/AADT richness is Orange County first; other shed counties degrade gracefully.

## Run locally

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Other scripts:

```bash
npm test             # acreage / zoning / FLU / OZ / scoring unit tests
npm run build        # production build
npm run seed         # parcels + income + AADT, then FLU join, then OZ join, then zoning coverage
npm run seed:flu     # re-join FLU onto the existing parcel fixture
npm run seed:oz      # designated QOZ polygons, then OZ 2.0 eligibility (Rev. Proc. 2026-14 + Notice 2025-50)
npm run seed:oz2     # refresh OZ 2.0 nomination tracts only (needs pypdf; see below)
npm run seed:oz2-markets  # seven-market rural-eligible tracts from the CSV + TIGER 2020
npm run seed:oz2-eligible # seven-market urban tracts + 15 other MSAs (rural and urban) + TIGER 2020
npm run seed:sc-mf        # South Carolina multifamily priority shortlist from its CSV
npm run seed:parcels:orlando  # full 5–150 acre parcels for Lake, Orange, Osceola, Polk, Seminole
npm run seed:parcels:markets  # 5–150 acre parcels for every other MSA (skips finished counties)
npm run seed:zoning  # refresh coverage report vs knowledge JSON (no LLM)
```

Orlando parcel architecture, county source URLs, and field mapping: [`docs/orlando-parcels.md`](docs/orlando-parcels.md) and [`data/orlando-parcel-sources.json`](data/orlando-parcel-sources.json).

Other MSAs use the same tile grid and the same zoom / area-lock / Show parcels gate. They load only while that market is selected. Refresh and the complete-vs-sample-vs-gap table: [`docs/market-parcels.md`](docs/market-parcels.md).

No API keys are required for the default fixture mode. Copy `.env.example` to `.env.local` only if you want to point at live feeds.

## What you can do

- Switch **Market** / **County** across seven Southeast sheds, or open **Other MSAs (15)** for the smaller markets. Primary markets stay listed first. Orlando loads multi-county parcel polygons. Each other market that already has a parcel extract loads only its own 5–150 acre tiles after you select it, and only at neighborhood zoom, an area lock, or Show parcels. Counties without an open polygon source stay on the tract overlay. Jacksonville loads 5–150 acre tiles for Duval, St. Johns, Clay, Nassau, and Baker from public county GIS, with city zoning where a public layer exists. Rural tracts are orange. Urban eligible tracts are blue. The legend toggles rural, urban, or both.
- Set a **minimum acreage**. The slider is 0–25 acres; larger sites still match any threshold at or below 25. Acreage is shown in the parcel drawer. Eligible tracts have no acreage field, so this slider does not hide tracts.
- Turn on **Consider zoning in parcels** (default No) to use a land-use mode: multifamily-capable zoning, all parcels, non-multifamily zoning, rezoning candidates (FLU yes / zoning no), FLU allows multifamily, either, or both. While the switch is No, those constraints are hidden and not applied.
- Turn on **Consider opportunity zone in parcels** (default No) to filter parcels by OZ 2.0 rural-eligible, OZ 2.0 eligible but not rural, in a current designated QOZ, not in a designated QOZ, or either. While the switch is No, those parcel constraints are hidden and not applied. The map toggles for the OZ 2.0 tract overlay (orange = rural-eligible, blue = urban eligible, amber = Orange County urban overlay) and the copper dashed designated-QOZ overlay stay available either way. Eligible is not designated.
- Include **planned development / PUD** (always labeled maybe — site-specific).
- Include **conditional zoning** (Live Local commercial/industrial, limited multiplex, some mixed-use overlays). Off by default so C-2 warehouses do not flood the map.
- Set a **minimum median household income** (tract or block group) and **minimum AADT**. Tract geography also hides eligible tracts whose joined Orange County ACS median income is below the minimum. Tracts outside that fixture have no AMI and stay visible while Include unknown income is on. Block group income, and AADT, apply to parcels only.
- Browse a **ranked sites** list (score 0–100) in the tract-details rail. It is collapsed until you expand it, and that choice is kept for the browser session. Click a row to open the drawer and fly the map.
- Open **Zoning knowledge** in the sidebar: jurisdictions covered, district explanations, citations, last-updated date. This is an offline JSON knowledge base, not a live model call.
- Switch the map between **Streets** (Esri World Street Map: roads, labels, and places — no API key), **Satellite hybrid** (Esri imagery plus road and city/place labels), and **Dark** (OpenFreeMap dark / Carto Dark Matter fallback). The toggle is a map control; parcel filters, selection, OZ overlay, and camera stay put. No API key is required. Set `NEXT_PUBLIC_MAPTILER_KEY` to use MapTiler Streets v2 and MapTiler Hybrid instead of the keyless tiles.
- **Measure** a polyline on any basemap. Each click adds a vertex; the readout lists every segment and the total in miles. Clear drops the line, Cancel (or Esc) leaves measure mode.
- **Lock an area of interest** on the Orlando parcel map: **Draw area** and drag a rectangle, or **Lock view** to use the current map bounds. Queries and the ranked list stay inside that boundary while you pan and zoom; **Clear** follows the viewport again. The outline and an “AOI locked” chip (approximate acreage and parcel count) stay on the map. County, market, the 5–150 acre band, Opportunity Zone overlays, and the South Carolina shortlist still apply.

Lake, Orange, Osceola, Polk, and Seminole load **every public parcel from 5.0 through 150.0 acres** from Florida DOH EHWATER (FDOR land square feet). Parcels under 5 or over 150 are excluded. Orange also joins OCPA zoning, sale, and tax when the parcel id matches, plus Orange County and Orlando future land use. The map requests the current viewport instead of shipping that whole extract in the page. Parcel outlines stay off below neighborhood zoom (about 10.5) so the shed is not a solid fill. The map says to zoom in, lock an area, or turn Show parcels on. Show parcels forces outlines on at any zoom; Hide parcels stays off until you turn them back on. Scroll, pinch, and +/- zoom the map. Draw area pauses dragging only while you trace a rectangle, then pan and zoom return. **Lock view** or **Draw area** freezes that query to a boundary so parcels do not swap in and out as the camera moves. Brevard, Marion, Sumter, and Volusia are still thinner samples. `data/fixtures/parcels.geojson` remains a separate 462-parcel Orange pilot with income and AADT, used by the legacy provider, not the Orlando shed map.

## How filters work

1. **Acreage.** OCPA parcel `ACREAGE`. Unknown acreage can be kept or dropped (the sample has acreage on every parcel).
2. **Zoning.** OCPA stores codes like `ORL-R-3B/T/AN`. The app parses the jurisdiction prefix (`ORL`) and base district (`R-3B`), then matches **that jurisdiction’s** districts in `data/zoning-config.json`. County `R-3` does not silently match Orlando `R-3A` unless Orlando lists it. Token `P-D` does **not** match Orlando public-use `P`.
3. **FLU.** Parcel centroids are joined to [Orange County Future Land Use](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21) and [Orlando Future Land Use](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83). `data/flu-config.json` decides which GIS codes are MF-supportive. Overlay suffixes such as `/RES-PRO` fall back to the base code.
4. **Opportunity Zones.** Designated QOZs use HUD/Treasury polygons (2010 Census tracts), not ACS 2020 tract IDs. OZ 2.0 uses 2020 census tracts from the Rev. Proc. 2026-14 appendix. Filters: rural-eligible, eligible but not rural, in a designated QOZ, not in a designated QOZ, or either. The OZ 2.0 overlay draws all 87 Orange County eligible tracts; the copper dashed overlay is the county’s 24 current QOZ tracts.
5. **Income.** ACS median household income (B19013) by tract or block group on parcels. The same tract minimum also filters eligible-tract overlays where that GEOID is in the Orange County ACS fixture. Acreage and AADT are not on tract features, so those sliders stay parcel-only.
6. **AADT.** Nearest FDOT Orange County count segment. Parcel-only.

Acreage, income, AADT, land use, and Opportunity Zone filters run in the parcel query before the viewport is thinned, then again on the loaded features so the map and ranked list stay in step. `/api/parcels?filter=1` is what the map calls (`minAcres`, `minIncome`, `minAadt`, `landUse`, `oz`, …). Orange County parcels in that response pick up ACS median income and the nearest FDOT AADT from the pilot fixtures. Other shed counties leave those fields unknown; uncheck “include unknown” to hide them. The map hides non-matches with a single `filterMatch` flag rather than a list of parcel ids.

### Land-use modes

The app is no longer MF-zoning-only. Modes:

| Mode | Keeps a parcel when |
| --- | --- |
| Multifamily-capable (default) | District is `permitted` in the knowledge base, or PD if that toggle is on, or conditional if that toggle is on |
| All parcels | Ignore zoning and FLU; still apply acreage, income, traffic, and OZ |
| Non-multifamily zoning | Current zoning is **not** MF-capable (zoning-only rezoning hunt). Missing/unknown districts count as not MF-capable |
| Rezoning candidates | Joined FLU supports multifamily / higher density **and** current zoning is not MF-capable. Missing FLU is **not** a candidate |
| FLU allows MF / higher density | Joined FLU category has `allowsMultifamily: true` |
| Either | Zoning match **or** FLU match |
| Both | Zoning match **and** FLU match |

FLU-only and rezoning modes do **not** treat missing FLU as a match. Other municipalities besides Orlando often have no joined FLU — that is an honest gap, not an empty county. The rezoning list shows a banner with the count of parcels that cannot be classified.

### Ranked site list

Matching parcels are scored 0–100 and listed (desktop overlay from the `xl` breakpoint; **Sites** sheet/button below that). Clicking a row selects the parcel, opens the drawer, and flies the map to the centroid.

**Formula.** `score = 100 × Σ (weightᵢ × componentᵢ)` with default weights:

| Component | Weight | What 1.0 means |
| --- | --- | --- |
| Acreage | 0.28 | At least ~8 acres above the active minimum (or 8 acres when there is no minimum) |
| Income | 0.22 | About $40k above the income minimum (or ~$80k when there is no minimum) |
| AADT | 0.18 | About 25k vehicles/day above the AADT minimum (or 15k when there is no minimum) |
| Zoning / FLU fit | 0.22 | Permitted MF + supportive FLU. Rezoning candidates (FLU yes, zoning no) get a high fit score so they surface in All-parcels mode |
| Opportunity Zone | 0.10 | Centroid in a **current designated** QOZ. Dropped (weights renormalized) when the OZ filter is **Not in designated Opportunity Zone**, because every remaining row would get a constant zero. OZ 2.0 nomination status is a filter, not a score |

Unknown acreage / income / AADT (when included) score 0.35 on that component. Ties break by acreage, then parcel id. This is a screen, not an appraisal.

Chips on each row are that component’s contribution to the 0–100 total (so they roughly sum to the score).

## Zoning knowledge base

Configured in `data/zoning-config.json` (edit that file; format is documented in `data/README.md`):

| Status | Meaning in the UI |
| --- | --- |
| Permitted | By-right / purpose-built multifamily (R-3, Orlando R-3A–D, Apopka RMF, …) |
| Conditional | Allowed with conditions — Live Local (F.S. § 125.01055) in some Orange County commercial/industrial districts, limited Orlando multiplex in O-1/O-2, some mixed-use overlays |
| Maybe — site-specific | PD, PUD, PURD, Bay Lake / LBV `MIXED`, Horizon West Village FLU |

Non-obvious inclusions (with citations in `why`):

- Unincorporated **R-2**: Sec. 38-77 lists multifamily as P, not only R-3.
- Unincorporated **C-1 / C-2 / C-3 / I-\***: Sec. 38-77 `24 P` plus Sec. 38-79(24) Live Local — **conditional toggle**, not default.
- Apopka **C-C / C-R / MU-ES-GT**: district purpose statements allow multifamily or MF over commercial.
- Orlando **AC-N through AC-3** and **MXD**: activity center / mixed-use including residential.

Ocoee Table 5-1 lists multi-family as P **only** in R-3. That city’s commercial districts are not treated as MF loopholes.

Belle Isle, Oakland, and Windermere are listed with **unverified** coverage and empty district lists. No industrial/commercial loopholes were invented.

PD/PUD is always “maybe — site-specific.” Confirm the regulating plan.

## Future Land Use

| Layer | What is joined |
| --- | --- |
| Orange County FLU (open data 21) | Unincorporated + annexed parcels still on county FLU. GIS codes `MD`/`HD`/`NR`/`NAC`/`NC`/`ACR`/`ACMU`/… |
| Orlando FLU (open data 83) | Preferred for `ORL` parcels. `RES-MED`, `RES-HIGH`, activity centers, mixed-use corridors, office-medium/high |
| Other cities | **Not joined.** County layer often returns placeholder `City`. Those parcels have `flu: null`. |

Product decisions:

- County **LDR** (4 du/ac) and Orlando **RES-LOW** (max 12 du/ac, neighborhood low-intensity) are **not** treated as MF-supportive FLU.
- County **LMDR** (10 du/ac) **is** treated as higher-density / small MF possible.
- County GIS does not have a separate **MHDR** code; plan text MHDR (35 du/ac) is noted in the MDR/HDR `why` fields.
- **Innovation Way (`IW`)** is maybe / plan-specific. **Lake Pickett (`LP`)** is not treated as MF-supportive.

The legacy Orange pilot file still has FLU joined on **375 / 462** parcels, including sites with MF-supportive FLU and non-MF zoning. The Orlando shed map uses the full 5–150 acre extract instead; its join counts are in `data/fixtures/orlando-parcels/meta.json`. Use land-use mode **Rezoning candidates**, **FLU allows multifamily / higher density**, or **Either** where FLU is joined.

## Opportunity Zones

Qualified Opportunity Zones are **2010 Census tracts** nominated by the state and certified by the U.S. Treasury (IRC §§ 1400Z-1 / 1400Z-2). They are **not** the same geography as ACS 2020 tracts used for income.

| Piece | Source |
| --- | --- |
| Overlay polygons | [HUD GIS Opportunity Zones](https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/FeatureServer/13) filtered to Florida `STATE='12'` and Orange County `COUNTY='095'` (24 tracts). Fallback: [Orange County Public_Dynamic / 61](https://ocgis4.ocfl.net/arcgis/rest/services/Public_Dynamic/MapServer/61) |
| Parcel flag | Centroid-in-polygon against those 2010 QOZ polygons (`npm run seed:oz`) |

The app runs offline from `data/fixtures/opportunity-zones.geojson` plus `opportunityZone` on each parcel. In this sample **26 / 462** parcels fall in a designated QOZ; the overlay still draws all 24 county tracts. The drawer shows yes/no, the 2010 tract GEOID when inside a zone, and whether Notice 2025-50 lists that designated tract as rural. None of Orange County’s 24 current QOZ tracts are on that rural list.

Product decisions:

- Join by geometry, never by ACS 2020 `incomeTract.geoid`.
- The designated overlay is off by default so it does not fight parcel fills; the Streets / Satellite hybrid / Dark toggle does not drop it.
- “Not in designated Opportunity Zone” requires a successful join that returned false, not a missing property.
- Rural on a **designated** zone is membership in the Notice 2025-50 appendix. The HUD `Rural` attribute is not the classifier.

## OZ 2.0 nomination eligibility

Rev. Proc. 2026-14 lists population census tracts that are low-income communities **eligible for nomination** as 2027 Qualified Opportunity Zones, including which of those tracts are comprised entirely of a rural area. Nomination is not designation. These tracts are not certified 2027 QOZs, and the UI does not call them designated.

| Piece | Source |
| --- | --- |
| Eligible tracts and Rural Status | [Rev. Proc. 2026-14 appendix](https://www.irs.gov/pub/irs-drop/rp-26-14-appendix.xlsx) (`State = Florida`, `County = Orange County`) |
| Tract polygons | Census TIGER 2020 tracts for those GEOIDs |
| Current designated rural flags | [Notice 2025-50](https://www.irs.gov/pub/irs-drop/n-25-50.pdf) appendix (3,309 GEOIDs). Orange County has none |

Orange County has **87** eligible tracts in that appendix. **One** is rural: GEOID `12095016605` (Census Tract 166.05, east Orange / Bithlo–Wedgefield, SR 50). The other 86 are `Non-rural`. The app does not run its own urban/rural classifier.

Offline files: `data/fixtures/oz2-eligible.geojson`, `oz2-eligible-tracts.json`, and `oz2Eligibility` on each parcel. In this sample **185 / 462** centroids fall in an eligible tract and **3 / 462** fall in `12095016605` (those three were appended from the public OCPA layer so the rural filter and drawer have something to open). The OZ 2.0 overlay is on by default. Orange is rural-eligible; amber is eligible and not rural. Designated QOZs use a copper fill and a dashed outline. Parcel fills stay green. Choosing the rural-eligible or non-rural filter narrows the overlay to that class.

The parcel drawer shows eligible / not eligible, the official rural flag, and the GEOID, and says the tract has not been nominated or certified. A rural-eligible parcel uses the status chip **Eligible (rural) — not designated**.

Clicking a census tract overlay shows the county and state with the GEOID, status, and rural flag. Eligible tracts (rural and urban) open the tract drawer, which labels county and state. Eligible tracts that are not rural, and current designated QOZ tracts, also open a map popup. County comes from the tract properties: the Orange eligible table for the OZ 2.0 overlay, Orange County (FIPS 12095) for the designated overlay, and the market pack for rural and urban tracts. That label is not a 2027 designation.

## Seven Southeast markets (rural and urban eligible)

The map can switch among **Atlanta, Tampa, Orlando, Charleston, Nashville, Charlotte, and Raleigh-Durham**. Each market loads eligible census tracts inside an approximate **90-minute county ring** of the city center. Rural tracts stay orange. Urban (non-rural) tracts are blue. A **Rural / Urban / Both** control filters the list and the overlay. The rural source table is `data/oz2-7markets-90min-rural-eligible.csv` (446 rows, 424 unique GEOIDs). The urban source table is `data/oz2-7markets-90min-urban-eligible.csv` (1,144 rows, 1,103 unique GEOIDs). Polk and Sumter, Florida are listed under **both** Tampa and Orlando; the county filter is state-aware (Charlotte’s Union is North Carolina, not South Carolina).

| Market | Rural rows | Urban rows |
| --- | ---: | ---: |
| Atlanta | 73 | 342 |
| Tampa | 66 | 251 |
| Orlando | 64 | 216 |
| Charleston | 49 | 30 |
| Nashville | 26 | 82 |
| Charlotte | 60 | 144 |
| Raleigh-Durham | 108 | 79 |

Urban status chips read **Eligible — not designated**. The rural chip stays **Eligible (rural) — not designated**. Neither chip is a designation. South Carolina notes that include the governor-filed sentence keep that soft copy; the tract is still not designated.

## Other metros

**Other MSAs (15)** in the market menu opens 15 smaller MSAs: Vero Beach, Melbourne, Jacksonville, Pensacola, Birmingham, Mobile, Huntsville, Savannah, Columbia, Greenville, Chattanooga, Knoxville, Memphis, Winston-Salem, and Wilmington. They are visually secondary to the seven. Each one has rural and urban eligible tracts from `data/oz2-other-msas-eligible.csv` (1,386 rows, 1,341 unique GEOIDs; 491 rural and 895 urban). County rings are in `data/oz2-other-msas-counties.md`. Each of these markets, including Jacksonville, loads 5–150 acre parcel tiles when that extract exists (`docs/market-parcels.md`). Jacksonville’s tiles are the public county parcel layers for Duval, St. Johns, Clay, Nassau, and Baker. City zoning replaces the county layer inside Jacksonville Beach, St. Augustine, St. Augustine Beach, Green Cove Springs, Fernandina Beach, Hilliard, and Callahan. Atlantic Beach, Neptune Beach, Baldwin, Orange Park, Keystone Heights, and Penney Farms have no public zoning REST and stay gaps.

| Market | Total | Rural | Urban |
| --- | ---: | ---: | ---: |
| Vero Beach | 62 | 25 | 37 |
| Melbourne | 175 | 24 | 151 |
| Jacksonville | 98 | 8 | 90 |
| Pensacola | 49 | 22 | 27 |
| Birmingham | 152 | 42 | 110 |
| Mobile | 66 | 15 | 51 |
| Huntsville | 58 | 31 | 27 |
| Savannah | 64 | 31 | 33 |
| Columbia | 105 | 62 | 43 |
| Greenville | 105 | 70 | 35 |
| Chattanooga | 47 | 21 | 26 |
| Knoxville | 70 | 41 | 29 |
| Memphis | 175 | 44 | 131 |
| Winston-Salem | 105 | 24 | 81 |
| Wilmington | 55 | 31 | 24 |

The status chip on this pack is **Eligible — not designated** for both rural and urban rows. Rural is still drawn orange and urban blue. Columbia, Greenville, and Savannah’s South Carolina fringe keep the governor-filed line where the notes say so. Alabama (Birmingham, Mobile, Huntsville, and Pensacola’s Baldwin spill) is new inventory. Memphis includes the Arkansas and Mississippi counties in the shed.

**90-minute sheds are approximate county rings, not drive-time isochrones.** A county is included when its main corridor is commonly within about 90 minutes off-peak. Outer-edge counties are flagged in the tract notes and in the county menu. County membership, exclusions, and sources for the seven are in `data/oz2-7markets-90min-counties.md`. The smaller MSAs are in `data/oz2-other-msas-counties.md`.

Every tract in the rural pack is **Eligible (rural) — not designated**. The chip uses that phrase. Florida, Georgia, Tennessee, and North Carolina had no public certified 2027 QOZ lists when the table was built (Sep 21, 2026). Do not read the orange overlay as a certified Opportunity Zone. Urban and other-MSA tracts use **Eligible — not designated** and are not certified either.

South Carolina is the exception on wording only. [SC Commerce](https://www.sccommerce.com/opportunity-zone) says Governor McMaster submitted OZ 2.0 nominations to Treasury on September 10, 2026. The page does not publish a GEOID list (the “list can be found here” sentence is not a link), and the ArcGIS map still describes eligibility. Charleston, and Charlotte’s South Carolina fringe (York, Lancaster, and Chester), therefore show a second line: **Governor-filed — list not public yet / not designated**. The chip and filters stay eligible / not designated. No tract is marked nominated or certified.

### South Carolina multifamily priority shortlist

Charleston and Charlotte can filter the rural layer to a **22-tract** multifamily shortlist (10 Tier A, 12 Tier B) sourced from `data/sc-oz2-mf-priority-shortlist.csv`. The research note is `data/sc-oz2-mf-priority-shortlist.md`. Buttons in the tract list and sidebar: **All rural**, **SC MF priority**, **Tier A**, **Tier B**.

Tier A is a gold outline and pin. Tier B is blue. Both sit on top of the orange rural-eligible fill. The drawer shows the corridor label, tier, multifamily rationale, acreage realism, and notes. Nom-watch in those notes is an inference, not a confirmed nomination. The status chip stays **Eligible (rural) — not designated**, with the governor-filed line. This shortlist does not change Atlanta, Tampa, Orlando, Nashville, Raleigh-Durham, or the Orange County parcel pilot.

Choose **Orlando** for shed parcels. Lake, Orange, Osceola, Polk, and Seminole are the complete 5–150 acre extracts. Orange still has the amber non-rural eligible tracts, the designated QOZ overlay, and green parcel fills. GEOID `12095016605` is still the only Orange County rural-eligible tract. Brevard, Marion, Sumter, and Volusia stay thinner samples. The other six metros do **not** have parcel extracts: the map draws the 2020 tract polygon and a Census Gazetteer pin. That is a coverage gap, not an empty county.

### Refresh the seven-market fixtures

```bash
npm run seed:oz2-markets
```

That script reads the rural CSV, checks the row counts above, and joins [Census TIGER 2020 tracts](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/6). It writes `data/fixtures/oz2-rural-markets.json` (one row per market listing, so dual-listed tracts stay duplicated) and `data/fixtures/oz2-rural-markets.geojson` (one polygon per GEOID, with a `markets` array). Pass `--offline` to rebuild the catalog from the CSV using polygons already on disk. It does not download assessor parcels. `npm run seed:oz2` is still the Orange County all-eligible refresh and is separate on purpose.

```bash
npm run seed:oz2-eligible
```

That script reads the urban seven-market CSV and the other-MSA CSV, checks the counts in the tables above (including the rural/urban splits), and joins the same TIGER 2020 tracts. It writes `data/fixtures/oz2-urban-markets.json`, `data/fixtures/oz2-other-msas.json`, and `data/fixtures/oz2-eligible-packs.geojson` (2,285 polygons). Status stays **Eligible — not designated**. Pass `--offline` to reuse polygons already on disk. It does not download parcels for the other metros.

```bash
npm run seed:sc-mf
```

That script reads `data/sc-oz2-mf-priority-shortlist.csv`, requires the eligible / not designated / not confirmed nominated status string, and checks each GEOID against the seven-market rural CSV (same market, county, South Carolina, and Gazetteer point). It writes `data/fixtures/sc-oz2-mf-priority.json`. It does not edit tract polygons or the Orange County parcel sample.

### Refresh

`npm run seed:oz` refreshes designated polygons and then OZ 2.0. `npm run seed:oz2` refreshes nomination eligibility only. Notice 2025-50 is a PDF, so install `pypdf` once (`python3 -m pip install pypdf`). The script refuses to guess a rural flag if the appendix columns change or the notice parse is not about 3,309 GEOIDs. Run `seed:oz2` after `seed:oz` / `join_oz.py`, because the designated join rewrites `opportunityZone` and the OZ 2.0 script stamps `designatedRural` afterward.

## Data sources

| Layer | Source | URL / adapter |
| --- | --- | --- |
| Parcels, owner, mailing, sale, tax, zoning, acreage | Orange County Property Appraiser public GIS | [`Webmap/PARCEL` layer 4](https://vgispublic.ocpafl.org/server/rest/services/Webmap/PARCEL/MapServer/4) |
| County FLU | Orange County open data | [Future Land Use Orange County](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21) |
| Orlando FLU | Orange County open data (city layer) | [Orlando Future Land Use](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83) |
| Zoning polygons (reference) | Orange County open data | [Unincorporated zoning](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/51), [Orlando zoning](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/82) |
| Median household income | ACS 5-year B19013 via [Census Reporter](https://api.censusreporter.org) (fixtures). Live Census Bureau API is optional. | County FIPS `12095` |
| Opportunity Zones | HUD GIS QOZ polygons (Treasury-certified 2010 tracts), Orange County subset | [Opportunity_Zones layer 13](https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/FeatureServer/13); county mirror [Public_Dynamic / 61](https://ocgis4.ocfl.net/arcgis/rest/services/Public_Dynamic/MapServer/61) |
| OZ 2.0 eligible tracts | Rev. Proc. 2026-14 appendix, Orange County rows | [rp-26-14-appendix.xlsx](https://www.irs.gov/pub/irs-drop/rp-26-14-appendix.xlsx) |
| OZ 2.0 tract geometry | Census TIGER 2020 census tracts | [TIGERweb Census 2020 tracts](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/6) |
| Designated rural QOZs | Notice 2025-50 appendix | [n-25-50.pdf](https://www.irs.gov/pub/irs-drop/n-25-50.pdf) |
| AADT | Florida DOT Traffic Characteristics Inventory | [`RCI_Layers` AADT](https://gis.fdot.gov/arcgis/rest/services/RCI_Layers/FeatureServer/0) (`COUNTY='Orange'`) |
| Streets basemap | Esri World Street Map raster (keyless). Optional MapTiler Streets v2 when `NEXT_PUBLIC_MAPTILER_KEY` is set | `https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}`. Attribution: *Tiles © Esri — Sources: Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), Esri Korea, Esri (Thailand), NGCC, © OpenStreetMap contributors, and the GIS User Community*. MapTiler: `https://api.maptiler.com/maps/streets-v2/256/{z}/{x}/{y}.png?key=` — *© MapTiler © OpenStreetMap contributors* |
| Satellite hybrid | Esri World Imagery + World Transportation + World Boundaries and Places. Optional MapTiler Hybrid when `NEXT_PUBLIC_MAPTILER_KEY` is set | Imagery `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`, roads `.../Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}`, labels `.../Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}`. No API key. Attribution: *Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community. Roads and place labels © Esri.* MapTiler hybrid replaces that stack: `https://api.maptiler.com/maps/hybrid/256/{z}/{x}/{y}.jpg?key=` |
| Dark basemap | OpenFreeMap Dark (Carto Dark Matter fallback) | Free vector tiles, no key |

Fixture snapshot metadata: `data/fixtures/meta.json`. Knowledge-base format and refresh steps: `data/README.md`.

A second public extract, [ArcGIS Online `orange_county_parcels`](https://services2.arcgis.com/N4cKzJ9dzXmsPNRs/ArcGIS/rest/services/orange_county_parcels/FeatureServer), was investigated and **not** used as the primary parcel source: it only covers a southwest subset (Bay Lake / Lake Buena Vista / nearby unincorporated), not the whole county.

## Why GeoJSON instead of PostGIS

The app installs and runs with one command, including in environments without Docker or a database. Pre-joined GeoJSON tiles plus a viewport API cover the five-county 5–150 acre extracts without posting every polygon in the first page load. A full cadastral database (every lot under 5 acres, or tracts over 150 acres) is still out of scope.

## Live keys and adapters

Default `DATA_SOURCE=fixture` reads `data/fixtures/*.geojson`.

Optional `.env.local`:

```
DATA_SOURCE=fixture
CENSUS_API_KEY=
OCPA_PARCELS_URL=https://vgispublic.ocpafl.org/server/rest/services/Webmap/PARCEL/MapServer/4/query
FDOT_AADT_URL=https://gis.fdot.gov/arcgis/rest/services/RCI_Layers/FeatureServer/0/query
OC_FLU_URL=https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21/query
ORL_FLU_URL=https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83/query
HUD_OZ_URL=https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/FeatureServer/13/query
NEXT_PUBLIC_MAPTILER_KEY=
```

- **Census Bureau ACS** now redirects unauthenticated `api.census.gov` calls to a “Missing Key” page. Sign up at [Census API key signup](https://api.census.gov/data/key_signup.html) and set `CENSUS_API_KEY` when you replace Census Reporter with a first-party live income adapter.
- **MapTiler basemap** (`NEXT_PUBLIC_MAPTILER_KEY`) is optional. Leave it unset to use keyless Esri World Street Map and the Esri imagery hybrid (roads + place labels). With a key, Streets uses [MapTiler Streets v2](https://docs.maptiler.com/cloud/api/maps/) and Satellite hybrid uses MapTiler Hybrid. The key is public in the browser; restrict it by URL in [MapTiler Cloud](https://cloud.maptiler.com/account/keys/). Dark stays on OpenFreeMap either way. Streets does not use CARTO Voyager.
- **`DATA_SOURCE=ocpa-live`** uses `OcpaLiveParcelProvider` in `src/lib/data/adapters.ts`. The Orlando map still reads the seeded fixtures. `getParcel(id)` can query OCPA live for a single Orange County id.
- **Commercial vendors:** implement `VendorParcelProvider` (Regrid, ATTOM, etc.). Do not commit paid credentials. The UI already consumes the `ParcelProvider` interface.

## Known gaps

- Lake, Orange, Osceola, Polk, and Seminole fixtures are every DOH parcel with land area from 5.0 through 150.0 acres, not a sample. Parcels under 5 or over 150 are omitted on purpose. Brevard, Marion, Sumter, and Volusia are still windowed samples and are not capped at 150. The legacy `parcels.geojson` pilot is still a 462-parcel Orange subset.
- Last sale is the **most recent OCPA sale fields** on the parcel layer (date, adjusted price, qualified flag). Older sales exist in OCPA CAMA extracts (up to five) and in Comptroller official records; those are linked, not inlined.
- Sentinel sale dates around 1900 are treated as “not available”.
- Zoning match is GIS-code based, not a substitute for a zoning opinion or PD regulating plan.
- FLU is centroid-joined, not a full polygon overlay. A parcel that straddles two FLU polygons gets one code.
- Municipal FLU besides Orlando is not in the public layers used here (Winter Park, Ocoee, Winter Garden, Apopka, Maitland, etc.). FLU-only and rezoning-candidate modes omit those parcels rather than guess.
- Designated Opportunity Zone flags use 2010 QOZ polygons; ACS income and OZ 2.0 eligibility use 2020 census tracts. Do not expect those GEOIDs to match.
- OZ 2.0 tracts are eligible for nomination under Rev. Proc. 2026-14. They are not designated 2027 QOZs. Rural vs non-rural is the appendix column, not a local rule. Orange County’s only rural-eligible tract in that list is `12095016605`.
- The seven primary markets draw rural-eligible tracts (orange) and urban eligible tracts (blue). Fourteen smaller MSAs under Other do the same. 90-minute sheds are approximate county rings, not isochrones. Parcel polygons outside the Orlando shed are not loaded. Inside the shed, Brevard, Marion, Sumter, and Volusia are thinner samples. South Carolina tracts add a governor-filed note (list not public, not designated) where that caveat is in the notes. They are not certified 2027 QOZs. The SC multifamily shortlist is a priority filter on the primary rural layer, not a nomination.
- Belle Isle, Oakland, and Windermere zoning use tables were not independently verified; district lists are empty on purpose.
- Winter Garden R-4 / R-5 exist in code but were not verified as multifamily in this pass.
- AADT is nearest FDOT **state-count** segment, not local-road counts. Some parcels sit far from a counted road.
- Block-group income is missing for a small number of centroids that do not fall in the simplified ACS polygons.
- Contact data is **mailing address + Sunbiz / OCPA / Comptroller links only**. No skip-traced phones or emails.

## Stack

TypeScript, Next.js 15 App Router, MapLibre GL, Tailwind CSS. Data layer is fixture GeoJSON with a `ParcelProvider` adapter (see above).

## Product decisions

- Desktop-first map + filter sidebar + tract-details rail. Ranked sites collapse into that rail instead of floating over the map. Filters and the sites list collapse to sheets on small screens. The Streets / Satellite hybrid / Dark control and the Measure tool sit at the top-left of the map so they stay clear of the mobile filter button, zoom controls, and the bottom parcel sheet.
- Parcel Opportunity Zone and zoning constraints stay off until their Yes/No switches are turned on. When zoning is considered, planned development is included and conditional zoning is off. No acreage/income/AADT minimum, and unknown values are included. The OZ 2.0 tract overlay starts on; the designated QOZ overlay stays off.
- Acreage slider caps at 25 ac because a linear slider to Disney-scale tracts would be unusable as a *minimum*.
- Honest empty/loading/error states rather than fake completeness, including when FLU data is missing for rezoning candidates.
- Orange County + municipal codes are both in the knowledge base because OCPA parcels span both. Unverified cities stay empty rather than copied from the county table.
- Existing apartments / airport “don’t demolish” constraints are out of scope for this pass.
