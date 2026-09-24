# Valdosta, Macon, Athens, Hilton Head, and Jackson MS

Parcel shelves for five metros. Acreage is **5.0–150.0 inclusive**. No Opportunity Zone designation, school letter grade, or base flood elevation is stored. Tract income is ACS 5-year 2020–2024 B19013, the same query-time join as the other live markets. Centroid fallback polygons were added for these counties. State DOT AADT from the priority-county layer applies in Lowndes, Bibb, Beaufort, Hinds, Madison, and Rankin. Clarke, Copiah, Simpson, Warren, and Yazoo have no verified count layer. Florida FDOT segments are not copied onto these parcels.

Mississippi layers are `https://gis.cmpdd.org/...`. `gis3.cmpdd.org` and `portal.cmpdd.org` are not used. The CMPDD certificate is a leaf-only GoDaddy chain; `scripts/certs/godaddy-g2.pem` is the public intermediate that completes it.

## In this pull

| Market | County | FIPS | Parcel source |
| --- | --- | --- | --- |
| Valdosta | Lowndes, GA | 13185 | VALOR `TaxOffice/TaxParcels` FeatureServer/0 (`TOTALACRES`) |
| Macon | Bibb, GA | 13021 | Macon-Bibb `ParcelCAMA_Current_2025` (`TOTALACRES_1`) |
| Athens | Clarke, GA | 13059 | Athens-Clarke `ACC_Parcels` FeatureServer/0 (`ACRES`) |
| Hilton Head | Beaufort, SC | 45013 | Beaufort EnerGov MapServer/1 (`GisFile_Acres`, cast from text) |
| Jackson MS | Rankin | 28121 | CMPDD `Rankin_County_Feature_Layer` FeatureServer/8 |
| Jackson MS | Madison, MS | 28089 | CMPDD `Madison_County_Map` FeatureServer/36 |
| Jackson MS | Hinds | 28049 | MARIS `MS_Parcels_August_2024` MapServer/1, `STCNTYFIPS='28049'` |
| Jackson MS | Copiah | 28029 | CMPDD `Copiah_County_Feature_Layer` FeatureServer/3 |
| Jackson MS | Simpson | 28127 | CMPDD `Simpson_County_Feature_Layer` FeatureServer/3 |
| Jackson MS | Warren | 28149 | CMPDD `Warren_County_Feature_Layer` FeatureServer/4 |
| Jackson MS | Yazoo | 28163 | CMPDD `Yazoo_County_2026_layers` FeatureServer/2 |

Beaufort also remains on the Savannah shelf. It was a polygon gap there. Jackson, Tennessee is a different market.

## Zoning and future land use

**Lowndes.** Zoning is VALOR `Zoning_Detailed` `ZOTXT`. Parcel `ZONINGCODE` remains only where that polygon misses. Future land use is Greater Lowndes `character_areas` (about a 2006 map; the 2021 plan and draft 2026 update may supersede it). Valdosta, Hahira, Lake Park, Dasher, and Remerton do not have their own zoning FeatureServers. Lake Park, Dasher, and Remerton are partial. Mailing city is not a city filter. Mailing ZIP and assessed `MAV*` values are empty on the REST layer. On-parcel sales are thin, and the sales year layers stop at 2021.

**Bibb.** Consolidated Macon-Bibb. Zoning is `ZoningDistrictsNew` `ZONECLASS`. Future land use is `MATS_Future_LandUse_2050`. There is no assessed value on the WinGAP extract. Sale prices of 0, 1, and 100 are dropped. `gis.maconbibb.us` was down and was not used. This is not Bibb County, Alabama, and not Macon County, Georgia.

**Clarke.** Zoning is `PlanningViewer2025` FeatureServer/14 `CurrentZn`. Future land use is FeatureServer/41 `Updated_FL`. Winterville and Bogart city limits clear those ACC values; they are not the cities' zoning. Tax values are not on the parcel REST (`qPublic` App=ClarkeCountyGA / AppID 630). Sales are `Parcel_Sales_2018` only. This is not Clarke County, Virginia or Alabama, and not Athens, Ohio or Texas.

**Beaufort.** County zoning is `Zoning/MapServer/9` `FBCode` where the centroid hits that unincorporated layer. Hilton Head `NEW_ZONE` replaces it inside the town. Bluffton zoning and future land use come from `AddressParcels` where `jurisdiction='Bluffton'`. County future land use is `BC_FLU`. City of Beaufort and Port Royal have no public zoning REST; nothing was invented for them. Hilton Head current-land-use inventory was not stored as future land use.

**Rankin.** County zoning `zoning2025` and future land use `fulu2025`. Brandon replaces both on a parcel match. Flowood zoning (December 2025) replaces the county code; the Flowood draft land use was not joined. Pearl future land use (`fulu2026`) replaces the county future land use; Pearl has no city zoning layer, so county zoning stays. Ridgeland has no verified zoning REST.

**Madison, Mississippi.** County `zone_2025` and `fulu`. Not Madison County, Tennessee. Gluckstadt's December 2021 zoning layer was not joined. The City of Madison viewer has land use and no zoning layer on this pass. Ridgeland zoning was not found.

**Hinds.** No county zoning or future land use. Unincorporated parcels stay unzoned. City of Jackson `zoneclass` joins on `dpin = PARNO`. Jackson `exlu2019` is existing land use and is not stored as future land use. Clinton `zoning2017` replaces Jackson when both ids match a Clinton parcel. Clinton's land-use plan was not field-mapped and was not joined. Byram zoning was not found. MARIS mail and deed fields are empty; owner, situs, and total value come from the state fabric.

**Copiah.** Parcels only. Zoning and future land use are gaps.

**Simpson.** Future land use is `fulu_2023`. County zoning is a gap. Magee, Mendenhall, and D'Lo layers date from 2008–2010 and were not joined as current zoning.

**Warren.** Future land use is FeatureServer/7 `fulu`, joined by centroid. The field is an integer; stored labels are the layer renderer's published classes (0 is Agricultural/Vacant, not a missing value). County zoning is a gap. The parcel zoning attribute was not copied.

**Yazoo.** County `zoning_2026` and `fulu_2026`. Yazoo City zoning, future land use, and `salepric` replace the county values on a match.

## Deferred

Holmes County and Scott County were deferred on the research pass (Warren was preferred over them for the outer list). No polygons were added.

Gluckstadt, Ridgeland, and Byram are not joined. City of Beaufort and Port Royal zoning stay empty. Clarke County was included with Lowndes and Bibb; Winterville and Bogart are documented above rather than dropped.
