# Zoning and Future Land Use knowledge

These JSON files are the **source of truth** for what the map treats as multifamily-capable. Edit them; do not add a second district list in React components.

| File | Role |
| --- | --- |
| `data/zoning-config.json` | Per-jurisdiction zoning knowledge base (OCPA prefixes, districts, citations, PD/PUD) |
| `data/flu-config.json` | Future Land Use codes → MF-supportive / maybe / no |
| `data/fixtures/parcels.geojson` | Sample parcels, including joined `flu`, `opportunityZone`, and `oz2Eligibility` objects |
| `data/fixtures/opportunity-zones.geojson` | Orange County HUD/Treasury QOZ tract polygons (map overlay). `rural` is Notice 2025-50 membership |
| `data/fixtures/oz-lookup.json` | Generated parcel → designated OZ join audit |
| `data/fixtures/oz2-eligible.geojson` | Orange County tracts eligible for nomination under Rev. Proc. 2026-14 (not designated) |
| `data/oz2-7markets-90min-rural-eligible.csv` | Source table for seven Southeast markets: rural-eligible tracts in approximate 90-minute county rings |
| `data/oz2-7markets-90min-counties.md` | Which counties are inside each shed, and which outer-edge counties are flagged |
| `data/fixtures/oz2-rural-markets.json` | 446 market rows (Polk/Sumter kept on both Tampa and Orlando) plus bounds |
| `data/fixtures/oz2-rural-markets.geojson` | One Census TIGER 2020 polygon per unique rural GEOID |
| `data/oz2-7markets-90min-urban-eligible.csv` | Non-rural eligible tracts for the same seven sheds (1,144 rows, 1,103 GEOIDs) |
| `data/oz2-other-msas-eligible.csv` | Eligible tracts for 15 smaller MSAs (1,386 rows, 1,341 GEOIDs; 491 rural / 895 urban) |
| `data/oz2-other-msas-rural-eligible.csv` | Rural split of the other-MSA pack |
| `data/oz2-other-msas-urban-eligible.csv` | Urban split of the other-MSA pack |
| `data/oz2-other-msas-counties.md` | County rings for the 15 smaller MSAs |
| `data/fixtures/oz2-urban-markets.json` | Urban pack catalog. Status chip is Eligible — not designated |
| `data/fixtures/oz2-other-msas.json` | Other-MSA catalog, rural and urban rows kept |
| `data/fixtures/oz2-eligible-packs.geojson` | One TIGER 2020 polygon per GEOID in the urban pack or the other-MSA pack (2,285) |
| `data/sc-oz2-mf-priority-shortlist.csv` | South Carolina multifamily priority shortlist (Charleston + York/Lancaster/Chester). Eligible rural only |
| `data/sc-oz2-mf-priority-shortlist.md` | Why those 22 tracts are Tier A or Tier B. Not a nominated list |
| `data/fixtures/sc-oz2-mf-priority.json` | Seeded shortlist joined to the rural pack. Chip stays eligible / not designated |
| `data/orlando-parcel-sources.json` | Orlando shed county GIS URLs, field mapping, gaps |
| `data/fixtures/orlando-parcels/` | Partitioned multi-county parcel fixtures (`{fips}.geojson` + `meta.json`) |
| `docs/orlando-parcels.md` | How to refresh Orlando parcels and live viewport API |
| `data/market-parcel-counties.json` | Non-Orlando shed counties and FIPS. Orlando is omitted |
| `data/fixtures/market-parcels/` | Per-county tiles, per-market meta, and `coverage.md` |
| `docs/market-parcels.md` | How to refresh non-Orlando parcels, and which counties are complete, sample, or gaps |
| `data/fixtures/oz2-eligible-tracts.json` | Appendix rows for those tracts, including Rural Status |
| `data/fixtures/oz2-lookup.json` | Generated parcel → OZ 2.0 join audit |
| `data/fixtures/notice-2025-50-rural-geoids.json` | GEOIDs parsed from the Notice 2025-50 rural appendix |
| `data/fixtures/zoning-coverage.json` | Generated coverage report (observed GIS codes vs knowledge files) |

The browser never calls an LLM. Refresh is an offline scripted pass (`npm run seed:zoning`, `npm run seed:flu`, `npm run seed:oz`).

## Zoning config shape

```json
{
  "version": 2,
  "updatedAt": "YYYY-MM-DD",
  "jurisdictions": [
    {
      "code": "ORG",
      "name": "Orange County (unincorporated)",
      "coverage": "verified | partial | unverified",
      "coverageNote": "Honest gap statement",
      "codeSource": { "label": "…", "url": "…" },
      "districts": [
        {
          "token": "R-3",
          "label": "Multiple-Family Dwelling",
          "status": "permitted | conditional | maybe | not-mf",
          "aliases": ["RSTD R-3"],
          "why": "Ordinance/chapter citation",
          "sourceUrl": "https://…"
        }
      ]
    }
  ],
  "plannedDevelopmentTokens": [],
  "notAllowedExamples": []
}
```

Matching rules (implemented in `src/lib/zoning.ts`):

- OCPA codes look like `ORL-R-3B/T/AN`. The app uses the 2–3 letter prefix plus the district before `/`.
- A token matches the same district or a prefix that is not followed by another digit (`R-3` matches `R-3B` only when that token is in **that jurisdiction’s** list; Orlando R-3B is listed explicitly, county R-3 does not leak into Orlando).
- `status: permitted` is the default “Current MF zoning” filter.
- `status: conditional` is Live Local / limited multiplex / mixed commercial. Off unless “include conditional zoning” is on.
- `status: maybe` and all PD/PUD tokens are **maybe — site-specific**. Off unless “include planned development” is on.
- Jurisdictions with `coverage: unverified` and empty `districts` must not invent loopholes.

## FLU config shape

```json
{
  "version": 1,
  "updatedAt": "YYYY-MM-DD",
  "categories": [
    {
      "code": "MD",
      "jurisdiction": "ORG",
      "label": "Medium Density Residential (MDR)",
      "allowsMultifamily": true,
      "status": "yes | maybe | no",
      "maxDensityDuAc": 20,
      "why": "Citation",
      "sourceUrl": "https://…"
    }
  ]
}
```

`code` is the GIS `LAND_USE` / `LANDUSETYPE` value. Overlay suffixes such as `/RES-PRO` fall back to the base code.

## How to refresh

```bash
npm run seed           # parcels + income + AADT, then FLU, designated OZ, OZ 2.0, then coverage report
npm run seed:flu       # re-join FLU onto the existing parcel fixture (network)
npm run seed:oz        # designated QOZ polygons, then OZ 2.0 eligibility and Notice 2025-50 rural flags
npm run seed:oz2       # OZ 2.0 + Notice 2025-50 only (python3 -m pip install pypdf)
npm run seed:oz2-markets  # seven-market rural tracts from the CSV + Census TIGER 2020
npm run seed:sc-mf        # SC multifamily priority shortlist from its CSV
npm run seed:parcels:orlando  # Orange from OCPA; Lake, Osceola, Polk, Seminole from DOH, all 5–150 acres
npm run seed:signals          # ACS tract income + FDOT AADT sidecars joined at query time
npm run seed:parcels:markets  # 5–150 acre tiles for the other MSAs; does not re-scrape Orlando
npm run seed:zoning    # coverage report only; does not scrape Municode
```

After a code amendment:

1. Update the relevant jurisdiction in `zoning-config.json` (token, status, `why` citation).
2. Update `flu-config.json` if GIS codes or density policy changed.
3. Set `updatedAt`.
4. Run `npm run seed:zoning` (and `seed:flu` / `seed:oz` if polygons may have moved).
5. Run `npm test`.

OZ 2.0 refresh (`npm run seed:oz2`) downloads the Rev. Proc. 2026-14 appendix workbook and Notice 2025-50, keeps Orange County eligible rows, and joins Census TIGER 2020 polygons. Rural is the appendix value `Rural` or `Non-rural` only. A designated tract is rural only when its GEOID is in the Notice 2025-50 appendix. If the workbook columns change, or the notice parse is not about 3,309 GEOIDs, the script stops instead of inventing a flag. Install `pypdf` before that refresh. Run it after `join_oz.py` so `designatedRural` is stamped on the designated join.

Seven-market refresh (`npm run seed:oz2-markets`) reads `data/oz2-7markets-90min-rural-eligible.csv` and joins the same TIGER 2020 tract service. It expects 446 rows and 424 unique GEOIDs. It does not fetch parcels. 90-minute sheds in that CSV are approximate county rings, not drive-time isochrones; outer-edge counties stay flagged in `notes`. `--offline` rebuilds the JSON catalog from the CSV and the polygons already saved.

SC multifamily refresh (`npm run seed:sc-mf`) reads `data/sc-oz2-mf-priority-shortlist.csv` and writes `data/fixtures/sc-oz2-mf-priority.json`. Every GEOID must already be rural-eligible in the seven-market CSV, in the same market and county, in South Carolina. The seeded status chip is Eligible (rural) — not designated. The script stops if the CSV status is not the eligible / not designated / not confirmed nominated label.

Do not require a live model in the app to “research zoning.” That is this file plus a future agent/script run.
