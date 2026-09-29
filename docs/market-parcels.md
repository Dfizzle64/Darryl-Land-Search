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

Newton County, Georgia is the University of Maryland AGOL redistribute (not an official county FeatureServer). Sales stop in 2021. County Euclidean zoning stays null except a Social Circle centroid join. Future land use is the NEGRC centroid join. Spalding County, Georgia is the public parcel view: owner, situs, sales, tax, and future land use stay null, and Griffin is left unzoned. Bradley County, Tennessee uses Census FIPS 47011 and the Cleveland GIS Parcels_Impact layer. The older Comptroller IMPACT tiles for that FIPS were the wrong geography and are replaced. Yadkin County, North Carolina uses the county GIS parcel layer instead of NC OneMap. Bryan County, Georgia uses PropertyDetails. Sales are a Beacon gap, and assessed values on that layer are empty. Effingham County, Georgia uses Parcels2024. Sale price and market value are joined from ParcelUpdate or the 2024 FLUM. No Opportunity Zone designation was added for these counties.

Valdosta, Macon, Athens, Hilton Head, and Jackson MS are parcel shelves with no eligible-tract rows. Sources, zoning and future-land-use gaps, and the counties left off this pull are in `docs/new-metro-parcels.md`. Beaufort County also fills the previous Savannah gap. Tract income is ACS 5-year 2020–2024 B19013. Those counties use the same statewide AADT join as the rest of the footprint. Nothing in these extracts is an Opportunity Zone designation, a school letter grade, or a base flood elevation.

South Carolina rural Opportunity Zone batch 1 loads 5.0–150.0 acre parcels for the first 20 interim-list counties that were not already a complete extract and whose card endpoint answered: Abbeville, Aiken, Allendale, Bamberg, Barnwell, Cherokee, Chester, Chesterfield, Clarendon, Colleton, Darlington, Dillon, Edgefield, Fairfield, Florence, Georgetown, Greenwood, Hampton, Horry, and Jasper. Anderson's NewPropertyViewer service closed the TLS connection and was skipped. Beaufort, Charleston, Dorchester, and Greenville were already on the card endpoint. Berkeley stays the existing Addr_muni extract. Edgefield uses the new RFA Edgefield_McCormick_Greenwood layer 9. City cards (Hilton Head, Myrtle Beach, and the other municipalities) are not this batch. qPublic and Beacon property-appraiser patterns are stored and were not requested. Owner phone and email are not ingested. Sale dates after the pull date are cleared. No Opportunity Zone status was added. AADT wiring and tract eligibility were not changed.

Alabama rural Opportunity Zone batch 1 loads 5.0–150.0 acre parcels for the first 20 priority-list counties that had a public parcel layer, were not already a complete extract, and whose card endpoint answered: Calhoun, Dallas, DeKalb, Etowah, Talladega, Macon, Jackson, Barbour, Franklin, Lauderdale, Monroe, Blount, Cullman, Bullock, Greene, Sumter, Wilcox, Hale, Winston, and Cherokee. Colbert's KCS service was not started and was skipped. Flagship counties with no public parcel REST were skipped. Limestone, Marshall, Baldwin, St. Clair, Madison, Mobile, Morgan, Elmore, Autauga, Jefferson, Shelby, and Montgomery were already complete and were not re-pulled. The loader strips leading zeros from a Mobile account number for links; Mobile itself was not re-pulled. Shelby stays the existing Cadastral_2025 extract, and the loader reads that card's field map as written. Counties already on a shelf stayed there. The others were added to the nearest existing Alabama shelf: Birmingham, Huntsville, Montgomery, Mobile, or Tuscaloosa. No new market shelf was added. Macon, Barbour, and Monroe use partial public layers. Sumter has no acre field and Wilcox's acre field is sparse, so those two use geodesic polygon area. Blount acreage is CalculatedAcreage because DeededAcres is empty on most parcels. Property-appraiser links are stored from the card pattern and were not requested. Owner phone and email are not ingested. Sale dates after the pull date are cleared. No Opportunity Zone status was added. AADT wiring and tract eligibility were not changed.

North Carolina rural Opportunity Zone batch 1 loads 5.0–150.0 acre parcels for the first 20 pass-1 counties that were verified or fixed, were not already a complete extract, and whose card endpoint answered: Alexander, Alleghany, Ashe, Avery, Beaufort, Bertie, Bladen, Burke, Caldwell, Carteret, Caswell, Cherokee, Chowan, Craven, Dare, Edgecombe, Graham, Greene, Halifax, and Haywood. Buncombe and Henderson were already complete and were not re-pulled. No endpoint in that stretch was unreachable. Alexander pages with orderByFields because the MapServer has no object id; its returnCountOnly figure repeats PROPERTY 99999 rows, so the stored count is the distinct parcel ids that page. Ashe pages with resultRecordCount. Counties already on a shelf stayed there. The others were added to the nearest existing North Carolina shelf: Asheville, Charlotte, Raleigh-Durham, Wilmington, or Winston-Salem. No new market shelf was added. Pass 2 tax, sale, owner, property-appraiser, and county GIS attributes are stored where the card or rural-oz-pass2 result published them. Chowan tax values were scrubbed on the layer and were not copied. Alleghany tax is the NC OneMap fallback join. Property-appraiser links are stored from the card or pass-2 pattern and were not requested. Owner phone and email are not ingested. Sale dates after the pull date are cleared. No Opportunity Zone status was added. NCDOT AADT stays the query-time statewide join. Household income stays ACS B19013_001E. Tract display was not changed.

North Carolina rural Opportunity Zone batch 2 loads 5.0–150.0 acre parcels for the next 20 pass-1 counties starting at Hertford that were verified or fixed, were not already a complete extract, and whose card endpoint answered: Hertford, Hoke, Hyde, Jackson, Jones, Lenoir, McDowell, Macon, Madison, Martin, Mitchell, Montgomery, Moore, Northampton, Pamlico, Pasquotank, Pitt, Polk, Richmond, and Robeson. No county in that stretch was already a complete extract, and no endpoint was unreachable. Rutherford was the next verified row and was not loaded because the batch of 20 was already filled. Jackson pages with resultRecordCount, and AssessedAcres is filtered with CAST AS FLOAT. Hoke uses the county AGOL June2025 layer, which has geometry, parcel id, and acreage only. Hoke, Mitchell, and Robeson repeat a parcel id across rows; the extract keeps one geometry per parcel id. Madison tax is the NC OneMap fallback join, and that county has no sale date on the public layer. Hyde has no sale price or date on the public layer. Robeson tax fields are land and improvement assessed values and are not summed into a total. Counties were added to the nearest existing North Carolina shelf: Asheville, Charlotte, Raleigh-Durham, Wilmington, or Winston-Salem. No new market shelf was added. Pass 2 tax, sale, owner, property-appraiser, and county GIS attributes are stored where the card or rural-oz-pass2 result published them. Property-appraiser links are stored from the card or pass-2 pattern and were not requested. A pass-2 sample account id is not copied onto every parcel. Owner phone and email are not ingested. A confidential-owner flag suppresses owner and mailing fields. Sale dates after the pull date are cleared. No Opportunity Zone status was added. NCDOT AADT stays the query-time statewide join. Household income stays ACS B19013_001E. Tract display was not changed.

Tennessee rural Opportunity Zone batch 3 loads the next 20 pass1-order counties that were not already a complete extract: Benton, Carter, Clay, Fentress, Franklin, Hancock, Hawkins, Humphreys, Jackson, Johnson, Lake, Lawrence, Marion, McMinn, Obion, Pickett, Scott, Sullivan, Tipton, and Wayne. Maury, Shelby, and Sumner were already complete and were not replaced. Geometry and owner stay on Tennessee Property Boundaries Public Use, filtered by the card's Comptroller COUNTY_ID. Acreage is geodesic polygon area, 5.0 through 150.0 inclusive. Sale date, sale price, and appraisal are joined on GISLINK from the card's sales-value layer. Lawrence, McMinn, and Marion are labeled 2025. Tipton is labeled 2026. Fentress has no public bulk sale/value layer, so those fields stay empty. The other fifteen use TN_County_Parcel_Map and are labeled 2023. A sale date later than the pull date is left blank. Sullivan zoning is joined on GISLINK. McMinn, Marion, and Tipton zoning polygons are stamped by centroid, with a later city layer replacing the county code only inside that city. The other counties leave zoning empty. The TPAD link is stored and not requested. Owner phone and email are not ingested. No new market shelf was added. No Opportunity Zone designation, school grade, or base flood elevation was added. AADT and tract-income wiring were not changed.

The next twenty Tennessee rural-OZ counties use the same public-GIS loader. Geometry and owner stay on Tennessee Property Boundaries Public Use, filtered by the card's Comptroller COUNTY_ID. Acreage is geodesic polygon area, 5.0 through 150.0 inclusive. Sale date, sale price, and appraisal are joined on GISLINK from the card's sales-value layer. Hamblen uses the MH-GIS assessor CAMA and is labeled 2026. The other nineteen use TN_County_Parcel_Map and are labeled 2023. A sale date later than the pull date is left blank. The TPAD link is stored and not requested. Owner phone and email are not ingested. Bradley and Grainger were already loaded and were not replaced. No new market shelf was added. No Opportunity Zone designation, school grade, or base flood elevation was added. AADT and tract-income wiring were not changed.

Twenty Tennessee counties were loaded from public GIS only. Geometry and owner come from the Office of Information Resources layer Tennessee Property Boundaries Public Use (edited 2026-09-10), except Hickman and Chester, which that layer does not include. Acreage is the geodesic area of the polygon, because deeded acres are often 0. Sale date, sale price, and appraisal are joined from AGOL TN_County_Parcel_Map (edited 2023-11-22) on GISLINK and labeled 2023 in the popup. A GISLINK that does not match is left without sale or value. Overton is not on that service; its sale and value come from UCDD Overton_Parcels and are labeled 2019, that roll's latest tax year. Sevier geometry and owner stay on OIR; sale, value, assessed value, and mailing come from the Sevierville countywide CAMA and are labeled 2025. Hickman is the May 2023 CaptureCAMA snapshot, labeled 2020, and links to the county portal instead of TPAD. Chester is the county CaptureCAMA Parcels_12 layer: the parcel id is the CAMA GISLINK, a blank GISLINK falls back to the map id, rows with neither id are dropped, sale data stays empty because GPDATA__LA is the record's last-updated date, and market and assessed values are labeled 2026. A sale date later than the pull date is left blank. The TPAD GIS link is stored for browsers and is not requested during ingest, tests, or the build. Parcel layers are chosen from `data/tn-parcel-cards` by each layer's `use` label and the card's `parcelSetup` block, never by taking the first parcels layer. Acreage is geodesic polygon area because the OIR layer has no acreage field. Zoning join URLs stay in `data/tn-rural-parcel-sources.json`. Re-pull one county after a card changes with `python3 scripts/tn_oir_parcels.py --county <Name> --refresh`. Zoning is stamped only where that county's research card published a usable layer. Bedford County, Pennsylvania is not a source. Utah Sevier County parcels are not a source. Macon had been a shelf gap because the generic loader queried IMPACT COUNTY_ID 111; the Comptroller county number is 56 and the public layer was live. No Opportunity Zone designation was added. AADT wiring was not changed.

## Coverage

# Market parcel coverage

Acreage band is **5.0–150.0 inclusive**. Lake, Osceola, Seminole, and Sumter Orlando tiles were reseeded from county GIS. Polk market parcels use the property-appraiser extract. Orange still points at the Orlando tiles.

Parcels stay off until neighborhood zoom, an area lock, or Show parcels. The map requests the selected market's viewport tiles only.

| Market | Tier | Parcels | Complete counties | Sample or partial | Gaps |
| --- | --- | ---: | ---: | ---: | ---: |
| Atlanta | primary | 93,811 | 17 | 0 | 18 |
| Tampa | primary | 127,713 | 10 | 0 | 0 |
| Charleston | primary | 86,151 | 14 | 0 | 1 |
| Nashville | primary | 169,243 | 25 | 0 | 3 |
| Charlotte | primary | 129,191 | 16 | 0 | 2 |
| Raleigh-Durham | primary | 215,243 | 30 | 0 | 0 |
| South Florida | shelf | 41,693 | 3 | 1 | 0 |
| SWFL | other | 32,749 | 4 | 0 | 0 |
| Vero Beach | other | 23,480 | 5 | 0 | 0 |
| Melbourne | other | 41,026 | 5 | 0 | 0 |
| Jacksonville | other | 26,878 | 5 | 0 | 0 |
| Big Bend | other | 53,214 | 8 | 2 | 0 |
| Pensacola | other | 66,437 | 7 | 0 | 0 |
| Birmingham | other | 94,992 | 8 | 0 | 3 |
| Mobile | other | 51,658 | 4 | 0 | 2 |
| Huntsville | other | 108,448 | 12 | 0 | 1 |
| Savannah | other | 19,987 | 5 | 0 | 3 |
| Columbia | other | 49,244 | 5 | 1 | 7 |
| Greenville | other | 48,073 | 5 | 0 | 4 |
| Chattanooga | other | 43,972 | 8 | 0 | 5 |
| Knoxville | other | 130,277 | 22 | 0 | 2 |
| Memphis | other | 95,916 | 19 | 0 | 1 |
| Jackson | other | 35,353 | 7 | 0 | 0 |
| Winston-Salem | other | 95,812 | 10 | 0 | 0 |
| Wilmington | other | 100,686 | 16 | 0 | 0 |
| Heartland | shelf | 21,163 | 4 | 1 | 0 |
| North-Central Florida | other | 103,358 | 13 | 0 | 0 |
| Asheville | other | 89,533 | 15 | 0 | 0 |
| Tuscaloosa | other | 27,452 | 4 | 0 | 1 |
| Montgomery | other | 56,134 | 8 | 0 | 1 |
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
| Citrus | Florida | 12017 | complete-gte-5ac | 5,992 | fl-citrus-swfwmd-12017 |
| Hardee | Florida | 12049 | complete-gte-5ac | 5,303 | fl-hardee-infomap-12049 |
| Hernando | Florida | 12053 | complete-gte-5ac | 6,601 | fl-hernando-parcels-12053 |
| Hillsborough | Florida | 12057 | complete-gte-5ac | 13,838 | fl-hillsborough-parcelpublishing-12 |
| Manatee | Florida | 12081 | complete-gte-5ac | 7,239 | fl-doh-ehwaters-12081 |
| Pasco | Florida | 12101 | complete-gte-5ac | 12,372 | fl-pasco-pascomapper-7 |
| Pinellas | Florida | 12103 | complete-gte-5ac | 42,230 | fl-pinellas-publicwebgis-1 |
| Polk | Florida | 12105 | complete-gte-5ac | 20,263 | fl-polk-property-appraiser-134 |
| Sarasota | Florida | 12115 | complete-gte-5ac | 4,303 | fl-doh-ehwaters-12115 |
| Sumter | Florida | 12119 | complete-gte-5ac | 9,572 | fl-sumter-bocc-parcels-12119 |

### Charleston

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Allendale | South Carolina | 45005 | complete-gte-5ac | 1,911 | sc-allendale-parcels-45005 |
| Bamberg | South Carolina | 45009 | complete-gte-5ac | 3,095 | sc-bamberg-parcels-45009 |
| Barnwell | South Carolina | 45011 | complete-gte-5ac | 4,150 | sc-barnwell-parcels-45011 |
| Berkeley | South Carolina | 45015 | complete-gte-5ac | 7,886 | sc-berkeley-addr-muni |
| Charleston | South Carolina | 45019 | complete-gte-5ac | 7,989 | sc-charleston-energov-ent |
| Clarendon | South Carolina | 45027 | complete-gte-5ac | 6,282 | sc-clarendon-parcels-45027 |
| Colleton | South Carolina | 45029 | complete-gte-5ac | 8,615 | sc-colleton-parcels-45029 |
| Darlington | South Carolina | 45031 | complete-gte-5ac | 6,449 | sc-darlington-parcels-45031 |
| Dillon | South Carolina | 45033 | complete-gte-5ac | 3,507 | sc-dillon-parcels-45033 |
| Dorchester | South Carolina | 45035 | complete-gte-5ac | 6,774 | sc-dorchester-parcels-public |
| Florence | South Carolina | 45041 | complete-gte-5ac | 10,091 | sc-florence-parcels-45041 |
| Georgetown | South Carolina | 45043 | complete-gte-5ac | 3,963 | sc-georgetown-parcels-45043 |
| Hampton | South Carolina | 45049 | complete-gte-5ac | 3,402 | sc-hampton-parcels-45049 |
| Horry | South Carolina | 45051 | complete-gte-5ac | 12,037 | sc-horry-parcels-45051 |
| Orangeburg | South Carolina | 45075 | gap | 0 | unavailable |

### Nashville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Bedford | Tennessee | 47003 | complete-gte-5ac | 6,686 | tn-oir-public-use-47003 |
| Cannon | Tennessee | 47015 | complete-gte-5ac | 3,863 | tn-oir-public-use-47015 |
| Cheatham | Tennessee | 47021 | complete-gte-5ac | 5,426 | apsu-cheatgis-47021 |
| Clay | Tennessee | 47027 | complete-gte-5ac | 2,455 | tn-oir-public-use-47027 |
| Coffee | Tennessee | 47031 | complete-gte-5ac | 5,715 | tn-oir-public-use-47031 |
| Davidson | Tennessee | 47037 | complete-gte-5ac | 9,478 | tn-metro-davidson-parcels |
| DeKalb | Tennessee | 47041 | complete-gte-5ac | 3,787 | tn-oir-public-use-47041 |
| Dickson | Tennessee | 47043 | complete-gte-5ac | 8,477 | tn-oir-public-use-47043 |
| Hickman | Tennessee | 47081 | complete-gte-5ac | 5,445 | tn-hickman-capturecama-202305 |
| Humphreys | Tennessee | 47085 | complete-gte-5ac | 4,798 | tn-oir-public-use-47085 |
| Jackson | Tennessee | 47087 | complete-gte-5ac | 3,604 | tn-oir-public-use-47087 |
| Lawrence | Tennessee | 47099 | complete-gte-5ac | 7,697 | tn-oir-public-use-47099 |
| Macon | Tennessee | 47111 | complete-gte-5ac | 5,064 | tn-oir-public-use-47111 |
| Marshall | Tennessee | 47117 | gap | 0 | tn-impact-47117 |
| Maury | Tennessee | 47119 | complete-gte-5ac | 9,033 | tn-columbia-agol-47119 |
| Montgomery | Tennessee | 47125 | complete-gte-5ac | 7,038 | tn-mcgtn-cama-47125 |
| Overton | Tennessee | 47133 | complete-gte-5ac | 5,557 | tn-oir-public-use-47133 |
| Pickett | Tennessee | 47137 | complete-gte-5ac | 1,737 | tn-oir-public-use-47137 |
| Putnam | Tennessee | 47141 | complete-gte-5ac | 6,089 | tn-oir-public-use-47141 |
| Robertson | Tennessee | 47147 | complete-gte-5ac | 8,606 | tn-oir-public-use-47147 |
| Rutherford | Tennessee | 47149 | complete-gte-5ac | 9,677 | tn-rutherford-agol-parcels |
| Smith | Tennessee | 47159 | gap | 0 | tn-impact-47159 |
| Sumner | Tennessee | 47165 | complete-gte-5ac | 15,982 | tn-sumner-911-parcels-cama |
| Trousdale | Tennessee | 47169 | gap | 0 | tn-impact-47169 |
| Warren | Tennessee | 47177 | complete-gte-5ac | 6,578 | tn-oir-public-use-47177 |
| Wayne | Tennessee | 47181 | complete-gte-5ac | 4,925 | tn-oir-public-use-47181 |
| Williamson | Tennessee | 47187 | complete-gte-5ac | 10,760 | tn-williamson-datapull-47187 |
| Wilson | Tennessee | 47189 | complete-gte-5ac | 10,766 | tn-oir-public-use-47189 |

### Charlotte

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Alexander | North Carolina | 37003 | complete-gte-5ac | 5,996 | nc-alexander-parcels-37003 |
| Anson | North Carolina | 37007 | complete-gte-5ac | 5,820 | nc-anson-vector-37007 |
| Cabarrus | North Carolina | 37025 | complete-gte-5ac | 6,983 | nc-cabarrus-tax-parcels-37025 |
| Catawba | North Carolina | 37035 | complete-gte-5ac | 8,502 | nc-onemap-37035 |
| Chester | South Carolina | 45023 | complete-gte-5ac | 5,369 | sc-chester-parcels-45023 |
| Cleveland | North Carolina | 37045 | complete-gte-5ac | 9,310 | nc-onemap-37045 |
| Davidson | North Carolina | 37057 | complete-gte-5ac | 12,063 | nc-davidson-opengov-37057 |
| Gaston | North Carolina | 37071 | complete-gte-5ac | 6,815 | nc-gaston-publicgis-37071 |
| Iredell | North Carolina | 37097 | complete-gte-5ac | 10,768 | nc-iredell-taxsql-37097 |
| Lancaster | South Carolina | 45057 | gap | 0 | unavailable |
| Lincoln | North Carolina | 37109 | complete-gte-5ac | 6,563 | nc-lincoln-operational-37109 |
| Mecklenburg | North Carolina | 37119 | complete-gte-5ac | 8,402 | meck-taxparcel-camadata-37119 |
| Montgomery | North Carolina | 37123 | complete-gte-5ac | 5,957 | nc-montgomery-parcels-37123 |
| Richmond | North Carolina | 37153 | complete-gte-5ac | 5,219 | nc-richmond-parcels-37153 |
| Rowan | North Carolina | 37159 | complete-gte-5ac | 10,375 | nc-rowan-open-data-37159 |
| Stanly | North Carolina | 37167 | complete-gte-5ac | 8,024 | nc-onemap-37167 |
| Union | North Carolina | 37179 | complete-gte-5ac | 13,025 | nc-union-atlas-37179 |
| York | South Carolina | 45091 | gap | 0 | unavailable |

### Raleigh-Durham

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Alamance | North Carolina | 37001 | complete-gte-5ac | 8,846 | nc-onemap-37001 |
| Bertie | North Carolina | 37015 | complete-gte-5ac | 4,411 | nc-bertie-parcels-37015 |
| Caswell | North Carolina | 37033 | complete-gte-5ac | 5,286 | nc-caswell-parcels-37033 |
| Chatham | North Carolina | 37037 | complete-gte-5ac | 13,229 | nc-onemap-37037 |
| Chowan | North Carolina | 37041 | complete-gte-5ac | 2,130 | nc-chowan-parcels-37041 |
| Durham | North Carolina | 37063 | complete-gte-5ac | 4,940 | durham-property-37063 |
| Edgecombe | North Carolina | 37065 | complete-gte-5ac | 4,257 | nc-edgecombe-parcels-37065 |
| Franklin | North Carolina | 37069 | complete-gte-5ac | 7,639 | nc-onemap-37069 |
| Granville | North Carolina | 37077 | complete-gte-5ac | 7,150 | nc-onemap-37077 |
| Greene | North Carolina | 37079 | complete-gte-5ac | 3,557 | nc-greene-parcels-37079 |
| Halifax | North Carolina | 37083 | complete-gte-5ac | 6,433 | nc-halifax-parcels-37083 |
| Harnett | North Carolina | 37085 | complete-gte-5ac | 11,657 | nc-onemap-37085 |
| Hertford | North Carolina | 37091 | complete-gte-5ac | 2,701 | nc-hertford-parcels-37091 |
| Hoke | North Carolina | 37093 | complete-gte-5ac | 3,202 | nc-hoke-parcels-37093 |
| Johnston | North Carolina | 37101 | complete-gte-5ac | 14,113 | nc-onemap-37101 |
| Lee | North Carolina | 37105 | complete-gte-5ac | 4,858 | nc-onemap-37105 |
| Martin | North Carolina | 37117 | complete-gte-5ac | 3,561 | nc-martin-parcels-37117 |
| Moore | North Carolina | 37125 | complete-gte-5ac | 12,638 | nc-moore-parcels-37125 |
| Nash | North Carolina | 37127 | complete-gte-5ac | 8,292 | nc-onemap-37127 |
| Northampton | North Carolina | 37131 | complete-gte-5ac | 4,840 | nc-northampton-parcels-37131 |
| Orange | North Carolina | 37135 | complete-gte-5ac | 9,375 | nc-orange-webparcel-37135 |
| Pasquotank | North Carolina | 37139 | complete-gte-5ac | 2,779 | nc-pasquotank-parcels-37139 |
| Person | North Carolina | 37145 | complete-gte-5ac | 5,956 | nc-onemap-37145 |
| Pitt | North Carolina | 37147 | complete-gte-5ac | 7,918 | nc-pitt-parcels-37147 |
| Sampson | North Carolina | 37163 | complete-gte-5ac | 14,031 | nc-onemap-37163 |
| Vance | North Carolina | 37181 | complete-gte-5ac | 3,181 | nc-onemap-37181 |
| Wake | North Carolina | 37183 | complete-gte-5ac | 12,436 | nc-wake-county-parcels |
| Warren | North Carolina | 37185 | complete-gte-5ac | 5,596 | nc-onemap-37185 |
| Wayne | North Carolina | 37191 | complete-gte-5ac | 15,079 | nc-onemap-37191 |
| Wilson | North Carolina | 37195 | complete-gte-5ac | 5,152 | nc-onemap-37195 |

### South Florida

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Broward | Florida | 12011 | partial | 7,549 | fl-broward-bcpa-jan26-16 |
| Miami-Dade | Florida | 12086 | complete-gte-5ac | 15,563 | fl-miami-dade-landinformation-26 |
| Monroe | Florida | 12087 | complete-gte-5ac | 6,492 | fl-monroe-apo-parcels-0 |
| Palm Beach | Florida | 12099 | complete-gte-5ac | 12,089 | fl-palm-beach-parcel-info-4 |

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
| Okeechobee | Florida | 12093 | complete-gte-5ac | 3,524 | fl-okeechobee-tyler-12093 |
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
| St. Johns | Florida | 12109 | complete-gte-5ac | 5,521 | fl-sjc-hosted-parcel-12109 |

### Big Bend

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Calhoun | Florida | 12013 | complete-gte-5ac | 4,121 | fl-fdor-cadastral-2025-12013 |
| Dixie | Florida | 12029 | complete-gte-5ac | 3,251 | fl-srwmd-parcels-12029 |
| Gadsden | Florida | 12039 | complete-gte-5ac | 6,170 | fl-fdor-cadastral-2025-12039 |
| Jackson | Florida | 12063 | complete-gte-5ac | 11,461 | fl-fdor-cadastral-2025-12063 |
| Jefferson | Florida | 12065 | sample | 5,165 | fl-jefferson-pa-parcels-12065 |
| Leon | Florida | 12073 | complete-gte-5ac | 5,685 | fl-leon-overlay-parcel-12073 |
| Liberty | Florida | 12077 | complete-gte-5ac | 1,586 | fl-fdor-cadastral-2025-12077 |
| Madison | Florida | 12079 | complete-gte-5ac | 7,178 | fl-srwmd-parcels-12079 |
| Taylor | Florida | 12123 | complete-gte-5ac | 3,813 | fl-srwmd-parcels-12123 |
| Wakulla | Florida | 12129 | sample | 4,784 | fl-wakulla-county-parcels-12129 |

### Pensacola

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Baldwin | Alabama | 01003 | complete-gte-5ac | 17,987 | al-baldwin-public-isv |
| Bay | Florida | 12005 | complete-gte-5ac | 4,863 | fl-bay-test-parcels-12005 |
| Escambia | Florida | 12033 | complete-gte-5ac | 9,240 | fl-panhandle-12033 |
| Holmes | Florida | 12059 | complete-gte-5ac | 6,532 | fl-holmes-taxparcels-12059 |
| Okaloosa | Florida | 12091 | complete-gte-5ac | 9,956 | fl-panhandle-12091 |
| Santa Rosa | Florida | 12113 | complete-gte-5ac | 8,928 | fl-panhandle-12113 |
| Walton | Florida | 12131 | complete-gte-5ac | 8,931 | fl-walton-energov-12131 |

### Birmingham

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Bibb | Alabama | 01007 | gap | 0 | unavailable |
| Blount | Alabama | 01009 | complete-gte-5ac | 11,515 | al-blount-parcels-01009 |
| Calhoun | Alabama | 01015 | complete-gte-5ac | 9,768 | al-calhoun-parcels-01015 |
| Chilton | Alabama | 01021 | gap | 0 | unavailable |
| Cullman | Alabama | 01043 | complete-gte-5ac | 14,885 | al-cullman-parcels-01043 |
| Etowah | Alabama | 01055 | complete-gte-5ac | 11,021 | al-etowah-parcels-01055 |
| Jefferson | Alabama | 01073 | complete-gte-5ac | 15,641 | al-jefferson-parcels |
| Shelby | Alabama | 01117 | complete-gte-5ac | 11,994 | al-shelby-cadastral-2025 |
| St. Clair | Alabama | 01115 | complete-gte-5ac | 10,466 | al-stclair-owner-parcels |
| Talladega | Alabama | 01121 | complete-gte-5ac | 9,702 | al-talladega-parcels-01121 |
| Walker | Alabama | 01127 | gap | 0 | unavailable |

### Mobile

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Baldwin | Alabama | 01003 | complete-gte-5ac | 17,987 | al-baldwin-public-isv |
| Escambia | Alabama | 01053 | gap | 0 | unavailable |
| George | Mississippi | 28039 | complete-gte-5ac | 7,189 | ms-mdeq-2023-28039 |
| Mobile | Alabama | 01097 | complete-gte-5ac | 17,270 | al-mobile-agol-capturecama |
| Monroe | Alabama | 01099 | complete-gte-5ac | 9,212 | al-monroe-parcels-01099 |
| Washington | Alabama | 01129 | gap | 0 | unavailable |

### Huntsville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Cherokee | Alabama | 01019 | complete-gte-5ac | 8,068 | al-cherokee-parcels-01019 |
| Cullman | Alabama | 01043 | complete-gte-5ac | 14,885 | al-cullman-parcels-01043 |
| DeKalb | Alabama | 01049 | complete-gte-5ac | 16,704 | al-dekalb-parcels-01049 |
| Franklin | Tennessee | 47051 | complete-gte-5ac | 5,483 | tn-oir-public-use-47051 |
| Franklin | Alabama | 01059 | complete-gte-5ac | 7,927 | al-franklin-parcels-01059 |
| Jackson | Alabama | 01071 | complete-gte-5ac | 13,862 | al-jackson-parcels-01071 |
| Lauderdale | Alabama | 01077 | complete-gte-5ac | 3,840 | al-lauderdale-parcels-01077 |
| Limestone | Alabama | 01083 | complete-gte-5ac | 5,445 | al-limestone-remap-1 |
| Lincoln | Tennessee | 47103 | gap | 0 | tn-impact-47103 |
| Madison | Alabama | 01089 | complete-gte-5ac | 12,312 | al-madison-public-isv-185 |
| Marshall | Alabama | 01095 | complete-gte-5ac | 11,014 | al-marshall-public-37 |
| Morgan | Alabama | 01103 | complete-gte-5ac | 827 | al-morgan-vam-10 |
| Winston | Alabama | 01133 | complete-gte-5ac | 8,081 | al-winston-parcels-01133 |

### Savannah

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Beaufort | South Carolina | 45013 | complete-gte-5ac | 4,756 | sc-beaufort-energov-parcels |
| Bryan | Georgia | 13029 | complete-gte-5ac | 2,138 | ga-bryan-property-details |
| Bulloch | Georgia | 13031 | gap | 0 | unavailable |
| Chatham | Georgia | 13051 | complete-gte-5ac | 3,283 | sagis-chatham-ga-parcel-digest |
| Effingham | Georgia | 13103 | complete-gte-5ac | 6,128 | ga-effingham-parcels-2024 |
| Jasper | South Carolina | 45053 | complete-gte-5ac | 3,682 | sc-jasper-parcels-45053 |
| Liberty | Georgia | 13179 | gap | 0 | unavailable |
| Screven | Georgia | 13251 | gap | 0 | unavailable |

### Columbia

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Aiken | South Carolina | 45003 | complete-gte-5ac | 15,502 | sc-aiken-parcels-45003 |
| Calhoun | South Carolina | 45017 | gap | 0 | unavailable |
| Chesterfield | South Carolina | 45025 | complete-gte-5ac | 8,287 | sc-chesterfield-parcels-45025 |
| Edgefield | South Carolina | 45037 | complete-gte-5ac | 5,811 | sc-edgefield-parcels-45037 |
| Fairfield | South Carolina | 45039 | complete-gte-5ac | 5,031 | sc-fairfield-parcels-45039 |
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
| Abbeville | South Carolina | 45001 | complete-gte-5ac | 5,266 | sc-abbeville-parcels-45001 |
| Anderson | South Carolina | 45007 | gap | 0 | unavailable |
| Cherokee | South Carolina | 45021 | complete-gte-5ac | 6,302 | sc-cherokee-parcels-45021 |
| Greenville | South Carolina | 45045 | complete-gte-5ac | 14,959 | sc-greenville-gcgia-tax-parcel |
| Greenwood | South Carolina | 45047 | complete-gte-5ac | 5,341 | sc-greenwood-parcels-45047 |
| Laurens | South Carolina | 45059 | gap | 0 | unavailable |
| Oconee | South Carolina | 45073 | gap | 0 | unavailable |
| Pickens | South Carolina | 45077 | gap | 0 | unavailable |
| Spartanburg | South Carolina | 45083 | complete-gte-5ac | 16,205 | sc-spartanburg-cama-parcels |

### Chattanooga

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Bledsoe | Tennessee | 47007 | complete-gte-5ac | 4,450 | tn-oir-public-use-47007 |
| Bradley | Tennessee | 47011 | complete-gte-5ac | 6,336 | tn-cleveland-parcels-impact-47011 |
| Catoosa | Georgia | 13047 | gap | 0 | unavailable |
| Dade | Georgia | 13083 | gap | 0 | unavailable |
| Grundy | Tennessee | 47061 | complete-gte-5ac | 3,732 | tn-oir-public-use-47061 |
| Hamilton | Tennessee | 47065 | complete-gte-5ac | 9,162 | tn-hamilton-live-parcels |
| Marion | Tennessee | 47115 | complete-gte-5ac | 4,903 | tn-oir-public-use-47115 |
| McMinn | Tennessee | 47107 | complete-gte-5ac | 8,070 | tn-oir-public-use-47107 |
| Meigs | Tennessee | 47121 | gap | 0 | tn-impact-47121 |
| Rhea | Tennessee | 47143 | complete-gte-5ac | 3,977 | tn-oir-public-use-47143 |
| Sequatchie | Tennessee | 47153 | complete-gte-5ac | 3,342 | tn-oir-public-use-47153 |
| Walker | Georgia | 13295 | gap | 0 | unavailable |
| Whitfield | Georgia | 13313 | gap | 0 | unavailable |

### Knoxville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Anderson | Tennessee | 47001 | complete-gte-5ac | 4,310 | tn-oir-public-use-47001 |
| Blount | Tennessee | 47009 | complete-gte-5ac | 8,183 | tn-blount-agol-47009 |
| Campbell | Tennessee | 47013 | complete-gte-5ac | 3,613 | tn-oir-public-use-47013 |
| Carter | Tennessee | 47019 | complete-gte-5ac | 4,589 | tn-oir-public-use-47019 |
| Claiborne | Tennessee | 47025 | complete-gte-5ac | 5,456 | tn-oir-public-use-47025 |
| Cocke | Tennessee | 47029 | complete-gte-5ac | 6,377 | tn-oir-public-use-47029 |
| Cumberland | Tennessee | 47035 | complete-gte-5ac | 8,540 | tn-oir-public-use-47035 |
| Fentress | Tennessee | 47049 | complete-gte-5ac | 5,166 | tn-oir-public-use-47049 |
| Grainger | Tennessee | 47057 | complete-gte-5ac | 6,406 | tn-impact-47057 |
| Greene | Tennessee | 47059 | complete-gte-5ac | 10,925 | tn-oir-public-use-47059 |
| Hamblen | Tennessee | 47063 | complete-gte-5ac | 3,024 | tn-oir-public-use-47063 |
| Hancock | Tennessee | 47067 | complete-gte-5ac | 3,058 | tn-oir-public-use-47067 |
| Hawkins | Tennessee | 47073 | complete-gte-5ac | 8,287 | tn-oir-public-use-47073 |
| Jefferson | Tennessee | 47089 | complete-gte-5ac | 6,586 | tn-impact-47089 |
| Johnson | Tennessee | 47091 | complete-gte-5ac | 3,886 | tn-oir-public-use-47091 |
| Knox | Tennessee | 47093 | complete-gte-5ac | 4,569 | kgis-parcel-search |
| Loudon | Tennessee | 47105 | gap | 0 | tn-impact-47105 |
| Monroe | Tennessee | 47123 | complete-gte-5ac | 7,395 | tn-oir-public-use-47123 |
| Morgan | Tennessee | 47129 | complete-gte-5ac | 5,113 | tn-oir-public-use-47129 |
| Roane | Tennessee | 47145 | complete-gte-5ac | 5,731 | tn-oir-public-use-47145 |
| Scott | Tennessee | 47151 | complete-gte-5ac | 4,340 | tn-oir-public-use-47151 |
| Sevier | Tennessee | 47155 | complete-gte-5ac | 7,587 | tn-oir-public-use-47155 |
| Sullivan | Tennessee | 47163 | complete-gte-5ac | 7,136 | tn-oir-public-use-47163 |
| Union | Tennessee | 47173 | gap | 0 | tn-impact-47173 |

### Memphis

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Benton | Mississippi | 28009 | complete-gte-5ac | 3,557 | ms-mdeq-2023-28009 |
| Crittenden | Arkansas | 05035 | complete-gte-5ac | 3,666 | ar-cadastre-05035 |
| DeSoto | Mississippi | 28033 | complete-gte-5ac | 6,219 | ms-mdeq-2023-28033 |
| Dyer | Tennessee | 47045 | complete-gte-5ac | 3,871 | tn-oir-public-use-47045 |
| Fayette | Tennessee | 47047 | gap | 0 | tn-impact-47047 |
| Gibson | Tennessee | 47053 | complete-gte-5ac | 7,282 | tn-oir-public-use-47053 |
| Hardeman | Tennessee | 47069 | complete-gte-5ac | 4,618 | tn-oir-public-use-47069 |
| Haywood | Tennessee | 47075 | complete-gte-5ac | 3,168 | tn-oir-public-use-47075 |
| Henderson | Tennessee | 47077 | complete-gte-5ac | 5,413 | tn-oir-public-use-47077 |
| Henry | Tennessee | 47079 | complete-gte-5ac | 6,064 | tn-oir-public-use-47079 |
| Lake | Tennessee | 47095 | complete-gte-5ac | 721 | tn-oir-public-use-47095 |
| Lauderdale | Tennessee | 47097 | complete-gte-5ac | 3,256 | tn-oir-public-use-47097 |
| Marshall | Mississippi | 28093 | complete-gte-5ac | 7,984 | ms-mdeq-2023-28093 |
| McNairy | Tennessee | 47109 | complete-gte-5ac | 6,291 | tn-oir-public-use-47109 |
| Mississippi | Arkansas | 05093 | complete-gte-5ac | 6,585 | ar-cadastre-05093 |
| Obion | Tennessee | 47131 | complete-gte-5ac | 4,424 | tn-oir-public-use-47131 |
| Shelby | Tennessee | 47157 | complete-gte-5ac | 9,667 | tn-shelby-current-parcels |
| Tate | Mississippi | 28137 | complete-gte-5ac | 5,758 | ms-mdeq-2023-28137 |
| Tipton | Tennessee | 47167 | complete-gte-5ac | 5,530 | tn-oir-public-use-47167 |
| Tunica | Mississippi | 28143 | complete-gte-5ac | 1,842 | ms-mdeq-2023-28143 |

### Jackson

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Benton | Tennessee | 47005 | complete-gte-5ac | 4,181 | tn-oir-public-use-47005 |
| Carroll | Tennessee | 47017 | complete-gte-5ac | 6,160 | tn-oir-public-use-47017 |
| Chester | Tennessee | 47023 | complete-gte-5ac | 3,333 | tn-chester-capturecama-parcels12 |
| Decatur | Tennessee | 47039 | complete-gte-5ac | 3,472 | tn-oir-public-use-47039 |
| Hardin | Tennessee | 47071 | complete-gte-5ac | 5,438 | tn-oir-public-use-47071 |
| Madison | Tennessee | 47113 | complete-gte-5ac | 6,384 | tn-impact-47113 |
| Weakley | Tennessee | 47183 | complete-gte-5ac | 6,385 | tn-oir-public-use-47183 |

### Winston-Salem

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Alleghany | North Carolina | 37005 | complete-gte-5ac | 3,613 | nc-alleghany-parcels-37005 |
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
| Beaufort | North Carolina | 37013 | complete-gte-5ac | 8,050 | nc-beaufort-parcels-37013 |
| Bladen | North Carolina | 37017 | complete-gte-5ac | 8,300 | nc-bladen-parcels-37017 |
| Brunswick | North Carolina | 37019 | complete-gte-5ac | 7,533 | bcgis-seamless-37019 |
| Carteret | North Carolina | 37031 | complete-gte-5ac | 3,283 | nc-carteret-parcels-37031 |
| Columbus | North Carolina | 37047 | complete-gte-5ac | 12,025 | nc-onemap-37047 |
| Craven | North Carolina | 37049 | complete-gte-5ac | 5,945 | nc-craven-parcels-37049 |
| Dare | North Carolina | 37055 | complete-gte-5ac | 2,066 | nc-dare-parcels-37055 |
| Duplin | North Carolina | 37061 | complete-gte-5ac | 11,397 | nc-onemap-37061 |
| Hyde | North Carolina | 37095 | complete-gte-5ac | 2,394 | nc-hyde-parcels-37095 |
| Jones | North Carolina | 37103 | complete-gte-5ac | 2,349 | nc-jones-parcels-37103 |
| Lenoir | North Carolina | 37107 | complete-gte-5ac | 5,242 | nc-lenoir-parcels-37107 |
| New Hanover | North Carolina | 37129 | complete-gte-5ac | 2,263 | nc-new-hanover-parcels-37129 |
| Onslow | North Carolina | 37133 | complete-gte-5ac | 6,747 | nc-onemap-37133 |
| Pamlico | North Carolina | 37137 | complete-gte-5ac | 3,154 | nc-pamlico-parcels-37137 |
| Pender | North Carolina | 37141 | complete-gte-5ac | 7,355 | nc-pender-energov-37141 |
| Robeson | North Carolina | 37155 | complete-gte-5ac | 12,583 | nc-robeson-parcels-37155 |

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
| Bradford | Florida | 12007 | complete-gte-5ac | 3,292 | fl-srwmd-parcels-12007 |
| Citrus | Florida | 12017 | complete-gte-5ac | 5,992 | fl-citrus-swfwmd-12017 |
| Columbia | Florida | 12023 | complete-gte-5ac | 10,748 | fl-columbia-parcels-12023 |
| Gilchrist | Florida | 12041 | complete-gte-5ac | 6,395 | fl-doh-ehwaters-12041 |
| Hamilton | Florida | 12047 | complete-gte-5ac | 4,149 | fl-srwmd-parcels-12047 |
| Hernando | Florida | 12053 | complete-gte-5ac | 6,601 | fl-hernando-parcels-12053 |
| Lafayette | Florida | 12067 | complete-gte-5ac | 3,165 | fl-srwmd-parcels-12067 |
| Levy | Florida | 12075 | complete-gte-5ac | 9,645 | fl-srwmd-parcels-12075 |
| Marion | Florida | 12083 | complete-gte-5ac | 17,730 | fl-marion-parcels-12083 |
| Putnam | Florida | 12107 | complete-gte-5ac | 5,899 | fl-putnam-parcels-pa-12107 |
| Suwannee | Florida | 12121 | complete-gte-5ac | 11,856 | fl-srwmd-parcels-12121 |
| Union | Florida | 12125 | complete-gte-5ac | 2,347 | fl-srwmd-parcels-12125 |

### Asheville

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Ashe | North Carolina | 37009 | complete-gte-5ac | 8,966 | nc-ashe-parcels-37009 |
| Avery | North Carolina | 37011 | complete-gte-5ac | 3,925 | nc-avery-parcels-37011 |
| Buncombe | North Carolina | 37021 | complete-gte-5ac | 10,523 | nc-buncombe-opendata-37021 |
| Burke | North Carolina | 37023 | complete-gte-5ac | 7,930 | nc-burke-parcels-37023 |
| Caldwell | North Carolina | 37027 | complete-gte-5ac | 8,109 | nc-caldwell-parcels-37027 |
| Cherokee | North Carolina | 37039 | complete-gte-5ac | 6,293 | nc-cherokee-parcels-37039 |
| Graham | North Carolina | 37075 | complete-gte-5ac | 1,920 | nc-graham-parcels-37075 |
| Haywood | North Carolina | 37087 | complete-gte-5ac | 5,393 | nc-haywood-parcels-37087 |
| Henderson | North Carolina | 37089 | complete-gte-5ac | 6,270 | nc-henderson-parcels-37089 |
| Jackson | North Carolina | 37099 | complete-gte-5ac | 6,732 | nc-jackson-parcels-37099 |
| Macon | North Carolina | 37113 | complete-gte-5ac | 6,321 | nc-macon-parcels-37113 |
| Madison | North Carolina | 37115 | complete-gte-5ac | 6,897 | nc-madison-parcels-37115 |
| McDowell | North Carolina | 37111 | complete-gte-5ac | 1,736 | nc-mcdowell-parcels-37111 |
| Mitchell | North Carolina | 37121 | complete-gte-5ac | 3,835 | nc-mitchell-parcels-37121 |
| Polk | North Carolina | 37149 | complete-gte-5ac | 4,683 | nc-polk-parcels-37149 |

### Tuscaloosa

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Greene | Alabama | 01063 | complete-gte-5ac | 4,327 | al-greene-parcels-01063 |
| Hale | Alabama | 01065 | complete-gte-5ac | 6,068 | al-hale-parcels-01065 |
| Pickens | Alabama | 01107 | gap | 0 | unavailable |
| Sumter | Alabama | 01119 | complete-gte-5ac | 5,461 | al-sumter-parcels-01119 |
| Tuscaloosa | Alabama | 01125 | complete-gte-5ac | 11,596 | al-tuscaloosa-parcels |

### Montgomery

| County | State | FIPS | Coverage | Parcels | Source |
| --- | --- | --- | --- | ---: | --- |
| Autauga | Alabama | 01001 | complete-gte-5ac | 7,047 | al-autauga-parcels |
| Barbour | Alabama | 01005 | complete-gte-5ac | 7,226 | al-barbour-parcels-01005 |
| Bullock | Alabama | 01011 | complete-gte-5ac | 3,579 | al-bullock-parcels-01011 |
| Dallas | Alabama | 01047 | complete-gte-5ac | 6,351 | al-dallas-parcels-01047 |
| Elmore | Alabama | 01051 | complete-gte-5ac | 9,758 | al-elmore-parcels |
| Lowndes | Alabama | 01085 | gap | 0 | unavailable |
| Macon | Alabama | 01087 | complete-gte-5ac | 5,757 | al-macon-parcels-01087 |
| Montgomery | Alabama | 01101 | complete-gte-5ac | 9,954 | al-montgomery-parcels |
| Wilcox | Alabama | 01131 | complete-gte-5ac | 6,462 | al-wilcox-parcels-01131 |

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

