# Treasure Coast parcels

Vero Beach and Melbourne load these counties from public GIS. The acreage band is **5.0–150.0** inclusive. City zoning and future land use come from that city's layer. A county layer fills unincorporated land and is not copied onto a city that does not publish one.

Eligible OZ 2.0 tracts are nomination geography. They are not designated QOZs. Layers named Opportunity Zone are not joined onto parcels.

Orlando's own Brevard sample is unchanged. These tiles are the market-parcel extract.

## What shipped

| County | Parcels | Zoning joined | FLU joined | Source |
| --- | ---: | ---: | ---: | --- |
| Indian River | 3,779 | 3,619 | 3,622 | Property appraiser parcels. Vero Beach and Sebastian use city layers. |
| St. Lucie | 5,585 | 5,320 | 5,399 | County parcel boundaries. Fort Pierce layer 7 and Port St. Lucie city layers. |
| Brevard | 6,802 | 3,809 | 3,813 | Accela parcels. Zoning and FLU are unincorporated only. |
| Martin | 3,790 | 3,712 | 3,461 | Geoweb county roll. Stuart and Indiantown zoning are city/village layers. |
| Okeechobee | 3,053 | 3,010 | 3,046 | County planning parcels. Acres are computed from the polygon. |

Every kept parcel is inside 5.0–150.0 acres. Centroids fall in the Florida county, not Tuscaloosa, Ocoee, or Australia.

## Wire order

1. **Indian River** — property appraiser parcels on `gisportal.ircgov.com` (`IRCPA/Parcels_MS`). Unincorporated zoning and FLU are the planning MapServers. Vero Beach and Sebastian use the city FeatureServers. Fellsmere, Indian River Shores, and Orchid are on the municipal boundary layer and have no public zoning or FLU service.
2. **St. Lucie** — `slcgis.stlucieco.gov` parcel boundaries, plus the county parcel-level zoning and FLU MapServers for unincorporated land. Fort Pierce zoning is FeatureServer layer 7. Port St. Lucie zoning is `PZ_ZONING` and FLU is `PZ_LandUse`. St. Lucie Village has no public zoning or FLU service.
3. **Brevard Accela** — `gis.brevardfl.gov` Accela parcels, zoning, and future land use. The City polygon on the General map names incorporated places. Accela zoning does not cover downtown Melbourne, so it is unincorporated only. Palm Bay, Melbourne, Titusville, Cocoa, and the other cities on that layer have no separate public zoning service in this pull.
4. **Martin** — `geoweb.martin.fl.us` parcel polygons (base map layer 10) and future land use / zoning. Stuart uses the city zoning service. Indiantown uses the village zoning service. Jupiter Island, Sewall's Point, and Ocean Breeze have no public zoning service. County values that are only a town name are stubs.
5. **Okeechobee** (optional, included) — county planning `Parcels_2022`, zoning, and future land use. The extent is Okeechobee County. Acres are computed from the polygon because the layer has no acreage field. The City of Okeechobee is not split out.

## Rejected

| Trap | Why it is not used |
| --- | --- |
| Tuscaloosa IRC AGOL | An IRC layer whose extent is Tuscaloosa County, Alabama is not Indian River County, Florida. |
| Ocoee | `maps.ocoee.org` is the City of Ocoee in Orange County, not Okeechobee County. |
| Martin thin AGOL clip | An Indiantown-sized parcel extract is not the county roll. Martin parcels are the geoweb county layer. |
| Fort Pierce Zoning/0 | Layer 0 is Current Project Development (project points). Zoning is layer 7. Layer 9 is an opportunity-zone overlay and is not a designation. |
| Australian Melbourne | Melbourne, Victoria is not Melbourne in Brevard County. Accela's extent is the Florida county. |

County `county.json` files repeat the reject note and the join gaps. Refresh with:

```bash
python3 scripts/seed_market_parcels.py --county "Indian River" --refresh --workers 1
python3 scripts/seed_market_parcels.py --county "St. Lucie" --refresh --workers 1
python3 scripts/seed_market_parcels.py --county Brevard --refresh --workers 1
python3 scripts/seed_market_parcels.py --county Martin --refresh --workers 1
python3 scripts/seed_market_parcels.py --county Okeechobee --refresh --workers 1
```
