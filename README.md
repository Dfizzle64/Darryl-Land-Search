# Orange County multifamily site search (pilot)

Interactive map of **Orange County, Florida** parcels for multifamily site selection. Filter by **minimum acreage**, **zoning mode** (multifamily-capable, all parcels, non-MF, rezoning candidates, FLU), **Opportunity Zones**, Census ACS median household income, and nearby FDOT Average Annual Daily Traffic (AADT). A ranked **sites** list scores matches. Click a row or parcel for owner, sale, tax, mailing address, zoning + FLU + OZ explanations, and public search links.

This is a v2 pass on the Orange County pilot: public data only, no paid parcel vendors, no scraped emails or phone numbers.

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
npm run seed:zoning  # refresh coverage report vs knowledge JSON (no LLM)
```

No API keys are required for the default fixture mode. Copy `.env.example` to `.env.local` only if you want to point at live feeds.

## What you can do

- Set a **minimum acreage** (OCPA `ACREAGE`). The slider is 0–25 acres; larger sites still match any threshold at or below 25. Acreage is shown in the parcel drawer.
- Choose a **land-use mode**: multifamily-capable zoning (default), all parcels, non-multifamily zoning, rezoning candidates (FLU yes / zoning no), FLU allows multifamily, either, or both.
- Filter **Opportunity Zones**: OZ 2.0 rural-eligible, OZ 2.0 eligible but not rural, in a current designated QOZ, not in a designated QOZ, or either. Toggle the OZ 2.0 tract overlay (orange = rural-eligible, amber = eligible and not rural) and the copper dashed designated-QOZ overlay.
- Include **planned development / PUD** (always labeled maybe — site-specific).
- Include **conditional zoning** (Live Local commercial/industrial, limited multiplex, some mixed-use overlays). Off by default so C-2 warehouses do not flood the map.
- Set a **minimum median household income** (tract or block group) and **minimum AADT**.
- Browse a **ranked sites list** (score 0–100) that stays in sync with filters. Click a row to open the drawer and fly the map.
- Open **Zoning knowledge** in the sidebar: jurisdictions covered, district explanations, citations, last-updated date. This is an offline JSON knowledge base, not a live model call.
- Switch the map between **Streets** (OpenFreeMap dark / Carto Dark Matter fallback) and **Satellite** (Esri World Imagery). The toggle is a map control; parcel filters, selection, OZ overlay, and camera stay put. Satellite imagery is a public Esri tile service and needs no API key.

The bundled sample is **462 parcels** spread across Orange County (Orlando, unincorporated county, Winter Park, Ocoee, Winter Garden, Apopka, Bithlo–Wedgefield, and others). It is large enough to exercise filters, not a complete cadastral extract. Three of those parcels sit in the one Orange County OZ 2.0 rural-eligible tract so the filter and drawer can open it.

## How filters work

1. **Acreage.** OCPA parcel `ACREAGE`. Unknown acreage can be kept or dropped (the sample has acreage on every parcel).
2. **Zoning.** OCPA stores codes like `ORL-R-3B/T/AN`. The app parses the jurisdiction prefix (`ORL`) and base district (`R-3B`), then matches **that jurisdiction’s** districts in `data/zoning-config.json`. County `R-3` does not silently match Orlando `R-3A` unless Orlando lists it. Token `P-D` does **not** match Orlando public-use `P`.
3. **FLU.** Parcel centroids are joined to [Orange County Future Land Use](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21) and [Orlando Future Land Use](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83). `data/flu-config.json` decides which GIS codes are MF-supportive. Overlay suffixes such as `/RES-PRO` fall back to the base code.
4. **Opportunity Zones.** Designated QOZs use HUD/Treasury polygons (2010 Census tracts), not ACS 2020 tract IDs. OZ 2.0 uses 2020 census tracts from the Rev. Proc. 2026-14 appendix. Filters: rural-eligible, eligible but not rural, in a designated QOZ, not in a designated QOZ, or either. The OZ 2.0 overlay draws all 87 Orange County eligible tracts; the copper dashed overlay is the county’s 24 current QOZ tracts.
5. **Income.** ACS median household income (B19013) by tract or block group.
6. **AADT.** Nearest FDOT Orange County count segment.

Filters run in the browser against the loaded GeoJSON so the map and ranked list update immediately. `/api/parcels` applies the same logic server-side (`landUse`, `oz`, `minAcres`, `cond`, `pd`, …).

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

In this sample, FLU joined on **375 / 462** parcels. There are parcels with MF-supportive FLU and non-MF current zoning — use land-use mode **Rezoning candidates**, **FLU allows multifamily / higher density**, or **Either**.

## Opportunity Zones

Qualified Opportunity Zones are **2010 Census tracts** nominated by the state and certified by the U.S. Treasury (IRC §§ 1400Z-1 / 1400Z-2). They are **not** the same geography as ACS 2020 tracts used for income.

| Piece | Source |
| --- | --- |
| Overlay polygons | [HUD GIS Opportunity Zones](https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/FeatureServer/13) filtered to Florida `STATE='12'` and Orange County `COUNTY='095'` (24 tracts). Fallback: [Orange County Public_Dynamic / 61](https://ocgis4.ocfl.net/arcgis/rest/services/Public_Dynamic/MapServer/61) |
| Parcel flag | Centroid-in-polygon against those 2010 QOZ polygons (`npm run seed:oz`) |

The app runs offline from `data/fixtures/opportunity-zones.geojson` plus `opportunityZone` on each parcel. In this sample **26 / 462** parcels fall in a designated QOZ; the overlay still draws all 24 county tracts. The drawer shows yes/no, the 2010 tract GEOID when inside a zone, and whether Notice 2025-50 lists that designated tract as rural. None of Orange County’s 24 current QOZ tracts are on that rural list.

Product decisions:

- Join by geometry, never by ACS 2020 `incomeTract.geoid`.
- The designated overlay is off by default so it does not fight parcel fills; the Streets / Satellite toggle does not drop it.
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

The parcel drawer shows eligible / not eligible, the official rural flag, and the GEOID, and says the tract has not been nominated or certified.

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
| Streets basemap | OpenFreeMap (Carto Dark Matter fallback) | Free vector tiles, no key |
| Satellite basemap | Esri World Imagery | Public XYZ tiles at `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}` — no API key. Attribution: *Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community* (shown on the map when Satellite is selected, and in MapLibre’s attribution control). |

Fixture snapshot metadata: `data/fixtures/meta.json`. Knowledge-base format and refresh steps: `data/README.md`.

A second public extract, [ArcGIS Online `orange_county_parcels`](https://services2.arcgis.com/N4cKzJ9dzXmsPNRs/ArcGIS/rest/services/orange_county_parcels/FeatureServer), was investigated and **not** used as the primary parcel source: it only covers a southwest subset (Bay Lake / Lake Buena Vista / nearby unincorporated), not the whole county.

## Why GeoJSON instead of PostGIS

The pilot needs to install and run with one command, including in environments without Docker or a database. Pre-joined GeoJSON + JSON config is enough for hundreds of parcels, keeps adapters explicit, and avoids operating PostGIS. Next step for a production county-wide build is PMTiles (or PostGIS + vector tiles) for ~400k parcels.

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
```

- **Census Bureau ACS** now redirects unauthenticated `api.census.gov` calls to a “Missing Key” page. Sign up at [Census API key signup](https://api.census.gov/data/key_signup.html) and set `CENSUS_API_KEY` when you replace Census Reporter with a first-party live income adapter.
- **`DATA_SOURCE=ocpa-live`** uses `OcpaLiveParcelProvider` in `src/lib/data/adapters.ts`. Map rendering still uses the sample extract because a full-county geometry payload is too large for this client. `getParcel(id)` can query OCPA live.
- **Commercial vendors:** implement `VendorParcelProvider` (Regrid, ATTOM, etc.). Do not commit paid credentials. The UI already consumes the `ParcelProvider` interface.

## Known gaps

- Sample, not a complete Orange County parcel universe. Seed script pulls a geographically mixed subset (zoning queries + eight metro windows) and is biased toward larger lots (`orderByFields=ACREAGE DESC`).
- Last sale is the **most recent OCPA sale fields** on the parcel layer (date, adjusted price, qualified flag). Older sales exist in OCPA CAMA extracts (up to five) and in Comptroller official records; those are linked, not inlined.
- Sentinel sale dates around 1900 are treated as “not available”.
- Zoning match is GIS-code based, not a substitute for a zoning opinion or PD regulating plan.
- FLU is centroid-joined, not a full polygon overlay. A parcel that straddles two FLU polygons gets one code.
- Municipal FLU besides Orlando is not in the public layers used here (Winter Park, Ocoee, Winter Garden, Apopka, Maitland, etc.). FLU-only and rezoning-candidate modes omit those parcels rather than guess.
- Designated Opportunity Zone flags use 2010 QOZ polygons; ACS income and OZ 2.0 eligibility use 2020 census tracts. Do not expect those GEOIDs to match.
- OZ 2.0 tracts are eligible for nomination under Rev. Proc. 2026-14. They are not designated 2027 QOZs. Rural vs non-rural is the appendix column, not a local rule. Orange County’s only rural-eligible tract in that list is `12095016605`.
- Belle Isle, Oakland, and Windermere zoning use tables were not independently verified; district lists are empty on purpose.
- Winter Garden R-4 / R-5 exist in code but were not verified as multifamily in this pass.
- AADT is nearest FDOT **state-count** segment, not local-road counts. Some parcels sit far from a counted road.
- Block-group income is missing for a small number of centroids that do not fall in the simplified ACS polygons.
- Contact data is **mailing address + Sunbiz / OCPA / Comptroller links only**. No skip-traced phones or emails.

## Stack

TypeScript, Next.js 15 App Router, MapLibre GL, Tailwind CSS. Data layer is fixture GeoJSON with a `ParcelProvider` adapter (see above).

## Product decisions

- Desktop-first map + filter sidebar + ranked sites overlay (`xl+`) + parcel drawer; filters collapse to a sheet on small screens and the sites list is a **Sites** sheet. The Streets / Satellite control sits at the top-left of the map so it stays clear of the mobile filter button, zoom controls, and the bottom parcel sheet.
- Default filters: multifamily-capable zoning, planned development included, conditional zoning off, OZ either, no acreage/income/AADT minimum, unknown values included — so first load still shows a useful candidate set. The OZ 2.0 tract overlay starts on; the designated QOZ overlay stays off.
- Acreage slider caps at 25 ac because a linear slider to Disney-scale tracts would be unusable as a *minimum*.
- Honest empty/loading/error states rather than fake completeness, including when FLU data is missing for rezoning candidates.
- Orange County + municipal codes are both in the knowledge base because OCPA parcels span both. Unverified cities stay empty rather than copied from the county table.
- Existing apartments / airport “don’t demolish” constraints are out of scope for this pass.
