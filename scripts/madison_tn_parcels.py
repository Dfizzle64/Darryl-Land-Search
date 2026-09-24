"""Madison County, Tennessee (FIPS 47113) parcel enrich helpers.

Production geometry is GeoJobe AGOL Cadastral/45 Parcels_57 joined to table/46
Cama MadisonTN on GISLINK. Comptroller IMPACT is the official sibling and is
not fetched here (maps.cot.tn.gov often returns 403). gis.cmpdd.org is Madison
County, Mississippi and must not be used.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any
from urllib.parse import quote

GEOJOBE_ORG = "https://services3.arcgis.com/k6aQP9AQncZQEtBv/arcgis/rest/services"
PARCEL_QUERY = f"{GEOJOBE_ORG}/Cadastral/FeatureServer/45/query"
CAMA_QUERY = f"{GEOJOBE_ORG}/Cadastral/FeatureServer/46/query"
JACKSON_ZONING_QUERY = f"{GEOJOBE_ORG}/Zoning/FeatureServer/0/query"
COUNTY_ZONING_QUERY = f"{GEOJOBE_ORG}/PSALayers/FeatureServer/19/query"
JACKSON_FLU_QUERY = f"{GEOJOBE_ORG}/PSALayers/FeatureServer/3/query"
THREE_WAY_FLU_QUERY = f"{GEOJOBE_ORG}/PSALayers/FeatureServer/29/query"

FIPS = "47113"
SOURCE = "tn-impact-47113"
WHERE = "PARCEL_TYPE=1 AND CALC_ACRE>=5 AND CALC_ACRE<=150"
PAGE_SIZE = 2000

CITY_BY_NUM = {
    "359": "Jackson",
    "720": "Three Way",
    "350": "Medon",
}

CAMA_FIELDS = [
    "PARCELID",
    "GISLINK",
    "TAXYR",
    "OWNER",
    "OWNER2",
    "ADDRESS",
    "ST_NUM",
    "STREET",
    "MAILADDR",
    "MAILCITY",
    "STATE",
    "ZIP",
    "MAILLINE1",
    "MAILLINE2",
    "CITYNUM",
    "JUR",
    "ZONING",
    "CAMACALCAC",
    "CAMADEEDAC",
    "LANDVAL",
    "IMPVAL",
    "OBYVAL",
    "APPRAISAL",
    "SALEDATE",
    "PRICE",
    "VI",
    "AR",
    "LANDUSE",
    "PROPTYPE",
    "UPDATED",
]

PARCEL_FIELDS = [
    "OBJECTID",
    "COUNTY_ID",
    "PARCEL_TYPE",
    "GISLINK",
    "CALC_ACRE",
    "CAMA_CALCAC",
    "CAMA_DEEDAC",
    "PARCELWP",
]


def madison_spec() -> dict:
    return {
        "kind": "madison-tn",
        "url": PARCEL_QUERY,
        "where": WHERE,
        "outFields": PARCEL_FIELDS,
        "idField": "GISLINK",
        "acresField": "CALC_ACRE",
        "source": SOURCE,
        "coverage": "complete-gte-5ac",
        "gaps": base_gaps(),
    }


def base_gaps() -> list[str]:
    return [
        "Anonymous production pull is GeoJobe AGOL Cadastral/45 Parcels_57 joined to table/46 Cama MadisonTN on GISLINK. Comptroller IMPACT Parcels (COUNTY_ID=57 / JUR=057) is the official sibling and can 403, so it is not the fetch path.",
        "Acreage band is geometry CALC_ACRE from 5 through 150 with PARCEL_TYPE=1. CAMA calc acres stay on the source row when present and do not set the band.",
        "Owner, mailing, situs, sale, and APPRAISAL come from the latest CAMA row (highest TAXYR, then UPDATED). Official assessed value is on TPAD, not this extract, so assessedValue stays null.",
        "Jackson (CITYNUM 359) zoning is city Zoning/0 Type_ joined onto countywide parcels. County R-* labels on PSALayers/19 are not applied inside Jackson.",
        "Jackson FLU is Civic Master PSALayers/3 HLA_FutLU (includes MF). It is plan guidance, not zoning, and is not applied outside Jackson.",
        "Three Way (CITYNUM 720) zoning prefers PSALayers/19 Type_. FLU is PSALayers/29 LU_TYPE.",
        "Medon (CITYNUM 350) has no public zoning or FLU FeatureServer. FLU is null. Zoning is only a PSALayers/19 hit when the centroid falls in a county district, not a Medon ordinance layer.",
        "Unincorporated Madison (blank CITYNUM) uses PSALayers/19 when the centroid hits. There is no parcel-scale county FLU layer.",
        "gis.cmpdd.org Madison_County_Map / City_of_Jackson is Madison County, Mississippi and is not used.",
        "Appraiser link is the TPAD GIS card https://assessment.cot.tn.gov/TPAD/Parcel/GIS?GISlink={GISLINK}.",
    ]


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def madison_city(citynum: Any) -> str | None:
    return CITY_BY_NUM.get(clean(citynum) or "")


def jurisdiction_code(city: str | None) -> str:
    if city == "Jackson":
        return "JACKSON"
    if city == "Three Way":
        return "THREE WAY"
    if city == "Medon":
        return "MEDON"
    return "UNINCORPORATED"


def parse_mdy(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    parts = text.split("/")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    month, day, year = (int(part) for part in parts)
    if year < 1900 or year > 2100 or month < 1 or month > 12 or day < 1 or day > 31:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def cama_sort_key(attrs: dict) -> tuple[float, str]:
    taxyr = num(attrs.get("TAXYR")) or 0
    updated = parse_mdy(attrs.get("UPDATED")) or ""
    return taxyr, updated


def pick_cama_row(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    return max(rows, key=cama_sort_key)


def tpad_gis_url(gislink: str) -> str:
    return "https://assessment.cot.tn.gov/TPAD/Parcel/GIS?GISlink=" + quote(gislink, safe="")


def situs_address(attrs: dict) -> str | None:
    address = clean(attrs.get("ADDRESS"))
    if address:
        return address
    number = clean(attrs.get("ST_NUM"))
    street = clean(attrs.get("STREET"))
    parts = [part for part in (number, street) if part]
    return " ".join(parts) or None


def sale_qualified(attrs: dict) -> str | None:
    vi = clean(attrs.get("VI"))
    ar = clean(attrs.get("AR"))
    if vi and ar:
        return f"{vi}/{ar}"
    return vi or ar


def positive_money(value: Any) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def point_in_ring(x: float, y: float, ring: list) -> bool:
    if len(ring) < 4:
        return False
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        if (yi > y) != (yj > y):
            denom = yj - yi
            if denom == 0:
                j = i
                continue
            x_cross = (xj - xi) * (y - yi) / denom + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_rings(x: float, y: float, rings: list) -> bool:
    hits = 0
    for ring in rings:
        if point_in_ring(x, y, ring):
            hits += 1
    return hits % 2 == 1


def ring_area(rings: list) -> float:
    area = 0.0
    for ring in rings:
        if len(ring) < 4:
            continue
        part = 0.0
        for i in range(len(ring) - 1):
            x1, y1 = float(ring[i][0]), float(ring[i][1])
            x2, y2 = float(ring[i + 1][0]), float(ring[i + 1][1])
            part += x1 * y2 - x2 * y1
        area += abs(part)
    return area / 2.0


class PolygonIndex:
    """Grid index of district polygons. Overlaps resolve to the smallest ring."""

    def __init__(self, cell: float = 0.03) -> None:
        self.cell = cell
        self.grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.polys: list[tuple[list, str, float]] = []

    def add(self, rings: list, code: str) -> None:
        label = clean(code)
        if not label or not rings:
            return
        idx = len(self.polys)
        area = ring_area(rings)
        self.polys.append((rings, label, area))
        xs = [float(pt[0]) for ring in rings for pt in ring]
        ys = [float(pt[1]) for ring in rings for pt in ring]
        if not xs:
            return
        c = self.cell
        for ix in range(math.floor(min(xs) / c), math.floor(max(xs) / c) + 1):
            for iy in range(math.floor(min(ys) / c), math.floor(max(ys) / c) + 1):
                self.grid[(ix, iy)].append(idx)

    def code_at(self, lon: float, lat: float) -> str | None:
        c = self.cell
        best: str | None = None
        best_area: float | None = None
        for idx in self.grid.get((math.floor(lon / c), math.floor(lat / c)), []):
            rings, label, area = self.polys[idx]
            if not point_in_rings(lon, lat, rings):
                continue
            if best_area is None or area < best_area:
                best = label
                best_area = area
        return best


def flu_info(city: str, code: str | None, source: str) -> dict | None:
    label = clean(code)
    if not label:
        return None
    return {
        "code": label,
        "label": label,
        "jurisdiction": city,
        "source": source,
    }


def medon_gaps() -> list[str]:
    return [
        "Medon has no public zoning or FLU FeatureServer. FLU is null. Any zoning code is a Madison County PSALayers/19 intersection, not a Medon city district.",
    ]


def apply_cama(feature: dict, attrs: dict | None) -> str | None:
    """Fill owner, mailing, situs, sale, and appraisal. Returns the city name."""
    props = feature["properties"]
    gislink = props["parcelId"]
    props["appraiserUrl"] = tpad_gis_url(gislink)
    if not attrs:
        props["jurisdictionCode"] = "UNINCORPORATED"
        return None
    city = madison_city(attrs.get("CITYNUM"))
    props["jurisdictionCode"] = jurisdiction_code(city)
    props["ownerName"] = clean(attrs.get("OWNER"))
    owner2 = clean(attrs.get("OWNER2"))
    if owner2 and owner2 != props["ownerName"]:
        props["ownerName2"] = owner2
    props["situsAddress"] = situs_address(attrs)
    props["situsCity"] = city
    mail1 = clean(attrs.get("MAILADDR")) or clean(attrs.get("MAILLINE1"))
    mail2 = clean(attrs.get("MAILLINE2"))
    if mail2 and mail2 == mail1:
        mail2 = None
    props["mailingAddress"] = {
        "line1": mail1,
        "line2": mail2,
        "city": clean(attrs.get("MAILCITY")),
        "state": clean(attrs.get("STATE")),
        "zip": zip5(attrs.get("ZIP")),
    }
    price = positive_money(attrs.get("PRICE"))
    props["lastSale"] = {
        "date": parse_mdy(attrs.get("SALEDATE")),
        "price": price,
        "qualified": sale_qualified(attrs),
    }
    props["tax"] = {
        "marketValue": positive_money(attrs.get("APPRAISAL")),
        "assessedValue": None,
        "taxableValue": None,
        "taxes": None,
    }
    props["dorCode"] = clean(attrs.get("LANDUSE")) or clean(attrs.get("PROPTYPE"))
    if city == "Medon":
        props["dataGaps"] = medon_gaps()
    return city


def zip5(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return text[:10]


def assign_land_use(
    feature: dict,
    city: str | None,
    *,
    jackson_zoning: str | None,
    county_zoning: str | None,
    jackson_flu: str | None,
    three_way_flu: str | None,
) -> None:
    """Join zoning and FLU only after CITYNUM. Zoning/0 covers rural F-A-R too, so a polygon hit is not a city limit."""
    props = feature["properties"]
    if city == "Jackson":
        props["jurisdictionCode"] = "JACKSON"
        props["zoningCode"] = jackson_zoning
        props["flu"] = flu_info(
            "Jackson",
            jackson_flu,
            "GeoJobe PSALayers/3 Civic Master HLA_FutLU",
        )
        return
    if city == "Three Way":
        props["jurisdictionCode"] = "THREE WAY"
        props["zoningCode"] = county_zoning
        props["flu"] = flu_info(
            "Three Way",
            three_way_flu,
            "GeoJobe PSALayers/29 LU_TYPE",
        )
        return
    if city == "Medon":
        props["jurisdictionCode"] = "MEDON"
        props["zoningCode"] = county_zoning
        props["flu"] = None
        props["dataGaps"] = medon_gaps()
        return
    props["jurisdictionCode"] = "UNINCORPORATED"
    props["zoningCode"] = county_zoning
    props["flu"] = None


def coverage_note(stats: dict) -> str:
    return (
        f"Joined {stats['features']} parcels. "
        f"Owner {stats['owner']}, situs {stats['situs']}, sale {stats['sale']}, appraisal {stats['appraisal']}. "
        f"Jackson zoning {stats['jacksonZoning']} / FLU {stats['jacksonFlu']} "
        f"(MF {stats['jacksonMf']}). "
        f"Three Way zoning {stats['threeWayZoning']} / FLU {stats['threeWayFlu']}. "
        f"Medon parcels {stats['medon']} (county zoning hits {stats['medonZoning']}, FLU {stats['medonFlu']}). "
        f"Unincorporated zoning {stats['unincorpZoning']}."
    )
