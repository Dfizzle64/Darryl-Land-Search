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

Municipal zoning, future land use, and Cobb/DeKalb batch-40 screening stay in [`muni-overlay-consolidator.md`](muni-overlay-consolidator.md). Those city codes are copied onto this shelf only when the parcel id still matches. The overlay does not add an Opportunity Zone, a school letter grade, or a base flood elevation. Polk's Orlando tiles still carry Lakeland, Bartow, Auburndale, Lake Alfred, and Lake Hamilton (`docs/polk-municipal.md`). Volusia city layers are in `docs/volusia-flagler-municipal.md`. Flagler has no parcel baseline here.

Marshall County, Alabama is the web5 Marshall/Public/37 5–150 acre extract. Zoning is null. Baldwin County keeps the existing parcel shelf and adds Daphne Class zoning, Daphne Future_Dev, and Fairhope base zoning. Fairhope AO/MO names are overlay notes, not zoning codes. Shelby County keeps the existing parcel shelf and adds Alabaster ZoneCode. Walker, Washington, and Escambia County, Alabama stay gaps. Morgan County stays the existing VAM extract already on this branch. No Opportunity Zone designation was added.

Carroll County, Georgia uses the OpenAddresses job 910028 parcel snapshot because the live county parcel service is blocked. Acreage is GIS area. Carrollton and Carroll-side Villa Rica supply the city CAMA, zoning, and future land use that matched a Carroll parcel id. County zoning and future land use remain PDFs. Sales are the commercial/industrial subset only. No Opportunity Zone designation was added.

Walton County, Georgia is the choosewalton 5–150 GIS-acre landbase. FLU and Description are character areas, not Euclidean zoning. Monroe CAMA matches a handful of shared parcel numbers. City zoning covers Monroe, Loganville, and Social Circle only. Countywide owner, tax, sales, and Euclidean zoning stay gaps. Nothing in that extract is an Opportunity Zone designation.

Newton County, Georgia is the University of Maryland AGOL redistribute (not an official county FeatureServer). Sales stop in 2021. County Euclidean zoning stays null except a Social Circle centroid join. Future land use is the NEGRC centroid join. Spalding County, Georgia is the public parcel view: owner, situs, sales, tax, and future land use stay null, and Griffin is left unzoned. Bradley County, Tennessee uses Census FIPS 47011 and the Cleveland GIS Parcels_Impact layer. The older Comptroller IMPACT tiles for that FIPS were the wrong geography and are replaced. The Tennessee card package is 9 usable / 7 partial / 0 gap, but the YAML files were not in this checkout, so those card URLs were not applied. The packaging note that says 47107 Bradley does not match this shelf: 47107 is McMinn County, and McMinn was not added. Yadkin County, North Carolina uses the county GIS parcel layer instead of NC OneMap. Bryan County, Georgia uses PropertyDetails. Sales are a Beacon gap, and assessed values on that layer are empty. Effingham County, Georgia uses Parcels2024. Sale price and market value are joined from ParcelUpdate or the 2024 FLUM. No Opportunity Zone designation was added for these counties.

Valdosta, Macon, Athens, Hilton Head, and Jackson MS are parcel shelves with no eligible-tract rows. Sources, zoning and future-land-use gaps, and the counties left off this pull are in `docs/new-metro-parcels.md`. Beaufort County also fills the previous Savannah gap. Tract income is ACS 5-year 2020–2024 B19013. Those counties use the same statewide AADT join as the rest of the footprint. Nothing in these extracts is an Opportunity Zone designation, a school letter grade, or a base flood elevation.

South Florida is a Wave 0 parcel shelf: Miami-Dade, Monroe, Broward, and Palm Beach only. Sources, zoning, future land use, property-appraiser links, and the Broward CAMA / Monroe TLS / Palm Beach TLS gaps are in `docs/south-florida-parcels.md`. Broward stays partial. No eligible-tract rows were added.

## Coverage

# Market parcel coverage

Acreage band is **5.0–150.0 inclusive**. Lake, Osceola, Seminole, and Sumter Orlando tiles were reseeded from county GIS. Polk market parcels use the property-appraiser extract. Orange still points at the Orlando tiles.

AADT is not copied onto these tiles. `/api/parcels` joins the nearest published count within 15 km. Florida uses FDOT RCI FeatureServer/0, field AADT, YEAR_=2025, for every footprint county. The nearest segment is the one closest to the parcel centroid, within 15 km. North Carolina gap counties use NCDOT 2024 stations, field AADT_2024 (a string; blanks dropped). Durham, Mecklenburg, and Wake stay on AADT_2022. South Carolina uses SCDOT 2025 Statewide Traffic Points, field FactoredAA, CountyName. Mississippi uses the HDR AGOL republish of RCI layer RC_AADT_2019, field ADT_21 (through 2021). COUNTYNMBR is the alphabetical county number, not FIPS, and this is not an MDOT-hosted FeatureServer. Tennessee uses TDOT Traffic Lines, field AADT, AADTYEAR 2025. COUNTY_NUMBER is the zero-padded alphabetical code, not FIPS. Arkansas uses ARDOT ADT Linear, field MostRecentADT, Year_ADT 2025, for Crittenden and Mississippi County. County is the ARDOT number, not FIPS. Actual stations only. Georgia uses the DeKalb County GIS republish of GDOT stations, field aadt, for every footprint county including Bibb, Cobb, DeKalb, Fulton, and Lowndes. That layer has no year field. Alabama uses ALDOT TDM TrafficCounterPoint, field AADT, YearAADT=2024. LUCountyID is the alphabetical county index, not FIPS, and 2025 AADT values are null. Counts are the published field. Zero and missing values are dropped. Nothing is estimated.

Parcels stay off until neighborhood zoom, an area lock, or Show parcels. The map requests the selected market's viewport tiles only.

| Market | Tier | Parcels | Complete counties | Sample or partial | Gaps |
| --- | --- | ---: | ---: | ---: | ---: |
| Atlanta | primary | 93,811 | 17 | 0 | 18 |
| Tampa | primary | 124,315 | 10 | 0 | 0 |
| Charleston | primary | 22,649 | 3 | 0 | 4 |
| Nashville | primary | 109,348 | 13 | 0 | 4 |
| Charlotte | primary | 106,650 | 12 | 0 | 3 |
| Raleigh-Durham | primary | 151,530 | 17 | 0 | 0 |
| South Florida | shelf | — | 3 | 1 | 0 |
| SWFL | other | 32,749 | 4 | 0 | 0 |
| Vero Beach | other | 23,009 | 5 | 0 | 0 |
| Melbourne | other | 41,026 | 5 | 0 | 0 |
| Jacksonville | other | 26,301 | 5 | 0 | 0 |
| Big Bend | other | 21,551 | 1 | 3 | 3 |
| Pensacola | other | 59,902 | 6 | 0 | 0 |
| Birmingham | other | 38,101 | 3 | 0 | 6 |
| Mobile | other | 42,446 | 3 | 0 | 2 |
| Huntsville | other | 29,598 | 4 | 0 | 3 |
| Savannah | other | 16,305 | 4 | 0 | 4 |
| Columbia | other | 14,613 | 1 | 1 | 8 |
| Greenville | other | 31,164 | 2 | 0 | 6 |
| Chattanooga | other | 15,498 | 2 | 0 | 8 |
| Knoxville | other | 39,939 | 7 | 0 | 6 |
| Memphis | other | 45,278 | 8 | 0 | 3 |
| Jackson | other | 6,384 | 1 | 0 | 0 |
| Winston-Salem | other | 92,199 | 9 | 0 | 0 |
| Wilmington | other | 47,320 | 6 | 0 | 0 |
| Heartland | shelf | 21,163 | 4 | 1 | 0 |
| North-Central Florida | other | 52,695 | 7 | 0 | 0 |
| Asheville | other | 16,793 | 2 | 0 | 0 |
| Tuscaloosa | other | 11,596 | 1 | 0 | 3 |
| Montgomery | other | 26,759 | 3 | 0 | 1 |
| Valdosta | other | 5,815 | 1 | 0 | 0 |
| Macon | other | 3,257 | 1 | 0 | 0 |
| Athens | other | 2,039 | 1 | 0 | 0 |
| Hilton Head | other | 4,756 | 1 | 0 | 0 |
| Jackson MS | other | 57,020 | 7 | 0 | 0 |

## Counties

### Atlanta

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Banks | Georgia | 13011 | gap | 0 | unavailable |
| Barrow | Georgia | 13013 | complete-gte-5ac | 4,251 | ga-barrow-parcels |
| Bartow | Georgia | 13015 | complete-gte-5ac | 7,077 | ga-bartow-land |
| Butts | Georgia | 13035 | gap | 0 | unavailable |
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
| Hall | Georgia | 13139 | gap | 0 | unavailable |
| Haralson | Georgia | 13143 | gap | 0 | unavailable |
| Heard | Georgia | 13149 | gap | 0 | unavailable |
| Henry | Georgia | 13151 | complete-gte-5ac | 7,418 | ga-henry-parcels |
| Jackson | Georgia | 13157 | gap | 0 | unavailable |
| Jasper | Georgia | 13159 | gap | 0 | unavailable |
| Lamar | Georgia | 13171 | gap | 0 | unavailable |
| Lumpkin | Georgia | 13187 | gap | 0 | unavailable |
| Meriwether | Georgia | 13199 | gap | 0 | unavailable |
| Monroe | Georgia | 13207 | gap | 0 | unavailable |
| Morgan | Georgia | 13211 | gap | 0 | unavailable |
| Newton | Georgia | 13217 | complete-gte-5ac | 4,474 | ga-newton-uofmd-parcels |
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

Manatee and Sarasota keep those DOH shelves. City zoning is on 221 Manatee parcels and 566 Sarasota parcels. Future land use is on 247 Manatee parcels and 124 Sarasota parcels. Bradenton, Palmetto, Longboat Key, and the City of Sarasota have both. North Port and Venice are zoning only. Anna Maria, Bradenton Beach, and Holmes Beach stay blank. Sources are in `docs/muni-overlay-consolidator.md`. County parcels were not re-downloaded.

Charlotte County, Florida (FIPS 12015) is not on these shelves. Punta Gorda city zoning and future land use are cataloged and were not stamped, because no county parcels were downloaded. County `CITY` stubs are not stored.

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

Martin and Indian River keep those DOH shelves. City zoning and future land use are stamped on top: Martin 203 zoning and 201 future land use; Indian River 191 zoning and 104 future land use. Stuart, Indiantown, and Vero Beach have both. Sebastian is zoning only. Ocean Breeze, Sewall's Point, Jupiter Island, Fellsmere, Indian River Shores, and Orchid stay blank. Sources are in `docs/muni-overlay-consolidator.md`. County parcels were not re-downloaded.

### Melbourne

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Brevard | Florida | 12009 | complete-gte-5ac | 6,802 | fl-brevard-accela-12009 |
| Indian River | Florida | 12061 | complete-gte-5ac | 3,779 | fl-ircpa-parcels-12061 |
| Orange | Florida | 12095 | complete-gte-5ac | 11,709 | reused-orlando-ocpa-5-150 |
| Osceola | Florida | 12097 | complete-gte-5ac | 6,169 | reused-orlando-complete-5-150 |
| Volusia | Florida | 12127 | complete-gte-5ac | 12,567 | fl-doh-ehwaters-12127 |

Brevard city zoning and future land use are cataloged in [`brevard-municipal.md`](brevard-municipal.md). Codes from that join are copied onto this Accela shelf only when the parcel id still matches. Cocoa Beach stays the unofficial 2021 layer when that stamp matches. Palm Bay and Titusville are not filled from a county code.

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

City zoning on these four shelves is in `docs/muni-overlay-consolidator.md`. Escambia has Pensacola zoning on 810 parcels. Okaloosa has Destin and Fort Walton Beach zoning and future land use on 270 parcels. Santa Rosa has 85 zoning codes and 9 future land use codes (Milton and Jay zoning, Gulf Breeze both). Walton has 135 zoning codes and 158 future land use codes (DeFuniak Springs both, Paxton future land use). Panama City Beach city layers sit in Bay County and miss the Walton PCB parcels. Bay County has no parcel shelf here, so Panama City, Callaway, Mexico Beach, Lynn Haven, Parker, and Springfield are indexed only. Freeport numeric codes stay blank. Crestview, Niceville, Valparaiso, Mary Esther, Laurel Hill, Shalimar, Cinco Bayou, Century, and Pensacola Beach stay blank. County parcels were not re-downloaded.

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
| Beaufort | South Carolina | 45013 | complete-gte-5ac | 4,756 | sc-beaufort-energov-parcels |
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
| Yadkin | North Carolina | 37197 | complete-gte-5ac | 8,102 | nc-yadkin-county-gis |

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

### Valdosta

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Lowndes | Georgia | 13185 | complete-gte-5ac | 5,815 | ga-lowndes-valor-taxparcels |

### Macon

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Bibb | Georgia | 13021 | complete-gte-5ac | 3,257 | ga-bibb-parcelcama-2025 |

### Athens

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Clarke | Georgia | 13059 | complete-gte-5ac | 2,039 | ga-clarke-acc-parcels |

### Hilton Head

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Beaufort | South Carolina | 45013 | complete-gte-5ac | 4,756 | sc-beaufort-energov-parcels |

### Jackson MS

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Copiah | Mississippi | 28029 | complete-gte-5ac | 6,731 | ms-copiah-cmpdd-parcels |
| Hinds | Mississippi | 28049 | complete-gte-5ac | 11,375 | ms-hinds-maris-august-2024 |
| Madison | Mississippi | 28089 | complete-gte-5ac | 10,002 | ms-madison-cmpdd-parcels |
| Rankin | Mississippi | 28121 | complete-gte-5ac | 12,150 | ms-rankin-cmpdd-parcels |
| Simpson | Mississippi | 28127 | complete-gte-5ac | 7,372 | ms-simpson-cmpdd-parcels |
| Warren | Mississippi | 28149 | complete-gte-5ac | 3,473 | ms-warren-cmpdd-parcels |
| Yazoo | Mississippi | 28163 | complete-gte-5ac | 5,917 | ms-yazoo-cmpdd-2026-parcels |

