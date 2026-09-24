"""Barrow County, Georgia (FIPS 13013) parcel normalize and overlay joins.

Preferred landbase is BarrowParcelswOwner_Project/FeatureServer/1 (Web Mercator).
GIS acres are Shape__Area / 4046.8564224. There is no deeded-acre field.
Sales and tax are not on the polygon service (qPublic AppID 635 is HTML only).

City Euclidean zoning is joined where the county card marks it usable:
Winder (spatial ZONECLASS), Bethlehem and Carl (PIN). Auburn, Statham, and
Braselton have no city zoning service. FLU is parcel-tied FLU2023, with
Winder 2023 character and usable NEGRC FLU for Statham and Braselton.
Auburn NEGRC FLU is partial and is not applied.

Not used: City of Norwalk CT ParcelViewer (org HfsHDBmkGwb1UtID) and ARC
LandPro as a cadastral substitute.
"""

from __future__ import annotations

import urllib.parse
from typing import Any, Callable

from parcel_geometry import esri_rings_to_geojson, polygon_parts

SQ_M_PER_ACRE = 4046.8564224
MIN_ACRES = 5.0
MAX_ACRES = 150.0

PARCEL_QUERY = (
    "https://services5.arcgis.com/OVFGXfRTCVcPwl55/arcgis/rest/services/"
    "BarrowParcelswOwner_Project/FeatureServer/1/query"
)
ZONING_QUERY = (
    "https://services5.arcgis.com/OVFGXfRTCVcPwl55/arcgis/rest/services/"
    "CurrentZoningDistricts/FeatureServer/0/query"
)
FLU_QUERY = (
    "https://services5.arcgis.com/OVFGXfRTCVcPwl55/arcgis/rest/services/"
    "BCGIS_Zoning_Layers/FeatureServer/137/query"
)
ADDRESS_QUERY = (
    "https://services5.arcgis.com/OVFGXfRTCVcPwl55/arcgis/rest/services/"
    "Address_Points/FeatureServer/0/query"
)
BETHLEHEM_ZONING_QUERY = (
    "https://services5.arcgis.com/OVFGXfRTCVcPwl55/arcgis/rest/services/"
    "Bethlehem_Zoning/FeatureServer/46/query"
)
CARL_ZONING_QUERY = (
    "https://services5.arcgis.com/OVFGXfRTCVcPwl55/arcgis/rest/services/"
    "Carl_Zoning/FeatureServer/0/query"
)
WINDER_ZONING_QUERY = (
    "https://gis.cityofwinder.com/arcgis/rest/services/Jason/Winder_Zoning/FeatureServer/0/query"
)
WINDER_FLU_QUERY = (
    "https://gis.cityofwinder.com/arcgis/rest/services/Jason/2023_Winder_Future_Land_Use/FeatureServer/0/query"
)
STATHAM_FLU_QUERY = (
    "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/"
    "NEGRC_Future_Development_Map_Inventory_WFL1/FeatureServer/5/query"
)
BRASELTON_FLU_QUERY = (
    "https://services1.arcgis.com/Ug5xGQbHsD8zuZzM/arcgis/rest/services/"
    "NEGRC_Future_Development_Map_Inventory_WFL1/FeatureServer/417/query"
)

QPUBLIC_SEARCH = (
    "https://qpublic.schneidercorp.com/Application.aspx?AppID=635&LayerID=11218&PageTypeID=2&PageID=0"
)

# City-name values on CurrentZoningDistricts are stubs, not Euclidean districts.
CITY_ZONING_STUBS = frozenset({"WINDER", "AUBURN", "STATHAM", "BRASELTON", "BETHLEHEM", "CARL"})
CITY_FLU_STUBS = {
    "city of winder": "Winder",
    "city of auburn": "Auburn",
    "city of statham": "Statham",
    "town of braselton": "Braselton",
    "city of braselton": "Braselton",
    "town of bethlehem": "Bethlehem",
    "city of bethlehem": "Bethlehem",
    "town of carl": "Carl",
    "city of carl": "Carl",
}
# Parcel_no prefixes from the county landbase. XX is unincorporated.
PREFIX_CITY = {
    "WN": "Winder",
    "AU": "Auburn",
    "ST": "Statham",
    "BR": "Braselton",
    "BE": "Bethlehem",
    "CA": "Carl",
}
# City FLU layers the card marks usable. Auburn's NEGRC layer is partial.
USABLE_CITY_FLU = frozenset({"Winder", "Statham", "Braselton"})
PARTIAL_CITIES = frozenset({"Auburn", "Statham", "Braselton"})

STREET_TOKENS = frozenset(
    {
        "ST",
        "STREET",
        "RD",
        "ROAD",
        "AVE",
        "AVENUE",
        "DR",
        "DRIVE",
        "LN",
        "LANE",
        "CT",
        "COURT",
        "BLVD",
        "BOULEVARD",
        "HWY",
        "HIGHWAY",
        "WAY",
        "CIR",
        "CIRCLE",
        "TRL",
        "TRAIL",
        "PKWY",
        "PARKWAY",
        "PL",
        "PLACE",
        "TER",
        "TERRACE",
        "LOOP",
        "XING",
        "CROSSING",
        "PATH",
        "RUN",
        "PASS",
        "PT",
        "POINT",
        "SQ",
        "SQUARE",
        "ALY",
        "ALLEY",
        "EXT",
        "EXTENSION",
        "PKY",
    }
)
UNIT_TOKENS = frozenset({"SUITE", "STE", "APT", "UNIT", "BLDG", "BUILDING", "FLOOR", "FL", "BOX", "PO", "PMB"})
_BLANK = frozenset({"NULL", "NONE", "N/A", "NA"})

BASE_FEATURE_GAPS = [
    "Acreage is GIS area from Shape__Area / 4046.8564224 (Web Mercator), not deeded acres.",
    "No sales or tax values on this public layer. qPublic AppID 635 is HTML only.",
]

BARROW_GAPS = [
    "Acreage is GIS area only (BarrowParcelswOwner_Project/FeatureServer/1 Shape__Area / 4046.8564224, Web Mercator). No deeded-acre field is published.",
    "No public sales or tax values on the parcel polygons. qPublic SchneiderCorp AppID=635 LayerID=11218 is HTML only.",
    "County CurrentZoningDistricts Zone is PIN-joined. City-name zones (Winder, Auburn, Statham, Braselton, Bethlehem, Carl) are stubs. City Euclidean zoning is joined for Winder (spatial ZONECLASS), Bethlehem, and Carl (PIN). Auburn, Statham, and Braselton have no city zoning service.",
    "Future land use is parcel-tied FLU2023. Winder 2023 character replaces the City of Winder stub on a centroid hit. Statham and Braselton NEGRC FLU replace those city stubs on a centroid hit. Auburn NEGRC FLU is partial and is not applied. Bethlehem and Carl have no separate city FLU layer.",
    "Situs is joined from Address_Points on Parcel_ID when that field is filled. Post_Comm is the postal community, not the municipality.",
    "Mailing ADDRESS1 is often a co-owner name. The street is ADDRESS2, then ADDRESS3, when ADDRESS1 looks like a person name.",
    "Opportunity Zone and OZ 2.0 designations are not assigned from this county layer.",
    "Rejected lookalikes were not used: City of Norwalk CT ParcelViewer (org HfsHDBmkGwb1UtID) and ARC LandPro as a cadastral substitute.",
]


def barrow_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in _BLANK:
        return None
    return text


def gis_acres(shape_area: Any) -> float | None:
    """Web Mercator square meters to acres, rounded to 4 decimal places."""
    if shape_area is None or shape_area == "":
        return None
    try:
        area = float(shape_area)
    except (TypeError, ValueError):
        return None
    if area <= 0:
        return None
    return round(area / SQ_M_PER_ACRE, 4)


def in_gis_band(acres: float | None) -> bool:
    return acres is not None and MIN_ACRES <= acres <= MAX_ACRES


def _tokens(text: str) -> set[str]:
    cleaned = text.upper().replace(".", " ").replace(",", " ").replace("#", " ")
    return {token for token in cleaned.split() if token}


def looks_like_person_name(value: Any) -> bool:
    """True when a WinGAP address line is a co-owner, not a street or unit."""
    text = barrow_text(value)
    if not text:
        return False
    if any(ch.isdigit() for ch in text):
        return False
    upper = text.upper()
    if upper.startswith("C/O") or upper.startswith("ATTN") or upper.startswith("%"):
        return True
    tokens = _tokens(text)
    if not tokens:
        return False
    if tokens & STREET_TOKENS or tokens & UNIT_TOKENS:
        return False
    return True


def compose_barrow_mailing(address1: Any, address2: Any, address3: Any) -> dict[str, str | None]:
    """Street from ADDRESS2 then ADDRESS3 when ADDRESS1 is a person name.

    Person lines before the first street become ownerName2. A numbered
    ADDRESS1 is the street. Literal NULL placeholders are blank.
    """
    people: list[str] = []
    streets: list[str] = []
    started_street = False
    for raw in (address1, address2, address3):
        line = barrow_text(raw)
        if not line:
            continue
        if looks_like_person_name(line) and not started_street:
            people.append(line)
            continue
        if looks_like_person_name(line):
            continue
        started_street = True
        streets.append(line)
    return {
        "ownerName2": " / ".join(people) if people else None,
        "line1": streets[0] if streets else None,
        "line2": streets[1] if len(streets) > 1 else None,
    }


def apply_barrow_mailing(feature: dict, attrs: dict) -> None:
    mailing = compose_barrow_mailing(attrs.get("ADDRESS1"), attrs.get("ADDRESS2"), attrs.get("ADDRESS3"))
    props = feature["properties"]
    props["ownerName"] = barrow_text(props.get("ownerName"))
    props["ownerName2"] = mailing["ownerName2"]
    props["mailingAddress"] = {
        "line1": mailing["line1"],
        "line2": mailing["line2"],
        "city": barrow_text(attrs.get("CITY")),
        "state": barrow_text(attrs.get("STATE")),
        "zip": _zip(attrs.get("ZIP")),
    }


def _zip(value: Any) -> str | None:
    text = barrow_text(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return None


def parcel_prefix_city(parcel_id: str) -> str | None:
    text = parcel_id.strip().upper()
    for prefix, city in PREFIX_CITY.items():
        if text.startswith(prefix):
            return city
    return None


def is_unincorporated_prefix(parcel_id: str) -> bool:
    return parcel_id.strip().upper().startswith("XX")


def district_label(value: Any) -> str | None:
    """Zone descriptions that are ordinance URLs are not district names."""
    text = barrow_text(value)
    if not text or text.lower().startswith("http://") or text.lower().startswith("https://"):
        return None
    return text


def euclidean_zone(zone: Any) -> str | None:
    text = barrow_text(zone)
    if not text or text.upper() in CITY_ZONING_STUBS:
        return None
    return text


def choose_zoning(county_zone: Any, city_zone: Any) -> str | None:
    """City Euclidean code wins. City-name stubs are not districts."""
    city = euclidean_zone(city_zone)
    if city:
        return city
    return euclidean_zone(county_zone)


def city_flu_overlay(city: str | None, label: Any) -> str | None:
    """Usable city FLU only. Auburn's partial NEGRC layer is refused."""
    if city not in USABLE_CITY_FLU:
        return None
    return barrow_text(label)


def choose_flu(
    county_label: Any,
    county_juris: Any,
    overlay_label: Any,
    overlay_juris: str | None,
    overlay_source: str | None,
) -> dict | None:
    label = barrow_text(overlay_label)
    if label and overlay_source:
        return {
            "code": label,
            "label": label,
            "jurisdiction": overlay_juris,
            "source": overlay_source,
        }
    county = barrow_text(county_label)
    if not county:
        return None
    return {
        "code": county,
        "label": county,
        "jurisdiction": barrow_text(county_juris),
        "source": "barrow-flu2023",
    }


def flu_stub_city(label: Any) -> str | None:
    text = barrow_text(label)
    if not text:
        return None
    return CITY_FLU_STUBS.get(text.lower())


def qpublic_parcel_url(parcel_id: str) -> str:
    return (
        "https://qpublic.schneidercorp.com/Application.aspx?App=BarrowCountyGA"
        "&Layer=Parcels&PageType=Report&KeyValue="
        + urllib.parse.quote(parcel_id.strip())
    )


def barrow_spec() -> dict:
    lo = MIN_ACRES * SQ_M_PER_ACRE
    hi = MAX_ACRES * SQ_M_PER_ACRE
    return {
        "kind": "arcgis",
        "url": PARCEL_QUERY,
        "where": f"Shape__Area>={lo} AND Shape__Area<={hi}",
        "outFields": [
            "Parcel_no",
            "PARCEL_NO_1",
            "LASTNAME",
            "ADDRESS1",
            "ADDRESS2",
            "ADDRESS3",
            "CITY",
            "STATE",
            "ZIP",
            "Shape__Area",
        ],
        "idField": "Parcel_no",
        "idFallbacks": ["PARCEL_NO_1"],
        "acresField": "Shape__Area",
        "acresScale": SQ_M_PER_ACRE,
        "roundAcres": 4,
        "ownerField": "LASTNAME",
        "mailing": "barrow-wingap",
        "enrich": "barrow",
        "source": "ga-barrow-parcels",
        "coverage": "complete-gte-5ac",
        "gaps": list(BARROW_GAPS),
    }


def _attrs(feature: dict) -> dict:
    return feature.get("attributes") or {}


def _index_by(features: list[dict], field: str, prefer: str | None = None) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for feature in features:
        attrs = _attrs(feature)
        key = barrow_text(attrs.get(field))
        if not key:
            continue
        current = indexed.get(key)
        if current is None:
            indexed[key] = attrs
            continue
        if prefer and not barrow_text(current.get(prefer)) and barrow_text(attrs.get(prefer)):
            indexed[key] = attrs
    return indexed


def _point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _contains(geometry: dict, lon: float, lat: float) -> bool:
    for poly in polygon_parts(geometry):
        if not poly or not _point_in_ring(lon, lat, poly[0]):
            continue
        if any(_point_in_ring(lon, lat, hole) for hole in poly[1:]):
            continue
        return True
    return False


class AreaIndex:
    def __init__(self) -> None:
        self.rows: list[tuple[float, float, float, float, dict, dict]] = []

    def add(self, feature: dict, payload: dict) -> None:
        rings = (feature.get("geometry") or {}).get("rings")
        if not rings:
            return
        geometry = esri_rings_to_geojson(rings)
        if not geometry:
            return
        xs: list[float] = []
        ys: list[float] = []

        def walk(coords: Any) -> None:
            if not coords:
                return
            if isinstance(coords[0], (int, float)):
                xs.append(float(coords[0]))
                ys.append(float(coords[1]))
                return
            for part in coords:
                walk(part)

        walk(geometry.get("coordinates"))
        if not xs:
            return
        self.rows.append((min(xs), min(ys), max(xs), max(ys), geometry, payload))

    def find(self, lon: float, lat: float) -> dict | None:
        for minx, miny, maxx, maxy, geometry, payload in self.rows:
            if lon < minx or lon > maxx or lat < miny or lat > maxy:
                continue
            if _contains(geometry, lon, lat):
                return payload
        return None


def page_features(
    fetch_json: Callable[..., dict],
    url: str,
    fields: list[str],
    *,
    geometry: bool,
    label: str,
) -> list[dict]:
    features: list[dict] = []
    offset = 0
    page = 1000
    while True:
        params: dict[str, Any] = {
            "where": "1=1",
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": page,
            "orderByFields": "OBJECTID",
        }
        if geometry:
            params["outSR"] = "4326"
        data = fetch_json(url, params, timeout=180)
        if data.get("error"):
            message = str(data["error"])
            if "orderByFields" in message or "OBJECTID" in message:
                params.pop("orderByFields", None)
                data = fetch_json(url, params, timeout=180)
            if data.get("error"):
                raise RuntimeError(f"{label}: {str(data['error'])[:240]}")
        batch = data.get("features") or []
        features.extend(batch)
        print(f"    {label} {len(features)}", flush=True)
        if not batch:
            break
        if len(batch) < page and not data.get("exceededTransferLimit"):
            break
        offset += len(batch)
        if offset > 250000:
            break
    return features


def _load_layer(
    fetch_json: Callable[..., dict],
    url: str,
    fields: list[str],
    *,
    geometry: bool,
    label: str,
) -> tuple[list[dict] | None, str | None]:
    try:
        return page_features(fetch_json, url, fields, geometry=geometry, label=label), None
    except Exception as exc:  # noqa: BLE001
        print(f"    {label} failed: {exc}", flush=True)
        return None, f"{label} failed and was not joined: {exc}"


def _jurisdiction(
    parcel_id: str,
    inc_muni: str | None,
    flu_juris: str | None,
    city_from_zoning: str | None,
) -> str | None:
    if city_from_zoning:
        return city_from_zoning
    prefixed = parcel_prefix_city(parcel_id)
    if prefixed:
        return prefixed
    muni = barrow_text(inc_muni)
    if muni and muni.upper() not in {"UNINCORPORATED", "BARROW", "BARROW COUNTY"}:
        return muni.title()
    juris = barrow_text(flu_juris)
    if juris and juris.lower() not in {"barrow county", "barrow"}:
        stub = flu_stub_city(juris) or CITY_FLU_STUBS.get(juris.lower())
        if stub:
            return stub
        if juris.lower().startswith("town of ") or juris.lower().startswith("city of "):
            return juris
        return juris
    if (
        is_unincorporated_prefix(parcel_id)
        or (muni and muni.upper() == "UNINCORPORATED")
        or (juris and juris.lower() in {"barrow county", "barrow"})
    ):
        return "Unincorporated"
    return None


def _feature_gaps(city: str | None, zoning: str | None, flu: dict | None, expected_city_zone: bool) -> list[str]:
    gaps = list(BASE_FEATURE_GAPS)
    if city in PARTIAL_CITIES and not zoning:
        gaps.append(
            f"No {city} Euclidean zoning service. The county city-name zone is a stub and is not stored as a district."
        )
    elif expected_city_zone and not zoning and city in {"Winder", "Bethlehem", "Carl"}:
        gaps.append(
            f"{city} has a city zoning layer, but this parcel did not match it. The county city-name stub is not stored as a district."
        )
    if flu and flu.get("source") == "barrow-flu2023" and flu_stub_city(flu.get("label")):
        stub = flu_stub_city(flu.get("label"))
        if stub == "Auburn":
            gaps.append("County FLU is the City of Auburn stub. Auburn NEGRC FLU is partial and was not applied.")
        elif stub in USABLE_CITY_FLU:
            gaps.append(
                f"County FLU is the {flu.get('label')} stub. A city FLU polygon was not hit for this centroid."
            )
    return gaps


def enrich_barrow_features(
    features: list[dict],
    fetch_json: Callable[..., dict],
) -> tuple[dict[str, int], list[str]]:
    """PIN-join county zoning/FLU/situs and usable city overlays. Returns stats and extra gaps."""
    print("  joining Barrow zoning, FLU, situs, and city overlays", flush=True)
    extra_gaps: list[str] = []
    zoning_rows, err = _load_layer(
        fetch_json, ZONING_QUERY, ["Parcel_no", "Zone"], geometry=False, label="county zoning"
    )
    flu_rows, err2 = _load_layer(
        fetch_json,
        FLU_QUERY,
        ["Parcel_no", "FLU2023", "Jurisdicti"],
        geometry=False,
        label="county FLU2023",
    )
    address_rows, err3 = _load_layer(
        fetch_json,
        ADDRESS_QUERY,
        ["Parcel_ID", "StrFullAdd", "Post_Comm", "Post_Code", "Inc_Muni"],
        geometry=False,
        label="address points",
    )
    beth_rows, err4 = _load_layer(
        fetch_json,
        BETHLEHEM_ZONING_QUERY,
        ["Parcel_no", "Zone", "Zone_Description"],
        geometry=False,
        label="Bethlehem zoning",
    )
    carl_rows, err5 = _load_layer(
        fetch_json,
        CARL_ZONING_QUERY,
        ["Parcel_no", "Zone", "Zone_Description"],
        geometry=False,
        label="Carl zoning",
    )
    winder_zone_rows, err6 = _load_layer(
        fetch_json,
        WINDER_ZONING_QUERY,
        ["ZONECLASS", "ZONEDESC"],
        geometry=True,
        label="Winder zoning",
    )
    winder_flu_rows, err7 = _load_layer(
        fetch_json,
        WINDER_FLU_QUERY,
        ["Character"],
        geometry=True,
        label="Winder FLU",
    )
    statham_rows, err8 = _load_layer(
        fetch_json,
        STATHAM_FLU_QUERY,
        ["FDM_Short", "FDM_Long"],
        geometry=True,
        label="Statham NEGRC FLU",
    )
    braselton_rows, err9 = _load_layer(
        fetch_json,
        BRASELTON_FLU_QUERY,
        ["FDM_Short", "FDM_Long"],
        geometry=True,
        label="Braselton NEGRC FLU",
    )
    for err in (err, err2, err3, err4, err5, err6, err7, err8, err9):
        if err:
            extra_gaps.append(err)

    zoning_by_pin = _index_by(zoning_rows or [], "Parcel_no")
    flu_by_pin = _index_by(flu_rows or [], "Parcel_no")
    address_by_pin = _index_by(address_rows or [], "Parcel_ID", prefer="StrFullAdd")
    beth_by_pin = _index_by(beth_rows or [], "Parcel_no")
    carl_by_pin = _index_by(carl_rows or [], "Parcel_no")

    winder_zoning = AreaIndex()
    for row in winder_zone_rows or []:
        zone = euclidean_zone(_attrs(row).get("ZONECLASS"))
        if zone:
            winder_zoning.add(row, {"zone": zone, "description": district_label(_attrs(row).get("ZONEDESC"))})
    winder_flu = AreaIndex()
    for row in winder_flu_rows or []:
        label = barrow_text(_attrs(row).get("Character"))
        if label:
            winder_flu.add(row, {"label": label})
    statham_flu = AreaIndex()
    for row in statham_rows or []:
        label = barrow_text(_attrs(row).get("FDM_Long")) or barrow_text(_attrs(row).get("FDM_Short"))
        if label:
            statham_flu.add(row, {"label": label})
    braselton_flu = AreaIndex()
    for row in braselton_rows or []:
        label = barrow_text(_attrs(row).get("FDM_Long")) or barrow_text(_attrs(row).get("FDM_Short"))
        if label:
            braselton_flu.add(row, {"label": label})

    stats = {
        "zoning": 0,
        "cityZoning": 0,
        "flu": 0,
        "cityFlu": 0,
        "situs": 0,
    }
    for feature in features:
        props = feature["properties"]
        parcel_id = str(props.get("parcelId") or "").strip()
        county_zone_attrs = zoning_by_pin.get(parcel_id) or {}
        county_flu_attrs = flu_by_pin.get(parcel_id) or {}
        address = address_by_pin.get(parcel_id) or {}
        county_zone = county_zone_attrs.get("Zone")
        prefix_city = parcel_prefix_city(parcel_id)
        inc_muni = barrow_text(address.get("Inc_Muni"))

        city_zone = None
        city_zone_name = None
        zoning_description = None
        if parcel_id in beth_by_pin:
            city_zone = beth_by_pin[parcel_id].get("Zone")
            zoning_description = district_label(beth_by_pin[parcel_id].get("Zone_Description"))
            city_zone_name = "Bethlehem"
        elif parcel_id in carl_by_pin:
            city_zone = carl_by_pin[parcel_id].get("Zone")
            zoning_description = district_label(carl_by_pin[parcel_id].get("Zone_Description"))
            city_zone_name = "Carl"
        else:
            lon, lat = props.get("centroid") or [None, None]
            if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
                hit = winder_zoning.find(float(lon), float(lat))
                if hit:
                    city_zone = hit.get("zone")
                    zoning_description = district_label(hit.get("description"))
                    city_zone_name = "Winder"

        zoning = choose_zoning(county_zone, city_zone)
        props["zoningCode"] = zoning
        props["zoningDistrict"] = zoning_description if zoning and city_zone_name else None
        if zoning:
            stats["zoning"] += 1
        if zoning and city_zone_name and euclidean_zone(city_zone):
            stats["cityZoning"] += 1

        jurisdiction = _jurisdiction(
            parcel_id,
            inc_muni,
            county_flu_attrs.get("Jurisdicti"),
            city_zone_name if euclidean_zone(city_zone) else prefix_city,
        )
        props["jurisdictionCode"] = jurisdiction
        props["jurisdictionPrefix"] = parcel_id[:2].upper() if len(parcel_id) >= 2 else None

        overlay_label = None
        overlay_juris = None
        overlay_source = None
        lon, lat = (props.get("centroid") or [None, None])[:2]
        city_for_flu = prefix_city or jurisdiction
        if isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
            if city_for_flu == "Winder" or city_zone_name == "Winder":
                hit = winder_flu.find(float(lon), float(lat))
                label = city_flu_overlay("Winder", (hit or {}).get("label"))
                if label:
                    overlay_label, overlay_juris, overlay_source = label, "Winder", "winder-2023-character"
            elif city_for_flu == "Statham":
                hit = statham_flu.find(float(lon), float(lat))
                label = city_flu_overlay("Statham", (hit or {}).get("label"))
                if label:
                    overlay_label, overlay_juris, overlay_source = label, "Statham", "negrc-statham-flu-2023"
            elif city_for_flu == "Braselton":
                hit = braselton_flu.find(float(lon), float(lat))
                label = city_flu_overlay("Braselton", (hit or {}).get("label"))
                if label:
                    overlay_label, overlay_juris, overlay_source = label, "Braselton", "negrc-braselton-flu-2025"
        flu = choose_flu(
            county_flu_attrs.get("FLU2023"),
            county_flu_attrs.get("Jurisdicti"),
            overlay_label,
            overlay_juris,
            overlay_source,
        )
        props["flu"] = flu
        if flu:
            stats["flu"] += 1
        if flu and flu.get("source") != "barrow-flu2023":
            stats["cityFlu"] += 1

        situs = barrow_text(address.get("StrFullAdd"))
        if situs:
            props["situsAddress"] = situs
            props["situsCity"] = barrow_text(address.get("Post_Comm"))
            props["situsZip"] = _zip(address.get("Post_Code"))
            stats["situs"] += 1

        expected_city_zone = bool(
            prefix_city in {"Winder", "Bethlehem", "Carl"}
            or (barrow_text(county_zone) or "").upper() in {"WINDER", "BETHLEHEM", "CARL"}
        )
        props["appraiserUrl"] = qpublic_parcel_url(parcel_id)
        props["dataGaps"] = _feature_gaps(prefix_city or jurisdiction, zoning, flu, expected_city_zone)
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        props["lastSale"] = {"date": None, "price": None, "qualified": None}
        props["tax"] = {"marketValue": None, "assessedValue": None, "taxableValue": None, "taxes": None}

    print(
        "  joins "
        f"zoning={stats['zoning']} cityZoning={stats['cityZoning']} "
        f"flu={stats['flu']} cityFlu={stats['cityFlu']} situs={stats['situs']}",
        flush=True,
    )
    return stats, extra_gaps
