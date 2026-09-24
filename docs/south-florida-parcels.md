# South Florida parcels (Wave 0)

Wave 0 is South Florida only. This shelf is Miami-Dade, Monroe, Broward, and Palm Beach. Acreage is **5.0–150.0 inclusive**. Utilities, school grades, base flood elevations, and Opportunity Zone status are not joined. No eligible-tract rows were added.

| County | FIPS | Status | Parcels | Source |
| --- | --- | --- | --- | --- |
| Miami-Dade | 12086 | live | MD_LandInformation MapServer/26 | `https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/26` |
| Monroe | 12087 | live | APO Parcels MapServer/0 | `https://mcgis4.monroecounty-fl.gov/public/rest/services/Parcels/MapServer/0` |
| Broward | 12011 | partial | BCPA_EXTERNAL_JAN26 MapServer/16 | `https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN26/MapServer/16` |
| Palm Beach | 12099 | live | PARCEL_INFO FeatureServer/4 | `https://gis.pbcgov.org/arcgis/rest/services/Parcels/PARCEL_INFO/FeatureServer/4` |

## Property appraiser links

- Miami-Dade: `https://apps.miamidadepa.gov/ComparableSales/#/?folio={FOLIO}` (13 digits, no dashes). Last sale is not on the parcel layer.
- Monroe: `https://qpublic.schneidercorp.com/Application.aspx?AppID=605&LayerID=9946&PageTypeID=4&PageID=7635&KeyValue={RECHAR}`
- Broward: `https://bcpa.net/RecInfo.asp?URL_Folio={FOLIO}`
- Palm Beach: `https://pbcpao.gov/Property/Details?parcelId={PARID}`. The legacy `pbcgov.org/papa` detail URL is not used.

## Zoning and future land use

- Miami-Dade zoning is unincorporated `MapServer/18` (`ZONE`) and the municipal mosaic `MapServer/19`. `PRIMARY_ZONE` on the parcel is a neighborhood code and is not stored as zoning. Future land use is CDMP `MapServer/7`.
- Monroe zoning is APO_GIS `MapServer/19`. Future land use is APO_GIS `MapServer/20`. City zoning was not inventoried.
- Broward BMSD zoning is unincorporated only. The city zoning mosaic (`MapServer/9`) is partial. Future land use is numeric `SLUC1` on `MapServer/10`, not a plain-language label.
- Palm Beach zoning is unincorporated OpenData `MapServer/9`. Future land use is `open_data_v2` FeatureServer/6. City zoning is not on this card.

## Known gaps

- **Broward CAMA join.** MapServer/16 is folio and geometry. Countywide owner, sale, and value come from the FDOR statewide cadastral layer where `CO_NO=16` and `PARCEL_ID` equals the folio. A countywide `CO_NO=16` query times out, so the join is by folio. BMSD parcel attributes are not the county roll.
- **Monroe TLS.** `mcgis4.monroecounty-fl.gov` fails default certificate verification. Ingest retries that host without verification. qPublic HTML often blocks bots. The record link is still for people. `maps.monroecounty.gov` is Monroe County, New York, and is rejected.
- **Palm Beach TLS.** `maps.co.palm-beach.fl.us` is fragile from some clients. The token-gated `gis.pbcgov.org` OpenData mirror and `opendata.pbcgov.org` are not used. `PROPERTY_USE` is text, not a numeric DOR code.

Refresh with:

```bash
python3 scripts/south_florida_parcels.py
```

That command does not rewrite the other market shelves.
