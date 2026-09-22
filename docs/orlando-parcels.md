# Orlando shed parcels

Public GIS parcels for the nine Orlando drive-shed counties:

**Brevard, Lake, Marion, Orange, Osceola, Polk, Seminole, Sumter, Volusia**

## Coverage

Seeded 2026-09-22 from Florida DOH EHWATER. Source row is the service count for `LND_SQFOOT >= 217800` (5.0 acres and up). Kept rows are the **5.0–150.0 acre** band after duplicate parcel ids are collapsed into one multipart geometry. Parcels under 5 or over 150 are excluded.

| County | FIPS | Kept (5–150 ac) | Source rows (≥5 ac) | Over 150 excluded | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| Lake | 12069 | 17,470 | 18,519 | 659 | 390 extra parts merged. No zoning/FLU. 1,237 rural-eligible centroids |
| Orange | 12095 | 14,031 | 14,369 | 218 | 120 extra parts merged. OCPA zoning on 8,072. FLU on 8,789 |
| Osceola | 12097 | 5,997 | 7,413 | 1,373 | 43 extra parts merged. No zoning/FLU. 1,482 rural-eligible centroids |
| Polk | 12105 | 19,734 | 21,292 | 1,551 | 7 extra parts merged. No zoning/FLU. 4,250 rural-eligible centroids |
| Seminole | 12117 | 4,788 | 4,909 | 121 | No zoning/FLU. No rural-eligible OZ 2.0 tracts in the pack |
| Brevard | 12009 | 120 | — | — | Thinner sample (not capped at 150) |
| Marion | 12083 | 120 | — | — | Thinner sample (not capped at 150) |
| Sumter | 12119 | 120 | — | — | Thinner sample (not capped at 150) |
| Volusia | 12127 | 120 | — | — | Thinner sample (not capped at 150) |

Shed total in `meta.json`: **62,500** parcels, of which **62,020** are the five complete 5–150 acre counties.

Counts, tile paths, and join gaps are in `data/fixtures/orlando-parcels/meta.json` after each seed. The five complete counties are not samples.

**Acreage rule.** A parcel is in a complete county when Florida DOH EHWATER `LND_SQFOOT` is from 217,800 through 6,534,000 (5.0 through 150.0 × 43,560). Stored acreage is `LND_SQFOOT / 43560`. On Orange County, the OCPA `ACREAGE` field replaces that value only when the appraiser acreage is also inside 5.0–150.0. Parcels under 5 or over 150 are excluded. A parcel of exactly 150.0 acres stays in.

## Architecture

| Layer | Role |
| --- | --- |
| `data/fixtures/orlando-parcels/tiles/{fips}/{ix}_{iy}.geojson` | Complete counties, 0.25° tiles (origin lon -83, lat 27). |
| `data/fixtures/orlando-parcels/lookup/{fips}.json` | Parcel id → tile, for `/api/parcels/[id]`. |
| `data/fixtures/orlando-parcels/{fips}.geojson` | Sample counties only (Brevard, Marion, Sumter, Volusia). |
| `data/fixtures/orlando-parcels/meta.json` | Counts, coverage, gaps. |
| `data/orlando-parcel-sources.json` | Source URLs, field mapping, rejected layers. |
| `GET /api/parcels?market=Orlando&bbox=w,s,e,n` | Reads only tiles that intersect the viewport. |
| `GET /api/parcels?market=Orlando&bbox=…&source=live` | Live DOH query used when a sample county is selected and the map is zoomed in. Sample live queries stay at ≥ 5 acres. A live query for one of the five complete counties uses the 5.0–150.0 acre band. |

The home page does not embed the full extract. The map asks for the current view. If that view still holds more parcels than the client should draw, the API returns a spatially even subset and `meta.truncated` so the UI can say to zoom in. The fixtures themselves stay complete.

Orange County still has the designated QOZ overlay, the amber non-rural OZ 2.0 tracts, FDOT traffic, and the zoning / FLU knowledge base. The separate `data/fixtures/parcels.geojson` file remains the smaller Orange pilot (income and AADT joined) used by the legacy parcel provider. The Orlando map reads the shed partitions, not that 462-parcel file.

## Refresh

```bash
npm run seed:parcels:orlando
# same thing:
python3 scripts/seed_orlando_parcels.py --full-core
```

That command re-downloads the five complete counties and leaves the four sample files in place. Optional flags:

```bash
python3 scripts/seed_orlando_parcels.py --county Lake --full-core
python3 scripts/seed_orlando_parcels.py --refresh-samples
python3 scripts/seed_orlando_parcels.py --sample --per-county 120 --min-acres 1
python3 scripts/seed_orlando_parcels.py --full-core --skip-flu
```

The seed simplifies rings (about 9 meters, looser on very dense shorelines), stamps OZ 2.0 from the local tract fixtures, and for Orange:

1. Joins OCPA owner, mailing, sale, tax, and zoning by `PARCEL` = DOH `PARCEL_ID`.
2. Centroid-joins Orange County future land use (open data layer 21) and Orlando future land use (layer 83).

A normalized cache under `/tmp/dls-orlando-core/` avoids a second DOH geometry download if the process is restarted in the same environment. Delete that directory to force a fresh pull.

## Sources

Primary layer for every county: [Florida DOH EHWATER Parcels](https://gis.floridahealth.gov/server/rest/services/EHWATER/Parcels/MapServer) (FDOR Name-Address-Legal attributes). Layer ids: Brevard 4, Lake 33, Marion 40, Orange 47, Osceola 48, Polk 52, Seminole 58, Sumter 59, Volusia 63.

Orange enrichment:

- [OCPA Webmap/PARCEL layer 4](https://vgispublic.ocpafl.org/server/rest/services/Webmap/PARCEL/MapServer/4)
- [Orange County FLU](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21)
- [Orlando FLU](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83)

## Gaps

- Lake, Osceola, Polk, and Seminole have no zoning or FLU on the DOH extract. Land-use filters should stay on **All parcels** there. Missing zoning is not treated as multifamily.
- Outside Orange, the OZ 2.0 flag is only the seven-market **rural-eligible** tract pack. Non-rural eligible tracts in those counties are not joined.
- Orange municipal FLU other than Orlando is often the county placeholder `City` and stays unknown.
- Income and AADT are not joined onto the full 5–150 acre extract.
- DOH land square feet and the county appraiser acreage field can disagree. The extract follows DOH for inclusion, then drops anything outside 5.0–150.0 acres. Orange OCPA acreage is stored only when it is still inside that band.
- A public ArcGIS Online layer named Polk County parcels is the wrong state (Minnesota). It is not used.
- Brevard’s property-appraiser MapServer has returned HTTP 403 from this environment. The sample uses DOH.
- Brevard, Marion, Sumter, and Volusia are still windowed samples around rural tracts, not every 5–150 acre parcel. Those samples are not capped at 150 acres.
