# North Carolina GIS county cards — Darryl-Land-Search

Research pass: **2026-09-23** (Guilford + Catawba + Alamance + Johnston + Stanly + Harnett + Nash + Franklin + Cleveland + Granville + Randolph + Vance + Wilson + Sampson + Rockingham + Duplin + Columbus added **2026-09-24**; outside-footprint **Craven** (New Bern/Eastern NC) + Batch A: **Pitt** + **Moore** + **Robeson** (+ Cumberland); Hickory–Asheville shed: **Burke** + **Caldwell** + **Haywood** + **Watauga**; Rocky Mount shed: **Edgecombe** + **Halifax** added **2026-09-24**; Greenville/Eastern NC: **Lenoir** added **2026-09-24**; Crystal Coast / Eastern NC: **Carteret** added **2026-09-24**; Washington / Eastern NC: **Beaufort** added **2026-09-24**; Asheville shed: **McDowell** added **2026-09-24**; Outer Banks / Eastern NC: **Dare** added **2026-09-24**; Fayetteville shed: **Hoke** + **Scotland** added **2026-09-24**; Charlotte shed: **Montgomery** added **2026-09-24**; Fayetteville/Wilmington shed: **Bladen** added **2026-09-24**; Hickory shed: **Alexander** added **2026-09-24**; Winston-Salem shed: **Yadkin** TRANCHE-3 re-verified **2026-09-24**; Fayetteville/Charlotte shed: **Richmond** added **2026-09-24**; Asheville shed: **Transylvania** added **2026-09-24**; Boone/Asheville shed: **Ashe** added **2026-09-24**; Asheville shed: **Jackson** + **Macon** + **Madison** added **2026-09-24**; Asheville/Charlotte shed: **Polk** added **2026-09-24**; Asheville / Western NC: **Cherokee** added **2026-09-24**; Asheville shed: **Yancey** added **2026-09-24**; Asheville shed: **Mitchell** added **2026-09-24**; Boone/Asheville shed: **Avery** added **2026-09-24**; Boone/Winston-Salem shed: **Alleghany** added **2026-09-24**; Asheville / Western NC: **Clay** added **2026-09-24**; Asheville / Western NC: **Swain** added **2026-09-24**; Asheville / Western NC: **Graham** added **2026-09-24**; RDU / Greensboro shed: **Caswell** added **2026-09-24**; Outer Banks / Eastern NC: **Pasquotank** added **2026-09-24**; Outer Banks / Eastern NC: **Currituck** added **2026-09-24**; Greenville/Eastern NC: **Martin** added **2026-09-24**; Eastern NC: **Bertie** added **2026-09-24**; Eastern NC: **Gates** added **2026-09-24**; Eastern NC: **Hertford** added **2026-09-24**; Eastern NC / Rocky Mount shed: **Northampton** added **2026-09-24**; Eastern NC: **Chowan** added **2026-09-24**; Greenville/Eastern NC: **Greene** added **2026-09-24**; Eastern NC / New Bern shed: **Jones** added **2026-09-24**; Eastern NC: **Pamlico** added **2026-09-24**; Outer Banks / Eastern NC: **Perquimans** added **2026-09-24**; Eastern NC: **Tyrrell** added **2026-09-24**; Outer Banks / Eastern NC: **Camden** added **2026-09-24**; Eastern NC: **Washington** added **2026-09-24**; Outer Banks / Eastern NC: **Hyde** added **2026-09-24**).

Cards live at `/workspace/gis-research/cards/NC/{fips}-{slug}.{md,json,yaml}`.

**Suite status (2026-09-24 ~2:56 PM ET):** **100/100** counties carded (full suite parcels+zoning/FLU+PA; utilities/AADT skipped). Closing county: Hyde 37095.

## Status by priority MSA

| MSA | County | FIPS | Files | Notes |
|-----|--------|------|-------|-------|
| Charlotte | Mecklenburg | 37119 | md, json, yaml | Rich CAMA + Charlotte/towns zoning split |
| Charlotte | Cabarrus | 37025 | md, json, yaml | Situs join needed |
| Charlotte | Gaston | 37071 | md, json, yaml | No public FLU FS |
| Charlotte | Union | 37179 | md, json, yaml | ~78k CITY zoning stubs |
| Charlotte | Iredell | 37097 | md, json, yaml | Mooresville FLU strong |
| Charlotte | Rowan | 37159 | md, json, yaml | Salisbury FLUM |
| Charlotte | Lincoln | 37109 | md, json, yaml | Maiden mostly Catawba |
| Charlotte | Catawba | 37035 | md, json, yaml | energov CAMA; Hickory city FLU/zoning |
| Charlotte | Cleveland | 37045 | md, json, yaml | County CAMA + city-first zoning; partial sale layers |
| Charlotte | Anson | 37007 | md, json, yaml | Peachland/Polkton zoning empty |
| Charlotte | Stanly | 37167 | md, json, yaml | parcel_records_base_2 CAMA; Jurisdiction2 city zoning; FLUM/20 |
| Charlotte | Montgomery | 37123 | md, json, yaml | WebGIS CAMA+sale; cities-first Troy/Biscoe zoning; PropertyCard `{PinNoDash}`; FLU PDF; OneMap '123' |
| Hickory | Caldwell | 37027 | md, json, yaml | Cities-first Lenoir/Hudson/Granite Falls zoning; NCOneMap CAMA; AppraisalCard {PID}; FLU PDF+Hickory FLU; sale REST gap |
| Hickory | Alexander | 37003 | md, json, yaml | Website_map CAMA+sale; cities-first Taylorsville overlays; FLU_Classification+Overlay/30; PRC `{PARCELID}`; OneMap '003' |
| RDU | Wake | 37183 | md, json, yaml | Per-jurisdiction zoning stack |
| RDU | Durham | 37063 | md, json, yaml | Use REID not PIN |
| RDU | Orange | 37135 | md, json, yaml | CH/Carrboro/Hillsborough city-first |
| RDU | Johnston | 37101 | md, json, yaml | Clayton Clariti zoning+FLU; situs join TAG |
| RDU | Alamance | 37001 | md, json, yaml | County CAMA strong; ReGIS+Mebane city zoning; unincorp base zoning gap |
| RDU | Harnett | 37085 | md, json, yaml | Tax/Parcels CAMA; ZoningDistricts multi-muni; NCPTS {AccountNumber} |
| RDU | Lee | 37105 | md, json, yaml | Taxaccess PA deep-link {PARID}; Zoning shapefile CurrentZon; Place_Types FLU; Sanford/Broadway consolidated |
| RDU | Chatham | 37037 | md, json, yaml | Cities-first Pittsboro/Siler/Goldston; CamaParcels+PropertySales; NCPTS {parcel_number} |
| RDU | Wayne | 37191 | md, json, yaml | AGOL TaxParcels CAMA; Goldsboro+MO/Fremont/Pikeville/Eureka city-first zoning; Goldsboro FLU only |
| RDU | Granville | 37077 | md, json, yaml | County AGOL CAMA; Oxford/Butner/Creedmoor/Stovall zoning; Stem gap; ITSPublic {Parcel} |
| RDU | Nash | 37127 | md, json, yaml | Cities-first RM/Nashville zoning; LDP 2022 FLU; taxdata {TAX_PARID} |
| RDU / Rocky Mount | Edgecombe | 37065 | md, json, yaml | Cities-first Tarboro/RM tip zoning; webmap CAMA+sale; Keystone {linkpin}; FLU UA/UB gap |
| RDU / Rocky Mount | Halifax | 37083 | md, json, yaml | OpenGov RR AGOL CAMA+sale; cities-first Roanoke Rapids Zoning2; NCPTS/qPublic {PARID}; FLU+county zoning REST gaps |
| Eastern NC / Rocky Mount | Northampton | 37131 | md, json, yaml | AGD NorthamptonService/8 CAMA+sale+owner; cities-first Rich Square zoning+FLU; PRC `pin{PIN}.pdf` + NCPTS `{PARCELNBR}`; OneMap '131'; county zoning/FLU REST gaps |
| RDU | Franklin | 37069 | md, json, yaml | Web View + TaxZoning CAMA/deeds; city-routed zoning; NCPTS {PARID}; FLU gap |
| RDU | Vance | 37181 | md, json, yaml | Envirolink CAMA; Henderson city-first zoning; ustaxdata {OWNID}+{PIN}; FLU/sale REST gap |
| RDU | Warren | 37185 | md, json, yaml | RokMap CAMA+Zoning; cities-first Warrenton/Norlina/Macon; NCPTS {NEWPIN}; FLU PDF gap |
| RDU | Person | 37145 | md, json, yaml | BitekParcelInfo CAMA; Roxboro city-first PlanZone; FLUM; NCPTS {Record_Number}/{PIN} |
| RDU / Greensboro | Caswell | 37033 | md, json, yaml | WebGIS NC/Caswell CAMA+owner/tax; cities-first Yanceyville/Milton/Hyco zoning; FLU Comp Plan PDF; AppraisalCard `{P_PIN}`; OneMap '033'; sale REST gap |
| RDU | Sampson | 37163 | md, json, yaml | AGOL Parcels CAMA; Clinton city-first zoning; county FLU; Tyler/NCPTS {PIN}; other towns ETJ stubs only |
| RDU | Wilson | 37195 | md, json, yaml | Taxparcels CAMA; Wilson city-first zoning+FLU 2043; town zoning stack; DevNet {OwnerID}; county FLU coarse |
| Winston-Salem | Forsyth | 37067 | md, json, yaml | MapForsyth + Kernersville |
| Winston-Salem / Greensboro | Guilford | 37081 | md, json, yaml | GC parcels + Combined Zoning; GSO/HP city-first |
| Winston-Salem | Davidson (NC) | 37057 | md, json, yaml | Not TN Davidson |
| Winston-Salem | Davie | 37059 | md, json, yaml | No sale price on REST |
| Winston-Salem | Stokes | 37169 | md, json, yaml | Viewer homepage stub |
| Winston-Salem | Yadkin | 37197 | md, json, yaml | CountyGISmap CAMA+sale+owner; cities-first Yadkinville/Jonesville/Boonville/East Bend zoning; FLU PDF; AppraisalCard `{PARCEL_NO}` + NCPTS `{PIN}`; OneMap '197' |
| Winston-Salem | Surry | 37171 | md, json, yaml | InternalUse CAMA+sale; cities-first MA/Elkin/Dobson/Pilot zoning; coarse FLU+Dobson; AppraisalCard {Parcel} |
| Winston-Salem | Randolph | 37151 | md, json, yaml | ParcelQuery CAMA; Zoning/31 JURISDICTION cities-first; GMA FLU; CAMA {REID}; sale price REST gap |
| Winston-Salem | Rockingham | 37157 | md, json, yaml | Tax_gdb Expanded CAMA+situs+sale; Reidsville city-first zoning; Land_Classification FLU proxy; PropertyCard/ustaxdata {ParcelNumber} |
| Winston-Salem | Wilkes | 37193 | md, json, yaml | Parcels CAMA+sale; cities-first Wilkesboro/NW zoning; FLU PDF; Datalet {PARCEL_ID}; OneMap '193'; CRS 32019 |
| Wilmington | New Hanover | 37129 | md, json, yaml | IASTAX join; Wilmington FLU gap |
| Wilmington | Brunswick | 37019 | md, json, yaml | 19 MuniZoning; no sale price |
| Wilmington | Pender | 37141 | md, json, yaml | Energov primary |
| Wilmington | Onslow | 37133 | md, json, yaml | Full CAMA parcels; Jax city-first zoning; Horizon 2040 + FLU/20 |
| Wilmington | Duplin | 37061 | md, json, yaml | TaxMapping CAMA; Kenansville/Warsaw/Beulaville/Calypso city-first zoning; unincorp unzoned; FLU PDF; ITSPublicDL/NCPTS {PIN}/{ParcelNumber} |
| Wilmington | Columbus | 37047 | md, json, yaml | OneMap+taxdata CAMA; MangoMap cities-first zoning; FLU PDF; PRC {GSEQ} |
| Fayetteville | Cumberland | 37051 | md, json, yaml | Tax/Parcels CAMA; Fay+town Jurisdiction zoning; FLU 2025; camapwa {REID}/{PARCEL_PK}; OneMap parno/gisacres weak |
| Fayetteville / Southern Pines | Moore | 37125 | md, json, yaml | Tax_Layers CAMA+sale; cities-first City Zoning JR (SP/PH/AB/CG/…); county FLU; Pinehurst AGOL; AppraisalCard {PARID} |
| Fayetteville | Robeson | 37155 | md, json, yaml | AGOL CAMA + ROKMAPS cities-first zoning; ustaxdata {MAPNO}; FLU PDF; sale price REST gap |
| Fayetteville | Scotland | 37165 | md, json, yaml | AGOL Tax Parcels CAMA+owner/tax/DeedDate; cities-first Laurinburg Zoning; county Zoning; FLU PDF; AppraisalCard `{PIN}` space-%20; OneMap '165'; sale price REST gap |
| Fayetteville | Hoke | 37093 | md, json, yaml | Parcels CAMA+COST_TOTAL+deed; cities-first Raeford ZONE stub; FLU PDF; TaxCards `{TWN_PIN}-`; OneMap CAMA empty; sale price REST gap |
| Fayetteville / Wilmington | Bladen | 37017 | md, json, yaml | TaxParcels CAMA+SalesAmoun; cities-first muni limits (Elizabethtown…); County_Zoning; FLU PDF; ustaxdata `{OwnerId:07d}`+`{ParcelId:07d}`+`{PIN}`; OneMap '017' |
| Fayetteville / Charlotte | Richmond | 37153 | md, json, yaml | ParcelViewer/12 CAMA+SaleDate+owner/tax; County Zoning; muni zoning REST gap; FLU PDF; AppraisalCard `{PIN}`; OneMap '153' |
| Greenville | Pitt | 37147 | md, json, yaml | CadastralPitt CAMA+sale; cities-first Greenville/Winterville/Ayden/Farmville zoning; Greenville+county FLU; NCPTS {PARCELNUMBER} |
| Greenville / Eastern NC | Lenoir | 37107 | md, json, yaml | PZA/OpenGov CAMA+sale; cities-first Kinston/Pink Hill zoning; Pink Hill FLU; La Grange PDF gap; Spatialest {Record_Num} + NCPTS {NC_PIN}; OneMap '107' |
| Greenville / Eastern NC | Martin | 37117 | md, json, yaml | TaxParcels CAMA+SALE_PRICE+owner; cities-first Williamston ZONING FS/5; Robersonville PDF; FLU Comp Plan+NCDOT PDF; ITSPublicMT `{PARCEL_ID}` + PropertyCards; OneMap '117' |
| Greenville / Eastern NC | Greene | 37079 | md, json, yaml | Greene_Service/4 CAMA+owner/tax+deed; cities-first Snow Hill/Hookerton/Walstonburg zoning; County_Zoning; FLU Comp Plan in-progress PDF; AGD PRC `{prc_ppn}01` + NCPTS `{pin}`; OneMap '079'; sale price REST gap |
| New Bern / Eastern NC | Craven | 37049 | md, json, yaml | JustParcels CAMA+sale price; cities-first New Bern+Havelock zoning; FLU PDF; map.htm?pid={PID}+NCPTS |
| Eastern NC / New Bern | Jones | 37103 | md, json, yaml | Jones_Bitek/0 CAMA+saleprice+owner; cities-first Trenton/Pollocksville/Maysville (zoning PDF/town-hall; Trenton gap); FLU LUP PDF; AppraisalCard `{pin83}` + NCPTS + AGD print; OneMap '103'; county/muni zoning REST gaps |
| Washington / Eastern NC | Beaufort | 37013 | md, json, yaml | Beaufort_Service/4 CAMA+sale+owner; cities-first Washington+Belhaven zoning; FLU PDF; NCPTS `{REID}` + AGD `{GPIN}`; OneMap '013' |
| Eastern NC | Washington | 37187 | md, json, yaml | Washington_Service/9 CAMA+SalePrice+owner; cities-first Plymouth PLYMOUTH_ZONING; Roper/Creswell limits; FLU DEQ CAMA edocs; taxweb `{WCParcel}` + AGD print `{NCPin}`; OneMap '187' |
| Eastern NC | Pamlico | 37137 | md, json, yaml | Pamlico_ParcelService/5 CAMA+SALE_AMT+owner/tax; cities-first Oriental GMO PDF; FLU CAMA+Map A/B PDF; PRC `{MAPID}.pdf` + NCPTS `{PIN}`; OneMap '137'; muni zoning REST gaps |
| Eastern NC | Bertie | 37015 | md, json, yaml | Bertie_Parcel_Viewer/4 CAMA+owner/tax+STAMPS; cities-first Windsor PARZONE+UDO PDF; FLU FLUM PDF; PRC `{GEOPIN}.pdf` + NCPTS; OneMap '015'; sale price REST gap |
| Eastern NC | Gates | 37073 | md, json, yaml | GatesParcelService/5 CAMA+saleprice+owner/tax; Zoning/6 countywide; cities-first Gatesville Towns/9; FLU Comp Plan+Gatesville LUP PDF; AppraisalCard `{pclnbr}` + NCPTS + AGD print; OneMap '073' (parno=pin swap) |
| Eastern NC | Chowan | 37041 | md, json, yaml | Chowan_Feature_Service/0 CAMA+SALE_PRICE+owner; tax REST scrubbed; cities-first Edenton_Zoning/16 + County_Zoning/15; FLU CAMA LUP PDF; AppraisalCard `{PIN}` + NCPTS; OneMap '041' |
| Eastern NC | Tyrrell | 37177 | md, json, yaml | TyrrellService/7 CAMA+SALEAMOUNT+owner; cities-first Columbia Map12 PDF (no zoning FS); unincorp unzoned; FLU CAMA Maps17A/B PDF; PRC `pid={MASTERRECORD}` + NCPTS `{pin}`; OneMap '177' |
| Eastern NC | Hertford | 37091 | md, json, yaml | TaxParcels CAMA+PKG_SALE+owner; cities-first Ahoskie/Murfreesboro/Winton/Cofield/Como zoning; FLU PDF; NCPTS PropertySummary `{Tax_REID}`; OneMap '091' |
| Crystal Coast / Eastern NC | Carteret | 37031 | md, json, yaml | Parceldata CAMA+sale+owner; cities-first MHC/Newport/EI zoning; MHC FLU; Beaufort+beach towns REST gap; AppraisalCard `{PIN15}`; OneMap '031' |
| Outer Banks / Eastern NC | Camden | 37029 | md, json, yaml | Parcels/1 CAMA+SaleDate+owner; county Zoning/1; cities-first South Mills SAP FLU PDF (no munis); NCPTS `{PIN}` + Instant `find=`; OneMap '029'; tax/sale-price REST scrubbed |
| Outer Banks / Eastern NC | Currituck | 37053 | md, json, yaml | OperationalLayers/20 CAMA+sale+owner; county Zoning/30 + overlays; cities-first Moyock/Corolla/Maple SAP FLU + Imagine LUP; NCPTS `{PARCEL_ID}` + viewer `?pin=`; OneMap '053'; no munis |
| Outer Banks / Eastern NC | Dare | 37055 | md, json, yaml | AGOL gis_polygons CAMA+owner/tax/zoning attr; sales_layer/points WFS join; cities-first KDH/NH/Manteo/KH/Duck/SS WFS zoning; FLU CAMA PDF; Spatialest `{parcel}` + landtransfer; OneMap '055' |
| Outer Banks / Eastern NC | Hyde | 37095 | md, json, yaml | Hyde_AGOL/3 CAMA+owner/tax; Sales_For_GIS/12 Sale_Price join; cities-first Ocracoke Ch.36 ODO (no munis/zoning FS); FLU CAMA LUP PDF; PRC `{REID_1}.pdf` + NCPTS `{REID_1}`; OneMap '095' |
| Outer Banks / Eastern NC | Pasquotank | 37139 | md, json, yaml | AGOL 20260101 CAMA+owner/tax; sales2025 join; cities-first Elizabeth City CityZoning; County_Zoning_2026; FLU PDF; taxcard `PP2={PPN_2}` + NCPTS; OneMap '139' |
| Outer Banks / Eastern NC | Perquimans | 37143 | md, json, yaml | Perquimans_Service/2 CAMA+owner/tax+DATE_SOLD (no SALE_PRICE); cities-first Hertford Zoning Map PDF + PERQ_ZONING/4; Winfall carve-out; FLU CAMA LUP PDF; PRC `search?for={parcel_id}` + NCPTS `{pin}`; OneMap '143' |
| Asheville | Buncombe | 37021 | md, json, yaml | City-split zoning; Asheville FLU |
| Asheville / Western NC | Cherokee | 37039 | md, json, yaml | OfficeView CAMA+sale+owner; cities-first Murphy/Andrews zoning; FLU PDF gap; TaxNet `{ParcelID}` + NCPTS `{NEWPIN}`; OneMap '039'; unincorp unzoned |
| Asheville / Western NC | Clay | 37043 | md, json, yaml | Parcels04162026 CAMA+sale+owner; cities-first Hayesville zoning PDF/JPG (no FS); FLU CLUP PDF; AppraisalCard `{ParcelNumb}` + NCPTS; OneMap '043'; unincorp unzoned |
| Asheville / Western NC | Graham | 37075 | md, json, yaml | GrahamAGOL CAMA+sale+owner; cities-first Lake Santeetlah zoning PDF (no FS); Robbinsville/Fontana Dam/unincorp unzoned; FLU Santeetlah LUP PDF; AppraisalCard `{PARNUM}` + NCPTS `{pin}`; OneMap '075' |
| Asheville / Western NC | Swain | 37173 | md, json, yaml | OperationalLayers CAMA+owner/tax; cities-first Bryson City limits (no district FS); FLU 1994 PDF; AppraisalCard `{PARCEL_ID}` + NCPTS; OneMap '173' altparno; sale price REST gap; unincorp unzoned |
| Asheville | Henderson | 37089 | md, json, yaml | City-split zoning; HVL AGOL FLU |
| Asheville | Haywood | 37087 | md, json, yaml | SmartGov CAMA+sale; cities-first Waynesville/Canton/Clyde/Maggie zoning; AppraisalCard {ALPHA_NO_DASHES}; FLU PDF; unincorp unzoned |
| Asheville | Macon | 37113 | md, json, yaml | JustParcels CAMA+sale+owner; cities-first Franklin AdditionalLayers/24 + Highlands Zoning_01_2025/31; FLU PDF; AppraisalCard `{PIN}` + TaxBillSearch/Parcel/{PIN}; OneMap '113'; unincorp unzoned |
| Asheville | Madison | 37115 | md, json, yaml | 2025_Parcels CAMA+owner; cities-first Marshall/Mars Hill zoning; Hot Springs gap; FLU PDF; NCPTS `{PARCEL_PK}`/`{PIN_DASHED}`; OneMap '115' tax; sale REST gap |
| Asheville | Mitchell | 37121 | md, json, yaml | WebMapNew/12 CAMA+owner/tax+Deed_Date; cities-first HCCOG Spruce_Pine_Zoning; Bakersville+unincorp unzoned; FLU gap; NCPTS `{GISPIN}`; OneMap '121'; Sales/18 partial price |
| Asheville | Jackson | 37099 | md, json, yaml | Tax_Admin Parcels CAMA+sale; cities-first Sylva/Dillsboro/Forest Hills/Webster + Cullowhee/Cashiers/441; PRC `{No_Dash}`; FLU SAP PDF; OneMap '099' |
| Asheville | Transylvania | 37175 | md, json, yaml | Parcels FS/2 CAMA+sale+owner; cities-first Brevard Zoning+FLU CLUP2030; Pisgah Forest zoning; Rosman gap; NCPTS `{PIN}`; OneMap '175' |
| Asheville | McDowell | 37111 | md, json, yaml | WebGIS NC/McDowell CAMA+sale date; cities-first Marion OfficialZoning; Old Fort gap; FLU PDF; AppraisalCard `{PIN}`; OneMap '111' |
| Asheville / Hickory | Burke | 37023 | md, json, yaml | ProdParcelViewFC CAMA+sale; cities-first Morganton/Valdese/…; FLU/19; CamaPWA {REID}; OneMap '023' |
| Asheville / Boone | Watauga | 37189 | md, json, yaml | parcelsdbf CAMA+sale; cities-first Boone Zoning_Mobile; BR/BM/SD ZONE attrs; FLU PDF gap; Datalet {PID}; OneMap '189' |
| Asheville / Boone | Ashe | 37009 | md, json, yaml | OpenData TaxParcel CAMA+sale; cities-first Jefferson/WJ AsheED_Zoning + WJ ETJ; Lansing gap; FLU Comp Plan PDF; AppraisalCard `{ParcelNumber}`; OneMap '009' |
| Asheville / Boone | Avery | 37011 | md, json, yaml | AGD Avery_AGOL/21 CAMA+sale+owner; cities-first Banner Elk/Sugar/Beech/Seven Devils; Newland+… zoning gap; FLU docx 404; AppraisalCard `{PARNUM}`; OneMap '011' |
| Boone / Winston-Salem | Alleghany | 37005 | md, json, yaml | WebGIS/11 owner+deed; OneMap '005' tax+mail/situs; Sparta zoning REST gap; Land Classifications FLU; AppraisalCard `{PIN}`; sale price REST gap |
| Asheville / Charlotte | Rutherford | 37161 | md, json, yaml | Addressing CAMA+sale; cities-first FC/Rutherfordton/Spindale/Lake Lure zoning; FLU PDF; NCPTS `{Parcel_Number}`; OneMap '161' |
| Asheville / Charlotte | Polk | 37149 | md, json, yaml | Parcels/0 CAMA+owner/tax+DEED_YEAR; cities-first Zoning1 Columbus/Tryon/Saluda; FLU PDF gap; PRC `{TMS}.pdf` + NCPTS `{TMS}`; OneMap '149'; sale price REST gap |
| Asheville | Yancey | 37199 | md, json, yaml | Op2025 TaxParcels CAMA+owner/tax+STAMPS; cities-first Burnsville Zoning; FLU PDF; IAS `{PIN}{Card}` + NCPTS `{PIN}`; OneMap '199' |

## Ingest rule (Land Search Builder)

City GIS wins inside city limits; county stubs only where munis don’t publish. Template: `/workspace/gis-research/COUNTY_CARD_TEMPLATE.md`.

## Enrichment pointers

See statewide AADT dig card: [`enrichment/_aadt/NC-statewide-aadt.md`](../../enrichment/_aadt/NC-statewide-aadt.md).
