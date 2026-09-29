# AL Rural OZ 2.0 — Pass 2 (full suite) progress, 2026-09-28

Scope: 62 AL rural OZ 2.0 counties. Per county: (a) enrichment.aadt (ALDOT TDMPublic/MapServer/0, AADT, YearAADT=2024, LUCountyID alpha index) with station count; (b) tax/sale/owner field mapping + owner entity-type rule; (c) top-level appraiserSearchUrl {PIN} verified by fetch where possible; (d) top-level jurisdictionGisUrl. Each card block: `pass2RuralOz2026_09_28`.

AADT note: aldotgis.dot.state.al.us TLS-EOFs from the box on 2026-09-28 (same failure as gis.montgomeryal.gov); counts were pulled through the external fetcher (one grouped outStatistics query, all 67 counties). LUCountyID=(FIPS3+1)/2 — alphabetical with "Saint Clair" before Shelby (58=St. Clair verified by point, 59=Shelby).

| County | LUCountyID | 2024 AADT stations | value / sale / owner fields | deep link verified? | GIS URL |
|---|---|---|---|---|---|
| Calhoun County | 8 | 655 | owner=NAME; assd=TOTAL_ASSD_VALUE; mkt=TOTAL_VALUE; tax=gap; saleDate=SALE_DATE; salePrice=SALE_PRICE | yes | https://gis.calhouncounty.org/Parcelviewer/ |
| Dallas County | 24 | 233 | owner=OWNERNAME; assd=gap; mkt=TOTALVALUE; tax=TAXES_DUE; saleDate=DEED_DATE; salePrice=gap | browser-only (pattern confirmed from viewer config) | https://dallas.capturecama.com/parcelviewer/ |
| DeKalb County | 25 | 312 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=DeedRecorded; salePrice=gap | yes | https://isv.kcsgis.com/al.dekalb_revenue/ |
| Etowah County | 28 | 535 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=gap; salePrice=gap | yes | https://isv.kcsgis.com/al.etowah_revenue/ |
| Franklin County | 30 | 204 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=DeedRecorded; salePrice=gap | yes | https://isv.kcsgis.com/al.franklin_revenue/ |
| Lauderdale County | 39 | 524 | owner=Owner; assd=TotalAssdValue; mkt=TotalMktValue; tax=TotalTaxDue; saleDate=DeedDate; salePrice=SalePrice | yes | https://isv.kcsgis.com/al.lauderdale_revenue/ |
| Colbert County | 17 | 390 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=DeedRecorded; salePrice=gap | yes | https://isv.kcsgis.com/al.colbert_revenue/ |
| Bullock County | 6 | 119 | owner=OwnerName; assd=gap; mkt=TotalValue; tax=gap; saleDate=gap; salePrice=gap | browser-only (pattern confirmed from viewer config) | https://bullock.capturecama.com/parcelviewer/ |
| Henry County | 34 | 162 | owner=NAME; assd=gap; mkt=TOTALVALUE; tax=gap; saleDate=DEED_B_P_D; salePrice=SALEPRICE | browser-only (pattern confirmed from viewer config) | https://henry.capturecama.com/parcelviewer/ |
| Winston County | 67 | 129 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=DeedRecorded; salePrice=gap | yes | https://isv.kcsgis.com/al.winston_revenue/ |
| Lawrence County | 40 | 166 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=DeedRecorded; salePrice=gap | yes | https://isv.kcsgis.com/al.lawrence_revenue/ |
| Cherokee County | 10 | 181 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=gap; salePrice=gap | yes | https://isv.kcsgis.com/al.cherokee_revenue/ |
| Hale County | 33 | 134 | owner=OWNERNAME; assd=gap; mkt=TOTALVALUE; tax=TAXES; saleDate=DEED_DATE; salePrice=gap | browser-only | https://experience.arcgis.com/experience/72a1479e2a384853bf7b3c512083c308 |
| Greene County | 32 | 122 | owner=FULLNAME; assd=gap; mkt=TOTAL_APPR; tax=gap; saleDate=D_DATE; salePrice=gap | browser-only | https://greenecountyal.maps.arcgis.com/apps/webappviewer/index.html?id=986a3ddc0daa4a819fc3ff68570819fa |
| Macon County | 44 | 209 | owner=gap; assd=gap; mkt=gap; tax=gap; saleDate=gap; salePrice=gap | browser-only (pattern confirmed from viewer config) | https://macon.capturecama.com/parcelviewer/ |
| Barbour County | 3 | 158 | owner=gap; assd=gap; mkt=gap; tax=gap; saleDate=gap; salePrice=gap | browser-only (pattern confirmed from viewer config) | https://barbour.capturecama.com/parcelviewer/ |
| Monroe County | 50 | 139 | owner=gap; assd=gap; mkt=gap; tax=gap; saleDate=gap; salePrice=gap | browser-only (pattern confirmed from viewer config) | https://monroe.capturecama.com/parcelviewer/ |
| Sumter County | 60 | 125 | owner=gap; assd=gap; mkt=gap; tax=gap; saleDate=gap; salePrice=gap | browser-only (pattern confirmed from viewer config) | https://sumter.capturecama.com/parcelviewer/ |
| Wilcox County | 66 | 134 | owner=gap; assd=gap; mkt=gap; tax=gap; saleDate=gap; salePrice=gap | browser-only (pattern confirmed from viewer config) | https://wilcox.capturecama.com/parcelviewer/ |
| Coosa County | 19 | 105 | owner=gap; assd=gap; mkt=gap; tax=gap; saleDate=gap; salePrice=gap | browser-only (pattern confirmed from viewer config) | https://coosa.capturecama.com/parcelviewer/ |
| Cullman County | 22 | 298 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=DeedRecorded; salePrice=gap | yes | https://isv.kcsgis.com/al.cullman_revenue/ |
| Jackson County | 36 | 210 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=gap (DeedRecorded empty); salePrice=gap | yes | https://isv.kcsgis.com/al.jackson_revenue/ |
| Talladega County | 61 | 301 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=DeedRecorded; salePrice=gap | yes | https://isv.kcsgis.com/al.talladega_revenue/ |
| Limestone County | 42 | 366 | owner=OwnerName; assd=gap; mkt=TotalValue; tax=gap; saleDate=gap; salePrice=gap | yes | https://isv.kcsgis.com/al.limestone_revenue/ |
| Marshall County | 48 | 325 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=DeedSigned; salePrice=gap | yes | https://isv.kcsgis.com/al.marshall_revenue/ |
| Blount County | 5 | 175 | owner=Owner; assd=TotalAssdValue; mkt=TotalMktValue; tax=TotalTaxDue; saleDate=gap; salePrice=gap | yes | https://isv.kcsgis.com/al.blount_revenue/ |
| Baldwin County | 2 | 642 | owner=Owner; assd=TAV; mkt=TTV; tax=TotalTaxDue; saleDate=DeedSigned; salePrice=gap | yes | https://isv.kcsgis.com/al.baldwin_revenue/ |
| St. Clair County | 58 | 238 | owner=NAME_1; assd=TOTAL_ASSD; mkt=TOTAL_VALU; tax=gap; saleDate=SALE_DATE; salePrice=SALE_PRICE | yes | https://map.stclairco.com/parcelviewer/ |
| Elmore County | 26 | 283 | owner=OwnerName; assd=gap; mkt=TotalValue; tax=gap; saleDate=gap; salePrice=gap | yes | https://isv.kcsgis.com/al.elmore_revenue/ |
| Madison County | 45 | 1001 | owner=PropertyOwner; assd=TotalAssessedValue; mkt=TotalAppraisedValue; tax=gap; saleDate=DeedDate; salePrice=gap | yes | https://isv.kcsgis.com/al.madison_revenue/ |
| Mobile County | 49 | 1216 | owner=Name1; assd=AssdValue; mkt=TotalValue; tax=gap; saleDate=gap; salePrice=gap | yes | https://gis.bisclient.com/alabama/mobilecad/ |
| Morgan County | 52 | 637 | owner=Owner; assd=AssdValue; mkt=TotalValue; tax=gap; saleDate=LastSalesDate; salePrice=SoldTotalPrice | yes | https://isv.kcsgis.com/al.morgan_revenue/ |
| Autauga County | 1 | 264 | owner=OWNER_NAME1; assd=ASSD_VALUE; mkt=TOTAL_VALUE; tax=gap; saleDate=gap; salePrice=gap | browser-only (not rendered this run) | https://autauga.capturecama.com/parcelviewer/ |
| Jefferson County | 37 | 2239 | owner=OWNERNAME; assd=AssdValue; mkt=PrevParcelTotal (prior-year); tax=gap; saleDate=gap; salePrice=gap | no (CaptureCAMA SPA, no PIN URL) | https://jccgis.jccal.org/ |
| Shelby County | 59 | 480 | owner=NAM1; assd=gap (OVRRIDE_ASD_VL all 0); mkt=gap (LN_VL1 is land only); tax=gap; saleDate=INST_DATE1 (yyyymmdd); salePrice=gap (SALES_PRICE all 0) | no (CaptureCAMA SPA, no PIN URL) | https://ptc.shelbyal.com/parcelviewer/ |
| Montgomery County | 51 | 958 | owner=OwnerName; assd=gap; mkt=TotalValue; tax=gap; saleDate=InstDate; salePrice=gap | yes | https://isv.kcsgis.com/al.montgomery_revenue/ |
| Bibb County | 4 | 152 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://bibb.alabamagis.com/bibb/ |
| Butler County | 7 | 208 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://butler.alabamagis.com/butler/ |
| Chambers County | 9 | 239 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://chambers.alabamagis.com/chambers/ |
| Chilton County | 11 | 238 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://chilton.alabamagis.com/chilton/ |
| Choctaw County | 12 | 99 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://choctaw.alabamagis.com/choctaw/ |
| Clarke County | 13 | 130 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://clarke.alabamagis.com/clarke/ |
| Clay County | 14 | 133 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://clay.alabamagis.com/clay/ |
| Coffee County | 16 | 324 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://coffee.alabamagis.com/coffee/ |
| Conecuh County | 18 | 170 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://conecuh.alabamagis.com/conecuh/ |
| Covington County | 20 | 293 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://covington.alabamagis.com/covington/ |
| Crenshaw County | 21 | 148 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://crenshaw.alabamagis.com/crenshaw/ |
| Dale County | 23 | 317 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://dale.alabamagis.com/dale/ |
| Escambia County (Alabama) | 27 | 235 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://escambia.alabamagis.com/escambia/ |
| Fayette County | 29 | 161 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://fayette.alabamagis.com/fayette/ |
| Geneva County | 31 | 188 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://geneva.alabamagis.com/geneva/ |
| Lamar County | 38 | 103 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://lamar.alabamagis.com/lamar/ |
| Lowndes County | 43 | 115 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://lowndes.alabamagis.com/lowndes/ |
| Marengo County | 46 | 153 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://marengo.alabamagis.com/marengo/ |
| Marion County | 47 | 250 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://marion.alabamagis.com/marion/ |
| Perry County | 53 | 94 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://perry.alabamagis.com/perry/ |
| Pickens County | 54 | 122 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://pickens.alabamagis.com/pickens/ |
| Pike County | 55 | 256 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://pike.alabamagis.com/pike/ |
| Randolph County | 56 | 153 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://randolph.alabamagis.com/randolph/ |
| Tallapoosa County | 62 | 242 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://tallapoosa.alabamagis.com/tallapoosa/ |
| Walker County | 64 | 303 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://walker.alabamagis.com/walker/ |
| Washington County | 65 | 70 | Flagship (no REST): owner/assd/mkt/tax/saleDate/salePrice = gap | no (Flagship search is POST-only; no GET deep link) | https://washington.alabamagis.com/washington/ |

## Pass 2 complete (2026-09-28, ~2:10 PM ET)

- Counties with a `pass2RuralOz2026_09_28` block: **62 / 62** (20 batch 1 + 16 usable batch 2 + 26 Flagship).
- AADT stamped (enrichment.aadt with luCountyId + stations2024, YearAADT=2024): **62 / 62**.
- Verified deep link (verified: yes; plain fetch, or external fetcher where the box TLS-EOFs): **22 / 62**. Calhoun, DeKalb, Etowah, Franklin, Lauderdale, Colbert, Winston, Lawrence, Cherokee, Cullman, Jackson, Talladega, Limestone, Marshall, Blount, Baldwin, St. Clair, Elmore, Madison, Mobile, Morgan, Montgomery.
- Browser-only deep links (pattern known, page is a JS app shell, content not confirmed by fetch): **12**. Autauga, Barbour, Bullock, Coosa, Dallas, Henry, Macon, Monroe, Sumter, Wilcox (all `https://{county}.capturecama.com/mapparceldetail/{PIN}`); Greene (`http://apps.agdmaps.com/print/al/greene/?PARCELID={PIN}`); Hale (`http://apps.agdmaps.com/print/al/hale/index.html?PARCELID={PIN}`).
- No deep link: **28**. The 26 Flagship counties have POST-only search with no GET parcel URL; Jefferson and Shelby use the CaptureCAMA Citizen Access Portal SPA with no PIN URL.
- Sale price available in the parcel layer (status usable): **4 / 62**. Calhoun (SALE_PRICE), Lauderdale (SalePrice), Morgan (SoldTotalPrice), St. Clair (SALE_PRICE, often 0). Partial: Henry (SALEPRICE text, usually blank). Shelby SALES_PRICE exists but is 0 on every parcel. The Mobile esearch page shows sale price, but the layer doesn't have it.
- Flagship viewer subdomains `{county}.alabamagis.com/{county}/` for all 26 returned HTTP 200 from the box (empty body to curl; content confirmed by external fetch for Bibb, Washington, Randolph; a made-up subdomain fails DNS). (b) field mapping = gap for all Flagship counties (no REST).
- cards/AL: 85 files, all pass yaml.safe_load, no duplicate top-level keys.
