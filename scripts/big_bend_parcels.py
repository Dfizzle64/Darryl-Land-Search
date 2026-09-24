"""Big Bend Florida parcel extract.

Wire order from the county card:

  Leon       usable countywide overlay parcels (TLC_OverlayParcel_D_WM/0)
  Wakulla    partial county parcels + future land use + Sopchoppy zoning
  Jefferson  partial county parcels + Monticello zoning and FLUM
  Gadsden    partial 2018 ARPC roll + Quincy FLUM + Havana zoning
  Madison, Taylor, Dixie   gaps (no county-hosted polygon service)

Acreage band is 5.0–150.0 inclusive. Public GIS only. A situs post office
is not a zoning jurisdiction. Eligible tracts are not designated QOZs.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

from parcel_geometry import contains_point, esri_rings_to_geojson

CACHE_VERSION = 1
STATUS = "Eligible — not designated"

LEON_PARCELS = "https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/TLC_OverlayParcel_D_WM/MapServer/0"
LEON_PROPINFO = "https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/TLC_OverlayPropInfo_D_WM/MapServer/0"
LEON_OWNERS = "https://tlcaccelasupp.leoncountyfl.gov/accelasupp/rest/services/AccelaXAPO/MapServer/2"
LEON_ZONING = "https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/TLC_OverlayZoning_D_WM/MapServer/0"
LEON_CITY = "https://intervector.leoncountyfl.gov/intervector/rest/services/MapServices/TLC_Overlay_Citylimits_WM_D/MapServer/0"

WAKULLA_PARCELS = "https://services9.arcgis.com/vAltLjtfYIJc7pDt/arcgis/rest/services/Wakulla_County_Parcels/FeatureServer/0"
WAKULLA_FLU = "https://services9.arcgis.com/vAltLjtfYIJc7pDt/arcgis/rest/services/Future_Land_Use_Map/FeatureServer/5"
SOPCHOPPY_ZONING = "https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Sopchoppy_FLUM_WFL1/FeatureServer/0"

JEFFERSON_PARCELS = "https://services5.arcgis.com/vFMp1Ly1q6rKKp0o/arcgis/rest/services/JC__PARCELS_view/FeatureServer/0"
JEFFERSON_ZONING = "https://services5.arcgis.com/vFMp1Ly1q6rKKp0o/arcgis/rest/services/JC_CITY_ZONING_view/FeatureServer/0"
JEFFERSON_FLUM = "https://services5.arcgis.com/vFMp1Ly1q6rKKp0o/arcgis/rest/services/JC_CITY_FLUM_view/FeatureServer/0"
JEFFERSON_CITY = "https://services5.arcgis.com/vFMp1Ly1q6rKKp0o/arcgis/rest/services/JC_CITY_OUTLINE_view/FeatureServer/0"

GADSDEN_PARCELS = "https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Gadsden_FLUM2/FeatureServer/0"
GADSDEN_FLUM_ROOT = "https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Gadsden_FLUM2/FeatureServer"
QUINCY_FLUM_ROOT = "https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Quincy_FLUM/FeatureServer"
HAVANA_ZONING = "https://services8.arcgis.com/N3lCn6dEKCL6LidU/arcgis/rest/services/Havana_Zoning_Districts_--_View_Layer/FeatureServer/1"

QUINCY_FLUM_LAYERS = (
    (0, "Recreation"),
    (1, "Public"),
    (2, "MixedUse"),
    (3, "MedRes"),
    (4, "LowRes"),
    (5, "Industrial"),
    (6, "HighRes"),
    (7, "Conservation"),
    (8, "Commercial"),
    (9, "Central_Business"),
    (10, "Agriculture"),
)
GADSDEN_FLUM_LAYERS = tuple(range(1, 16))

GAP_FIPS = {"12079", "12123", "12029"}
PARTIAL_FIPS = {"12129", "12065", "12039"}

NOT_DESIGNATED = (
    "Eligible tracts in this county stay eligible and are not designated QOZs."
)


def leon_appraiser_url(taxid: str) -> str:
    return f"https://search.leonpa.gov/Property/Details/{taxid}"


def in_band(acres: float | None) -> bool:
    return acres is not None and 5.0 <= acres <= 150.0


def parse_totacres(value: Any) -> float | None:
    """ARPC stores deed acres as a zero-padded string. 0 means blank, not a lot."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number <= 0:
        return None
    return number


def title_city(value: Any) -> str | None:
    text = _clean(value)
    if not text or text in {"0", "00"}:
        return None
    return text.title()


def quincy_flum_is_zoning(_code: str | None) -> bool:
    """Quincy publishes future land use polygons. The zoning map is a PDF."""
    return False


def spec_for_fips(fips: str) -> dict:
    if fips == "12073":
        return {
            "kind": "big-bend",
            "countyKey": "leon",
            "url": f"{LEON_PARCELS}/query",
            "where": "CALC_ACREA >= 5 AND CALC_ACREA <= 150",
            "source": "fl-leon-overlay-parcel-12073",
            "coverage": "complete-gte-5ac",
            "gaps": [
                "Usable countywide 5–150 acre extract from TLC_OverlayParcel_D_WM/MapServer/0 (TAXID and CALC_ACREA). Property Appraiser link is https://search.leonpa.gov/Property/Details/{TAXID}. " + NOT_DESIGNATED,
                "Tallahassee and unincorporated Leon County are separate jurisdictions. The city-limits polygon sets Tallahassee. Zoning polygons keep City versus County. PropInfo supplies situs, future land use, and tax. AccelaXAPO supplies owner and mailing address.",
                "The overlay parcel layer has no owner or value. PropInfo has no sale date, no situs ZIP, and no DOR use code.",
            ],
        }
    if fips == "12129":
        return {
            "kind": "big-bend",
            "countyKey": "wakulla",
            "url": f"{WAKULLA_PARCELS}/query",
            "where": "MAP_ACRES >= 5 AND MAP_ACRES <= 150",
            "source": "fl-wakulla-county-parcels-12129",
            "coverage": "sample",
            "gaps": [
                "Partial. The county parcel layer has MAP_ACRES and PARCEL_ID only. No owner, situs, or county zoning.",
                "County future land use is joined from the planning Future Land Use layer. Sopchoppy zoning (ZoningCat on Sopchoppy_FLUM_WFL1) is joined when the centroid falls inside it. St. Marks has no public zoning FeatureServer. " + NOT_DESIGNATED,
                "Property appraiser search is https://mywakullapa.com/.",
            ],
        }
    if fips == "12065":
        return {
            "kind": "big-bend",
            "countyKey": "jefferson",
            "url": f"{JEFFERSON_PARCELS}/query",
            "where": "COGO_ACRES >= 5 AND COGO_ACRES <= 150",
            "source": "fl-jefferson-pa-parcels-12065",
            "coverage": "sample",
            "gaps": [
                "Partial. Jefferson County Property Appraiser parcels have COGO_ACRES and a parcel id. No owner or situs.",
                "Monticello city zoning and city future land use are joined inside the city outline. Unincorporated Jefferson County has no public zoning FeatureServer. " + NOT_DESIGNATED,
                "Property appraiser search is https://jeffersonpa.net/. Null COGO_ACRES rows are omitted.",
            ],
        }
    if fips == "12039":
        return {
            "kind": "big-bend",
            "countyKey": "gadsden",
            "url": f"{GADSDEN_PARCELS}/query",
            "where": "CAST(TOTACRES AS FLOAT) >= 5 AND CAST(TOTACRES AS FLOAT) <= 150",
            "source": "fl-gadsden-arpc-par-071218-12039",
            "coverage": "sample",
            "gaps": [
                "Partial. Parcels are Apalachee RPC Gadsden_FLUM2 layer Par_071218 (a 2018 roll), not a live county host. Deed acres are a zero-padded string. Rows stored as 0 are omitted instead of guessed from the polygon.",
                "Quincy zoning is a PDF at https://www.myquincy.net/building-planning/page/maps, not a FeatureServer. Quincy FLUM categories are joined as future land use inside those polygons and are not zoning codes. Havana zoning districts are joined from the city zoning layer. Midway, Gretna, Chattahoochee, and Greensboro publish FLUM only and are not joined. The roll's situs city is a post office and is not the zoning jurisdiction. " + NOT_DESIGNATED,
                "County FLUM categories are joined outside Quincy. Property appraiser search is https://gadsdenpa.com/.",
            ],
        }
    if fips in GAP_FIPS:
        name = {"12079": "Madison", "12123": "Taylor", "12029": "Dixie"}[fips]
        portal = {
            "12079": "https://madisonpa.com/",
            "12123": "https://qpublic.net/fl/taylor/",
            "12029": "https://www.qpublic.net/fl/dixie/",
        }[fips]
        return {
            "kind": "gap",
            "source": "unavailable",
            "queryUrl": None,
            "coverage": "gap",
            "reason": f"{name} County has no county-hosted parcel polygon service.",
            "gaps": [
                f"Gap. No county-hosted parcel polygon service for {name} County. The property appraiser portal ({portal}) is qPublic/Schneider or a search page, not an open parcel GIS, and was not used as a geometry source.",
                "Statewide FDOR cadastral, Florida DOH EHWATER, and SRWMD republished rolls exist and were not wired. No municipal zoning FeatureServer was confirmed. " + NOT_DESIGNATED,
            ],
        }
    raise KeyError(fips)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _bbox(geometry: dict) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, list) and node and isinstance(node[0], (int, float)):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        if isinstance(node, list):
            for child in node:
                walk(child)

    walk(geometry.get("coordinates"))
    if not xs:
        return (0, 0, 0, 0)
    return min(xs), min(ys), max(xs), max(ys)


class PolyIndex:
    def __init__(self, items: list[dict], cell: float = 0.05):
        self.items = items
        self.cell = cell
        self.grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        for index, item in enumerate(items):
            minx, miny, maxx, maxy = item["bbox"]
            for ix in range(math.floor(minx / cell), math.floor(maxx / cell) + 1):
                for iy in range(math.floor(miny / cell), math.floor(maxy / cell) + 1):
                    self.grid[(ix, iy)].append(index)

    def hits(self, x: float, y: float) -> list[dict]:
        ix = math.floor(x / self.cell)
        iy = math.floor(y / self.cell)
        found = []
        for index in self.grid.get((ix, iy), ()):
            item = self.items[index]
            minx, miny, maxx, maxy = item["bbox"]
            if minx <= x <= maxx and miny <= y <= maxy and contains_point(item["geometry"], x, y):
                found.append(item)
        return found


def _polygon_items(raw: list[dict], extra: dict | None = None) -> list[dict]:
    items = []
    for feature in raw:
        geometry = esri_rings_to_geojson((feature.get("geometry") or {}).get("rings"))
        if not geometry:
            continue
        attrs = dict(feature.get("attributes") or {})
        if extra:
            attrs.update(extra)
        items.append({"geometry": geometry, "attrs": attrs, "bbox": _bbox(geometry)})
    return items


def _smallest(hits: list[dict]) -> dict | None:
    if not hits:
        return None

    def area(item: dict) -> float:
        minx, miny, maxx, maxy = item["bbox"]
        return (maxx - minx) * (maxy - miny)

    return min(hits, key=area)


def pick_leon_zone(hits: list[dict], jurisdiction: str) -> dict | None:
    """Prefer the City or County polygon that matches the parcel jurisdiction."""
    want = "City" if jurisdiction == "Tallahassee" else "County"
    matched = [item for item in hits if _clean(item["attrs"].get("JURISDICTION")) == want]
    if matched:
        return _smallest(matched)
    multiple = [item for item in hits if _clean(item["attrs"].get("JURISDICTION")) == "Multiple"]
    return _smallest(multiple or hits)


def assemble_situs(house: Any, street: Any) -> str | None:
    parts = []
    house_text = _clean(house)
    street_text = _clean(street)
    if house_text and house_text not in {"0", "00"}:
        parts.append(house_text)
    if street_text:
        parts.append(street_text)
    return " ".join(parts) or None


def parse_city_state_zip(value: Any) -> tuple[str | None, str | None, str | None]:
    text = _clean(value)
    if not text:
        return None, None, None
    match = re.fullmatch(r"(.+?)\s+([A-Za-z]{2})\s+(\d{5})(?:-\d{4})?", text)
    if not match:
        return text, None, None
    return title_city(match.group(1)), match.group(2).upper(), match.group(3)


def _set_flu(feature: dict, code: str | None, label: str | None, jurisdiction: str, source: str) -> None:
    if not code and not label:
        return
    feature["properties"]["flu"] = {
        "code": code,
        "label": (label or code or "")[:80] or None,
        "jurisdiction": jurisdiction,
        "source": source,
    }


def _set_zone(feature: dict, code: str | None, district: str | None, jurisdiction: str, prefix: str) -> None:
    feature["properties"]["jurisdictionCode"] = jurisdiction
    feature["properties"]["jurisdictionPrefix"] = prefix
    if code:
        feature["properties"]["zoningCode"] = code
    if district:
        feature["properties"]["zoningDistrict"] = district[:80]


def download_big_bend(county: dict, markets: list[str], spec: dict) -> dict:
    import seed_market_parcels as seed

    cache_path = seed.CACHE_DIR / f"{county['fips']}.json"
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = seed.json.loads(cache_path.read_text())
        if cached.get("version") == CACHE_VERSION and cached.get("features"):
            print(f"  cache hit {len(cached['features'])}", flush=True)
            return _write(seed, county, markets, cached)

    key = spec["countyKey"]
    print(f"Pulling {county['name']} via {spec['source']}", flush=True)
    builders = {
        "leon": _build_leon,
        "wakulla": _build_wakulla,
        "jefferson": _build_jefferson,
        "gadsden": _build_gadsden,
    }
    features, dropped, source_count, stats = builders[key](seed, county, markets, spec)
    if not features:
        raise RuntimeError(f"{county['name']} kept 0 parcels in the 5–150 acre band")
    payload = {
        "version": CACHE_VERSION,
        "source": spec["source"],
        "queryUrl": spec["url"],
        "sourceCount": source_count,
        "dropped": dropped,
        "features": features,
        "gaps": list(spec.get("gaps") or []),
        "coverage": spec["coverage"],
        "stats": stats,
    }
    seed.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(seed.json.dumps(payload, separators=(",", ":")))
    return _write(seed, county, markets, payload)


def _write(seed: Any, county: dict, markets: list[str], payload: dict) -> dict:
    features = payload["features"]
    for feature in features:
        feature["properties"]["marketIds"] = markets
        feature["properties"]["oz2Eligibility"] = None
        if feature["properties"].get("opportunityZone") is None:
            feature["properties"]["opportunityZone"] = None
    path, lookup, tiles = seed.write_tiles(county, features)
    stats = payload.get("stats") or {}
    print(
        f"  kept {len(features)} dropped {payload.get('dropped')} stats {stats}",
        flush=True,
    )
    gaps = list(payload.get("gaps") or [])
    if stats:
        gaps.append("Join counts: " + ", ".join(f"{key}={value}" for key, value in stats.items()))
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=payload.get("coverage") or "sample",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=payload.get("source"),
        query_url=payload.get("queryUrl"),
        gaps=gaps,
        source_count=payload.get("sourceCount"),
        dropped=payload.get("dropped"),
        tile_count=tiles,
    )


def _pull(seed: Any, url: str, where: str, fields: list[str], batch: int = 80) -> tuple[list[dict], int]:
    ids = seed.fetch_object_ids(url, where)
    print(f"    ids {len(ids)} {url.rsplit('/', 2)[-2]}", flush=True)
    if not ids:
        return [], 0
    raw = seed.fetch_by_ids(url, ids, fields, batch=batch)
    return raw, len(ids)


def _attrs_by_id(seed: Any, url: str, field: str, ids: list[str], out_fields: list[str]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    unique = [parcel_id for parcel_id in dict.fromkeys(ids) if parcel_id and "'" not in parcel_id]
    for start in range(0, len(unique), 40):
        chunk = unique[start : start + 40]
        quoted = ",".join(f"'{parcel_id}'" for parcel_id in chunk)
        data = seed.fetch_json(
            url,
            {
                "where": f"{field} IN ({quoted})",
                "outFields": ",".join(out_fields),
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=120,
        )
        if data.get("error"):
            raise RuntimeError(str(data["error"])[:240])
        for feature in data.get("features") or []:
            attrs = feature.get("attributes") or {}
            key = _clean(attrs.get(field))
            if key:
                grouped[key].append(attrs)
        if start and start % 400 == 0:
            print(f"    attrs {start}/{len(unique)}", flush=True)
    return grouped


def _index_layer(seed: Any, url: str, where: str, fields: list[str], extra: dict | None = None) -> PolyIndex:
    raw, _count = _pull(seed, url, where, fields, batch=100)
    return PolyIndex(_polygon_items(raw, extra))


def _safe_index(seed: Any, url: str, where: str, fields: list[str], extra: dict | None = None) -> PolyIndex:
    try:
        return _index_layer(seed, url, where, fields, extra)
    except Exception as exc:  # noqa: BLE001
        print(f"    overlay failed {url}: {exc}", flush=True)
        return PolyIndex([])


def _feature_from_raw(
    seed: Any,
    county: dict,
    markets: list[str],
    raw: list[dict],
    *,
    source: str,
    parcel_id_of,
    acres_of,
    appraiser_of,
) -> tuple[list[dict], int]:
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, _computed = seed.rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            dropped += 1
            continue
        parcel_id = parcel_id_of(attrs)
        acres = acres_of(attrs)
        if not parcel_id or not in_band(acres):
            dropped += 1
            continue
        center = seed.centroid_of(geometry)
        if not seed.plausible_centroid(center):
            dropped += 1
            continue
        feature = seed.empty_feature(
            fips=county["fips"],
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source=source,
        )
        feature["properties"]["appraiserUrl"] = appraiser_of(parcel_id)
        feature["properties"]["dataGaps"] = []
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features, dropped


def _build_leon(seed: Any, county: dict, markets: list[str], spec: dict) -> tuple[list[dict], int, int, dict]:
    raw, source_count = _pull(seed, spec["url"], spec["where"], ["TAXID", "CALC_ACREA"], batch=50)
    features, dropped = _feature_from_raw(
        seed,
        county,
        markets,
        raw,
        source=spec["source"],
        parcel_id_of=lambda attrs: _clean(attrs.get("TAXID")),
        acres_of=lambda attrs: _num(attrs.get("CALC_ACREA")),
        appraiser_of=leon_appraiser_url,
    )
    ids = [feature["properties"]["parcelId"] for feature in features]
    prop = _attrs_by_id(
        seed,
        f"{LEON_PROPINFO}/query",
        "TAXID",
        ids,
        ["TAXID", "SITEADDR", "CITYINOUT", "ZONING", "ZONED", "FUTURELU", "FLANDU", "MARKETVAL", "TAXABLE", "TAXES", "CURSALES"],
    )
    owners = _attrs_by_id(
        seed,
        f"{LEON_OWNERS}/query",
        "TAXID",
        ids,
        ["TAXID", "OWNERS", "ADDR1", "ADDR2", "ADDR3", "PRIMARY"],
    )
    zoning = _safe_index(seed, f"{LEON_ZONING}/query", "1=1", ["ZONING", "ZONED", "JURISDICTION", "ACRES"])
    city = _safe_index(seed, f"{LEON_CITY}/query", "1=1", ["NAME"])
    stats = {"tallahassee": 0, "leonCounty": 0, "zoning": 0, "flu": 0, "owners": 0, "propinfo": 0}
    for feature in features:
        props = feature["properties"]
        taxid = props["parcelId"]
        lon, lat = props["centroid"]
        info = (prop.get(taxid) or [{}])[0]
        if city.items:
            inside_city = bool(city.hits(lon, lat))
        else:
            inside_city = (_clean(info.get("CITYINOUT")) or "").upper() == "IN"
        jurisdiction = "Tallahassee" if inside_city else "Leon County"
        prefix = "TLH" if inside_city else "LEON"
        stats["tallahassee" if inside_city else "leonCounty"] += 1
        if info:
            stats["propinfo"] += 1
            props["situsAddress"] = _clean(info.get("SITEADDR"))
            if inside_city:
                props["situsCity"] = "Tallahassee"
            zone_hit = pick_leon_zone(zoning.hits(lon, lat), jurisdiction)
            code = _clean((zone_hit or {}).get("attrs", {}).get("ZONING")) or _clean(info.get("ZONING"))
            district = _clean((zone_hit or {}).get("attrs", {}).get("ZONED")) or _clean(info.get("ZONED"))
            if code or district:
                stats["zoning"] += 1
            _set_zone(feature, code, district, jurisdiction, prefix)
            flu_code = _clean(info.get("FUTURELU"))
            flu_label = _clean(info.get("FLANDU"))
            if flu_code or flu_label:
                stats["flu"] += 1
                _set_flu(feature, flu_code, flu_label, jurisdiction, "tlc-propinfo")
            price = _num(info.get("CURSALES"))
            props["lastSale"] = {"date": None, "price": price if price and price > 0 else None, "qualified": None}
            market_value = _num(info.get("MARKETVAL"))
            taxable = _num(info.get("TAXABLE"))
            taxes = _num(info.get("TAXES"))
            props["tax"] = {
                "marketValue": market_value if market_value and market_value > 0 else None,
                "assessedValue": None,
                "taxableValue": taxable if taxable and taxable > 0 else None,
                "taxes": taxes if taxes and taxes > 0 else None,
            }
        else:
            _set_zone(feature, None, None, jurisdiction, prefix)
            props["dataGaps"].append("No PropInfo row for this TAXID.")
        owner_rows = owners.get(taxid) or []
        primary = [row for row in owner_rows if (_clean(row.get("PRIMARY")) or "").upper() == "Y" and _clean(row.get("OWNERS"))]
        chosen = (primary or owner_rows or [None])[0]
        if chosen and _clean(chosen.get("OWNERS")):
            stats["owners"] += 1
            props["ownerName"] = _clean(chosen.get("OWNERS"))
            city_name, state, zip_code = parse_city_state_zip(chosen.get("ADDR2"))
            props["mailingAddress"] = {
                "line1": _clean(chosen.get("ADDR1")),
                "line2": _clean(chosen.get("ADDR3")),
                "city": city_name,
                "state": state,
                "zip": zip_code,
            }
        else:
            props["dataGaps"].append("No Accela owner row for this TAXID.")
        if not props["dataGaps"]:
            props["dataGaps"] = None
    return features, dropped, source_count, stats


def _build_wakulla(seed: Any, county: dict, markets: list[str], spec: dict) -> tuple[list[dict], int, int, dict]:
    raw, source_count = _pull(seed, spec["url"], spec["where"], ["PARCEL_ID", "MAP_ACRES"], batch=60)
    features, dropped = _feature_from_raw(
        seed,
        county,
        markets,
        raw,
        source=spec["source"],
        parcel_id_of=lambda attrs: _clean(attrs.get("PARCEL_ID")),
        acres_of=lambda attrs: _num(attrs.get("MAP_ACRES")),
        appraiser_of=lambda _parcel: "https://mywakullapa.com/",
    )
    flu = _safe_index(seed, f"{WAKULLA_FLU}/query", "1=1", ["LAND_USE"])
    sop = _safe_index(seed, f"{SOPCHOPPY_ZONING}/query", "1=1", ["ZoningCat", "FLU_Cat", "Zone_Full"])
    stats = {"flu": 0, "sopchoppy": 0, "county": 0}
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        town = _smallest(sop.hits(lon, lat))
        land = _smallest(flu.hits(lon, lat))
        if town:
            stats["sopchoppy"] += 1
            code = _clean(town["attrs"].get("ZoningCat"))
            _set_zone(feature, code, _clean(town["attrs"].get("Zone_Full")), "Sopchoppy", "SOP")
            flu_code = _clean(town["attrs"].get("FLU_Cat"))
            if flu_code:
                _set_flu(feature, flu_code, flu_code, "Sopchoppy", "sopchoppy-flum")
                stats["flu"] += 1
            elif land:
                _set_flu(feature, _clean(land["attrs"].get("LAND_USE")), _clean(land["attrs"].get("LAND_USE")), "Sopchoppy", "wakulla-flu")
                stats["flu"] += 1
        else:
            stats["county"] += 1
            _set_zone(feature, None, None, "Wakulla County", "WAK")
            if land:
                code = _clean(land["attrs"].get("LAND_USE"))
                _set_flu(feature, code, code, "Wakulla County", "wakulla-flu")
                stats["flu"] += 1
        feature["properties"]["dataGaps"] = ["No owner or situs on the county parcel layer."]
        if not feature["properties"].get("zoningCode"):
            feature["properties"]["dataGaps"].append("No zoning polygon contains this parcel.")
    return features, dropped, source_count, stats


def _build_jefferson(seed: Any, county: dict, markets: list[str], spec: dict) -> tuple[list[dict], int, int, dict]:
    raw, source_count = _pull(seed, spec["url"], spec["where"], ["PARCELID", "COGO_ACRES"], batch=60)
    features, dropped = _feature_from_raw(
        seed,
        county,
        markets,
        raw,
        source=spec["source"],
        parcel_id_of=lambda attrs: _clean(attrs.get("PARCELID")),
        acres_of=lambda attrs: _num(attrs.get("COGO_ACRES")),
        appraiser_of=lambda _parcel: "https://jeffersonpa.net/",
    )
    zoning = _safe_index(seed, f"{JEFFERSON_ZONING}/query", "1=1", ["ZONES", "ZONENAME"])
    flum = _safe_index(seed, f"{JEFFERSON_FLUM}/query", "1=1", ["CODE", "CODENAME"])
    city = _safe_index(seed, f"{JEFFERSON_CITY}/query", "1=1", ["CITYBNDYFN"])
    stats = {"monticello": 0, "county": 0, "zoning": 0, "flu": 0}
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        inside = bool(city.hits(lon, lat))
        jurisdiction = "Monticello" if inside else "Jefferson County"
        prefix = "MONT" if inside else "JEFF"
        stats["monticello" if inside else "county"] += 1
        zone = _smallest(zoning.hits(lon, lat)) if inside else None
        land = _smallest(flum.hits(lon, lat)) if inside else None
        code = _clean((zone or {}).get("attrs", {}).get("ZONES")) if zone else None
        district = _clean((zone or {}).get("attrs", {}).get("ZONENAME")) if zone else None
        if district:
            district = district.replace("\\", " / ")
        if code:
            stats["zoning"] += 1
        _set_zone(feature, code, district, jurisdiction, prefix)
        if land:
            stats["flu"] += 1
            _set_flu(
                feature,
                _clean(land["attrs"].get("CODE")),
                _clean(land["attrs"].get("CODENAME")),
                "Monticello",
                "monticello-flum",
            )
        feature["properties"]["dataGaps"] = ["No owner or situs on the county parcel layer."]
        if not inside:
            feature["properties"]["dataGaps"].append("Unincorporated Jefferson County has no public zoning layer.")
    return features, dropped, source_count, stats


def _build_gadsden(seed: Any, county: dict, markets: list[str], spec: dict) -> tuple[list[dict], int, int, dict]:
    fields = [
        "PARCELNO",
        "TOTACRES",
        "OWNER_NAME",
        "HOUSE_NO",
        "STREET",
        "ST_CITY",
        "ST_ZIP5",
        "JUSTVAL",
        "ADDRESS_1",
        "ADDRESS_2",
        "CITY_NAME",
        "ST",
        "ZIPCODE",
    ]
    raw, source_count = _pull(seed, spec["url"], spec["where"], fields, batch=40)
    features, dropped = _feature_from_raw(
        seed,
        county,
        markets,
        raw,
        source=spec["source"],
        parcel_id_of=lambda attrs: _clean(attrs.get("PARCELNO")),
        acres_of=lambda attrs: parse_totacres(attrs.get("TOTACRES")),
        appraiser_of=lambda _parcel: "https://gadsdenpa.com/",
    )
    by_id = {}
    for item in raw:
        parcel_id = _clean((item.get("attributes") or {}).get("PARCELNO"))
        if parcel_id and parcel_id not in by_id:
            by_id[parcel_id] = item.get("attributes") or {}
    quincy_items: list[dict] = []
    for layer_id, name in QUINCY_FLUM_LAYERS:
        try:
            raw_layer, _count = _pull(seed, f"{QUINCY_FLUM_ROOT}/{layer_id}/query", "1=1", ["Category"], batch=50)
        except Exception as exc:  # noqa: BLE001
            print(f"    quincy flum {name} failed: {exc}", flush=True)
            continue
        quincy_items.extend(_polygon_items(raw_layer, {"fluCode": name}))
    quincy = PolyIndex(quincy_items)
    havana = _safe_index(seed, f"{HAVANA_ZONING}/query", "1=1", ["Category"])
    county_items: list[dict] = []
    for layer_id in GADSDEN_FLUM_LAYERS:
        try:
            raw_layer, _count = _pull(
                seed,
                f"{GADSDEN_FLUM_ROOT}/{layer_id}/query",
                "1=1",
                ["ZONE", "Zone_full", "CITY"],
                batch=80,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"    gadsden flum {layer_id} failed: {exc}", flush=True)
            continue
        county_items.extend(_polygon_items(raw_layer))
    county_flu = PolyIndex(county_items)
    stats = {"quincyFlu": 0, "havanaZoning": 0, "countyFlu": 0, "county": 0}
    for feature in features:
        props = feature["properties"]
        attrs = by_id.get(props["parcelId"]) or {}
        props["ownerName"] = _clean(attrs.get("OWNER_NAME"))
        props["situsAddress"] = assemble_situs(attrs.get("HOUSE_NO"), attrs.get("STREET"))
        props["situsCity"] = title_city(attrs.get("ST_CITY"))
        props["situsZip"] = seed.zip_str(attrs.get("ST_ZIP5"))
        just = _num(attrs.get("JUSTVAL"))
        props["tax"] = {
            "marketValue": just if just and just > 0 else None,
            "assessedValue": None,
            "taxableValue": None,
            "taxes": None,
        }
        props["mailingAddress"] = {
            "line1": _clean(attrs.get("ADDRESS_1")),
            "line2": _clean(attrs.get("ADDRESS_2")),
            "city": title_city(attrs.get("CITY_NAME")),
            "state": _clean(attrs.get("ST")),
            "zip": seed.zip_str(attrs.get("ZIPCODE")),
        }
        lon, lat = props["centroid"]
        town = _smallest(havana.hits(lon, lat))
        quin = _smallest(quincy.hits(lon, lat))
        land = _smallest(county_flu.hits(lon, lat))
        if town:
            stats["havanaZoning"] += 1
            category = _clean(town["attrs"].get("Category"))
            _set_zone(feature, category, category, "Havana", "HAV")
        elif quin:
            stats["quincyFlu"] += 1
            _set_zone(feature, None, None, "Quincy", "QUIN")
            props["dataGaps"] = ["Quincy zoning is a PDF, not a zoning code. FLUM is future land use only."]
        else:
            stats["county"] += 1
            _set_zone(feature, None, None, "Gadsden County", "GAD")
            props["dataGaps"] = ["No municipal zoning polygon contains this parcel."]
        if quin:
            code = _clean(quin["attrs"].get("fluCode"))
            # FLUM must not be stored as zoning, even inside Quincy.
            if quincy_flum_is_zoning(code):
                props["zoningCode"] = code
            _set_flu(feature, code, _clean(quin["attrs"].get("Category")) or code, "Quincy", "quincy-flum")
        elif land:
            stats["countyFlu"] += 1
            _set_flu(
                feature,
                _clean(land["attrs"].get("ZONE")),
                _clean(land["attrs"].get("Zone_full")),
                props["jurisdictionCode"] or "Gadsden County",
                "gadsden-flum2",
            )
        if not props.get("dataGaps"):
            props["dataGaps"] = None
    return features, dropped, source_count, stats
