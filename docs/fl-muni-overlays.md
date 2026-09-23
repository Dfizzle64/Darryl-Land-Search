# Florida city zoning and future land use overlays

Seven city layers are joined onto parcels already on the shelf. The join is the parcel centroid inside that city's limits. Acreage was not re-extracted. A centroid inside the city that misses a zoning or future-land-use polygon stays null.

Checked 2026-09-23. Counts are in `data/fixtures/fl-muni-overlays/summary.json`.

| City | County | Parcels inside | Zoning | FLU | Source |
| --- | --- | ---: | ---: | ---: | --- |
| Sanford | Seminole | 373 | 368 | 368 | City of Sanford `Zoning/MapServer/0` and `Land_Use/FeatureServer/2` |
| Kissimmee | Osceola | 356 | 352 | 352 | City of Kissimmee `Zoning_Districts/MapServer/10` and `Future_Land_Use/MapServer/4` |
| Clermont | Lake | 247 | 212 | 212 | Lake County CityView, Clermont zoning layer 1 and future land use layer 27 |
| Mount Dora | Lake | 144 | 132 | 123 | Lake County CityView, Mount Dora zoning layer 4 and future land use layer 40 |
| Sanibel | Lee | 0 | 0 | 0 | Sanibel GIS ecological zones (LDC Ch. 126 and the FLUM series) |
| Fort Myers | Lee | 0 | 0 | 0 | CFMGIS ArcGIS Online `Zoning1` and `Fort_Myers_Future_Land_Use` |
| Bonita Springs | Lee | 0 | 0 | 0 | Bonita Springs EnerGov `EG_Data_v2` zoning areas and Future Land Use 2040 |

Sanibel, Fort Myers, and Bonita Springs layers were geo-checked in Florida. Lee County (FIPS 12071) has no parcel polygons on this shelf, so there is nothing to stamp. That is not a filled zoning code.

## Not used

- `gis.fortmyers.gov` failed TLS on an earlier pass. Fort Myers uses the CFMGIS ArcGIS Online path.
- Lee County Property Appraiser zoning layer 4 is a county copy of Fort Myers, not the city service.
- Lee County `Future Land Use BS` is the county stub. Bonita Springs uses the city EnerGov layers instead.
- Edgewood, Texas is a wrong-state namesake and is rejected. Situs strings for Bonita, North Carolina, Fort Myers, South Carolina, and Doraville, Georgia are not city-limit matches.

## Left null

Pensacola is still an HTTP 523 gap. No zoning was invented for it. Municipal rows other than the seven cities above stay null, including the rest of Lake, Osceola, Seminole, and Polk.

Refresh:

```bash
npm run seed:fl-muni
```
