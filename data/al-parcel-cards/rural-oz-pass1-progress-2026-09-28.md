# AL rural OZ 2.0 — parcel pass 1 progress (2026-09-28)

List: SWITCHED 13:29 ET to LSB statewide appendix CSV /workspace/coverage/rural-oz-priority-counties-statewide-appendix-2026-09-28.csv (AL rows; order = no-card gaps first, then carded gap/partial, then usable). Provisional list kept at rural-oz2-candidate-counties-2026-09-28.csv (superseded). Rows above the switch were done under provisional order.
Scope: top 20.

| # | fips | county | status | parcel URL |
|---|---|---|---|---|
| 5 | 01121 | Talladega | usable (re-verified, 57181) | https://web5.kcsgis.com/kcsgis/rest/services/Talladega911/Public/MapServer/7 |
| 8 | 01083 | Limestone | usable (re-verified, 40139) | https://gis.limestonecounty-al.gov/arcgis/rest/services/Limestone_Parcels/MapServer/1 |
| 9 | 01071 | Jackson | usable (re-verified, 44933) | https://web3.kcsgis.com/kcsgis/rest/services/Jackson/Public_ISV_Jackson/MapServer/1 |
| 16 | 01095 | Marshall | usable (re-verified, 66601) | https://web5.kcsgis.com/kcsgis/rest/services/Marshall/Public/MapServer/37 |
| 3 | 01049 | DeKalb | usable (NEW card, 52861) | https://al28portal.kcsgis.com/al28server/rest/services/Dekalb_Public_ISV/MapServer/48 |
| 4 | 01055 | Etowah | usable (NEW card, 75665) | https://web3.kcsgis.com/kcsgis/rest/services/Etowah/Etowah_Public_ISV/MapServer/91 |
| 13 | 01059 | Franklin | usable (NEW card, 23519) | https://web6.kcsgis.com/kcsgis/rest/services/Franklin/Franklin_Public_ISV/MapServer/105 |
| 14 | 01077 | Lauderdale | usable (NEW card, 55490) | https://al41portal.kcsgis.com/al41server/rest/services/Lauderdale_Public_ISV/MapServer/120 |
| 19 | 01033 | Colbert | usable (NEW card, 43311) | https://al20portal.kcsgis.com/al20server/rest/services/Internal/Colbert_Public_ISV/MapServer/43 |
| 2 | 01047 | Dallas | usable (NEW card, 29996; CaptureCAMA AGOL) | https://services8.arcgis.com/9e1lVZPGgkrztAhh/ArcGIS/rest/services/Dallas_ParcelViewer_Service/FeatureServer/2 |
| 1 | 01015 | Calhoun | usable (NEW card, 75424) | https://gis.calhouncounty.org/arcgis/rest/services/Parcel_Viewer_IPV/MapServer/106 |
| 5 | 01087 | Macon | partial (NEW card, 20282; geom+PARCELID+CALC_ACRE, no owner) | https://gis.capturecama.com/arcgis/rest/services/MaconAL/MaconCapture/MapServer/1 |
| 6 | 01005 | Barbour | partial (NEW card, 25303; geom+PARCELID+CALC_ACRE, no owner) | https://gis.capturecama.com/arcgis/rest/services/BarbourAL/BarbourCapture/MapServer/213 |
| 7 | 01031 | Coffee | gap (NEW card; Flagship only) | — |
| 8 | 01039 | Covington | gap (NEW card; Flagship only) | — |
| 11 | 01013 | Butler | gap (NEW card; Flagship only) | — |
| 12 | 01017 | Chambers | gap (NEW card; Flagship only) | — |
| 14 | 01045 | Dale | gap (NEW card; Flagship only) | — |
| 15 | 01093 | Marion | gap (NEW card; Flagship only) | — |
| 16 | 01099 | Monroe | partial (NEW card, 27018; geom+PARCELID+CALC_ACRE; dated snapshot) | https://maps.capturecama.com/arcgis/rest/services/Monroe/Monroe12092025/MapServer/84 |
| 17 | 01011 | Bullock | usable (NEW card, 10689; owner/value) | https://gis.capturecama.com/arcgis/rest/services/BullockAL/BullockCapture/MapServer/3 |

## Stopped cleanly at 21 counties (2026-09-28 ~1:36 PM ET). Remaining no-card: Pike, Sumter, Tallapoosa, Wilcox, Fayette, Randolph, Winston, Cherokee, Clay, Crenshaw, Geneva, Henry, Lamar, Lawrence, Coosa. Carded gaps not re-chased: Walker, Escambia, Marengo, Clarke, Bibb, Conecuh, Greene, Hale, Lowndes, Perry, Pickens, Choctaw, Chilton, Washington.
### Leads found for next pass (not yet carded)
- Sumter: maps.capturecama.com/.../Sumter/Sumter03282024/MapServer/2 (PARCEL 16242, OWNER/CALC_ACRE/DEED_ACRE)
- Wilcox: maps.capturecama.com/.../Wilcox/Wilcox_03122025/MapServer/10 (PARCEL 16604, OWNER/CALC_ACRE)
- Coosa: maps.capturecama.com/.../Coosa/Coosa03122026/MapServer/171 (Parcel 16294, PARCELID/CALC_ACRE)
- Henry: maps.capturecama.com/.../Henry/Henry05042023/MapServer/0 (Parcels 21876, NAME/values/SALEPRICE; 2023 vintage)
- Hale (carded gap): maps.capturecama.com/.../Hale/HALE_11132024/MapServer/921 (Parcel 16288)
- Winston: web3.kcsgis.com/kcsgis/rest/services/Winston/Winston_Public_ISV/MapServer/141
- Lawrence: web6.kcsgis.com/kcsgis/rest/services/Lawrence/Lawrence_Public_ISV/MapServer/49
- Cherokee: web3.kcsgis.com/kcsgis/rest/services/Cherokee/Public/MapServer/116 (deep link cherokeeproperty.countygovservices.com)
- Russell (not rural-OZ): maps.capturecama.com/.../Russell/Russell_02122026/MapServer/133
- REJECT: services6.arcgis.com/VUsVQlvugJlIRS3I/.../Alabama_Parcel_Data (PowerSouth; Regrid LL_* schema = paid vendor derived)

## BATCH 2 (started 1:36 PM ET 2026-09-28)
| # | fips | county | status | parcel URL |
|---|---|---|---|---|
| B2-1 | 01119 | Sumter | partial (NEW, 16242; geom+PARCEL_NUM only, no pagination) | https://maps.capturecama.com/arcgis/rest/services/Sumter/Sumter03282024/MapServer/2 |
| B2-2 | 01131 | Wilcox | partial (NEW, 16604; geom+PARCEL_NUM, acreage sparse) | https://maps.capturecama.com/arcgis/rest/services/Wilcox/Wilcox_03122025/MapServer/10 |
| B2-3 | 01037 | Coosa | partial (NEW, 16294; geom+PARCELID+CALC_ACRE) | https://maps.capturecama.com/arcgis/rest/services/Coosa/Coosa03122026/MapServer/171 |
| B2-4 | 01067 | Henry | usable (NEW, 21876; owner/value, 2023 vintage) | https://maps.capturecama.com/arcgis/rest/services/Henry/Henry05042023/MapServer/0 |
| B2-5 | 01133 | Winston | usable (NEW, 31471) | https://web3.kcsgis.com/kcsgis/rest/services/Winston/Winston_Public_ISV/MapServer/141 |
| B2-6 | 01079 | Lawrence | usable (NEW, 25136) | https://web6.kcsgis.com/kcsgis/rest/services/Lawrence/Lawrence_Public_ISV/MapServer/49 |
| B2-7 | 01019 | Cherokee | usable (NEW, 35748) | https://web3.kcsgis.com/kcsgis/rest/services/Cherokee/Public/MapServer/116 |
| B2-8 | 01065 | Hale | usable (conflict settled; INDEX row was stale; 16418) | https://services9.arcgis.com/AhiZvN2uMZkZVfSu/arcgis/rest/services/Hale_Web_Service/FeatureServer/10 |
| B2-9 | 01063 | Greene | gap → usable (AGD AGOL, 11053) | https://services8.arcgis.com/XI1FxP9uZwSBSNV8/arcgis/rest/services/GreeneAL_Service/FeatureServer/5 |
| B2-10 | 01109 | Pike | gap (NEW; Flagship only) | — |
| B2-11 | 01123 | Tallapoosa | gap (NEW; Flagship only) | — |
| B2-12 | 01057 | Fayette | gap (NEW; Flagship only) | — |
| B2-13 | 01111 | Randolph | gap (NEW; KCS ISV link 404) | — |
| B2-14 | 01027 | Clay | gap (NEW; Flagship only) | — |
| B2-15 | 01041 | Crenshaw | gap (NEW; Flagship only) | — |
| B2-16 | 01061 | Geneva | gap (NEW; Flagship only) | — |
| B2-17 | 01075 | Lamar | gap (NEW; Flagship only) | — |
| B2-18 | 01127 | Walker | gap (re-chased; still Flagship; AGOL Walker AL token-gated, Walker GA trap) | — |
| B2-19 | 01053 | Escambia | gap (re-chased; still Flagship; Jacobs PFAS subset not a source) | — |
| B2-20 | 01091 | Marengo | gap (re-chased; still Flagship) | — |

## Batch 2 stopped cleanly at 20 counties (~1:41 PM ET). Remaining carded gaps not re-chased: Clarke, Bibb, Conecuh, Lowndes, Perry, Pickens, Choctaw, Chilton, Washington.
- Conecuh lead checked: AGOL 'Conecuh Al Parcels for Public Map' (Jacobs) = 580-parcel PFAS sampling subset with contact fields — not usable.
- Pickens: ADOR links taxes.pickensalabama.com (not yet examined) + Flagship.

## BATCH 3 (started 1:45 PM ET 2026-09-28)
- YAML fix: 6 city cards quoted (backups in pass1-tmp/yaml-backup-2026-09-28/); all 85 cards/AL files pass yaml.safe_load.
| # | fips | county | status | parcel URL |
|---|---|---|---|---|
| B3-1 | 01111 | Randolph | gap confirmed (Flagship; KCS link stale; no al56 portal) | — |
| B3-2 | 01025 | Clarke | gap confirmed (Flagship) | — |
| B3-3 | 01007 | Bibb | gap confirmed (Flagship; WARC org no parcels) | — |
| B3-4 | 01035 | Conecuh | gap confirmed (Flagship; Jacobs PFAS subset rejected) | — |
| B3-5 | 01085 | Lowndes | gap confirmed (Flagship) | — |
| B3-6 | 01105 | Perry | gap confirmed (Flagship) | — |
| B3-7 | 01107 | Pickens | gap confirmed (Flagship; tax site = Catalis payment portal) | — |
| B3-8 | 01023 | Choctaw | gap confirmed (Flagship) | — |
| B3-9 | 01021 | Chilton | gap confirmed (Flagship; KCS web3 has only ChiltonWaterAuthority utility service, no parcels) | — |
| B3-10 | 01129 | Washington | gap confirmed (Flagship) | — |
| B3-11 | 01027 | Clay | gap (addendum: NSGIC-listed AGOL app deleted/private) | — |
| B3-12 | 11 LSB-live usable counties | Baldwin, Blount, Cullman, St. Clair, Elmore, Madison, Mobile, Morgan, Autauga, Jefferson, Shelby | usable re-verified (counts in cards) | see cards |
| B3-13 | 01101 | Montgomery | usable (NOT re-verified: TLS EOF from box) | https://gis.montgomeryal.gov/server/rest/services/Parcels/FeatureServer/0 |

## PASS 1 COMPLETE (1:47 PM ET): 62 AL rural-OZ counties — usable 30, partial 6, gap 26 (all gaps Flagship-only; no public parcel REST).
