# OZ 2.0 Eligible GEOIDs — Other Tier MSAs (~90-Minute County Rings)

Repo copies: `data/oz2-other-msas-eligible.csv`, `data/oz2-other-msas-rural-eligible.csv`, `data/oz2-other-msas-urban-eligible.csv`. Refresh polygons with `npm run seed:oz2-eligible`.



**Prepared for:** Land Search Builder (Darryl Oswald)
**As of:** Tue Sep 22, 2026 (ET)
**Source appendix:** IRS Rev. Proc. 2026-14 — `/workspace/rp-26-14-appendix.xlsx`
**Companion CSV:** `/workspace/oz2-other-msas-eligible.csv`
**Splits:** `/workspace/oz2-other-msas-rural-eligible.csv` · `/workspace/oz2-other-msas-urban-eligible.csv`

## Method & honesty on drive time

Drive-time sheds are **approximate county sets**, not surveyed isochrones. Each metro starts from the **OMB July 2023 MSA county list**, then adds a sensible adjacent ring commonly reachable in **~90 minutes** off-peak from the listed city-center anchor. Peak congestion can push some included counties over 90 minutes. **Conservative research filter for Land Search Builder, not survey-grade isochrones.**

County matching is **state-aware**. Alabama markets are **NEW** to Darryl's map. Memphis includes AR/MS MSA counties clearly in the drive shed (documented below).

Status labeling: **Eligible — not designated**. SC markets include Governor-filed Sep 10, 2026 caveat in notes (nominated GEOID list not public) — do **not** mark designated. GA/FL/NC/TN/AL(/AR/MS for Memphis spill): eligible only.

---

## Vero Beach

- **City center:** Downtown Vero Beach (Indian River)
- **OMB MSA core:** Sebastian-Vero Beach-West Vero Corridor, FL (OMB 2023: Indian River)
- **Eligible tract count:** **62** (rural Y=25, non-rural N=37)
- **Rationale:** MSA core Indian River + St. Lucie/Martin coastal I-95 ring and Okeechobee inland; southern Brevard (Palm Bay corridor) commonly ≤90 off-peak. Excludes Palm Beach (routine >90 from Vero proper).
- **Counties included:**
  - Florida: Indian River, St. Lucie, Martin, Okeechobee, Brevard
- **Eligible by county (rural / non-rural):**
  - Brevard (Florida): 28 (Y=9, N=19) _(outer/uncertain)_
  - Indian River (Florida): 9 (Y=9, N=0)
  - Martin (Florida): 7 (Y=2, N=5) _(outer/uncertain)_
  - Okeechobee (Florida): 4 (Y=4, N=0) _(outer/uncertain)_
  - St. Lucie (Florida): 14 (Y=1, N=13)
- **Uncertain / outer-edge counties:** Brevard, Martin, Okeechobee
- **Exclusions / notes:** Palm Beach (often >90) excluded

## Melbourne

- **City center:** Downtown Melbourne / Palm Bay (Brevard)
- **OMB MSA core:** Palm Bay-Melbourne-Titusville, FL (OMB 2023: Brevard)
- **Eligible tract count:** **175** (rural Y=24, non-rural N=151)
- **Rationale:** Brevard MSA + Indian River south, Volusia north via I-95, Osceola west via US-192, Orange east/SE fringe via Beachline. Intentionally overlaps Vero (Brevard/Indian River) and Orlando (Brevard/Osceola/Orange/Volusia) for dual-market Land Search tabs.
- **Counties included:**
  - Florida: Brevard, Indian River, Osceola, Orange, Volusia
- **Eligible by county (rural / non-rural):**
  - Brevard (Florida): 28 (Y=9, N=19)
  - Indian River (Florida): 9 (Y=9, N=0)
  - Orange (Florida): 87 (Y=1, N=86) _(outer/uncertain)_
  - Osceola (Florida): 20 (Y=3, N=17) _(outer/uncertain)_
  - Volusia (Florida): 31 (Y=2, N=29) _(outer/uncertain)_
- **Uncertain / outer-edge counties:** Orange, Osceola, Volusia
- **Exclusions / notes:** Seminole core / Lake generally oriented to Orlando — excluded here

## Jacksonville

- **City center:** Downtown Jacksonville (Duval)
- **OMB MSA core:** Jacksonville, FL (OMB 2023: Baker, Clay, Duval, Nassau, St. Johns)
- **Eligible tract count:** **98** (rural Y=8, non-rural N=90)
- **Rationale:** Standard OMB Jacksonville MSA core only. Eligible tracts are the Rev. Proc. 2026-14 appendix rows in those five Florida counties. Rural vs urban is the appendix Rural Status column. Duval’s eligible tracts are all Non-rural. This cut does not add a wider ~90-minute ring.
- **Counties included:**
  - Florida: Duval, Clay, St. Johns, Nassau, Baker
- **Eligible by county (rural / non-rural):**
  - Baker (Florida): 1 (Y=1, N=0)
  - Clay (Florida): 8 (Y=4, N=4)
  - Duval (Florida): 86 (Y=0, N=86)
  - Nassau (Florida): 1 (Y=1, N=0)
  - St. Johns (Florida): 2 (Y=2, N=0)
- **Uncertain / outer-edge counties:** none (MSA core)
- **Exclusions / notes:** Putnam, Flagler, Bradford, and Union (Florida) and Camden (Georgia) are outside the OMB 2023 MSA and are not in this market. No tract is marked designated or certified.

## Pensacola

- **City center:** Downtown Pensacola
- **OMB MSA core:** Pensacola-Ferry Pass-Brent, FL (Escambia, Santa Rosa)
- **Eligible tract count:** **49** (rural Y=22, non-rural N=27)
- **Rationale:** Pensacola MSA + Okaloosa (Fort Walton ~45–70) and Baldwin AL (Gulf Shores/Daphne corridor clearly in ~60–90 across Perdido). Walton FL coastal included as outer US-98 ring. Alabama Baldwin is intentional AL inventory for Darryl's expanding map.
- **Counties included:**
  - Florida: Escambia, Santa Rosa, Okaloosa, Walton
  - Alabama: Baldwin
- **Eligible by county (rural / non-rural):**
  - Baldwin (Alabama): 4 (Y=4, N=0) _(outer/uncertain)_
  - Escambia (Florida): 29 (Y=2, N=27)
  - Okaloosa (Florida): 6 (Y=6, N=0)
  - Santa Rosa (Florida): 4 (Y=4, N=0)
  - Walton (Florida): 6 (Y=6, N=0) _(outer/uncertain)_
- **Uncertain / outer-edge counties:** Baldwin, Walton
- **Exclusions / notes:** Escambia AL / Washington AL generally >90 from Pensacola — excluded

## Birmingham

- **City center:** Downtown Birmingham
- **OMB MSA core:** Birmingham, AL (Bibb, Blount, Chilton, Jefferson, St. Clair, Shelby, Walker)
- **Eligible tract count:** **152** (rural Y=42, non-rural N=110)
- **Rationale:** Birmingham MSA + Talladega (I-20) and Cullman (I-65 N) as clear ≤90 rings. Tuscaloosa flagged as outer (~50–75 off-peak; peak can exceed). Alabama is NEW to Darryl's map — MSA-first, conservative outer add.
- **Counties included:**
  - Alabama: Bibb, Blount, Chilton, Jefferson, St. Clair, Shelby, Walker, Talladega, Cullman, Tuscaloosa
- **Eligible by county (rural / non-rural):**
  - Bibb (Alabama): 4 (Y=4, N=0)
  - Blount (Alabama): 4 (Y=4, N=0)
  - Chilton (Alabama): 1 (Y=1, N=0)
  - Cullman (Alabama): 4 (Y=4, N=0) _(outer/uncertain)_
  - Jefferson (Alabama): 85 (Y=1, N=84)
  - Shelby (Alabama): 2 (Y=1, N=1)
  - St. Clair (Alabama): 4 (Y=4, N=0)
  - Talladega (Alabama): 12 (Y=12, N=0) _(outer/uncertain)_
  - Tuscaloosa (Alabama): 25 (Y=0, N=25) _(outer/uncertain)_
  - Walker (Alabama): 11 (Y=11, N=0)
- **Uncertain / outer-edge counties:** Cullman, Talladega, Tuscaloosa
- **Exclusions / notes:** Etowah/Gadsden and Anniston/Calhoun often outer/congested — excluded

## Mobile

- **City center:** Downtown Mobile
- **OMB MSA core:** Mobile, AL (OMB 2023: Mobile County only; Baldwin is separate Daphne MSA)
- **Eligible tract count:** **66** (rural Y=15, non-rural N=51)
- **Rationale:** Mobile County + Baldwin (Daphne/Fairhope ~20–40; treated as same labor shed despite separate MSA) + Washington AL north and Escambia AL NE via US-43/I-65. George MS Pascagoula corridor flagged as outer coastal ring.
- **Counties included:**
  - Alabama: Mobile, Baldwin, Washington, Escambia
  - Mississippi: George
- **Eligible by county (rural / non-rural):**
  - Baldwin (Alabama): 4 (Y=4, N=0)
  - Escambia (Alabama): 6 (Y=6, N=0) _(outer/uncertain)_
  - Mobile (Alabama): 54 (Y=3, N=51)
  - Washington (Alabama): 1 (Y=1, N=0) _(outer/uncertain)_
  - George (Mississippi): 1 (Y=1, N=0) _(outer/uncertain)_
- **Uncertain / outer-edge counties:** Escambia, George, Washington
- **Exclusions / notes:** Jackson MS / Clarke AL routinely >90 — excluded

## Huntsville

- **City center:** Downtown Huntsville
- **OMB MSA core:** Huntsville, AL (Madison, Limestone); Decatur/Morgan adjacent
- **Eligible tract count:** **58** (rural Y=31, non-rural N=27)
- **Rationale:** Huntsville MSA + Morgan (Decatur ~25–40) + Marshall (Guntersville) + Jackson (Scottsboro outer) + Cullman south via I-65. Lincoln TN (Fayetteville) flagged as optional TN spill ≤90 via US-231/431.
- **Counties included:**
  - Alabama: Madison, Limestone, Morgan, Marshall, Jackson, Cullman
  - Tennessee: Lincoln
- **Eligible by county (rural / non-rural):**
  - Cullman (Alabama): 4 (Y=4, N=0) _(outer/uncertain)_
  - Jackson (Alabama): 7 (Y=7, N=0) _(outer/uncertain)_
  - Limestone (Alabama): 8 (Y=8, N=0)
  - Madison (Alabama): 26 (Y=3, N=23)
  - Marshall (Alabama): 6 (Y=6, N=0)
  - Morgan (Alabama): 7 (Y=3, N=4)
- **Included counties with 0 eligible tracts:**
  - Lincoln (Tennessee)
- **Uncertain / outer-edge counties:** Cullman, Jackson, Lincoln
- **Exclusions / notes:** Franklin TN / Lawrence AL deeper west — excluded

## Savannah

- **City center:** Downtown Savannah
- **OMB MSA core:** Savannah, GA (Bryan, Chatham, Effingham)
- **Eligible tract count:** **64** (rural Y=31, non-rural N=33)
- **Rationale:** Savannah MSA + Liberty (Hinesville) and Bulloch (Statesboro) GA ring; Jasper SC and Beaufort SC coastal fringe commonly ≤90 via US-17/I-95. Screven flagged outer.
- **Counties included:**
  - Georgia: Bryan, Chatham, Effingham, Liberty, Bulloch, Screven
  - South Carolina: Jasper, Beaufort
- **Eligible by county (rural / non-rural):**
  - Bulloch (Georgia): 12 (Y=12, N=0) _(outer/uncertain)_
  - Chatham (Georgia): 33 (Y=0, N=33)
  - Liberty (Georgia): 3 (Y=3, N=0)
  - Screven (Georgia): 3 (Y=3, N=0) _(outer/uncertain)_
  - Beaufort (South Carolina): 9 (Y=9, N=0) _(outer/uncertain)_
  - Jasper (South Carolina): 4 (Y=4, N=0)
- **Included counties with 0 eligible tracts:**
  - Bryan (Georgia)
  - Effingham (Georgia)
- **Uncertain / outer-edge counties:** Beaufort, Bulloch, Screven
- **Exclusions / notes:** Charleston County SC is Charleston pack, not Savannah — excluded

## Columbia

- **City center:** Downtown Columbia, SC
- **OMB MSA core:** Columbia, SC (Calhoun, Fairfield, Kershaw, Lexington, Richland, Saluda)
- **Eligible tract count:** **105** (rural Y=62, non-rural N=43)
- **Rationale:** Columbia MSA + Newberry west, Orangeburg south, Sumter east, Lee NE as I-20/I-26/US-378 rings commonly ≤90. SC Governor-filed caveat applies to notes.
- **Counties included:**
  - South Carolina: Calhoun, Fairfield, Kershaw, Lexington, Richland, Saluda, Newberry, Orangeburg, Sumter, Lee
- **Eligible by county (rural / non-rural):**
  - Fairfield (South Carolina): 3 (Y=3, N=0)
  - Kershaw (South Carolina): 4 (Y=4, N=0)
  - Lee (South Carolina): 5 (Y=5, N=0) _(outer/uncertain)_
  - Lexington (South Carolina): 15 (Y=9, N=6)
  - Newberry (South Carolina): 4 (Y=4, N=0) _(outer/uncertain)_
  - Orangeburg (South Carolina): 21 (Y=21, N=0) _(outer/uncertain)_
  - Richland (South Carolina): 39 (Y=2, N=37)
  - Saluda (South Carolina): 4 (Y=4, N=0)
  - Sumter (South Carolina): 10 (Y=10, N=0) _(outer/uncertain)_
- **Included counties with 0 eligible tracts:**
  - Calhoun (South Carolina)
- **Uncertain / outer-edge counties:** Lee, Newberry, Orangeburg, Sumter
- **Exclusions / notes:** Aiken (Augusta-oriented) and Chester (Charlotte pack) — excluded

## Greenville

- **City center:** Downtown Greenville, SC
- **OMB MSA core:** Greenville-Anderson-Greer, SC (Anderson, Greenville, Laurens, Pickens)
- **Eligible tract count:** **105** (rural Y=70, non-rural N=35)
- **Rationale:** Greenville MSA + Spartanburg (same Upstate CSA, ~30–50) + Oconee west + Greenwood/Abbeville south ring. Intentionally overlaps Charlotte fringe only if Spartanburg — Spartanburg not in Charlotte 7-market pack.
- **Counties included:**
  - South Carolina: Anderson, Greenville, Laurens, Pickens, Spartanburg, Oconee, Greenwood, Abbeville
- **Eligible by county (rural / non-rural):**
  - Abbeville (South Carolina): 1 (Y=1, N=0) _(outer/uncertain)_
  - Anderson (South Carolina): 18 (Y=17, N=1)
  - Greenville (South Carolina): 32 (Y=2, N=30)
  - Greenwood (South Carolina): 6 (Y=6, N=0) _(outer/uncertain)_
  - Laurens (South Carolina): 6 (Y=5, N=1)
  - Oconee (South Carolina): 8 (Y=8, N=0) _(outer/uncertain)_
  - Pickens (South Carolina): 9 (Y=7, N=2)
  - Spartanburg (South Carolina): 25 (Y=24, N=1)
- **Uncertain / outer-edge counties:** Abbeville, Greenwood, Oconee
- **Exclusions / notes:** Union SC / Cherokee SC toward Charlotte — excluded from this shed

## Chattanooga

- **City center:** Downtown Chattanooga
- **OMB MSA core:** Chattanooga, TN-GA (Hamilton/Marion/Sequatchie TN; Catoosa/Dade/Walker GA)
- **Eligible tract count:** **47** (rural Y=21, non-rural N=26)
- **Rationale:** Chattanooga MSA + Bradley TN (Cleveland) + Meigs + Whitfield GA (Dalton) as I-75 rings. Rhea flagged outer via US-27.
- **Counties included:**
  - Tennessee: Hamilton, Marion, Sequatchie, Bradley, Meigs, Rhea
  - Georgia: Catoosa, Dade, Walker, Whitfield
- **Eligible by county (rural / non-rural):**
  - Catoosa (Georgia): 2 (Y=0, N=2)
  - Dade (Georgia): 1 (Y=1, N=0)
  - Walker (Georgia): 7 (Y=3, N=4)
  - Whitfield (Georgia): 8 (Y=8, N=0) _(outer/uncertain)_
  - Bradley (Tennessee): 3 (Y=3, N=0)
  - Hamilton (Tennessee): 20 (Y=0, N=20)
  - Marion (Tennessee): 2 (Y=2, N=0)
  - Rhea (Tennessee): 2 (Y=2, N=0) _(outer/uncertain)_
  - Sequatchie (Tennessee): 2 (Y=2, N=0)
- **Included counties with 0 eligible tracts:**
  - Meigs (Tennessee)
- **Uncertain / outer-edge counties:** Meigs, Rhea, Whitfield
- **Exclusions / notes:** McMinn / Polk TN deeper SE — excluded

## Knoxville

- **City center:** Downtown Knoxville
- **OMB MSA core:** Knoxville, TN (Anderson, Blount, Campbell, Grainger, Knox, Loudon, Morgan, Roane, Union)
- **Eligible tract count:** **70** (rural Y=41, non-rural N=29)
- **Rationale:** Knoxville MSA + Sevier (Pigeon Forge/Gatlinburg tourism corridor ≤60) + Jefferson and Hamblen (Morristown) east via I-40. Cocke flagged outer.
- **Counties included:**
  - Tennessee: Anderson, Blount, Campbell, Grainger, Knox, Loudon, Morgan, Roane, Union, Sevier, Jefferson, Hamblen, Cocke
- **Eligible by county (rural / non-rural):**
  - Anderson (Tennessee): 6 (Y=5, N=1)
  - Blount (Tennessee): 3 (Y=0, N=3)
  - Campbell (Tennessee): 9 (Y=9, N=0) _(outer/uncertain)_
  - Cocke (Tennessee): 5 (Y=5, N=0) _(outer/uncertain)_
  - Grainger (Tennessee): 3 (Y=3, N=0)
  - Hamblen (Tennessee): 4 (Y=4, N=0) _(outer/uncertain)_
  - Jefferson (Tennessee): 1 (Y=1, N=0)
  - Knox (Tennessee): 25 (Y=1, N=24)
  - Loudon (Tennessee): 1 (Y=0, N=1)
  - Morgan (Tennessee): 1 (Y=1, N=0) _(outer/uncertain)_
  - Roane (Tennessee): 4 (Y=4, N=0)
  - Sevier (Tennessee): 7 (Y=7, N=0)
  - Union (Tennessee): 1 (Y=1, N=0)
- **Uncertain / outer-edge counties:** Campbell, Cocke, Hamblen, Morgan
- **Exclusions / notes:** Cumberland / Crossville often ≥90 — excluded

## Memphis

- **City center:** Downtown Memphis
- **OMB MSA core:** Memphis, TN-MS-AR (Shelby/Fayette/Tipton TN; DeSoto/Marshall/Tate/Tunica/Benton MS; Crittenden AR)
- **Eligible tract count:** **175** (rural Y=44, non-rural N=131)
- **Rationale:** Full OMB Memphis MSA included — DeSoto MS and Crittenden AR are clearly ≤45–60 from downtown; Marshall/Tate/Tunica/Benton MS are MSA outlying and flagged as outer/uncertain. Lauderdale TN and Mississippi County AR added as I-55/US-61 outer ring. Only appendix-eligible tracts in those states are exported.
- **Counties included:**
  - Tennessee: Shelby, Fayette, Tipton, Lauderdale
  - Mississippi: DeSoto, Marshall, Tate, Tunica, Benton
  - Arkansas: Crittenden, Mississippi
- **Eligible by county (rural / non-rural):**
  - Crittenden (Arkansas): 11 (Y=10, N=1)
  - Mississippi (Arkansas): 9 (Y=9, N=0) _(outer/uncertain)_
  - Benton (Mississippi): 3 (Y=3, N=0) _(outer/uncertain)_
  - DeSoto (Mississippi): 8 (Y=0, N=8)
  - Marshall (Mississippi): 8 (Y=8, N=0) _(outer/uncertain)_
  - Tate (Mississippi): 3 (Y=3, N=0) _(outer/uncertain)_
  - Tunica (Mississippi): 2 (Y=2, N=0) _(outer/uncertain)_
  - Lauderdale (Tennessee): 4 (Y=4, N=0) _(outer/uncertain)_
  - Shelby (Tennessee): 124 (Y=2, N=122)
  - Tipton (Tennessee): 3 (Y=3, N=0)
- **Included counties with 0 eligible tracts:**
  - Fayette (Tennessee)
- **Uncertain / outer-edge counties:** Benton, Lauderdale, Marshall, Mississippi, Tate, Tunica
- **Exclusions / notes:** Craighead AR / Panola MS deeper — excluded as outside clear 90-min

## Jackson

- **City center:** Downtown Jackson, Tennessee (Madison County). Not Jacksonville, Florida, and not Jackson, Mississippi.
- **OMB MSA core:** Jackson, TN (Madison; Chester is the other OMB county and is not in this parcel pull).
- **Eligible tract count:** **0**. Rev. Proc. 2026-14 rows for this MSA are not in `data/oz2-other-msas-eligible.csv`. The tract overlay stays empty. Do not invent GEOIDs.
- **Parcels:** Madison County FIPS 47113, 5–150 acres, from the GeoJobe IMPACT mirror. Medon has no public zoning or FLU layer.
- **Counties included:**
  - Tennessee: Madison

## Winston-Salem

- **City center:** Downtown Winston-Salem
- **OMB MSA core:** Winston-Salem, NC (Davidson, Davie, Forsyth, Stokes, Yadkin)
- **Eligible tract count:** **105** (rural Y=24, non-rural N=81)
- **Rationale:** Winston-Salem MSA + Guilford (Greensboro ~25–40; Piedmont Triad CSA) + Surry, Rockingham, Randolph as adjacent rings. Davidson dual-lists with Charlotte pack intentionally (same county name/state).
- **Counties included:**
  - North Carolina: Davidson, Davie, Forsyth, Stokes, Yadkin, Guilford, Surry, Rockingham, Randolph
- **Eligible by county (rural / non-rural):**
  - Davidson (North Carolina): 9 (Y=1, N=8)
  - Forsyth (North Carolina): 27 (Y=0, N=27)
  - Guilford (North Carolina): 45 (Y=0, N=45)
  - Randolph (North Carolina): 7 (Y=6, N=1) _(outer/uncertain)_
  - Rockingham (North Carolina): 6 (Y=6, N=0) _(outer/uncertain)_
  - Stokes (North Carolina): 2 (Y=2, N=0)
  - Surry (North Carolina): 7 (Y=7, N=0) _(outer/uncertain)_
  - Yadkin (North Carolina): 2 (Y=2, N=0)
- **Included counties with 0 eligible tracts:**
  - Davie (North Carolina)
- **Uncertain / outer-edge counties:** Randolph, Rockingham, Surry
- **Exclusions / notes:** Alamance is Raleigh-Durham pack primary; excluded here to limit sprawl

## Wilmington

- **City center:** Downtown Wilmington, NC
- **OMB MSA core:** Wilmington, NC (Brunswick, New Hanover, Pender)
- **Eligible tract count:** **55** (rural Y=31, non-rural N=24)
- **Rationale:** Wilmington MSA + Columbus inland, Duplin north via I-40, Onslow (Jacksonville) as coastal/US-17 ring commonly ≤90 off-peak.
- **Counties included:**
  - North Carolina: Brunswick, New Hanover, Pender, Columbus, Duplin, Onslow
- **Eligible by county (rural / non-rural):**
  - Brunswick (North Carolina): 7 (Y=7, N=0)
  - Columbus (North Carolina): 8 (Y=8, N=0) _(outer/uncertain)_
  - Duplin (North Carolina): 12 (Y=12, N=0) _(outer/uncertain)_
  - New Hanover (North Carolina): 17 (Y=0, N=17)
  - Onslow (North Carolina): 9 (Y=2, N=7) _(outer/uncertain)_
  - Pender (North Carolina): 2 (Y=2, N=0)
- **Uncertain / outer-edge counties:** Columbus, Duplin, Onslow
- **Exclusions / notes:** Sampson is Raleigh-Durham SE ring — excluded here

---

## Totals

| Market | Total eligible | Rural (Y) | Non-rural (N) |
| --- | ---: | ---: | ---: |
| Vero Beach | 62 | 25 | 37 |
| Melbourne | 175 | 24 | 151 |
| Jacksonville | 98 | 8 | 90 |
| Pensacola | 49 | 22 | 27 |
| Birmingham | 152 | 42 | 110 |
| Mobile | 66 | 15 | 51 |
| Huntsville | 58 | 31 | 27 |
| Savannah | 64 | 31 | 33 |
| Columbia | 105 | 62 | 43 |
| Greenville | 105 | 70 | 35 |
| Chattanooga | 47 | 21 | 26 |
| Knoxville | 70 | 41 | 29 |
| Memphis | 175 | 44 | 131 |
| Winston-Salem | 105 | 24 | 81 |
| Wilmington | 55 | 31 | 24 |
| **CSV rows** | **1386** | **491** | **895** |
| **Unique GEOIDs** | **1341** |  |  |

Dual-list notes: Melbourne overlaps Vero Beach (Brevard/Indian River) and Orlando primary pack counties; Winston-Salem shares Davidson NC with Charlotte primary pack; Pensacola/Mobile both list Baldwin AL (intentional dual-market). Columbia and Charleston both can list Orangeburg SC.

Missing Gazetteer lat/lon in Pack 2: **0**
