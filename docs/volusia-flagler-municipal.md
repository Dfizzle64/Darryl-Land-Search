# Volusia and Flagler municipal zoning and future land use

City zoning and future land use are joined by parcel centroid onto parcels that are already in the app. This pass does not download a new county parcel layer.

Volusia parcels are the Melbourne market extract (`data/fixtures/market-parcels/counties/12127`, 5–150 acres) and the smaller Orlando-shed sample (`data/fixtures/orlando-parcels/12127.geojson`). Flagler has no parcel baseline in this repo. Flagler city and unincorporated layers are cataloged and the join script will stamp them when a `12035` parcel fixture exists. County parcels are not pulled to fill that gap.

The catalog is `data/volusia-flagler-municipal.json`. Refresh the stamp with:

```bash
npm run seed:volusia-flagler-municipal
```

Joined codes are the published GIS values. They are not added to `data/zoning-config.json` or `data/flu-config.json`, and they do not create Opportunity Zone designations. A code the knowledge base does not list stays unknown.

## Wire-ready cities

Both zoning and future land use come from that city's service.

| City | County | Zoning | Future land use |
| --- | --- | --- | --- |
| Daytona Beach | Volusia | City Planning MapServer 10 `NewZoningClassification` | Planning MapServer 4 `LANDUSECODE` |
| Port Orange | Volusia | AGOL zoning layer 14 `Zoning` | AGOL layer 6 `FLU`. `Name` / `name` are case or ordinance titles and are not stored |
| Ormond Beach | Volusia | EnerGov layer 6 `ZONING` | EnerGov layer 5 `LAND_USE` |
| Deltona | Volusia | Zoning layer 1 `ZONING` | Land use designation layer 0 |
| DeLand | Volusia | ZoningDistricts layer 9 `Zoning_Dis` | FLU layer 4 `FLU_NAME` |
| Edgewater | Volusia | Development view layer 3 `ZONING` | Development view layer 2 `FLU` |
| South Daytona | Volusia | Zoning layer 0 `ZONING` | Future land use layer 0 `USE_` |
| Holly Hill | Volusia | AGOL parcel join on `PID`/`ALTKEY` when the parcel id matches; otherwise maps5 layer 4 `ZONDIST` | maps5 layer 5 `FLU_code` |
| Oak Hill | Volusia | CityServices layer 0 `ZONING` | CityServices layer 1 `LUNAME` |
| Ponce Inlet | Volusia | maps5 layer 3 `JUR_ZONING` | maps5 layer 4 `Land_Use` |
| Palm Coast | Flagler | Palm Coast zoning `LAYER` | Palm Coast FLUM `FLUCATEGOR` |
| Flagler Beach | Flagler | AGISO zoning layer 1 `ZONING_CO` | AGISO FLU layer 1 `FLU` |
| Bunnell | Flagler | AGISO zoning layer 2 `Zone_Code` | AGISO FLU layer 2 `FLU_Code` |
| Marineland | Flagler | AGISO zoning layer 4, field name `FLU` (that value is the district) | AGISO FLU layer 3 `FLU` |

## Flagler host

Flagler County does not publish a public county zoning or future land use FeatureServer. Palm Coast, Flagler Beach, Bunnell, Beverly Beach, Marineland, and unincorporated Flagler layers are hosted by the City of Palm Coast at `gis.palmcoast.gov`.

Unincorporated Flagler is AGISO zoning layer 0 (`ZONECODE`) and AGISO FLU layer 0 (`Label` / `LandUse`). It is used only when no incorporated city polygon covers the parcel.

## Partial (zoning only)

| Place | Zoning | Future land use |
| --- | --- | --- |
| Daytona Beach Shores | City zoning view `ZoningCode`. CountywideZoning `JURISD='Daytona Beach Shores'` is a fallback only when the city layer misses. | No public city FLU service. Left blank. |
| Beverly Beach | AGISO zoning layer 3 `ZONECODE` | No AGISO FLU layer. Left blank. |
| DeBary | CountywideZoning `OriginalZoningCode` where `JURISD='DeBary'` | Gap. Debary MapServer 21 matches the county FLU dump and is not a city FLUM. |
| New Smyrna Beach | CountywideZoning `OriginalZoningCode` where `JURISD='New Smyrna Beach'` | Gap. Not a city FLUM. |
| Orange City | CountywideZoning `OriginalZoningCode` where `JURISD='Orange City'` | Gap. Not a city FLUM. |
| Lake Helen | CountywideZoning `OriginalZoningCode` where `JURISD='Lake Helen'` | Gap. Not a city FLUM. |
| Pierson | CountywideZoning `OriginalZoningCode` where `JURISD='Pierson'` | Gap. Not a city FLUM. |

CountywideZoning is `https://maps5.vcgov.org/arcgis/rest/services/CountywideZoning/FeatureServer/2` (`C_DATE` 1/25/2024). It is not applied to cities that have their own zoning service.

## Rejected

- Volusia Open Data zoning `/Open_Data_4/FeatureServer/36` city rows with `ZONCODE=999`. Not municipal districts.
- `Future_Land_Use__2035` on `services.arcgis.com/ZOyb2t4B0UYuYNYH`. Sample geometry is Seattle, Washington.
- Ormond Beach `Zoning/FeatureServer/160` (about 27 polygons). EnerGov layer 6 is the zoning layer.
- maps5 `Port_Orange` (parcels and basemap, not zoning).
