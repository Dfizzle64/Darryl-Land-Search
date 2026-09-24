# South Carolina OZ 2.0 — Multifamily Priority Shortlist (Deeper Pass)
## Charleston MSA + Charlotte SC fringe (York / Lancaster / Chester)

**Prepared for:** Darryl Oswald / Land Search Builder  
**As of:** Tuesday, Sep 22, 2026 (ET)  
**Product:** ~220–330 unit garden/wrap multifamily; sites conceptually **5–40 acres**; prefer Rev. Proc. 2026-14 **entirely rural** flag  
**Companion CSV:** `data/sc-oz2-mf-priority-shortlist.csv` (seeded into the map; the UI chip stays **Eligible (rural) — not designated**)

---

## Honest status (read first)

| Fact | Detail |
| --- | --- |
| **SC Commerce (Sep 22, 2026)** | States Governor McMaster **submitted OZ 2.0 nominations to Treasury on Sep 10, 2026** |
| **Nominated GEOID list** | **Not public.** Do **not** treat any tract below as nominated |
| **This shortlist** | **Likelihood / underwriting priority** among **rural-eligible** tracts — not a nominated list |
| **Designation** | Still **not designated**; Treasury certification expected late 2026; zones effective **Jan 1, 2027** |
| **Cap** | SC may nominate ≤**112** of **445** eligible; rural boost is statutory but tract-level outcome unknown until list posts |

**Label used on every row:** *Eligible rural — SC Gov filed statewide Sep 10 2026 / not designated; this GEOID not confirmed nominated.*

Local June 15, 2026 community submissions to SC Commerce were **not published tract-by-tract**. “Nomination-watch” below is an **inference** from corridor growth + scarcity of rural-eligible inventory + typical EDC interest — **not** confirmed loud local GEOID advocacy.

---

## Universe pulled

From `data/oz2-7markets-90min-rural-eligible.csv` (Rev. Proc. 2026-14 Rural = entirely rural):

| Market | Counties | Rural-eligible GEOIDs |
| --- | --- | ---: |
| Charleston | Berkeley, Charleston, Clarendon, Colleton, Dorchester, Georgetown, Orangeburg | **49** |
| Charlotte SC fringe | York, Lancaster, Chester | **18** |
| **Total SC in scope** | | **67** |

**Deprioritized from shortlist (eligible but weak MF thesis):** Georgetown coastal/swamp-heavy; Clarendon outer; Orangeburg west of Holly Hill / deep farm; Francis Marion / Jamestown mega-swamp (e.g. 45015020401); tiny built-out Lancaster/Chester downtown tracts; barrier-island tips.

---

## Ranking logic (Tier A / Tier B)

1. Official **Rural** flag (entirely rural)  
2. Proximity to **I-26 / I-85 / I-77 / US-17 / US-521** corridors  
3. Small-city / exurban growth nodes named in brief (Moncks Corner, Summerville fringe, Goose Creek fringe, Ridgeville, Ravenel–Hollywood, Clover, Rock Hill fringe, Lancaster, Chester)  
4. Tract ALAND large enough that **5–40 ac** pads are plausible (Census Gazetteer — tract-wide, not a site)  
5. Avoid deep swamp-only / barrier-island / pure farm with no sewer story  

**Tier A (10):** chase first for garden/wrap land search  
**Tier B (12):** secondary / watch — still map-worthy  

---

## Tier A — 10 tracts

| GEOID | County | Place / corridor | Acreage realism | Nom-watch* | Why MF-interesting |
| --- | --- | --- | --- | --- | --- |
| **45015020712** | Berkeley | Moncks Corner S–Goose Creek N (US-52 / I-26) | **High** | **High** | Primary Berkeley growth corridor; Charleston job shed |
| **45015020506** | Berkeley | Moncks Corner east | **High** | **High** | Small-city growth; utility-adjacent fringe |
| **45015020504** | Berkeley | Bonneau fringe | **High** | **High** | Central Berkeley pads on US-52 axis |
| **45035010301** | Dorchester | Ridgeville (I-26 / US-78) | **High** | **High** | Inland I-26; Summerville ring; logistics+MF |
| **45019002503** | Charleston | Ravenel–Hollywood (US-17) | **High** | Med | Rare Charleston Co. rural; West Ashley fringe |
| **45091061602** | York | Clover–Lake Wylie fringe | **High** | **High** | Charlotte SW bedroom; York only **2** rural-eligible |
| **45091061601** | York | Clover west | **High** | **High** | Companion Clover west land |
| **45057011001** | Lancaster | Indian Land S–Heath Springs (US-521) | **High** | **High** | US-521 growth south of Indian Land |
| **45015020303** | Berkeley | Huger–Wando / Cainhoy fringe | **High** | Med | Cainhoy master-plan adjacency |
| **45035010302** | Dorchester | N-central Dorchester (I-26) | **High** | Med | Large inland pads; Ridgeville companion |

\*Nom-watch = inferred priority if local govs were active in June input — **not** a confirmed nomination.

### Tier A caveats
- **45019002503:** flood/wetland screening; not barrier island but Lowcountry hydro risk  
- **45015020303 / Cainhoy:** utility extension timing vs master-plan hype  
- **York pair:** high scarcity → land competition if designated; Lake Wylie politics/HOA density limits  

---

## Tier B — 12 tracts

| GEOID | County | Place / corridor | Acreage realism | Nom-watch* | Why MF-interesting |
| --- | --- | --- | --- | --- | --- |
| **45015020201** | Berkeley | Cordesville–Cainhoy fringe | **High** | Med | Very large NE Berkeley; longer horizon |
| **45015020101** | Berkeley | St. Stephen–Cross (I-26 N) | **High** | Med | Land-rich I-26 N; thinner MF comps |
| **45015020202** | Berkeley | St. Stephen / Bonneau west | **High** | Med | US-52 N between St. Stephen & Moncks Corner |
| **45057010500** | Lancaster | Lancaster city fringe | **Med** | **High** | Small-city fringe; denser pad hunt |
| **45057010300** | Lancaster | Heath Springs / US-521 S | **High** | Med | US-521 continuity; thinner retail |
| **45023020700** | Chester | Richburg / I-77 | **High** | Med | I-77 logistics → workforce MF |
| **45023020800** | Chester | Fort Lawn–Richburg (I-77) | **High** | Med | I-77 / SC-9 toward Rock Hill |
| **45019002402** | Charleston | Edisto–Adams Run (US-17) | **Med** | Low | Large land; farther from jobs; flood risk |
| **45035010200** | Dorchester | St. George–Harleyville | **High** | Low | Deep inland I-26; weaker rents |
| **45029970601** | Colleton | Walterboro E (US-17 / I-95) | **High** | Low | Secondary Charleston ring |
| **45075010200** | Orangeburg | Holly Hill / I-26 fringe | **Med** | Low | Outer Orangeburg east only |
| **45023020900** | Chester | Great Falls–Richburg fringe | **Med** | Low | Land-rich; sewer story weak |

---

## Counts by county (shortlist)

| County | Market | Tier A | Tier B | Total |
| --- | --- | ---: | ---: | ---: |
| Berkeley | Charleston | 5 | 2 | **7** |
| Dorchester | Charleston | 2 | 1 | **3** |
| Charleston | Charleston | 1 | 1 | **2** |
| Lancaster | Charlotte | 1 | 2 | **3** |
| York | Charlotte | 2 | 0 | **2** |
| Chester | Charlotte | 0 | 3 | **3** |
| Colleton | Charleston | 0 | 1 | **1** |
| Orangeburg | Charleston | 0 | 1 | **1** |
| **Total** | | **10** | **12** | **22** |

---

## Top 10 one-liners (map these first)

1. **45015020712** — Berkeley / Moncks Corner–Goose Creek (US-52/I-26): #1 Charleston rural MF corridor.  
2. **45035010301** — Dorchester / Ridgeville (I-26/US-78): inland Summerville ring garden sites.  
3. **45091061602** — York / Clover–Lake Wylie: Charlotte SW bedroom; scarce rural inventory.  
4. **45057011001** — Lancaster / US-521 Indian Land south–Heath Springs: Charlotte fringe growth.  
5. **45015020506** — Berkeley / Moncks Corner east: small-city utility-adjacent pads.  
6. **45019002503** — Charleston / Ravenel–Hollywood (US-17): rare county rural on West Ashley fringe.  
7. **45091061601** — York / Clover west: companion to 61602.  
8. **45015020504** — Berkeley / Bonneau fringe: central Berkeley US-52 axis.  
9. **45015020303** — Berkeley / Huger–Wando Cainhoy fringe: master-plan adjacency watch.  
10. **45023020700** — Chester / Richburg I-77: Rock Hill south logistics → workforce MF.

---

## Explicitly not claimed / not chased here

- **The shortlist itself as a nominated list** — nomination is the official 112-GEOID file, not this ranking. A GEOID here is Governor-nominated only when it is also on that file.  
- Georgetown coastal / Francis Marion swamp mega-tracts  
- Barrier islands / Edisto Beach tip  
- Deep Orangeburg west / Clarendon / pure farm with no corridor story  
- Rock Hill / Indian Land **non-rural** eligible cores (outside this rural-only pass)

---

## Caveats for Land Search Builder

1. **Eligible ≠ nominated ≠ certified.** This is a priority list among **67** SC rural-eligible tracts in the two markets.  
2. **Tract ≠ site.** ALAND is Census tract land area, not a developable pad. Need parcel GIS + sewer/water + zoning.  
3. **Rural boost** (~30% basis step-up for qualifying rural OZ investments) is statutory; confirm final regs before underwriting.  
4. **Research only** — no broker outreach, no local FOIA, no assumption of June local rankings.  
5. Revisit the day SC posts the nominated GEOID list; re-filter this shortlist to intersection.

---

## Sources

- IRS Rev. Proc. 2026-14 appendix (Rural = entirely rural), joined through `data/oz2-7markets-90min-rural-eligible.csv`
- 90-min rural-eligible extract: `data/oz2-7markets-90min-rural-eligible.csv`
- Census 2024 Gazetteer internal points (lat/lon on the CSV)  
- SC Commerce OZ page (Sep 10 filing claim; GEOID list not usable as public nominated set): https://www.sccommerce.com/opportunity-zone  
- Prosody Labs OZ monitor (process context): https://prosodylabs.prosodyconsulting.com/projects/oz-monitor/

**Outputs**
- `data/sc-oz2-mf-priority-shortlist.md` (this file)
- `data/sc-oz2-mf-priority-shortlist.csv`
- `data/fixtures/sc-oz2-mf-priority.json` (`npm run seed:sc-mf`)
