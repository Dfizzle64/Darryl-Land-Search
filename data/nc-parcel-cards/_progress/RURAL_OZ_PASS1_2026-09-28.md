# NC Rural-OZ Pass 1 — parcel re-verify (2026-09-28)

**County set:** the 50 NC counties on LSB's statewide rural-OZ list (`/workspace/coverage/rural-oz-priority-counties-statewide-appendix-2026-09-28.csv`, IRS Rev. Proc. 2026-14 appendix, Rural) that are **not** among the 35 market-area counties already live in the app (`rural-oz-priority-counties-2026-09-28.csv`). The live 35 were skipped on purpose (Pass 2 covers them separately). Full list: `/workspace/gis-research/enrichment/NC/rural-oz-counties-2026-09-28.{md,csv}`.

**Method:** live checks on the card's primary parcels layer, public and with no token. Each check covers: layer `f=json` (polygon geometry); `returnCountOnly`; a populated parcel-ID field (non-empty on ≥80% of rows); one sample feature with rings in WGS84 whose centroid falls inside NC; and an acreage field returning a non-trivial count for 5–150 ac. Script: `_progress/rural-oz-pass1/check.py`. No paid vendors, emails or phones.

**Result:** 49 verified · 1 fixed · 0 still-blocked.

| fips | county | rural OZ tracts | parcel layer URL | parcel ID field | count | acreage field | 5–150 ac | status | notes | coverage-inventory 09-24 |
|---|---|---:|---|---|---:|---|---:|---|---|---|
| 37003 |  Alexander | 1 | https://maps.alexandercountync.gov/arcgis/rest/services/Website_map/MapServer/26 | PIN | 26980 | CALCULATED_ACREAGE | 7305 | verified | resultRecordCount is rejected unless orderByFields is set (the MapServer exposes no OID for paging). An unpaged sample query works. | carded |
| 37005 |  Alleghany | 1 | https://www.webgis.net/arcgis/rest/services/NC/Alleghany/MapServer/11 | PIN | 14808 | TOTAL_CALCULATED | 3628 | verified |  | in_progress |
| 37009 |  Ashe | 3 | https://gis.ashecountygov.com/arcgis/rest/services/OpenData/TaxParcel/MapServer/0 | ParcelNumber | 38842 | TotalCalculatedAcres | 9066 | verified | Sample needs resultRecordCount (a full-page geometry query returns 500). | carded |
| 37011 |  Avery | 1 | https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Avery_AGOL/FeatureServer/21 | PIN | 24610 | Calculated_Acreage | 4043 | verified |  | carded |
| 37013 |  Beaufort | 7 | https://services1.arcgis.com/oXsk9nimtmSEU8Ko/arcgis/rest/services/Beaufort_Service/FeatureServer/4 | ALPHA | 45229 | CalcAcres | 8050 | verified |  | carded |
| 37015 |  Bertie | 3 | https://services3.arcgis.com/tiupcc8dC1j2CPV5/arcgis/rest/services/Bertie_Parcel_Viewer/FeatureServer/4 | GEOPIN | 18788 | CALCACRE | 4455 | verified |  | in_progress |
| 37017 |  Bladen | 6 | https://gis.bladenco.org/server/rest/services/BladenCounty/MapServer/1 | PIN | 33335 | MapAcres | 9242 | verified |  | carded |
| 37021 |  Buncombe | 1 | https://gis.buncombecounty.org/arcgis/rest/services/opendata/FeatureServer/1 | PIN | 135323 | Acreage | 10526 | verified |  | live |
| 37023 |  Burke | 5 | https://gis.burkenc.org/arcgis/rest/services/ProdParcelViewFC/MapServer/0 | PIN | 59479 | CALCULATED_ACRES | 8045 | verified |  | carded |
| 37027 |  Caldwell | 4 | https://gis.caldwellcountync.org/arcgis/rest/services/NCOnemap/NCOneMap/FeatureServer/45 | PID | 52763 | TotalCalcAcres | 8142 | verified |  | carded |
| 37031 |  Carteret | 5 | https://arcgisweb.carteretcountync.gov/arcgis/rest/services/Layers/Parceldata/FeatureServer/0 | PIN15 | 64284 | GISacres | 3466 | verified |  | carded |
| 37033 |  Caswell | 2 | https://www.webgis.net/arcgis/rest/services/NC/Caswell/MapServer/9 | PIN | 17222 | AV_ACRES | 5921 | verified |  | in_progress |
| 37039 |  Cherokee | 5 | https://maps.cherokeecounty-nc.gov/ccgis/rest/services/OfficeView/MapServer/1 | NEWPIN | 35749 | TOTAL_CALCULATED_ACRES | 6510 | verified |  | carded |
| 37041 |  Chowan | 1 | https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Chowan_Feature_Service/FeatureServer/0 | PIN | 12888 | ACRES | 2153 | verified |  | in_progress |
| 37049 |  Craven | 10 | https://gis.cravencountync.gov/arcgis/rest/services/JustParcels/MapServer/0 | PID | 60029 | PACREA | 5945 | verified |  | carded |
| 37055 |  Dare | 1 | https://services1.arcgis.com/ozZJ6IIlcOT869Kx/arcgis/rest/services/gis_polygons/FeatureServer/0 | parcel | 47870 | calcacre | 2222 | verified |  | carded |
| 37065 |  Edgecombe | 3 | https://gis.edgecombecountync.gov/arcgis/rest/services/webmap/MapServer/10 | linkpin | 31608 | acreage | 4257 | verified |  | carded |
| 37075 |  Graham | 2 | https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GrahamAGOL/FeatureServer/6 | PARNUM | 9459 | calcacres | 1963 | verified |  | in_progress |
| 37079 |  Greene | 4 | https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Greene_Service/FeatureServer/4 | pin | 12778 | calc_acre | 3604 | verified |  | in_progress |
| 37083 |  Halifax | 12 | https://services8.arcgis.com/0zS9csrI5fS6Bcym/arcgis/rest/services/OpenGov_RR_Layers/FeatureServer/22 | PARID | 39355 | ACREAGE | 6461 | verified |  | carded |
| 37087 |  Haywood | 3 | https://maps.haywoodcountync.gov/arcgis/rest/services/SmartGov/SmartGovTaxView/FeatureServer/0 | ALPHA | 51574 | Calc_Acres | 5765 | verified |  | carded |
| 37089 |  Henderson | 9 | https://gisweb.hendersoncountync.gov/arcgis/rest/services/Parcels/FeatureServer/0 | PIN | 71360 | CALCULATED_ACRES | 6268 | verified |  | live |
| 37091 |  Hertford | 5 | https://gis.hertfordcounty.org/server/rest/services/TaxParcels/MapServer/2 | REID | 16106 | ACREAGE | 2711 | verified |  | in_progress |
| 37093 |  Hoke | 4 | https://services1.arcgis.com/7LEXuvWjhz6cyraH/arcgis/rest/services/June2025/FeatureServer/1 | TWN_PIN | 30121 | TOTAL_ACRE | 3743 | fixed | County maps.hokecounty.org Parcels/0 (and OperationalLayers/6, Overlays/4 zoning) query fails with 400 'Bad login user' (server DB fault). Switched to county AGOL June2025/1 (data 2025-06-27). Geometry + ID + acreage only; no owner/tax. md/json/yaml updated with verifiedAt 2026-09-28. | carded |
| 37095 |  Hyde | 1 | https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Hyde_AGOL/FeatureServer/3 | REID_1 | 7794 | Assessed_Acreage | 2414 | verified |  | in_progress |
| 37099 |  Jackson | 2 | https://gis.jacksonnc.org/jcgis/rest/services/Tax_Admin/Parcels/FeatureServer/0 | PIN | 41439 | AssessedAcres (string; CAST AS FLOAT) | 6754 | verified | Acreage is a string field: CAST(AssessedAcres AS FLOAT) 5–150 = 6754. Sample needs resultRecordCount. | carded |
| 37103 |  Jones | 1 | https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Jones_Bitek/FeatureServer/0 | pin83 | 9526 | calc_acre | 2351 | verified |  | in_progress |
| 37107 |  Lenoir | 8 | https://services3.arcgis.com/bDx73HOFAO3oSeDq/arcgis/rest/services/Parcels_Zoning_Addressing/FeatureServer/6 | NC_PIN | 36474 | GIS_ACRE | 5326 | verified |  | carded |
| 37111 |  McDowell | 3 | https://www.webgis.net/arcgis/rest/services/NC/McDowell/MapServer/2 | PIN | 33500 | CALCULATED_ACREAGE | 1789 | verified |  | carded |
| 37113 |  Macon | 2 | https://gis.maconnc.org/arcgis/rest/services/JustParcels/MapServer/0 | PIN | 44701 | ACREAGE | 6332 | verified |  | carded |
| 37115 |  Madison | 2 | https://services3.arcgis.com/NwIC4HArqo0JlKGT/arcgis/rest/services/2025_Parcels/FeatureServer/19 | PIN | 21753 | CACRES | 7134 | verified |  | carded |
| 37117 |  Martin | 4 | https://gis.martincountyncgov.com/server/rest/services/TaxParcels/FeatureServer/0 | PARCEL_ID | 17048 | ACRES | 3588 | verified |  | in_progress |
| 37121 |  Mitchell | 2 | https://mapping.mitchellcountync.gov/arcgis/rest/services/WebMapNew/MapServer/12 | GISPIN | 17664 | LegalAc | 4221 | verified |  | carded |
| 37123 |  Montgomery | 5 | https://www.webgis.net/arcgis/rest/services/NC/Montgomery/MapServer/1 | PIN | 30316 | Deed_Acre | 6024 | verified |  | carded |
| 37125 |  Moore | 3 | https://gis.moorecountync.gov/server/rest/services/Tax/Tax_Layers/FeatureServer/0 | PARID | 76935 | TAX_ACRES | 12640 | verified |  | carded |
| 37131 |  Northampton | 7 | https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/NorthamptonService/FeatureServer/8 | PIN | 20561 | Acreage | 4886 | verified |  | in_progress |
| 37137 |  Pamlico | 2 | https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/Pamlico_ParcelService/FeatureServer/5 | PIN | 17106 | CALACRES | 3155 | verified |  | in_progress |
| 37139 |  Pasquotank | 3 | https://services2.arcgis.com/0sC2n3LxYOcxBOg0/arcgis/rest/services/PasquotankCountyNC_20260101/FeatureServer/0 | PARCEL_ID | 22788 | TAXACRES | 2814 | verified |  | in_progress |
| 37147 |  Pitt | 4 | https://gis.pittcountync.gov/gis/rest/services/PittOpenData/CadastralPitt/MapServer/0 | PARCELNUMBER | 81372 | CalculatedAcres | 7919 | verified |  | carded |
| 37149 |  Polk | 2 | https://services1.arcgis.com/23uf7jKvz6SRPFWJ/arcgis/rest/services/Parcels/FeatureServer/0 | TMS | 17413 | TOTAL_CALCULATED_ACRES | 4702 | verified |  | carded |
| 37153 |  Richmond | 7 | https://gis.richmondnc.com/server/rest/services/GISWebsite/ParcelViewer/MapServer/12 | PIN | 32662 | CalculatedAcres | 5403 | verified |  | carded |
| 37155 |  Robeson | 31 | https://services7.arcgis.com/miWUVbMhSUq6a8y1/arcgis/rest/services/Robeson_County_Parcels/FeatureServer/0 | PIN_NUMBER | 76928 | MAPACRE | 14307 | verified |  | carded |
| 37161 |  Rutherford | 12 | https://gis.rutherfordcountync.gov/server/rest/services/Addressing/MapServer/2 | PIN | 57442 | Acreage | 11199 | verified |  | carded |
| 37165 |  Scotland | 7 | https://services3.arcgis.com/bgKigTDifCMNj8OU/arcgis/rest/services/Tax_Parcels_Scotland_County_view/FeatureServer/6 | PIN | 22020 | ACRES | 3361 | verified |  | carded |
| 37173 |  Swain | 2 | https://maps.swaincountync.gov/server/rest/services/OperationalLayers/MapServer/4 | PARCEL_ID | 12704 | LegalLandUnits (string; CAST AS FLOAT, LegalLandType=AC) | 2521 | verified | PIN is null everywhere, so use PARCEL_ID (the card md/yaml already say so; the JSON layer has no fieldMap). The acreage field is a string and needs CAST. Numeric alternate: AGOL Swain_County_Parcels/0 Acreage (13,551; 5–150 = 2906). | in_progress |
| 37175 |  Transylvania | 2 | https://gis.transylvaniacounty.org/server/rest/services/Parcels/FeatureServer/2 | PIN | 31781 | ACRES | 5188 | verified |  | carded |
| 37177 |  Tyrrell | 1 | https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/TyrrellService/FeatureServer/7 | pin | 4378 | ACRESPARCEL | 1164 | verified |  | in_progress |
| 37187 |  Washington | 3 | https://services6.arcgis.com/hBMRLv0wWV0IhJ8I/arcgis/rest/services/Washington_Service/FeatureServer/9 | NCPin | 12630 | CalculatedAcres | 1800 | verified |  | in_progress |
| 37189 |  Watauga | 4 | https://gissvr.watgov.org/arcgis/rest/services/TaxParcels/parcelsdbf/FeatureServer/0 | PIN | 47364 | TX_ACREAGE | 7413 | verified |  | carded |
| 37193 |  Wilkes | 9 | https://gis.wilkescounty.net/arcgis/rest/services/Parcels/MapServer/0 | PARCEL_ID | 52720 | TOTALACRES | 14800 | verified |  | carded |
