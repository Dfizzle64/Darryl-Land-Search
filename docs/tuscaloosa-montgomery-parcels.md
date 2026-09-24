# Tuscaloosa and Montgomery MSA parcels

Public GIS only. Acreage band is 5.0–150.0 inclusive. Sale price is null on every parcel.
These markets have no new eligible-tract rows. Nothing here is an Opportunity Zone designation.

Rejected: `https://services6.arcgis.com/EbVsqZ18sv1kVJ3k/arcgis/rest/services/Montgomery_County_Parcels/FeatureServer/0` (New York East / Amsterdam sample, SWIS fields).
Not queried: `https://services5.arcgis.com/6AasMFHPoqawuioF/arcgis/rest/services/Zoning_Districts_Public/FeatureServer` (HTTP 499).
Not joined: `https://services1.arcgis.com/DADyRNMb7tdzKmmq/arcgis/rest/services/Framework_Zoning_Map/FeatureServer/0` (draft, not the official zoning map).

Prattville zoning is ZONING_JULY_2017 (internal layer name Zoning_2022). Vintage is unclear: sampled DATE_ZONED values are often May 1, 1987, with some later ordinances. Joined only where the polygon overlaps Autauga or Elmore parcels. Partial until a current official zoning service is confirmed.

## Counties

| County | FIPS | Parcels | Source count | Zoning joined | FLU joined | Sale dates | Sale prices |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tuscaloosa | 01125 | 11,596 | 11646 | 1046 | 703 | 10996 | 0 |
| Montgomery | 01101 | 9,954 | 10026 | 5106 | 0 | 0 | 0 |
| Elmore | 01051 | 9,758 | 14848 | 288 | 0 | 0 | 0 |
| Autauga | 01001 | 7,047 | 7530 | 589 | 0 | 0 | 0 |
| Hale | 01065 | 0 | — | — | — | — | — |
| Pickens | 01107 | 0 | — | — | — | — | — |
| Greene | 01063 | 0 | — | — | — | — | — |
| Lowndes | 01085 | 0 | — | — | — | — | — |

## Zoning by city

- **Tuscaloosa** (01125): zoning join rate 9.0% (City of Tuscaloosa 805, Northport 241).
- **Montgomery** (01101): zoning join rate 51.3% (City of Montgomery 5,106).
- **Elmore** (01051): zoning join rate 2.9% (Millbrook 203, Prattville 85).
- **Autauga** (01001): zoning join rate 8.4% (Prattville 589).

## Remaining gaps

- Hale County (01065), Pickens County (01107), and Greene County (01063): no public parcel REST.
- Bibb County (01007): still a Birmingham parcel gap. No public REST in this pull.
- Lowndes County (01085): Montgomery MSA county with no verified public parcel card.
- Wetumpka: token-gated zoning (HTTP 499). Not joined.
- Prattville future land use is 13 coarse polygons and was not joined as site-level FLU.
- City of Montgomery has no separate public FLU FeatureServer in this pull.

