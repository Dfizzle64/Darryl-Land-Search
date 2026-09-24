# Stokes County, North Carolina (37169)

Winston-Salem market. Public GIS only. Acreage band is **5.0–150.0** on county `CALCULATED_ACREAGE`.

Kept **8,844** parcels from AllLayers/MapServer/24 (`nc-stokes-alllayers-24`).

## Sources

| Role | Service | Page size |
| --- | --- | ---: |
| Parcels | `https://stokescountygis.com/server/rest/services/AllLayers/MapServer/24` | 2000 |
| Zoning | `https://stokescountygis.com/server/rest/services/AllLayers/MapServer/27` | 2000 |
| Land Use 2035 | `https://stokescountygis.com/server/rest/services/WebApp2026/MapServer/34` | 2000 |
| King QA | `https://www.webgis.net/arcgis/rest/services/NC/CityOfKing/MapServer/7` | 1000 |
| OneMap QA | `https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1/query` `cntyfips='169'` | 2000 |

Eligible OZ 2.0 tracts come from `data/fixtures/oz2-eligible-packs.geojson` (Rev. Proc. 2026-14). They are not designated. Designated tracts come from the HUD Opportunity Zones service (2010 census geography). Notice 2025-50 only flags whether a designated tract is rural.

## Gaps

- OZ 2.0 eligibility is not a designated QOZ. Rev. Proc. 2026-14 tracts 37169070101, 37169070302 stay on oz2Eligibility as eligible-for-nomination. Designated status is only the HUD 2010 join (37169070501). 1596 centroids are eligible; 285 are in a current designated tract; 0 sit in both geographies with different GEOIDs.
- Stored acreage is Stokes CALCULATED_ACREAGE (GIS), the same figure NC OneMap publishes as gisacres. DEEDED_ACREAGE in the numeric 5–150 band is 9,026 and is not the filter. County query returned 8,865 rows; 8,844 unique PINs were kept. The other 21 rows were duplicate PINs or failed the ring or centroid check.
- Zoning is AllLayers/MapServer/27 (page size 2000), joined by centroid. 8,839 hit a polygon; 5 did not and kept the assessor ZONING field when it was present. 121 assessor codes disagree with the polygon; the polygon wins. 60 blank assessor codes were filled from the polygon. Stokes codes are not in the Orange County multifamily zoning knowledge base.
- Future land use is WebApp2026/MapServer/34 Land Use 2035 (requested page size 2000). Ungeneralized geometry pages above about 200 features return HTTP 500, so the polygons are simplified with maxAllowableOffset 0.00008 degrees (about 8 meters) before the centroid join. This is not a separate municipal FLU layer. 8,831 centroids hit a polygon; 13 have no FLU. King, Walnut Cove, Danbury, and other towns do not have a separate public FLU service wired here.
- City of King WebGIS CityOfKing/MapServer/7 is a QA crosswalk, not the county roll. Its maxRecordCount pages at 1000 (the service cap; below the 2000 used for county layers). 197 King rows are Stokes and inside 5–150 calculated acres; 197 match a county PIN; 0 do not; 31 zoning codes disagree. 388 Forsyth County parcels on that layer are excluded.
- NC OneMap cntyfips='169' and gisacres 5–150 is a QA crosswalk (page size 2000), not the geometry source. OneMap count 8,847 (8,826 unique parnos); 121 county PINs are absent there; 103 OneMap parnos are absent from the county extract; 79 shared PINs differ by more than 0.05 acres.
- No public Stokes parcel-search deep link was confirmed, so appraiserUrl is empty. LAND_CLASS is not a Florida DOR use code. Sale qualification is not on the county layer. Income and traffic are not joined. County parcel pages use resultOffset at 2000, the AllLayers maxRecordCount.
