# Durham County parcels (Raleigh–Durham)

Durham County (FIPS **37063**) is a complete 5.0–150.0 acre extract on the shared market-parcel tiles. The primary source is the City–County property layer, not NC OneMap.

## Wire

| Role | Endpoint | Id / fields |
| --- | --- | --- |
| Parcels | `PublicServices/Property/MapServer/4` | **REID** (not PIN). Owner, mailing, situs, acreage, tax, last sale, `CITY` / `ETJ`, attribute `ZONING` |
| Zoning | `PublicServices/Planning/MapServer/12` | `UDO_LABEL` / `ZONE_CODE` for Durham City and unincorporated Durham County |
| Future land use | `PublicServices/Planning/MapServer/25` Place Type | `PlaceType` / `PlaceTypeName` |
| Fallback | NC OneMap `NC1Map_Parcels` FeatureServer/1 | `cntyfips='063'`. `parno` tracks PIN. No sale price |

Appraiser: `https://taxcama.dconc.gov/camapwa/PropertySummary.aspx?PARCELPK={PARCEL_PK}` or `?REID={REID}`. Viewer: https://maps.durhamnc.gov/

Count checked 2026-09-23: about 133,548 countywide parcels and **4,940** with `ACREAGE` from 5 through 150. MaxRecordCount is 2,000, so the seed pages by object id.

## Municipalities

County parcels are countywide. Zoning and future land use for tip cities are municipal.

| Municipality | In this pull | Zoning | Future land use |
| --- | --- | --- | --- |
| Durham (city) | Wired | Joint UDO. Keep a non-null parcel `ZONING`; spatial-join `/12` when it is null | Place Type `/25` |
| Durham County (unincorporated) | Wired | Same joint UDO | Place Type `/25` |
| Chapel Hill | Wired for the Durham tip | `OpenData/Zoning_Districts` `ZONING` | **Gap.** ImageServer only |
| Morrisville | Wired for the Durham tip | Wake `Planning/Zoning/22` `CLASS` | **Gap.** No polygon layer verified on this footprint |
| Raleigh | Wired for the Durham tip | Raleigh `Planning/Zoning/0` `ZONING` | **Gap.** No polygon layer verified on this footprint |
| Cary | Wired for the Durham tip | Raleigh regional `Planning/Zoning/3` `CLASS` (there is no `ZONING` field) | **Gap.** Two parcels in the acreage band |

A parcel is spatial-joined to the tip layer when `CITY` or `ETJ` names that city, or when `ZONING` is null or tip-mixed (annotated values such as `CHAP HILL,R-1`). A Chapel Hill / Morrisville / Raleigh / Cary parcel does not take Durham UDO as its only zoning, and it does not take Place Type as future land use.

## Follow-ups (not in this pull)

Wake (37183) and Orange (37135) still use NC OneMap. Their shared tip layers are already registered in `scripts/triangle_municipalities.py`:

- Wake can reuse Raleigh, Cary, and Morrisville zoning via `layers_for_county("37183")`.
- Orange can reuse Chapel Hill zoning via `layers_for_county("37135")`.
- Place Type is Durham-only. `place_type_for_county` returns nothing for Wake and Orange.

Those counties are not re-downloaded here.

## Other gaps

- PIN is not a stable parcel id. The tile id is `37063:{REID}`.
- Last sale is the package sale, then the land sale. There is no multi-transfer sales layer.
- Owner phones and emails are not collected.
- The public Cary zoning field is `CLASS`, not `ZONING`.
