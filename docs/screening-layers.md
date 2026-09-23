# Site screening layers

Public map layers for a first look at flood, wetlands, schools, and utilities. They do not change the acreage band or the existing parcel filters. Every toggle starts **off**.

Nothing here is a will-serve letter, a survey, a jurisdictional determination, or an insurance quote. If a market has no public layer, the drawer says **unknown**. It does not invent a provider, a grade, or a phone number.

## What you can turn on

| Layer | Where it draws | Source |
| --- | --- | --- |
| Flood zones | Raster overlay, from about zoom 8 | [FEMA National Flood Hazard Layer](https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer), layer 28 (flood hazard zones). Map export tiles. |
| Wetlands | Raster overlay, from about zoom 11 | [USFWS National Wetlands Inventory](https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer). This is the national layer, so it covers Florida and the other states in the app. The service itself stops drawing past about 1:100,000. |
| Schools | Dots in the current view, plus Orange County attendance-zone tiles | Florida 2025-26 letter grades from the public [Know Your Schools](https://edudata.fldoe.org/ReportCards/Schools.html) report card. The School Grades Excel workbook on fldoe.org returns 403 from many hosts, so this app does not re-download it and does not use a secondary grade list. Orange County zones are live: elementary layer 91, high school layer 90, middle school [InfoMap layer 66](https://ocgis4.ocfl.net/arcgis/rest/services/InfoMap_Public_Layers/MapServer/66). North Carolina 2024-25 grades come from the [DPI researcher file](https://www.dpi.nc.gov/data-reports/school-report-cards/school-report-card-resources-researchers). Other states plot [NCES locations](https://services1.arcgis.com/Ua5sjt3LWTPigjyD/arcgis/rest/services/Public_School_Locations_Current/FeatureServer/0) and link the state report card. Gray means no letter in this extract. |
| Water | Orange County polygons only | [Orange County open data](https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer), layer 60 (`SERVEDBY`). |
| Sewer | Orange County polygons only | Same service, layer 61. |
| Electric | Orange County polygons; HIFLD outside that county | Orange County layer 68 (`COMPANY`) inside the county. Outside it, [HIFLD electric retail service territories](https://services3.arcgis.com/OYP7N6mAJJCyH6hd/ArcGIS/rest/services/Electric_Retail_Service_Territories_HIFLD/FeatureServer/0). Neither is a connection or a will-serve. |
| Gas | No overlay | No public gas service-area layer. The drawer says unknown. |

Selecting a parcel or a tract looks up flood, utilities, and Orange County attendance zones at that point (tracts use the Census internal point) and lists nearby public schools within 3 miles. Flood reads `STATIC_BFE`. The value `-9999` means no published static base flood elevation, and the drawer does not turn that sentinel into a number. Wetlands use a roughly 70-foot box because the NWI service does not answer a bare point.

## Contact

The parcel drawer shows the **owner mailing address already on the parcel extract**. If that address is empty, it says so. It does not look up a phone or an email.

- County property appraiser: Orange County still deep-links the parcel id. Other cataloged Florida counties open that county’s appraiser search. A county that is not cataloged is left as a gap — it is not sent to the Orange County appraiser.
- Entity owners (LLC, Inc, and similar tokens in the assessor name): Florida opens Sunbiz with the name filled in. Georgia, North Carolina, South Carolina, Tennessee, and Alabama open that state’s secretary-of-state search. Georgia, South Carolina, Tennessee, and Alabama do not accept a prefilled name, and the link says so.

## Gaps

- Water and sewer outside Orange County, Florida. No second metro had a public service-area layer that was clearly usable for this pass. Hillsborough County’s utilities folder is geocoding tools, not service areas.
- Gas. Orange County’s open-data map has water, sewer, and electric service areas, and no gas polygon. Other markets do not gain a gas layer either.
- Electric outside Orange County is still the HIFLD retail territory, which can overlap (a downtown Orlando HIFLD query returns more than one utility). Inside Orange County the drawer uses layer 68 instead, which is one service-area company.
- School letter grades are Florida 2025-26 and North Carolina 2024-25 only. Georgia, South Carolina, Tennessee, and Alabama dots link the state report card and do not show a made-up grade.
- An empty FEMA response is **unknown**, not Zone X. An empty NWI hit is “no polygon at this centroid,” not a permit answer.
- There is no “hide floodway” filter. Turning that on would query FEMA for every parcel.

## Refresh

School grades are a server fixture, not a live call on every map move. Locations for non-Florida schools are queried live from NCES.

```bash
npm run seed:schools
```

That reads the Florida report-card API, the NCES CCD directory, and the North Carolina `rcd_acc_spg1.xlsx` file, then writes `data/fixtures/screening/school-ratings.json`. The Florida workbook on fldoe.org blocks a lot of scripted downloads; the script uses the same public report-card API the Know Your Schools page uses. Re-run it when a new grade year is published and update the year strings in `scripts/seed_school_ratings.py` and `src/lib/screening.ts`.

Flood, wetlands, utilities, and NCES locations are live ArcGIS queries (`/api/screening/point`, `/api/screening/schools`, `/api/screening/utilities`). No key. Vector layers wait until the view is about a county wide so a statewide polygon dump never lands in the browser.
