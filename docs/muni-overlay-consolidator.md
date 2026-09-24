# Municipal zoning, future land use, and screening overlays

This pass stamps city zoning, future land use, and a small set of school, flood, and utility joins onto parcels that are already on the shelf. It does not add a new county parcel extract. Opportunity Zone designation is not written from an eligible tract, and no school letter grade or base flood elevation is invented.

Refresh commands:

```bash
npm run seed:volusia-flagler-municipal
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

## Not in this pass

- Pinellas and Pasco municipal zoning are inside the Tampa shed parcel re-extract (`cursor/tampa-shed-parcels-7119`, also folded into the Southeast parcel batch). That work replaces county parcel shelves, so it stays with that batch. This checkout does not copy those tiles.
- Brevard city future land use for Melbourne, West Melbourne, Rockledge, Satellite Beach, and Cocoa is not on a finished overlay branch. The Treasure Coast parcel pull records those cities as having no separate public zoning service in that extract, and that pull is a new county shelf.
- New county parcel extracts for any other market.
