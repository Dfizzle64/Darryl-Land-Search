# Market parcels (every MSA except Orlando)

Orlando keeps `scripts/seed_orlando_parcels.py` and `data/fixtures/orlando-parcels`. This pull does not rewrite those tiles.

Other markets use the same 0.25° tile grid (origin longitude -83, latitude 27) under `data/fixtures/market-parcels/counties/{fips}/tiles`. The home page does not embed the polygons. `GET /api/parcels?market={Market}&bbox=w,s,e,n` reads only the tiles for **that market** that intersect the viewport. Outlines stay off until neighborhood zoom (about 10.5), an area is locked, or Show parcels is on — the same gate as Orlando.

Orange, Osceola, and Polk already have a complete 5.0–150.0 acre Orlando extract. Tampa and Melbourne point at those tiles instead of downloading them again.

## Refresh

```bash
npm run seed:parcels:markets
python3 scripts/seed_market_parcels.py --market Charlotte
python3 scripts/seed_market_parcels.py --market Tampa --county Hardee
python3 scripts/seed_market_parcels.py --refresh
```

A finished county is skipped unless `--refresh` is passed. Cached normalized features, when present, live under `/tmp/dls-market-parcels`.

## Sources

| State | Endpoint | What shipped |
| --- | --- | --- |
| Florida | Florida DOH EHWATER Parcels | Complete 5–150 acre extract where the county is not already an Orlando complete county |
| North Carolina | NC OneMap `NC1Map_Parcels` polygons | Complete 5–150 acre extract. Most counties use `gisacres`. Cleveland, Columbus, Orange, and Warren store polygon acres because `gisacres` is 0 |
| Tennessee | Comptroller IMPACT Parcels | Complete where `CALC_ACRE` returns rows. Several large counties are absent from that layer and stay gaps |
| Mississippi | MDEQ statewide parcels (2023) | Complete 5–150 acre extract on `GISACRES` |
| Arkansas | Arkansas GIS cadastre polygons | Complete band using polygon-derived acres |
| Georgia | Cobb and DeKalb county services only | Cobb complete. DeKalb is a polygon-acre sample. Other Georgia counties are gaps |
| South Carolina | Dorchester public parcels; Greenville city GIS | Dorchester complete. Greenville is a city-hosted sample. Charleston County's GIS requires a token. Other counties are gaps |
| Alabama | Jefferson parcels; Madison Public ISV/185; Limestone Remap/1; Morgan VAM/10 | Jefferson, Madison, Limestone, and Morgan are complete 5–150 acre extracts. Huntsville ZoningDistricts/5 and City of Madison layers 57+58+59+73 are centroid-joined onto Madison and Limestone (both cities cross those counties). Marshall has no countywide REST (CombinedParcels/9 is a 137-feature sample). Decatur zoning is MapGeo-only. Other Alabama counties stay gaps |

Zoning is joined when the county layer carries a zoning field (DeKalb) or when a city overlay is configured. Huntsville and City of Madison overlays are not limited to one county FIPS. City of Madison zoning is the union of DV_PlanningPro1_MIL1 layers 57, 58, 59, and 73. The Layers/MapServer path on maps.madisonal.gov returns 404 and is not used. Joined codes are not a multifamily knowledge-base match outside Orange County. Prefer **All parcels** in these markets.

## Coverage

# Market parcel coverage

Acreage band is **5.0–150.0 inclusive**. Orlando is not re-scraped. Complete Orlando counties that also sit in another shed (Orange, Osceola, Polk) are reused in place.

Parcels stay off until neighborhood zoom, an area lock, or Show parcels. The map requests the selected market's viewport tiles only.

| Market | Tier | Parcels | Complete counties | Sample counties | Gaps |
| --- | --- | ---: | ---: | ---: | ---: |
| Atlanta | primary | 8,149 | 1 | 1 | 33 |
| Tampa | primary | 98,259 | 10 | 0 | 0 |
| Charleston | primary | 6,774 | 1 | 0 | 6 |
| Nashville | primary | 31,132 | 6 | 0 | 11 |
| Charlotte | primary | 119,168 | 12 | 0 | 3 |
| Raleigh-Durham | primary | 153,279 | 17 | 0 | 0 |
| Vero Beach | other | 20,964 | 5 | 0 | 0 |
| Melbourne | other | 39,435 | 5 | 0 | 0 |
| Pensacola | other | 30,141 | 4 | 0 | 1 |
| Birmingham | other | 15,641 | 1 | 0 | 9 |
| Mobile | other | 7,189 | 1 | 0 | 4 |
| Huntsville | other | 18,584 | 3 | 0 | 4 |
| Savannah | other | 0 | 0 | 0 | 8 |
| Columbia | other | 0 | 0 | 0 | 10 |
| Greenville | other | 1,570 | 0 | 1 | 7 |
| Chattanooga | other | 10,537 | 2 | 0 | 8 |
| Knoxville | other | 38,433 | 7 | 0 | 6 |
| Memphis | other | 35,611 | 7 | 0 | 4 |
| Winston-Salem | other | 91,784 | 9 | 0 | 0 |
| Wilmington | other | 46,720 | 6 | 0 | 0 |

## Counties

### Atlanta

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Banks | Georgia | 13011 | gap | 0 | unavailable |
| Barrow | Georgia | 13013 | gap | 0 | unavailable |
| Bartow | Georgia | 13015 | gap | 0 | unavailable |
| Butts | Georgia | 13035 | gap | 0 | unavailable |
| Carroll | Georgia | 13045 | gap | 0 | unavailable |
| Cherokee | Georgia | 13057 | gap | 0 | unavailable |
| Clayton | Georgia | 13063 | gap | 0 | unavailable |
| Cobb | Georgia | 13067 | complete-gte-5ac | 4,780 | ga-cobb-parcels |
| Coweta | Georgia | 13077 | gap | 0 | unavailable |
| Dawson | Georgia | 13085 | gap | 0 | unavailable |
| DeKalb | Georgia | 13089 | sample | 3,369 | ga-dekalb-tax-parcels |
| Douglas | Georgia | 13097 | gap | 0 | unavailable |
| Fayette | Georgia | 13113 | gap | 0 | unavailable |
| Forsyth | Georgia | 13117 | gap | 0 | unavailable |
| Fulton | Georgia | 13121 | gap | 0 | unavailable |
| Gordon | Georgia | 13129 | gap | 0 | unavailable |
| Gwinnett | Georgia | 13135 | gap | 0 | unavailable |
| Hall | Georgia | 13139 | gap | 0 | unavailable |
| Haralson | Georgia | 13143 | gap | 0 | unavailable |
| Heard | Georgia | 13149 | gap | 0 | unavailable |
| Henry | Georgia | 13151 | gap | 0 | unavailable |
| Jackson | Georgia | 13157 | gap | 0 | unavailable |
| Jasper | Georgia | 13159 | gap | 0 | unavailable |
| Lamar | Georgia | 13171 | gap | 0 | unavailable |
| Lumpkin | Georgia | 13187 | gap | 0 | unavailable |
| Meriwether | Georgia | 13199 | gap | 0 | unavailable |
| Monroe | Georgia | 13207 | gap | 0 | unavailable |
| Morgan | Georgia | 13211 | gap | 0 | unavailable |
| Newton | Georgia | 13217 | gap | 0 | unavailable |
| Paulding | Georgia | 13223 | gap | 0 | unavailable |
| Pickens | Georgia | 13227 | gap | 0 | unavailable |
| Pike | Georgia | 13231 | gap | 0 | unavailable |
| Rockdale | Georgia | 13247 | gap | 0 | unavailable |
| Spalding | Georgia | 13255 | gap | 0 | unavailable |
| Walton | Georgia | 13297 | gap | 0 | unavailable |

### Tampa

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Citrus | Florida | 12017 | complete-gte-5ac | 5,810 | fl-doh-ehwaters-12017 |
| Hardee | Florida | 12049 | complete-gte-5ac | 5,055 | fl-doh-ehwaters-12049 |
| Hernando | Florida | 12053 | complete-gte-5ac | 7,180 | fl-doh-ehwaters-12053 |
| Hillsborough | Florida | 12057 | complete-gte-5ac | 13,351 | fl-doh-ehwaters-12057 |
| Manatee | Florida | 12081 | complete-gte-5ac | 7,239 | fl-doh-ehwaters-12081 |
| Pasco | Florida | 12101 | complete-gte-5ac | 10,590 | fl-doh-ehwaters-12101 |
| Pinellas | Florida | 12103 | complete-gte-5ac | 18,638 | fl-doh-ehwaters-12103 |
| Polk | Florida | 12105 | complete-gte-5ac | 19,734 | reused-orlando-complete-5-150 |
| Sarasota | Florida | 12115 | complete-gte-5ac | 4,303 | fl-doh-ehwaters-12115 |
| Sumter | Florida | 12119 | complete-gte-5ac | 6,359 | fl-doh-ehwaters-12119 |

### Charleston

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Berkeley | South Carolina | 45015 | gap | 0 | unavailable |
| Charleston | South Carolina | 45019 | gap | 0 | unavailable |
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
| Cheatham | Tennessee | 47021 | complete-gte-5ac | 3,790 | tn-impact-47021 |
| Davidson | Tennessee | 47037 | complete-gte-5ac | 8,286 | tn-impact-47037 |
| Dickson | Tennessee | 47043 | complete-gte-5ac | 4,797 | tn-impact-47043 |
| Hickman | Tennessee | 47081 | complete-gte-5ac | 3,672 | tn-impact-47081 |
| Macon | Tennessee | 47111 | gap | 0 | tn-impact-47111 |
| Marshall | Tennessee | 47117 | gap | 0 | tn-impact-47117 |
| Maury | Tennessee | 47119 | gap | 0 | tn-impact-47119 |
| Montgomery | Tennessee | 47125 | gap | 0 | tn-impact-47125 |
| Robertson | Tennessee | 47147 | gap | 0 | tn-impact-47147 |
| Rutherford | Tennessee | 47149 | gap | 0 | tn-impact-47149 |
| Smith | Tennessee | 47159 | gap | 0 | tn-impact-47159 |
| Sumner | Tennessee | 47165 | gap | 0 | tn-impact-47165 |
| Trousdale | Tennessee | 47169 | gap | 0 | tn-impact-47169 |
| Williamson | Tennessee | 47187 | gap | 0 | tn-impact-47187 |
| Wilson | Tennessee | 47189 | gap | 0 | tn-impact-47189 |

### Charlotte

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Anson | North Carolina | 37007 | complete-gte-5ac | 5,814 | nc-onemap-37007 |
| Cabarrus | North Carolina | 37025 | complete-gte-5ac | 6,974 | nc-onemap-37025 |
| Catawba | North Carolina | 37035 | complete-gte-5ac | 8,502 | nc-onemap-37035 |
| Chester | South Carolina | 45023 | gap | 0 | unavailable |
| Cleveland | North Carolina | 37045 | complete-gte-5ac | 9,310 | nc-onemap-37045 |
| Davidson | North Carolina | 37057 | complete-gte-5ac | 11,685 | nc-onemap-37057 |
| Gaston | North Carolina | 37071 | complete-gte-5ac | 6,816 | nc-onemap-37071 |
| Iredell | North Carolina | 37097 | complete-gte-5ac | 10,771 | nc-onemap-37097 |
| Lancaster | South Carolina | 45057 | gap | 0 | unavailable |
| Lincoln | North Carolina | 37109 | complete-gte-5ac | 6,543 | nc-onemap-37109 |
| Mecklenburg | North Carolina | 37119 | complete-gte-5ac | 21,331 | nc-onemap-37119 |
| Rowan | North Carolina | 37159 | complete-gte-5ac | 10,347 | nc-onemap-37159 |
| Stanly | North Carolina | 37167 | complete-gte-5ac | 8,024 | nc-onemap-37167 |
| Union | North Carolina | 37179 | complete-gte-5ac | 13,051 | nc-onemap-37179 |
| York | South Carolina | 45091 | gap | 0 | unavailable |

### Raleigh-Durham

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Alamance | North Carolina | 37001 | complete-gte-5ac | 8,846 | nc-onemap-37001 |
| Chatham | North Carolina | 37037 | complete-gte-5ac | 13,229 | nc-onemap-37037 |
| Durham | North Carolina | 37063 | complete-gte-5ac | 4,934 | nc-onemap-37063 |
| Franklin | North Carolina | 37069 | complete-gte-5ac | 7,639 | nc-onemap-37069 |
| Granville | North Carolina | 37077 | complete-gte-5ac | 7,150 | nc-onemap-37077 |
| Harnett | North Carolina | 37085 | complete-gte-5ac | 11,657 | nc-onemap-37085 |
| Johnston | North Carolina | 37101 | complete-gte-5ac | 14,113 | nc-onemap-37101 |
| Lee | North Carolina | 37105 | complete-gte-5ac | 4,858 | nc-onemap-37105 |
| Nash | North Carolina | 37127 | complete-gte-5ac | 8,292 | nc-onemap-37127 |
| Orange | North Carolina | 37135 | complete-gte-5ac | 11,139 | nc-onemap-37135 |
| Person | North Carolina | 37145 | complete-gte-5ac | 5,956 | nc-onemap-37145 |
| Sampson | North Carolina | 37163 | complete-gte-5ac | 14,031 | nc-onemap-37163 |
| Vance | North Carolina | 37181 | complete-gte-5ac | 3,181 | nc-onemap-37181 |
| Wake | North Carolina | 37183 | complete-gte-5ac | 12,427 | nc-onemap-37183 |
| Warren | North Carolina | 37185 | complete-gte-5ac | 5,596 | nc-onemap-37185 |
| Wayne | North Carolina | 37191 | complete-gte-5ac | 15,079 | nc-onemap-37191 |
| Wilson | North Carolina | 37195 | complete-gte-5ac | 5,152 | nc-onemap-37195 |

### Vero Beach

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Brevard | Florida | 12009 | complete-gte-5ac | 5,746 | fl-doh-ehwaters-12009 |
| Indian River | Florida | 12061 | complete-gte-5ac | 3,416 | fl-doh-ehwaters-12061 |
| Martin | Florida | 12085 | complete-gte-5ac | 3,802 | fl-doh-ehwaters-12085 |
| Okeechobee | Florida | 12093 | complete-gte-5ac | 3,176 | fl-doh-ehwaters-12093 |
| St. Lucie | Florida | 12111 | complete-gte-5ac | 4,824 | fl-doh-ehwaters-12111 |

### Melbourne

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Brevard | Florida | 12009 | complete-gte-5ac | 5,746 | fl-doh-ehwaters-12009 |
| Indian River | Florida | 12061 | complete-gte-5ac | 3,416 | fl-doh-ehwaters-12061 |
| Orange | Florida | 12095 | complete-gte-5ac | 11,709 | reused-orlando-ocpa-5-150 |
| Osceola | Florida | 12097 | complete-gte-5ac | 5,997 | reused-orlando-complete-5-150 |
| Volusia | Florida | 12127 | complete-gte-5ac | 12,567 | fl-doh-ehwaters-12127 |

### Pensacola

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Baldwin | Alabama | 01003 | gap | 0 | unavailable |
| Escambia | Florida | 12033 | complete-gte-5ac | 9,097 | fl-doh-ehwaters-12033 |
| Okaloosa | Florida | 12091 | complete-gte-5ac | 5,854 | fl-doh-ehwaters-12091 |
| Santa Rosa | Florida | 12113 | complete-gte-5ac | 7,011 | fl-doh-ehwaters-12113 |
| Walton | Florida | 12131 | complete-gte-5ac | 8,179 | fl-doh-ehwaters-12131 |

### Birmingham

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Bibb | Alabama | 01007 | gap | 0 | unavailable |
| Blount | Alabama | 01009 | gap | 0 | unavailable |
| Chilton | Alabama | 01021 | gap | 0 | unavailable |
| Cullman | Alabama | 01043 | gap | 0 | unavailable |
| Jefferson | Alabama | 01073 | complete-gte-5ac | 15,641 | al-jefferson-parcels |
| Shelby | Alabama | 01117 | gap | 0 | unavailable |
| St. Clair | Alabama | 01115 | gap | 0 | unavailable |
| Talladega | Alabama | 01121 | gap | 0 | unavailable |
| Tuscaloosa | Alabama | 01125 | gap | 0 | unavailable |
| Walker | Alabama | 01127 | gap | 0 | unavailable |

### Mobile

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Baldwin | Alabama | 01003 | gap | 0 | unavailable |
| Escambia | Alabama | 01053 | gap | 0 | unavailable |
| George | Mississippi | 28039 | complete-gte-5ac | 7,189 | ms-mdeq-2023-28039 |
| Mobile | Alabama | 01097 | gap | 0 | unavailable |
| Washington | Alabama | 01129 | gap | 0 | unavailable |

### Huntsville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Cullman | Alabama | 01043 | gap | 0 | unavailable |
| Jackson | Alabama | 01071 | gap | 0 | unavailable |
| Limestone | Alabama | 01083 | complete-gte-5ac | 5,445 | al-limestone-remap-1 |
| Lincoln | Tennessee | 47103 | gap | 0 | tn-impact-47103 |
| Madison | Alabama | 01089 | complete-gte-5ac | 12,312 | al-madison-public-isv-185 |
| Marshall | Alabama | 01095 | gap | 0 | unavailable |
| Morgan | Alabama | 01103 | complete-gte-5ac | 827 | al-morgan-vam-10 |

### Savannah

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Beaufort | South Carolina | 45013 | gap | 0 | unavailable |
| Bryan | Georgia | 13029 | gap | 0 | unavailable |
| Bulloch | Georgia | 13031 | gap | 0 | unavailable |
| Chatham | Georgia | 13051 | gap | 0 | unavailable |
| Effingham | Georgia | 13103 | gap | 0 | unavailable |
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
| Lexington | South Carolina | 45063 | gap | 0 | unavailable |
| Newberry | South Carolina | 45071 | gap | 0 | unavailable |
| Orangeburg | South Carolina | 45075 | gap | 0 | unavailable |
| Richland | South Carolina | 45079 | gap | 0 | unavailable |
| Saluda | South Carolina | 45081 | gap | 0 | unavailable |
| Sumter | South Carolina | 45085 | gap | 0 | unavailable |

### Greenville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Abbeville | South Carolina | 45001 | gap | 0 | unavailable |
| Anderson | South Carolina | 45007 | gap | 0 | unavailable |
| Greenville | South Carolina | 45045 | sample | 1,570 | sc-greenville-city-gis |
| Greenwood | South Carolina | 45047 | gap | 0 | unavailable |
| Laurens | South Carolina | 45059 | gap | 0 | unavailable |
| Oconee | South Carolina | 45073 | gap | 0 | unavailable |
| Pickens | South Carolina | 45077 | gap | 0 | unavailable |
| Spartanburg | South Carolina | 45083 | gap | 0 | unavailable |

### Chattanooga

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Bradley | Tennessee | 47011 | complete-gte-5ac | 5,429 | tn-impact-47011 |
| Catoosa | Georgia | 13047 | gap | 0 | unavailable |
| Dade | Georgia | 13083 | gap | 0 | unavailable |
| Hamilton | Tennessee | 47065 | complete-gte-5ac | 5,108 | tn-impact-47065 |
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
| Blount | Tennessee | 47009 | complete-gte-5ac | 6,102 | tn-impact-47009 |
| Campbell | Tennessee | 47013 | complete-gte-5ac | 5,445 | tn-impact-47013 |
| Cocke | Tennessee | 47029 | complete-gte-5ac | 4,448 | tn-impact-47029 |
| Grainger | Tennessee | 47057 | complete-gte-5ac | 6,406 | tn-impact-47057 |
| Hamblen | Tennessee | 47063 | gap | 0 | tn-impact-47063 |
| Jefferson | Tennessee | 47089 | complete-gte-5ac | 6,586 | tn-impact-47089 |
| Knox | Tennessee | 47093 | complete-gte-5ac | 5,144 | tn-impact-47093 |
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
| Shelby | Tennessee | 47157 | gap | 0 | tn-impact-47157 |
| Tate | Mississippi | 28137 | complete-gte-5ac | 5,758 | ms-mdeq-2023-28137 |
| Tipton | Tennessee | 47167 | gap | 0 | tn-impact-47167 |
| Tunica | Mississippi | 28143 | complete-gte-5ac | 1,842 | ms-mdeq-2023-28143 |

### Winston-Salem

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Davidson | North Carolina | 37057 | complete-gte-5ac | 11,685 | nc-onemap-37057 |
| Davie | North Carolina | 37059 | complete-gte-5ac | 5,721 | nc-onemap-37059 |
| Forsyth | North Carolina | 37067 | complete-gte-5ac | 8,134 | nc-onemap-37067 |
| Guilford | North Carolina | 37081 | complete-gte-5ac | 12,953 | nc-onemap-37081 |
| Randolph | North Carolina | 37151 | complete-gte-5ac | 16,449 | nc-onemap-37151 |
| Rockingham | North Carolina | 37157 | complete-gte-5ac | 9,378 | nc-onemap-37157 |
| Stokes | North Carolina | 37169 | complete-gte-5ac | 8,826 | nc-onemap-37169 |
| Surry | North Carolina | 37171 | complete-gte-5ac | 10,547 | nc-onemap-37171 |
| Yadkin | North Carolina | 37197 | complete-gte-5ac | 8,091 | nc-onemap-37197 |

### Wilmington

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Brunswick | North Carolina | 37019 | complete-gte-5ac | 7,020 | nc-onemap-37019 |
| Columbus | North Carolina | 37047 | complete-gte-5ac | 12,025 | nc-onemap-37047 |
| Duplin | North Carolina | 37061 | complete-gte-5ac | 11,397 | nc-onemap-37061 |
| New Hanover | North Carolina | 37129 | complete-gte-5ac | 2,256 | nc-onemap-37129 |
| Onslow | North Carolina | 37133 | complete-gte-5ac | 6,747 | nc-onemap-37133 |
| Pender | North Carolina | 37141 | complete-gte-5ac | 7,275 | nc-onemap-37141 |

