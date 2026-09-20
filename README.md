# Orange County multifamily site search (pilot)

Interactive map of **Orange County, Florida** parcels for multifamily site selection. Filter by **minimum acreage**, **current zoning**, **Future Land Use (FLU)**, Census ACS median household income, and nearby FDOT Average Annual Daily Traffic (AADT). Click a parcel for owner, sale, tax, mailing address, zoning + FLU explanations, and public search links.

This is a v2 pass on the Orange County pilot: public data only, no paid parcel vendors, no scraped emails or phone numbers.

## Run locally

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Other scripts:

```bash
npm test             # acreage / zoning / FLU unit tests
npm run build        # production build
npm run seed         # parcels + income + AADT, then FLU join, then zoning coverage
npm run seed:flu     # re-join FLU onto the existing parcel fixture
npm run seed:zoning  # refresh coverage report vs knowledge JSON (no LLM)
```

No API keys are required for the default fixture mode. Copy `.env.example` to `.env.local` only if you want to point at live feeds.

## What you can do

- Set a **minimum acreage** (OCPA `ACREAGE`). The slider is 0–25 acres; larger sites still match any threshold at or below 25. Acreage is shown in the parcel drawer.
- Choose a **land-use mode**: current MF zoning, FLU allows multifamily / higher density, either, both, or off.
- Include **planned development / PUD** (always labeled maybe — site-specific).
- Include **conditional zoning** (Live Local commercial/industrial, limited multiplex, some mixed-use overlays). Off by default so C-2 warehouses do not flood the map.
- Set a **minimum median household income** (tract or block group) and **minimum AADT**.
- Open **Zoning knowledge** in the sidebar: jurisdictions covered, district explanations, citations, last-updated date. This is an offline JSON knowledge base, not a live model call.
- Switch the map between **Streets** (OpenFreeMap dark / Carto Dark Matter fallback) and **Satellite** (Esri World Imagery). The toggle is a map control; parcel filters, selection, and camera stay put. Satellite imagery is a public Esri tile service and needs no API key.

The bundled sample is **459 parcels** spread across Orange County (Orlando, unincorporated county, Winter Park, Ocoee, Winter Garden, Apopka, and others). It is large enough to exercise filters, not a complete cadastral extract.

## How filters work

1. **Acreage.** OCPA parcel `ACREAGE`. Unknown acreage can be kept or dropped (the sample has acreage on every parcel).
2. **Zoning.** OCPA stores codes like `ORL-R-3B/T/AN`. The app parses the jurisdiction prefix (`ORL`) and base district (`R-3B`), then matches **that jurisdiction’s** districts in `data/zoning-config.json`. County `R-3` does not silently match Orlando `R-3A` unless Orlando lists it. Token `P-D` does **not** match Orlando public-use `P`.
3. **FLU.** Parcel centroids are joined to [Orange County Future Land Use](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21) and [Orlando Future Land Use](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83). `data/flu-config.json` decides which GIS codes are MF-supportive. Overlay suffixes such as `/RES-PRO` fall back to the base code.
4. **Income.** ACS median household income (B19013) by tract or block group.
5. **AADT.** Nearest FDOT Orange County count segment.

Filters run in the browser against the loaded GeoJSON so the map updates immediately. `/api/parcels` applies the same logic server-side (`landUse`, `minAcres`, `cond`, `pd`, …).

### Land-use modes

| Mode | Keeps a parcel when |
| --- | --- |
| Current MF zoning (default) | District is `permitted` in the knowledge base, or PD if that toggle is on, or conditional if that toggle is on |
| FLU allows MF / higher density | Joined FLU category has `allowsMultifamily: true` |
| Either | Zoning match **or** FLU match |
| Both | Zoning match **and** FLU match |
| Off | No zoning/FLU filter |

FLU-only mode does **not** treat missing FLU as a match. Other municipalities besides Orlando often have no joined FLU — that is an honest gap, not an empty county.

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

In this sample, FLU joined on **372 / 459** parcels. There are parcels with MF-supportive FLU and non-MF current zoning — use land-use mode **FLU allows multifamily / higher density** or **Either**.

## Data sources

| Layer | Source | URL / adapter |
| --- | --- | --- |
| Parcels, owner, mailing, sale, tax, zoning, acreage | Orange County Property Appraiser public GIS | [`Webmap/PARCEL` layer 4](https://vgispublic.ocpafl.org/server/rest/services/Webmap/PARCEL/MapServer/4) |
| County FLU | Orange County open data | [Future Land Use Orange County](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21) |
| Orlando FLU | Orange County open data (city layer) | [Orlando Future Land Use](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83) |
| Zoning polygons (reference) | Orange County open data | [Unincorporated zoning](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/51), [Orlando zoning](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/82) |
| Median household income | ACS 5-year B19013 via [Census Reporter](https://api.censusreporter.org) (fixtures). Live Census Bureau API is optional. | County FIPS `12095` |
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
- Municipal FLU besides Orlando is not in the public layers used here (Winter Park, Ocoee, Winter Garden, Apopka, Maitland, etc.). FLU-only mode will omit those parcels rather than guess.
- Belle Isle, Oakland, and Windermere zoning use tables were not independently verified; district lists are empty on purpose.
- Winter Garden R-4 / R-5 exist in code but were not verified as multifamily in this pass.
- AADT is nearest FDOT **state-count** segment, not local-road counts. Some parcels sit far from a counted road.
- Block-group income is missing for a small number of centroids that do not fall in the simplified ACS polygons.
- Contact data is **mailing address + Sunbiz / OCPA / Comptroller links only**. No skip-traced phones or emails.

## Stack

TypeScript, Next.js 15 App Router, MapLibre GL, Tailwind CSS. Data layer is fixture GeoJSON with a `ParcelProvider` adapter (see above).

## Product decisions

- Desktop-first map + filter sidebar + parcel drawer; filters collapse to a sheet on small screens. The Streets / Satellite control sits at the top-left of the map so it stays clear of the mobile filter button, zoom controls, and the bottom parcel sheet.
- Default filters: current MF zoning, planned development included, conditional zoning off, no acreage/income/AADT minimum, unknown values included — so first load still shows a useful candidate set.
- Acreage slider caps at 25 ac because a linear slider to Disney-scale tracts would be unusable as a *minimum*.
- Honest empty/loading/error states rather than fake completeness, including when FLU data is missing.
- Orange County + municipal codes are both in the knowledge base because OCPA parcels span both. Unverified cities stay empty rather than copied from the county table.
