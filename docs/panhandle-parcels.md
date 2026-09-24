# Panhandle shelf parcels

Pensacola loads Bay, Okaloosa, Walton, Escambia, and Santa Rosa from public county and city GIS. These five counties are not the Florida DOH extract. Acreage is **5.0–150.0 inclusive**. The same 0.25° tiles as the other markets are written under `data/fixtures/market-parcels/counties/{fips}/tiles`.

Bay is on this shelf because the source card is the Pensacola / Destin / Panama City coast, not because Bay is inside the Pensacola MSA tract pack. Baldwin County, Alabama stays a gap. No phone numbers or email addresses are stored.

## Refresh

```bash
python3 scripts/seed_panhandle_parcels.py
python3 scripts/seed_panhandle_parcels.py --county Bay
npm run seed:parcels:panhandle
```

Wire order is Bay (12005), Okaloosa (12091), Walton (12131), Escambia (12033), Santa Rosa (12113). A finished `fl-panhandle-*` county is rebuilt when this script runs. `scripts/seed_market_parcels.py` uses the same path and will not send these FIPS back to DOH.

The field map and the rejected endpoints live in `data/panhandle-parcel-sources.json`. Counts and join totals live on each `county.json`.

## City zoning

City layers replace county districts only where the city layer hits (centroid in the city polygon, or a parcel-id join when the card says so).

| Place | Zoning | FLU |
| --- | --- | --- |
| Panama City Beach | City Land Use and Zoning FeatureServer 47, else county `SUB_ZONING=6` | FeatureServer 49, else county `SUB_FLU=6` |
| Callaway, Lynn Haven, Mexico Beach, Panama City | Bay LandUsePlanning zoning with `SUB_ZONING` 2, 3, 4, 5 | Same service, FLU layer, `SUB_FLU` |
| Destin | `Zoning_JulyB_WFL1` (geo-verified Destin) | `LandUse_DND25_WFL1` `LU_CODE` |
| Fort Walton Beach | `gis.fwb.org` Maps/Zoning | Maps/FLU |
| DeFuniak Springs | WeeklyUpdatesDFS parcel id `PARCELNO` | WeeklyUpdatesDFS FLU |
| Freeport | WeeklyUpdatesFreeport numeric `Zoning` | WeeklyUpdatesFreeport `Land_Use` |
| Paxton | Gap | WeeklyUpdatesPaxton `FLU_CLASS` |
| Milton | City of Milton `zone_code` | Gap — county FLUM |
| Gulf Breeze | `par_num` = county `ParNum` | `flum` on the same layer |
| Jay | Town of Jay `zone` | Gap — county FLUM |
| Pensacola | Gap on the city server. Accela county zoning until it recovers | Gap on the city server. Accela FLU 2030 |
| Century | No city layer. Accela | Accela |

County unincorporated layers for Okaloosa (zoning 515 and FLU 44) are not copied onto Crestview, Niceville, Valparaiso, Mary Esther, Laurel Hill, Cinco Bayou, or Shalimar. Those cities have no verified public FeatureServer on this pass.

## Rejected

- `https://services5.arcgis.com/GcvM6vDlR2gM4x31/arcgis/rest/services/Zoning/FeatureServer` — FGDL statewide Albers parcel/tax layer titled Zoning. It is not Destin. The seeder refuses that host.
- Monroe County layers titled “Walton County Tax Parcels” inside unrelated web maps. Not a Walton source.

## Gaps

- **Sale price** is on Okaloosa (`PATPCL_SALE1`, date `PATPCL_SALEDT1` as YYYYMMDD, qualifier `Q`/`U`) and Bay (`sale1pradj`, `sale1date`, `sale1qu_vi`). Escambia and Santa Rosa publish no sale price or date. Walton publishes `SALE_DATE_1` only. Escambia `SOHYEAR` is not a sale date and is not stored.
- **Situs** is on Escambia (`SITEADDR`) and Santa Rosa Basemap (`Address`, or street number + name). Bay `dsiteaddr` is often legal text on rural parcels; it is still the published situs field. Okaloosa PARCELS/17 and Walton EnerGov are mailing-only.
- **Pensacola city GIS** `https://gis.cityofpensacola.com/arcgis/rest/services/Planning/Zoning/MapServer` returned **HTTP 523** on 2026-09-23. Parcels with `CITYCD` `B` or `Z` keep Escambia Accela zoning (`AccelaMain/20`) and FLU (`AccelaMain/22`) until that service returns JSON and the layer id is checked again. There is no separate Pensacola FLU service on this pass.
- **Freeport zoning** is a small integer (card range 0–16) and `Description` was blank. The number is stored. It is not a named district and should not drive a product filter until the city LDC legend is confirmed. Freeport `Land_Use` was also numeric with a blank description; the code is stored and no legend was invented.
- **Paxton zoning** is a gap. FLU is stored. `SubType` is numeric and is not turned into a name.
- **Parker and Springfield** have no dedicated city REST. Bay’s `SUB_ZONING` covers Bay County, Callaway, Lynn Haven, Mexico Beach, Panama City, and Panama City Beach only.
- **Gulf Breeze** public zoning is parcel-keyed and small. Unmatched parcels are not labeled Gulf Breeze, because this pass has no separate city-limits layer for that city.
- **Santa Rosa `dorCode`** is `PropertyUse` text, not a numeric FDOR code.
- **Appraiser links:** Bay uses the layer `plink` (qPublic AppID 834). Escambia uses `LINK`. Okaloosa, Walton, and Santa Rosa link to the property-appraiser search portal only; those layers do not publish a verified per-parcel URL.
- **Not in this pass:** Leon, Gulf, Franklin, Jackson, Holmes, Washington, Calhoun, Gadsden, Jefferson, Wakulla, Liberty. FDOR statewide mirrors are not used for this shelf.

## Landed on this pass

Unique parcel ids inside 5.0–150.0 acres. Repeated basemap rows are one parcel.

| County | FIPS | Parcels | Zoning | FLU | Sale price | Situs | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Bay | 12005 | 4,861 | 4,768 | 4,777 | 4,083 | 4,861 | 5,667 rows; split parcel ids merged. PCB 172, Panama City 252, Lynn Haven 91, Callaway 69, Mexico Beach 18, unincorporated Bay 4,166 |
| Okaloosa | 12091 | 9,956 | 9,449 | 9,470 | 9,562 | 0 | Destin 2,035, Fort Walton Beach 227, unincorporated 7,208. 486 have no city or unincorporated district |
| Walton | 12131 | 8,930 | 8,801 | 8,867 | 0 | 0 | Sale date on 8,492. Freeport 304 (numeric codes), DeFuniak Springs 199, Paxton 79 (FLU only) |
| Escambia | 12033 | 9,240 | 8,487 | 8,487 | 0 | 8,879 | Pensacola 329 uses Accela because city GIS returned HTTP 523. Century 67 uses Accela |
| Santa Rosa | 12113 | 8,928 | 8,901 | 8,900 | 0 | 6,356 | 16,194 basemap rows collapsed to unique ParNum. Milton 71, Gulf Breeze 345, Jay 37 |

Baldwin County, Alabama is still a gap. The rejected FGDL and Monroe “Walton” layers were not queried.

## What the record contains

Owner, mailing address, acreage, and DOR or use code where the card names the field. Tax market value is Bay `vasjust`, Okaloosa `PATPCL_JUSTVAL`, Walton `JUST_VALUE`, Escambia `CURRMKT`, Santa Rosa `TotalValue`. Escambia assessed value is land + building + extra features. Walton assessed value is `APPRAISED_VALUE`. Okaloosa also stores assessed and taxable values.
