# Tampa shed parcels

Hillsborough, Pasco, Pinellas, and Polk replace the Florida DOH extract in the Tampa market. Tiles stay on the market-parcel grid (`data/fixtures/market-parcels/counties/{fips}/tiles`, origin longitude -83, latitude 27, 0.25°). Acreage is **5.0–150.0 inclusive**. Orlando tiles are not rewritten. Orange and Osceola stay on the Orlando extract.

```bash
npm run seed:parcels:tampa
python3 scripts/seed_tampa_shed.py --county Hillsborough --refresh
```

City zoning and future land use join onto **county** parcel polygons. A city layer is never treated as a countywide zoning map.

## Sources

| County | FIPS | Parcels | Zoning | Future land use |
| --- | --- | --- | --- | --- |
| Hillsborough | 12057 | ParcelPublishing FeatureServer/12 | Unincorporated RegulatoryZoning/8. Tampa Planning/28. Temple Terrace Zoning/0 (FOLIO). Plant City Zoning/2 | Planning FeatureServer/4, filtered by `JURISDICTION` |
| Pasco | 12101 | PascoMapper Parcels/7 | Landuse_Planning/4 for unincorporated only. New Port Richey WFL1/10 on `HPARCEL`. Zephyrhills Euclidean/4 | Landuse_Planning/1 for unincorporated. New Port Richey WFL1/11. Zephyrhills Euclidean/5. Other city values stay parcel-attribute hints |
| Pinellas | 12103 | PublicWebGIS Parcels/1 | Unincorporated Landuse_Zoning/1. St. Petersburg Zoning/0. Clearwater Zoning_WGS84/1. Dunedin, Pinellas Park, Tarpon Springs, Safety Harbor, Oldsmar, and ten county-hosted city views | Unincorporated Landuse_Zoning/0. St. Petersburg Zoning/2. Clearwater FLU/0. Largo MapServer/1162. City FLU for the five Pinellas cities above. County-hosted views have no city FLU |
| Polk | 12105 | Property_Appraiser MapServer/134 | Lakeland AGOL Zoning/0 only. No countywide districts | County FLU FeatureServer/10 (`FLU_LDC` / `FLUNAME`). Lakeland AGOL Future_Land_Use/0 inside the city |

Pasco `Hosted/County_Master_Property_List/FeatureServer/0` is about 2,266 features. It is recorded under `rejected` and is not the parcel source.

## Municipalities

Each parcel has `municipality`. The drawer and the site list show that label, and the situs city when it is a different place name (Odessa inside unincorporated Hillsborough, Palm Harbor inside unincorporated Pinellas).

Hillsborough `MUNI` was checked against the PIN prefix and situs city. `A` is Tampa, `T` is Temple Terrace, `P` is Plant City, and `U` is unincorporated. City zoning is not taken from the unincorporated atlas. A note that swaps `A` and `T` does not match the live parcels.

Pasco cities (New Port Richey, Port Richey, San Antonio, Dade City, Zephyrhills, St. Leo) are labeled from `JURISDICTION_NAME`. County `ZN_TYPE` values `NPR`, `PR`, `SA`, `DC`, and `ZH` are placeholders and are not stored as zoning districts. New Port Richey uses the city WFL1 zoning and FLU layers (`Zoning2025`, `FLU`) joined on `HPARCEL`, then by centroid. Zephyrhills uses the citywide Euclidean zoning and FLU layers (`CODE`) by centroid. The traditional city center layer is a second citywide map and is not stacked on the Euclidean codes. Port Richey, Dade City, San Antonio, and St. Leo stay hints.

Pinellas uses St. Petersburg, Clearwater, and Largo layers only inside those cities. Dunedin, Pinellas Park, Tarpon Springs, Safety Harbor, and Oldsmar add city zoning and future land use inside those city labels. Pinellas Park joins on `PARCELID` when the city layer has it. Safety Harbor drops `UN`. Oldsmar future land use prefers the Landuse polygons, then the parcel `FLUM` value. The county situs label Oldsmar is wider than those city polygons, so a parcel outside them stays empty. Seminole, South Pasadena, Treasure Island, Kenneth City, North Redington Beach, Indian Shores, Belleair, Indian Rocks Beach, Redington Shores, and Madeira Beach take zoning from the Pinellas County GIS city view. Their city future land use stays empty. The countywide plan map is not copied in as a city FLUM. Gulfport, Belleair Beach, Belleair Bluffs, Redington Beach, and St. Pete Beach stay empty. Unincorporated Landuse_Zoning is not applied inside any of these cities. Largo keeps future land use only. No Largo zoning code is invented from mowing or community-standards layers.

Polk `municipality` is the property-appraiser city. Lakeland zoning and future land use are a spatial join, so a parcel gets them when its polygon falls inside the city layer. A Lakeland situs that misses the city polygon keeps county future land use and an empty zoning code. A few parcels labeled Auburndale or Polk City still receive Lakeland zoning where the city polygon contains them. Winter Haven and the other Polk cities stay on county future land use only.

## Gaps

- **Polk zoning districts.** Land_Use_and_Zoning layers are overlays and FLU categories, not a countywide zoning-district map. Nothing is invented. FLU is not copied into `zoningCode`.
- **Polk sales.** MapServer/134 has no sale fields. `lastSale` is copied from the existing FDOR/DOH Orlando extract when the parcel id matches.
- **Lakeland.** City zoning (`LABEL`) and future land use (`LABEL`) come from `services1.arcgis.com/mcbQY5xNGGGM1vBX` Zoning/0 and Future_Land_Use/0 after the extent checks out inside Florida. The older `gismims.lakelandgov.net` host failed TLS and stays under `rejected`. A Lakeland situs that misses the city polygon keeps county future land use and an empty zoning code.
- **Pinellas market value.** The public parcel layer has taxable, land, and improvement values only. `tax.marketValue` stays null. The property-appraiser site is often Cloudflare-blocked for bots.
- **Pinellas cities still blank.** Gulfport, Belleair Beach, Belleair Bluffs, Redington Beach, and St. Pete Beach have no verified city zoning or future land use layer.
- **Pinellas partials.** The ten county-hosted zoning views are official city zoning. City future land use for those places is still a gap.
- **Largo.** Future land use only. No zoning layer on the city MapServer. Mowing and community-standards layers are not LDC districts.
- **Namesakes not used.** Hernando `Zoning_Flu` (Weeki Wachee), Anderson County CA `Zoning_view`, and Gulfport MS `GPT_Zoning` are the wrong geography.
- **Pasco subset trap.** The hosted master property list is the wrong coverage.
- **Pasco cities still blank.** Port Richey, Dade City, San Antonio, and St. Leo. Parcel `ZONING` / `FUTURELANDUSE` strings there stay hints (`zoningDescription` / FLU source `pasco-parcel-attribute`), not official districts.

Refresh city overlays without downloading county parcels again:

```bash
npm run seed:pinellas-pasco-muni
```
- **Hillsborough VI.** Vacant/improved. It is not stored as a qualified sale.
- **Manatee and Hernando.** Not upgraded in this pass. They remain on the Florida DOH extract.

`AGO/Planning_LandUse` on Pinellas returned a service error in the source card and is not a dependency.
