# AL Statewide AADT — ALDOT TDM Public (2026-09-24)

| Item | Value |
|---|---|
| Status | **usable** |
| Source | ALDOT official (`EGISATDServices/TDMPublic`) |
| REST | `https://aldotgis.dot.state.al.us/pubgis2/rest/services/EGISATDServices/TDMPublic/MapServer/0` |
| Layer name | TrafficCounterPoint |
| Layer ID | 0 |
| Geometry | point |
| Auth | none (public Query) |
| AADT field | `AADT` (integer) |
| Year field | `YearAADT` (2014–2025 present) |
| County filter | `LUCountyID` (1–67 alphabetical AL county index; not FIPS) |
| Feature count | **282,482** total (multi-year); **~23,731** per year shell; **~22,009** with `AADT>0` for **2024** |
| Latest usable year | **2024** (2025 station shells exist but `AADT` still null as of dig) |
| Viewer | https://aldotgis.dot.state.al.us/TDMPublic/ |

## Probe notes

- Host: `aldotgis.dot.state.al.us/pubgis2` — official ALDOT ArcGIS Server.
- Folder `EGISATDServices` exposes `TDMPublic` MapServer (traffic) and `TDMPublicBasemap`.
- Layer 0 returns full TDM attributes including `AADT`, `YearAADT`, `Station`, `RouteID`, `Description`, truck factors (`TADT`, `SUTADT`, `CUTADT`), growth rates, lat/lon.
- Prefer filter `YearAADT=2024` for current AADT; do **not** use 2025 until AADT values populate.
- Optional county subset via `LUCountyID` (examples: Autauga=1, Baldwin=2, Blount=5, Elmore=26, Escambia=27, Jefferson=37, Limestone=42, Madison=45, Marshall=48, Mobile=49, Montgomery=51, Morgan=52, St. Clair=58, Shelby=60, Tuscaloosa=64, Walker=65, Washington=66).
- `ATD_Services` folder empty; `Roads/EGISRoutes` is route geometry only (no AADT). `TSI_Services` are traffic-signal inventory, not AADT.
- Rejected false lead: AGOL `services3.arcgis.com/u6Nvh8zpOQRNNRJi/.../AADT/FeatureServer` is **NCDOT** (NC State Plane / NCDOT description), not Alabama.
- No separate statewide AADT shapefile/CSV download confirmed on aldot.gov this pass; REST layer is the canonical join source.

## Cards stamped (county only)

Statewide `enrichment.aadt` block added to all existing AL county YAMLs (17):

- 01001-autauga, 01003-baldwin, 01009-blount, 01051-elmore, 01053-escambia
- 01073-jefferson, 01083-limestone, 01089-madison, 01095-marshall, 01097-mobile
- 01101-montgomery, 01103-morgan, 01115-st-clair, 01117-shelby, 01125-tuscaloosa
- 01127-walker, 01129-washington

City cards intentionally **not** stamped (statewide join lives on county cards).

`verifiedAt: 2026-09-24` · `verifiedBy: Alabama Public Info Researcher`
