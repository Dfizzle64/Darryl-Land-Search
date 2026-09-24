# Market parcels (every MSA except Orlando)

Orlando keeps `scripts/seed_orlando_parcels.py` and `data/fixtures/orlando-parcels`. Lake, Osceola, Seminole, and Sumter in that store were reseeded from public county GIS. Polk's market extract is the property-appraiser layer under `data/fixtures/market-parcels`. The Orlando Polk tiles were not replaced.

Other markets use the same 0.25° tile grid (origin longitude -83, latitude 27) under `data/fixtures/market-parcels/counties/{fips}/tiles`, or they point at an Orlando tile folder when the county is shared. The home page does not embed the polygons. `GET /api/parcels?market={Market}&bbox=w,s,e,n` reads only the tiles for **that market** that intersect the viewport. Outlines stay off until neighborhood zoom (about 10.5), an area is locked, or Show parcels is on — the same gate as Orlando.

## Refresh

```bash
npm run seed:parcels:markets
python3 scripts/seed_market_parcels.py --market Charlotte
python3 scripts/seed_market_parcels.py --market Tampa --county Hardee
python3 scripts/seed_market_parcels.py --refresh
```

A finished county is skipped unless `--refresh` is passed. Cached normalized features, when present, live under `/tmp/dls-market-parcels`.

## Sources

Finished extracts in this batch were merged from public county and state GIS branches. Each `county.json` records the service URL, the feature count, and what was not joined. The coverage table is the inventory. A gap means no finished extract was included. Zoning and future land use are stored only where that county's source or a joined municipal layer published them.

DeKalb County, Georgia is the complete assessment extract already merged on main (`ga-dekalb-assessment-view-2`). City zoning and future land use are joined where that extract published them. That service has no sale table.

Marshall County, Alabama is the web5 Marshall/Public/37 5–150 acre extract. Zoning is null. Baldwin County keeps the existing parcel shelf and adds Daphne Class zoning, Daphne Future_Dev, and Fairhope base zoning. Fairhope AO/MO names are overlay notes, not zoning codes. Shelby County keeps the existing parcel shelf and adds Alabaster ZoneCode. Walker, Washington, and Escambia County, Alabama stay gaps. Morgan County stays the existing VAM extract already on this branch. No Opportunity Zone designation was added.

Carroll County, Georgia uses the OpenAddresses job 910028 parcel snapshot because the live county parcel service is blocked. Acreage is GIS area. Carrollton and Carroll-side Villa Rica supply the city CAMA, zoning, and future land use that matched a Carroll parcel id. County zoning and future land use remain PDFs. Sales are the commercial/industrial subset only. No Opportunity Zone designation was added.

Walton County, Georgia is the choosewalton 5–150 GIS-acre landbase. FLU and Description are character areas, not Euclidean zoning. Monroe CAMA matches a handful of shared parcel numbers. City zoning covers Monroe, Loganville, and Social Circle only. Countywide owner, tax, sales, and Euclidean zoning stay gaps. Nothing in that extract is an Opportunity Zone designation.

Spalding County, Georgia is the public Parcels_Public_View. Acreage is GIS area in Georgia West State Plane feet, inclusive 5–150. The layer publishes parcel id and jurisdiction only, so owner, situs, tax, and last sale stay null. County zoning is joined outside Griffin. Griffin city parcels stay unzoned. Future land use is a PDF. Sunny Side is not treated as a city. University of Maryland / Regrid and ARC LandPro were not used. No Opportunity Zone designation was added.

Hall County, Georgia is the official hallgis HallCo_Addr_Pcl_Rds/MapServer/1 extract. Acreage is deeded DEED_ACRE in the inclusive 5–150 band. Owner and mailing are blank where NO_RELEASE is 1. CUR_VALUE is the published market value; land value is not copied into it. Sales stay null. Zoning is Gainesville, Flowery Branch, and Oakwood, then unincorporated Hall County. MUNI stubs for Lula, Clermont, Gillsville, Braselton, Buford, and Rest Haven are not zoning codes. Future land use is HC_FLU_2024, replaced by Gainesville FLU_2022 inside that city. Hall County, Nebraska, Gainesville, Florida, and ARC LandPro were not used. No Opportunity Zone designation was added.

Jackson County, Georgia is the county Tax_Parcels/FeatureServer/9 extract. Acreage is TOTALACRES in the inclusive 5–150 band. Market value is the sum of the published fair-market components. Sales stay null. City Euclidean zoning covers Jefferson, Commerce, Hoschton, Pendergrass, Arcade, Nicholson, and Talmo. Braselton zoning is the partial county table. Maysville stays unzoned. Future land use is the county parcel layer, replaced by NEGRC city layers where those polygons have a label. Jackson County, Missouri, Michigan, and Wisconsin, Jefferson Parish, Louisiana, and ARC LandPro were not used. No Opportunity Zone designation was added.

Butts County, Georgia is the SchneiderCorp ButtsCountyGA_WFS/MapServer/0 extract. Acreage is TOTALACRES in the inclusive 5–150 band. CURR_VAL is the current value and ESTTAX is the estimated tax. Sales stay null because SALES_AREA is a neighborhood code. Zoning is City of Jackson, Flovilla, and Jenkinsburg, then unincorporated Butts County. Future land use is a comprehensive-plan PDF. Butte County, California, Jackson, Mississippi, and ARC LandPro were not used. No Opportunity Zone designation was added.

Bradley County, Tennessee is the Cleveland GIS Parcels_Impact extract. Census FIPS is 47011. Comptroller county 006 is the layer filter, not the FIPS. The older IMPACT COUNTY_ID=11 tiles, whose centroids sat near longitude -87, are replaced. Cleveland zoning applies only inside the city limits. Charleston and unincorporated Bradley keep the assessor label. Future land use stays null. Hamilton County is unchanged. No Opportunity Zone designation was added.

Effingham County, Georgia is the Parcels2024 extract in the Savannah market. Acreage is TOTALACRES in the inclusive 5–150 band. Zoning is the parcel ZCODE. Rincon, Guyton, and Springfield boundaries are joined, and those cities have no public zoning or future-land-use service. Future land use is FLUM EFF_REV2 where the parcel id matches. Sale price and current value come from ParcelUpdate when that older table has the parcel. Effingham County, Illinois was not used. No Opportunity Zone designation was added.

Bryan County, Georgia is the PropertyDetails extract in the Savannah market, paired with Effingham. Acreage is TOTALACRES in the inclusive 5–150 band. Unincorporated zoning is the county Zoning layer. Pembroke and Richmond Hill use the parcel zoning code, and CITY stubs are not districts. Future land use is the 2023 comprehensive plan outside those cities. City future land use and sales stay null. Bryan County, Texas, Bryan County, Oklahoma, and Chatham County SAGIS were not used. No Opportunity Zone designation was added.

## Coverage

# Market parcel coverage

Acreage band is **5.0–150.0 inclusive**. Lake, Osceola, Seminole, and Sumter Orlando tiles were reseeded from county GIS. Polk market parcels use the property-appraiser extract. Orange still points at the Orlando tiles.

Parcels stay off until neighborhood zoom, an area lock, or Show parcels. The map requests the selected market's viewport tiles only.

| Market | Tier | Parcels | Complete counties | Sample or partial | Gaps |
| --- | --- | ---: | ---: | ---: | ---: |
| Atlanta | primary | 105,653 | 19 | 0 | 16 |
| Tampa | primary | 124,315 | 10 | 0 | 0 |
| Charleston | primary | 22,649 | 3 | 0 | 4 |
| Nashville | primary | 109,348 | 13 | 0 | 4 |
| Charlotte | primary | 106,650 | 12 | 0 | 3 |
| Raleigh-Durham | primary | 151,530 | 17 | 0 | 0 |
| SWFL | other | 32,749 | 4 | 0 | 0 |
| Vero Beach | other | 23,009 | 5 | 0 | 0 |
| Melbourne | other | 41,026 | 5 | 0 | 0 |
| Jacksonville | other | 26,301 | 5 | 0 | 0 |
| Big Bend | other | 21,551 | 1 | 3 | 3 |
| Pensacola | other | 59,902 | 6 | 0 | 0 |
| Birmingham | other | 38,101 | 3 | 0 | 6 |
| Mobile | other | 42,446 | 3 | 0 | 2 |
| Huntsville | other | 29,598 | 4 | 0 | 3 |
| Savannah | other | 11,549 | 3 | 0 | 5 |
| Columbia | other | 14,613 | 1 | 1 | 8 |
| Greenville | other | 31,164 | 2 | 0 | 6 |
| Chattanooga | other | 15,498 | 2 | 0 | 8 |
| Knoxville | other | 39,939 | 7 | 0 | 6 |
| Memphis | other | 45,278 | 8 | 0 | 3 |
| Jackson | other | 6,384 | 1 | 0 | 0 |
| Winston-Salem | other | 92,188 | 9 | 0 | 0 |
| Wilmington | other | 47,320 | 6 | 0 | 0 |
| Heartland | shelf | 21,163 | 4 | 1 | 0 |
| North-Central Florida | other | 52,695 | 7 | 0 | 0 |
| Asheville | other | 16,793 | 2 | 0 | 0 |
| Tuscaloosa | other | 11,596 | 1 | 0 | 3 |
| Montgomery | other | 26,759 | 3 | 0 | 1 |

## Counties

### Atlanta

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Banks | Georgia | 13011 | gap | 0 | unavailable |
| Barrow | Georgia | 13013 | complete-gte-5ac | 4,251 | ga-barrow-parcels |
| Bartow | Georgia | 13015 | complete-gte-5ac | 7,077 | ga-bartow-land |
| Butts | Georgia | 13035 | complete-gte-5ac | 2,738 | ga-butts-wfs-0 |
| Carroll | Georgia | 13045 | complete-gte-5ac | 9,217 | oa-carroll-ga-910028 |
| Cherokee | Georgia | 13057 | gap | 0 | unavailable |
| Clayton | Georgia | 13063 | gap | 0 | unavailable |
| Cobb | Georgia | 13067 | complete-gte-5ac | 4,770 | ga-cobb-taxassessorsdaily |
| Coweta | Georgia | 13077 | complete-gte-5ac | 8,090 | ga-coweta-wingap-parcels |
| Dawson | Georgia | 13085 | gap | 0 | unavailable |
| DeKalb | Georgia | 13089 | complete-gte-5ac | 3,401 | ga-dekalb-assessment-view-2 |
| Douglas | Georgia | 13097 | complete-gte-5ac | 4,231 | ga-douglas-landrecords |
| Fayette | Georgia | 13113 | complete-gte-5ac | 4,725 | ga-fayette-parcels |
| Forsyth | Georgia | 13117 | complete-gte-5ac | 3,925 | ga-forsyth-tax-parcels |
| Fulton | Georgia | 13121 | complete-gte-5ac | 8,274 | ga-fulton-pmv-mapserver-11 |
| Gordon | Georgia | 13129 | gap | 0 | unavailable |
| Gwinnett | Georgia | 13135 | complete-gte-5ac | 6,653 | ga-gwinnett-gc-parcel |
| Hall | Georgia | 13139 | complete-gte-5ac | 6,904 | ga-hall-addr-pcl-1 |
| Haralson | Georgia | 13143 | gap | 0 | unavailable |
| Heard | Georgia | 13149 | gap | 0 | unavailable |
| Henry | Georgia | 13151 | complete-gte-5ac | 7,418 | ga-henry-parcels |
| Jackson | Georgia | 13157 | complete-gte-5ac | 6,674 | ga-jackson-tax-parcels-9 |
| Jasper | Georgia | 13159 | gap | 0 | unavailable |
| Lamar | Georgia | 13171 | gap | 0 | unavailable |
| Lumpkin | Georgia | 13187 | gap | 0 | unavailable |
| Meriwether | Georgia | 13199 | gap | 0 | unavailable |
| Monroe | Georgia | 13207 | gap | 0 | unavailable |
| Morgan | Georgia | 13211 | gap | 0 | unavailable |
| Newton | Georgia | 13217 | gap | 0 | unavailable |
| Paulding | Georgia | 13223 | complete-gte-5ac | 5,094 | ga-paulding-parcels |
| Pickens | Georgia | 13227 | gap | 0 | unavailable |
| Pike | Georgia | 13231 | gap | 0 | unavailable |
| Rockdale | Georgia | 13247 | complete-gte-5ac | 2,555 | ga-rockdale-parcels |
| Spalding | Georgia | 13255 | complete-gte-5ac | 3,832 | ga-spalding-parcels-public |
| Walton | Georgia | 13297 | complete-gte-5ac | 5,824 | ga-walton-choosewalton-parcels |

### Tampa

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Citrus | Florida | 12017 | complete-gte-5ac | 5,807 | fl-citrus-doh-municipal-12017 |
| Hardee | Florida | 12049 | complete-gte-5ac | 5,303 | fl-hardee-infomap-12049 |
| Hernando | Florida | 12053 | complete-gte-5ac | 6,601 | fl-hernando-parcels-12053 |
| Hillsborough | Florida | 12057 | complete-gte-5ac | 13,838 | fl-hillsborough-parcelpublishing-12 |
| Manatee | Florida | 12081 | complete-gte-5ac | 7,239 | fl-doh-ehwaters-12081 |
| Pasco | Florida | 12101 | complete-gte-5ac | 12,372 | fl-pasco-pascomapper-7 |
| Pinellas | Florida | 12103 | complete-gte-5ac | 42,230 | fl-pinellas-publicwebgis-1 |
| Polk | Florida | 12105 | complete-gte-5ac | 20,263 | fl-polk-property-appraiser-134 |
| Sarasota | Florida | 12115 | complete-gte-5ac | 4,303 | fl-doh-ehwaters-12115 |
| Sumter | Florida | 12119 | complete-gte-5ac | 6,359 | fl-doh-ehwaters-12119 |

### Charleston

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Berkeley | South Carolina | 45015 | complete-gte-5ac | 7,886 | sc-berkeley-addr-muni |
| Charleston | South Carolina | 45019 | complete-gte-5ac | 7,989 | sc-charleston-energov-ent |
| Clarendon | South Carolina | 45027 | gap | 0 | unavailable |
| Colleton | South Carolina | 45029 | gap | 0 | unavailable |
| Dorchester | South Carolina | 45035 | complete-gte-5ac | 6,774 | sc-dorchester-parcels-public |
| Georgetown | South Carolina | 45043 | gap | 0 | unavailable |
| Orangeburg | South Carolina | 45075 | gap | 0 | unavailable |

### Nashville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Bedford | Tennessee | 47003 | complete-gte-5ac | 4,211 | tn-impact-47003 |
| Cannon | Tennessee | 47015 | complete-gte-5ac | 6,376 | tn-impact-47015 |
| Cheatham | Tennessee | 47021 | complete-gte-5ac | 5,426 | apsu-cheatgis-47021 |
| Davidson | Tennessee | 47037 | complete-gte-5ac | 9,478 | tn-metro-davidson-parcels |
| Dickson | Tennessee | 47043 | complete-gte-5ac | 8,443 | tn-impact-47043 |
| Hickman | Tennessee | 47081 | complete-gte-5ac | 3,672 | tn-impact-47081 |
| Macon | Tennessee | 47111 | gap | 0 | tn-impact-47111 |
| Marshall | Tennessee | 47117 | gap | 0 | tn-impact-47117 |
| Maury | Tennessee | 47119 | complete-gte-5ac | 9,033 | tn-columbia-agol-47119 |
| Montgomery | Tennessee | 47125 | complete-gte-5ac | 7,038 | tn-mcgtn-cama-47125 |
| Robertson | Tennessee | 47147 | complete-gte-5ac | 8,581 | tn-impact-47147 |
| Rutherford | Tennessee | 47149 | complete-gte-5ac | 9,677 | tn-rutherford-agol-parcels |
| Smith | Tennessee | 47159 | gap | 0 | tn-impact-47159 |
| Sumner | Tennessee | 47165 | complete-gte-5ac | 15,982 | tn-sumner-911-parcels-cama |
| Trousdale | Tennessee | 47169 | gap | 0 | tn-impact-47169 |
| Williamson | Tennessee | 47187 | complete-gte-5ac | 10,760 | tn-williamson-datapull-47187 |
| Wilson | Tennessee | 47189 | complete-gte-5ac | 10,671 | tn-impact-47189 |

### Charlotte

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Anson | North Carolina | 37007 | complete-gte-5ac | 5,820 | nc-anson-vector-37007 |
| Cabarrus | North Carolina | 37025 | complete-gte-5ac | 6,983 | nc-cabarrus-tax-parcels-37025 |
| Catawba | North Carolina | 37035 | complete-gte-5ac | 8,502 | nc-onemap-37035 |
| Chester | South Carolina | 45023 | gap | 0 | unavailable |
| Cleveland | North Carolina | 37045 | complete-gte-5ac | 9,310 | nc-onemap-37045 |
| Davidson | North Carolina | 37057 | complete-gte-5ac | 12,063 | nc-davidson-opengov-37057 |
| Gaston | North Carolina | 37071 | complete-gte-5ac | 6,815 | nc-gaston-publicgis-37071 |
| Iredell | North Carolina | 37097 | complete-gte-5ac | 10,768 | nc-iredell-taxsql-37097 |
| Lancaster | South Carolina | 45057 | gap | 0 | unavailable |
| Lincoln | North Carolina | 37109 | complete-gte-5ac | 6,563 | nc-lincoln-operational-37109 |
| Mecklenburg | North Carolina | 37119 | complete-gte-5ac | 8,402 | meck-taxparcel-camadata-37119 |
| Rowan | North Carolina | 37159 | complete-gte-5ac | 10,375 | nc-rowan-open-data-37159 |
| Stanly | North Carolina | 37167 | complete-gte-5ac | 8,024 | nc-onemap-37167 |
| Union | North Carolina | 37179 | complete-gte-5ac | 13,025 | nc-union-atlas-37179 |
| York | South Carolina | 45091 | gap | 0 | unavailable |

### Raleigh-Durham

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Alamance | North Carolina | 37001 | complete-gte-5ac | 8,846 | nc-onemap-37001 |
| Chatham | North Carolina | 37037 | complete-gte-5ac | 13,229 | nc-onemap-37037 |
| Durham | North Carolina | 37063 | complete-gte-5ac | 4,940 | durham-property-37063 |
| Franklin | North Carolina | 37069 | complete-gte-5ac | 7,639 | nc-onemap-37069 |
| Granville | North Carolina | 37077 | complete-gte-5ac | 7,150 | nc-onemap-37077 |
| Harnett | North Carolina | 37085 | complete-gte-5ac | 11,657 | nc-onemap-37085 |
| Johnston | North Carolina | 37101 | complete-gte-5ac | 14,113 | nc-onemap-37101 |
| Lee | North Carolina | 37105 | complete-gte-5ac | 4,858 | nc-onemap-37105 |
| Nash | North Carolina | 37127 | complete-gte-5ac | 8,292 | nc-onemap-37127 |
| Orange | North Carolina | 37135 | complete-gte-5ac | 9,375 | nc-orange-webparcel-37135 |
| Person | North Carolina | 37145 | complete-gte-5ac | 5,956 | nc-onemap-37145 |
| Sampson | North Carolina | 37163 | complete-gte-5ac | 14,031 | nc-onemap-37163 |
| Vance | North Carolina | 37181 | complete-gte-5ac | 3,181 | nc-onemap-37181 |
| Wake | North Carolina | 37183 | complete-gte-5ac | 12,436 | nc-wake-county-parcels |
| Warren | North Carolina | 37185 | complete-gte-5ac | 5,596 | nc-onemap-37185 |
| Wayne | North Carolina | 37191 | complete-gte-5ac | 15,079 | nc-onemap-37191 |
| Wilson | North Carolina | 37195 | complete-gte-5ac | 5,152 | nc-onemap-37195 |

### SWFL

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Charlotte | Florida | 12015 | complete-gte-5ac | 4,565 | fl-doh-ehwaters-12015 |
| Collier | Florida | 12021 | complete-gte-5ac | 13,889 | fl-collier-parceljoin |
| Lee | Florida | 12071 | complete-gte-5ac | 9,992 | fl-lee-parceladdress |
| Sarasota | Florida | 12115 | complete-gte-5ac | 4,303 | fl-doh-ehwaters-12115 |

### Vero Beach

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Brevard | Florida | 12009 | complete-gte-5ac | 6,802 | fl-brevard-accela-12009 |
| Indian River | Florida | 12061 | complete-gte-5ac | 3,779 | fl-ircpa-parcels-12061 |
| Martin | Florida | 12085 | complete-gte-5ac | 3,790 | fl-martin-geoweb-12085 |
| Okeechobee | Florida | 12093 | complete-gte-5ac | 3,053 | fl-okeechobee-planning-12093 |
| St. Lucie | Florida | 12111 | complete-gte-5ac | 5,585 | fl-slc-parcels-12111 |

### Melbourne

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Brevard | Florida | 12009 | complete-gte-5ac | 6,802 | fl-brevard-accela-12009 |
| Indian River | Florida | 12061 | complete-gte-5ac | 3,779 | fl-ircpa-parcels-12061 |
| Orange | Florida | 12095 | complete-gte-5ac | 11,709 | reused-orlando-ocpa-5-150 |
| Osceola | Florida | 12097 | complete-gte-5ac | 6,169 | reused-orlando-complete-5-150 |
| Volusia | Florida | 12127 | complete-gte-5ac | 12,567 | fl-doh-ehwaters-12127 |

### Jacksonville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Baker | Florida | 12003 | complete-gte-5ac | 3,314 | fl-baker-parcels-web2-12003 |
| Clay | Florida | 12019 | complete-gte-5ac | 4,688 | fl-clay-parcels-lgim-12019 |
| Duval | Florida | 12031 | complete-gte-5ac | 7,768 | fl-coj-citybiz-parcels-12031 |
| Nassau | Florida | 12089 | complete-gte-5ac | 5,587 | fl-nassau-taxmap-12089 |
| St. Johns | Florida | 12109 | complete-gte-5ac | 4,944 | fl-sjc-hosted-parcel-12109 |

### Big Bend

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Dixie | Florida | 12029 | gap | 0 | unavailable |
| Gadsden | Florida | 12039 | sample | 5,917 | fl-gadsden-arpc-par-071218-12039 |
| Jefferson | Florida | 12065 | sample | 5,165 | fl-jefferson-pa-parcels-12065 |
| Leon | Florida | 12073 | complete-gte-5ac | 5,685 | fl-leon-overlay-parcel-12073 |
| Madison | Florida | 12079 | gap | 0 | unavailable |
| Taylor | Florida | 12123 | gap | 0 | unavailable |
| Wakulla | Florida | 12129 | sample | 4,784 | fl-wakulla-county-parcels-12129 |

### Pensacola

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Baldwin | Alabama | 01003 | complete-gte-5ac | 17,987 | al-baldwin-public-isv |
| Bay | Florida | 12005 | complete-gte-5ac | 4,861 | fl-panhandle-12005 |
| Escambia | Florida | 12033 | complete-gte-5ac | 9,240 | fl-panhandle-12033 |
| Okaloosa | Florida | 12091 | complete-gte-5ac | 9,956 | fl-panhandle-12091 |
| Santa Rosa | Florida | 12113 | complete-gte-5ac | 8,928 | fl-panhandle-12113 |
| Walton | Florida | 12131 | complete-gte-5ac | 8,930 | fl-panhandle-12131 |

### Birmingham

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Bibb | Alabama | 01007 | gap | 0 | unavailable |
| Blount | Alabama | 01009 | gap | 0 | unavailable |
| Chilton | Alabama | 01021 | gap | 0 | unavailable |
| Cullman | Alabama | 01043 | gap | 0 | unavailable |
| Jefferson | Alabama | 01073 | complete-gte-5ac | 15,641 | al-jefferson-parcels |
| Shelby | Alabama | 01117 | complete-gte-5ac | 11,994 | al-shelby-cadastral-2025 |
| St. Clair | Alabama | 01115 | complete-gte-5ac | 10,466 | al-stclair-owner-parcels |
| Talladega | Alabama | 01121 | gap | 0 | unavailable |
| Walker | Alabama | 01127 | gap | 0 | unavailable |

### Mobile

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Baldwin | Alabama | 01003 | complete-gte-5ac | 17,987 | al-baldwin-public-isv |
| Escambia | Alabama | 01053 | gap | 0 | unavailable |
| George | Mississippi | 28039 | complete-gte-5ac | 7,189 | ms-mdeq-2023-28039 |
| Mobile | Alabama | 01097 | complete-gte-5ac | 17,270 | al-mobile-agol-capturecama |
| Washington | Alabama | 01129 | gap | 0 | unavailable |

### Huntsville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Cullman | Alabama | 01043 | gap | 0 | unavailable |
| Jackson | Alabama | 01071 | gap | 0 | unavailable |
| Limestone | Alabama | 01083 | complete-gte-5ac | 5,445 | al-limestone-remap-1 |
| Lincoln | Tennessee | 47103 | gap | 0 | tn-impact-47103 |
| Madison | Alabama | 01089 | complete-gte-5ac | 12,312 | al-madison-public-isv-185 |
| Marshall | Alabama | 01095 | complete-gte-5ac | 11,014 | al-marshall-public-37 |
| Morgan | Alabama | 01103 | complete-gte-5ac | 827 | al-morgan-vam-10 |

### Savannah

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Beaufort | South Carolina | 45013 | gap | 0 | unavailable |
| Bryan | Georgia | 13029 | complete-gte-5ac | 2,138 | ga-bryan-property-details |
| Bulloch | Georgia | 13031 | gap | 0 | unavailable |
| Chatham | Georgia | 13051 | complete-gte-5ac | 3,283 | sagis-chatham-ga-parcel-digest |
| Effingham | Georgia | 13103 | complete-gte-5ac | 6,128 | ga-effingham-parcels-2024 |
| Jasper | South Carolina | 45053 | gap | 0 | unavailable |
| Liberty | Georgia | 13179 | gap | 0 | unavailable |
| Screven | Georgia | 13251 | gap | 0 | unavailable |

### Columbia

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Calhoun | South Carolina | 45017 | gap | 0 | unavailable |
| Fairfield | South Carolina | 45039 | gap | 0 | unavailable |
| Kershaw | South Carolina | 45055 | gap | 0 | unavailable |
| Lee | South Carolina | 45061 | gap | 0 | unavailable |
| Lexington | South Carolina | 45063 | complete-gte-5ac | 13,975 | sc-lexington-property-4 |
| Newberry | South Carolina | 45071 | gap | 0 | unavailable |
| Orangeburg | South Carolina | 45075 | gap | 0 | unavailable |
| Richland | South Carolina | 45079 | sample | 638 | sc-columbia-city-landrecords |
| Saluda | South Carolina | 45081 | gap | 0 | unavailable |
| Sumter | South Carolina | 45085 | gap | 0 | unavailable |

### Greenville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Abbeville | South Carolina | 45001 | gap | 0 | unavailable |
| Anderson | South Carolina | 45007 | gap | 0 | unavailable |
| Greenville | South Carolina | 45045 | complete-gte-5ac | 14,959 | sc-greenville-gcgia-tax-parcel |
| Greenwood | South Carolina | 45047 | gap | 0 | unavailable |
| Laurens | South Carolina | 45059 | gap | 0 | unavailable |
| Oconee | South Carolina | 45073 | gap | 0 | unavailable |
| Pickens | South Carolina | 45077 | gap | 0 | unavailable |
| Spartanburg | South Carolina | 45083 | complete-gte-5ac | 16,205 | sc-spartanburg-cama-parcels |

### Chattanooga

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Bradley | Tennessee | 47011 | complete-gte-5ac | 6,336 | tn-cleveland-parcels-impact-47011 |
| Catoosa | Georgia | 13047 | gap | 0 | unavailable |
| Dade | Georgia | 13083 | gap | 0 | unavailable |
| Hamilton | Tennessee | 47065 | complete-gte-5ac | 9,162 | tn-hamilton-live-parcels |
| Marion | Tennessee | 47115 | gap | 0 | tn-impact-47115 |
| Meigs | Tennessee | 47121 | gap | 0 | tn-impact-47121 |
| Rhea | Tennessee | 47143 | gap | 0 | tn-impact-47143 |
| Sequatchie | Tennessee | 47153 | gap | 0 | tn-impact-47153 |
| Walker | Georgia | 13295 | gap | 0 | unavailable |
| Whitfield | Georgia | 13313 | gap | 0 | unavailable |

### Knoxville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Anderson | Tennessee | 47001 | complete-gte-5ac | 4,302 | tn-impact-47001 |
| Blount | Tennessee | 47009 | complete-gte-5ac | 8,183 | tn-blount-agol-47009 |
| Campbell | Tennessee | 47013 | complete-gte-5ac | 5,445 | tn-impact-47013 |
| Cocke | Tennessee | 47029 | complete-gte-5ac | 4,448 | tn-impact-47029 |
| Grainger | Tennessee | 47057 | complete-gte-5ac | 6,406 | tn-impact-47057 |
| Hamblen | Tennessee | 47063 | gap | 0 | tn-impact-47063 |
| Jefferson | Tennessee | 47089 | complete-gte-5ac | 6,586 | tn-impact-47089 |
| Knox | Tennessee | 47093 | complete-gte-5ac | 4,569 | kgis-parcel-search |
| Loudon | Tennessee | 47105 | gap | 0 | tn-impact-47105 |
| Morgan | Tennessee | 47129 | gap | 0 | tn-impact-47129 |
| Roane | Tennessee | 47145 | gap | 0 | tn-impact-47145 |
| Sevier | Tennessee | 47155 | gap | 0 | tn-impact-47155 |
| Union | Tennessee | 47173 | gap | 0 | tn-impact-47173 |

### Memphis

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Benton | Mississippi | 28009 | complete-gte-5ac | 3,557 | ms-mdeq-2023-28009 |
| Crittenden | Arkansas | 05035 | complete-gte-5ac | 3,666 | ar-cadastre-05035 |
| DeSoto | Mississippi | 28033 | complete-gte-5ac | 6,219 | ms-mdeq-2023-28033 |
| Fayette | Tennessee | 47047 | gap | 0 | tn-impact-47047 |
| Lauderdale | Tennessee | 47097 | gap | 0 | tn-impact-47097 |
| Marshall | Mississippi | 28093 | complete-gte-5ac | 7,984 | ms-mdeq-2023-28093 |
| Mississippi | Arkansas | 05093 | complete-gte-5ac | 6,585 | ar-cadastre-05093 |
| Shelby | Tennessee | 47157 | complete-gte-5ac | 9,667 | tn-shelby-current-parcels |
| Tate | Mississippi | 28137 | complete-gte-5ac | 5,758 | ms-mdeq-2023-28137 |
| Tipton | Tennessee | 47167 | gap | 0 | tn-impact-47167 |
| Tunica | Mississippi | 28143 | complete-gte-5ac | 1,842 | ms-mdeq-2023-28143 |

### Jackson

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Madison | Tennessee | 47113 | complete-gte-5ac | 6,384 | tn-impact-47113 |

### Winston-Salem

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Davidson | North Carolina | 37057 | complete-gte-5ac | 12,063 | nc-davidson-opengov-37057 |
| Davie | North Carolina | 37059 | complete-gte-5ac | 5,728 | davie-county-gis-parcels |
| Forsyth | North Carolina | 37067 | complete-gte-5ac | 8,135 | nc-mapforsyth-37067 |
| Guilford | North Carolina | 37081 | complete-gte-5ac | 12,953 | nc-onemap-37081 |
| Randolph | North Carolina | 37151 | complete-gte-5ac | 16,449 | nc-onemap-37151 |
| Rockingham | North Carolina | 37157 | complete-gte-5ac | 9,378 | nc-onemap-37157 |
| Stokes | North Carolina | 37169 | complete-gte-5ac | 8,844 | nc-stokes-alllayers-24 |
| Surry | North Carolina | 37171 | complete-gte-5ac | 10,547 | nc-onemap-37171 |
| Yadkin | North Carolina | 37197 | complete-gte-5ac | 8,091 | nc-onemap-37197 |

### Wilmington

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Brunswick | North Carolina | 37019 | complete-gte-5ac | 7,533 | bcgis-seamless-37019 |
| Columbus | North Carolina | 37047 | complete-gte-5ac | 12,025 | nc-onemap-37047 |
| Duplin | North Carolina | 37061 | complete-gte-5ac | 11,397 | nc-onemap-37061 |
| New Hanover | North Carolina | 37129 | complete-gte-5ac | 2,263 | nc-new-hanover-parcels-37129 |
| Onslow | North Carolina | 37133 | complete-gte-5ac | 6,747 | nc-onemap-37133 |
| Pender | North Carolina | 37141 | complete-gte-5ac | 7,355 | nc-pender-energov-37141 |

### Heartland

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| DeSoto | Florida | 12027 | partial | 4,677 | fl-desoto-swfwmd-12027 |
| Glades | Florida | 12043 | complete-gte-5ac | 2,256 | fl-glades-agol-2026-06-12043 |
| Hardee | Florida | 12049 | complete-gte-5ac | 5,303 | fl-hardee-infomap-12049 |
| Hendry | Florida | 12051 | complete-gte-5ac | 3,070 | fl-hendry-parcels-feb2024-12051 |
| Highlands | Florida | 12055 | complete-gte-5ac | 5,857 | fl-highlands-pao-12055 |

### North-Central Florida

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Alachua | Florida | 12001 | complete-gte-5ac | 15,539 | fl-alachua-parcels35-12001 |
| Bradford | Florida | 12007 | complete-gte-5ac | 593 | fl-doh-ehwaters-12007 |
| Citrus | Florida | 12017 | complete-gte-5ac | 5,807 | fl-citrus-doh-municipal-12017 |
| Gilchrist | Florida | 12041 | complete-gte-5ac | 6,395 | fl-doh-ehwaters-12041 |
| Hernando | Florida | 12053 | complete-gte-5ac | 6,601 | fl-hernando-parcels-12053 |
| Levy | Florida | 12075 | complete-gte-5ac | 10,200 | fl-doh-ehwaters-12075 |
| Putnam | Florida | 12107 | complete-gte-5ac | 7,560 | fl-putnam-doh-municipal-12107 |

### Asheville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Buncombe | North Carolina | 37021 | complete-gte-5ac | 10,523 | nc-buncombe-opendata-37021 |
| Henderson | North Carolina | 37089 | complete-gte-5ac | 6,270 | nc-henderson-parcels-37089 |

### Tuscaloosa

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Greene | Alabama | 01063 | gap | 0 | unavailable |
| Hale | Alabama | 01065 | gap | 0 | unavailable |
| Pickens | Alabama | 01107 | gap | 0 | unavailable |
| Tuscaloosa | Alabama | 01125 | complete-gte-5ac | 11,596 | al-tuscaloosa-parcels |

### Montgomery

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Autauga | Alabama | 01001 | complete-gte-5ac | 7,047 | al-autauga-parcels |
| Elmore | Alabama | 01051 | complete-gte-5ac | 9,758 | al-elmore-parcels |
| Lowndes | Alabama | 01085 | gap | 0 | unavailable |
| Montgomery | Alabama | 01101 | complete-gte-5ac | 9,954 | al-montgomery-parcels |

