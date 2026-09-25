# FL-rest batch 1 parcels

This is FL-rest batch 1 (parcel gaps). Twenty Florida counties that had no 5.0–150.0 acre parcels on main, or only a sample or gap row. Acreage is **5.0–150.0 inclusive**. Utilities, school grades, base flood elevations, and Opportunity Zone status are not joined. Household income stays Census ACS 5-year B19013_001E by 2020 tract GEOID. No eligible-tract rows were added.

Shelves: **North Florida** and **Panhandle Florida** are new parcel shelves appended after the existing markets. **Marion** is on the existing North-Central Florida shelf. Dixie, Gadsden, Jefferson, Madison, Taylor, and Wakulla stay on Big Bend. Leon was not rewritten.

| County | FIPS | Status | Parcels | Source |
| --- | --- | --- | ---: | --- |
| Calhoun | 12013 | live | 3,863 | `fl-calhoun-mil1-12013` |
| Columbia | 12023 | live | 10,747 | `fl-columbia-parcels-12023` |
| Dixie | 12029 | partial | 3,213 | `fl-dixie-mil1-12029` |
| Flagler | 12035 | live | 3,446 | `fl-flagler-parcels-12035` |
| Franklin | 12037 | partial | 742 | `fl-franklin-mil1-12037` |
| Gadsden | 12039 | live | 5,933 | `fl-gadsden-mil1-12039` |
| Gulf | 12045 | partial | 1,219 | `fl-gulf-mil1-12045` |
| Hamilton | 12047 | partial | 4,158 | `fl-hamilton-mil1-12047` |
| Holmes | 12059 | partial | 6,339 | `fl-holmes-mil1-12059` |
| Jackson | 12063 | live | 11,026 | `fl-jackson-mil1-12063` |
| Jefferson | 12065 | live | 5,158 | `fl-jefferson-parcels-12065` |
| Lafayette | 12067 | partial | 2,834 | `fl-lafayette-srwmd-12067` |
| Liberty | 12077 | live | 1,627 | `fl-liberty-mil1-12077` |
| Madison | 12079 | partial | 7,266 | `fl-madison-sdl-12079` |
| Marion | 12083 | live | 17,576 | `fl-marion-parcels-12083` |
| Suwannee | 12121 | partial | 11,818 | `fl-suwannee-srwmd-12121` |
| Taylor | 12123 | partial | 3,836 | `fl-taylor-mil1-12123` |
| Union | 12125 | partial | 2,344 | `fl-union-srwmd-12125` |
| Wakulla | 12129 | live | 4,866 | `fl-wakulla-parcelm-12129` |
| Washington | 12133 | live | 7,090 | `fl-washington-agol-12133` |

## Parcel sources

Polygons come from the research card's public parcel layer, filtered to 5.0–150.0 acres. FDOR Florida Statewide Cadastral 2025 (`FeatureServer/0`) fills blank owner, just value, DOR use, acreage, and roll-year sale by `PARCEL_ID`. A county-number-only filter is not used.

- Calhoun, Dixie, Franklin, Gadsden, Gulf, Hamilton, Holmes, Jackson, Liberty, Taylor: `https://gis.arpc.org/server/rest/services/Florida_Statewide_Cadastral_MIL1/MapServer/0`
- Columbia: `https://gis.columbiacountyfla.com/hosting/rest/services/Parcels_and_Addresses/MapServer/2`
- Flagler: `https://services3.arcgis.com/hSKL9bYjhP4rHxSD/arcgis/rest/services/Flagler_County_Parcels/FeatureServer/0`
- Jefferson: `https://services5.arcgis.com/vFMp1Ly1q6rKKp0o/arcgis/rest/services/JC__PARCELS_view/FeatureServer/0`
- Lafayette, Suwannee, Union: `http://gis.srwmd.state.fl.us/arcgis/rest/services/SRWMDGIS/SRWMD_Parcels/FeatureServer/8` (Lafayette), `/11` (Suwannee), `/13` (Union)
- Madison: `https://services3.arcgis.com/DvTqoyLKkslnGFR5/arcgis/rest/services/Madison_County_Florida/FeatureServer/0`
- Marion: `https://gis.marionfl.org/public/rest/services/General/ParcelsAndSubdivisions/MapServer/0`
- Wakulla: `https://services9.arcgis.com/vAltLjtfYIJc7pDt/arcgis/rest/services/ParcelM/FeatureServer/0`
- Washington: `https://services2.arcgis.com/xDFo56nFuq1SBnBw/arcgis/rest/services/WashingtonParcelsAGOL/FeatureServer/0`
- FDOR join: `https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0`

## Property appraiser links

The parcel id is in the URL except Gadsden, Madison, and Marion, which stay on a search page.

- Calhoun: `https://qpublic.schneidercorp.com/Application.aspx?AppID=829&LayerID=15004&PageTypeID=4&PageID=6748&KeyValue={id}`
- Columbia: `https://www.columbiacountyfla.com/ParcelDetails.aspx?ParcelNo={id}`
- Dixie: `https://qpublic.schneidercorp.com/Application.aspx?AppID=867&LayerID=16385&PageTypeID=4&PageID=7230&KeyValue={id}`
- Flagler: `https://qpublic.schneidercorp.com/Application.aspx?AppID=598&LayerID=9801&PageTypeID=4&PageID=4330&KeyValue={id}`
- Franklin: `https://franklin-search.gsacorp.io/parcel/{id}`
- Gadsden: `https://qpublic.schneidercorp.com/Application.aspx?App=GadsdenCountyFL&PageType=Search` (search page)
- Gulf: `https://beacon.schneidercorp.com/Application.aspx?AppID=819&LayerID=15077&PageTypeID=4&PageID=6812&KeyValue={id}`
- Hamilton: `https://beacon.schneidercorp.com/Application.aspx?AppID=817&LayerID=14544&PageTypeID=4&PageID=6409&KeyValue={id}`
- Holmes: `https://qpublic.schneidercorp.com/Application.aspx?AppID=821&LayerID=14700&PageTypeID=4&PageID=6565&KeyValue={id}`
- Jackson: `https://qpublic.schneidercorp.com/Application.aspx?AppID=851&LayerID=15884&PageTypeID=4&PageID=7081&KeyValue={id}`
- Jefferson: `https://qpublic.schneidercorp.com/Application.aspx?AppID=866&LayerID=16381&PageTypeID=4&PageID=7228&KeyValue={id}`
- Lafayette: `https://beacon.schneidercorp.com/Application.aspx?AppID=1396&LayerID=47258&PageTypeID=4&PageID=19927&KeyValue={id}`
- Liberty: `https://qpublic.schneidercorp.com/Application.aspx?AppID=828&LayerID=15003&PageTypeID=4&PageID=13691&KeyValue={id}`
- Madison: `https://qpublic.schneidercorp.com/Application.aspx?App=MadisonCountyFL&Layer=Parcels&PageType=Search` (search page)
- Marion: `https://www.pa.marion.fl.us/PropertySearch.aspx` (search page)
- Suwannee: `https://suwannee-search.gsacorp.io/parcel/{id}`
- Taylor: `https://beacon.schneidercorp.com/Application.aspx?AppID=792&LayerID=11749&PageTypeID=4&PageID=5268&KeyValue={id}`
- Union: `https://union.floridapa.com/GIS/?pin={id}`
- Wakulla: `https://qpublic.schneidercorp.com/Application.aspx?AppID=836&LayerID=15205&PageTypeID=4&PageID=6833&KeyValue={id}` (dashes kept)
- Washington: `https://qpublic.schneidercorp.com/Application.aspx?AppID=896&LayerID=16944&PageTypeID=4&PageID=7615&KeyValue={id}`

## Jurisdiction GIS viewers

- Calhoun: `https://qpublic.schneidercorp.com/Application.aspx?AppID=829&LayerID=15004&PageTypeID=2&PageID=6748`
- Columbia: `https://columbia.floridapa.com/gis/` (alt `https://search.ccpafl.com/map/`)
- Dixie: `https://qpublic.schneidercorp.com/Application.aspx?AppID=867&LayerID=16385&PageTypeID=2&PageID=7230`
- Flagler: `https://qpublic.schneidercorp.com/Application.aspx?AppID=598&LayerID=9801&PageTypeID=2&PageID=4328`
- Franklin: `https://franklin-search.gsacorp.io/map`
- Gadsden: `https://qpublic.schneidercorp.com/Application.aspx?App=GadsdenCountyFL&PageType=Search`
- Gulf: `https://beacon.schneidercorp.com/Application.aspx?AppID=819&LayerID=15077&PageTypeID=2&PageID=6812`
- Hamilton: `https://beacon.schneidercorp.com/Application.aspx?AppID=817&LayerID=14544&PageTypeID=2&PageID=6409`
- Holmes: `https://qpublic.schneidercorp.com/Application.aspx?AppID=821&LayerID=14700&PageTypeID=2&PageID=6565`
- Jackson: `https://qpublic.schneidercorp.com/Application.aspx?AppID=851&LayerID=15884&PageTypeID=2&PageID=7081`
- Jefferson: `https://qpublic.schneidercorp.com/Application.aspx?AppID=866&LayerID=16381&PageTypeID=2&PageID=7228`
- Lafayette: `https://beacon.schneidercorp.com/Application.aspx?AppID=1396&LayerID=47258&PageTypeID=2&PageID=19927`
- Liberty: `https://qpublic.schneidercorp.com/Application.aspx?AppID=828&LayerID=15003&PageTypeID=2&PageID=13691`
- Madison: `https://planning.madisoncountyfla.com/gis/`
- Marion: `https://gis.marionfl.org/`
- Suwannee: `https://suwannee-search.gsacorp.io/map`
- Taylor: `https://beacon.schneidercorp.com/Application.aspx?AppID=792&LayerID=11749&PageTypeID=2&PageID=5268`
- Union: `https://union.floridapa.com/GIS/`
- Wakulla: `https://gis-portal-update-wakullaplanning.hub.arcgis.com/`
- Washington: `https://qpublic.schneidercorp.com/Application.aspx?AppID=896&LayerID=16944&PageTypeID=2&PageID=7613`

## Zoning and future land use

- Calhoun, Jackson, Liberty, and Washington publish future land use and no countywide zoning layer.
- Columbia, Flagler, Jefferson, Marion, and Wakulla publish zoning and future land use.
- Gadsden uses the future-land-use category as the land-use district. Quincy and Havana zoning override it inside those cities.
- Franklin zoning is a parcel attribute. Carrabelle has city zoning and future land use. Unincorporated future land use is not queryable.
- Gulf, Hamilton, Holmes, Lafayette, Suwannee, and Union have no queryable zoning or future land use.
- Dixie, Madison, and Taylor have no queryable zoning or future land use. Their future-land-use fallback is labeled **2008 statewide broad land-use categories, not current zoning**. Those three stay partial.

## Known gaps

- **Partial counties.** Dixie, Franklin, Gulf, Hamilton, Holmes, Lafayette, Madison, Suwannee, Taylor, and Union stay partial.
- **Search-only appraisers.** Gadsden, Madison, and Marion do not put the parcel id in the URL.
- **Gadsden owners.** The property appraiser warns that owner names may be swapped after a data migration. FDOR is preferred. 537 parcels flag a conflict with the county roll name.
- **Jefferson.** The land-use layer repeats parcels. Rows are deduped on parcel id. `OwnerPhone` and `OwnerEmail` are not requested.
- **Wakulla FDOR key.** Dashes are stripped for the FDOR join and kept in the property-appraiser URL.
- **Columbia FDOR ids.** County `ParcelNo` and FDOR `PARCEL_ID` often differ, so some rows keep county owner and acres only.
- **GeoPlan.** Dixie, Madison, and Taylor future land use is the 2008 statewide broad category, not current zoning.
- **No TLS fallback.** None of these 20 cards called out a certificate host.

Refresh with:

```bash
python3 scripts/fl_rest_batch1.py
```

That command patches these counties into the existing shelves. It does not rewrite the other markets.
