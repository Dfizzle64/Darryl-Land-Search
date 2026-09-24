# Municipal zoning, future land use, and screening overlays

This pass stamps city zoning, future land use, and a small set of school, flood, and utility joins onto parcels that are already on the shelf. It does not add a new county parcel extract. Opportunity Zone designation is not written from an eligible tract, and no school letter grade or base flood elevation is invented.

Refresh commands:

```bash
npm run seed:volusia-flagler-municipal
npm run seed:polk-municipal
npm run seed:pinellas-pasco-muni
npm run seed:seminole-municipal
npm run seed:martin-irc-municipal
npm run seed:brevard-municipal
npm run seed:manatee-sarasota-municipal
npm run seed:charlotte-municipal
npm run seed:panhandle-municipal
npm run seed:sc-muni
```

`npm run seed:sc-muni` also downloads Berkeley, Charleston, and Greenville County parcel shelves before it joins zoning. Those shelves are not in this checkout. Run that command only when those extracts are meant to land. Dorchester was joined here without adding or dropping parcels.

## Cobb County, Georgia (FIPS 13067) — batch-40 screening

Join: parcel id from `data/fixtures/screening/cobb-batch40.json` when the county is 13067. Applied when the parcel loads and when the drawer screens it. Other Cobb parcels stay on the live lookup. Forty parcels.

| Theme | Source | Result |
| --- | --- | --- |
| Schools | Cobb County School District attendance zones (`ccsdschoolzonemapwm` layers 0–2) and Marietta City Schools assignment. Scores are GOSA 2025 CCRPI single scores. | 38 CCSD, 2 Marietta. No A–F letter. |
| Flood | FEMA NFHL at the centroid. `STATIC_BFE` only when it is a real number. | 28 Zone X, 11 Zone AE, 1 Zone A. Static BFE on 3 parcels, all 861 ft NAVD88. |
| Water | Cobb service-boundary polygons. CCWS is the documented jurisdiction where no city polygon hits. | 35 CCWS, 1 former Powder Springs CCWS boundary, 2 Marietta, 1 Austell, 1 Dobbins ARB. |
| Sewer | Same service boundaries, plus sewer-not-anticipated polygons. | 31 CCWS, 2 Marietta collection / CCWS treatment, 1 Austell collection / CCWS treatment, 1 Dobbins ARB, 5 gaps. |
| Electric | HIFLD retail territories. One name is kept when territories overlap. | 22 Cobb EMC, 10 Georgia Power, 7 Marietta BLW, 1 Greystone Power. |
| Gas | No public gas service-area polygon. | Unknown on all 40. |

The five sewer gaps are `18000800010`, `20004100010`, `20004300010`, `20008000010`, and `20011000290`.

## DeKalb County, Georgia (FIPS 13089) — batch-40 screening

Join: parcel id from `data/fixtures/screening/dekalb-batch40.json` when the county is 13089. City zoning and future land use on the DeKalb shelf were already joined in the county extract (Decatur, Brookhaven, Dunwoody, Doraville, Tucker, Stonecrest, Atlanta inside DeKalb, Chamblee future land use only). This pass does not replace that shelf. Stone Mountain, Avondale Estates, Clarkston, Lithonia, and Pine Lake stay blank. Forty parcels get screening fields.

| Theme | Source | Result |
| --- | --- | --- |
| Schools | DeKalb County School District FeatureServers (elementary, middle, high). There is no MapServer export. Scores are GOSA 2025 CCRPI. | 40 DCSD. Two City of Atlanta parcels still zone to Druid Hills because the DCSD polygons cover them, not Atlanta Public Schools. No A–F letter. |
| Flood | FEMA NFHL. No published static BFE on these centroids. | 31 Zone X (one is the 0.2% annual-chance subtype), 9 Zone AE (five are floodway). No BFE stored. |
| Water and sewer | No DWM service-area polygon. Names are a jurisdiction proxy, not a connection. | 38 DeKalb DWM, 2 City of Atlanta DWM (the Atlanta parcels inside DeKalb). |
| Electric | HIFLD. A cooperative is kept when it overlaps Georgia Power. | 28 Georgia Power, 10 Snapping Shoals EMC, 2 Walton EMC. |
| Gas | No public gas service-area polygon. | Unknown on all 40. |

## Volusia and Flagler, Florida

Catalog: `data/volusia-flagler-municipal.json`. Join: parcel centroid inside the city polygon, onto parcels already in the app. Flagler (FIPS 12035) has no parcel baseline here, so those layers are cataloged and not stamped onto a new county download. Details and the partial cities are in `docs/volusia-flagler-municipal.md`.

The Melbourne shelf (12,567 Volusia parcels) now has zoning on 2,942 parcels and future land use on 1,914. The Orlando-shed Volusia sample (120 parcels in one file) has zoning on 79 and future land use on 58. Parcel ids, acreage, and Opportunity Zone fields were not changed. Flagler layers were indexed and stamped onto zero parcels because FIPS 12035 is not on the shelf.

| City | Zoning parcels | FLU parcels |
| --- | ---: | ---: |
| Daytona Beach | 473 | 473 |
| Ormond Beach | 394 | 347 |
| Pierson | 319 | 0 |
| Deltona | 279 | 277 |
| New Smyrna Beach | 259 | 0 |
| DeLand | 255 | 265 |
| Port Orange | 235 | 234 |
| Edgewater | 142 | 133 |
| Lake Helen | 133 | 0 |
| DeBary | 130 | 0 |
| Oak Hill | 126 | 102 |
| Orange City | 111 | 0 |
| South Daytona | 28 | 28 |
| Ponce Inlet | 28 | 28 |
| Holly Hill | 27 | 27 |
| Daytona Beach Shores | 3 | 0 |

Palm Coast, Flagler Beach, Bunnell, Marineland, Beverly Beach, and unincorporated Flagler are on the Palm Coast host and were not stamped. Pierson, New Smyrna Beach, Lake Helen, DeBary, and Orange City use the CountywideZoning `OriginalZoningCode` bridge only, so future land use stays empty. Daytona Beach Shores is zoning only. Rejected: Seattle future land use, Volusia Open Data zoning layer 36 (`ZONCODE` 999), and DeBary MapServer 21 as a future land use source.

## Polk County, Florida (FIPS 12105)

Catalog: `data/polk-municipal.json`. Details: `docs/polk-municipal.md`. Join: parcel id when the city layer carries a Polk id, otherwise the parcel centroid, onto the existing 19,734 Orlando tiles. No new county shelf. County LDC zoning districts are still a gap. County `FLUNAME` is not copied into zoning, and county future land use is not stamped.

| City | Zoning parcels | FLU parcels |
| --- | ---: | ---: |
| Lakeland | 795 | 815 |
| Bartow | 318 | 318 |
| Auburndale | 262 | 281 |
| Lake Alfred | 173 | 173 |
| Lake Hamilton | 148 | 148 |

Winter Haven, Haines City, Davenport, Fort Meade, Dundee, Eagle Lake, Frostproof, Mulberry, Polk City, Hillcrest Heights, and Highland Park stay blank. Lake Wales is token-blocked. Rejected namesakes: Iowa Polk City, New Jersey Highland Park, Georgia Mulberry, the Georgia Bartow GIS host, and UK Dundee. Auburndale `POLK_FLU` and `NO ZONING INSIDE CITY` are not stored. Lake Alfred's June 2025 ULDC layer is not mixed in with the Ord. 742 codes.

## South Carolina municipal zoning

Script: `scripts/sc_muni_zoning.py`. City layers win over county layers. The inclusive 5–150 acre band is unchanged. Eligible tracts are not written as designated Opportunity Zones.

Shipped in this checkout:

| Place | County | Join | Gap |
| --- | --- | --- | --- |
| Summerville | Dorchester | Town `Zone_Class` filtered to County=DORCHESTER, on TMS, over the county code | 253 parcels. No future land use layer |
| Dorchester County | Dorchester | `ZONINGCODE` on the existing Parcels_Public set | 6,519 parcels. 6,772 of 6,774 have a zoning code. No FLU. Parcel ids and acreage were not changed |

Wired in the seed script and not downloaded here (those shelves belong with the county-parcel batch):

| Place | County | Join method when the seed is run | Gap |
| --- | --- | --- | --- |
| Goose Creek, Hanahan, Moncks Corner, Summerville | Berkeley | Attribute join on `O_TMS` | No field-mapped FLU |
| Berkeley County | Berkeley | County layer where no city hits | No FLU |
| Folly Beach, Summerville, Charleston, North Charleston, Mount Pleasant | Charleston | PID or spatial city layers | — |
| Isle of Palms | Charleston | District services only | Partial. PDD not joined |
| Charleston County | Charleston | Remainder, not on Sullivan's Island, James Island, or Isle of Palms | — |
| Sullivan's Island, James Island | Charleston | — | No usable REST |
| Fountain Inn, City of Greenville, Greer | Greenville | Spatial or attribute city layers on county parcels | Fountain Inn has no city FLU |
| Mauldin, Simpsonville, Travelers Rest | Greenville | County JCODE only | No city REST. Simpsonville AGOL is Shelby County, Tennessee and is rejected |
| Greenville County | Greenville | Unincorporated county zoning | — |

Berkeley and Charleston stay coverage gaps (0 parcels). Greenville stays the city-GIS sample (1,570 parcels, `sc-greenville-city-gis`). Laurens-side Fountain Inn and Spartanburg-side Greer are not joined.

Rejected and not queried: SimpsonvilleZoning AGOL, Fountain Inn `ZoningFireSewer/2`, the Fountain Inn consultant swipe map, Sullivan's Island unofficial `Zoning_2025`, the Folly Beach CofC alternate, the AGOL Greenville base-data subset, and the Isle of Palms PDD service.

## Pinellas and Pasco, Florida

Catalog: `data/pinellas-pasco-municipal.json`. Join script: `scripts/pinellas_pasco_muni.py`. Stamped onto the existing Florida DOH 5–150 acre shelves (`fl-doh-ehwaters-12103`, 18,638 parcels; `fl-doh-ehwaters-12101`, 10,590 parcels). County parcels were not re-downloaded, and the Tampa shed re-extract is not in this pull request. Join is the city parcel id when it matches the DOH strap, otherwise a point inside the parcel. Opportunity Zone fields were not written.

Pinellas now has zoning on 3,901 parcels and future land use on 3,211. Pasco has zoning on 142 and future land use on 140. A situs city on this acreage band is often wider than the municipal polygon, so a miss stays blank.

| City | County | Zoning parcels | FLU parcels |
| --- | --- | ---: | ---: |
| Dunedin | Pinellas | 809 | 812 |
| Pinellas Park | Pinellas | 1,570 | 1,570 |
| Tarpon Springs | Pinellas | 708 | 707 |
| Safety Harbor | Pinellas | 43 | 49 |
| Oldsmar | Pinellas | 71 | 73 |
| Seminole | Pinellas | 665 | 0 |
| South Pasadena | Pinellas | 12 | 0 |
| Treasure Island | Pinellas | 7 | 0 |
| Kenneth City | Pinellas | 3 | 0 |
| Indian Shores | Pinellas | 2 | 0 |
| Belleair | Pinellas | 4 | 0 |
| Indian Rocks Beach | Pinellas | 2 | 0 |
| Madeira Beach | Pinellas | 5 | 0 |
| New Port Richey | Pasco | 34 | 34 |
| Zephyrhills | Pasco | 108 | 106 |

North Redington Beach is on the county zoning view and has no situs parcels in this acreage band. Redington Shores is on that view too; its two situs parcels do not intersect the zoning polygons. Seminole through Madeira Beach are county zoning only. City future land use stays blank, and the countywide plan map is not stored.

Largo zoning is a gap. Largo future land use is not on this shelf and was not invented. Gulfport, Belleair Beach, Belleair Bluffs, Redington Beach, and St. Pete Beach stay blank. St. Petersburg and Clearwater stay blank here; their city layers were not copied from the Tampa parcel re-extract. Port Richey, Dade City, San Antonio, and St. Leo stay blank. Zephyrhills uses the Euclidean layers only. The traditional city center layer is not stacked. County `ZN_TYPE` placeholders `NPR`, `PR`, `SA`, `DC`, and `ZH` are not stored.

Rejected and not queried: Hernando `Zoning_Flu` (Weeki Wachee), Anderson County, California `Zoning_view`, and Gulfport, Mississippi `GPT_Zoning`.

## Seminole County, Florida (FIPS 12117)

Catalog: `data/seminole-municipal.json`. Join script: `scripts/join_seminole_municipal.py`. Stamped onto the existing Orlando DOH shelf (`doh-ehwaters`, 4,788 parcels, 5–150 acres). County parcels were not re-downloaded. Casselberry joins on `PARCEL` and Winter Springs on `PIN`, then a point inside the parcel. Lake Mary, Sanford, Oviedo, and Altamonte Springs are spatial. Opportunity Zone fields were not written.

| City | Zoning parcels | FLU parcels |
| --- | ---: | ---: |
| Casselberry | 68 | 63 |
| Winter Springs | 147 | 144 |
| Lake Mary | 132 | 131 |
| Sanford | 369 | 369 |
| Oviedo | 145 | 144 |
| Altamonte Springs | 140 | 140 |

Shelf totals: zoning 1,001, future land use 991. A situs city on this acreage band is often wider than the municipal polygon, so a miss stays blank.

Longwood stays blank. County `Land_Use` FeatureServer 0 and 1 are not stamped. `CITY` and Casselberry `SEMINOLE COUNTY` are not stored. Geneva, Chuluota, and the other unincorporated labels stay blank, as do Winter Park, Apopka, and Maitland. Oviedo uses `maps.cityofoviedo.net` DevelopmentServices MapServer 11 and 10. The retired AGOL `DSZoning` service is not called. Winter Springs EnerGov, the Lake Mary twin layers, and Sanford `Land_Use` MapServer 0 are not stacked.

Rejected and not queried: Hernando `Zoning_Flu`, Lake County InteractiveMap zoning, Winter Park EnerGov, the FDOR `Zoning` product, and the Longwood giswebtechguru host.

## Martin County and Indian River County, Florida (FIPS 12085 and 12061)

Catalog: `data/martin-irc-municipal.json`. Join script: `scripts/join_martin_irc_municipal.py`. Stamped onto the existing Florida DOH shelves (`fl-doh-ehwaters-12085`, 3,802 parcels; `fl-doh-ehwaters-12061`, 3,416 parcels; both 5–150 acres). County parcels were not re-downloaded. Stuart joins on `PCN` when that key matches a DOH parcel id, otherwise a point inside the parcel. Indiantown, Vero Beach, and Sebastian are spatial. Opportunity Zone fields were not written.

| Place | Situs parcels | Zoning | Future land use |
| --- | ---: | ---: | ---: |
| Stuart | 488 | 109 | 107 |
| Indiantown | 780 | 94 | 94 |
| Ocean Breeze | 2 | 0 | 0 |
| Vero Beach | 2,303 | 104 | 104 |
| Sebastian | 228 | 87 | 0 |

Shelf totals: Martin zoning 203 and future land use 201; Indian River zoning 191 and future land use 104. A situs city on this acreage band is often wider than the municipal polygon, so a miss stays blank.

Stuart zoning is `COS_Zoning` and future land use is `Future_Land_Use` (`LAND_USE`). The dissolved `ZoningMerged` and `Zoning_Parcels` twins are not stacked. `COUNTY` on the Stuart future land use layer is not stored. Indiantown uses the village layers `voi_zoning_public` and `voi_flu_public`. County zoning inside the village is not copied in.

Vero Beach zoning is `ZoningDistricts` and future land use is `ZoningFutureLandUse`. A shared abbreviation such as `GU` still comes from those two layers. The token-gated Indian River `COVB` folder is not called. Sebastian zoning is `COS/COS_Zoning`. Sebastian future land use is still a gap.

Ocean Breeze has no city service. The Martin County zoning and future land use maps were checked only at those two parcels. Both hits were the town-name stub or `NO DATA`, so nothing was stored. Sewall's Point, Jupiter Island, Fellsmere, Indian River Shores, and Orchid stay blank. County labels `JUPITER ISLAND`, `SEWALLS POINT`, `OCEAN BREEZE`, and `INDIANTOWN` are not districts.

Rejected and not queried: Ocoee `ParcelsFLUZoning`, Palm Beach County zoning, and ClearviewGeographic stacks.

## Brevard County, Florida (FIPS 12009)

Catalog: `data/brevard-municipal.json`. Join script: `scripts/join_brevard_municipal.py`. Stamped onto the existing Florida DOH shelf (`fl-doh-ehwaters-12009`, 5,746 parcels, 5–150 acres), not the Accela cadastre. County parcels were not re-downloaded. West Melbourne, Rockledge, Satellite Beach, Cocoa, and Cocoa Beach join on a parcel id when it matches, then a point inside the parcel. Melbourne is spatial. Opportunity Zone fields, school grades, and base flood elevations were not written.

Shelf totals: zoning 979, future land use 973. The Orlando shed sample (mostly Titusville) joined none.

| City | Zoning | Future land use | Join |
| --- | ---: | ---: | --- |
| Melbourne | 409 | 409 | CommunityDevelopmentViewer_AGOL MapServer 109 `ZONING` and 108 `FLUM` |
| West Melbourne | 149 | 149 | `Zoning_View` `zoningnew` and `Future_Land_Use_View_2` `flunew` |
| Rockledge | 163 | 160 | Planning_Building_Public FeatureServer 0 `Zoning` and 1 `FLU` |
| Satellite Beach | 16 | 16 | FeatureServer 16 `Zoning` and 15 `FLU`, on `PID` |
| Cocoa | 206 | 215 | Public_View_Cocoa_Zoning FeatureServer 1 `Zoning` and `FLU_Public_View` FeatureServer 6 `FLUCity` |
| Indian Harbour Beach | 12 | 0 | Zoning only. Land cover is not stored as future land use |
| Cocoa Beach | 24 | 24 | Unofficial 2021 `CBParcelsMaster2021`. The drawer flags that vintage |

Palm Bay and Titusville stay on their prior cards and are not applied here. Cape Canaveral, Indialantic, Melbourne Beach, Grant-Valkaria, Palm Shores, Melbourne Village, and Malabar have no public city service. County `Zoning_WKID2881`, county future land use, Accela zoning, West Melbourne `County_FLU_Areas`, and West Melbourne school-zone layers are not copied in. `gis.melbourneflorida.org` and Melbourne, Australia are rejected.

## Manatee and Sarasota Counties, Florida (FIPS 12081 and 12115)

Catalog: `data/manatee-sarasota-municipal.json`. Join script: `scripts/join_manatee_sarasota_municipal.py`. Stamped onto the existing Florida DOH shelves (`fl-doh-ehwaters-12081`, 7,239 parcels; `fl-doh-ehwaters-12115`, 4,303 parcels). County parcels were not re-downloaded. Join is spatial: the centroid plus up to four points inside the parcel, and the smallest containing polygon wins. Opportunity Zone fields, school grades, and base flood elevations were not written.

Shelf totals: Manatee zoning 221 and future land use 247; Sarasota zoning 566 and future land use 124. A situs city on this acreage band is often wider than the municipal polygon, so a miss stays blank. Unincorporated labels such as Myakka City, Parrish, Ellenton, Nokomis, Englewood, and Osprey are not stamped.

| City | Situs parcels | Zoning | Future land use | Layer |
| --- | ---: | ---: | ---: | --- |
| Bradenton | 2,080 | 129 | 152 | City `Zoning` `ZONING` and `FLU_CoB` `FLULABEL` |
| Palmetto | 648 | 73 | 76 | City `Zoning` `ZONE` and `FLU` `FLU` |
| Longboat Key | 28 | 28 | 28 | Town zoning polygons `ZONING` and `Future_Land_Use` `FLU`. 19 parcels are in Manatee and 9 are in Sarasota |
| Sarasota | 2,547 | 120 | 115 | Native `Zoning_Districts_(View_Only)` `ZONECLASS` and `FutureLandUse` layer 3 `LANDUSECODE` |
| North Port | 428 | 367 | 0 | Sarasota County `Hosted/CityNorthPortZoning`. City future land use is still a gap |
| Venice | 657 | 70 | 0 | Sarasota County `Hosted/CityVeniceZoning`. City future land use is still a gap |

Anna Maria, Bradenton Beach, and Holmes Beach stay blank. PDF maps and parcel `AM_`, `BB_`, and `HB_` fields are not a city service. Manatee County Planning zoning is not copied into those cities or into Bradenton and Palmetto.

City of Sarasota uses the native city services. The county `Hosted/CitySarasotaZoning` copy is not used. `Hosted/CityVeniceZoningView` is token-gated, so the public zoning layer is used and Venice future land use is left blank. County `FLUBoundary` is not stored as city future land use. Northport, Alabama ArcGIS org `3u10F1chkeawsUZY` is rejected.

## Charlotte County, Florida (FIPS 12015)

Catalog: `data/charlotte-municipal.json`. Join script: `scripts/join_charlotte_municipal.py`. Punta Gorda is the only incorporated city. Its zoning is `ZoningOfficial_View` FeatureServer 0 `Zoning_Cla` (154 polygons; one has no class and is not indexed) and its future land use is `FLU_All_2045` FeatureServer 5 `LUName` (117 polygons). Both extents sit inside Charlotte County, Florida (about lon −82.10 to −82.01, lat 26.84 to 26.95).

This checkout has no Charlotte County parcel shelf, and none was downloaded. The city layers were indexed and stamped onto zero parcels. Opportunity Zone fields, school grades, and base flood elevations were not written.

County zoning `ZONE_` value `CITY` (21 polygons) and county future land use `NEWLU` value `City` (571 polygons) are city stubs, not districts. The county `PG_Zoning` copy is not used. Charlotte, North Carolina, Punta Gorda, Belize, and the `BO_Charlotte_*` prefer-official layers are rejected.

## Panhandle Florida (Escambia 12033, Okaloosa 12091, Santa Rosa 12113, Walton 12131, Bay 12005)

Catalog: `data/panhandle-municipal.json`. Join script: `scripts/join_panhandle_municipal.py`. The four Pensacola-market shelves stay on the existing Florida DOH 5–150 acre extracts. Bay County has no parcel shelf in this checkout, so its city layers were indexed and stamped onto zero parcels. County parcels were not downloaded. Opportunity Zone fields, school grades, and base flood elevations were not written. The join is spatial: the centroid plus up to four points inside the parcel, and the smallest containing polygon wins.

Shelf totals: Escambia zoning 810 and future land use 0 (9,097 parcels); Okaloosa zoning 270 and future land use 270 (5,854); Santa Rosa zoning 85 and future land use 9 (7,011); Walton zoning 135 and future land use 158 (8,179); Bay zoning 0 and future land use 0.

| City | County | Situs parcels | Zoning | Future land use | Layer |
| --- | --- | ---: | ---: | ---: | --- |
| Panama City | Bay | 0 | 0 | 0 | City `Zoning_CPC` `LABEL` (18,777 indexed) and `FutureLandUse_CPC` `LANDUSE` (17,300 indexed) |
| Callaway | Bay | 0 | 0 | 0 | Bay `LandUsePlanning` `SUB_ZONING=2` (702 indexed) and `SUB_FLU=2` (751 indexed) |
| Mexico Beach | Bay | 0 | 0 | 0 | Same service, `SUB_ZONING=4` (234) and `SUB_FLU=4` (226) |
| Lynn Haven | Bay | 0 | 0 | 0 | Future land use only, `SUB_FLU=3` (778 indexed) |
| Parker | Bay | 0 | 0 | 0 | Future land use only, `SUB_FLU=7` (242 indexed) |
| Springfield | Bay | 0 | 0 | 0 | Future land use only, `SUB_FLU=8` (434 indexed) |
| Pensacola | Escambia | 4,368 | 810 | 0 | `maps.cityofpensacola.com` `Zoning_WebMap_MIL1` layer 16 `ZONING`. City future land use stays a gap |
| Destin | Okaloosa | 226 | 202 | 202 | `Zoning_JulyB_WFL1` `Zone_ABBR` and `LandUse_DND25_WFL1` layer 2 `LU_CODE` |
| Fort Walton Beach | Okaloosa | 119 | 68 | 68 | `gis.fwb.org` Maps/Zoning `Zoning` and Maps/FLU `FLU` |
| Milton | Santa Rosa | 1,946 | 53 | 0 | `City_of_Milton_Zoning` `zone_code`. Future land use stays a gap |
| Gulf Breeze | Santa Rosa | 108 | 9 | 9 | `Gulf_Breeze_Zoning` `zoning` and `flum` on the same layer |
| Jay | Santa Rosa | 983 | 23 | 0 | `TownOfJayZoning` `zone`. Future land use stays a gap |
| Panama City Beach | Walton | 24 | 0 | 0 | City twin FeatureServer 47 `ZONING` and 49 `FLU_CODE` (633 and 696 indexed). The polygons sit in Bay County and miss these Walton centroids |
| DeFuniak Springs | Walton | 2,816 | 135 | 134 | `WeeklyUpdatesDFS` FeatureServer 7 `ZONING` and 6 `FLU` |
| Paxton | Walton | 0 named | 0 | 24 | `WeeklyUpdatesPaxton` FeatureServer 6 `FLU_CLASS` (103 indexed). Zoning stays a gap. The 24 hits are blank-situs parcels inside the town |

A situs city on this acreage band is often wider than the municipal polygon, so a miss stays blank. Freeport zoning is a numeric code with a blank description and was left blank. Crestview, Niceville, Valparaiso, Mary Esther, Laurel Hill, Shalimar, Cinco Bayou, Century, and Pensacola Beach stay blank.

`gis.cityofpensacola.com` still returns HTTP 523. Escambia Accela zoning, the FGDL statewide zoning service, Okaloosa county zoning and future land use, Walton EnerGov county layers, Santa Rosa county `Hosted/ZONE` and `OpenDataFlum`, and Bay unincorporated `SUB_ZONING=1` / `SUB_FLU=1` stay unused. Panama City uses the city `Zoning_CPC` layers rather than county subtype 5. Lynn Haven, Parker, and Springfield zoning filters stay unused.

## Not in this pass

- New county parcel extracts for any other market. Bay County parcels were not downloaded for the Panhandle city layers.
