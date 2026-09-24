#!/usr/bin/env python3
"""Wilson County, Tennessee parcels (FIPS 47189) for the Nashville market.

Comptroller IMPACT county id is 95 (JUR 095), not Census FIPS 189.
Geometry is IMPACT Parcels layer 0, parcel type 1, CALC_ACRE 5–150.
Attributes are Parcel_Layer_Themes layer 12 joined on GISLINK (latest TAXYR).

City zoning and FLU are not countywide:
  - Lebanon Hosted Zoning_Districts field `zone`, inside the Lebanon city limit
  - Mt. Juliet Planning___Zoning field `Zone_Curre` and FLU `FLU_Lisa`, inside Mt. Juliet
  - Watertown and unincorporated Wilson stay null (PDF / paid shapefile only)

Do not use gis.wilson-co.com (Wilson County, North Carolina) or token-gated
GEOJobe PSA services. Nomination-eligible tracts are not designated QOZs.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from parcel_geometry import _inside_polygon, esri_rings_to_geojson, representative_point

from seed_market_parcels import (
    CACHE_DIR,
    COUNTY_DIR,
    MAX_ACRES,
    MIN_ACRES,
    clean,
    county_row,
    empty_feature,
    fetch_by_ids,
    fetch_json,
    fetch_object_ids,
    in_band,
    num,
    plausible_centroid,
    rebuild_indexes,
    write_tiles,
    zip_str,
)

ROOT = Path(__file__).resolve().parents[1]
FIPS = "47189"
COMPTROLLER_COUNTY_ID = 95
JUR = "095"
SOURCE = "tn-impact-47189"

PARCELS_URL = "https://maps.cot.tn.gov/server3/rest/services/IMPACT/Parcels/FeatureServer/0/query"
THEMES_URL = "https://maps.cot.tn.gov/server3/rest/services/IMPACT/Parcel_Layer_Themes/FeatureServer/12/query"
LEBANON_ZONING_URL = "https://maps.lebanontn.org/arcgis/rest/services/Hosted/Zoning_Districts/FeatureServer/0/query"
LEBANON_LIMIT_URL = (
    "https://maps.lebanontn.org/arcgis/rest/services/WilsonEnterpriseInternal/"
    "Lebanon_Information_Outside_PSA/FeatureServer/0/query"
)
MTJ_ZONING_URL = (
    "https://utility.arcgis.com/usrsvcs/servers/5e2f5bfd27984da89b2e45a726d0e37b/"
    "rest/services/Planning___Zoning/FeatureServer/5/query"
)
MTJ_FLU_URL = (
    "https://utility.arcgis.com/usrsvcs/servers/5e2f5bfd27984da89b2e45a726d0e37b/"
    "rest/services/Planning___Zoning/FeatureServer/1/query"
)
MTJ_LIMIT_URL = (
    "https://utility.arcgis.com/usrsvcs/servers/621b088a06a84f16b412e25b8d127804/"
    "rest/services/Administration_City/FeatureServer/2/query"
)
HUD_OZ_URL = (
    "https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/FeatureServer/13/query"
)
TIGER_URL = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/6/query"
RURAL_PACK = ROOT / "data" / "fixtures" / "oz2-rural-markets.json"

WHERE = f"COUNTY_ID={COMPTROLLER_COUNTY_ID} AND PARCEL_TYPE=1 AND CALC_ACRE>={MIN_ACRES} AND CALC_ACRE<={MAX_ACRES}"
PARCEL_FIELDS = ["GISLINK", "COUNTY_ID", "PARCEL_TYPE", "CALC_ACRE", "PARCELWP"]
THEME_FIELDS = [
    "OBJECTID",
    "GISLINK",
    "JUR",
    "PARID",
    "TAXYR",
    "PARCELID",
    "ID",
    "CITYNUM",
    "ST_NUM",
    "STREET",
    "ADDRESS",
    "OWNER",
    "OWNER2",
    "MAILADDR",
    "MAILCITY",
    "STATE",
    "ZIP",
    "ZONING",
    "CALC_ACRE",
    "CAMADEEDAC",
    "CAMACALCAC",
    "LANDVAL",
    "IMPVAL",
    "OBYVAL",
    "APPRAISAL",
    "SALEDATE",
    "SALEYEAR",
    "PRICE",
    "DEEDBKPG",
    "LANDUSE",
    "PROPTYPE",
    "UPDATED",
]

CITYNUM_JURIS = {"404": "LEB", "508": "MTJ", "758": "WAT"}
SITUS_CITY = {"LEB": "Lebanon", "MTJ": "Mt. Juliet", "WAT": "Watertown"}

GAPS = [
    "Unincorporated Wilson zoning and future land use have no public FeatureServer (county PDF maps only; the $75 shapefile was not purchased). Zoning and FLU stay null outside Lebanon and Mt. Juliet.",
    "Watertown zoning is the 2017 ordinance PDF only. No anonymous city-limit or zoning FeatureServer was verified. CITYNUM 758 parcels keep IMPACT geometry with null zoning and FLU.",
    "Lebanon zone and Mt. Juliet Zone_Curre / FLU_Lisa are city-only. They are applied only when the parcel centroid is inside that city limit. CAMA ZONING is not used as an entitlement.",
    "Rejected gis.wilson-co.com and county-data-wilsoncounty.opendata.arcgis.com — those are Wilson County, North Carolina.",
    "Rejected token-gated GEOJobe PSA layers (WilsonTN_PSA and related utility proxies, including Lebanon Parcels_Address).",
    "Comptroller COUNTY_ID is 95 (JUR 095), not Census FIPS 189. Attributes come from IMPACT Parcel_Layer_Themes layer 12 joined on GISLINK using the latest TAXYR.",
    "HUD Opportunity Zones has no designated tract in Wilson County (GEOID 47189). Rev. Proc. 2026-14 rural eligibility is stored only on oz2Eligibility for the Nashville rural pack and is not a designated QOZ.",
    "Assessed and taxable values are not on the public IMPACT extract. marketValue is APPRAISAL when it is positive; otherwise null.",
]

ALLOWED_PREFIXES = (
    "https://maps.cot.tn.gov/server3/rest/services/IMPACT/",
    "https://maps.lebanontn.org/arcgis/rest/services/Hosted/Zoning_Districts/",
    "https://maps.lebanontn.org/arcgis/rest/services/WilsonEnterpriseInternal/Lebanon_Information_Outside_PSA/",
    "https://utility.arcgis.com/usrsvcs/servers/5e2f5bfd27984da89b2e45a726d0e37b/rest/services/Planning___Zoning/",
    "https://utility.arcgis.com/usrsvcs/servers/621b088a06a84f16b412e25b8d127804/rest/services/Administration_City/",
    "https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/Opportunity_Zones/",
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/",
)


def wilson_spec() -> dict:
    return {
        "kind": "wilson-tn",
        "source": SOURCE,
        "url": PARCELS_URL,
        "coverage": "complete-gte-5ac",
        "gaps": list(GAPS),
    }


def assert_public_url(url: str) -> None:
    lowered = url.lower()
    if any(token in lowered for token in ("wilson-co.com", "wilsoncounty.opendata", "geojobe", "geopowered")):
        raise RuntimeError(f"Rejected North Carolina lookalike or token-gated host: {url}")
    if not url.startswith(ALLOWED_PREFIXES):
        raise RuntimeError(f"URL is outside the Wilson County, Tennessee public allowlist: {url}")


def checked_fetch(url: str, params: dict | None = None, timeout: int = 180) -> dict:
    assert_public_url(url)
    data = fetch_json(url, params, timeout=timeout)
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:400])
    return data


def squeeze(value) -> str | None:
    text = clean(value)
    if not text:
        return None
    return " ".join(text.split())


def positive(value) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def parse_sale_date(value) -> str | None:
    if isinstance(value, (int, float)) and value > 0:
        millis = value if value > 10_000_000_000 else value * 1000
        try:
            return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    text = clean(value)
    if not text or text in {"0", "0000-00-00"}:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return None


def updated_ordinal(value) -> int:
    text = clean(value) or ""
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date().toordinal()
        except ValueError:
            continue
    return 0


def latest_theme(rows: list[dict]) -> dict:
    return max(rows, key=lambda row: (int(num(row.get("TAXYR")) or 0), updated_ordinal(row.get("UPDATED"))))


def point_in_geometry(lon: float, lat: float, geometry: dict | None) -> bool:
    if not geometry:
        return False
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    polygons = [coords] if kind == "Polygon" else coords if kind == "MultiPolygon" else []
    return any(bool(poly) and _inside_polygon(lon, lat, poly) for poly in polygons)


def geometry_bounds(geometry: dict | None) -> tuple[float, float, float, float] | None:
    if not geometry:
        return None
    xs: list[float] = []
    ys: list[float] = []

    def walk(node) -> None:
        if isinstance(node, (int, float)):
            return
        if node and isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        for child in node:
            walk(child)

    walk(geometry.get("coordinates") or [])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def feature_attr(feature: dict, *names: str) -> str | None:
    props = feature.get("properties") or feature.get("attributes") or {}
    folded = {str(key).lower(): value for key, value in props.items()}
    for name in names:
        text = squeeze(props.get(name))
        if text:
            return text
        text = squeeze(folded.get(name.lower()))
        if text:
            return text
    return None


def prepare_labels(features: list[dict], *field_names: str) -> list[tuple]:
    prepared = []
    for feature in features:
        geometry = feature.get("geometry")
        label = feature_attr(feature, *field_names)
        bounds = geometry_bounds(geometry)
        if not geometry or not label or not bounds:
            continue
        prepared.append((bounds, geometry, label))
    return prepared


def label_at(prepared: list[tuple], lon: float, lat: float) -> str | None:
    for (minx, miny, maxx, maxy), geometry, label in prepared:
        if lon < minx or lon > maxx or lat < miny or lat > maxy:
            continue
        if point_in_geometry(lon, lat, geometry):
            return label
    return None


def fetch_geojson(url: str, where: str, out_fields: list[str]) -> list[dict]:
    ids_data = checked_fetch(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=120)
    ids = [int(i) for i in (ids_data.get("objectIds") or [])]
    features: list[dict] = []
    batch_size = 120
    start = 0
    while start < len(ids):
        chunk = ids[start : start + batch_size]
        try:
            data = checked_fetch(
                url,
                {
                    "objectIds": ",".join(str(i) for i in chunk),
                    "outFields": ",".join(out_fields),
                    "returnGeometry": "true",
                    "outSR": "4326",
                    "f": "geojson",
                },
                timeout=180,
            )
        except RuntimeError:
            if batch_size > 20:
                batch_size = max(20, batch_size // 2)
                continue
            raise
        batch = data.get("features") or []
        if data.get("exceededTransferLimit") and batch_size > 20:
            batch_size = max(20, batch_size // 2)
            continue
        features.extend(batch)
        start += len(chunk)
    return features


def normalize_geometry(raw: list[dict], county: dict, markets: list[str]) -> tuple[list[dict], int]:
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        if int(num(attrs.get("COUNTY_ID")) or -1) != COMPTROLLER_COUNTY_ID:
            dropped += 1
            continue
        if int(num(attrs.get("PARCEL_TYPE")) or -1) != 1:
            dropped += 1
            continue
        geometry = esri_rings_to_geojson((item.get("geometry") or {}).get("rings") or [])
        if not geometry:
            dropped += 1
            continue
        center = representative_point(geometry)
        if not plausible_centroid(center):
            dropped += 1
            continue
        acres = num(attrs.get("CALC_ACRE"))
        if not in_band(acres):
            dropped += 1
            continue
        parcel_id = clean(attrs.get("GISLINK"))
        if not parcel_id or not parcel_id.startswith(JUR):
            dropped += 1
            continue
        feature = empty_feature(
            fips=FIPS,
            county=county["name"],
            state="Tennessee",
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,  # type: ignore[arg-type]
            source=SOURCE,
        )
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def fetch_themes(links: list[str]) -> dict[str, dict]:
    """Page the county Themes extract once. GISLINK IN (...) queries were much slower."""
    wanted = set(links)
    grouped: dict[str, list[dict]] = {}
    offset = 0
    page = 2000
    seen_ids: set[int] = set()
    while offset < 200000:
        data = checked_fetch(
            THEMES_URL,
            {
                "where": f"JUR='{JUR}'",
                "outFields": ",".join(THEME_FIELDS),
                "returnGeometry": "false",
                "orderByFields": "OBJECTID",
                "resultOffset": offset,
                "resultRecordCount": page,
                "f": "json",
            },
            timeout=180,
        )
        rows = [feat.get("attributes") or {} for feat in data.get("features") or []]
        fresh = 0
        for row in rows:
            oid = row.get("OBJECTID")
            if isinstance(oid, int) and oid in seen_ids:
                continue
            if isinstance(oid, int):
                seen_ids.add(oid)
                fresh += 1
            link = clean(row.get("GISLINK"))
            if link in wanted:
                grouped.setdefault(link, []).append(row)
        print(f"    themes scanned {offset + len(rows)} matched {len(grouped)}", flush=True)
        if not rows or (rows and fresh == 0 and any(isinstance(row.get("OBJECTID"), int) for row in rows)):
            break
        if not data.get("exceededTransferLimit") and len(rows) < page:
            break
        offset += len(rows)
    return {link: latest_theme(rows) for link, rows in grouped.items()}


def apply_themes(features: list[dict], themes: dict[str, dict]) -> dict:
    stats = {"themes": 0, "owners": 0, "situs": 0, "appraisals": 0}
    for feature in features:
        props = feature["properties"]
        row = themes.get(props["parcelId"])
        if not row:
            continue
        stats["themes"] += 1
        owner = squeeze(row.get("OWNER"))
        owner2 = squeeze(row.get("OWNER2"))
        props["ownerName"] = owner
        props["ownerName2"] = owner2
        if owner or owner2:
            stats["owners"] += 1
        situs = squeeze(row.get("ADDRESS"))
        if not situs:
            number = squeeze(row.get("ST_NUM"))
            street = squeeze(row.get("STREET"))
            situs = " ".join(part for part in (number, street) if part) or None
        props["situsAddress"] = situs
        if situs:
            stats["situs"] += 1
        props["mailingAddress"] = {
            "line1": squeeze(row.get("MAILADDR")),
            "line2": None,
            "city": squeeze(row.get("MAILCITY")),
            "state": squeeze(row.get("STATE")),
            "zip": zip_str(row.get("ZIP")),
        }
        props["dorCode"] = squeeze(row.get("LANDUSE")) or squeeze(row.get("PROPTYPE"))
        price = positive(row.get("PRICE"))
        props["lastSale"] = {
            "date": parse_sale_date(row.get("SALEDATE")),
            "price": price,
            "qualified": None,
        }
        appraisal = positive(row.get("APPRAISAL"))
        props["tax"] = {
            "marketValue": appraisal,
            "assessedValue": None,
            "taxableValue": None,
            "taxes": None,
        }
        if appraisal:
            stats["appraisals"] += 1
        props["cityNum"] = squeeze(row.get("CITYNUM"))
    return stats


def resolve_jurisdiction(lon: float, lat: float, citynum: str | None, lebanon, mt_juliet) -> tuple[str, bool]:
    in_lebanon = point_in_geometry(lon, lat, lebanon)
    in_mtj = point_in_geometry(lon, lat, mt_juliet)
    if in_lebanon and in_mtj:
        return "OVERLAP", True
    if in_lebanon:
        return "LEB", True
    if in_mtj:
        return "MTJ", True
    coded = CITYNUM_JURIS.get(citynum or "")
    if coded:
        return coded, False
    return "UNINC", False


def apply_cities(features: list[dict], layers: dict) -> dict:
    stats = {
        "lebLimit": 0,
        "mtjLimit": 0,
        "lebZoning": 0,
        "mtjZoning": 0,
        "mtjFlu": 0,
        "watertown": 0,
        "unincorporated": 0,
        "cityNumOutsideLimit": 0,
        "overlap": 0,
    }
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        juris, inside_limit = resolve_jurisdiction(lon, lat, props.get("cityNum"), layers["lebanonLimit"], layers["mtjLimit"])
        props["jurisdictionCode"] = juris if juris != "OVERLAP" else None
        props["situsCity"] = SITUS_CITY.get(juris)
        props["zoningCode"] = None
        props["flu"] = None
        if juris == "OVERLAP":
            stats["overlap"] += 1
            continue
        if inside_limit and juris == "LEB":
            stats["lebLimit"] += 1
            zone = label_at(layers["lebanonZoning"], lon, lat)
            if zone:
                props["zoningCode"] = zone
                stats["lebZoning"] += 1
        elif inside_limit and juris == "MTJ":
            stats["mtjLimit"] += 1
            zone = label_at(layers["mtjZoning"], lon, lat)
            if zone:
                props["zoningCode"] = zone
                stats["mtjZoning"] += 1
            flu = label_at(layers["mtjFlu"], lon, lat)
            if flu:
                props["flu"] = {
                    "code": flu,
                    "label": flu,
                    "jurisdiction": "MTJ",
                    "source": MTJ_FLU_URL.replace("/query", ""),
                }
                stats["mtjFlu"] += 1
        elif juris == "WAT":
            stats["watertown"] += 1
        elif juris in {"LEB", "MTJ"}:
            stats["cityNumOutsideLimit"] += 1
        else:
            stats["unincorporated"] += 1
    return stats


def wilson_eligible_tracts() -> list[dict]:
    pack = json.loads(RURAL_PACK.read_text())
    tracts = []
    for tract in pack.get("rows") or []:
        if tract.get("state") != "Tennessee" or tract.get("county") != "Wilson":
            continue
        if tract.get("geoid") and str(tract.get("rural")).upper() == "Y":
            tracts.append(tract)
    geoids = {tract["geoid"] for tract in tracts}
    expected = {"47189030402", "47189030500", "47189030700"}
    if geoids != expected:
        raise RuntimeError(f"Wilson rural-eligible pack changed: {sorted(geoids)}")
    quoted = ",".join(f"'{geoid}'" for geoid in sorted(expected))
    data = checked_fetch(
        TIGER_URL,
        {
            "where": f"GEOID IN ({quoted})",
            "outFields": "GEOID,NAME",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )
    by_geoid = {}
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        geoid = str(props.get("GEOID") or "")
        if geoid and feature.get("geometry"):
            by_geoid[geoid] = feature
    if set(by_geoid) != expected:
        raise RuntimeError(f"TIGER did not return Wilson eligible tract polygons: {sorted(by_geoid)}")
    joined = []
    for tract in tracts:
        feature = by_geoid[tract["geoid"]]
        feature = {
            "type": "Feature",
            "properties": {
                "tractGeoid": tract["geoid"],
                "name": tract_name(tract["geoid"]),
                "rural": True,
                "designation": "eligible-for-nomination",
                "source": "rev-proc-2026-14",
            },
            "geometry": feature["geometry"],
        }
        joined.append(feature)
    return joined


def tract_name(geoid: str) -> str:
    value = int(geoid[5:])
    pretty = str(value // 100) if value % 100 == 0 else f"{value / 100:.2f}".rstrip("0")
    return f"Census tract {pretty}"


def apply_opportunity_zones(features: list[dict], eligible: list[dict], designated: list[dict]) -> dict:
    stats = {"eligible": 0, "designated": 0}
    for feature in features:
        props = feature["properties"]
        lon, lat = props["centroid"]
        hit = next((zone for zone in eligible if point_in_geometry(lon, lat, zone["geometry"])), None)
        if hit:
            zone_props = hit["properties"]
            props["oz2Eligibility"] = {
                "eligible": True,
                "rural": True,
                "tractGeoid": zone_props["tractGeoid"],
                "tractName": zone_props["name"],
                "designation": "eligible-for-nomination",
                "source": "rev-proc-2026-14",
            }
            stats["eligible"] += 1
        else:
            props["oz2Eligibility"] = None
        designated_hit = next((zone for zone in designated if point_in_geometry(lon, lat, zone["geometry"])), None)
        if designated_hit:
            zone_props = designated_hit.get("properties") or {}
            geoid = str(zone_props.get("GEOID10") or zone_props.get("geoid") or "")
            props["opportunityZone"] = {
                "inOpportunityZone": True,
                "tractGeoid": geoid or None,
                "tractName": tract_name(geoid) if len(geoid) == 11 else None,
                "source": HUD_OZ_URL.replace("/query", ""),
                "designatedRural": None,
            }
            stats["designated"] += 1
        else:
            props["opportunityZone"] = {
                "inOpportunityZone": False,
                "tractGeoid": None,
                "tractName": None,
                "source": HUD_OZ_URL.replace("/query", ""),
                "designatedRural": None,
            }
        oz2 = props.get("oz2Eligibility") or {}
        oz = props["opportunityZone"]
        if oz2.get("eligible") and oz.get("inOpportunityZone") and oz.get("tractGeoid") == oz2.get("tractGeoid"):
            raise RuntimeError(f"Eligible tract {oz2.get('tractGeoid')} was stored as a designated QOZ")
        if oz2.get("eligible") and oz2.get("designation") != "eligible-for-nomination":
            raise RuntimeError("Eligible Wilson tract is missing the nomination-only designation")
    return stats


def assert_rules(features: list[dict], hud_count: int) -> None:
    if len(features) < 9000:
        raise RuntimeError(f"Wilson extract kept only {len(features)} parcels; expected about 10,671")
    for feature in features:
        props = feature["properties"]
        if not in_band(props.get("acreage")):
            raise RuntimeError(f"Parcel {props.get('parcelId')} is outside 5–150 acres")
        if props.get("countyFips") != FIPS or props.get("state") != "Tennessee":
            raise RuntimeError("Wilson parcel is not tagged as Tennessee 47189")
        if "Nashville" not in (props.get("marketIds") or []):
            raise RuntimeError("Wilson parcel is missing the Nashville market")
        if props.get("source") != SOURCE:
            raise RuntimeError("Wilson parcel source is not the Tennessee IMPACT extract")
        juris = props.get("jurisdictionCode")
        if juris in {None, "UNINC", "WAT"} and (props.get("zoningCode") or props.get("flu")):
            raise RuntimeError("City zoning or FLU was applied outside Lebanon and Mt. Juliet")
        flu = props.get("flu")
        if flu and (flu.get("jurisdiction") != "MTJ" or juris != "MTJ"):
            raise RuntimeError("Mt. Juliet FLU was applied outside Mt. Juliet")
        if juris == "LEB" and props.get("flu"):
            raise RuntimeError("Lebanon has no public FLU layer; FLU must stay null")
        oz2 = props.get("oz2Eligibility") or {}
        oz = props.get("opportunityZone") or {}
        if oz2.get("eligible"):
            if oz.get("inOpportunityZone") and not hud_count:
                raise RuntimeError("Eligible parcel marked designated even though HUD has no Wilson QOZ")
            if oz2.get("designation") != "eligible-for-nomination":
                raise RuntimeError("Eligible parcel designation is not nomination-only")
        if hud_count == 0 and oz.get("inOpportunityZone"):
            raise RuntimeError("HUD reported no Wilson QOZ, but a parcel was marked designated")


def load_geometry(county: dict, markets: list[str], refresh: bool) -> tuple[list[dict], int, int]:
    cache_path = CACHE_DIR / "47189-geometry.json"
    if cache_path.exists() and not refresh:
        cached = json.loads(cache_path.read_text())
        features = cached.get("features") or []
        if features:
            print(f"  geometry cache {len(features)}", flush=True)
            for feature in features:
                feature["properties"]["marketIds"] = markets
            return features, int(cached.get("sourceCount") or 0), int(cached.get("dropped") or 0)
    expected = int(checked_fetch(PARCELS_URL, {"where": WHERE, "returnCountOnly": "true", "f": "json"})["count"])
    print(f"  source rows {expected}", flush=True)
    if expected < 9000:
        raise RuntimeError(f"IMPACT returned {expected} Wilson type-1 parcels in 5–150 acres")
    ids = fetch_object_ids(PARCELS_URL, WHERE)
    raw = fetch_by_ids(PARCELS_URL, ids, PARCEL_FIELDS)
    features, dropped = normalize_geometry(raw, county, markets)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"sourceCount": expected, "dropped": dropped, "features": features}, separators=(",", ":")))
    return features, expected, dropped


def download_wilson(county: dict, markets: list[str], refresh: bool = False) -> dict:
    print(f"Pulling Wilson Tennessee ({FIPS}) via IMPACT COUNTY_ID={COMPTROLLER_COUNTY_ID}", flush=True)
    features, expected, dropped = load_geometry(county, markets, refresh)
    print(f"  joining themes for {len(features)} parcels", flush=True)
    themes = fetch_themes([feature["properties"]["parcelId"] for feature in features])
    theme_stats = apply_themes(features, themes)
    print("  joining city limits, zoning, and FLU", flush=True)
    lebanon_limits = fetch_geojson(LEBANON_LIMIT_URL, "CityName='Lebanon'", ["CityName", "CityCode"])
    mtj_limits = fetch_geojson(MTJ_LIMIT_URL, "NAME='MT. JULIET'", ["NAME"])
    if len(lebanon_limits) != 1 or len(mtj_limits) != 1:
        raise RuntimeError(f"Expected one city limit each; Lebanon {len(lebanon_limits)} Mt. Juliet {len(mtj_limits)}")
    layers = {
        "lebanonLimit": lebanon_limits[0]["geometry"],
        "mtjLimit": mtj_limits[0]["geometry"],
        "lebanonZoning": prepare_labels(fetch_geojson(LEBANON_ZONING_URL, "1=1", ["zone"]), "zone"),
        "mtjZoning": prepare_labels(fetch_geojson(MTJ_ZONING_URL, "1=1", ["Zone_Curre"]), "Zone_Curre"),
        "mtjFlu": prepare_labels(fetch_geojson(MTJ_FLU_URL, "1=1", ["FLU_Lisa"]), "FLU_Lisa"),
    }
    if len(layers["lebanonZoning"]) < 100 or len(layers["mtjZoning"]) < 100 or len(layers["mtjFlu"]) < 50:
        raise RuntimeError("City zoning or FLU layer was too small to be the public county-city extract")
    city_stats = apply_cities(features, layers)
    print("  joining designated QOZs and nomination-eligible tracts", flush=True)
    hud = checked_fetch(
        HUD_OZ_URL,
        {
            "where": "GEOID10 LIKE '47189%'",
            "outFields": "GEOID10,STATE,COUNTY,TRACT",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )
    designated = hud.get("features") or []
    hud_count = len(designated)
    eligible = wilson_eligible_tracts()
    oz_stats = apply_opportunity_zones(features, eligible, designated)
    assert_rules(features, hud_count)
    path, lookup, tiles = write_tiles(county, features)
    gaps = list(GAPS)
    if expected and len(features) < expected:
        gaps.insert(
            0,
            f"{expected} source rows collapsed to {len(features)} parcel ids (duplicate ids or rings that failed the WGS84 check). The acreage query covered Wilson County.",
        )
    row = county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=SOURCE,
        query_url=PARCELS_URL,
        gaps=gaps,
        source_count=expected,
        dropped=dropped,
        tile_count=tiles,
    )
    row["comptrollerCountyId"] = COMPTROLLER_COUNTY_ID
    row["joinStats"] = {**theme_stats, **city_stats, **oz_stats, "hudDesignatedTracts": hud_count}
    (COUNTY_DIR / FIPS / "county.json").write_text(json.dumps(row, indent=2) + "\n")
    print(f"  kept {len(features)} Wilson TN parcels", flush=True)
    print(f"  join {json.dumps(row['joinStats'])}", flush=True)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    catalog = json.loads((ROOT / "data" / "market-parcel-counties.json").read_text())
    county = None
    markets: list[str] = []
    for market in catalog["markets"]:
        for item in market["counties"]:
            if item["fips"] == FIPS and item["state"] == "Tennessee":
                county = item
                if market["id"] not in markets:
                    markets.append(market["id"])
    if not county:
        raise RuntimeError("Wilson County, Tennessee is missing from the market catalog")
    download_wilson(county, markets, refresh=args.refresh)
    rebuild_indexes(catalog)


if __name__ == "__main__":
    main()
