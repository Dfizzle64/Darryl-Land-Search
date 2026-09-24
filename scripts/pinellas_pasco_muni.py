#!/usr/bin/env python3
"""Join Pinellas and Pasco city zoning and FLU onto parcels already on the shelf.

Does not download county parcel polygons. St. Petersburg, Clearwater, Tampa,
Temple Terrace, and Plant City stay on the layers already joined. Largo keeps
its future land use and does not get a zoning code invented from mowing layers.

  python3 scripts/pinellas_pasco_muni.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import tampa_shed as shed

ROOT = Path(__file__).resolve().parents[1]
COUNTY_DIR = ROOT / "data" / "fixtures" / "market-parcels" / "counties"
PCGIS = "https://services.arcgis.com/f5HgUpxURgEzTccH/arcgis/rest/services"

# County boxes are tight enough that Hernando, Anderson County CA, and Gulfport MS fail.
COUNTY_BOX = {
    "12103": (-82.95, 27.55, -82.55, 28.25),
    "12101": (-82.95, 28.05, -81.90, 28.55),
}
MAX_CITY_SPAN = 0.35
STUB_CODES = {"NPR", "PR", "SA", "DC", "ZH"}

NAMESAKE_REJECTS = [
    "Rejected namesake: AGOL Zoning_Flu (Weeki Wachee situs, Hernando County FIPS 12053), not Pinellas or Pasco.",
    "Rejected namesake: AGOL Zoning_view zone_code R1-8 (centroid about -122.31, 40.46, Anderson County, California).",
    "Rejected namesake: maps.gulfport-ms.gov GPT_Zoning (Gulfport, Mississippi), not Gulfport, Florida.",
    "Pasco county ZN_TYPE values NPR, PR, SA, DC, and ZH are city placeholders, not district maps.",
]
PINELLAS_REJECTS = [
    *NAMESAKE_REJECTS,
    "Pinellas unincorporated Landuse_Zoning is not used as a city district map.",
    "Pinellas Countywide Plan Map categories are not stored as a city future land use map.",
]
PASCO_REJECTS = [
    *NAMESAKE_REJECTS,
    "Zephyrhills traditional city center zoning (Zhills_EnGov_Map_11_2025/3) is a second citywide map and is not stacked on the Euclidean layer.",
]

STRIP_GAPS = {
    "No verified public zoning/FLU layer for this Pinellas municipality. Unincorporated layers were not applied.",
    "Inside a Pasco city. County district polygons and NPR/PR/SA placeholders were not applied.",
    "St. Petersburg and Clearwater have city zoning and FLU. Largo has FLU only. Other Pinellas municipalities have no verified zoning/FLU layer.",
    "New Port Richey, Port Richey, San Antonio, Dade City, Zephyrhills, and St. Leo have no verified public city zoning/FLU FeatureServer.",
    "City zoning polygon did not intersect this parcel.",
    "City future land use polygon did not intersect this parcel.",
    "City future land use polygon did not intersect this parcel. The county parcel-attribute land-use hint was kept.",
    "City zoning polygon did not intersect this parcel. The parcel-attribute hint was kept and is not an official district.",
    "Zoning is the Pinellas County GIS city zoning view. City future land use is not published here. The countywide plan map was not stored as a city FLUM.",
    "County zoning code was a city placeholder (NPR, PR, SA, DC, or ZH) and was not stored as a district.",
}

PARTIAL_FLU_GAP = (
    "Zoning is the Pinellas County GIS city zoning view. City future land use is not published here. "
    "The countywide plan map was not stored as a city FLUM."
)


def id_key(value: Any) -> str | None:
    text = shed.clean(value)
    if not text:
        return None
    if text.endswith(".0") and text[:-2].replace("-", "").isdigit():
        text = text[:-2]
    key = "".join(ch for ch in text.upper() if ch.isalnum())
    return key or None


def pcgis(service: str) -> str:
    return f"{PCGIS}/{service}/FeatureServer/0"


def query_url(layer: str) -> str:
    return layer if layer.endswith("/query") else layer + "/query"


def layer_root(url: str) -> str:
    return url[: -len("/query")] if url.endswith("/query") else url


def verify_city_layer(url: str, fips: str) -> str | None:
    """Return a rejection note when the layer is not a small polygon service in the parent county."""
    try:
        meta = shed.fetch_json(url, {"f": "json"}, timeout=60, retries=3)
        if meta.get("error") or "Polygon" not in str(meta.get("geometryType") or ""):
            return f"{url} did not return a polygon layer and was not joined."
        extent = shed.fetch_json(
            query_url(url),
            {"where": "1=1", "returnExtentOnly": "true", "outSR": "4326", "f": "json"},
            timeout=60,
            retries=3,
        ).get("extent") or {}
        west, south, east, north = (float(extent[key]) for key in ("xmin", "ymin", "xmax", "ymax"))
        box_west, box_south, box_east, box_north = COUNTY_BOX[fips]
        span = max(east - west, north - south)
        outside = west < box_west or south < box_south or east > box_east or north > box_north
        if outside or span > MAX_CITY_SPAN or span <= 0:
            return (
                f"{url} extent ({west:.3f},{south:.3f},{east:.3f},{north:.3f}) "
                "is outside the parent county city box and was not joined."
            )
        count = int(
            shed.fetch_json(
                query_url(url),
                {"where": "1=1", "returnCountOnly": "true", "f": "json"},
                timeout=60,
                retries=3,
            ).get("count")
            or 0
        )
        if count < 10 or count > 40000:
            return f"{url} feature count {count} is not a city overlay and was not joined."
        return None
    except Exception as exc:  # noqa: BLE001
        return f"{url} failed verification ({exc.__class__.__name__}) and was not joined."


def _payload(attrs: dict, code_field: str, desc_field: str | None, source: str, extra: dict | None = None) -> dict:
    code = shed.clean(attrs.get(code_field))
    if not code or code.upper() in STUB_CODES or code.upper() == "UN":
        return {}
    desc = shed.clean(attrs.get(desc_field)) if desc_field else None
    payload = {"code": code, "desc": desc, "source": source}
    if extra:
        payload.update(extra)
    return payload


def spatial_index(key: str, url: str, where: str, fields: list[str], reader: Callable[[dict], dict], *, redownload: bool) -> shed.SpatialIndex:
    features = shed.download_layer(key, query_url(url), where, fields, redownload=redownload, batch=40, workers=6)
    return shed.SpatialIndex(features, reader)


def attributes_for_ids(url: str, id_field: str, ids: list[str], fields: list[str]) -> list[dict]:
    rows: list[dict] = []
    batch = 40
    for index in range(0, len(ids), batch):
        chunk = ids[index : index + batch]
        quoted = ",".join("'" + item.replace("'", "''") + "'" for item in chunk)
        where = f"{id_field} IN ({quoted})"
        data = shed.fetch_json(
            query_url(url),
            {"where": where, "outFields": ",".join(fields), "returnGeometry": "false", "f": "json"},
            timeout=90,
            retries=4,
        )
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        for feature in data.get("features") or []:
            rows.append(feature.get("attributes") or {})
    return rows


def id_index(rows: list[dict], id_field: str, code_field: str, desc_field: str | None, source: str) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for attrs in rows:
        payload = _payload(attrs, code_field, desc_field, source)
        key = id_key(attrs.get(id_field))
        if payload and key and key not in found:
            found[key] = payload
    return found


def lookup_hit(index: dict[str, dict] | None, spatial: shed.SpatialIndex | None, feature: dict, points: list[tuple[float, float]]) -> dict | None:
    if index is not None:
        key = id_key(feature["properties"].get("parcelId"))
        if key and key in index:
            return index[key]
    if spatial is not None:
        return shed.first_overlay(spatial, points)
    return None


FULL_CITIES = [
    {
        "municipality": "Dunedin",
        "fips": "12103",
        "flu": "city",
        "zoning": {
            "role": "dunedin-zoning",
            "url": "https://gis.dunedingov.com/server/rest/services/CommunityDevelopment/ZoningDistrict/FeatureServer/0",
            "fields": ["ZONECLASS", "ZONEDESC"],
            "code": "ZONECLASS",
            "desc": "ZONEDESC",
            "source": "dunedin-zoning",
            "where": "1=1",
        },
        "landUse": {
            "role": "dunedin-flu",
            "url": "https://gis.dunedingov.com/server/rest/services/CommunityDevelopment/LandUseCurrent/FeatureServer/0",
            "fields": ["LANDUSECODE", "LANDUSEDESC"],
            "code": "LANDUSECODE",
            "desc": "LANDUSEDESC",
            "source": "dunedin-flu",
            "where": "1=1",
        },
    },
    {
        "municipality": "Pinellas Park",
        "fips": "12103",
        "flu": "city",
        "idField": "PARCELID",
        "zoning": {
            "role": "pinellas-park-zoning",
            "url": "https://services6.arcgis.com/fH2ZwfxOgb5eaBS4/arcgis/rest/services/Planning_Development_2_WFL1/FeatureServer/19",
            "fields": ["PARCELID", "CATEGORY", "DESCRIPTION"],
            "code": "CATEGORY",
            "desc": "DESCRIPTION",
            "source": "pinellas-park-zoning",
            "where": "1=1",
        },
        "landUse": {
            "role": "pinellas-park-flu",
            "url": "https://services6.arcgis.com/fH2ZwfxOgb5eaBS4/arcgis/rest/services/Planning_Development_2_WFL1/FeatureServer/9",
            "fields": ["PARCELID", "CATEGORY", "DESCRIPTION"],
            "code": "CATEGORY",
            "desc": "DESCRIPTION",
            "source": "pinellas-park-flu",
            "where": "1=1",
        },
    },
    {
        "municipality": "Tarpon Springs",
        "fips": "12103",
        "flu": "city",
        "zoning": {
            "role": "tarpon-springs-zoning",
            "url": "https://gis.ctsfl.us/arcgis/rest/services/Hosted/Zoning_2025/FeatureServer/3",
            "fields": ["curr_code", "curr_zone"],
            "code": "curr_code",
            "desc": "curr_zone",
            "source": "tarpon-springs-zoning",
            "where": "1=1",
        },
        "landUse": {
            "role": "tarpon-springs-flu",
            "url": "https://gis.ctsfl.us/arcgis/rest/services/Hosted/Future_Land_Use_2025/FeatureServer/0",
            "fields": ["flu", "fluname"],
            "code": "flu",
            "desc": "fluname",
            "source": "tarpon-springs-flu",
            "where": "1=1",
        },
    },
    {
        "municipality": "Safety Harbor",
        "fips": "12103",
        "flu": "city",
        "zoning": {
            "role": "safety-harbor-zoning",
            "url": "https://services3.arcgis.com/mmHgYti6dbsFdG2U/arcgis/rest/services/SafetyHarborZoning_11272023/FeatureServer/0",
            "fields": ["Zoning", "ZoningDesc"],
            "code": "Zoning",
            "desc": "ZoningDesc",
            "source": "safety-harbor-zoning",
            "where": "Zoning <> 'UN'",
        },
        "landUse": {
            "role": "safety-harbor-flu",
            "url": "https://services3.arcgis.com/mmHgYti6dbsFdG2U/arcgis/rest/services/SH_FLU_May2025/FeatureServer/0",
            "fields": ["Zone", "Type"],
            "code": "Zone",
            "desc": "Type",
            "source": "safety-harbor-flu",
            "where": "1=1",
        },
    },
    {
        "municipality": "Oldsmar",
        "fips": "12103",
        "flu": "city",
        "zoning": {
            "role": "oldsmar-zoning",
            "url": "https://services8.arcgis.com/4LjX8EYY898im7w3/arcgis/rest/services/Public_Zoning/FeatureServer/0",
            "fields": ["ZONING", "FLUM", "PublicParcelID"],
            "code": "ZONING",
            "desc": None,
            "source": "oldsmar-zoning",
            "where": "1=1",
            "flum": "FLUM",
        },
        "landUse": {
            "role": "oldsmar-flu",
            "url": "https://services8.arcgis.com/4LjX8EYY898im7w3/arcgis/rest/services/Landuse/FeatureServer/0",
            "fields": ["FLU", "FLU_NAME"],
            "code": "FLU",
            "desc": "FLU_NAME",
            "source": "oldsmar-flu",
            "where": "1=1",
        },
    },
    {
        "municipality": "New Port Richey",
        "fips": "12101",
        "flu": "city",
        "idField": "HPARCEL",
        "zoning": {
            "role": "new-port-richey-zoning",
            "url": "https://services7.arcgis.com/5fOG6RMXXiEvqNzn/arcgis/rest/services/NPR_2026_Community_Development_Map_WFL1/FeatureServer/10",
            "fields": ["HPARCEL", "Zoning2025"],
            "code": "Zoning2025",
            "desc": None,
            "source": "new-port-richey-zoning",
            "where": "1=1",
        },
        "landUse": {
            "role": "new-port-richey-flu",
            "url": "https://services7.arcgis.com/5fOG6RMXXiEvqNzn/arcgis/rest/services/NPR_2026_Community_Development_Map_WFL1/FeatureServer/11",
            "fields": ["HPARCEL", "FLU"],
            "code": "FLU",
            "desc": None,
            "source": "new-port-richey-flu",
            "where": "1=1",
        },
    },
    {
        "municipality": "Zephyrhills",
        "fips": "12101",
        "flu": "city",
        "zoning": {
            "role": "zephyrhills-zoning",
            "url": "https://services6.arcgis.com/Q4fB6OTUhdN4M9BR/arcgis/rest/services/Zhills_EnGov_Map_11_2025/FeatureServer/4",
            "fields": ["CODE", "ZONING"],
            "code": "CODE",
            "desc": "ZONING",
            "source": "zephyrhills-zoning",
            "where": "1=1",
        },
        "landUse": {
            "role": "zephyrhills-flu",
            "url": "https://services6.arcgis.com/Q4fB6OTUhdN4M9BR/arcgis/rest/services/Zhills_EnGov_Map_11_2025/FeatureServer/5",
            "fields": ["CODE", "CATEGORY"],
            "code": "CODE",
            "desc": "CATEGORY",
            "source": "zephyrhills-flu",
            "where": "1=1",
        },
    },
]

PARTIALS = [
    ("Seminole", "Pinellas_Seminole_Zoning_view"),
    ("South Pasadena", "Pinellas_South_Pasadena_Zoning_view"),
    ("Treasure Island", "Pinellas_Treasure_Island_Zoning_view"),
    ("Kenneth City", "Pinellas_Kenneth_City_Zoning_view"),
    ("North Redington Beach", "Pinellas_N_Red_Beach_Zoning_view"),
    ("Indian Shores", "Pinellas_Indian_Shores_Zoning_view"),
    ("Belleair", "Pinellas_Belleair_Zoning_view"),
    ("Indian Rocks Beach", "Pinellas_Indian_Rocks_Beach_Zoning_view"),
    ("Redington Shores", "Pinellas_Redington_Shores_Zoning_view"),
    ("Madeira Beach", "Pinellas_Madeira_Beach_Zoning_view"),
]


def partial_specs() -> list[dict]:
    specs = []
    for name, service in PARTIALS:
        slug = name.lower().replace(" ", "-")
        specs.append(
            {
                "municipality": name,
                "fips": "12103",
                "flu": "gap",
                "zoning": {
                    "role": f"{slug}-zoning",
                    "url": pcgis(service),
                    "fields": ["ZONING"],
                    "code": "ZONING",
                    "desc": None,
                    "source": f"{slug}-zoning",
                    "where": "ZONING IS NOT NULL",
                },
            }
        )
    return specs


def cities_for(fips: str) -> list[dict]:
    return [city for city in [*FULL_CITIES, *partial_specs()] if city["fips"] == fips]


def _reader(layer: dict) -> Callable[[dict], dict]:
    def read(attrs: dict) -> dict:
        extra = {}
        flum_field = layer.get("flum")
        if flum_field:
            flum = shed.clean(attrs.get(flum_field))
            if flum and flum.upper() not in STUB_CODES:
                extra["flum"] = flum
        return _payload(attrs, layer["code"], layer.get("desc"), layer["source"], extra or None)

    return read


def prepare_layer(city: dict, layer: dict, parcel_ids: list[str], *, redownload: bool) -> tuple[dict[str, dict] | None, shed.SpatialIndex | None, str | None]:
    note = verify_city_layer(layer["url"], city["fips"])
    if note:
        print(f"  skip {layer['role']}: {note}", flush=True)
        return None, None, note
    id_field = city.get("idField")
    indexed: dict[str, dict] | None = None
    if id_field and parcel_ids:
        print(f"  {layer['role']} attribute join {len(parcel_ids)}", flush=True)
        rows = attributes_for_ids(layer["url"], id_field, parcel_ids, layer["fields"])
        indexed = id_index(rows, id_field, layer["code"], layer.get("desc"), layer["source"])
        print(f"    matched {len(indexed)}", flush=True)
    spatial = None
    # District layers are spatial. Parcel-id layers fall back to geometry only when most ids miss.
    matched = len(indexed or {})
    needs_spatial = id_field is None or (parcel_ids and matched * 5 < len(parcel_ids) * 4)
    if needs_spatial:
        print(f"  {layer['role']} spatial", flush=True)
        spatial = spatial_index(
            layer["role"],
            layer["url"],
            layer["where"],
            layer["fields"],
            _reader(layer),
            redownload=redownload,
        )
    return indexed, spatial, None


def _points(feature: dict) -> list[tuple[float, float]]:
    props = feature["properties"]
    center = tuple(props.get("centroid") or (0, 0))
    return shed.candidate_points(feature.get("geometry") or {}, center)  # type: ignore[arg-type]


def _strip_gaps(props: dict) -> list[str]:
    return [gap for gap in (props.get("dataGaps") or []) if gap not in STRIP_GAPS]


def _clear_stubs(features: list[dict]) -> int:
    cleared = 0
    for feature in features:
        props = feature["properties"]
        code = (props.get("zoningCode") or "").upper()
        if code not in STUB_CODES:
            continue
        props["zoningCode"] = None
        props["zoningDistrict"] = None
        gaps = _strip_gaps(props)
        gaps.append("County zoning code was a city placeholder (NPR, PR, SA, DC, or ZH) and was not stored as a district.")
        props["dataGaps"] = gaps
        cleared += 1
    return cleared


def _flu_payload(hit: dict, municipality: str) -> dict:
    return {
        "code": hit["code"],
        "label": hit.get("desc") or hit["code"],
        "jurisdiction": municipality,
        "source": hit.get("source"),
    }


def apply_municipal_overlays(features: list[dict], fips: str, *, redownload: bool = False) -> dict:
    """Stamp city zoning and FLU onto features already built from county parcels."""
    if fips == "12101":
        cleared = _clear_stubs(features)
        if cleared:
            print(f"  cleared {cleared} Pasco stub zoning codes", flush=True)
    by_city: dict[str, list[dict]] = {}
    for feature in features:
        name = feature["properties"].get("municipality")
        if name:
            by_city.setdefault(name, []).append(feature)

    overlays: list[dict] = []
    rejected = list(PINELLAS_REJECTS if fips == "12103" else PASCO_REJECTS)
    stats: dict[str, dict] = {}
    for city in cities_for(fips):
        name = city["municipality"]
        group = by_city.get(name, [])
        parcel_ids = [feature["properties"]["parcelId"] for feature in group if feature["properties"].get("parcelId")]
        print(f"Join {name} parcels {len(group)}", flush=True)
        zoning_ids, zoning_spatial, zoning_note = prepare_layer(city, city["zoning"], parcel_ids, redownload=redownload)
        flu_ids = flu_spatial = None
        flu_note = None
        if city.get("landUse"):
            flu_ids, flu_spatial, flu_note = prepare_layer(city, city["landUse"], parcel_ids, redownload=redownload)
        if zoning_note:
            rejected.append(zoning_note)
        elif zoning_ids is not None or zoning_spatial is not None:
            overlays.append({"role": city["zoning"]["role"], "url": city["zoning"]["url"]})
        if flu_note:
            rejected.append(flu_note)
        elif city.get("landUse") and (flu_ids is not None or flu_spatial is not None):
            overlays.append({"role": city["landUse"]["role"], "url": city["landUse"]["url"]})

        zoning_joined = 0
        flu_joined = 0
        for feature in group:
            props = feature["properties"]
            points = _points(feature)
            zone = lookup_hit(zoning_ids, zoning_spatial, feature, points) if not zoning_note else None
            flu_hit = lookup_hit(flu_ids, flu_spatial, feature, points) if city.get("landUse") and not flu_note else None
            gaps = _strip_gaps(props)
            if zone and zone.get("code"):
                props["zoningCode"] = zone["code"]
                props["zoningDistrict"] = zone["code"]
                props["zoningDescription"] = zone.get("desc")
                zoning_joined += 1
            elif city["flu"] == "city":
                if props.get("zoningDescription") and str(props.get("zoningDescription")).startswith("Parcel attribute hint"):
                    gaps.append("City zoning polygon did not intersect this parcel. The parcel-attribute hint was kept and is not an official district.")
                else:
                    gaps.append("City zoning polygon did not intersect this parcel.")
            else:
                gaps.append("City zoning polygon did not intersect this parcel.")
            if flu_hit and flu_hit.get("code"):
                props["flu"] = _flu_payload(flu_hit, name)
                flu_joined += 1
            elif city["flu"] == "city" and zone and zone.get("flum"):
                props["flu"] = {
                    "code": zone["flum"],
                    "label": zone["flum"],
                    "jurisdiction": name,
                    "source": "oldsmar-parcel-flum",
                }
                flu_joined += 1
            elif city["flu"] == "city":
                existing = props.get("flu") or {}
                if existing.get("source") == "pasco-parcel-attribute":
                    gaps.append("City future land use polygon did not intersect this parcel. The county parcel-attribute land-use hint was kept.")
                else:
                    gaps.append("City future land use polygon did not intersect this parcel.")
            else:
                gaps.append(PARTIAL_FLU_GAP)
            props["dataGaps"] = gaps
        stats[name] = {
            "parcels": len(group),
            "zoningJoined": zoning_joined,
            "fluJoined": flu_joined,
            "fluStatus": city["flu"],
        }
        print(f"  {name} zoning {zoning_joined} flu {flu_joined}", flush=True)
    return {"stats": stats, "overlays": overlays, "rejected": rejected}


def _load_tiles(fips: str) -> list[tuple[Path, dict]]:
    folder = COUNTY_DIR / fips / "tiles"
    loaded = []
    for path in sorted(folder.glob("*.geojson")):
        loaded.append((path, json.loads(path.read_text())))
    return loaded


def _features_of(tiles: list[tuple[Path, dict]]) -> list[dict]:
    features: list[dict] = []
    for _path, collection in tiles:
        features.extend(collection.get("features") or [])
    return features


def deepen_county(fips: str, *, redownload: bool) -> dict:
    county_path = COUNTY_DIR / fips / "county.json"
    row = json.loads(county_path.read_text())
    before_count = row["featureCount"]
    before_munis = dict(row["municipalityCounts"])
    tiles = _load_tiles(fips)
    snapshots: list[tuple[Path, dict, list[str]]] = []
    for path, collection in tiles:
        before = [json.dumps(feature.get("properties"), sort_keys=True, separators=(",", ":")) for feature in collection.get("features") or []]
        snapshots.append((path, collection, before))
    features = _features_of(tiles)
    if len(features) != before_count:
        raise RuntimeError(f"{fips} tile count {len(features)} does not match county.json {before_count}")
    applied = apply_municipal_overlays(features, fips, redownload=redownload)
    zoning_joined, flu_joined, munis = shed.tally(features)
    if munis != before_munis and sorted(munis.items()) != sorted(before_munis.items()):
        raise RuntimeError(f"{fips} municipality counts changed: {set(munis) ^ set(before_munis)}")
    # Same labels and counts. Order in county.json stays put.
    for label, count in before_munis.items():
        if munis.get(label) != count:
            raise RuntimeError(f"{fips} {label} count changed {count} -> {munis.get(label)}")
    owned_roles = {item["role"] for item in applied["overlays"]}
    kept = [item for item in row.get("overlays") or [] if item.get("role") not in owned_roles]
    # Drop prior copies of the namesake notes, then append the current list.
    namesake_prefix = ("Rejected namesake:", "Pinellas unincorporated", "Pasco county ZN_TYPE", "Pinellas Countywide", "Zephyrhills traditional")
    rejected = [item for item in row.get("rejected") or [] if not str(item).startswith(namesake_prefix)]
    for note in applied["rejected"]:
        if note not in rejected:
            rejected.append(note)
    row["gaps"] = list(shed.PINELLAS_GAPS if fips == "12103" else shed.PASCO_GAPS)
    row["overlays"] = kept + applied["overlays"]
    row["rejected"] = rejected
    row["zoningJoinedCount"] = zoning_joined
    row["fluJoinedCount"] = flu_joined
    row["municipalOverlayJoins"] = applied["stats"]
    row["featureCount"] = before_count
    written = 0
    for path, collection, before in snapshots:
        after = [json.dumps(feature.get("properties"), sort_keys=True, separators=(",", ":")) for feature in collection.get("features") or []]
        if after == before:
            continue
        path.write_text(json.dumps(collection, separators=(",", ":")))
        written += 1
    county_path.write_text(json.dumps(row, indent=2) + "\n")
    print(f"{row['name']} tiles rewritten {written} zoning {zoning_joined} flu {flu_joined}", flush=True)
    _require_joins(fips, applied["stats"])
    return row


def _require_joins(fips: str, stats: dict[str, dict]) -> None:
    if fips == "12103":
        required = ["Dunedin", "Pinellas Park", "Tarpon Springs", "Safety Harbor", "Oldsmar"]
    else:
        required = ["New Port Richey", "Zephyrhills"]
    for name in required:
        row = stats[name]
        if row["parcels"] < 1 or row["zoningJoined"] < 1 or row["fluJoined"] < 1:
            raise RuntimeError(f"{name} did not join zoning and FLU: {row}")
        # County situs labels are wider than some city maps (Oldsmar). Require a real join, not full coverage.
        floor = 40 if row["parcels"] >= 100 else 1
        if row["zoningJoined"] < floor or row["fluJoined"] < floor:
            raise RuntimeError(f"{name} join count is below {floor}: {row}")
    if fips == "12103":
        for name, _service in PARTIALS:
            row = stats[name]
            if row["fluJoined"] != 0:
                raise RuntimeError(f"{name} partial city stored a FLU code")
            if row["parcels"] >= 20 and row["zoningJoined"] < 1:
                raise RuntimeError(f"{name} zoning view did not join: {row}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    for fips in ("12103", "12101"):
        deepen_county(fips, redownload=args.refresh)
    print("Pinellas and Pasco city overlays joined onto existing county parcels.", flush=True)


if __name__ == "__main__":
    main()
