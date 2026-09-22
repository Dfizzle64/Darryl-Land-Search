# Orlando shed parcels

Public GIS parcels for the nine Orlando drive-shed counties:

**Brevard, Lake, Marion, Orange, Osceola, Polk, Seminole, Sumter, Volusia**

## Coverage

Seeded 2026-09-22 from Florida DOH EHWATER. Source row is the service count for `LND_SQFOOT >= 217800`. Kept rows collapse duplicate parcel ids into one multipart geometry.

| County | FIPS | Kept | Source rows | Notes |
| --- | --- | ---: | ---: | --- |
| Lake | 12069 | 18,129 | 18,519 | 390 extra parts merged. No zoning/FLU. 1,257 rural-eligible centroids |
| Orange | 12095 | 14,249 | 14,369 | 120 extra parts merged. OCPA zoning on 8,258. FLU on 8,946 |
| Osceola | 12097 | 7,370 | 7,413 | 43 extra parts merged. No zoning/FLU |
| Polk | 12105 | 21,285 | 21,292 | 7 extra parts merged. No zoning/FLU. 4,959 rural-eligible centroids |
| Seminole | 12117 | 4,909 | 4,909 | No zoning/FLU. No rural-eligible OZ 2.0 tracts in the pack |
| Brevard | 12009 | 120 | — | Thinner sample |
| Marion | 12083 | 120 | — | Thinner sample |
| Sumter | 12119 | 120 | — | Thinner sample |
| Volusia | 12127 | 120 | — | Thinner sample |

Shed total in `meta.json`: **66,422** parcels, of which **65,942** are the five complete ≥5 acre counties.

Counts, tile paths, and join gaps are in `data/fixtures/orlando-parcels/meta.json` after each seed. The five complete counties are not samples.

**Acreage rule.** A parcel is in a complete county when Florida DOH EHWATER `LND_SQFOOT` is at least 217,800 (5.0 × 43,560). Stored acreage is `LND_SQFOOT / 43560`. On Orange County, the OCPA `ACREAGE` field replaces that value when the appraiser acreage is also ≥ 5. Parcels under 5 acres are out of scope for this extract.

## Architecture

| Layer | Role |
| --- | --- |
| `data/fixtures/orlando-parcels/tiles/{fips}/{ix}_{iy}.geojson` | Complete counties, 0.25° tiles (origin lon -83, lat 27). |
| `data/fixtures/orlando-parcels/lookup/{fips}.json` | Parcel id → tile, for `/api/parcels/[id]`. |
| `data/fixtures/orlando-parcels/{fips}.geojson` | Sample counties only (Brevard, Marion, Sumter, Volusia). |
| `data/fixtures/orlando-parcels/meta.json` | Counts, coverage, gaps. |
| `data/orlando-parcel-sources.json` | Source URLs, field mapping, rejected layers. |
| `GET /api/parcels?market=Orlando&bbox=w,s,e,n` | Reads only tiles that intersect the viewport. |
| `GET /api/parcels?market=Orlando&bbox=…&source=live` | Live DOH query, also ≥ 5 acres, used when a sample county is selected and the map is zoomed in. |

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
- Income and AADT are not joined onto the full ≥5 acre extract.
- DOH land square feet and the county appraiser acreage field can disagree. The extract follows DOH for inclusion.
- A public ArcGIS Online layer named Polk County parcels is the wrong state (Minnesota). It is not used.
- Brevard’s property-appraiser MapServer has returned HTTP 403 from this environment. The sample uses DOH.
- Brevard, Marion, Sumter, and Volusia are still windowed samples around rural tracts, not every ≥5 acre parcel.
