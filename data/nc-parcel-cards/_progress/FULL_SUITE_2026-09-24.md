# NC full-suite progress — 2026-09-24

**Ask:** Full suite for entire NC (100 counties): parcels + zoning/FLU + PA. Skip utilities + AADT. Cards → Land Search Builder only.

## Already complete (21)
Charlotte 8, RDU 3, Winston-Salem 5, Wilmington 3, Asheville 2 — see INDEX.md

## Footprint gaps first (24) — parcels already live in product
Queue order (metro weight):
1. Guilford (Greensboro)
2. Johnston, Harnett, Alamance, ~~Chatham~~, Franklin, Granville, Person, Lee, Nash, Vance, Warren, Wayne, Wilson, Sampson (RDU shed)
3. Catawba, Cleveland, Stanly (Charlotte shed)
4. Randolph, Rockingham, ~~Surry~~ (WS shed)
5. Onslow, Columbus, Duplin (Wilmington shed)

## Outside footprint (55)
Footprint closed 2026-09-24. Batch A: Cumberland, Moore, Pitt, Robeson.

## Status
- in_flight: see todos / executor batches

## Coordination
- Patterns: `/workspace/gis-research/enrichment/_patterns/full-suite-cross-state-2026-09-24.md` (PIR)
- Batch A in flight (2026-09-24 ~12:40 ET): Guilford, Johnston, Catawba, Alamance

## Completed this pass
- **37171 Surry** (Winston-Salem) — InternalUse/SurryLayers CAMA+sale; cities-first Mount Airy/Elkin/Dobson/Pilot zoning; coarse FLU+DobsonLandUse; AppraisalCard `{Parcel}` — cards written 2026-09-24
- **37037 Chatham** (Raleigh-Durham) — LandReference/CamaParcels + PropertySales + cities-first Pittsboro/Siler/Goldston zoning/FLU + NCPTS {parcel_number} — cards written 2026-09-24
- **37191 Wayne** (RDU) — AGOL TaxParcels + city-first zoning + Goldsboro FLU + ITSPublic/NCPTS PA — cards written 2026-09-24
- **37145 Person** (Raleigh-Durham) — BitekParcelInfo CAMA + PlanZone Roxboro/county zoning + FLUM + NCPTS/BT PA — cards written 2026-09-24
- **37167 Stanly** (Charlotte) — parcel_records_base_2 + Zoning Jurisdiction2 + FLUM/20 + stanlytax PA — cards written 2026-09-24

## Tranche-3 (2026-09-24 ~12:50 ET)
Every card must include: tax/sale/owner where public; PA deep-link with parcel-ID placeholder; jurisdiction public GIS URL. Cards → LSB only.

- **37127 Nash** (RDU) — PUBLIC/Parcels CAMA + Avineon city-first zoning + LDP2022 FLU + taxdata {TAX_PARID} — cards written 2026-09-24
- **37151 Randolph** (Winston-Salem) — ParcelQuery CAMA + Zoning/31 JURISDICTION cities-first + GMA/33 FLU + CAMA {REID}/{PARCEL_PK}; sale price REST gap — cards written 2026-09-24
- **37195 Wilson** (RDU) — Taxparcels CAMA + city/town zoning + FLU 2043/2045 + DevNet OwnerID PA — cards written 2026-09-24

- **37157 Rockingham** (Winston-Salem) — Tax_gdb Expanded CAMA + Reidsville city-first zoning + Land_Classification FLU proxy + PropertyCard/ustaxdata {ParcelNumber} — cards written 2026-09-24

- **37047 Columbus** (Wilmington) — OneMap cntyfips='047' + taxdata CAMA join; MangoMap cities-first zoning; PRC pid{GSEQ}; FLU CLUP PDF gap — cards written 2026-09-24

## Milestone — footprint 45/45 complete (2026-09-24 ~1:11 PM ET)
Duplin 37061 closed the footprint queue. **45 unique FIPS** carded under cards/NC/.

### Outside-footprint Batch A (started)
~~Cumberland 37051~~, ~~Moore 37125~~, ~~Pitt 37147~~, ~~Robeson 37155~~ — then continue remaining 51.

## Outside-footprint Batch A — progress
- **37051 Cumberland** (Fayetteville) — Tax/Parcels CAMA+sale+owner; cities-first Fayetteville CCZoning/0 + town Jurisdiction zoning; CCFutureLandUse2025 FLU; camapwa PropertySummary `{REID}`/`{PARCEL_PK}` + NCPTS `{PIN}`; DataViewer GIS — cards written 2026-09-24
- **37125 Moore** (Fayetteville / Southern Pines) — Tax/Tax_Layers CAMA+sale+owner; cities-first Planning_Intranet City Zoning JR (SP/PH/AB/CG/WP/…); county FLU Class; Pinehurst Official Zoning AGOL; AppraisalCard `{PARID}` + NCPTS; OpenData token gap — cards written 2026-09-24

- **37155 Robeson** (Fayetteville) — AGOL Robeson_County_Parcels CAMA (owner/tax/acres/DATESOLD); ROKMAPS cities-first ZONE_CODE (Lmbr/Pmbr/Rdsp/Frmt/…); OneMap cntyfips='155'; ustaxdata account.cfm?parcelID={MAPNO}; FLU Comprehensive Plan PDF gap; sale price REST gap — cards written 2026-09-24
- **37147 Pitt** (Greenville) — CadastralPitt CAMA+sale/owner/tax; cities-first Greenville/Winterville/Ayden/Farmville(+towns) zoning; Greenville+county FLU; NCPTS `{PARCELNUMBER}`/`{REID}` + OPIS — cards written 2026-09-24

- **37027 Caldwell** (Hickory) — NCOnemap/NCOneMap FS/45 CAMA (owner/tax/acres/ZoningInfo); cities-first WarehouseServices/Zoning (Lenoir/Hudson/Granite Falls/Gamewell/…); County Zoning; Hickory city FLU; Comp Plan + Living Lenoir 2045 PDF; AppraisalCard `{PID}` + viewer `?pid={NCPIN}` + NCPTS `{NCPIN}`; OneMap cntyfips='027'; sale price REST gap; Rhodhiss zoning miswired — cards written 2026-09-24

- **37023 Burke** (Hickory / Asheville shed) — ProdParcelViewFC CAMA+sale+owner; cities-first Morganton native + PublicAccessAux Valdese/Hildebran/Drexel/… + Hickory city; FLU/19 F_LU; CamaPWA PropertySummary `{REID}`/`{PARCEL_PK}` (HTTP) + GIS `default.htm?PIN=` + NCPTS `{PIN}`; OneMap cntyfips='023' — cards written 2026-09-24

- **37189 Watauga** (Boone / Asheville shed) — TaxParcels/parcelsdbf CAMA+sale+owner; cities-first Boone Zoning_Mobile/Boone_Zoning + BR/BM/SD parcel ZONE prefixes + Foscoe FC corridor; FLU Comp Plan PDF gap; Datalet `{PID}` taxyr=2026 + NCPTS `{PIN}` + GIS gissvr.watgov.org/maps/; OneMap cntyfips='189' — cards written 2026-09-24

- **37087 Haywood** (Asheville) — SmartGovTaxView FS/0 CAMA+sale+owner (~53.2k); Open_Data Parcels/3 mirror; cities-first Open_Data Zoning/9 MAPNAME (Waynesville/Maggie/Canton/Clyde); unincorp unzoned; Waynesville FLU PDF; AppraisalCard `{ALPHA_NO_DASHES}` + Spatialest `#/property/{ALPHA}` + NCPTS `{ALPHA}`; gisweb Jurisdiction GIS; OneMap cntyfips='087' — cards written 2026-09-24
- **37065 Edgecombe** (Rocky Mount / RDU shed) — webmap/10 CAMA+sale/owner/tax; cities-first Tarboro/RM-tip/Sharpsburg/Leggett/Pinetops/Princeville/Macclesfield/Conetoe zoning; county Zoning/23; FLU UA/UB gap; Keystone PA `pKEY={linkpin}` + map `?PIN={linkpin}` + NCPTS `{parcel}`; OneMap cntyfips='065' — cards written 2026-09-24

- **37049 Craven** (New Bern/Eastern NC) — JustParcels CAMA+SALE_PRICE+owner/tax; OneMap cntyfips='049' saledate; cities-first New Bern Zoning FS + Havelock Planning/5; FLU PDF gap; map.htm?pid={PID} + NCPTS `{PID}` + ITSPublicCRRP/CR — cards written 2026-09-24

- **37083 Halifax** (Rocky Mount / RDU shed) — OpenGov_RR_Layers/22 Halifax_County_Parcels CAMA+sale+owner (~39.4k; ACREAGE 5–150 → 6461); cities-first Roanoke_Rapids_Zoning2_(2)/0 ZONE (~9083) + overlays; OneMap cntyfips='083'; NCPTS `{PARID}` + qPublic AppID=872 `KeyValue={PARID}`; jurisdiction qPublic map; county Official Zoning Map + FLU Comp Plan PDF REST gaps; Weldon/Enfield/Scotland Neck/… zoning REST gaps — cards written 2026-09-24

- **37107 Lenoir** (Greenville/Eastern NC) — Parcels_Zoning_Addressing/6 + OpenGov/2 CAMA+sale/owner/tax; cities-first Kinston/Pink Hill zoning; Pink Hill Future_LU; County_Zoning coarse + Proposed_Z; La Grange PDF gap; Spatialest `{Record_Num}` + NCPTS `{NC_PIN}`; OneMap cntyfips='107' — cards written 2026-09-24

- **37031 Carteret** (Crystal Coast / Eastern NC) — Layers/Parceldata CAMA+sale+owner/tax (~64.3k; GISacres 5–150 → 3466); cities-first Morehead City AGOL Zoning/FLU + county Newport/Emerald_Isle zoning + county Zoning; Beaufort+beach towns zoning REST gap; CAMA LUP FLU PDF; AppraisalCard/BasicSearch `{PIN15}` + NCPTS `{PIN15}`; jurisdictionGis `arcgisweb.carteretcountync.gov/maps/`; OneMap cntyfips='031' — cards written 2026-09-24

- **37161 Rutherford** (Asheville / Charlotte shed) — Addressing/2 CAMA+sale+owner (~57.4k; Acreage 5–150 → 11199; Sale_Price>0 → 28893); EnerGov FS/3 twin; Possible Sales/3; cities-first NewLayers/22 ZONE_CODE (Forest City+ETJ / Rutherfordton / Spindale / Lake Lure); unincorp unzoned; FLU Comp Plan PDF gap; NCPTS `REID={Parcel_Number}` + GIS `default.htm?pin={Parcel_Number}`; OneMap cntyfips='161' — cards written 2026-09-24

- **37193 Wilkes** (Winston-Salem shed) — Parcels/0 CAMA+SALEPRICE+owner/tax; cities-first Wilkesboro/NW WebMap zoning; County Zones; FLU Growth Plan+WB/NW PDF gap; Datalet `{PARCEL_ID}` + viewer `?PARCEL_ID=`/`?PIN=` + NCPTS; OneMap cntyfips='193'; CRS 32019 NAD27; Elkin/Ronda zoning gap; PIN↔parno remap — cards written 2026-09-24

- **37013 Beaufort** (Washington / Eastern NC) — Beaufort_Service/4 CAMA+SALE_PRICE+owner/tax (~45.2k; CalcAcres 5–150 → 8050); OneMap cntyfips='013' (saledate null — use DATE/date_dt / saledatetx); cities-first Washington Static/16 Zoning (556) + Belhaven Static/28 (11); FLU Washington 2024 Comp/CAMA LUP+FLU Map PDF gap; NCPTS `parcel-detail?reid={REID}` + AGD print `?GPIN={GPIN}` + webappviewer jurisdiction GIS; Aurora/Bath/Chocowinity/Pantego/WPark + unincorp zoning REST gaps — cards written 2026-09-24

- **37111 McDowell** (Asheville) — WebGIS `NC/McDowell/MapServer/2` CAMA+owner/tax+sale date (~33.5k; Shape acres 5–150 → 5638; SalePrice REST gap); cities-first Marion OfficialZoningDistricts/0 (~168) + Current_Zoning_WFL1 PIN join; County Zoning/236 limited (~669); Old Fort zoning REST gap; FLU Comp Plan PDF; AppraisalCard `{PIN}` + NCPTS `{PIN}`; jurisdictionGis webgis.net/nc/McDowell/; OneMap cntyfips='111' — cards written 2026-09-24

- **37055 Dare** (Outer Banks / Eastern NC) — AGOL gis_polygons CAMA+owner/tax/zoning attr (~47.9k; calcacre 5–150 → 2222); sales_layer/points WFS join (tasaleprice/sl1price); cities-first KDH/Nags Head/Manteo/Kitty Hawk/Duck/Southern Shores WFS zoning + countyzones; FLU CAMA LUP PDF/edocs gap; Spatialest `#/property/{parcel}` + tax landtransfer/bill + NCPTS `{parcel}`; jurisdictionGis `maps.darecountync.gov`; OneMap cntyfips='055' — cards written 2026-09-24

- **37093 Hoke** (Fayetteville) — Parcels MS/0 CAMA+COST_TOTAL+owner+deed (~29.6k; TOTAL_ACRE 5–150 → 3190); cities-first Overlays Zoning ZONE RAEFORD (~3330) + county RA-20/HC/…; Raeford City/12 gate; FLU Land Use Plan PDF gap (+ planhokecounty.com 2025 update); TaxCards `Default.aspx?Id={TWN_PIN}-` + PDF `TaxCards/{TWN_PIN}-01.pdf` + GIS `?TWN_PIN=` + NCPTS; OneMap cntyfips='093' geometry-only (CAMA empty); sale price REST gap — cards written 2026-09-24

- **37165 Scotland** (Fayetteville) — AGOL Tax_Parcels FS/6 CAMA+owner/tax/DeedDate (~22.0k; ACRES 5–150 → 3361); Parcel_Sales FS/7 date overlay (~3378, no price); cities-first Zoning_Laurinburg FS/14 (~9705) + County Zoning FS/9 (~10632); City Limits+ETJ; FLU Comp Plan PDF gap; AppraisalCard `{PIN}` space→`%20` + NCPTS `{PINID}` + TaxBillSearch; jurisdictionGis Parcel Explorer + hub; OneMap cntyfips='165' (gisacres usable); Wagram/Gibson/East Laurinburg zoning REST gaps; sale price REST gap — cards written 2026-09-24

- **37123 Montgomery** (Charlotte shed) — WebGIS `NC/Montgomery/MapServer/1` CAMA+SalesAmt+owner/tax (~30.3k; Deed_Acre 5–150 → 6024); cities-first Troy Zoning/17 (769) + Biscoe Zoning/16 (458); county Zoning/18 + PTRC Existing ETJs; Mt Gilead/Candor/Star zoning REST gap; FLU Comp LUP 2010+Mt Gilead Comp Plan PDF; PropertyCard `{PinNoDash}` + NCPTS `{PinNoDash}`; jurisdictionGis webgis.net/nc/montgomery/; OneMap cntyfips='123' — cards written 2026-09-24

- **37017 Bladen** (Fayetteville / Wilmington shed) — BladenCounty TaxParcels MS/1 CAMA+SalesAmoun+owner/tax (~33.3k; MapAcres 5–150 → 9242); cities-first MunicipalBoundaries (Elizabethtown/Bladenboro/White Lake/Clarkton/East Arcadia/Dublin/Tar Heel; town zoning FS gap) + County_Zoning MS/2 RA/CON/I/C/R; FLU 2014–2030 PDF gap; ustaxdata `ownerID={OwnerId:07d}&parcelID={ParcelId:07d}&groupParcel={PIN}` + bladenmap `?PIN=`; OneMap cntyfips='017' (gisacres broken); calcacre broken — cards written 2026-09-24

- **37197 Yadkin** (Winston-Salem) — CountyGISmap/1 CAMA+SALES_AMT+owner/tax (~28.4k; TOTAL_ACRES 5–150 → 8175); cities-first Yadkinville/44 + Jonesville/43 + Boonville/41 + East Bend/42 + County Zoning/40; FLU Comp Plan+FLUM PDF gap (Land Use/38 cropland≠FLU); AppraisalCard `{PARCEL_NO}` + NCPTS `{PIN}` + jurisdictionGis `gis.yadkincountync.gov`; OneMap cntyfips='197' (saledate 0) — cards written 2026-09-24

- **37153 Richmond** (Fayetteville / Charlotte shed) — GISWebsite/ParcelViewer/12 CAMA+SaleDate+owner/tax (~32.7k; CalculatedAcres 5–150 → 5403); County Zoning/14 (69; A-R/C-C/C-R/H-C/H-I/L-I/R-R/V-R); cities-first intent Rockingham/Hamlet/Ellerbe/Hoffman/Norman/Dobbins Heights zoning REST gap (City Limits+ETJ routing); FLU Strategic Land Use Plan 2022 PDF; AppraisalCard `{PIN}` + TaxBillSearch/Parcel/{PIN}; jurisdictionGis `gis.richmondnc.com/maps/`; OneMap cntyfips='153'; sale price REST gap; NCPTS richmond tenant invalid; legacy gis3 TLS fragile — cards written 2026-09-24

- **37003 Alexander** (Hickory) — Website_map/26 Parcels CAMA+SALES_PRICE+owner/tax (~27.0k; CALCULATED_ACREAGE 5–150 → 7303; SALES_PRICE>0 → 6411); cities-first Taylorsville Downtown/Biz Corridor overlays + ProposedZoning; FLU_Classification (USA/RTA/RAA/IND) + Overlay/30 FLU (skewed); PRC `{PARCELID}` + viewer `?pin=` + NCPTS `{PIN}`; OneMap cntyfips='003'; CDPs Bethlehem/Hiddenite/Stony Point unincorporated — cards written 2026-09-24

- **37175 Transylvania** (Asheville) — Parcels FS/2 CAMA+SALE_PRICE+owner/tax (~31.8k; ACRES 5–150 → 5188; SALE_PRICE>0 → 11666); cities-first Brevard AGOL Zoning_Districts/200 (~129) + FutureLandUse_CLUP2030/800 (~79); Pisgah_Forest_Zoning OpenUse/CorridorMixedUse (329/99); Rosman limits-only zoning REST gap; unincorp mostly unzoned; NCPTS `{PIN}` + RealEstateSearch (AppraisalCard idP-only); jurisdictionGis Tax & Land Records webappviewer + Hub; OneMap cntyfips='175' — cards written 2026-09-24

- **37009 Ashe** (Boone / Asheville shed) — OpenData/TaxParcel/0 CAMA+SalePrice+owner/tax (~38.8k; TotalCalculatedAcres 5–150 → 9061; SalePrice>0 → 18077 / in-range 3505); Web_Map_2026/16 twin + rp_sale history (~31k); cities-first AsheED_Zoning Jefferson/0 (6) + WJ/1 (250) + WJ-ETJ/2 (1970); Lansing zoning REST gap; unincorp unzoned REST; FLU Comp Plan 2022 PDF gap; AppraisalCard `id={ParcelNumber}` + viewer `?pin=` + NCPTS `{ParcelNumber}`; OneMap cntyfips='009' — cards written 2026-09-24

- **37113 Macon** (Asheville) — JustParcels/0 CAMA+SALES_PRICE+owner/tax (~44.7k; ACREAGE 5–150 → 6329; SALES_PRICE>0 → 25352); Sales/1 twin (~40.0k); cities-first Franklin AdditionalLayers/24 Zoning (4138) + Highlands AGOL Zoning_01_2025/31 DISTRICT (78); unincorp unzoned; FLU Comp Plan + Highlands 2022 PDF gap; AppraisalCard `{PIN}` PDF + TaxBillSearch/Parcel/{PIN} + NCPTS `{PIN}`; jurisdictionGis gis2.maconnc.org/maps/; OneMap cntyfips='113' — cards written 2026-09-24

- **37099 Jackson** (Asheville) — Tax_Admin/Parcels FS/0 CAMA+SalePrice+owner/tax (~41.4k; CAST AssessedAcres 5–150 → 6754; SalePrice>0 → 22006); Appraisal/0 MktValue+VldSale; cities-first Planning Sylva/Dillsboro/Forest Hills/Webster + Cullowhee/Cashiers/US-441; Energov Zoning/6 combined (55); FLU SAP PDF gap; PRC `{No_Dash}` + NCPTS `{PIN}`; jurisdictionGis `gis.jacksonnc.org/rpv/`; OneMap cntyfips='099' — cards written 2026-09-24

- **37115 Madison** (Asheville) — 2025_Parcels/19 CAMA+owner/zoning attr (~21.8k; CACRES 5–150 → 7134); OneMap cntyfips='115' tax (parval>0 → 19810; saledate 0); cities-first Mars_Hill_Zoning/0 (39) + Marshall_Zoning2023v2 CLASSIFICA (82) + CtyZoningWO_MH_Marsh (~20.2k); Hot Springs zoning REST gap; FLU Comp Plan+Map 3 PDF; NCPTS `PropertySummary.aspx?PARCELPK={PARCEL_PK}` / `?PIN={PIN_DASHED}` / `?REID={REID}`; jurisdictionGis Experience Builder; sale REST gap — cards written 2026-09-24

- **37149 Polk** (Asheville / Charlotte shed) — Parcels/0 CAMA+owner/tax+DEED_YEAR (~17.4k; TOTAL_CALCULATED_ACRES 5–150 → 4702); TaxParcels stale; cities-first Zoning1/53 Columbus/Tryon/Saluda (~143); PolkPublicData County Zoning twin; FLU 20/20 Vision PDF gap; PRC `http://parcels.polknc.org:8080/{TMS}.pdf` + NCPTS `{TMS}`; Experience Builder jurisdictionGis; OneMap cntyfips='149'; sale price REST gap — cards written 2026-09-24

- **37039 Cherokee** (Asheville / Western NC) — OfficeView/1 CAMA+SalePrice+owner/tax (~35.7k; TOTAL_CALCULATED_ACRES 5–150 → 6510; SalePrice>0 → 20249); AGOL Parcels mirror; cities-first MurphyNCZoning/0 (36) + AndrewsNCZoning/0 (21); unincorp unzoned; FLU ordinance/CTP PDF gap; TaxNet AppraisalCard `idP={ParcelID}` + NCPTS `{NEWPIN}`; jurisdictionGis `maps.cherokeecounty-nc.gov/GISweb/GISviewer/`; OneMap cntyfips='039'; legacy Dynamic/MurphyZoning MapServers 404 — cards written 2026-09-24

- **37199 Yancey** (Asheville) — Op2025 TaxParcels/0 CAMA+owner/tax+STAMPS (~17.4k; CALCULATED_ACREAGE 5–150 → 4555; STAMPS>0 → 7581 / in-range 1576); Op Layers/6 twin; cities-first Reference Zoning/0 Burnsville (10; C-1/C-2/C-3/I-1/R-10); unincorp unzoned; FLU Burnsville CLUP 2021 PDF gap; IAS `parcel.detail.php?id={PIN}{Card}` + NCPTS `{PIN}` + maps/?pin=; OneMap cntyfips='199' (parval/saledate empty); sale price REST gap (STAMPS proxy) — cards written 2026-09-24

- **37121 Mitchell** (Asheville) — WebMapNew/12 CAMA+owner/tax+Deed_Date (~17.7k; LegalAc 5–150 → 4221); WebMap Sales/18 partial sale_price (~397, ~2021); cities-first HCCOG Spruce_Pine_Zoning ZoneCode (244) + WebMapNew/8 Zoning_11 (242); Bakersville+unincorp unzoned (county FAQ); FLU Comp Plan page gap; NCPTS `parcel-detail/{GISPIN}` + esearch/publicaccessnow; jurisdictionGis mapping.mitchellcountync.gov/maps/; OneMap cntyfips='121' — cards written 2026-09-24

- **37011 Avery** (Boone / Asheville shed) — AGD Avery_AGOL/21 Parcels_Reval CAMA+SALEPRICE+owner/tax (~24.6k; Calculated_Acreage 5–150 → 4043; SALEPRICE>0 → 11765 / in-range 1475); /5 twin+PRC; cities-first HCCOG Banner Elk (1619) + Sugar (36) + Beech (45) + Seven Devils (1032); Newland/Crossnore/Elk Park/Linville/Grandfather Village zoning REST gaps; unincorp unzoned; FLU Land Use Update.docx 404 gap; AppraisalCard `id={PARNUM}` (PIN+00000) + AGD viewer + NCPTS `{PIN}`; OneMap cntyfips='011'; rejected mislabeled HCCOG Avery_County_Parcels (Ashe) — cards written 2026-09-24

- **37043 Clay** (Asheville / Western NC) — claynctax AGOL Parcels04162026/0 CAMA+SalePrice+owner/tax (~17.0k; LegalLandU AC 5–150 → 2907; SalePrice>0 → 9796); Clay_AGOL/5 total_calculated_acres 5–150 → 3054; Parcels_2025 CityCode=52 Hayesville (~373); cities-first Hayesville Zoning & ETJ Map PDF/JPG + Ordinances DOC (no zoning FS); FLU Hayesville CLUP 2022 PDF gap; AppraisalCard `id={ParcelNumb}` PDF + NCPTS `{ParcelNumb}`; jurisdictionGis Experience Builder `d706343410ba46c586bfb15b0ca30bdb`; OneMap cntyfips='043' (gisacres broken; recareano OK; sale empty) — cards written 2026-09-24

- **37173 Swain** (Asheville / Western NC) — OperationalLayers/4 CAMA+owner/tax (~12.7k; LegalLandUnits 5–150 → 2522); ParcelsForDownload + AGOL Swain_County_Parcels (Deed_Date, no price); cities-first Bryson City limits only (Op/5 + AGOL; no district FS; UDO in development); unincorp unzoned; FLU 1994 Land Use Plan PDF gap; AppraisalCard `{PARCEL_ID}` + viewer `?pin=` + NCPTS `{PARCEL_ID}`; OneMap cntyfips='173' (altparno; parno empty); sale price REST gap — cards written 2026-09-24

- **37005 Alleghany** (Boone / Winston-Salem shed) — WebGIS `NC/Alleghany/MapServer/11` parcels owner+deed (~14.8k; TOTAL_CALCULATED 5–150 → 3628); OneMap cntyfips='005' tax+mail/situs (parval>0 → 14591; saledate 0; no sale price); Land Classifications/26 FLU proxy (19; Urban/Developed/Transition/Rural Community); cities-first Sparta Limits/16+ETJ/17 zoning REST gap (AmLegal+LUP PDF); unincorp Open District LDP; AppraisalCard `id={PIN}` + viewer `?id=Parcels|PIN|{PIN}` + NCPTS `{PIN}`; sale price REST gap; rejected VA Alleghany_Zoning_2022 — cards written 2026-09-24

- **37075 Graham** (Asheville / Western NC) — GrahamAGOL/6 CAMA+SALEPRICE+owner/tax (~9.5k; calcacres 5–150 → 1963; SALEPRICE>0 → 4457); twins /15,/16; cities-first Lake Santeetlah zoning+LUP PDF (no FS); Robbinsville/Fontana Dam/unincorp unzoned; FLU Santeetlah LUP PDF gap; AppraisalCard `parcel={PARNUM}` + NCPTS `{pin}`; jurisdictionGis AGD webappviewer; OneMap cntyfips='075' (parno↔pin; saledatetx empty); reject Tax_View token + grahamconc canceled + REGIS City-of-Graham GrahZoning* — cards written 2026-09-24

- **37033 Caswell** (RDU / Greensboro shed) — WebGIS `NC/Caswell/MapServer/9` CAMA+owner/tax (~17.2k; AV_ACRES 5–150 → 5921); cities-first City Zoning/21 Yanceyville (125) + Milton/22 (11) + Hyco Lake/10 (16); unincorp unzoned; FLU Comp Plan+PTRC LDP PDF; AppraisalCard `id={P_PIN}` (Account) + TaxBillSearch + NCPTS; jurisdictionGis webgis.net/nc/caswell/; OneMap cntyfips='033' (parno=Account; saledate 0); sale price/date REST gap — cards written 2026-09-24

- **37139 Pasquotank** (Outer Banks / Eastern NC) — PasquotankCountyNC_20260101 CAMA+owner/tax (~22.8k; TAXACRES 5–150 → 2814; Shape_Area/gisacres → 3145); sales2025 (1201) + Sales_2024 (2146) price join on PARCEL_ID; cities-first CityZoning Elizabeth City (329) + County_Zoning_2026 (778); FLU 2023 Plan+CAMA/DEQ PDF gap; taxcard `PP2={PPN_2}` (NOT PID) + NCPTS `{PIN}` + Instant Basic GIS; OneMap cntyfips='139'; rejected zoning_toh (Hertford/Perquimans) + paid $200 parcel download — cards written 2026-09-24

- **37053 Currituck** (Outer Banks / Eastern NC) — OperationalLayers/20 CAMA+SALE_PRICE+owner/tax (~27.9k; ACREAGE_GI 5–150 → 2913; SALE_PRICE>0 → 16207); county Official Zoning Base/30 (1058) + overlays; cities-first Moyock/42 + Corolla/46 + Maple-Barco/44 SAP FLU + Imagine LUP Classes/40 (1139); no incorporated munis; NCPTS `parcel-detail/{PARCEL_ID}` + viewer `?pin={PARCEL_ID}` + Munis/ICARE; jurisdictionGis `maps.currituckcountync.gov/gis/`; OneMap cntyfips='053' (parno=PARCEL_ID) — cards written 2026-09-24

- **37117 Martin** (Greenville / Eastern NC) — TaxParcels FS/0 CAMA+SALE_PRICE+owner/tax (~17.0k; ACRES 5–150 → 3588; SALE_PRICE>0 → 6057 / in-range 971); ParcelPolygon twin; cities-first Williamston ZONING FS/5 ZONE (65; CH/O&I/M1/R*); Robersonville Zoning Map PDF; Hamilton ordinance-only + Bear Grass/Everetts/Hassell/Jamesville/Oak City/Parmele/unincorp unzoned; FLU Comp Plan 2013 + NCDOT FLU 2017 PDF gap; ITSPublicMT AppraisalCard `{PARCEL_ID}` + PropertyRecordCards/PropertyCards PDF + NCPTS `{PARCEL_ID}`; jurisdictionGis gis.martincountyncgov.com; OneMap cntyfips='117' (saledate 0; landval/improvval empty) — cards written 2026-09-24

- **37015 Bertie** (Eastern NC) — Bertie_Parcel_Viewer/4 CAMA+owner/tax+PARZONE+STAMPS (~18.8k; CALCACRE 5–150 → 4455; STAMPS>0 → 7736 / in-range 1570; no SALE_PRICE); OneMap cntyfips='015' (saledate/saledatetx empty); cities-first Windsor PARZONE districts + UDO/Zoning Map PDF (no zoning FS); other munis PARZONE stubs; unincorp unzoned; FLU County CAMA LUP+FLUM PDF gap; PRC `https://dl.agd.cc/prc/nc/bertie/{GEOPIN}.pdf` + NCPTS `?reid={GEOPIN}` + Experience/webappviewer jurisdictionGis; City Limits 8 (Windsor/Aulander/Lewiston/Roxobel/Askewville/Kelford/Powellsville/Colerain) — cards written 2026-09-24

- **37091 Hertford** (Eastern NC) — TaxParcels/2 CAMA+PKG_SALE_PRICE+owner/tax (~16.1k; ACREAGE 5–150 → 2711; PKG_SALE>0 → 5165 / in-range 305); cities-first Zoning/2 Ahoskie (340) + /5 Murfreesboro (239) + /6 Winton (103) + /3 Cofield (37) + /4 Como (5); county Zoning/1 (413); Harrellsville NO ZONING; FLU CAMA LUP 2011+Ahoskie Comp Plan PDF gap (LandUse/0 not FLU); NCPTS PropertySummary `PIN={Tax_REID}` + parcel-detail `{REID}` + Instant Sidebar jurisdictionGis; OneMap cntyfips='091' — cards written 2026-09-24

- **37131 Northampton** (Eastern NC / Rocky Mount shed) — NorthamptonService/8 CAMA+Sale_Price+owner/tax (~20.6k; Acreage 5–150 → 4886; Sale_Price>0 → 6719 / in-range 1423); cities-first Rich Square Official Zoning WFL1/4 + Zoning/0 (25; Type R-20/C-1/A-0/…) + Land_Use/0 FLU (830); Jackson/Gaston/Conway/Seaboard/Woodland/Severn/Lasker/Garysburg + county zoning/FLU REST gaps (ordinance+Comp Plan PDF); PRC `pin{PIN}.pdf` + NCPTS `{PARCELNBR}`/`{PIN}`; jurisdictionGis webapp.agdmaps.com/nc/northampton/; OneMap cntyfips='131'; rejected PA gis.northamptoncounty.org — cards written 2026-09-24

- **37073 Gates** (Eastern NC) — GatesParcelService/5 CAMA+saleprice+owner/tax (~8.0k; acres 5–150 → 2331; saleprice>0 → 2999 / in-range 877); Zoning/6 countywide (8027; A-1/R-1/…); cities-first Gatesville Towns/9 (~283 intersect; no town zoning FS); FLU Comp Plan 2017 + Gatesville LUP 2025 PDF gap; AppraisalCard `{pclnbr}` + NCPTS `{pclnbr}` + AGD print; jurisdictionGis AGD Parcel App / gatescountygis.com; OneMap cntyfips='073' (parno↔pin swap; saledate empty) — cards written 2026-09-24

- **37041 Chowan** (Eastern NC) — Chowan_Feature_Service/0 CAMA+SALE_PRICE+owner (~12.9k; ACRES 5–150 → 2153; SALE_PRICE>0 → 6581 / in-range 763; tax REST scrubbed LAND_VAL>0 → 1); cities-first Edenton_Zoning/16 (420) + County_Zoning/15 (77) + parcel ZONING_CDE; City_Limit EDENTON only; FLU 2018 Chowan–Edenton CAMA LUP PDF gap (Landuse/13 ALPHA-only rejected); AppraisalCard `id={PIN}` PDF + AGD print `?PIN=` + NCPTS `?reid={PIN}` + webappviewer/Experience jurisdictionGis; OneMap cntyfips='041' (inflated; gisacres/tax empty; recareano OK); rejected dl.agd.cc/prc/nc/chowan 404 — cards written 2026-09-24

- **37079 Greene** (Greenville / Eastern NC) — Greene_Service/4 TaxParcels CAMA+owner/tax+DEED_DATE (~12.8k; calc_acre 5–150 → 3605; ADJUSTED_SALE_PRICE 0 — sale price REST gap); cities-first Snow_Hill_Zoning/0 (101) + Hookerton Static/13 (9) + Walstonburg Static/15 (8); County_Zoning/0 (485; AR/R/C/I); TownLimits 3 munis; Maury CDP fire-only; FLU Comp Plan in-progress flyer + Snow Hill Comp Plan PDF (LandUse2016 WOOD/CLEAR ≠ FLU); AGD PRC `{prc_ppn}01.pdf` + NCPTS `{pin}` + greenecountygis.com→agdonline webappviewer; OneMap cntyfips='079'; reject Greene NY Tax Parcels + Spatialest 404 — cards written 2026-09-24

- **37103 Jones** (Eastern NC / New Bern shed) — Jones_Bitek/0 CAMA+saleprice+owner/tax (~9.5k; calc_acre 5–150 → 2351; saleprice>0 → 3707 / in-range 854); cities-first municipal/21 Trenton/Pollocksville/Maysville (zoning ordinance PDF + Town Hall maps; Trenton online gap; county unzoned); FLU LUP 2013–2033 PDF gap; AppraisalCard `{pin83}` + NCPTS `{pin83}` + AGD print `?pin83=`; jurisdictionGis AGD webappviewer + Experience; OneMap cntyfips='103'; rejected Jones_NC_Service + maps.agdmaps.com/nc/jones + Spatialest + WI Trenton_Zoning + MS Jones_Service — cards written 2026-09-24

- **37137 Pamlico** (Eastern NC) — Pamlico_ParcelService/5 CAMA+SALE_AMT+owner/tax (~17.1k; CALACRES 5–150 → 3155; SALE_AMT>0 → 7155 / in-range 979); Pamlico_Sales QS (801) + HistoricSales (3665); cities-first Oriental GMO Map+Ordinance PDF (no FS); Bayboro/Alliance/Arapahoe/Grantsboro/Mesic/Minnesott/Stonewall/Vandemere + unincorp zoning REST gaps (VolAgDist overlay only); FLU CAMA LUP 2004 + Future LU Map A/B PDF gap; PRC `http://dl.agd.cc/prc/nc/pamlico/{MAPID}.pdf` + print `?MAPID=` + NCPTS `{PIN}`; jurisdictionGis `webapp.agdmaps.com/nc/pamlico/`; OneMap cntyfips='137'; GDB+Tax CSV dl.agd.cc; rejected utilities + CO Arapahoe Zoning — cards written 2026-09-24

- **37143 Perquimans** (Outer Banks / Eastern NC) — Perquimans_Service/2 CAMA+owner/tax+DATE_SOLD (~15.1k; dacre 5–150 → 2912; TAX_VAL nonempty → 14874; no SALE_PRICE); /15 twin; cities-first Hertford Zoning Map+Use District List+Art.3 PDF (RA/R10/R8/R6/TR/C1–C6/O/1/M1; no town FS) + PERQ_ZONING/4 (108; Hertford ETJ + Winfall Town Limits carve-outs); Winfall zoning FS gap; FLU joint CAMA LUP PDF (DEQ) gap; PRC `https://www.perquimanscountync.com/search?for={parcel_id}` + NCPTS `?reid={pin}` + perquimans.agdmaps.com / webappviewer jurisdictionGis; OneMap cntyfips='143' (saledate 0; saledatetx text-only; siteadd 0); rejected dl.agd.cc/prc + AGD print 404 + Experience 268c… (statewide OneMap) — cards written 2026-09-24
- **37177 Tyrrell** (Eastern NC) — TyrrellService/7 CAMA+SALEAMOUNT+owner/tax (~4.4k; ACRESPARCEL 5–150 → 1164; SALEAMOUNT>0 → 1456 / in-range 323); cities-first Columbia Town=1 (~520) LUP Table40/Map12 PDF (A-1/R-7/…; no zoning FS); unincorp unzoned (ISR 2022 draft never adopted); FLU CAMA Maps17A/B PDF gap; PRC `pid={MASTERRECORD}` + card JPG + NCPTS `{pin}`; jurisdictionGis tyrrellcountygis.com→TyrrellWebApp; OneMap cntyfips='177' (gisacres weak; saledate 0); rejected empty Tyrrell_parcels + AGD print/maps 404 + PRC-by-PIN 404 — cards written 2026-09-24

- **37029 Camden** (Outer Banks / Eastern NC) — Parcels/1 CAMA+SaleDate/SaleQualified+owner (~8.0k; ACRES_GIS 5–150 → 1997; Q sales → 1231 / in-range 164); Zoning/1 countywide (224; NR/WL/RR/SR/…); cities-first South Mills SAP FLU PDF (no munis; Courthouse/Shiloh townships); FLU Comp Plan+County FLU Map+DEQ CAMA PDF gap (no FLU FS); NCPTS `parcel-detail/{PIN}` + Instant Sidebar `find={PIN}`; jurisdictionGis Experience `60ecb9b737384e7dbd1ad3f1f20b27b2`; OneMap cntyfips='029' (tax scrubbed parval=0; saledate OK); tax/sale-price REST gap; reject Camden NJ Parcels org + Spatialest/AGD 404 — cards written 2026-09-24

- **37187 Washington** (Eastern NC) — Washington_Service/9 Parcels_in_use CAMA+SalePrice+owner/tax (~12.6k; CalculatedAcres 5–150 → 1800; SalePrice>0 → 4374 / in-range 617); Parcels/0 GIS twin; cities-first PLYMOUTH_ZONING/21 DISTRICT (313; R10/R7/R20/C2/…); Roper/Creswell City_Limits+ETJ only (no zoning FS); county Zoning/10 CI stubs (24) Official Zoning Map REST gap; FLU DEQ CAMA edocs (county 1994 Under Review + Plymouth 2024) gap (landuse/5 LUSE W/C ≠ FLU); taxweb `Parcel.aspx?{WCParcel}` + AGD print `?NCPIN={NCPin}` + NCPTS `{NCPin}`; jurisdictionGis Experience Parcel Viewer + webappviewer; OneMap cntyfips='187'; reject dl.agd.cc/prc 404 + Beaufort City-of-Washington miswire — cards written 2026-09-24

- **37095 Hyde** (Outer Banks / Eastern NC) — Hyde_AGOL/3 Tax_Parcels CAMA+owner/tax (~7.8k; Assessed_Acreage 5–150 → 2414; vacant band → 2179); Sales_For_GIS/12 Sale_Price (~228 / in-range 43) join on REID_1/Pin_Num; **no incorporated munis**; cities-first **Ocracoke** Ch.36 ODO Municode (no zoning FS); mainland townships unzoned; FLU CAMA LUP Plan+appendices+map groups PDF gap; PRC `https://dl.agd.cc/prc/nc/hyde/{REID_1}.pdf` + NCPTS `parcel-detail/{REID_1}`; jurisdictionGis Experience `7d56b8f7…` / hydecountygis.com / webappviewer `4ee8283f…`; OneMap cntyfips='095' (saledate empty; parno↔Pin_Num, altparno↔REID_1); Townships/7 (6); AGD zip OK; rejected AGD print 404 + null PRC_LINK — cards written 2026-09-24


## MILESTONE — NC 100/100 complete

**2026-09-24 ~2:56 PM ET** — All 100 NC counties have md/json/yaml cards under `/workspace/gis-research/cards/NC/`. Scope: parcels + zoning/FLU + PA (tranche-3). Skipped: utilities, AADT. Closing county: **37095 Hyde**. Handed to Land Search Builder; CoS + Darryl milestone pinged. NC Public Info Researcher idle until next direction.
