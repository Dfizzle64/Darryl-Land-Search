# North-Central Florida parcels

Market id: `North-Central Florida` (other MSA, after Jacksonville). Acreage band is **5.0–150.0 inclusive**. Sources are public GIS only. Eligible tracts are Rev. Proc. 2026-14 appendix rows and stay **Eligible — not designated**. They are not designated QOZs.

Refresh:

```bash
npm run seed:oz2-eligible
npm run seed:parcels:north-central
```

`seed:parcels:north-central` passes `--refresh` so Hernando and Citrus replace the earlier Florida DOH-only tiles. Those two counties stay on the Tampa list as well. The shared tile files are the upgraded extract. The Orlando sample is not rewritten. Marion parcels were added later by FL-rest batch 1. That pull did not add eligible tracts.

## Eligible tracts

62 rows (39 rural, 23 urban). Gilchrist is in the Gainesville MSA and has **zero** appendix tracts. Do not invent any.

| County | Rows | Rural | Urban | Outer edge |
| --- | ---: | ---: | ---: | --- |
| Alachua | 24 | 1 | 23 | no |
| Hernando | 12 | 12 | 0 | no; also Tampa |
| Citrus | 10 | 10 | 0 | no; also Tampa |
| Putnam | 9 | 9 | 0 | yes |
| Levy | 5 | 5 | 0 | no |
| Bradford | 2 | 2 | 0 | yes |
| Gilchrist | 0 | 0 | 0 | included, no eligible tract |

## Parcels

52,695 stored parcels. Coverage `complete-gte-5ac` means the 5–150 acre roll was queried countywide. It does **not** mean every county has municipal zoning or future land use.

| County | Stored | Source rows | What is joined |
| --- | ---: | ---: | --- |
| Alachua | 15,539 | 15,563 | County Parcels35. Jurisdiction is `JurisNo`, not the mailing city |
| Hernando | 6,601 | 6,601 | County parcels. Upgrade off DOH. Zoning by `PARCEL_KEY` |
| Levy | 10,200 | 10,984 | DOH acreage only. Partial |
| Putnam | 7,560 | 8,810 | DOH polygons plus municipal zoning centroids |
| Gilchrist | 6,395 | 6,854 | DOH acreage only. Partial |
| Citrus | 5,807 | 5,813 | DOH polygons plus corporate limits and county zoning centroids |
| Bradford | 593 | 598 | DOH acreage only. Partial |

### Alachua

Parcels35 (`acres` 5–150). 15,563 source rows, 15,539 stored (22 failed the acreage or extent check and 2 duplicate ids were collapsed). Situs is the AddressPoints join (`FULLADDR`). `Address1` / city / zip on the parcel are the owner mailing address and are not the site address. 4,679 parcels had no address-point hit; their situs is blank rather than the mailing city.

`JurisNo`: 0 unincorporated, 100 Alachua, 200 Archer, 300 Gainesville, 400 Hawthorne, 500 High Springs, 600 LaCrosse, 700 Micanopy, 800 Newberry, 900 Waldo. Stored counts: unincorporated 12,156, Newberry 1,027, Alachua 814, Gainesville 703, High Springs 485, Hawthorne 111, LaCrosse 93, Archer 89, Waldo 41, Micanopy 20. 29 unrecognized `JurisNo` values were left as unincorporated and counted in the gap note.

Zoning and FLU are stored only when `ZONECODE` / `FluCode` starts with the jurisdiction prefix (`0100` county, `0103` Gainesville, same pattern for the other cities). 214 zoning codes failed that prefix check and were left blank. 14,323 parcels have a zoning code; 15,492 have FLU. Gainesville’s separate FLU service needs a token and was not used. Assessed value is not on this layer. `JustValue` is market value. `TaxAmount` is the tax bill when present. Appraiser: https://www.acpafl.org/

### Hernando

Upgrade off Florida DOH layer 25. County Parcels FeatureServer (`ACRES`, owner, situs, `CER_JUST_VALUE`, `CER_ASSESSED_CNTY`, `CER_TAXABLE_CNTY`). `CER_JURISDICTION` `B` is Brooksville (200 parcels) and anything else, including `C`, is unincorporated (6,401). Situs cities Brooksville, Spring Hill, and Weeki Wachee are not the city limit. Spring Hill stays unincorporated. Levy code CWWE is not a municipality.

County zoning joins on `KEY_NUMBER`. The value `CITY` is a placeholder and is not stored. All 200 Brooksville parcels are left without city zoning (174 of those rows were the placeholder). County future land use skips polygons whose FLU code is `city` (the Brooksville hole, not a city FLU map). 5,748 parcels have county zoning and 6,389 have FLU. No public Brooksville or Weeki Wachee zoning service was verified. Appraiser: https://hernandocountypa-florida.us/

### Citrus

DOH EHWATER layer 8 supplies polygons, owner, situs, and tax values (5,813 source rows, 5,807 stored: 3 failed the extent check and 3 duplicate ids were collapsed). County lots have no acre or owner field and `PRCLKEY` is empty, so zoning is a centroid join. Corporate limits are Crystal River and Inverness only. `PHY_CITY` is postal.

Unincorporated 5,633, Crystal River 88, Inverness 86. County zoning and land use values `CITY` are not stored. Inverness zoning is `INV_FLU` and land use is `FLU` on the city layer. Crystal River has no verified zoning or FLU service, so those 88 parcels have neither. 5,588 parcels have a zoning code and 5,585 have FLU. No placeholder `CITY` code was stored. Appraiser: https://www.citruspa.org/

### Putnam

Optional pull. DOH layer 53. 8,810 source rows stored as 7,560 parcels; the drop is duplicate parcel ids, not an acreage filter. The property-appraiser `COMMUNITY` field is Unincorporated on essentially every row and is not used as a municipality.

Municipal zoning is a centroid join to `ReferenceMap/Zoning_R` (Crescent City, Interlachen, Palatka, Pomona Park, Welaka). Stored counts: unincorporated 7,220, Palatka 108, Interlachen 95, Pomona Park 75, Crescent City 40, Welaka 22. Those 340 city parcels have zoning. Unincorporated zoning and future land use returned an error and were not joined. The hosted Palatka FLU service returned HTTP 500, so Palatka FLU is blank. The other cities do not have a verified FLU layer separate from zoning. `PHY_CITY` stays the postal city. Appraiser: https://pa.putnam-fl.com/

### Levy, Gilchrist, and Bradford (partial)

These stay on the Florida DOH 5–150 acre roll. No public municipal boundary, zoning, or future-land-use service was verified, so zoning and FLU are blank and `PHY_CITY` is not treated as a municipality.

| County | Stored | Source rows | Appraiser |
| --- | ---: | ---: | --- |
| Levy | 10,200 | 10,984 | https://www.qpublic.net/fl/levy/ |
| Gilchrist | 6,395 | 6,854 | https://www.qpublic.net/fl/gilchrist/ |
| Bradford | 593 | 598 | https://www.bradfordappraiser.com/ |

Gilchrist still appears in the county menu because the parcel extract exists, even though it has no eligible tract.

## Not in this pull

- The Orlando central sample was not rewritten by this North-Central pull. Marion's 5–150 acre parcels are the later FL-rest batch 1 extract on this same shelf, not a second market listing.
- Placeholder zoning (`CITY`, `MUNICIPAL`, `MUNI`, `CITY LIMITS`, `CITY LIMITS OF INV. OR C.R.`) is never stored.
- City zoning codes are labels. They are not Orange County multifamily districts.
