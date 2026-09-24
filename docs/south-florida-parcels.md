# South Florida parcels (Wave 0)

Wave 0 is South Florida only: Miami-Dade, Monroe, Broward, and Palm Beach. Acreage is **5.0–150.0 inclusive**. Utilities, school grades, base flood elevations, and Opportunity Zone status are not joined. No eligible-tract rows were added.

| County | FIPS | Status | Parcels | Source |
| --- | --- | --- | --- | --- |
| Miami-Dade | 12086 | live | MD_LandInformation MapServer/26 | `https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/26` |
| Monroe | 12087 | live | APO Parcels MapServer/0 | `https://mcgis4.monroecounty-fl.gov/public/rest/services/Parcels/MapServer/0` |
| Broward | 12011 | partial | BCPA_EXTERNAL_JAN26 MapServer/16 | `https://gisweb-adapters.bcpa.net/arcgis/rest/services/BCPA_EXTERNAL_JAN26/MapServer/16` |
| Palm Beach | 12099 | partial | PARCEL_INFO FeatureServer/4 | `https://gis.pbcgov.org/arcgis/rest/services/Parcels/PARCEL_INFO/FeatureServer/4` |

## Property appraiser links

- Miami-Dade: `https://apps.miamidadepa.gov/ComparableSales/#/?folio={FOLIO}` (13 digits, no dashes). Last sale is not on the parcel layer.
- Monroe: `https://qpublic.schneidercorp.com/Application.aspx?AppID=605&LayerID=9946&PageTypeID=4&PageID=7635&KeyValue={RECHAR}`
- Broward: `https://bcpa.net/RecInfo.asp?URL_Folio={FOLIO}`
- Palm Beach: `https://pbcpao.gov/Property/Details?parcelId={PARID}`. The legacy `pbcgov.org/papa` detail URL is not used.

## Jurisdiction GIS viewers

The parcel drawer opens two public links. The property-appraiser link above already contains the parcel id. The GIS viewer is the card `gisViewerUrl`, with `gisViewerUrlAlt` when the card has one. A new shelf adds the same pair to `src/lib/jurisdictionLinks.ts`. Zoning REST layers stay on the join. They are not the viewer link. Fort Lauderdale does not get its own viewer URL.

- Miami-Dade: `https://experience.arcgis.com/experience/74e9a9f78b094ba2b17d86a0bfeb2eeb` (alt `https://mdc.maps.arcgis.com/home/index.html`)
- Monroe: `https://monroecounty-fl.maps.arcgis.com/apps/webappviewer/index.html?id=2e52d422378e4b48a471d02959265ecc` (alt `https://www.monroecounty-fl.gov/gis`)
- Broward: `https://geohub-bcgis.opendata.arcgis.com/` (alt `https://web.bcpa.net/bcpaclient/#/Record-Search`)
- Palm Beach: `https://pbcgov.maps.arcgis.com/home/index.html` (alt `https://pbcgov.maps.arcgis.com/apps/webappviewer/index.html`)

## Jump to an address

The header jump box accepts a street address or coordinates (`26.1224, -80.1373` or `26.1224 -80.1373`). A street address uses the Census oneline geocoder. Invalid coordinates say "Those coordinates are not valid." A missed address says "Couldn't find that address." The map flies to the point. When a loaded parcel polygon contains that point, the drawer selects it. A point inside the South Florida shelf switches to that market when the current market does not already contain it.

## Zoning and future land use

- Miami-Dade zoning is unincorporated `MapServer/18` (`ZONE`) and the municipal mosaic `MapServer/19`. `PRIMARY_ZONE` on the parcel is a neighborhood code and is not stored as zoning. Future land use is CDMP `MapServer/7`.
- Monroe zoning is APO_GIS `MapServer/19`. Future land use is APO_GIS `MapServer/20`. City zoning was not inventoried.
- Broward BMSD zoning is unincorporated only. The city zoning mosaic (`MapServer/9`) is partial and is not a Fort Lauderdale ordinance. Future land use is numeric `SLUC1` on `MapServer/10`, not a plain-language label.
- Palm Beach zoning is unincorporated OpenData `MapServer/9`. Future land use is `open_data_v2` FeatureServer/6. City zoning is not on this card.

## Known gaps

- **Broward CAMA.** MapServer/16 is folio and geometry. The FDOR `CO_NO=16` join did not return from batched `PARCEL_ID` queries, so owner, sale, and value are not on these rows. BMSD parcel attributes are not the county roll. City zoning is the partial mosaic, not a Fort Lauderdale ordinance.
- **Monroe TLS.** `mcgis4.monroecounty-fl.gov` fails default certificate verification. Ingest retries that host without verification. qPublic often blocks bots. The record link is still for people. `maps.monroecounty.gov` is Monroe County, New York, and is rejected.
- **Palm Beach count.** The ACRES 5.0–150.0 query reports about 146,014 object ids. This shelf kept the parcels that survived geometry normalize and parcel-id dedupe, so Palm Beach is partial, not a full object-id extract. `maps.co.palm-beach.fl.us` TLS is fragile. The token-gated OpenData mirror and `opendata.pbcgov.org` are not used. `PROPERTY_USE` is text, not a numeric DOR code.

Refresh with:

```bash
python3 scripts/south_florida_parcels.py
```

That command does not rewrite the other market shelves.
