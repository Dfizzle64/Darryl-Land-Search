# Polk County municipal zoning and future land use

Parent county FIPS **12105**. This pass stamps city zoning and future land use onto the existing Orlando 5.0–150.0 acre tiles. It does not download a new parcel shelf. Parcel ids, acreage, geometry, and Opportunity Zone fields are unchanged.

Refresh: `npm run seed:polk-municipal`

Catalog: `data/polk-municipal.json`. Join report: `data/fixtures/polk-municipal-join.json`.

On the 19,734 parcels already on the shelf, zoning is filled on 1,696 and future land use on 1,735.

| City | Join | Zoning parcels | FLU parcels | Source |
| --- | --- | ---: | ---: | --- |
| Lakeland | Centroid inside the city polygon | 795 | 815 | AGOL `Zoning/0` `LABEL`, `Future_Land_Use/0` `LABEL` |
| Bartow | `Parcel_Id`, then centroid | 318 | 318 | `Bartow_Zoning_8_25_2026/1` `ZON`, `Bartow_Future_Land_Use_8_25_2026/2` `FLU` |
| Auburndale | `PARCELID` when it is a 15-digit-or-longer Polk id, then centroid | 262 | 281 | `Auburndale_Zoning/3` `ZN_ABREV`, `Auburndale_FLU/0` `FLU_ABREV` |
| Lake Alfred | `Parcel_Id`, then centroid | 173 | 173 | `Lake_Alfred_Zoning/0` `ZON` and `FLU` |
| Lake Hamilton | `Parcel_Id`, then centroid | 148 | 148 | CFRPC `Lake_Hamilton_Zoning/0` `ZON`, `Lake_Hamilton_Future_Land_Use/0` `FLU` |

Future land use stays on the same city that supplied zoning. A neighbor city does not fill a miss.

## Left blank

Polk County does not publish an LDC zoning-district polygon. County `FLUNAME` is not copied into `zoningCode`. County future land use (`PublicViewer/Map_Land_Use_and_Zoning/MapServer/9`) is not stamped.

These cities are not wired:

| City | Why |
| --- | --- |
| Winter Haven | Gridics only. No public FeatureServer. |
| Haines City | Inquiry form and a 2019 PDF. |
| Davenport | Zoning map PDFs. |
| Fort Meade | No public zoning or future land use service. |
| Dundee | The CFRPC `Dundee_FLU` service is gone. |
| Eagle Lake | No city service. |
| Frostproof | No city zoning or future land use service. |
| Mulberry | No Polk County service. |
| Polk City | No Polk County service. |
| Hillcrest Heights | No service. |
| Highland Park | No Polk County service. |
| Lake Wales | AGOL requires a token. The city site publishes PDFs. |

Auburndale `POLK_FLU` is a county stub and is not stored. Auburndale `NO ZONING INSIDE CITY` is the city's empty value and is left blank. Short Auburndale ids such as `10` are not treated as Polk parcel ids. `NA` on Bartow and Lake Hamilton is the published new-annex code, not a guessed district. Lake Alfred's June 2025 ULDC layer (`Planning_WFL1`, `ZON_20` / `FLU_20`) is not wired, so those codes are not mixed with the Ord. 742 codes.

## Rejected namesakes

| Candidate | Why |
| --- | --- |
| `Polk_City_Zoning_VIEW` | Polk City, Iowa |
| `HP_Zoning` | Highland Park, New Jersey |
| `City_of_Mulberry_Zoning` | Mulberry, Georgia |
| `bartowgis.org` BartowZoning | Bartow County, Georgia |
| Dundee LEZ / housing layers | Dundee, Scotland |
| AGOL Polk County Parcels | Minnesota extent. Already rejected as a parcel source. |
