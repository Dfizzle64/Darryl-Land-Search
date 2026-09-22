# Orlando ~90-minute shed parcels

Public GIS parcel coverage for the nine Orlando drive-shed counties:

**Brevard, Lake, Marion, Orange, Osceola, Polk, Seminole, Sumter, Volusia**

## Architecture (keeps Vercel usable)

| Layer | Role |
| --- | --- |
| `data/fixtures/orlando-parcels/{fips}.geojson` | Partitioned **demo fixtures** (~1 acre+, rural-tract windows). ~1.4k features / ~2.6 MB total — not a multi-GB county dump. |
| `data/orlando-parcel-sources.json` | Per-county source URLs, field mapping, gaps, rejected sources. |
| `GET /api/parcels?market=Orlando&bbox=w,s,e,n` | Viewport / county filter over fixtures (`source=fixture`). |
| `GET /api/parcels?market=Orlando&bbox=…&source=live` | Live DOH EHWATER query by viewport (zoom-aware in the map). |

Orange County keeps the richer OCPA pilot (zoning / FLU / income / AADT). Other counties use Florida DOH EHWATER parcels (FDOR NAL attributes): owner, mailing, sale, just/assessed/taxable values, acreage from `LND_SQFOOT`. **Zoning is absent** on that extract — land-use modes degrade honestly (prefer **All parcels**).

## Refresh

```bash
npm run seed:parcels:orlando
# optional:
python3 scripts/seed_orlando_parcels.py --per-county 200 --min-acres 1.0
python3 scripts/seed_orlando_parcels.py --county Lake
```

Re-pulls public endpoints, simplifies geometries, stamps OZ 2.0 rural-eligible centroids from the seven-market rural pack, and rewrites `data/fixtures/orlando-parcels/`.

## County notes

See `data/orlando-parcel-sources.json` for authoritative URLs. Highlights:

- **Polk** — a public AGOL “Polk_County_Parcels” layer points at Minnesota; do not use. DOH layer 52 is correct.
- **Brevard** — BCPAO MapServer returned 403 here; DOH layer 4 is used.
- **Seminole** — no rural-eligible OZ 2.0 tracts in the pack; parcels still load for shed completeness.
- **Osceola** — St Cloud city layer has zoning but is not county-wide; fixtures use DOH.

## Product behavior

- Market **Orlando** shows shed parcels + rural tract overlays.
- County switcher filters partitions; viewport idle refreshes via `/api/parcels`.
- Other six metros remain tract-only (scaffold OK).
- Filters (acreage, OZ 2.0 rural-eligible, etc.) run on loaded parcels; missing fields use include-unknown toggles.
