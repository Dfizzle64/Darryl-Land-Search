# Orange County multifamily site search (pilot)

Interactive map of **Orange County, Florida** parcels for multifamily site selection. Filter by zoning, Census ACS median household income, and nearby FDOT Average Annual Daily Traffic (AADT). Click a parcel for owner, sale, tax, mailing address, and public search links.

This is a v1 pilot: Orange County only, public data, no paid parcel vendors, no scraped emails or phone numbers.

## Run locally

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Other scripts:

```bash
npm test          # filter/zoning unit tests
npm run build     # production build
npm run seed      # refresh fixtures from live public GIS feeds
```

No API keys are required for the default fixture mode. Copy `.env.example` to `.env.local` only if you want to point at live feeds.

## What you can do

- Toggle **multifamily zoning only** (default on). Allowed district codes are documented and editable in `data/zoning-config.json`.
- Include or exclude **planned development / PUD** (PD may allow multifamily, but entitlements are site-specific).
- Set a **minimum median household income** and switch geography between **census tract** and **block group**.
- Set a **minimum AADT** on the nearest FDOT count segment.
- Click a parcel for owner name/LLC, last sale, assessed/market/taxable values, mailing address, and links to OCPA, Florida Sunbiz, and the Comptroller’s official records.

The bundled sample is **459 parcels** spread across Orange County (Orlando, unincorporated county, Winter Park, Ocoee, Winter Garden, Apopka, and others). It is large enough to exercise filters, not a complete cadastral extract.

## How filters work

1. **Zoning.** OCPA stores codes like `ORL-R-3B/T/AN`. The app parses the jurisdiction prefix (`ORL`) and base district (`R-3B`), then matches against tokens in `data/zoning-config.json`. Token `R-3` also matches `R-3A` / `R-3B` / `R-3C` / `R-3D`. Token `P-D` does **not** match Orlando public-use `P`.
2. **Income.** Each parcel centroid is joined to ACS median household income (table B19013). The income dropdown chooses whether the threshold applies to the tract or the block group. Parcels with no income can be kept or dropped.
3. **AADT.** Each parcel is associated with the nearest FDOT Orange County AADT polyline (by centroid). The threshold is vehicles per day on that segment. Distance is shown in the detail drawer.

Filters run in the browser against the loaded GeoJSON so the map updates immediately. `/api/parcels` applies the same logic server-side if you want a filtered FeatureCollection.

## Zoning codes treated as multifamily-capable

Configured in `data/zoning-config.json` (edit that file; do not hard-code a second list):

| Token | Why it is included |
| --- | --- |
| `R-3` | Orange County Multiple-Family Dwelling District; municipal R-3 equivalents (Apopka, Ocoee, Winter Garden, Winter Park, Edgewood, Eatonville) |
| `U-R-3` / `UR-3` | Orange County University Residential (four or more units) |
| `R-3A`–`R-3D` | City of Orlando multifamily development districts (Ch. 58 Part 2E) |
| `MXD-1` / `MXD-2` / `MIXED` | Mixed-use districts that permit residential |
| `AC-1`, `AC-2`, `AC-3`, `AC-3A`, `AC-N` | Orlando Activity Center districts (high-intensity mixed use including residential) |
| `RM` | Legacy OCPA multifamily label when present |
| `P-D` / `PD` / `PUD` | Optional. Planned development *may* allow multifamily; confirm the PD ordinance |

Not treated as multifamily by default: `R-1` family, `R-2` (one- and two-family), commercial `C-1`/`C-2`, office `P-O`, and Orlando public-use `P`.

## Data sources

| Layer | Source | URL / adapter |
| --- | --- | --- |
| Parcels, owner, mailing, sale, tax, zoning | Orange County Property Appraiser public GIS | [`Webmap/PARCEL` layer 4](https://vgispublic.ocpafl.org/server/rest/services/Webmap/PARCEL/MapServer/4) |
| Zoning polygons (reference) | Orange County open data | [Unincorporated zoning](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/51), [Orlando zoning](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/82) |
| Median household income | ACS 5-year B19013 via [Census Reporter](https://api.censusreporter.org) (fixtures). Live Census Bureau API is optional. | County FIPS `12095` |
| AADT | Florida DOT Traffic Characteristics Inventory | [`RCI_Layers` AADT](https://gis.fdot.gov/arcgis/rest/services/RCI_Layers/FeatureServer/0) (`COUNTY='Orange'`) |
| Basemap | OpenFreeMap (Carto Dark Matter fallback) | Free tiles, no key |

Fixture snapshot metadata: `data/fixtures/meta.json`. Refresh with `npm run seed` (network required).

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
```

- **Census Bureau ACS** now redirects unauthenticated `api.census.gov` calls to a “Missing Key” page. Sign up at [Census API key signup](https://api.census.gov/data/key_signup.html) and set `CENSUS_API_KEY` when you replace Census Reporter with a first-party live income adapter.
- **`DATA_SOURCE=ocpa-live`** uses `OcpaLiveParcelProvider` in `src/lib/data/adapters.ts`. Map rendering still uses the sample extract because a full-county geometry payload is too large for this client. `getParcel(id)` can query OCPA live.
- **Commercial vendors:** implement `VendorParcelProvider` (Regrid, ATTOM, etc.). Do not commit paid credentials. The UI already consumes the `ParcelProvider` interface.

## Known gaps

- Sample, not a complete Orange County parcel universe. Seed script pulls a geographically mixed subset (zoning queries + eight metro windows).
- Last sale is the **most recent OCPA sale fields** on the parcel layer (date, adjusted price, qualified flag). Older sales exist in OCPA CAMA extracts (up to five) and in Comptroller official records; those are linked, not inlined.
- Sentinel sale dates around 1900 are treated as “not available”.
- Zoning match is GIS-code based, not a substitute for a zoning opinion or PD regulating plan.
- AADT is nearest FDOT **state-count** segment, not local-road counts. Some parcels sit far from a counted road.
- Block-group income is missing for a small number of centroids that do not fall in the simplified ACS polygons.
- Contact data is **mailing address + Sunbiz / OCPA / Comptroller links only**. No skip-traced phones or emails.

## Stack

TypeScript, Next.js 15 App Router, MapLibre GL, Tailwind CSS. Data layer is fixture GeoJSON with a `ParcelProvider` adapter (see above).

## Product decisions

- Desktop-first map + filter sidebar + parcel drawer; filters collapse to a sheet on small screens.
- Default filters: multifamily zoning on, planned development included, no income/AADT minimum, unknown values included — so first load shows a useful candidate set.
- Honest empty/loading/error states rather than fake completeness.
- Orange County + City of Orlando codes are both in the default token list because OCPA parcels span both.
