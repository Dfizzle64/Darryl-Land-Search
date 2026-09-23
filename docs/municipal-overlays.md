# Orange County municipal zoning and FLU

Orange County parcels stay on the 5.0–150.0 acre DOH extract. OCPA remains the appraiser deep-link. When a parcel matches a city layer, the drawer shows that city’s zoning and future land use instead of the county code.

County AGOL zoning layer 51 is not used for city district codes. Municipal rows there are mostly `ZONING=CITY` stubs.

The join prefers a parcel id (`PARCEL`, with or without the `12095-` prefix). If the id misses, the parcel centroid is tested against the city polygons. A city match with a blank district does not fall back to the county code. Acreage, owner, sale, and tax are left on the county record. City layers are not scraped for names, mailing addresses, or tax values.

Refresh with `npm run seed:municipal`. Each layer is checked before download: the sample centroid has to fall in Florida and in Orange County. A bbox outside Florida is dropped and is not applied at read time.

## Wired

| City | Join | Zoning | FLU |
| --- | --- | --- | --- |
| Winter Garden | Parcel id `PARCEL` | [FLU_New/2](https://services6.arcgis.com/dUj2ew1ea9QOFR6u/arcgis/rest/services/FLU_New/FeatureServer/2) `ZONING_COD` | same layer `FLU_2025_W` |
| Ocoee | Parcel id `PARCELID` (not the alternate `PIN`), then district polygons | [Zoning_District_2026/0](https://maps.ocoee.org/arcgis/rest/services/Zoning_District_2026/FeatureServer/0) | [LandUse/1](https://maps.ocoee.org/arcgis/rest/services/LandUse/MapServer/1) |
| Apopka | Centroid | [Apopka_Zoning_view/8](https://services.arcgis.com/syn8rfJ2eTAK0T6k/arcgis/rest/services/Apopka_Zoning_view/FeatureServer/8) | [Apopka_FLUM_Data/1](https://services.arcgis.com/syn8rfJ2eTAK0T6k/arcgis/rest/services/Apopka_FLUM_Data/FeatureServer/1) |
| Maitland | Parcel id `PARCEL` | [Maitland_Zoning_AppLayer/2](https://services8.arcgis.com/q4Vpy7r3KXnWcTBW/arcgis/rest/services/Maitland_Zoning_AppLayer/FeatureServer/2) `New_Zoning` | [Future_Land_Use_public/6](https://services8.arcgis.com/q4Vpy7r3KXnWcTBW/arcgis/rest/services/Future_Land_Use_public/FeatureServer/6) `F2018FLU` |
| Winter Park | Centroid | [PublicAccess/6](https://gis.cityofwinterpark.org/arcgis/rest/services/PublicAccess/MapServer/6) | [PublicAccess/7](https://gis.cityofwinterpark.org/arcgis/rest/services/PublicAccess/MapServer/7) |
| Orlando | Centroid | [OrlandoLandUsePlanning/7](https://gis.orlando.gov/server/rest/services/Socrata_OpenData/OrlandoLandUsePlanning/MapServer/7) | [OrlandoLandUsePlanning/3](https://gis.orlando.gov/server/rest/services/Socrata_OpenData/OrlandoLandUsePlanning/MapServer/3) |
| Eatonville | Centroid | [InfoMap/137](https://ocgis4.ocfl.net/arcgis/rest/services/InfoMap_Public_Layers/MapServer/137) | [InfoMap/102](https://ocgis4.ocfl.net/arcgis/rest/services/InfoMap_Public_Layers/MapServer/102) |

Ocoee’s parcel layer is [ParcelsFLUZoning/0](https://maps.ocoee.org/arcgis/rest/services/ParcelsFLUZoning/MapServer/0). District polygons fill a row when `ZONECLASS` is blank.

The catalog is `data/municipal-overlays.json`. Fixtures are `data/fixtures/municipal-overlays/*.json`. The same registry shape can take another city later: status, prefix, layer URLs, and a fixture. Gap cities are listed and not fetched.

## Gaps

| City | Why it is not joined |
| --- | --- |
| Edgewood | PDF zoning map only ([edgewood-fl.gov](https://edgewood-fl.gov/planning/page/zoning-map)). County layer 51 is 18 `ZONING=CITY` stubs, not LDC districts. |
| Windermere | No public zoning or FLU service. County rows are `CITY` stubs. |
| Belle Isle | Boundary and parcel PDFs only. County rows are `CITY` stubs. |
| Oakland | No public REST for the Town of Oakland, Florida. |
| Bay Lake | No public city zoning or FLU service. |
| Lake Buena Vista | No public city zoning or FLU service. |

### Rejected: Edgewood, Texas

`https://maps.etcog.org/arcgis/rest/services/EDGEWOOD/EdgewoodZoning_Public/FeatureServer/4` is the East Texas Council of Governments. A sample centroid is about (-95.88, 32.68). It is not the City of Edgewood, Florida, and it is not downloaded or applied.

## Not in this overlay

Polk’s public land-use service is Future Land Use 2030, not an LDC zoning-district layer. Seminole’s shed extract still has no countywide zoning/FLU join in this app. Sumter remains a thinner DOH sample. Those counties are unchanged here.
