# OZ 2.0 Rural-Eligible GEOIDs — 7 Markets ≈90-Minute Drive Sheds

**Prepared for:** Land Search Builder (Darryl Oswald)
**As of:** Monday, Sep 21, 2026 (ET)
**Source appendix:** IRS Rev. Proc. 2026-14 — `/workspace/rp-26-14-appendix.xlsx` (Rural Status = Rural / entirely rural)
**Companion CSV:** `/workspace/oz2-7markets-90min-rural-eligible.csv`

## Method & honesty on drive time

Drive-time sheds are **approximate county sets**, not surveyed isochrones. A county is included when its primary population / corridor is commonly reachable in **~90 minutes** off-peak from the listed city-center anchor(s), using MSA membership, adjacent ring counties, and documented commute corridors (I-4, I-75, I-85, I-40, I-26, etc.). Peak congestion can push some included counties over 90 minutes; conversely some excluded fringe pockets may be ≤90 along freeways. **This is a conservative research filter for Land Search Builder, not a survey-grade isochrone.**

County matching is **state-aware** (e.g., Charlotte includes NC Union only — not SC Union).

Status labeling for all rows: **Eligible — not designated**. As of Sep 21, 2026, Florida, Georgia, South Carolina, Tennessee, and North Carolina have **no public certified 2027 QOZ lists**.

**Sep 24, 2026 update:** Governor McMaster’s September 23, 2026 announcement and the SC Commerce Final Recommendations PDF dated September 22, 2026 publish 112 nominated GEOIDs (`data/oz/sc-oz2-nominated-official-sccommerce-2026-09-23.csv`). South Carolina’s map shows only those GEOIDs, labeled **Governor-nominated / awaiting Treasury**. Eligible tracts that were not nominated are not shown in South Carolina. Florida, Georgia, North Carolina, and Tennessee rows stay on the eligible list. No GEOID is marked designated.

**Multifamily priority (same date):** `data/sc-oz2-mf-priority-shortlist.csv` ranks 22 of these rural-eligible tracts (10 Tier A, 12 Tier B) for garden/wrap site search. That rank is not a nomination. Refresh with `npm run seed:sc-mf`.

---

## Atlanta

- **City center:** Downtown Atlanta / Five Points (unchanged)
- **Rural-eligible tract count:** **73**
- **Rationale:** Atlanta MSA/CSA ring + ARC commuting geography; clear I-75/85/20/575/400 counties within ~90 min off-peak from Five Points. Excludes Troup/Upson as routinely >90 in peak.
- **Counties included (35):** Banks, Barrow, Bartow, Butts, Carroll, Cherokee, Clayton, Cobb, Coweta, Dawson, DeKalb, Douglas, Fayette, Forsyth, Fulton, Gordon, Gwinnett, Hall, Haralson, Heard, Henry, Jackson, Jasper, Lamar, Lumpkin, Meriwether, Monroe, Morgan, Newton, Paulding, Pickens, Pike, Rockdale, Spalding, Walton
- **Rural-eligible by county:**
  - Banks (Georgia): 1
  - Barrow (Georgia): 3
  - Bartow (Georgia): 4
  - Butts (Georgia): 2
  - Carroll (Georgia): 11
  - Fayette (Georgia): 1
  - Gordon (Georgia): 5
  - Hall (Georgia): 10
  - Haralson (Georgia): 1
  - Heard (Georgia): 2
  - Henry (Georgia): 2
  - Jackson (Georgia): 1
  - Jasper (Georgia): 3
  - Lumpkin (Georgia): 2
  - Meriwether (Georgia): 6
  - Monroe (Georgia): 2
  - Morgan (Georgia): 1
  - Pickens (Georgia): 2
  - Rockdale (Georgia): 1
  - Spalding (Georgia): 10
  - Walton (Georgia): 3
- **Included counties with 0 rural-eligible tracts:** Cherokee (Georgia), Clayton (Georgia), Cobb (Georgia), Coweta (Georgia), Dawson (Georgia), DeKalb (Georgia), Douglas (Georgia), Forsyth (Georgia), Fulton (Georgia), Gwinnett (Georgia), Lamar (Georgia), Newton (Georgia), Paulding (Georgia), Pike (Georgia)
- **Explicitly excluded (outside clear 90-min / wrong namesake):**
  - Troup (LaGrange often 75–100+ peak — excluded)
  - Upson (Thomaston often ≥90 — excluded)
- **Uncertain / outer-edge counties (included but flagged in CSV notes):** Heard (Georgia), Meriwether (Georgia), Lumpkin (Georgia), Banks (Georgia), Gordon (Georgia)
- **Sources:**
  - Wikipedia Metro Atlanta / Atlanta CSA county lists
  - Atlanta Regional Commission commuting / 21-county region framing (33n.atlantaregional.com)
  - Prior Atlanta ring extract: /workspace/ga-ring-rural-oz2-eligible.csv (expanded; Troup/Upson dropped for 90-min honesty)

## Tampa

- **City center:** Downtown Tampa (unchanged)
- **Rural-eligible tract count:** **66**
- **Rationale:** Tampa Bay MSA + north/east ring via I-75 / Suncoast / I-4. Pasco–Hernando–Polk–Sumter are primary rural OZ inventory. Citrus/Hardee included as outer but commonly ≤90 off-peak; DeSoto dropped.
- **Counties included (10):** Citrus, Hardee, Hernando, Hillsborough, Manatee, Pasco, Pinellas, Polk, Sarasota, Sumter
- **Rural-eligible by county:**
  - Citrus (Florida): 10
  - Hardee (Florida): 7
  - Hernando (Florida): 12
  - Hillsborough (Florida): 1
  - Pasco (Florida): 14
  - Polk (Florida): 16
  - Sumter (Florida): 6
- **Included counties with 0 rural-eligible tracts:** Manatee (Florida), Pinellas (Florida), Sarasota (Florida)
- **Explicitly excluded (outside clear 90-min / wrong namesake):**
  - DeSoto (Arcadia often ~90–110 — excluded as outside clear 90-min)
- **Uncertain / outer-edge counties (included but flagged in CSV notes):** Hardee (Florida), Citrus (Florida), Sarasota (Florida)
- **Sources:**
  - Tampa–St. Petersburg–Clearwater MSA + Polk I-4 commute articles (Lakeland ~35–60 min to Tampa)
  - Prior Tampa shortlist geography: /workspace/rural-oz2-tampa.md

## Orlando

- **City center:** Downtown Orlando (unchanged)
- **Rural-eligible tract count:** **64**
- **Rationale:** Orlando–Kissimmee–Sanford MSA + Lake/Polk/Sumter/Volusia/Brevard/Marion ring. Marion (Ocala) is outer ~75–90 via Turnpike/I-75 — included conservatively as prior ring.
- **Counties included (9):** Brevard, Lake, Marion, Orange, Osceola, Polk, Seminole, Sumter, Volusia
- **Rural-eligible by county:**
  - Brevard (Florida): 9
  - Lake (Florida): 14
  - Marion (Florida): 13
  - Orange (Florida): 1
  - Osceola (Florida): 3
  - Polk (Florida): 16
  - Sumter (Florida): 6
  - Volusia (Florida): 2
- **Included counties with 0 rural-eligible tracts:** Seminole (Florida)
- **Explicitly excluded (outside clear 90-min / wrong namesake):**
  - Flagler / Indian River (generally >90 from downtown Orlando — excluded)
- **Uncertain / outer-edge counties (included but flagged in CSV notes):** Marion (Florida), Brevard (Florida)
- **Sources:**
  - Orlando MSA + I-4 / Turnpike / US-27 commute geography
  - Prior Orlando shortlist: /workspace/rural-oz2-orlando.md

## Charleston

- **City center:** Charleston peninsula / King St area (unchanged)
- **Rural-eligible tract count:** **49**
- **Rationale:** Charleston–North Charleston MSA (Berkeley/Charleston/Dorchester) + Colleton/Georgetown clear coastal/I-26 ring. Orangeburg/Clarendon included as I-26 / US-176 outer (~75–95); Williamsburg dropped.
- **Counties included (7):** Berkeley, Charleston, Clarendon, Colleton, Dorchester, Georgetown, Orangeburg
- **Rural-eligible by county:**
  - Berkeley (South Carolina): 9
  - Charleston (South Carolina): 2
  - Clarendon (South Carolina): 2
  - Colleton (South Carolina): 5
  - Dorchester (South Carolina): 4
  - Georgetown (South Carolina): 6
  - Orangeburg (South Carolina): 21
- **Explicitly excluded (outside clear 90-min / wrong namesake):**
  - Williamsburg (Kingstree often ≥90 — excluded)
  - Beaufort (Hilton Head corridor often >90 from peninsula — excluded)
- **Uncertain / outer-edge counties (included but flagged in CSV notes):** Orangeburg (South Carolina), Clarendon (South Carolina), Georgetown (South Carolina)
- **MF priority shortlist inside this shed:** 14 of 49 rural-eligible tracts (Berkeley, Charleston, Colleton, Dorchester, Orangeburg). See `data/sc-oz2-mf-priority-shortlist.md`.
- **Sources:**
  - Charleston–North Charleston MSA
  - Prior Charleston ring: /workspace/rural-oz2-charleston.md (Williamsburg removed for 90-min)

## Nashville

- **City center:** Downtown Nashville (unchanged)
- **Rural-eligible tract count:** **26**
- **Rationale:** Nashville–Davidson–Murfreesboro–Franklin MSA + Clarksville (Montgomery) + Dickson/Maury/Hickman west and Macon/Smith/Cannon northeast rings commonly ≤90 via I-24/I-40/I-65.
- **Counties included (17):** Bedford, Cannon, Cheatham, Davidson, Dickson, Hickman, Macon, Marshall, Maury, Montgomery, Robertson, Rutherford, Smith, Sumner, Trousdale, Williamson, Wilson
- **Rural-eligible by county:**
  - Bedford (Tennessee): 2
  - Cannon (Tennessee): 3
  - Dickson (Tennessee): 1
  - Hickman (Tennessee): 3
  - Macon (Tennessee): 3
  - Marshall (Tennessee): 1
  - Maury (Tennessee): 3
  - Robertson (Tennessee): 4
  - Smith (Tennessee): 1
  - Sumner (Tennessee): 2
  - Wilson (Tennessee): 3
- **Included counties with 0 rural-eligible tracts:** Cheatham (Tennessee), Davidson (Tennessee), Montgomery (Tennessee), Rutherford (Tennessee), Trousdale (Tennessee), Williamson (Tennessee)
- **Explicitly excluded (outside clear 90-min / wrong namesake):**
  - Warren (McMinnville often ~70–95 — excluded as deep SE)
  - DeKalb TN (Smithville outer — excluded)
  - Giles / Lawrence (farther south — excluded)
- **Uncertain / outer-edge counties (included but flagged in CSV notes):** Hickman (Tennessee), Bedford (Tennessee), Macon (Tennessee), Smith (Tennessee), Cannon (Tennessee)
- **Sources:**
  - Nashville–Davidson–Murfreesboro–Franklin MSA county list
  - Prior Nashville ring: /workspace/rural-oz2-nashville.md (Warren/DeKalb dropped)

## Charlotte

- **City center:** Uptown Charlotte (unchanged); includes York/Lancaster SC fringe
- **Rural-eligible tract count:** **60**
- **Rationale:** Charlotte–Concord–Gastonia MSA + adjacent I-77/I-85/US-74 ring. York & Lancaster SC included per brief. Chester SC included (~45–70). NC Union only (not SC Union). Catawba/Cleveland/Anson/Davidson NC as clear ≤90 corridors.
- **Counties included (15):** North Carolina: Anson, Cabarrus, Catawba, Cleveland, Davidson, Gaston, Iredell, Lincoln, Mecklenburg, Rowan, Stanly, Union | South Carolina: Chester, Lancaster, York
- **Rural-eligible by county:**
  - Anson (North Carolina): 4
  - Cabarrus (North Carolina): 1
  - Catawba (North Carolina): 4
  - Cleveland (North Carolina): 9
  - Davidson (North Carolina): 1
  - Gaston (North Carolina): 4
  - Iredell (North Carolina): 10
  - Lincoln (North Carolina): 3
  - Rowan (North Carolina): 2
  - Stanly (North Carolina): 3
  - Union (North Carolina): 1
  - Chester (South Carolina): 10
  - Lancaster (South Carolina): 6
  - York (South Carolina): 2
- **Included counties with 0 rural-eligible tracts:** Mecklenburg (North Carolina)
- **MF priority shortlist inside the SC fringe:** 8 tracts in York, Lancaster, and Chester. North Carolina rows are not on that shortlist.
- **Explicitly excluded (outside clear 90-min / wrong namesake):**
  - Chesterfield SC (often ~75–100 — excluded)
  - Union SC (not the NC Union ring; excluded — different county)
  - Rutherford NC / Fairfield SC (generally >90 — excluded)
- **Uncertain / outer-edge counties (included but flagged in CSV notes):** Anson (North Carolina), Chester (South Carolina), Cleveland (North Carolina), Catawba (North Carolina)
- **Sources:**
  - Charlotte MSA + Charlotte Urban Institute regional commuting framing
  - Prior Charlotte ring: /workspace/rural-oz2-charlotte.md (Chesterfield dropped; SC Union explicitly excluded)
  - Rowan EDC drive-time map context (60-min covers deep into Charlotte labor shed; 90-min extends further)

## Raleigh-Durham

- **City center:** Dual anchors: downtown Raleigh AND downtown Durham (include if ≤90 min of either)
- **Rural-eligible tract count:** **108**
- **Rationale:** Raleigh-Cary + Durham-Chapel Hill MSAs; county included if county seat / primary corridor commonly ≤90 of Raleigh or Durham. Alamance (Burlington) added via I-40/I-85 from Durham. Sampson/Wayne/Wilson kept as SE ring from Raleigh.
- **Counties included (17):** Alamance, Chatham, Durham, Franklin, Granville, Harnett, Johnston, Lee, Nash, Orange, Person, Sampson, Vance, Wake, Warren, Wayne, Wilson
- **Rural-eligible by county:**
  - Chatham (North Carolina): 5
  - Franklin (North Carolina): 11
  - Granville (North Carolina): 5
  - Harnett (North Carolina): 8
  - Johnston (North Carolina): 21
  - Lee (North Carolina): 6
  - Nash (North Carolina): 1
  - Person (North Carolina): 3
  - Sampson (North Carolina): 9
  - Vance (North Carolina): 7
  - Wake (North Carolina): 3
  - Warren (North Carolina): 5
  - Wayne (North Carolina): 11
  - Wilson (North Carolina): 13
- **Included counties with 0 rural-eligible tracts:** Alamance (North Carolina), Durham (North Carolina), Orange (North Carolina)
- **Explicitly excluded (outside clear 90-min / wrong namesake):**
  - Edgecombe / Halifax (generally >90 from both anchors — excluded)
  - Duplin (often >90 — excluded)
- **Uncertain / outer-edge counties (included but flagged in CSV notes):** Sampson (North Carolina), Warren (North Carolina), Wayne (North Carolina), Wilson (North Carolina), Alamance (North Carolina)
- **Sources:**
  - Raleigh-Cary and Durham-Chapel Hill MSA lists
  - Prior RDU ring: /workspace/rural-oz2-raleigh-durham.md (+ Alamance)

---

## Totals

| Market | Rural-eligible GEOIDs |
| --- | ---: |
| Atlanta | 73 |
| Tampa | 66 |
| Orlando | 64 |
| Charleston | 49 |
| Nashville | 26 |
| Charlotte | 60 |
| Raleigh-Durham | 108 |
| **CSV rows (multi-market overlap allowed)** | **446** |
| **Unique GEOIDs** | **424** |

Polk and Sumter (FL) appear under both Tampa and Orlando when within both sheds — intentional for dual-market Land Search Builder use.
