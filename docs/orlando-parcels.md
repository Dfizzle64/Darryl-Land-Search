# Orlando shed parcels

Public GIS parcels for the nine Orlando drive-shed counties:

**Brevard, Lake, Marion, Orange, Osceola, Polk, Seminole, Sumter, Volusia**

## Coverage

Lake and Osceola are county property-appraiser / open-data cadastres. Sumter is the SWFWMD parcel mirror. Orange is the public OCPA cadastre. Seminole keeps DOH parcel geometry and joins county land use. Polk, plus the three sample counties, stay on Florida DOH EHWATER. Kept rows are the **5.0–150.0 acre** band after shapes that share a parcel id are collapsed into one geometry. Parcels under 5 or over 150 are excluded.

| County | FIPS | Kept (5–150 ac) | Source rows in band | Notes |
| --- | --- | ---: | ---: | --- |
| Lake | 12069 | 16,753 | 16,826 | 66 extra parts merged. 7 multipart accounts summed past 150 and dropped. Zoning on 13,633. FLU on 13,602. 1,134 rural-eligible centroids |
| Orange | 12095 | 11,709 | 11,887 | OCPA shapes. 320 extra parts merged. 36 multipart accounts summed past 150 and dropped. Zoning on 9,789. FLU on 8,238 |
| Osceola | 12097 | 6,169 | 6,170 | 1 extra part merged. Zoning on 6,081, including 400 St. Cloud overrides. FLU on 6,032, including 1,376 St. Cloud overrides. 1,511 rural-eligible centroids |
| Polk | 12105 | 19,734 | 19,738 | 4 extra parts merged. No zoning/FLU. 4,253 rural-eligible centroids |
| Seminole | 12117 | 4,788 | 4,788 | DOH geometry. Zoning on 4,012. FLU on 4,013. Altamonte Springs zoning on 138. Oviedo zoning on 146. 67 parcels still carry the county `CITY` stub. No rural-eligible OZ 2.0 tracts in the pack |
| Sumter | 12119 | 6,602 | 6,602 | SWFWMD `AREANO`. Zoning on 6,578. FLU on 6,575. 2026 qualified sales matched 65 parcels. 2,268 rural-eligible centroids |
| Brevard | 12009 | 120 | — | Thinner sample (not capped at 150) |
| Marion | 12083 | 120 | — | Thinner sample (not capped at 150) |
| Volusia | 12127 | 120 | — | Thinner sample (not capped at 150) |

Shed total in `meta.json`: **66,115** parcels, of which **65,755** are the six complete 5–150 acre counties. Orange is lower than the old DOH extract because the appraiser layer is the current cadastre: stale DOH parent parcels are gone, and multipart accounts whose piece acres sum above 150 are dropped.

Counts, tile paths, and join gaps are in `data/fixtures/orlando-parcels/meta.json` after each seed. The six complete counties are not samples.

**Acreage rule.** Lake uses Open Data `Acres`. Osceola uses county `TotalAcres`. Sumter uses SWFWMD `AREANO` (the `ACRES` column on that layer is empty). Polk and Seminole use Florida DOH EHWATER `LND_SQFOOT` from 217,800 through 6,534,000 (5.0 through 150.0 × 43,560). Orange uses OCPA `ACREAGE` on each shape. Shapes that share a parcel id are one tax account: when the piece acres differ, they are summed, and the parcel is dropped if that sum is outside 5.0–150.0. A parcel of exactly 150.0 acres stays in.

## Architecture

| Layer | Role |
| --- | --- |
| `data/fixtures/orlando-parcels/tiles/{fips}/{ix}_{iy}.geojson` | Complete counties, 0.25° tiles (origin lon -83, lat 27). |
| `data/fixtures/orlando-parcels/lookup/{fips}.json` | Parcel id → tile, for `/api/parcels/[id]`. |
| `data/fixtures/orlando-parcels/{fips}.geojson` | Sample counties only (Brevard, Marion, Volusia). |
| `data/fixtures/orlando-parcels/meta.json` | Counts, coverage, gaps. |
| `data/orlando-parcel-sources.json` | Source URLs, field mapping, rejected layers. |
| `GET /api/parcels?market=Orlando&bbox=w,s,e,n` | Reads only tiles that intersect the viewport. |
| `GET /api/parcels?market=Orlando&bbox=…&source=live` | Live DOH query used when a sample county is selected and the map is zoomed in. Sample live queries stay at ≥ 5 acres. A live query for one of the complete counties uses the 5.0–150.0 acre band. |

The home page does not embed the full extract. The map asks for the current view. If that view still holds more parcels than the client should draw, the API returns a spatially even subset and `meta.truncated` so the UI can say to zoom in. The fixtures themselves stay complete.

Orange County geometry and tax attributes come from the public OCPA parcel layer. Lake geometry and tax attributes come from the county Open Data tax-parcel layer. Osceola geometry and tax attributes come from the county Parcels feature service. Sumter geometry, owner, tax, and DOR come from the SWFWMD parcel mirror. Seminole geometry and tax attributes stay on DOH, with zoning and future land use joined from the county Land Use service. DOH remains the source for Polk and the three sample counties, and for live viewport fills. Rings are simplified at about 1–7 meters and written with GeoJSON winding (Esri clockwise exteriors stay exteriors; holes stay holes). The separate `data/fixtures/parcels.geojson` file remains the smaller Orange pilot used by the legacy parcel provider. The Orlando map reads the shed partitions, not that 462-parcel file.

Median household income and FDOT AADT are not stored on the tiles. `npm run seed:signals` writes `data/fixtures/income-tracts.geojson` (ACS B19013 for Florida counties that have parcels) and `data/fixtures/aadt-segments.geojson` (FDOT 2025). `/api/parcels` joins them at query time. A segment farther than 15 km is left unknown. That is a size choice, not a missing attribute: copying the same tract income onto every parcel would inflate the extract without adding a fact.

## Refresh

```bash
npm run seed:parcels:orlando
# same thing:
python3 scripts/seed_orlando_parcels.py --full-core
```

That command re-downloads the complete counties and leaves the three sample files in place. Optional flags:

```bash
python3 scripts/seed_orlando_parcels.py --county Lake --full-core
python3 scripts/seed_orlando_parcels.py --refresh-samples
python3 scripts/seed_orlando_parcels.py --sample --per-county 120 --min-acres 1
python3 scripts/seed_orlando_parcels.py --full-core --skip-flu
```

The seed simplifies rings at about 1–7 meters (never collapsing a ring to its first three vertices), writes GeoJSON winding, stamps OZ 2.0 from the local tract fixtures, and:

1. For Orange, downloads geometry, owner, mailing, sale, tax, and zoning from the OCPA parcel layer. Shapes that share a parcel id are one tax account: piece acres are summed, and the parcel is dropped if that sum is outside 5.0–150.0. Future land use is a centroid join to Orange County open-data layer 21 and Orlando layer 83.
2. For Osceola, downloads Parcels FeatureServer/3 (`TotalAcres` 5–150) and centroid-joins Zoning MapServer/13 and Future Land Use FeatureServer/12. A zoning miss falls back to parcel `Zone1` when that field is set. St. Cloud zoning FeatureServer/2 and FLU FeatureServer/98 then override a matching PIN.
3. For Lake, downloads Open Data Tax Parcels FeatureServer/12 (`Acres` 5–150) and centroid-joins Interactive Map zoning layer 50 and Future Land Use 2030 layer 48.
4. For Seminole, keeps the DOH 5–150 acre extract and centroid-joins Land Use FeatureServer/1 (zoning) and FeatureServer/0 (future land use). Altamonte Springs EnerGov layers 39 and 44, then Oviedo DSZoning layers 11 and 10, override the county code inside those cities.
5. For Sumter, downloads SWFWMD Sumter County Parcels (`AREANO` 5–150), joins 2026 qualified sales on PIN, and centroid-joins county FLU_Zoning layers 11 and 5 when that host answers.

```bash
python3 scripts/seed_orlando_parcels.py --county Osceola,Lake --full-core
```

A normalized cache under `/tmp/dls-orlando-core/` (`*-geom2.json`) avoids a second geometry download if the process is restarted in the same environment. Delete that directory to force a fresh pull. Older caches without `geometryVersion: 2` are ignored.

## Sources

Primary layer for Polk, Seminole parcel geometry, and the three sample counties: [Florida DOH EHWATER Parcels](https://gis.floridahealth.gov/server/rest/services/EHWATER/Parcels/MapServer) (FDOR Name-Address-Legal attributes). Layer ids: Brevard 4, Marion 40, Polk 52, Seminole 58, Sumter 59, Volusia 63. Live viewport queries still use DOH for every shed county, including Lake 33, Osceola 48, and Sumter 59.

Osceola cadastre (verified 2026-09-23; directory HTML is often 403, JSON queries return 200; the host certificate chain is incomplete from some clients):

- [Parcels FeatureServer/3](https://gis.osceola.org/hosting/rest/services/Parcels/FeatureServer/3)
- [Zoning MapServer/13](https://gis.osceola.org/hosting/rest/services/Zoning/MapServer/13)
- [Future Land Use FeatureServer/12](https://gis.osceola.org/hosting/rest/services/Future_Land_Use/FeatureServer/12)
- Appraiser map: `https://maps.property-appraiser.org/?Pin={PIN}`

Lake cadastre:

- [Open Data Tax Parcels FeatureServer/12](https://gis.lakecountyfl.gov/lakegis/rest/services/OpenData/OpenData1/FeatureServer/12)
- [Zoning MapServer/50](https://gis.lakecountyfl.gov/lakegis/rest/services/InteractiveMap/MapServer/50)
- [Future Land Use 2030 MapServer/48](https://gis.lakecountyfl.gov/lakegis/rest/services/InteractiveMap/MapServer/48)
- Appraiser record: `https://www.lakecopropappr.com/property-details.aspx?AltKey={AltKey}`

Orange cadastre:

- [OCPA Webmap/PARCEL layer 4](https://vgispublic.ocpafl.org/server/rest/services/Webmap/PARCEL/MapServer/4)
- [Orange County FLU](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21)
- [Orlando FLU](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83)

Seminole land use (verified 2026-09-23, geometries in Florida near -81.22, 28.7):

- [Future land use FeatureServer/0](https://services3.arcgis.com/n4VF6lyYfB5kizho/arcgis/rest/services/Land_Use/FeatureServer/0) (`FutureLandUse`)
- [Zoning FeatureServer/1](https://services3.arcgis.com/n4VF6lyYfB5kizho/arcgis/rest/services/Land_Use/FeatureServer/1) (`Zoning`)
- [Altamonte Springs zoning](https://webgis.altamonte.org/gis/rest/services/EnerGov/EnerGovService/MapServer/39) and [FLU](https://webgis.altamonte.org/gis/rest/services/EnerGov/EnerGovService/MapServer/44)
- [Oviedo zoning](https://services.arcgis.com/0EfLIvtSLPR9PKI2/arcgis/rest/services/DSZoning/FeatureServer/11) and [FLU](https://services.arcgis.com/0EfLIvtSLPR9PKI2/arcgis/rest/services/DSZoning/FeatureServer/10)

Sumter (verified 2026-09-23, geometries in Florida):

- [SWFWMD Sumter County Parcels](https://services1.arcgis.com/gdr0FcZCwx1BmrQk/arcgis/rest/services/Sumter_County_Parcels/FeatureServer/0) (`AREANO`, owner, `PARVAL`, `ASSD_TOT`, DOR, `PALINK`)
- [2026 qualified sales](https://services3.arcgis.com/ITa4LPv6Pe88ISGp/arcgis/rest/services/2026_Qualified_Sales/FeatureServer/0) joined on PIN
- County [zoning FeatureServer/11](https://gis.sumtercountyfl.gov/sumtergis/rest/services/Interactive/FLU_Zoning/FeatureServer/11) and [FLU FeatureServer/5](https://gis.sumtercountyfl.gov/sumtergis/rest/services/Interactive/FLU_Zoning/FeatureServer/5) when TLS succeeds

St. Cloud (city overlay on Osceola parcels, not a county extract):

- [Zoning FeatureServer/2](https://arcgisweb.stcloud.org/arcgis/rest/services/Referenced_Layers/Zoning/FeatureServer/2)
- [Future land use FeatureServer/98](https://arcgisweb.stcloud.org/arcgis/rest/services/Referenced_Layers/Future_Land_Use_Update/FeatureServer/98)

Marion was checked and not seeded: [ParcelsAndSubdivisions/0](https://gis.marionfl.org/public/rest/services/General/ParcelsAndSubdivisions/MapServer/0), [FLU /6](https://gis.marionfl.org/public/rest/services/General/PlanningZoning/MapServer/6) (`PARCELID` join), [Zoning /20](https://gis.marionfl.org/public/rest/services/General/PlanningZoning/MapServer/20). About 17,840 parcels sit in the 5–150 acre band.

## Gaps

- Polk has no zoning or FLU on the DOH extract. Land-use filters should stay on **All parcels** there. Missing zoning is not treated as multifamily. Polk future-land-use polygons were not seeded in this pass.
- Seminole zoning and FLU come from the county Land Use service. A code of `CITY` is the municipal stub. Altamonte Springs and Oviedo replace it. Sanford, Lake Mary, Winter Springs, Longwood, and Casselberry stay `CITY`.
- Lake, Osceola, Seminole, Sumter, and the city overlay codes are displayed, and they are not in `data/zoning-config.json` or `data/flu-config.json`. Multifamily filters treat those codes as unknown rather than inventing a match.
- Lake open data has just value and last tax amount. It does not have assessed value, taxable value, a qualified-sale flag, or a situs city. City FLU layers are not county-wide and are not joined.
- Osceola taxable value is prior-roll `PrevTaxabl`. `EstimatedT` is an estimate, not a certified bill. `Q_U` is stored and is not used to drop sales. A zoning miss uses parcel `Zone1` when that field is set. St. Cloud overrides county zoning and FLU on a matching PIN and is not a county extract.
- Sumter taxable value is not on the SWFWMD layer. The 2026 qualified-sales layer matched 65 of 6,602 parcels in this band; the flag is stored and is not used to drop sales. That layer has no sale date. County zoning and FLU joined in this build. They are omitted when `gis.sumtercountyfl.gov` fails TLS. Tampa’s DOH Sumter tiles are a separate extract.
- Winter Springs EnerGov is Seminole, not Osceola. Lake Mary AGOL is not a Seminole county substitute. Hernando `Zoning_Flu` is the wrong county. The Georgia Sumter parcel service is the wrong state. Edgewood on `maps.etcog.org` is Edgewood, Texas; Edgewood, Florida stays a gap. Orange city overlays (Maitland, Winter Garden, Apopka, Winter Park, Orlando) are a separate change.
- Outside Orange, the OZ 2.0 flag is only the seven-market **rural-eligible** tract pack. Non-rural eligible tracts in those counties are not joined.
- Orange municipal FLU other than Orlando is often the county placeholder `City` and stays unknown. In this 5–150 acre snapshot, 8,238 Orange parcels have a FLU code and 3,471 do not.
- Income and AADT are not stored on the parcel tiles. `/api/parcels` joins ACS B19013 and FDOT AADT at query time for Florida. Block-group income is still Orange County only. Other states stay unknown. Uncheck Include unknown to hide those parcels.
- Orange inclusion uses OCPA `ACREAGE`, including sibling shapes under 5 acres that belong to the same parcel id. Those pieces are summed and the parcel is dropped when the sum is outside 5.0–150.0. Lake, Osceola, and Sumter use the county acreage field the same way. Polk and Seminole still use DOH `LND_SQFOOT`.
- A public ArcGIS Online layer named Polk County parcels is the wrong state (Minnesota). It is not used.
- Brevard’s property-appraiser MapServer has returned HTTP 403 from this environment. The sample uses DOH.
- Brevard, Marion, and Volusia are still windowed samples around rural tracts, not every 5–150 acre parcel. Those samples are not capped at 150 acres. Kissimmee, Clermont, Lakeland, and Sanford city zoning stay follow-ups.
