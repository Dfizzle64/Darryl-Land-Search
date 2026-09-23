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
| Pasco | 12101 | PascoMapper Parcels/7 | Landuse_Planning/4 for unincorporated only | Landuse_Planning/1 for unincorporated. City values stay parcel-attribute hints |
| Pinellas | 12103 | PublicWebGIS Parcels/1 | Unincorporated Landuse_Zoning/1. St. Petersburg Zoning/0. Clearwater Zoning_WGS84/1 | Unincorporated Landuse_Zoning/0. St. Petersburg Zoning/2. Clearwater FLU/0. Largo MapServer/1162 |
| Polk | 12105 | Property_Appraiser MapServer/134 | Lakeland AGOL Zoning/0 only. No countywide districts | County FLU FeatureServer/10 (`FLU_LDC` / `FLUNAME`). Lakeland AGOL Future_Land_Use/0 inside the city |

Pasco `Hosted/County_Master_Property_List/FeatureServer/0` is about 2,266 features. It is recorded under `rejected` and is not the parcel source.

## Municipalities

Each parcel has `municipality`. The drawer and the site list show that label, and the situs city when it is a different place name (Odessa inside unincorporated Hillsborough, Palm Harbor inside unincorporated Pinellas).

Hillsborough `MUNI` was checked against the PIN prefix and situs city. `A` is Tampa, `T` is Temple Terrace, `P` is Plant City, and `U` is unincorporated. City zoning is not taken from the unincorporated atlas. A note that swaps `A` and `T` does not match the live parcels.

Pasco cities (New Port Richey, Port Richey, San Antonio, Dade City, Zephyrhills, St. Leo) are labeled from `JURISDICTION_NAME`. County `ZN_TYPE` values `NPR`, `PR`, and `SA` are placeholders and are not stored as zoning districts.

Pinellas uses St. Petersburg, Clearwater, and Largo layers only inside those cities. Other incorporated places stay labeled and do not receive the unincorporated zoning layer.

Polk `municipality` is the property-appraiser city. Lakeland zoning and future land use are a spatial join, so a parcel gets them when its polygon falls inside the city layer. A Lakeland situs that misses the city polygon keeps county future land use and an empty zoning code. A few parcels labeled Auburndale or Polk City still receive Lakeland zoning where the city polygon contains them. Winter Haven and the other Polk cities stay on county future land use only.

## Gaps

- **Polk zoning districts.** Land_Use_and_Zoning layers are overlays and FLU categories, not a countywide zoning-district map. Nothing is invented. FLU is not copied into `zoningCode`.
- **Polk sales.** MapServer/134 has no sale fields. `lastSale` is copied from the existing FDOR/DOH Orlando extract when the parcel id matches.
- **Lakeland.** City zoning (`LABEL`) and future land use (`LABEL`) come from `services1.arcgis.com/mcbQY5xNGGGM1vBX` Zoning/0 and Future_Land_Use/0 after the extent checks out inside Florida. The older `gismims.lakelandgov.net` host failed TLS and stays under `rejected`. A Lakeland situs that misses the city polygon keeps county future land use and an empty zoning code.
- **Pinellas market value.** The public parcel layer has taxable, land, and improvement values only. `tax.marketValue` stays null. The property-appraiser site is often Cloudflare-blocked for bots.
- **Pinellas cities.** Dunedin, Pinellas Park, Seminole, Tarpon Springs, Safety Harbor, the beach towns, and the other incorporated places in the parcel city list have no verified zoning/FLU FeatureServer.
- **Largo.** Future land use only. No zoning layer on the city MapServer.
- **Pasco subset trap.** The hosted master property list is the wrong coverage.
- **Pasco cities.** No verified city zoning/FLU FeatureServer. Parcel `ZONING` / `FUTURELANDUSE` strings are hints (`zoningDescription` / FLU source `pasco-parcel-attribute`), not official districts.
- **Hillsborough VI.** Vacant/improved. It is not stored as a qualified sale.
- **Manatee and Hernando.** Not upgraded in this pass. They remain on the Florida DOH extract.

`AGO/Planning_LandUse` on Pinellas returned a service error in the source card and is not a dependency.
