# Zoning and Future Land Use knowledge

These JSON files are the **source of truth** for what the map treats as multifamily-capable. Edit them; do not add a second district list in React components.

| File | Role |
| --- | --- |
| `data/zoning-config.json` | Per-jurisdiction zoning knowledge base (OCPA prefixes, districts, citations, PD/PUD) |
| `data/flu-config.json` | Future Land Use codes → MF-supportive / maybe / no |
| `data/fixtures/parcels.geojson` | Sample parcels, including joined `flu` objects |
| `data/fixtures/zoning-coverage.json` | Generated coverage report (observed GIS codes vs knowledge files) |

The browser never calls an LLM. Refresh is an offline scripted pass (`npm run seed:zoning`, `npm run seed:flu`).

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
npm run seed           # parcels + income + AADT, then FLU join, then coverage report
npm run seed:flu       # re-join FLU onto the existing parcel fixture (network)
npm run seed:zoning    # coverage report only; does not scrape Municode
```

After a code amendment:

1. Update the relevant jurisdiction in `zoning-config.json` (token, status, `why` citation).
2. Update `flu-config.json` if GIS codes or density policy changed.
3. Set `updatedAt`.
4. Run `npm run seed:zoning` (and `seed:flu` if polygons may have moved).
5. Run `npm test`.

Do not require a live model in the app to “research zoning.” That is this file plus a future agent/script run.
