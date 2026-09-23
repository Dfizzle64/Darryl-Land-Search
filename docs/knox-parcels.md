# Knox County parcels, zoning, and future land use

Knox County (FIPS 47093) is in the Knoxville market. It includes the **City of Knoxville**, the **Town of Farragut**, and **unincorporated Knox County**. Knox is **not** a Tennessee Comptroller IMPACT county. This pull does not call `maps.cot.tn.gov`.

Checked 2026-09-23T22:53:16Z.

## Parcels

Countywide parcels are the public KGIS Portal proxy `Parcel_Search_Layer` MapServer layer 0. The extract keeps `CALCULATED_AREA` from 5.0 through 150.0 inclusive (4,569 polygons kept, 4,569 returned by that filter). Owner, situs, mailing, sale, appraised land/building/total, and assessed total are on the parcel. `RECORDED_AREA` is stored and is not used to add rows whose calculated acres are null.

Direct `www.kgis.org/arcgis` GlobalSearch query returned **HTTP 401**. Property layer 2 returned **HTTP 401**. Those hosts are not the extract. Comptroller IMPACT is not used.

Tiles: `data/fixtures/market-parcels/counties/47093/tiles`. Source id `kgis-parcel-search`.

Zoning and future land use are joined at the centroid after resolving Town of Farragut, then City of Knoxville, then unincorporated Knox County. Joined zoning: 4,564. Joined unincorporated place types: 3,498.

Appraiser record, when a parcel id exists:

`https://propertyinfo.knoxcountytn.gov/Datalets/Datalet.aspx?ParcelID={PARCELID}&UseSearch=yes`

Search fallback: `https://propertyinfo.knoxcountytn.gov/search/CommonSearch.aspx?mode=parid`

## Municipalities

Resolve jurisdiction **before** the zoning or FLU join. Farragut is tested first, then the Knoxville city limits. Everything else is unincorporated. Farragut is not a `ZONE_TYPE` on the city/county zoning layer.

| Municipality | Zoning | Future land use |
| --- | --- | --- |
| City of Knoxville | `KnoxvilleKnoxCountyZoning` where `ZONE_TYPE` is `City of Knoxville`. Code is `ZONE1` plus non-empty `ZONE2`. | Honest gap. KGIS city future land use returned **HTTP 200 with ArcGIS error 499 Token Required**. The One Year Plan returned **HTTP 401**. |
| Town of Farragut | `Farragut_Zoning` field `ZONE` (201 polygons; 124 have `ACRES` from 5 through 150). | Honest gap. No public Farragut future-land-use FeatureServer. |
| Unincorporated Knox County | Same zoning service where `ZONE_TYPE` is `Knox County`. | Advance Knox `PLACETYPE` (1195 polygons). Not applied inside the city or Farragut. |

## Overlays on disk

| File | Features | Source |
| --- | ---: | --- |
| `data/fixtures/knox/zoning.geojson` | 13462 | https://services1.arcgis.com/QWaOgwdmpqI9HUzf/arcgis/rest/services/KnoxvilleKnoxCountyZoning/FeatureServer/2/query |
| `data/fixtures/knox/county-flu.geojson` | 1195 | https://services1.arcgis.com/QWaOgwdmpqI9HUzf/arcgis/rest/services/Knox_County_Future_Land_Use/FeatureServer/326/query |
| `data/fixtures/knox/farragut-zoning.geojson` | 201 | https://services6.arcgis.com/Ff4u1o0TAdiPJay7/arcgis/rest/services/Farragut_Zoning/FeatureServer/1/query |
| `data/fixtures/knox/municipalities.geojson` | 2 | Knoxville city limits and Farragut boundary |

Zoning `ZONE_TYPE` values: City of Knoxville, Knox County. City polygons on the service: 9727. County polygons on the service: 3769. Place types: BP, CC, CI, CMU, MHI, POS, RA, RC, RCC, RL, ROW, SMR, SR, TCMU, TN.

Service counts include polygons that ring simplification could not keep. A centroid that lands on a right-of-way polygon joins that polygon.

`joinKnoxDesignation` in `src/lib/knox.ts` is the join. It is centroid-in-polygon, keeps the smallest containing polygon, and leaves city and Farragut FLU null.

Refresh:

```bash
npm run seed:knox
```
