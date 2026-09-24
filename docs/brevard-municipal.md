# Brevard city zoning and future land use

City layers are joined onto parcels already on the shelf for FIPS 12009. The parcel roll is not re-downloaded. A parcel gets a code when its id matches `TaxAcct`, `PID`, `RENUM`, or `Name`, or when its centroid falls in that city's polygon. The smaller polygon wins when two city layers overlap. County zoning and county future land use are not copied into these cities.

Checked 2026-09-24. The 5–150 acre market extract joined zoning on 979 parcels and future land use on 973. Counts are also in `data/fixtures/brevard-municipal-join.json`.

The shelf is the Florida DOH extract, not the Accela cadastre. TaxAcct, PID, and Name still match most West Melbourne, Rockledge, Satellite Beach, Cocoa, and Cocoa Beach rows. Centroids fill the rest. Melbourne has no parcel id on the zoning layer, so it is spatial only. Indian Harbour Beach `RENUM` did not match this extract, so those 12 parcels are spatial. The Orlando shed sample (120 parcels, mostly Titusville) joined none, because Titusville is not applied in this pass.

## Wired this pass

| City | Join | Zoning | Future land use |
| --- | --- | --- | --- |
| Melbourne | centroid | `maps.mlbfl.org` CommunityDevelopmentViewer_AGOL MapServer 109 `ZONING` | MapServer 108 `FLUM`, `Status='Active / Current'` |
| West Melbourne | `taxacct` / `name`, then centroid | Hosted `Zoning_View` `zoningnew` | Hosted `Future_Land_Use_View_2` `flunew` |
| Rockledge | `TaxAcct` / `Name`, then centroid | Planning_Building_Public FeatureServer 0 `Zoning` | FeatureServer 1 `FLU` |
| Satellite Beach | `PID`, then centroid | City_of_Satellite_Beach_Map_v1_0 FeatureServer 16 `Zoning` | FeatureServer 15 `FLU` |
| Cocoa | `TaxAcct`, then centroid | Prior layer: Public_View_Cocoa_Zoning FeatureServer 1 `Zoning` | **New:** `FLU_Public_View` FeatureServer **6** `FLUCity` |

Melbourne is the Florida city on `maps.mlbfl.org`. `gis.melbourneflorida.org` is the dead prior host. Melbourne, Australia is refused: a layer whose sample centroid is outside Brevard County is not joined.

Joined parcels on the market extract:

| City | Zoning | FLU | How |
| --- | ---: | ---: | --- |
| Melbourne | 409 | 409 | centroid |
| West Melbourne | 149 | 149 | 117 attribute, 32 centroid |
| Rockledge | 163 | 160 | 153 attribute, 10 centroid |
| Satellite Beach | 16 | 16 | PID |
| Cocoa | 206 | 215 | 195 attribute, 23 centroid. FLU is layer 6 |
| Indian Harbour Beach | 12 | 0 | centroid. FLU left blank |
| Cocoa Beach | 24 | 24 | 21 attribute, 3 centroid. Unofficial 2021 |

## Partials

| City | What is joined | Caveat |
| --- | --- | --- |
| Indian Harbour Beach | Zoning only, IHB FeatureServer 1 `Zoning` | Future land use stays null. Land-cover vintages are not a FLUM. The FLU string on the zoning layer is not used. |
| Cocoa Beach | Zoning and FLU from `CBParcelsMaster2021` FeatureServer 0 | Unofficial. Vintage 2021. `municipal.unofficial` and `municipal.vintage` are set on the parcel. |

## Not applied here

Palm Bay and Titusville already have prior cards (BR-C1 and BR-C2). This pass does not re-wire them.

These cities have no public city zoning or FLU service in this catalog: Cape Canaveral, Indialantic, Melbourne Beach, Grant-Valkaria, Palm Shores, Melbourne Village, Malabar.

Not used as city substitutes:

- Brevard `Zoning_WKID2881` and `FLU_WKID2881`
- Accela zoning MapServer 7 and FLU MapServer 8
- West Melbourne hosted `County_FLU_Areas`
- West Melbourne school-zone layers (grades are not invented)
- Base flood elevations are not invented

Joined codes are the published GIS values. They are not added to the multifamily knowledge base and they do not create Opportunity Zone designations.

Refresh:

```bash
npm run seed:brevard-municipal
```

Re-run that command after `npm run seed:parcels:markets` refreshes Brevard. A parcel refresh clears the overlay until the join runs again.
