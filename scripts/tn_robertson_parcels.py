#!/usr/bin/env python3
"""Robertson County, Tennessee (FIPS 47147) 5–150 acre parcels.

IMPACT keys this county as COUNTY_ID 74 / JUR 074. The FIPS suffix 147 is a
different, empty id on the Comptroller layer, which is why the generic
Tennessee spec left Robertson as a gap.

Geometry comes from IMPACT Parcels/0 (parcel type 1). Owner, situs, and
assessment attributes come from Parcel_Layer_Themes/12 joined on GISLINK.
If that attribute service fails, the weekly Comptroller Assessment_Data_074.dbf
is the fallback (local file or a discovered zip). It is not a paid vendor.

Municipal zoning is first-class and wins inside city limits. Unincorporated
land uses the APSU RobertsonZoning overlay. West Virginia's GreenbrierService
and the Pennsylvania Millersville map are rejected.

OZ 2.0 flags are Rev. Proc. 2026-14 nomination eligibility. They are not
designated Qualified Opportunity Zones.
"""

from __future__ import annotations

import json
import struct
import zipfile
from pathlib import Path
from typing import Any

from parcel_geometry import esri_rings_to_geojson, geometry_contains, representative_point

ROOT = Path(__file__).resolve().parents[1]
FIPS = "47147"
COUNTY_ID = 74
JUR = "074"
PARCELS_URL = "https://maps.cot.tn.gov/server3/rest/services/IMPACT/Parcels/FeatureServer/0/query"
THEMES_URL = "https://maps.cot.tn.gov/server3/rest/services/IMPACT/Parcel_Layer_Themes/FeatureServer/12/query"
WHERE = f"COUNTY_ID={COUNTY_ID} AND PARCEL_TYPE=1 AND CALC_ACRE>=5 AND CALC_ACRE<=150"
OZ2_PATH = ROOT / "data" / "fixtures" / "oz2-rural-markets.geojson"
TPAD_URL = "https://assessment.cot.tn.gov/TPAD/"
OZ2_SOURCE = (
    "Rev. Proc. 2026-14 appendix via data/fixtures/oz2-rural-markets.geojson. "
    "Eligible for nomination as a 2027 QOZ. Not nominated and not a designated QOZ."
)

# Wrong-state services that look like Robertson cities in a loose search.
REJECTED_SOURCES = (
    {
        "id": "wv-greenbrier-service",
        "url": "https://services3.arcgis.com/nJbIFHiSnaX0z0hS/arcgis/rest/services/GreenbrierService/FeatureServer",
        "reason": (
            "GreenbrierService is Greenbrier County, West Virginia (magisterial districts, "
            "EPSG:26854). It is not the City of Greenbrier, Tennessee."
        ),
    },
    {
        "id": "pa-millersville-map",
        "url": "https://services1.arcgis.com/2B26wNHYx3IO9pri/arcgis/rest/services/Map/FeatureServer",
        "reason": (
            "This Map service is Millersville, Pennsylvania (Lancaster and Dauphin refugee layers). "
            "It is not the City of Millersville, Tennessee."
        ),
    },
)

GAP_PLACES = ("COOPERTOWN", "CROSS PLAINS", "RIDGETOP", "PORTLAND")

THEME_FIELDS = [
    "GISLINK",
    "OWNER",
    "OWNER2",
    "ADDRESS",
    "CITYNUM",
    "PROPTYPE",
    "APPRAISAL",
    "LANDVAL",
    "PRICE",
    "SALEDATE",
    "SALEYEAR",
    "VI",
    "MAILADDR",
    "MAILCITY",
    "STATE",
    "ZIP",
    "MAILLINE1",
    "MAILLINE2",
    "PARCELID",
    "JUR",
    "COUNTY",
]

CODE_FIELDS = ("Zoning", "ZONING", "ZoneCode", "ZONECLASS", "ZONE_2021", "zone", "zoning", "ZONE")
LABEL_FIELDS = ("ZoneName", "ZONEDESC", "zoning", "Zoning")


def reject_source(url: str) -> None:
    lowered = (url or "").lower()
    if "greenbrierservice" in lowered:
        raise RuntimeError(REJECTED_SOURCES[0]["reason"])
    if "2b26wnhyx3io9pri" in lowered:
        raise RuntimeError(REJECTED_SOURCES[1]["reason"])
    for item in REJECTED_SOURCES:
        if item["url"].lower().rstrip("/") in lowered:
            raise RuntimeError(item["reason"])


def gis_key(value: Any) -> str | None:
    if value is None:
        return None
    text = "".join(str(value).split())
    return text or None


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
    if parsed != parsed:  # NaN
        return None
    return parsed


def zip5(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return None


def parse_sale_date(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 8:
        year, month, day = int(digits[:4]), int(digits[4:6]), int(digits[6:8])
        if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return None


def read_dbf(path: Path) -> list[dict[str, Any]]:
    """Read a dBase III/IV table. Enough for Assessment_Data_074.dbf."""
    data = path.read_bytes()
    if len(data) < 32:
        raise RuntimeError(f"{path} is not a DBF")
    count = struct.unpack_from("<I", data, 4)[0]
    header_len = struct.unpack_from("<H", data, 8)[0]
    record_len = struct.unpack_from("<H", data, 10)[0]
    fields: list[tuple[str, str, int]] = []
    pos = 32
    while pos + 32 <= header_len and data[pos] != 0x0D:
        name = data[pos : pos + 11].split(b"\x00", 1)[0].decode("ascii", "replace").strip()
        kind = chr(data[pos + 11])
        length = data[pos + 16]
        fields.append((name, kind, length))
        pos += 32
    rows: list[dict[str, Any]] = []
    for index in range(count):
        start = header_len + index * record_len
        rec = data[start : start + record_len]
        if len(rec) < record_len or rec[:1] == b"*":
            continue
        cursor = 1
        row: dict[str, Any] = {}
        for name, kind, length in fields:
            raw = rec[cursor : cursor + length]
            cursor += length
            text = raw.decode("latin1", "replace").strip()
            if kind in {"N", "F", "I", "Y"}:
                row[name] = num(text.replace(",", ""))
            else:
                row[name] = text or None
        rows.append(row)
    return rows


def assessment_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map collapsed GISLINK to a theme-shaped attribute row."""
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        upper = {str(key).upper(): value for key, value in row.items()}
        key = gis_key(upper.get("GISLINK") or upper.get("GIS_LINK"))
        if not key:
            continue
        shaped = {
            "GISLINK": upper.get("GISLINK") or upper.get("GIS_LINK"),
            "OWNER": upper.get("OWNER") or upper.get("OWNERNAME") or upper.get("OWNERNME1"),
            "OWNER2": upper.get("OWNER2"),
            "ADDRESS": upper.get("ADDRESS") or upper.get("PROP_ADDR") or upper.get("SITEADDR"),
            "PROPTYPE": upper.get("PROPTYPE") or upper.get("PROPERTYTYPE"),
            "APPRAISAL": upper.get("APPRAISAL") or upper.get("APPRVAL") or upper.get("TOTALAPPR"),
            "LANDVAL": upper.get("LANDVAL") or upper.get("LANDVALUE"),
            "PRICE": upper.get("PRICE") or upper.get("SALEPRICE") or upper.get("SALE_PRICE"),
            "SALEDATE": upper.get("SALEDATE") or upper.get("SALE_DATE") or upper.get("SALEDT"),
            "VI": upper.get("VI"),
            "MAILADDR": upper.get("MAILADDR") or upper.get("MAIL_ADDR") or upper.get("MAILING"),
            "MAILCITY": upper.get("MAILCITY") or upper.get("MAIL_CITY"),
            "STATE": upper.get("STATE") or upper.get("MAILSTATE") or upper.get("MAIL_STATE"),
            "ZIP": upper.get("ZIP") or upper.get("MAILZIP") or upper.get("MAIL_ZIP"),
            "MAILLINE1": upper.get("MAILLINE1"),
            "MAILLINE2": upper.get("MAILLINE2"),
            "JUR": upper.get("JUR"),
        }
        previous = indexed.get(key)
        if previous is None or (not clean(previous.get("OWNER")) and clean(shaped.get("OWNER"))):
            indexed[key] = shaped
    return indexed


def oz2_not_designated(hit: dict | None) -> dict:
    """Nomination eligibility only. Never a designated QOZ."""
    if not hit:
        return {
            "eligible": False,
            "rural": None,
            "tractGeoid": None,
            "tractName": None,
            "designation": "not-eligible",
            "source": OZ2_SOURCE,
        }
    return {
        "eligible": True,
        "rural": True,
        "tractGeoid": hit["tractGeoid"],
        "tractName": hit.get("tractName"),
        "designation": "eligible-for-nomination",
        "source": OZ2_SOURCE,
    }


def _bbox(parts: list) -> tuple[float, float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    area = 0.0
    for poly in parts:
        ring = poly[0]
        for x, y in ring:
            xs.append(x)
            ys.append(y)
        total = 0.0
        for i in range(len(ring) - 1):
            total += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
        area += abs(total) / 2
    return min(xs), min(ys), max(xs), max(ys), area


def prepare_feature(geometry: dict | None, props: dict) -> dict | None:
    if not geometry:
        return None
    parts = []
    if geometry.get("type") == "Polygon":
        parts = [geometry["coordinates"]]
    elif geometry.get("type") == "MultiPolygon":
        parts = list(geometry["coordinates"])
    if not parts or not parts[0] or not parts[0][0]:
        return None
    minx, miny, maxx, maxy, area = _bbox(parts)
    return {"geometry": geometry, "props": props, "bbox": (minx, miny, maxx, maxy), "area": area}


def containing(prepared: list[dict], lon: float, lat: float) -> dict | None:
    best = None
    best_area = None
    for item in prepared:
        minx, miny, maxx, maxy = item["bbox"]
        if lon < minx or lon > maxx or lat < miny or lat > maxy:
            continue
        if not geometry_contains(item["geometry"], lon, lat):
            continue
        if best is None or item["area"] < best_area:
            best = item
            best_area = item["area"]
    return best


def first_attr(attrs: dict, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in attrs:
            text = clean(attrs.get(name))
            if text:
                return text
    lowered = {str(key).lower(): value for key, value in attrs.items()}
    for name in names:
        text = clean(lowered.get(name.lower()))
        if text:
            return text
    return None


def robertson_spec() -> dict:
    return {
        "kind": "robertson",
        "url": PARCELS_URL,
        "where": WHERE,
        "source": f"tn-impact-{FIPS}",
        "coverage": "complete-gte-5ac",
        "countyId": COUNTY_ID,
        "jur": JUR,
    }


def load_oz2_tracts() -> list[dict]:
    if not OZ2_PATH.exists():
        return []
    collection = json.loads(OZ2_PATH.read_text())
    prepared = []
    for feature in collection.get("features") or []:
        props = feature.get("properties") or {}
        geoid = str(props.get("tractGeoid") or "")
        if not geoid.startswith(FIPS):
            continue
        if props.get("designation") != "eligible-for-nomination":
            continue
        item = prepare_feature(
            feature.get("geometry"),
            {"tractGeoid": geoid, "tractName": props.get("name") or props.get("placeOrCorridor")},
        )
        if item:
            prepared.append(item)
    return prepared


def _seed():
    import seed_market_parcels as seed

    return seed


def fetch_layer_polygons(
    query_url: str,
    out_fields: list[str],
    code_fallback: str | None = None,
    extra_code_fields: tuple[str, ...] = (),
    extra_label_fields: tuple[str, ...] = (),
) -> list[dict]:
    reject_source(query_url)
    seed = _seed()
    ids = seed.fetch_object_ids(query_url, "1=1")
    if not ids:
        return []
    raw = seed.fetch_by_ids(query_url, ids, out_fields, batch=80)
    code_names = extra_code_fields + CODE_FIELDS
    label_names = extra_label_fields + LABEL_FIELDS
    prepared = []
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        code = first_attr(attrs, code_names) or code_fallback
        label = first_attr(attrs, label_names) or code
        ready = prepare_feature(geometry, {"code": code, "label": label})
        if ready and ready["props"]["code"]:
            prepared.append(ready)
    return prepared


def fetch_attributes_only(query_url: str, where: str, out_fields: list[str]) -> list[dict]:
    reject_source(query_url)
    seed = _seed()
    ids = seed.fetch_object_ids(query_url, where)
    rows: list[dict] = []
    batch = 250
    for start in range(0, len(ids), batch):
        chunk = ids[start : start + batch]
        data = seed.fetch_json(
            query_url,
            {
                "objectIds": ",".join(str(i) for i in chunk),
                "outFields": ",".join(out_fields),
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=180,
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        for feature in data.get("features") or []:
            rows.append(feature.get("attributes") or {})
        done = min(start + len(chunk), len(ids))
        if done == len(chunk) or done == len(ids) or done % 1000 == 0:
            print(f"    attrs {done}/{len(ids)}", flush=True)
    return rows


def theme_index(rows: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        key = gis_key(row.get("GISLINK"))
        if not key:
            continue
        previous = indexed.get(key)
        if previous is None or (not clean(previous.get("OWNER")) and clean(row.get("OWNER"))):
            indexed[key] = row
    return indexed


def find_assessment_dbf() -> Path | None:
    cache = Path("/tmp/dls-market-parcels")
    direct = cache / "Assessment_Data_074.dbf"
    if direct.exists():
        return direct
    zipped = cache / "Assessment_Data_074.zip"
    if zipped.exists():
        with zipfile.ZipFile(zipped) as archive:
            name = next((item for item in archive.namelist() if item.lower().endswith("assessment_data_074.dbf")), None)
            if not name:
                return None
            cache.mkdir(parents=True, exist_ok=True)
            target = cache / "Assessment_Data_074.dbf"
            target.write_bytes(archive.read(name))
            return target
    return None


def service_layers(service_url: str) -> list[dict]:
    reject_source(service_url)
    seed = _seed()
    data = seed.fetch_json(service_url, {"f": "json"}, timeout=90)
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    return list(data.get("layers") or [])


def load_springfield() -> list[dict]:
    service = "https://services6.arcgis.com/OvhYC4wRuXsRGdB3/arcgis/rest/services/Springfield_Current_Zoning/FeatureServer"
    prepared: list[dict] = []
    for layer in service_layers(service):
        url = f"{service}/{layer['id']}/query"
        fallback = str(layer.get("name") or "").replace("_", "")
        prepared.extend(fetch_layer_polygons(url, ["Zoning"], code_fallback=fallback))
    return prepared


def load_named_layers() -> dict[str, list[dict]]:
    print("  zoning Springfield", flush=True)
    springfield = load_springfield()
    print(f"    {len(springfield)} Springfield polygons", flush=True)
    print("  zoning Greenbrier TN public view", flush=True)
    greenbrier = fetch_layer_polygons(
        "https://services3.arcgis.com/2J1sItLsWSeMbkZB/arcgis/rest/services/Zoning_Public_View/FeatureServer/0/query",
        ["ZoneCode", "ZoneName"],
    )
    print(f"    {len(greenbrier)} Greenbrier polygons", flush=True)
    print("  zoning White House + CompPlan Future_LU", flush=True)
    try:
        white_house = fetch_layer_polygons(
            "https://gis.cityofwhitehouse.com/arcgis/rest/services/WhiteHouseTN_Zoning/FeatureServer/3/query",
            ["ZONECLASS", "ZONEDESC"],
        )
        future = fetch_layer_polygons(
            "https://gis.cityofwhitehouse.com/arcgis/rest/services/WhiteHouseTN_CompPlan/FeatureServer/2/query",
            ["Future_LU"],
            extra_code_fields=("Future_LU",),
        )
        wh_source = "city-server"
    except Exception as exc:  # noqa: BLE001
        print(f"    White House city server failed ({exc}); using AGOL zoning districts", flush=True)
        white_house = fetch_layer_polygons(
            "https://services3.arcgis.com/pFngyvIqq2CUcLpI/arcgis/rest/services/ZoningDistricts/FeatureServer/0/query",
            ["ZONECLASS", "ZONEDESC"],
        )
        future = []
        wh_source = "agol-fallback"
    print(f"    {len(white_house)} White House zoning polygons ({wh_source}), {len(future)} future land use", flush=True)
    print("  zoning Millersville AGOL", flush=True)
    millersville = fetch_layer_polygons(
        "https://services.arcgis.com/jcrrmnzMsBOEAFJp/arcgis/rest/services/Millersville_Zoning_view/FeatureServer/5/query",
        ["ZONE_2021"],
    )
    print(f"    {len(millersville)} Millersville polygons", flush=True)
    print("  APSU communities, Adams, Orlinda, Cedar Hill", flush=True)
    base = "https://apnsgis4.apsu.edu/arcgis/rest/services/Robertson/RobertsonPlanningZoning/MapServer"
    communities = fetch_layer_polygons(f"{base}/5/query", ["name"], extra_code_fields=("name",))
    # Adams/Orlinda keep a legacy class (RA) and a district code (R-40) plus zone_id text.
    adams = fetch_layer_polygons(
        f"{base}/6/query",
        ["zoning_1", "zone_id", "zoning"],
        extra_code_fields=("zoning_1",),
        extra_label_fields=("zone_id",),
    )
    cedar = fetch_layer_polygons(f"{base}/7/query", ["zone", "zoning"])
    orlinda = fetch_layer_polygons(
        f"{base}/8/query",
        ["zoning", "zone_id", "zone"],
        extra_code_fields=("zoning",),
        extra_label_fields=("zone_id",),
    )
    print(
        f"    communities {len(communities)} adams {len(adams)} cedar {len(cedar)} orlinda {len(orlinda)}",
        flush=True,
    )
    return {
        "springfield": springfield,
        "greenbrier": greenbrier,
        "white-house": white_house,
        "white-house-flu": future,
        "white-house-source": wh_source,
        "millersville": millersville,
        "communities": communities,
        "adams": adams,
        "cedar-hill": cedar,
        "orlinda": orlinda,
    }


def load_unincorporated_zoning() -> dict[str, str]:
    print("  APSU RobertsonZoning attributes (unincorporated)", flush=True)
    base = "https://apnsgis4.apsu.edu/arcgis/rest/services/Robertson/RobertsonPlanningZoning/MapServer/9/query"
    rows = fetch_attributes_only(base, "1=1", ["gislink", "zoning"])
    indexed: dict[str, str] = {}
    for row in rows:
        key = gis_key(row.get("gislink") or row.get("GISLINK"))
        code = clean(row.get("zoning") or row.get("ZONING"))
        if key and code and key not in indexed:
            indexed[key] = code
    print(f"    {len(indexed)} unincorporated zoning keys", flush=True)
    return indexed


PLACE_ZONING = {
    "SPRINGFIELD": ("springfield", "SPF", "Springfield"),
    "GREENBRIER": ("greenbrier", "GBR", "Greenbrier"),
    "WHITE HOUSE": ("white-house", "WHT", "White House"),
    "MILLERSVILLE": ("millersville", "MLV", "Millersville"),
    "ADAMS": ("adams", "ADM", "Adams"),
    "ORLINDA": ("orlinda", "ORD", "Orlinda"),
    "CEDAR HILL": ("cedar-hill", "CDH", "Cedar Hill"),
}


def apply_place_and_zoning(
    feature: dict,
    layers: dict,
    unincorporated: dict[str, str],
) -> None:
    props = feature["properties"]
    lon, lat = props["centroid"]
    place_hit = containing(layers["communities"], lon, lat)
    place = clean((place_hit or {}).get("props", {}).get("code") if place_hit else None)
    place_name = (place or "").upper()
    props["situsCity"] = None
    key = gis_key(props["parcelId"])
    if place_name in PLACE_ZONING:
        layer_name, prefix, label = PLACE_ZONING[place_name]
        props["situsCity"] = label
        props["jurisdictionCode"] = prefix
        props["jurisdictionPrefix"] = prefix
        hit = containing(layers[layer_name], lon, lat)
        if hit and hit["props"].get("code"):
            code = hit["props"]["code"]
            district = hit["props"].get("label") or code
            props["zoningCode"] = f"{prefix}-{code}"
            props["zoningDistrict"] = district
        else:
            props["dataGaps"] = [f"No {label} zoning polygon contains this parcel."]
        if place_name == "WHITE HOUSE":
            flu_hit = containing(layers["white-house-flu"], lon, lat)
            if flu_hit and flu_hit["props"].get("code"):
                flu_code = flu_hit["props"]["code"]
                props["flu"] = {
                    "code": flu_code,
                    "label": flu_code,
                    "jurisdiction": "White House",
                    "source": "tn-white-house-compplan-future-lu",
                }
        return
    if place_name in GAP_PLACES:
        label = place_name.title()
        props["situsCity"] = label
        props["jurisdictionCode"] = place_name.replace(" ", "-")
        props["jurisdictionPrefix"] = None
        props["zoningCode"] = None
        props["zoningDistrict"] = None
        props["dataGaps"] = [f"No public zoning polygons for {label}."]
        return
    props["jurisdictionCode"] = "RBC"
    props["jurisdictionPrefix"] = "RBC"
    code = unincorporated.get(key or "")
    if code:
        props["zoningCode"] = f"RBC-{code}"
        props["zoningDistrict"] = code
    else:
        props["dataGaps"] = [
            "Unincorporated parcel has no match on the dated APSU RobertsonZoning overlay."
        ]


def build_features(county: dict, markets: list[str], raw_geom: list[dict], attributes: dict[str, dict]) -> tuple[list[dict], int]:
    seed = _seed()
    spec = {
        "acresField": "CALC_ACRE",
        "idField": "GISLINK",
        "source": f"tn-impact-{FIPS}",
    }
    # Reuse the shared normalizer, then overlay assessment attributes.
    features, dropped = seed.normalize_rows(raw_geom, county, markets, spec)
    for feature in features:
        props = feature["properties"]
        attrs = attributes.get(gis_key(props["parcelId"]) or "", {})
        owner = clean(attrs.get("OWNER"))
        props["ownerName"] = owner
        props["ownerName2"] = clean(attrs.get("OWNER2"))
        props["situsAddress"] = clean(attrs.get("ADDRESS"))
        props["dorCode"] = clean(attrs.get("PROPTYPE"))
        price = num(attrs.get("PRICE"))
        if price is not None and price <= 0:
            price = None
        props["lastSale"] = {
            "date": parse_sale_date(attrs.get("SALEDATE")),
            "price": price,
            "qualified": clean(attrs.get("VI")),
        }
        appraisal = num(attrs.get("APPRAISAL"))
        props["tax"] = {
            "marketValue": appraisal if appraisal and appraisal > 0 else None,
            "assessedValue": None,
            "taxableValue": None,
            "taxes": None,
        }
        props["mailingAddress"] = {
            "line1": clean(attrs.get("MAILLINE1")) or clean(attrs.get("MAILADDR")),
            "line2": clean(attrs.get("MAILLINE2")),
            "city": clean(attrs.get("MAILCITY")),
            "state": clean(attrs.get("STATE")),
            "zip": zip5(attrs.get("ZIP")),
        }
        props["appraiserUrl"] = TPAD_URL
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
    return features, dropped


def join_oz2(features: list[dict], tracts: list[dict]) -> int:
    eligible = 0
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        hit = containing(tracts, lon, lat)
        info = oz2_not_designated(hit["props"] if hit else None)
        feature["properties"]["oz2Eligibility"] = info
        feature["properties"]["opportunityZone"] = None
        if info["eligible"]:
            eligible += 1
    return eligible


def gap_notes(attribute_source: str, layers: dict, counts: dict) -> list[str]:
    wh = "White House city server" if layers.get("white-house-source") == "city-server" else "White House AGOL ZoningDistricts fallback"
    flu = "CompPlan Future_LU joined inside White House." if layers.get("white-house-flu") else "CompPlan Future_LU was not returned by the fallback service."
    return [
        (
            "IMPACT COUNTY_ID 74 / JUR 074. The FIPS suffix 147 returns no parcels on this service. "
            f"Geometry is Parcels/0 parcel type 1, CALC_ACRE 5–150 ({counts['source']} source rows, {counts['kept']} kept). "
            f"Attributes joined from {attribute_source} on GISLINK ({counts['attr']} matches)."
        ),
        (
            "Weekly Assessment_Data_074.dbf is the attribute fallback when Parcel_Layer_Themes/12 is blocked. "
            "The Comptroller ships that table inside the county shapefile from the parcel-data request form; "
            "there is no stable anonymous file URL, and paid parcel vendors are not used. "
            + (
                "This pull used the local Assessment_Data_074.dbf."
                if attribute_source.startswith("Assessment_Data")
                else "This pull used Themes/12, so the DBF was not required."
            )
        ),
        (
            "Municipalities are first-class. City zoning wins inside APSU community limits and is not replaced by county zoning. "
            "Springfield Current Zoning (city AGOL, described as updated 2025-07-15). "
            "Greenbrier, Tennessee Zoning Public View (April 2022): RD is published as Mobile Home Park and R8 as High Density Residential. "
            "West Virginia GreenbrierService (magisterial districts, EPSG:26854) is rejected. "
            f"{wh} zoning. {flu} "
            "Millersville zoning is the city AGOL view Millersville_Zoning_view (ZONE_2021). "
            "The Pennsylvania Millersville map (Lancaster/Dauphin) is rejected. "
            "Adams and Orlinda zoning polygons on the APSU service were last edited 2009-05-06; Cedar Hill zoning is dated 2014-08-04. "
            "Unincorporated zoning is the APSU RobertsonZoning overlay (service description edited 2014-07-30), joined on GISLINK."
        ),
        (
            "No public zoning polygons for Coopertown, Cross Plains, or Ridgetop. "
            "Portland is an incorporated community on the same APSU layer and also has no public zoning service in this pull. "
            "County zoning is not substituted inside those four cities."
        ),
        (
            "OZ 2.0 on these parcels is Rev. Proc. 2026-14 nomination eligibility for four rural Robertson tracts. "
            "Eligible means eligible for nomination, not a designated Qualified Opportunity Zone. "
            "opportunityZone is left unset. This pull does not certify a 2018 or 2027 QOZ."
        ),
    ]


def download_robertson(county: dict, markets: list[str]) -> dict:
    seed = _seed()
    cache_path = seed.CACHE_DIR / f"{FIPS}.json"
    print(f"Pulling Robertson Tennessee ({FIPS}) IMPACT COUNTY_ID={COUNTY_ID} JUR={JUR}", flush=True)
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features:
            print(f"  cache hit {len(features)}", flush=True)
            for feature in features:
                feature["properties"]["marketIds"] = markets
                feature["properties"]["opportunityZone"] = None
            path, lookup, tiles = seed.write_tiles(county, features)
            row = seed.county_row(
                county,
                markets,
                feature_count=len(features),
                coverage="complete-gte-5ac",
                partition="tiles",
                path=path,
                lookup=lookup,
                source=f"tn-impact-{FIPS}",
                query_url=PARCELS_URL,
                gaps=cached.get("gaps") or [],
                source_count=cached.get("sourceCount"),
                dropped=cached.get("dropped"),
                tile_count=tiles,
            )
            _stamp(row, cached.get("places"))
            return row

    expected = seed.count_where(PARCELS_URL, WHERE)
    print(f"  Parcels/0 type-1 5–150 rows {expected}", flush=True)
    if expected <= 0:
        raise RuntimeError("IMPACT Parcels/0 returned no Robertson type-1 parcels in the 5–150 acre band")
    ids = seed.fetch_object_ids(PARCELS_URL, WHERE)
    raw = seed.fetch_by_ids(PARCELS_URL, ids, ["GISLINK", "COUNTY_ID", "PARCEL_TYPE", "CALC_ACRE", "PARCELWP"])
    attribute_source = "Parcel_Layer_Themes/12"
    try:
        print("  Themes/12 attributes", flush=True)
        theme_rows = fetch_attributes_only(THEMES_URL, WHERE, THEME_FIELDS)
        attributes = theme_index(theme_rows)
    except Exception as exc:  # noqa: BLE001
        print(f"  Themes/12 failed ({exc}); trying Assessment_Data_074.dbf", flush=True)
        dbf_path = find_assessment_dbf()
        if not dbf_path:
            raise RuntimeError(
                "Parcel_Layer_Themes/12 failed and Assessment_Data_074.dbf was not in /tmp/dls-market-parcels. "
                "The Comptroller weekly table is the fallback, but the public page is a request form rather than a direct file."
            ) from exc
        attributes = assessment_index(read_dbf(dbf_path))
        attribute_source = "Assessment_Data_074.dbf"
    print(f"  attribute keys {len(attributes)} via {attribute_source}", flush=True)
    features, dropped = build_features(county, markets, raw, attributes)
    if not features:
        raise RuntimeError("Robertson geometry survived no 5–150 acre parcels")
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Robertson emitted a parcel outside 5–150 acres")
    layers = load_named_layers()
    unincorporated = load_unincorporated_zoning()
    tracts = load_oz2_tracts()
    if len(tracts) != 4:
        raise RuntimeError(f"Expected 4 Robertson rural-eligible tracts, found {len(tracts)}")
    matched_attr = 0
    for feature in features:
        if gis_key(feature["properties"]["parcelId"]) in attributes:
            matched_attr += 1
        apply_place_and_zoning(feature, layers, unincorporated)
    eligible = join_oz2(features, tracts)
    for feature in features:
        oz = feature["properties"].get("opportunityZone")
        elig = feature["properties"].get("oz2Eligibility") or {}
        if oz and oz.get("inOpportunityZone"):
            raise RuntimeError("Robertson parcel was marked as a designated QOZ")
        if elig.get("designation") not in {"eligible-for-nomination", "not-eligible"}:
            raise RuntimeError("Robertson OZ 2.0 designation is missing")
        if elig.get("eligible") and elig.get("designation") != "eligible-for-nomination":
            raise RuntimeError("Eligible Robertson tract was stored as designated")
    notes = gap_notes(
        attribute_source,
        layers,
        {"source": expected, "kept": len(features), "attr": matched_attr},
    )
    notes.append(
        f"{eligible} parcels have a centroid in a Rev. Proc. 2026-14 rural-eligible tract. "
        f"{dropped} source rows were dropped for geometry or duplicate ids."
    )
    seed.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {"sourceCount": expected, "dropped": dropped, "features": features, "gaps": notes, "places": sorted(PLACE_ZONING)},
            separators=(",", ":"),
        )
    )
    path, lookup, tiles = seed.write_tiles(county, features)
    print(f"  kept {len(features)} eligible {eligible} tiles {tiles}", flush=True)
    row = seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=f"tn-impact-{FIPS}",
        query_url=PARCELS_URL,
        gaps=notes,
        source_count=expected,
        dropped=dropped,
        tile_count=tiles,
    )
    _stamp(row, sorted(PLACE_ZONING))
    return row


def _stamp(row: dict, places: list | None) -> None:
    """Keep municipality metadata on county.json without changing the shared row writer."""
    path = ROOT / "data" / "fixtures" / "market-parcels" / "counties" / FIPS / "county.json"
    if not path.exists():
        return
    saved = json.loads(path.read_text())
    saved["impactCountyId"] = COUNTY_ID
    saved["impactJur"] = JUR
    saved["parcelType"] = 1
    saved["rejectedSources"] = [{"id": item["id"], "url": item["url"], "reason": item["reason"]} for item in REJECTED_SOURCES]
    saved["municipalities"] = [
        {"name": "Springfield", "prefix": "SPF", "zoning": "public", "vintage": "2025-07-15"},
        {"name": "Greenbrier", "prefix": "GBR", "zoning": "public", "vintage": "2022-04", "note": "RD is Mobile Home Park on the city layer; R8 is High Density Residential."},
        {"name": "White House", "prefix": "WHT", "zoning": "public", "flu": "CompPlan Future_LU"},
        {"name": "Millersville", "prefix": "MLV", "zoning": "public", "note": "AGOL Millersville_Zoning_view"},
        {"name": "Adams", "prefix": "ADM", "zoning": "dated", "vintage": "2009-05-06"},
        {"name": "Orlinda", "prefix": "ORD", "zoning": "dated", "vintage": "2009-05-06"},
        {"name": "Cedar Hill", "prefix": "CDH", "zoning": "dated", "vintage": "2014-08-04"},
        {"name": "Unincorporated Robertson", "prefix": "RBC", "zoning": "dated", "vintage": "2014-07-30"},
        {"name": "Coopertown", "zoning": "gap"},
        {"name": "Cross Plains", "zoning": "gap"},
        {"name": "Ridgetop", "zoning": "gap"},
        {"name": "Portland", "zoning": "gap"},
    ]
    if places:
        saved["sourcedPlaces"] = places
    saved["gaps"] = row.get("gaps") or saved.get("gaps") or []
    path.write_text(json.dumps(saved, indent=2) + "\n")


def _self_test() -> None:
    try:
        reject_source(REJECTED_SOURCES[0]["url"])
        raise SystemExit("WV GreenbrierService was not rejected")
    except RuntimeError as exc:
        if "West Virginia" not in str(exc):
            raise
    try:
        reject_source(REJECTED_SOURCES[1]["url"] + "/0/query")
        raise SystemExit("PA Millersville map was not rejected")
    except RuntimeError as exc:
        if "Pennsylvania" not in str(exc):
            raise
    reject_source(PARCELS_URL)
    square = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }
    prepared = [prepare_feature(square, {"code": "SPRINGFIELD", "label": "Springfield"})]
    assert containing(prepared, 0.5, 0.5) is not None
    assert containing(prepared, 2, 2) is None
    flagged = oz2_not_designated({"tractGeoid": "47147080301", "tractName": "Robertson"})
    assert flagged["eligible"] is True
    assert flagged["designation"] == "eligible-for-nomination"
    assert "designated QOZ" in flagged["source"]
    empty = oz2_not_designated(None)
    assert empty["eligible"] is False and empty["rural"] is None
    # Tiny DBF: one GISLINK / OWNER row.
    fields = [("GISLINK", "C", 8), ("OWNER", "C", 5)]
    header = bytearray(32)
    header[0] = 3
    struct.pack_into("<I", header, 4, 1)
    header_len = 32 + 32 * len(fields) + 1
    record_len = 1 + sum(length for _, _, length in fields)
    struct.pack_into("<H", header, 8, header_len)
    struct.pack_into("<H", header, 10, record_len)
    body = bytearray()
    for name, kind, length in fields:
        desc = bytearray(32)
        desc[: len(name)] = name.encode("ascii")
        desc[11] = ord(kind)
        desc[16] = length
        body += desc
    body.append(0x0D)
    record = bytearray(b" ")
    record += b"07400001"
    record += b"ADAIR"
    payload = bytes(header) + bytes(body) + bytes(record)
    tmp = Path("/tmp/dls-robertson-self.dbf")
    tmp.write_bytes(payload)
    indexed = assessment_index(read_dbf(tmp))
    assert indexed["07400001"]["OWNER"] == "ADAIR"
    assert gis_key("074 001") == "074001"
    assert parse_sale_date("20240115") == "2024-01-15"
    print("tn_robertson_parcels self-test ok")


if __name__ == "__main__":
    import sys

    if "--self-test" in sys.argv:
        _self_test()
    else:
        raise SystemExit("Run from seed_market_parcels.py --county Robertson, or pass --self-test")
