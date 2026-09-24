#!/usr/bin/env python3
"""State DOT traffic counts for the Southeast footprint outside Florida.

Florida stays on FDOT RCI FeatureServer/0 (`aadt-segments.geojson`),
field AADT, YEAR_=2025. `scripts/seed_fl_signals.py --aadt-only` refreshes
that sidecar. This script only records which footprint counties it contains.

Every other footprint state uses one verified public statewide layer. Counts
are copied from the published field. Zero and missing values are left out.
Arkansas rows marked Estimated Station, Estimated CCS, or Cross County are
left out. No count is estimated or filled in.

Linework is generalized to about 90 m so the fixture stays one file. The
count, year, and county tag are the published values. The join is still the
nearest segment within 15 km.

  python3 scripts/seed_state_aadt.py
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from parcel_geometry import douglas_peucker

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "data" / "fixtures"
OUT = FIX / "aadt-state-dots.geojson"
SEGMENTS = FIX / "aadt-segments.geojson"
META = FIX / "signals-meta.json"

# About 90 m. Screening joins at 15 km, so this does not invent a count.
LINE_TOLERANCE = 0.0008

# NCDOT station county name -> FIPS. AADT_2022 is a string (HPMS 2022 on AGOL).
# Blank strings are not counts. 2023–2025 station files on NCDOT Connect are not
# on this FeatureServer.
NC = {
    "ALAMANCE": "37001",
    "ANSON": "37007",
    "BRUNSWICK": "37019",
    "BUNCOMBE": "37021",
    "CABARRUS": "37025",
    "CATAWBA": "37035",
    "CHATHAM": "37037",
    "CLEVELAND": "37045",
    "COLUMBUS": "37047",
    "DAVIDSON": "37057",
    "DAVIE": "37059",
    "DUPLIN": "37061",
    "DURHAM": "37063",
    "FORSYTH": "37067",
    "FRANKLIN": "37069",
    "GASTON": "37071",
    "GRANVILLE": "37077",
    "GUILFORD": "37081",
    "HARNETT": "37085",
    "HENDERSON": "37089",
    "IREDELL": "37097",
    "JOHNSTON": "37101",
    "LEE": "37105",
    "LINCOLN": "37109",
    "MECKLENBURG": "37119",
    "NASH": "37127",
    "NEW HANOVER": "37129",
    "ONSLOW": "37133",
    "ORANGE": "37135",
    "PENDER": "37141",
    "PERSON": "37145",
    "RANDOLPH": "37151",
    "ROCKINGHAM": "37157",
    "ROWAN": "37159",
    "SAMPSON": "37163",
    "STANLY": "37167",
    "STOKES": "37169",
    "SURRY": "37171",
    "UNION": "37179",
    "VANCE": "37181",
    "WAKE": "37183",
    "WARREN": "37185",
    "WAYNE": "37191",
    "WILSON": "37195",
    "YADKIN": "37197",
}

# SCDOT CountyName is stored uppercase.
SC = {
    "ABBEVILLE": "45001",
    "ANDERSON": "45007",
    "BEAUFORT": "45013",
    "BERKELEY": "45015",
    "CALHOUN": "45017",
    "CHARLESTON": "45019",
    "CHESTER": "45023",
    "CLARENDON": "45027",
    "COLLETON": "45029",
    "DORCHESTER": "45035",
    "FAIRFIELD": "45039",
    "GEORGETOWN": "45043",
    "GREENVILLE": "45045",
    "GREENWOOD": "45047",
    "JASPER": "45053",
    "KERSHAW": "45055",
    "LANCASTER": "45057",
    "LAURENS": "45059",
    "LEE": "45061",
    "LEXINGTON": "45063",
    "NEWBERRY": "45071",
    "OCONEE": "45073",
    "ORANGEBURG": "45075",
    "PICKENS": "45077",
    "RICHLAND": "45079",
    "SALUDA": "45081",
    "SPARTANBURG": "45083",
    "SUMTER": "45085",
    "YORK": "45091",
}

# GDOT stations republished by DeKalb County GIS. `county` is title case
# (DeKalb, not Dekalb). No year field. Keep aadt > 0. ITOS MapServer/21 is not used.
GA = {
    "Banks": "13011",
    "Barrow": "13013",
    "Bartow": "13015",
    "Bibb": "13021",
    "Bryan": "13029",
    "Bulloch": "13031",
    "Butts": "13035",
    "Carroll": "13045",
    "Catoosa": "13047",
    "Chatham": "13051",
    "Cherokee": "13057",
    "Clarke": "13059",
    "Clayton": "13063",
    "Cobb": "13067",
    "Coweta": "13077",
    "Dade": "13083",
    "Dawson": "13085",
    "DeKalb": "13089",
    "Douglas": "13097",
    "Effingham": "13103",
    "Fayette": "13113",
    "Forsyth": "13117",
    "Fulton": "13121",
    "Gordon": "13129",
    "Gwinnett": "13135",
    "Hall": "13139",
    "Haralson": "13143",
    "Heard": "13149",
    "Henry": "13151",
    "Jackson": "13157",
    "Jasper": "13159",
    "Lamar": "13171",
    "Liberty": "13179",
    "Lowndes": "13185",
    "Lumpkin": "13187",
    "Meriwether": "13199",
    "Monroe": "13207",
    "Morgan": "13211",
    "Newton": "13217",
    "Paulding": "13223",
    "Pickens": "13227",
    "Pike": "13231",
    "Rockdale": "13247",
    "Screven": "13251",
    "Spalding": "13255",
    "Walker": "13295",
    "Walton": "13297",
    "Whitfield": "13313",
}

# TDOT COUNTY_NUMBER is not FIPS. It is the 1-based alphabetical code with
# "Mc" sorted as "Mac", zero-padded. Checked against Census interior points
# on 2026-09-24. Davidson stays 19.
TN = {
    "47001": "01",
    "47003": "02",
    "47009": "05",
    "47011": "06",
    "47013": "07",
    "47015": "08",
    "47021": "11",
    "47029": "15",
    "47037": "19",
    "47043": "22",
    "47047": "24",
    "47057": "29",
    "47063": "32",
    "47065": "33",
    "47081": "41",
    "47089": "45",
    "47093": "47",
    "47097": "49",
    "47103": "52",
    "47105": "53",
    "47111": "56",
    "47113": "57",
    "47115": "58",
    "47117": "59",
    "47119": "60",
    "47121": "61",
    "47125": "63",
    "47129": "65",
    "47143": "72",
    "47145": "73",
    "47147": "74",
    "47149": "75",
    "47153": "77",
    "47155": "78",
    "47157": "79",
    "47159": "80",
    "47165": "83",
    "47167": "84",
    "47169": "85",
    "47173": "87",
    "47187": "94",
    "47189": "95",
}

# Mississippi RCI COUNTYNMBR is not FIPS. It is the 1-based ASCII alphabetical
# county index (1=Adams … 82=Yazoo). HDR AGOL republish of layer RC_AADT_2019,
# field ADT_21. Not an MDOT-hosted FeatureServer.
# Benton 5, Copiah 15, DeSoto 17, George 20, Hinds 25, Madison 45, Marshall 47,
# Rankin 61, Simpson 64, Tate 69, Tunica 72, Warren 75, Yazoo 82.
MS = {
    "28009": 5,
    "28029": 15,
    "28033": 17,
    "28039": 20,
    "28049": 25,
    "28089": 45,
    "28093": 47,
    "28121": 61,
    "28127": 64,
    "28137": 69,
    "28143": 72,
    "28149": 75,
    "28163": 82,
}

# ALDOT TDM LUCountyID is not FIPS. It is the 1-based alphabetical code with
# "St. Clair" sorted as "Saint Clair". Checked at Census interior points and
# against 2024 station descriptions (Shelby 59, Tuscaloosa 63, Walker 64,
# Washington 65). YearAADT=2024 is the latest year with a populated AADT
# (2025 rows are null).
AL = {
    "01001": 1,
    "01003": 2,
    "01007": 4,
    "01009": 5,
    "01021": 11,
    "01043": 22,
    "01051": 26,
    "01053": 27,
    "01063": 32,
    "01065": 33,
    "01071": 36,
    "01073": 37,
    "01083": 42,
    "01085": 43,
    "01089": 45,
    "01095": 48,
    "01097": 49,
    "01101": 51,
    "01103": 52,
    "01107": 54,
    "01115": 58,
    "01117": 59,
    "01121": 61,
    "01125": 63,
    "01127": 64,
    "01129": 65,
}

# ARDOT County is the 1-based alphabetical code. Crittenden 18 and Mississippi
# 47 were checked at Census interior points. Only these two counties are in
# the footprint.
AR = {"05035": 18, "05093": 47}

# FDOT RCI COUNTY names (Title Case; DeSoto is Desoto).
FL = {
    "12001": "Alachua",
    "12003": "Baker",
    "12005": "Bay",
    "12007": "Bradford",
    "12009": "Brevard",
    "12015": "Charlotte",
    "12017": "Citrus",
    "12019": "Clay",
    "12021": "Collier",
    "12027": "DeSoto",
    "12029": "Dixie",
    "12031": "Duval",
    "12033": "Escambia",
    "12039": "Gadsden",
    "12041": "Gilchrist",
    "12043": "Glades",
    "12049": "Hardee",
    "12051": "Hendry",
    "12053": "Hernando",
    "12055": "Highlands",
    "12057": "Hillsborough",
    "12061": "Indian River",
    "12065": "Jefferson",
    "12071": "Lee",
    "12073": "Leon",
    "12075": "Levy",
    "12079": "Madison",
    "12081": "Manatee",
    "12085": "Martin",
    "12089": "Nassau",
    "12091": "Okaloosa",
    "12093": "Okeechobee",
    "12095": "Orange",
    "12097": "Osceola",
    "12101": "Pasco",
    "12103": "Pinellas",
    "12105": "Polk",
    "12107": "Putnam",
    "12109": "St. Johns",
    "12111": "St. Lucie",
    "12113": "Santa Rosa",
    "12115": "Sarasota",
    "12119": "Sumter",
    "12123": "Taylor",
    "12127": "Volusia",
    "12129": "Wakulla",
    "12131": "Walton",
}

SOURCES = {
    "FL": {
        "agency": "FDOT",
        "field": "AADT",
        "year": 2025,
        "url": "https://gis.fdot.gov/arcgis/rest/services/RCI_Layers/FeatureServer/0",
        "crs": "EPSG:26917",
        "yearField": "YEAR_",
    },
    "NC": {
        "agency": "NCDOT",
        "field": "AADT_2022",
        "year": 2022,
        "url": "https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0",
        "valueType": "string",
        "vintage": "HPMS 2022 on the FeatureServer. NCDOT Connect 2023/2024/2025 station files are not ingested.",
    },
    "GA": {
        "agency": "GDOT",
        "field": "aadt",
        "year": None,
        "url": "https://services2.arcgis.com/IxVN2oUE9EYLSnPE/arcgis/rest/services/GDOT_AADT/FeatureServer/1",
        "countyField": "county",
        "host": "DeKalb County GIS AGOL republish",
        "layer": "GDOT_sites_join",
        "vintage": "No year field. AGOL item last modified 2026-05-07. Year is unknown.",
        "geometry": "points",
    },
    "SC": {
        "agency": "SCDOT",
        "field": "FactoredAA",
        "year": 2025,
        "yearField": "FactoredA1",
        "countyField": "CountyName",
        "url": "https://services1.arcgis.com/VaY7cY9pvUYUP1Lf/arcgis/rest/services/2025_Statewide_Traffic_Points/FeatureServer/0",
        "geometry": "points",
        "statewideCount": 11570,
    },
    "TN": {
        "agency": "TDOT",
        "field": "AADT",
        "yearField": "AADTYEAR",
        "url": "https://services2.arcgis.com/nf3p7v7Zy4fTOh6M/arcgis/rest/services/Traffic_Lines/FeatureServer/0",
    },
    "MS": {
        "agency": "Mississippi RCI",
        "field": "ADT_21",
        "year": 2021,
        "layer": "RC_AADT_2019",
        "host": "HDR AGOL republish",
        "url": "https://services.arcgis.com/04HiymDgLlsbhaV4/arcgis/rest/services/Mississippi_RCI/FeatureServer/3",
        "countyField": "COUNTYNMBR",
    },
    "AL": {
        "agency": "ALDOT",
        "field": "AADT",
        "year": 2024,
        "url": "https://aldotgis.dot.state.al.us/pubgis2/rest/services/EGISATDServices/TDMPublic/MapServer/0",
    },
    "AR": {
        "agency": "ARDOT",
        "field": "MostRecentADT",
        "yearField": "Year_ADT",
        "url": "https://gis.ardot.gov/referenced/rest/services/SIR_TIS/Average_Daily_Traffic_Points/MapServer/0",
        "kept": "Comment = Actual Station",
    },
}


def fetch_json(url: str, params: dict, timeout: int = 180) -> dict:
    full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": "darryl-land-search/state-aadt"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed {url[:80]}: {last}")


def simplify_line(path: list) -> list[list[float]]:
    pts = [(float(x), float(y)) for x, y in path]
    if len(pts) > 2:
        pts = douglas_peucker(pts, LINE_TOLERANCE)
    slim: list[list[float]] = []
    for x, y in pts:
        pair = [round(x, 4), round(y, 4)]
        if not slim or pair != slim[-1]:
            slim.append(pair)
    if len(slim) >= 2:
        return slim
    if not pts:
        return []
    mid = pts[len(pts) // 2]
    lon, lat = round(mid[0], 4), round(mid[1], 4)
    return [[lon, lat], [lon, lat]]


def as_count(value) -> int | None:
    if isinstance(value, str):
        value = value.strip()
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0 or number > 500_000:
        return None
    return int(round(number))


def as_year(value) -> int | None:
    try:
        year = int(float(value))
    except (TypeError, ValueError):
        return None
    return year if 1990 <= year <= 2026 else None


def line_features(item: dict, props: dict) -> list[dict]:
    paths = (item.get("geometry") or {}).get("paths") or []
    out = []
    for path in paths[:1]:
        line = simplify_line(path)
        if len(line) < 2:
            continue
        out.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": line}, "properties": props})
    return out


def point_feature(item: dict, attrs: dict, props: dict) -> dict | None:
    geom = item.get("geometry") or {}
    x = geom.get("x")
    y = geom.get("y")
    if x is None or y is None:
        x = attrs.get("Longitude")
        if x is None:
            x = attrs.get("Longtitude_Use")
        y = attrs.get("Latitude")
        if y is None:
            y = attrs.get("Latitude_Use")
    if x is None or y is None:
        return None
    lon, lat = round(float(x), 5), round(float(y), 5)
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[lon, lat], [lon, lat]]},
        "properties": props,
    }


def page_query(url: str, params: dict, label: str, on_batch=None) -> list[dict]:
    features: list[dict] = []
    offset = 0
    page_size = int(params.get("resultRecordCount") or 2000)
    while offset < 400_000:
        data = fetch_json(url, {**params, "resultOffset": offset, "f": "json"})
        if data.get("error"):
            raise RuntimeError(data["error"])
        batch = data.get("features") or []
        if not batch:
            break
        if on_batch:
            on_batch(batch)
        else:
            features.extend(batch)
        offset += len(batch)
        if offset == len(batch) or offset % 10000 < page_size:
            print(f"    {label} {offset}", flush=True)
        if len(batch) < page_size and not data.get("exceededTransferLimit"):
            break
        time.sleep(0.05)
    return features


def props(aadt: int, year: int | None, roadway: str | None, agency: str, state: str, fips: str) -> dict:
    kept = {
        "aadt": aadt,
        "agency": agency,
        "state": state,
        "countyFips": fips,
    }
    if year is not None:
        kept["year"] = year
    if roadway:
        kept["roadwayId"] = roadway
    return kept


def fetch_nc() -> list[dict]:
    url = "https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services/NCDOT_AADT_Stations/FeatureServer/0/query"
    names = "','".join(sorted(NC))
    rows = page_query(
        url,
        {
            "where": f"COUNTY IN ('{names}')",
            "outFields": "FID,COUNTY,AADT_2022,ROUTE",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultRecordCount": 1000,
        },
        "NC",
    )
    out = []
    seen = set()
    for item in rows:
        attrs = item.get("attributes") or {}
        oid = attrs.get("FID")
        if oid in seen:
            continue
        seen.add(oid)
        raw_count = attrs.get("AADT_2022")
        count = as_count(raw_count.strip() if isinstance(raw_count, str) else raw_count)
        fips = NC.get(str(attrs.get("COUNTY") or "").strip().upper())
        if count is None or not fips:
            continue
        feature = point_feature(item, attrs, props(count, 2022, attrs.get("ROUTE") or None, "NCDOT", "North Carolina", fips))
        if feature:
            out.append(feature)
    print(f"  NC stations {len(out)}")
    return out


def fetch_sc() -> list[dict]:
    url = "https://services1.arcgis.com/VaY7cY9pvUYUP1Lf/arcgis/rest/services/2025_Statewide_Traffic_Points/FeatureServer/0/query"
    names = "','".join(sorted(SC))
    rows = page_query(
        url,
        {
            "where": f"CountyName IN ('{names}')",
            "outFields": "CountyName,FactoredAA,FactoredA1,OBJECTID",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultRecordCount": 2000,
        },
        "SC",
    )
    out = []
    seen = set()
    for item in rows:
        attrs = item.get("attributes") or {}
        oid = attrs.get("OBJECTID")
        if oid in seen:
            continue
        seen.add(oid)
        count = as_count(attrs.get("FactoredAA"))
        fips = SC.get(str(attrs.get("CountyName") or "").strip().upper())
        if count is None or not fips:
            continue
        feature = point_feature(
            item,
            attrs,
            props(count, as_year(attrs.get("FactoredA1")) or 2025, None, "SCDOT", "South Carolina", fips),
        )
        if feature:
            out.append(feature)
    print(f"  SC points {len(out)}")
    return out


def fetch_tn() -> list[dict]:
    url = "https://services2.arcgis.com/nf3p7v7Zy4fTOh6M/arcgis/rest/services/Traffic_Lines/FeatureServer/0/query"
    reverse = {code: fips for fips, code in TN.items()}
    quoted = "','".join(sorted(reverse))
    out: list[dict] = []
    seen: set = set()

    def consume(batch: list[dict]) -> None:
        for item in batch:
            attrs = item.get("attributes") or {}
            oid = attrs.get("OBJECTID")
            if oid in seen:
                continue
            seen.add(oid)
            count = as_count(attrs.get("AADT"))
            code = str(attrs.get("COUNTY_NUMBER") or "").zfill(2)
            fips = reverse.get(code)
            if count is None or not fips:
                continue
            out.extend(line_features(item, props(count, as_year(attrs.get("AADTYEAR")), None, "TDOT", "Tennessee", fips)))

    page_query(
        url,
        {
            "where": f"COUNTY_NUMBER IN ('{quoted}') AND AADT>0",
            "outFields": "COUNTY_NUMBER,AADT,AADTYEAR,OBJECTID",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultRecordCount": 2000,
        },
        "TN",
        consume,
    )
    print(f"  TN segments {len(out)}")
    return out


def fetch_ms() -> list[dict]:
    """One county at a time.

    Rows with ADT_21 > 0 and a null shape are omitted. They cannot be joined
    to a parcel centroid. A combined COUNTYNMBR IN (...) page is not used.
    """
    url = "https://services.arcgis.com/04HiymDgLlsbhaV4/arcgis/rest/services/Mississippi_RCI/FeatureServer/3/query"
    out: list[dict] = []
    seen: set = set()
    for fips, code in sorted(MS.items(), key=lambda item: item[1]):
        before = len(out)

        def consume(batch: list[dict], fips: str = fips) -> None:
            for item in batch:
                attrs = item.get("attributes") or {}
                oid = attrs.get("OBJECTID")
                if oid in seen:
                    continue
                seen.add(oid)
                count = as_count(attrs.get("ADT_21"))
                if count is None:
                    continue
                out.extend(line_features(item, props(count, 2021, None, "Mississippi RCI", "Mississippi", fips)))

        page_query(
            url,
            {
                "where": f"COUNTYNMBR={code} AND ADT_21>0 AND Shape IS NOT NULL",
                "outFields": "COUNTYNMBR,ADT_21,OBJECTID",
                "returnGeometry": "true",
                "outSR": 4326,
                "orderByFields": "OBJECTID",
                "resultRecordCount": 2000,
            },
            f"MS {fips}",
            consume,
        )
        counted = fetch_json(
            url,
            {
                "where": f"COUNTYNMBR={code} AND ADT_21>0 AND Shape IS NOT NULL",
                "returnCountOnly": "true",
                "f": "json",
            },
        )
        expected = int(counted.get("count") or 0)
        got = len(out) - before
        print(f"  MS {fips} COUNTYNMBR={code} {got}/{expected}")
        if got != expected:
            raise RuntimeError(f"MS {fips} COUNTYNMBR={code} kept {got}, layer reports {expected}")
    print(f"  MS segments {len(out)}")
    return out


def fetch_al() -> list[dict]:
    url = "https://aldotgis.dot.state.al.us/pubgis2/rest/services/EGISATDServices/TDMPublic/MapServer/0/query"
    reverse = {code: fips for fips, code in AL.items()}
    nums = ",".join(str(code) for code in sorted(reverse))
    rows = page_query(
        url,
        {
            "where": f"YearAADT=2024 AND AADT>0 AND LUCountyID IN ({nums})",
            "outFields": "TrafficCounterDetailID,LUCountyID,AADT,YearAADT,Station,Longitude,Latitude",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultRecordCount": 1000,
        },
        "AL",
    )
    out = []
    seen = set()
    for item in rows:
        attrs = item.get("attributes") or {}
        oid = attrs.get("TrafficCounterDetailID")
        if oid in seen:
            continue
        seen.add(oid)
        count = as_count(attrs.get("AADT"))
        try:
            code = int(attrs.get("LUCountyID") or 0)
        except (TypeError, ValueError):
            code = 0
        fips = reverse.get(code)
        if count is None or not fips:
            continue
        feature = point_feature(
            item,
            attrs,
            props(count, as_year(attrs.get("YearAADT")) or 2024, attrs.get("Station") or None, "ALDOT", "Alabama", fips),
        )
        if feature:
            out.append(feature)
    print(f"  AL stations {len(out)}")
    return out


def fetch_ar() -> list[dict]:
    url = "https://gis.ardot.gov/referenced/rest/services/SIR_TIS/Average_Daily_Traffic_Points/MapServer/0/query"
    reverse = {code: fips for fips, code in AR.items()}
    nums = ",".join(str(code) for code in sorted(reverse))
    rows = page_query(
        url,
        {
            "where": f"County IN ({nums}) AND MostRecentADT>0 AND Comment='Actual Station'",
            "outFields": "OBJECTID,County,MostRecentADT,Year_ADT,Route,Comment,Latitude_Use,Longtitude_Use",
            "returnGeometry": "true",
            "outSR": 4326,
            "resultRecordCount": 1000,
        },
        "AR",
    )
    out = []
    seen = set()
    for item in rows:
        attrs = item.get("attributes") or {}
        if attrs.get("Comment") != "Actual Station":
            continue
        oid = attrs.get("OBJECTID")
        if oid in seen:
            continue
        seen.add(oid)
        count = as_count(attrs.get("MostRecentADT"))
        year = as_year(attrs.get("Year_ADT"))
        try:
            code = int(attrs.get("County") or 0)
        except (TypeError, ValueError):
            code = 0
        fips = reverse.get(code)
        if count is None or year is None or not fips:
            continue
        feature = point_feature(item, attrs, props(count, year, attrs.get("Route") or None, "ARDOT", "Arkansas", fips))
        if feature:
            out.append(feature)
    print(f"  AR actual stations {len(out)}")
    return out


def fetch_ga() -> list[dict]:
    """DeKalb GIS republish of GDOT stations. Year is not on the layer."""
    url = "https://services2.arcgis.com/IxVN2oUE9EYLSnPE/arcgis/rest/services/GDOT_AADT/FeatureServer/1/query"
    names = "','".join(sorted(GA))
    by_name = {name.casefold(): fips for name, fips in GA.items()}
    out: list[dict] = []
    seen: set = set()

    def consume(batch: list[dict]) -> None:
        for item in batch:
            attrs = item.get("attributes") or {}
            oid = attrs.get("OBJECTID")
            if oid in seen:
                continue
            seen.add(oid)
            count = as_count(attrs.get("aadt"))
            # One DeKalb station is stored as "Dekalb". Match county names case-insensitively.
            fips = by_name.get(str(attrs.get("county") or "").strip().casefold())
            if count is None or not fips:
                continue
            station = str(attrs.get("name") or "").strip() or None
            feature = point_feature(item, attrs, props(count, None, station, "GDOT", "Georgia", fips))
            if feature:
                out.append(feature)

    page_query(
        url,
        {
            "where": f"county IN ('{names}') AND aadt>0",
            "outFields": "aadt,county,name,OBJECTID",
            "returnGeometry": "true",
            "outSR": 4326,
            "orderByFields": "OBJECTID",
            "resultRecordCount": 2000,
        },
        "GA",
        consume,
    )
    for name, fips in sorted(GA.items()):
        counted = fetch_json(
            url,
            {"where": f"county='{name}' AND aadt>0", "returnCountOnly": "true", "f": "json"},
        )
        expected = int(counted.get("count") or 0)
        got = sum(1 for feature in out if feature["properties"]["countyFips"] == fips)
        print(f"  GA {fips} {name} {got}/{expected}")
        if got != expected:
            raise RuntimeError(f"GA {fips} {name} kept {got}, layer reports {expected}")
    print(f"  GA stations {len(out)}")
    return out


def _norm_county(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def stamp_florida() -> dict[str, int]:
    """Count existing FDOT 2025 segments for each footprint county. No refetch."""
    if not SEGMENTS.exists():
        raise RuntimeError(f"Missing {SEGMENTS}")
    data = json.loads(SEGMENTS.read_text())
    by_norm = {_norm_county(name): fips for fips, name in FL.items()}
    counts: dict[str, int] = {}
    for feature in data.get("features") or []:
        props_ = feature.get("properties") or {}
        fips = by_norm.get(_norm_county(str(props_.get("county") or "")))
        if not fips or as_count(props_.get("aadt")) is None:
            continue
        counts[fips] = counts.get(fips, 0) + 1
    missing = [fips for fips in FL if fips not in counts]
    if missing:
        raise RuntimeError(f"FDOT RCI sidecar has no segments for {missing}")
    print(f"  FL footprint counties {len(counts)} segments {sum(counts.values())}")
    return counts


def coverage_notes() -> list[str]:
    return [
        "Florida AADT is FDOT RCI FeatureServer/0 (gis.fdot.gov), field AADT, YEAR_=2025, for every footprint county including Orange and Hillsborough. The service is EPSG:26917; the fixture requested outSR 4326. Nearest segment to the parcel centroid within 15 km.",
        "North Carolina uses NCDOT AADT Stations, field AADT_2022. That field is a string; blanks are trimmed and dropped. The FeatureServer is still HPMS 2022. NCDOT Connect publishes 2023, 2024, and 2025 station files that are not on this REST layer, so they are not ingested.",
        "South Carolina uses SCDOT 2025 Statewide Traffic Points, field FactoredAA, year FactoredA1 2025, filtered by CountyName. The layer has 11,570 stations statewide. Charleston, Dorchester, Berkeley, and Beaufort stay on this same layer. The 2025 lines layer is not used.",
        "Mississippi uses the HDR AGOL republish of Mississippi RCI layer RC_AADT_2019, field ADT_21 (counts through 2021). COUNTYNMBR is the alphabetical county number, not FIPS. This is not an MDOT-hosted FeatureServer. The MDOT 2025 traffic-count application has no public FeatureServer. Segments with ADT_21 of zero, or with no shape, are left out.",
        "Georgia uses the DeKalb County GIS republish of GDOT stations (GDOT_AADT FeatureServer/1), field aadt, including Bibb, Cobb, DeKalb, Fulton, and Lowndes. The layer has no year field, so the year is unknown. ITOS MapServer/21 is not used. "
        "Alabama uses ALDOT TDM TrafficCounterPoint, field AADT, YearAADT=2024. 2025 rows are present and AADT is null. LUCountyID is the alphabetical county index with St. Clair sorted as Saint Clair, not FIPS. "
        "Tennessee COUNTY_NUMBER and Mississippi COUNTYNMBR and Alabama LUCountyID are alphabetical county codes, not FIPS. "
        "Arkansas keeps Comment = Actual Station only. Estimated Station, Estimated CCS, and Cross County rows are omitted. "
        "Line geometry is generalized to about 90 m. Counts are the published values.",
        "A parcel more than 15 km from the nearest count stays unknown. Outside Florida the drawer label is Nearest AADT, not FDOT.",
    ]


def apply_state_meta(features: list[dict], fl_counts: dict[str, int] | None = None) -> None:
    by_fips: dict[str, int] = {}
    for feature in features:
        fips = feature["properties"]["countyFips"]
        by_fips[fips] = by_fips.get(fips, 0) + 1
    ga_deferred = [
        {
            "fips": fips,
            "state": "GA",
            "reason": "GDOT_AADT FeatureServer/1 returned no station with aadt greater than 0 for this county. No count was estimated.",
        }
        for fips in sorted(GA.values())
        if fips not in by_fips
    ]
    meta = json.loads(META.read_text()) if META.exists() else {}
    notes = [
        note
        for note in (meta.get("notes") or [])
        if not any(
            marker in note
            for marker in ("AADT", "FDOT", "FactoredAA", "ADT_21", "HPMS 2022", "statewide segments")
        )
    ]
    notes.extend(coverage_notes())
    update = {
        "stateAadtSource": "SE footprint state DOT layers, 2026-09-24",
        "stateAadtCount": len(features),
        "stateAadtByCounty": dict(sorted(by_fips.items())),
        "stateAadtSources": SOURCES,
        "aadtDeferred": ga_deferred,
        "notes": notes,
    }
    if fl_counts is not None:
        update["flAadtByCounty"] = dict(sorted(fl_counts.items()))
    meta.update(update)
    META.write_text(json.dumps(meta, indent=2) + "\n")


def require_counts(features: list[dict], expected: dict | set, label: str) -> None:
    found = {feature["properties"]["countyFips"] for feature in features}
    missing = [fips for fips in expected if fips not in found]
    if missing:
        raise RuntimeError(f"{label} returned no counts for {missing}")


def refresh_mississippi() -> None:
    """Replace Mississippi features only. Other states stay in the fixture."""
    print("MS")
    ms = fetch_ms()
    require_counts(ms, MS, "MS")
    data = json.loads(OUT.read_text())
    kept = [
        feature
        for feature in data.get("features") or []
        if (feature.get("properties") or {}).get("state") != "Mississippi"
    ]
    data["features"] = kept + ms
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    apply_state_meta(data["features"])
    print(f"replaced Mississippi with {len(ms)} segments; fixture {len(data['features'])}")


def main() -> None:
    import sys

    if "--only" in sys.argv:
        which = sys.argv[sys.argv.index("--only") + 1].upper()
        if which == "MS":
            refresh_mississippi()
            return
        if which == "GA":
            print("GA")
            ga = fetch_ga()
            require_counts(ga, GA.values(), "GA")
            data = json.loads(OUT.read_text())
            kept = [
                feature
                for feature in data.get("features") or []
                if (feature.get("properties") or {}).get("state") != "Georgia"
            ]
            data["features"] = kept + ga
            OUT.write_text(json.dumps(data, separators=(",", ":")))
            apply_state_meta(data["features"])
            print(f"replaced Georgia with {len(ga)} stations; fixture {len(data['features'])}")
            return
        raise SystemExit("Only --only MS or --only GA is supported. A full run rebuilds every state.")
    print("NC")
    nc = fetch_nc()
    require_counts(nc, NC.values(), "NC")
    print("SC")
    sc = fetch_sc()
    require_counts(sc, SC.values(), "SC")
    print("TN")
    tn = fetch_tn()
    require_counts(tn, TN, "TN")
    print("MS")
    ms = fetch_ms()
    require_counts(ms, MS, "MS")
    print("AL")
    al = fetch_al()
    require_counts(al, AL, "AL")
    print("AR")
    ar = fetch_ar()
    require_counts(ar, AR, "AR")
    print("GA")
    ga = fetch_ga()
    require_counts(ga, GA.values(), "GA")
    features = nc + sc + tn + ms + al + ar + ga
    if len(features) < 1000:
        raise RuntimeError(f"State DOT download returned only {len(features)} counts")
    OUT.write_text(
        json.dumps(
            {"type": "FeatureCollection", "name": "state-dot-aadt-se-footprint", "features": features},
            separators=(",", ":"),
        )
    )
    print("FL sidecar")
    fl_counts = stamp_florida()
    apply_state_meta(features, fl_counts)
    print(f"wrote {len(features)} counts, {OUT.stat().st_size} bytes")
    for fips in (
        "37119",
        "37183",
        "37063",
        "13121",
        "13067",
        "13089",
        "13185",
        "13021",
        "45019",
        "45035",
        "45015",
        "45013",
        "47037",
        "28049",
        "28089",
        "28121",
    ):
        if fips not in by_fips:
            raise RuntimeError(f"Lost previously live county {fips}")


if __name__ == "__main__":
    main()
