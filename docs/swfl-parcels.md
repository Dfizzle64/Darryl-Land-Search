# SWFL parcels

SWFL is an other market: **Lee**, **Collier**, optional **Sarasota**, and partial **Charlotte**. Acreage is **5.0–150.0 inclusive**. Sources are public GIS only. Eligible tracts use **Eligible — not designated**. Nothing in this market is a certified or designated 2027 QOZ.

Municipalities are first-class records in `data/swfl-municipalities.json`. Lee parcels carry `jurisdictionCode` from the county municipal code. Collier ParcelJoin has no city field, so Naples, Marco Island, and Everglades City stay on that list without a spatial join.

## What was pulled

| County | Role | Parcels | Source |
| --- | --- | --- | --- |
| Lee | Core | County ParcelAddress, `GISACRES` 5–150 | `https://gismapserver.leegov.com/gisserver910/rest/services/Layers/ParcelAddress/MapServer/0` |
| Collier | Core | County ParcelJoin (`TOTALACRES` cast to float) | `https://services2.arcgis.com/SlIq32SqARUHIhSx/arcgis/rest/services/Parcels/FeatureServer/42` |
| Sarasota | Optional | Reused Tampa tiles | Florida DOH EHWATER layer 57, not downloaded again |
| Charlotte | Partial | DOH land square feet 5–150 | Florida DOH EHWATER layer 7 |

Refresh Lee, Collier, and Charlotte with:

```bash
python3 scripts/seed_market_parcels.py --market SWFL
```

Sarasota is skipped when its tiles already exist. `--refresh` would re-download it from DOH.

## Gaps

- **Collier sales are not on ParcelJoin.** The layer has folio, owner names, and total acres. Sale price and date are left empty. They are not filled from a paid vendor. The state DOH Collier layer does carry NAL sales; this extract stays on ParcelJoin so the gap stays visible.
- **Sanibel zoning REST.** Lee ParcelAddress zoning is blank for almost every 5–150 acre Sanibel parcel (`MUNICODE` T). Sanibel's public services are a future-land-use map series, not a parcel zoning code, and were not joined.
- **Fort Myers native GIS is TLS-blocked.** `https://gis.fortmyers.gov/arcgis/rest/services` failed certificate verification and was not ingested. City of Fort Myers parcels in the band are the county layer where `MUNICODE` is P.
- **Bonita Springs, Estero, and Fort Myers Beach are county stubs.** They have no independent parcel REST. They are Lee County rows (`MUNICODE` B, E, and W).

Charlotte is partial: the county MapServer publishes zoning and Punta Gorda zoning, not the parcel roll used here. Those zoning polygons are not joined. The parcel polygons are the countywide DOH land-area slice.

## Rejected

- **FGDL zoning.** The Florida Geographic Data Library zoning layer is a north-Florida geography. It is not used for any SWFL county or city.
- **EagleView Lee republish.** `Lee_County_FL_Parcels` on EagleView's server is a republish of county parcels. Lee uses the county ParcelAddress service instead.

## Eligible tracts

75 Rev. Proc. 2026-14 appendix tracts (11 rural, 64 non-rural): Lee 38, Collier 19, Sarasota 13, Charlotte 5. Sarasota is optional and outer-edge; its 13 non-rural GEOIDs are the same ones already on Tampa. Charlotte is outer-edge. The status chip is **Eligible — not designated**.
