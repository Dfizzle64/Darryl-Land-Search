# South Florida parcels (Wave 0)

Wave 0 on this shelf is Miami-Dade, Broward, and Palm Beach. Monroe is deferred to a follow-up. Acreage is **5.0–150.0 inclusive**. Utilities, school grades, base flood elevations, and Opportunity Zone status are not joined. No eligible-tract rows were added.

| County | FIPS | Status | Parcels | Source |
| --- | --- | --- | --- | --- |
| Miami-Dade | 12086 | live | MD_LandInformation MapServer/26 | `https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/26` |
| Broward | 12011 | partial | BCPA_EXTERNAL_JAN26 MapServer/16 | `https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN26/MapServer/16` |
| Palm Beach | 12099 | partial | PARCEL_INFO FeatureServer/4 | `https://gis.pbcgov.org/arcgis/rest/services/Parcels/PARCEL_INFO/FeatureServer/4` |

## Property appraiser links

- Miami-Dade: `https://apps.miamidadepa.gov/ComparableSales/#/?folio={FOLIO}` (13 digits, no dashes). Last sale is not on the parcel layer.
- Broward: `https://bcpa.net/RecInfo.asp?URL_Folio={FOLIO}`
- Palm Beach: `https://pbcpao.gov/Property/Details?parcelId={PARID}`. The legacy `pbcgov.org/papa` detail URL is not used.

## Jurisdiction GIS viewers

The parcel drawer links the layer that supplied zoning. When zoning misses, the link is the county parcel service. These are the card REST homes, without `/query`. Fort Lauderdale does not have its own joined layer. A Broward city hit uses the partial mosaic, and the label says that mosaic is not a Fort Lauderdale ordinance.

- Miami-Dade municipal: `MD_LandInformation/MapServer/19`. Unincorporated: `MapServer/18`. Parcel fallback: `MapServer/26`.
- Broward BMSD (unincorporated): `Broward_Municipal_Service_District_Zoning/FeatureServer/2`. City mosaic: `BCPA_EXTERNAL_JAN26/MapServer/9`. Parcel fallback: `MapServer/16`.
- Palm Beach unincorporated zoning: `Planning_Open_Data/MapServer/9`. Parcel fallback: `PARCEL_INFO/FeatureServer/4`.

## Jump to an address

The header accepts a street address or `lat, long`. A street address uses the Census oneline geocoder. The map flies to the point. When a loaded parcel polygon contains that point, the drawer selects it. A point inside the South Florida shelf switches to that market when the current market does not already contain it.

## Zoning and future land use

- Miami-Dade zoning is unincorporated `MapServer/18` (`ZONE`) and the municipal mosaic `MapServer/19`. `PRIMARY_ZONE` on the parcel is a neighborhood code and is not stored as zoning. Future land use is CDMP `MapServer/7`.
- Broward BMSD zoning is unincorporated only. The city zoning mosaic (`MapServer/9`) is partial and is not a Fort Lauderdale ordinance. Future land use is numeric `SLUC1` on `MapServer/10`, not a plain-language label.
- Palm Beach zoning is unincorporated OpenData `MapServer/9`. Future land use is `open_data_v2` FeatureServer/6. City zoning is not on this card.

## Known gaps

- **Broward CAMA.** MapServer/16 is folio and geometry. The FDOR `CO_NO=16` join did not return from batched `PARCEL_ID` queries, so owner, sale, and value are not on these rows. BMSD parcel attributes are not the county roll. City zoning is the partial mosaic, not a Fort Lauderdale ordinance.
- **Monroe deferred.** Monroe County (12087) is not on this shelf. The TLS/qPublic ingest is a follow-up, not part of this pull request.
- **Palm Beach count.** The ACRES 5.0–150.0 query reports about 146,014 object ids. This shelf kept the parcels that survived geometry normalize and parcel-id dedupe, so Palm Beach is partial, not a full object-id extract. `maps.co.palm-beach.fl.us` TLS is fragile. The token-gated OpenData mirror and `opendata.pbcgov.org` are not used. `PROPERTY_USE` is text, not a numeric DOR code.

Refresh with:

```bash
python3 scripts/south_florida_parcels.py
```

That command does not rewrite the other market shelves.
