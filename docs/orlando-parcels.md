# Orlando shed parcels

Public GIS parcels for the nine Orlando drive-shed counties:

**Brevard, Lake, Marion, Orange, Osceola, Polk, Seminole, Sumter, Volusia**

## Coverage

Orange is the public OCPA cadastre. The other complete counties are Florida DOH EHWATER. Kept rows are the **5.0–150.0 acre** band after shapes that share a parcel id are collapsed into one geometry. Parcels under 5 or over 150 are excluded.

| County | FIPS | Kept (5–150 ac) | Source rows in band | Notes |
| --- | --- | ---: | ---: | --- |
| Lake | 12069 | 17,470 | 17,845 | 375 extra parts merged. No zoning/FLU. 1,234 rural-eligible centroids |
| Orange | 12095 | 11,709 | 11,887 | OCPA shapes. 320 extra parts merged. 36 multipart accounts summed past 150 and dropped. Zoning on 9,789. FLU on 8,238 |
| Osceola | 12097 | 5,997 | 6,028 | 31 extra parts merged. No zoning/FLU. 1,481 rural-eligible centroids |
| Polk | 12105 | 19,734 | 19,738 | 4 extra parts merged. No zoning/FLU. 4,253 rural-eligible centroids |
| Seminole | 12117 | 4,788 | 4,788 | No zoning/FLU. No rural-eligible OZ 2.0 tracts in the pack |
| Brevard | 12009 | 120 | — | Thinner sample (not capped at 150) |
| Marion | 12083 | 120 | — | Thinner sample (not capped at 150) |
| Sumter | 12119 | 120 | — | Thinner sample (not capped at 150) |
| Volusia | 12127 | 120 | — | Thinner sample (not capped at 150) |

Shed total in `meta.json`: **60,178** parcels, of which **59,698** are the five complete 5–150 acre counties. Orange is lower than the old DOH extract because the appraiser layer is the current cadastre: stale DOH parent parcels are gone, and multipart accounts whose piece acres sum above 150 are dropped.

Counts, tile paths, and join gaps are in `data/fixtures/orlando-parcels/meta.json` after each seed. The five complete counties are not samples.

**Acreage rule.** Lake, Osceola, Polk, and Seminole use Florida DOH EHWATER `LND_SQFOOT` from 217,800 through 6,534,000 (5.0 through 150.0 × 43,560). Stored acreage is `LND_SQFOOT / 43560`. Orange uses OCPA `ACREAGE` on each shape. Shapes that share a parcel id are one tax account: when the piece acres differ, they are summed, and the parcel is dropped if that sum is outside 5.0–150.0. A parcel of exactly 150.0 acres stays in.

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

Orange County geometry and tax attributes come from the public OCPA parcel layer, not the DOH statewide copy. DOH remains the source for the other shed counties. Rings are simplified at about 1–7 meters and written with GeoJSON winding (Esri clockwise exteriors stay exteriors; holes stay holes). The separate `data/fixtures/parcels.geojson` file remains the smaller Orange pilot used by the legacy parcel provider. The Orlando map reads the shed partitions, not that 462-parcel file.

Median household income and FDOT AADT are not stored on the tiles. `npm run seed:signals` writes `data/fixtures/income-tracts.geojson` (ACS B19013 for Florida counties that have parcels) and `data/fixtures/aadt-segments.geojson` (FDOT 2025). `/api/parcels` joins them at query time. A segment farther than 15 km is left unknown. That is a size choice, not a missing attribute: copying the same tract income onto every parcel would inflate the extract without adding a fact.

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

The seed simplifies rings at about 1–7 meters (never collapsing a ring to its first three vertices), writes GeoJSON winding, stamps OZ 2.0 from the local tract fixtures, and for Orange:

1. Downloads geometry, owner, mailing, sale, tax, and zoning from the OCPA parcel layer. Shapes that share a parcel id are one tax account: piece acres are summed, and the parcel is dropped if that sum is outside 5.0–150.0.
2. Centroid-joins Orange County future land use (open data layer 21) and Orlando future land use (layer 83).

A normalized cache under `/tmp/dls-orlando-core/` (`*-geom2.json`) avoids a second geometry download if the process is restarted in the same environment. Delete that directory to force a fresh pull. Older caches without `geometryVersion: 2` are ignored.

## Sources

Primary layer for Lake, Osceola, Polk, Seminole, and the four sample counties: [Florida DOH EHWATER Parcels](https://gis.floridahealth.gov/server/rest/services/EHWATER/Parcels/MapServer) (FDOR Name-Address-Legal attributes). Layer ids: Brevard 4, Lake 33, Marion 40, Osceola 48, Polk 52, Seminole 58, Sumter 59, Volusia 63.

Orange cadastre:

- [OCPA Webmap/PARCEL layer 4](https://vgispublic.ocpafl.org/server/rest/services/Webmap/PARCEL/MapServer/4)
- [Orange County FLU](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21)
- [Orlando FLU](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83)

## Gaps

- Lake, Osceola, Polk, and Seminole have no zoning or FLU on the DOH extract. Land-use filters should stay on **All parcels** there. Missing zoning is not treated as multifamily.
- Outside Orange, the OZ 2.0 flag is only the seven-market **rural-eligible** tract pack. Non-rural eligible tracts in those counties are not joined.
- Orange municipal FLU other than Orlando is often the county placeholder `City` and stays unknown. In this 5–150 acre snapshot, 8,238 Orange parcels have a FLU code and 3,471 do not.
- Income and AADT are not stored on the parcel tiles. `/api/parcels` joins ACS B19013 and FDOT AADT at query time for Florida. Block-group income is still Orange County only. Other states stay unknown. Uncheck Include unknown to hide those parcels.
- Orange inclusion uses OCPA `ACREAGE`, including sibling shapes under 5 acres that belong to the same parcel id. Those pieces are summed and the parcel is dropped when the sum is outside 5.0–150.0. Other complete counties still use DOH `LND_SQFOOT`.
- A public ArcGIS Online layer named Polk County parcels is the wrong state (Minnesota). It is not used.
- Brevard’s property-appraiser MapServer has returned HTTP 403 from this environment. The sample uses DOH.
- Brevard, Marion, Sumter, and Volusia are still windowed samples around rural tracts, not every 5–150 acre parcel. Those samples are not capped at 150 acres. The Brevard sample is stamped with the same city zoning and FLU join as the market tiles when a centroid falls in a wired city (`docs/brevard-municipal.md`). Titusville and Palm Bay are not applied in that join.
