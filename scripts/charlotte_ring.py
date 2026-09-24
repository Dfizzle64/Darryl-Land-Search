"""Charlotte-ring county GIS extracts (5–150 acres) with municipal zoning.

Union, Gaston, Cabarrus, Rowan, Lincoln, and Anson. County parcel polygons
carry ownership, mailing, tax, and last sale. Zoning is joined from the town
layer that actually covers the parcel. NC OneMap is the fallback when a
county host fails. Public GIS only.
"""

from __future__ import annotations

import datetime
import math
import urllib.parse
from collections import defaultdict
from typing import Any

SKIP_ZONE = {"CITY", "MUN", "NONE", "NULL", "NA", "N/A"}
SKIP_FLU = {"MUN", "CITY", "NONE", "NULL", "NA", "N/A"}

UNION_GAPS = [
    "No countywide future land use service. Secrest Short Cut and employment-center scraps are not joined as county FLU.",
    "FMV_LAND and FMV_IMPRV are zero on OperationalLayers parcels; tax totals only. Hemby Bridge has no zoning layer. Mint Hill in Union is negligible and is not joined.",
    "About 78k parcels stub CountyZoning=CITY. Zoning is routed by ParcelCentroids ZoningAdmin to town layers. Legacy gis.unioncountync.gov returns 404; the atlas host is used. Stallings is joined by account number (its service is State Plane).",
]
GASTON_GAPS = [
    "No public future land use service. Envision Gaston 2050 is policy-only. High Shoals, Spencer Mountain, and Dellview have municipal boundaries and no zoning layer.",
    "Zoning is a spatial join to PublicGIS/Zoning in the county CRS. Gastonia cogserver is a different State Plane vintage and is not the join source. Many sale amounts are zero.",
]
CABARRUS_GAPS = [
    "Situs is not on Tax_Parcels polygons; it is joined from AA ParcelAddresses by PIN14. gis.cabarruscounty.us redirects to the map and is not the REST host.",
    "No countywide future land use service. Concord 2030 and Kannapolis Character Areas are joined. Harrisburg, Midland, Mount Pleasant, Locust, and the Huntersville edge have no public FLU layer.",
]
ROWAN_GAPS = [
    "No countywide future land use service. Salisbury FLUM and Kannapolis Character Areas are joined. Other towns and unincorporated Rowan have no public FLU layer.",
    "Zoning is split by municipality on Alll_Zoning. Cleveland is on that service (Municipal_Zoning omits it). No separate assessed-versus-taxable field beyond total value.",
]
LINCOLN_GAPS = [
    "Maiden zoning and future land use are a gap on Lincoln County REST. The town is mostly in Catawba County; Lincoln publishes about one Maiden zoning polygon.",
    "County Blueprint 2043 future land use is joined outside Lincolnton and Maiden. Lincolnton uses the city land-use layer. Parcel ZONING can be overlay-prefixed, so district polygons supply the code.",
]
ANSON_GAPS = [
    "Peachland and Polkton zoning layers are empty. McFarlan has no public zoning service. Those towns stay unmatched.",
    "CountyZoning=Mun. is not a zone class; town layers supply the code. LandUsePlan=MUN is not future land use. No town FLU service is published.",
]


def charlotte_ring_spec(fips: str) -> dict | None:
    specs = {
        "37179": {
            "kind": "charlotte-ring",
            "source": "nc-union-atlas-37179",
            "url": "https://atlas.unioncountync.gov/server/rest/services/OperationalLayers/MapServer/215/query",
            "coverage": "complete-gte-5ac",
            "gaps": list(UNION_GAPS),
        },
        "37071": {
            "kind": "charlotte-ring",
            "source": "nc-gaston-publicgis-37071",
            "url": "https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Parcels/MapServer/11/query",
            "coverage": "complete-gte-5ac",
            "gaps": list(GASTON_GAPS),
        },
        "37025": {
            "kind": "charlotte-ring",
            "source": "nc-cabarrus-tax-parcels-37025",
            "url": "https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/Tax_Parcels/MapServer/1/query",
            "coverage": "complete-gte-5ac",
            "gaps": list(CABARRUS_GAPS),
        },
        "37159": {
            "kind": "charlotte-ring",
            "source": "nc-rowan-open-data-37159",
            "url": "https://gis.rowancountync.gov/arcgis/rest/services/Public/Open_Data_Downloads/MapServer/37/query",
            "coverage": "complete-gte-5ac",
            "gaps": list(ROWAN_GAPS),
        },
        "37109": {
            "kind": "charlotte-ring",
            "source": "nc-lincoln-operational-37109",
            "url": "https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer/6/query",
            "coverage": "complete-gte-5ac",
            "gaps": list(LINCOLN_GAPS),
        },
        "37007": {
            "kind": "charlotte-ring",
            "source": "nc-anson-vector-37007",
            "url": "https://ansoncountygis.com/arcgis/rest/services/Vector/MapServer/10/query",
            "coverage": "complete-gte-5ac",
            "gaps": list(ANSON_GAPS),
        },
    }
    return specs.get(fips)


def download_charlotte_ring(county: dict, markets: list[str], spec: dict) -> dict:
    import seed_market_parcels as seed

    fips = county["fips"]
    cache_path = seed.CACHE_DIR / f"{fips}-charlotte-ring-v1.json"
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = __import__("json").loads(cache_path.read_text())
        features = cached.get("features") or []
        if features and cached.get("version") == 1:
            print(f"  cache hit {len(features)}", flush=True)
            for feature in features:
                feature["properties"]["marketIds"] = markets
            return _finish(seed, county, markets, spec, features, cached.get("gaps") or spec.get("gaps") or [], cached.get("sourceCount"), cached.get("dropped"))
    pullers = {
        "37179": pull_union,
        "37071": pull_gaston,
        "37025": pull_cabarrus,
        "37159": pull_rowan,
        "37109": pull_lincoln,
        "37007": pull_anson,
    }
    print(f"Pulling {county['name']} {county['state']} ({fips}) via {spec['source']}", flush=True)
    try:
        features, gaps, source_count, dropped = pullers[fips](seed, county, markets, spec)
        if len(features) < 1000:
            raise RuntimeError(f"only {len(features)} parcels survived")
    except Exception as exc:  # noqa: BLE001
        print(f"  county GIS failed ({exc}); NC OneMap fallback", flush=True)
        fallback = seed.nc_spec(fips)
        fallback["gaps"] = [
            f"County GIS pull failed ({exc}). Fell back to NC OneMap without municipal zoning.",
            *list(fallback.get("gaps") or []),
        ]
        fallback["ignoreCache"] = True
        return seed.download_county(county, markets, fallback)
    seed.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        __import__("json").dumps(
            {"version": 1, "sourceCount": source_count, "dropped": dropped, "gaps": gaps, "features": features},
            separators=(",", ":"),
        )
    )
    return _finish(seed, county, markets, spec, features, gaps, source_count, dropped)


def _finish(seed, county, markets, spec, features, gaps, source_count, dropped) -> dict:
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{county['fips']} emitted a parcel outside 5–150 acres")
    path, lookup, tiles = seed.write_tiles(county, features)
    print(f"  kept {len(features)}", flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=spec["coverage"],
        partition="tiles",
        path=path,
        lookup=lookup,
        source=spec["source"],
        query_url=spec["url"],
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        tile_count=tiles,
    )


def situs_text(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    if text.upper() in {"NO ASSIGNED ADDRESS", "NONE", "NULL", "0", "N/A"}:
        return None
    return text


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


def positive(value: Any) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def zip_str(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return text[:10]


def attr_get(attrs: dict, name: str) -> Any:
    if name in attrs:
        return attrs[name]
    suffix = "." + name
    upper = name.upper()
    for key, value in attrs.items():
        if key.endswith(suffix) or key.upper().endswith("." + upper) or key.upper() == upper:
            return value
    return None


def usable_zone(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    token = text.upper().rstrip(".")
    if token in SKIP_ZONE:
        return None
    return text


def usable_flu(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    if text.upper().rstrip(".") in SKIP_FLU:
        return None
    return text


def arcgis_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
        ms = float(value)
        sec = ms / 1000.0 if ms > 10_000_000_000 else ms
        if sec < 1_000_000_000:
            return None
        dt = datetime.datetime.fromtimestamp(sec, datetime.timezone.utc)
        if 1900 <= dt.year <= 2100:
            return dt.strftime("%Y-%m-%d")
        return None
    text = str(value).strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    if len(text) >= 10 and text[4] == "-":
        return text[:10]
    return None


def flu_info(code: str | None, label: str | None, jurisdiction: str | None, source: str) -> dict | None:
    if not code and not label:
        return None
    return {"code": code or label, "label": label or code, "jurisdiction": jurisdiction, "source": source}


def point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        if (yi > y) != (yj > y):
            denom = (yj - yi) or 1e-12
            if x < (xj - xi) * (y - yi) / denom + xi:
                inside = not inside
        j = i
    return inside


def point_in_rings(x: float, y: float, rings: list) -> bool:
    hits = 0
    for ring in rings:
        if len(ring) >= 4 and point_in_ring(x, y, ring):
            hits += 1
    return hits % 2 == 1


class GridIndex:
    def __init__(self, items: list[tuple], cell: float = 0.03):
        self.cell = cell
        self.buckets: dict[tuple, list] = defaultdict(list)
        for item in items:
            minx, miny, maxx, maxy = item[0], item[1], item[2], item[3]
            ix0, ix1 = math.floor(minx / cell), math.floor(maxx / cell)
            iy0, iy1 = math.floor(miny / cell), math.floor(maxy / cell)
            if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 48:
                self.buckets[("big",)].append(item)
                continue
            for ix in range(ix0, ix1 + 1):
                for iy in range(iy0, iy1 + 1):
                    self.buckets[(ix, iy)].append(item)

    def hit(self, x: float, y: float) -> Any:
        found = self.hit_area(x, y)
        return None if found is None else found[0]

    def hit_area(self, x: float, y: float) -> tuple[Any, float] | None:
        ix, iy = math.floor(x / self.cell), math.floor(y / self.cell)
        best = None
        best_area = None
        for item in self.buckets.get((ix, iy), []) + self.buckets.get(("big",), []):
            minx, miny, maxx, maxy, area, rings, payload = item
            if x < minx or x > maxx or y < miny or y > maxy:
                continue
            if not point_in_rings(x, y, rings):
                continue
            if best is None or area < best_area:
                best = payload
                best_area = area
        if best is None:
            return None
        return best, best_area


def index_polygons(features: list[dict], fields: list[str]) -> GridIndex:
    items = []
    for feat in features:
        attrs = feat.get("attributes") or {}
        payload = None
        for field in fields:
            payload = usable_zone(attr_get(attrs, field))
            if payload:
                break
        if not payload:
            continue
        rings = (feat.get("geometry") or {}).get("rings") or []
        if not rings:
            continue
        xs: list[float] = []
        ys: list[float] = []
        for ring in rings:
            for x, y in ring:
                xs.append(float(x))
                ys.append(float(y))
        if not xs:
            continue
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        items.append((minx, miny, maxx, maxy, (maxx - minx) * (maxy - miny), rings, payload))
    return GridIndex(items)


def index_labels(features: list[dict], field: str) -> GridIndex:
    items = []
    for feat in features:
        label = clean(attr_get(feat.get("attributes") or {}, field))
        rings = (feat.get("geometry") or {}).get("rings") or []
        if not label or not rings:
            continue
        xs: list[float] = []
        ys: list[float] = []
        for ring in rings:
            for x, y in ring:
                xs.append(float(x))
                ys.append(float(y))
        if not xs:
            continue
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        items.append((minx, miny, maxx, maxy, (maxx - minx) * (maxy - miny), rings, label))
    return GridIndex(items)


def hit_smallest(layers: list[tuple[str, GridIndex]], x: float, y: float) -> tuple[str | None, Any]:
    best_name = None
    best_payload = None
    best_area = None
    for name, index in layers:
        found = index.hit_area(x, y)
        if found and (best_area is None or found[1] < best_area):
            best_payload, best_area = found
            best_name = name
    return best_name, best_payload


def load_polygons(seed, url: str, fields: list[str], where: str = "1=1") -> list[dict]:
    ids = seed.fetch_object_ids(url, where)
    if not ids and where == "1=1":
        ids = seed.fetch_object_ids(url, "OBJECTID>=0")
    print(f"    polygons {len(ids)} {url.split('/rest/services/')[-1][:72]}", flush=True)
    if not ids:
        return []
    return seed.fetch_by_ids(url, ids, fields, batch=80, geometry=True)


def load_parcels(seed, url: str, where: str, fields: list[str]) -> list[dict]:
    ids = seed.fetch_object_ids(url, where)
    print(f"    parcel ids {len(ids)}", flush=True)
    if not ids:
        raise RuntimeError(f"no parcel ids for {where}")
    return seed.fetch_by_ids(url, ids, fields, batch=50, geometry=True)


def page_attrs(seed, url: str, where: str, fields: list[str], page: int = 2000) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    seen: set[str] = set()
    while True:
        params = {
            "where": where,
            "outFields": ",".join(fields),
            "returnGeometry": "false",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": page,
            "orderByFields": "OBJECTID",
        }
        try:
            data = seed.fetch_json(url, params, timeout=180)
        except RuntimeError:
            params.pop("orderByFields")
            data = seed.fetch_json(url, params, timeout=180)
        if data.get("error"):
            raise RuntimeError(str(data["error"])[:240])
        feats = data.get("features") or []
        if not feats:
            break
        marker = str((feats[0].get("attributes") or {}).get("OBJECTID") or (feats[0].get("attributes") or {}))
        if offset and marker in seen:
            raise RuntimeError("attribute page repeated")
        seen.add(marker)
        rows.extend(feats)
        print(f"    attrs {len(rows)}", flush=True)
        if len(feats) < page and not data.get("exceededTransferLimit"):
            break
        offset += len(feats)
        if offset > 400000:
            break
    return rows


def load_attrs(seed, url: str, where: str, fields: list[str]) -> list[dict]:
    try:
        rows = page_attrs(seed, url, where, fields)
        if rows:
            return rows
    except Exception as exc:  # noqa: BLE001
        print(f"    attr page failed ({exc}); object ids", flush=True)
    ids = seed.fetch_object_ids(url, where)
    if not ids and where == "1=1":
        ids = seed.fetch_object_ids(url, "OBJECTID>=0")
    if not ids:
        return []
    return seed.fetch_by_ids(url, ids, fields, batch=400, geometry=False)


def norm_admin(value: Any) -> str:
    text = clean(value) or ""
    text = " ".join(text.upper().replace(".", " ").split())
    for prefix in ("TOWN OF ", "CITY OF "):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    aliases = {
        "MT HOLLY": "MOUNT HOLLY",
        "KINGS MTN": "KINGS MOUNTAIN",
        "KINGS MT": "KINGS MOUNTAIN",
        "EAST SPENCER": "EAST SPENCER",
        "CHINA GROVE": "CHINA GROVE",
        "GRANITE QUARRY": "GRANITE QUARRY",
        "MOUNT PLEASANT": "MOUNT PLEASANT",
        "MT PLEASANT": "MOUNT PLEASANT",
    }
    return aliases.get(text, text)


def quote_url(template: str, **values: str) -> str:
    return template.format(**{key: urllib.parse.quote(value, safe="") for key, value in values.items()})


def geometry_of(seed, item: dict):
    geometry, _computed = seed.rings_to_feature_geometry(item.get("geometry"))
    if not geometry:
        return None, None
    center = seed.centroid_of(geometry)
    if not seed.plausible_centroid(center):
        return None, None
    return geometry, center


def base_feature(seed, county, markets, source, parcel_id, acres, geometry, center, gaps, **kwargs):
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
        data_gaps=gaps,
        **kwargs,
    )
    return feature


def publish_stats(features: list[dict], gaps: list[str], sentence: str) -> list[str]:
    """Attach the post-dedupe join sentence. One list is shared; do not append after this."""
    cleaned = [gap for gap in gaps if not str(gap).startswith("Zoning joined")]
    cleaned.append(sentence)
    for feature in features:
        feature["properties"]["dataGaps"] = cleaned
    return cleaned


def dedupe(features: list[dict]) -> tuple[list[dict], int]:
    by_id: dict[str, dict] = {}
    dropped = 0
    for feature in features:
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None:
            by_id[parcel_id] = feature
        elif (feature["properties"].get("acreage") or 0) > (previous["properties"].get("acreage") or 0):
            by_id[parcel_id] = feature
            dropped += 1
        else:
            dropped += 1
    rows = list(by_id.values())
    rows.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return rows, dropped


def pull_union(seed, county, markets, spec):
    raw = load_parcels(
        seed,
        spec["url"],
        "mapped_acres>=5 AND mapped_acres<=150",
        [
            "PID",
            "ACCTNO",
            "mapped_acres",
            "CURR_NAME1",
            "CURR_NAME2",
            "CURR_ADDR1",
            "CURR_ADDR2",
            "CURR_CITY",
            "CURR_STATE",
            "CURR_ZIPCODE",
            "PHYSSTRADD",
            "s1_SALEDATE",
            "s1_SALESAMT",
            "s1_DEEDQUAL_CODEDESC",
            "TOTVAL",
            "FMV_TOTAL",
            "property_use",
            "DESC1_DESC",
        ],
    )
    centroids = {}
    for row in load_attrs(
        seed,
        "https://atlas.unioncountync.gov/server/rest/services/ParcelCentroids/MapServer/0/query",
        "1=1",
        ["PID", "CountyZoning", "ZoningAdmin"],
    ):
        attrs = row.get("attributes") or {}
        pid = clean(attrs.get("PID"))
        if pid:
            centroids[pid] = attrs
    attr_layers = {
        "WAXHAW": (
            "https://services2.arcgis.com/Sa3FPjCP8681JQgz/arcgis/rest/services/Official_Zoning_gdb/FeatureServer/0/query",
            ["PID", "ACCTNO"],
            "Zoning",
        ),
        "STALLINGS": (
            "https://services8.arcgis.com/eIIzSLwZoq8C0D6F/arcgis/rest/services/Zoning_Map/FeatureServer/7/query",
            ["ACCTNO"],
            "CurrentZon",
        ),
        "INDIAN TRAIL": (
            "https://atlas.unioncountync.gov/server/rest/services/OperationalLayers/MapServer/174/query",
            ["ACCTNO"],
            "NEW_ZONIN",
        ),
        "UNIONVILLE": (
            "https://atlas.unioncountync.gov/server/rest/services/UNION_COUNTY_LAYERS/MapServer/182/query",
            ["ACCTNO"],
            "zoning",
        ),
        "MARSHVILLE": (
            "https://atlas.unioncountync.gov/server/rest/services/OperationalLayers/MapServer/176/query",
            ["ACCTNO"],
            "Zoning",
        ),
    }
    attr_maps: dict[str, dict[str, str]] = {}
    for admin, (url, keys, field) in attr_layers.items():
        mapping: dict[str, str] = {}
        for row in load_attrs(seed, url, "1=1", [*keys, field]):
            attrs = row.get("attributes") or {}
            zone = usable_zone(attr_get(attrs, field))
            if not zone:
                continue
            for key in keys:
                pid = clean(attr_get(attrs, key))
                if pid:
                    mapping[pid] = zone
        attr_maps[admin] = mapping
        print(f"    {admin} attr {len(mapping)}", flush=True)
    spatial_specs = {
        "MONROE": ("https://atlas.unioncountync.gov/server/rest/services/OperationalLayers/MapServer/180/query", ["NEW_ZONING"]),
        "WEDDINGTON": ("https://atlas.unioncountync.gov/server/rest/services/OperationalLayers/MapServer/184/query", ["ZONE"]),
        "WESLEY CHAPEL": ("https://atlas.unioncountync.gov/server/rest/services/UNION_COUNTY_LAYERS/MapServer/185/query", ["ZONE"]),
        "WINGATE": ("https://atlas.unioncountync.gov/server/rest/services/OperationalLayers/MapServer/186/query", ["ZONE"]),
        "MARVIN": ("https://atlas.unioncountync.gov/server/rest/services/OperationalLayers/MapServer/177/query", ["Marvin_Zon"]),
        "FAIRVIEW": ("https://atlas.unioncountync.gov/server/rest/services/OperationalLayers/MapServer/173/query", ["ZONE"]),
        "MINERAL SPRINGS": ("https://atlas.unioncountync.gov/server/rest/services/UNION_COUNTY_LAYERS/MapServer/178/query", ["ZoneDesc"]),
        "LAKE PARK": ("https://atlas.unioncountync.gov/server/rest/services/OperationalLayers/MapServer/175/query", ["LP_Zone"]),
    }
    spatial = {name: index_polygons(load_polygons(seed, url, fields), fields) for name, (url, fields) in spatial_specs.items()}
    gaps = list(UNION_GAPS)
    features = []
    dropped = 0
    zoned = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        acres = num(attrs.get("mapped_acres"))
        geometry, center = geometry_of(seed, item)
        pid = clean(attrs.get("PID")) or clean(attrs.get("ACCTNO"))
        if not geometry or not center or not pid or not seed.in_band(acres):
            dropped += 1
            continue
        cent = centroids.get(pid) or {}
        admin = norm_admin(cent.get("ZoningAdmin"))
        district = clean(cent.get("ZoningAdmin"))
        zone = None
        if admin in {"", "UNION COUNTY"}:
            zone = usable_zone(cent.get("CountyZoning"))
            district = district or "Union County"
        elif admin in attr_maps:
            zone = attr_maps[admin].get(pid) or attr_maps[admin].get(clean(attrs.get("ACCTNO")) or "")
        elif admin in spatial:
            zone = spatial[admin].hit(center[0], center[1])
        elif admin in {"HEMBY BRIDGE", "MINT HILL"}:
            zone = None
        if zone:
            zoned += 1
        features.append(
            base_feature(
                seed,
                county,
                markets,
                spec["source"],
                pid,
                acres,
                geometry,
                center,
                gaps,
                owner=clean(attrs.get("CURR_NAME1")),
                owner2=clean(attrs.get("CURR_NAME2")),
                situs=situs_text(attrs.get("PHYSSTRADD")),
                zoning=zone,
                zoning_district=district,
                jurisdiction=district,
                dor=clean(attrs.get("property_use")),
                sale_price=positive(attrs.get("s1_SALESAMT")),
                sale_date=arcgis_date(attrs.get("s1_SALEDATE")),
                sale_qualified=clean(attrs.get("s1_DEEDQUAL_CODEDESC")),
                market_value=positive(attrs.get("FMV_TOTAL")),
                assessed=positive(attrs.get("TOTVAL")),
                taxable=positive(attrs.get("TOTVAL")),
                mail1=clean(attrs.get("CURR_ADDR1")),
                mail2=clean(attrs.get("CURR_ADDR2")),
                mail_city=clean(attrs.get("CURR_CITY")),
                mail_state=clean(attrs.get("CURR_STATE")),
                mail_zip=zip_str(attrs.get("CURR_ZIPCODE")),
                appraiser_url=quote_url("https://unionnc.devnetwedge.com/parcel/view/{pid}", pid=pid),
            )
        )
    features, extra = dedupe(features)
    zoned = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    gaps = publish_stats(
        features,
        gaps,
        f"Zoning joined on {zoned} of {len(features)} parcels in the 5–150 acre band.",
    )
    return features, gaps, len(raw), dropped + extra


def pull_gaston(seed, county, markets, spec):
    raw = load_parcels(
        seed,
        spec["url"],
        "CALCAC>=5 AND CALCAC<=150",
        [
            "AKPAR",
            "PIN",
            "PID",
            "CALCAC",
            "CURR_NAME1",
            "CURR_NAME2",
            "CURR_ADDR1",
            "CURR_ADDR2",
            "CURR_CITY",
            "CURR_STATE",
            "CURR_ZIPCODE",
            "WHOLE_ADDRESS",
            "POSTAL",
            "STATE",
            "ZIP",
            "SALEDATE",
            "SALESAMT",
            "FMV_TOTAL",
            "TOTVAL",
            "property_use",
            "DEEDQUAL_CODEDESC",
        ],
    )
    host = "https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Zoning/MapServer"
    city_specs = [
        ("Gastonia", f"{host}/2/query", ["ZONING", "ZONE_"]),
        ("Belmont", f"{host}/11/query", ["TYPE"]),
        ("Bessemer City", f"{host}/7/query", ["TYPE"]),
        ("Cherryville", f"{host}/13/query", ["TYPE"]),
        ("Cramerton", f"{host}/14/query", ["TYPE"]),
        ("Dallas", f"{host}/15/query", ["TYPE"]),
        ("Kings Mountain", f"{host}/19/query", ["TYPE"]),
        ("Lowell", f"{host}/9/query", ["TYPE"]),
        ("McAdenville", f"{host}/10/query", ["TYPE"]),
        ("Mount Holly", f"{host}/16/query", ["TYPE"]),
        ("Ranlo", f"{host}/20/query", ["TYPE"]),
        ("Stanley", f"{host}/17/query", ["TYPE"]),
    ]
    cities = [(name, index_polygons(load_polygons(seed, url, fields), fields)) for name, url, fields in city_specs]
    udo = index_polygons(
        load_polygons(seed, f"{host}/1/query", ["TYPE"]),
        ["TYPE"],
    )
    holly = index_polygons(
        load_polygons(
            seed,
            "https://services7.arcgis.com/R3hvotzf6HmfdzVd/arcgis/rest/services/Zoning_Auth/FeatureServer/0/query",
            ["Zone_Abbv"],
        ),
        ["Zone_Abbv"],
    )
    munis = index_labels(
        load_polygons(
            seed,
            "https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Municipalities/MapServer/18/query",
            ["NAME"],
        ),
        "NAME",
    )
    gap_towns = {"HIGH SHOALS", "SPENCER MTN", "SPENCER MOUNTAIN", "DELLVIEW"}
    gaps = list(GASTON_GAPS)
    features = []
    dropped = 0
    zoned = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        acres = num(attrs.get("CALCAC"))
        geometry, center = geometry_of(seed, item)
        parcel_id = clean(attrs.get("AKPAR")) or clean(attrs.get("PID")) or clean(attrs.get("PIN"))
        if not geometry or not center or not parcel_id or not seed.in_band(acres):
            dropped += 1
            continue
        x, y = center
        muni = norm_admin(munis.hit(x, y))
        district, zone = hit_smallest(cities, x, y)
        if district == "Mount Holly":
            richer = holly.hit(x, y)
            if richer:
                zone = richer
        if not zone and muni not in gap_towns:
            zone = udo.hit(x, y)
            if zone:
                district = "Gaston County"
        elif muni in gap_towns and not zone:
            district = clean(munis.hit(x, y)) or district
            zone = None
        if zone:
            zoned += 1
        features.append(
            base_feature(
                seed,
                county,
                markets,
                spec["source"],
                parcel_id,
                acres,
                geometry,
                center,
                gaps,
                owner=clean(attrs.get("CURR_NAME1")),
                owner2=clean(attrs.get("CURR_NAME2")),
                situs=situs_text(attrs.get("WHOLE_ADDRESS")),
                city=clean(attrs.get("POSTAL")),
                zip_code=zip_str(attrs.get("ZIP")),
                zoning=zone,
                zoning_district=district,
                jurisdiction=district,
                dor=clean(attrs.get("property_use")),
                sale_price=positive(attrs.get("SALESAMT")),
                sale_date=arcgis_date(attrs.get("SALEDATE")),
                sale_qualified=clean(attrs.get("DEEDQUAL_CODEDESC")),
                market_value=positive(attrs.get("FMV_TOTAL")),
                assessed=positive(attrs.get("TOTVAL")),
                taxable=positive(attrs.get("TOTVAL")),
                mail1=clean(attrs.get("CURR_ADDR1")),
                mail2=clean(attrs.get("CURR_ADDR2")),
                mail_city=clean(attrs.get("CURR_CITY")),
                mail_state=clean(attrs.get("CURR_STATE")),
                mail_zip=zip_str(attrs.get("CURR_ZIPCODE")),
                appraiser_url=quote_url("https://gastonnc.devnetwedge.com/parcel/view/{pid}", pid=parcel_id),
            )
        )
    features, extra = dedupe(features)
    zoned = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    gaps = publish_stats(
        features,
        gaps,
        f"Zoning joined on {zoned} of {len(features)} parcels in the 5–150 acre band.",
    )
    return features, gaps, len(raw), dropped + extra


def pull_cabarrus(seed, county, markets, spec):
    raw = load_parcels(
        seed,
        spec["url"],
        "CALCULATED_ACREAGE>=5 AND CALCULATED_ACREAGE<=150 AND PIN14 IS NOT NULL",
        [
            "PIN14",
            "PIN",
            "CALCULATED_ACREAGE",
            "AcctName1",
            "AcctName2",
            "MailAddr1",
            "MailAddr2",
            "MailCity",
            "MailState",
            "MailZipCode",
            "SaleYear",
            "SaleMonth",
            "SalePrice",
            "QualifiedCode",
            "MarketValue",
            "AssessedValue",
        ],
    )
    addresses: dict[str, dict] = {}
    for row in load_attrs(
        seed,
        "https://location.cabarruscounty.us/arcgishost/rest/services/AA/MapServer/1/query",
        "PIN14 IS NOT NULL AND Full_con_cat IS NOT NULL",
        ["PIN14", "Full_con_cat", "City", "Zip"],
    ):
        attrs = row.get("attributes") or {}
        pin = clean(attrs.get("PIN14"))
        line = clean(attrs.get("Full_con_cat"))
        if not pin or not line:
            continue
        previous = addresses.get(pin)
        line = situs_text(line)
        if not line:
            continue
        if previous is None or _prefer_address(line, previous["line"]):
            addresses[pin] = {"line": line, "city": clean(attrs.get("City")), "zip": zip_str(attrs.get("Zip"))}
    print(f"    situs pins {len(addresses)}", flush=True)
    host = "https://location.cabarruscounty.us/arcgisservices/rest/services/Zoning/MapServer"
    kannapolis = index_polygons(
        load_polygons(
            seed,
            "https://maps.kannapolisnc.gov/arcgis/rest/services/Official_City_Zoning/MapServer/0/query",
            ["ZONINGCODE"],
        ),
        ["ZONINGCODE"],
    )
    cities = [
        ("Concord", index_polygons(load_polygons(seed, f"{host}/6/query", ["*"]), ["ZONINGCODE"])),
        ("Harrisburg", index_polygons(load_polygons(seed, f"{host}/5/query", ["*"]), ["ZONINGCODE"])),
        ("Midland", index_polygons(load_polygons(seed, f"{host}/2/query", ["*"]), ["ZONINGCODE"])),
        ("Mount Pleasant", index_polygons(load_polygons(seed, f"{host}/1/query", ["*"]), ["ZONINGCODE"])),
        ("Locust", index_polygons(load_polygons(seed, f"{host}/3/query", ["*"]), ["ZONINGCODE"])),
        ("Kannapolis", kannapolis),
    ]
    kannapolis_county = index_polygons(load_polygons(seed, f"{host}/4/query", ["*"]), ["ZONINGCODE", "BASE_DISTR"])
    county_zone = index_polygons(load_polygons(seed, f"{host}/7/query", ["*"]), ["ZONINGCODE"])
    districts = index_labels(
        load_polygons(
            seed,
            "https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/MunicipalDistrict/MapServer/0/query",
            ["DISTRICT"],
        ),
        "DISTRICT",
    )
    concord_flu = _labeled_index(
        load_polygons(
            seed,
            "https://services2.arcgis.com/0esqB0FgvL32hAbY/arcgis/rest/services/GeocortexZoningStaff_WFL1/FeatureServer/63/query",
            ["Code", "Category"],
        ),
        "Code",
        "Category",
    )
    character = _labeled_index(
        load_polygons(
            seed,
            "https://services6.arcgis.com/U9SsvkRoA6RuruHj/arcgis/rest/services/CharacterUses/FeatureServer/0/query",
            ["Char_Dist", "LabelName"],
        ),
        "Char_Dist",
        "LabelName",
    )
    gaps = list(CABARRUS_GAPS)
    features = []
    dropped = 0
    zoned = 0
    sited = 0
    flu_n = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        acres = num(attrs.get("CALCULATED_ACREAGE"))
        geometry, center = geometry_of(seed, item)
        pin = clean(attrs.get("PIN14"))
        pin_raw = clean(attrs.get("PIN"))
        if pin_raw in {None, "0.00000000", "0"}:
            pin = None
        if not geometry or not center or not pin or not seed.in_band(acres):
            dropped += 1
            continue
        x, y = center
        district_name = clean(districts.hit(x, y))
        admin = norm_admin(district_name)
        district, zone = hit_smallest(cities, x, y)
        if not zone:
            zone = kannapolis_county.hit(x, y)
            if zone:
                district = "Kannapolis"
        if not zone and admin != "HUNTERSVILLE":
            zone = county_zone.hit(x, y)
            if zone:
                district = "Cabarrus County"
        if admin == "HUNTERSVILLE" and district == "Cabarrus County":
            zone = None
            district = district_name
        flu = None
        if district == "Concord":
            found = concord_flu.hit(x, y)
            if found:
                flu = flu_info(found[0], found[1], "Concord", "concord-lu-2030")
        elif district == "Kannapolis":
            found = character.hit(x, y)
            if found:
                flu = flu_info(found[0], found[1], "Kannapolis", "kannapolis-character-areas")
        situs = addresses.get(pin)
        if situs:
            sited += 1
        if zone:
            zoned += 1
        if flu:
            flu_n += 1
        sale_year = attrs.get("SaleYear")
        features.append(
            base_feature(
                seed,
                county,
                markets,
                spec["source"],
                pin,
                acres,
                geometry,
                center,
                gaps,
                owner=clean(attrs.get("AcctName1")),
                owner2=clean(attrs.get("AcctName2")),
                situs=situs["line"] if situs else None,
                city=situs["city"] if situs else None,
                zip_code=situs["zip"] if situs else None,
                zoning=zone,
                zoning_district=district or district_name,
                jurisdiction=district or district_name,
                sale_price=positive(attrs.get("SalePrice")),
                sale_date=seed.sale_date(sale_year, attrs.get("SaleMonth")),
                sale_qualified=clean(attrs.get("QualifiedCode")),
                market_value=positive(attrs.get("MarketValue")),
                assessed=positive(attrs.get("AssessedValue")),
                mail1=clean(attrs.get("MailAddr1")),
                mail2=clean(attrs.get("MailAddr2")),
                mail_city=clean(attrs.get("MailCity")),
                mail_state=clean(attrs.get("MailState")),
                mail_zip=zip_str(attrs.get("MailZipCode")),
                appraiser_url="https://tax.cabarruscounty.us/BasicSearch.aspx",
                flu=flu,
            )
        )
    features, extra = dedupe(features)
    zoned = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    sited = sum(1 for feature in features if feature["properties"].get("situsAddress"))
    flu_n = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    gaps = publish_stats(
        features,
        gaps,
        f"Zoning joined on {zoned} of {len(features)} parcels. Situs joined on {sited}. Future land use joined on {flu_n} (Concord and Kannapolis only).",
    )
    return features, gaps, len(raw), dropped + extra


def _prefer_address(candidate: str, current: str) -> bool:
    def noisy(text: str) -> bool:
        upper = text.upper()
        return any(token in upper for token in (" UNIT ", " APT ", " STE ", " SUITE ", " #"))

    if noisy(current) and not noisy(candidate):
        return True
    if noisy(candidate) and not noisy(current):
        return False
    return len(candidate) < len(current)


def _flu_label_index(features: list[dict], code_field: str, label_field: str) -> dict[str, str]:
    labels = {}
    for feat in features:
        attrs = feat.get("attributes") or {}
        code = usable_flu(attr_get(attrs, code_field)) or usable_zone(attr_get(attrs, code_field))
        label = clean(attr_get(attrs, label_field))
        if code and label:
            labels[code] = label
    return labels


def _labeled_index(features: list[dict], code_field: str, label_field: str) -> GridIndex:
    items = []
    for feat in features:
        attrs = feat.get("attributes") or {}
        code = usable_flu(attr_get(attrs, code_field))
        label = clean(attr_get(attrs, label_field))
        rings = (feat.get("geometry") or {}).get("rings") or []
        if not code or not rings:
            continue
        xs: list[float] = []
        ys: list[float] = []
        for ring in rings:
            for x, y in ring:
                xs.append(float(x))
                ys.append(float(y))
        if not xs:
            continue
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        items.append((minx, miny, maxx, maxy, (maxx - minx) * (maxy - miny), rings, (code, label)))
    return GridIndex(items)


def pull_rowan(seed, county, markets, spec):
    raw = load_parcels(
        seed,
        spec["url"],
        "CALCACRE>=5 AND CALCACRE<=150",
        [
            "PARCEL_ID",
            "PIN",
            "CALCACRE",
            "OWNNAME",
            "OWN2",
            "TAXADD1",
            "TAXADD2",
            "CITY",
            "STATE",
            "ZIPCODE",
            "PROP_ADDRESS",
            "DATESOLD",
            "SALE_AMT",
            "QUALCODE",
            "TOT_VAL",
        ],
    )
    host = "https://gis.rowancountync.gov/arcgis/rest/services/Public/Alll_Zoning/MapServer"
    kannapolis = index_polygons(
        load_polygons(
            seed,
            "https://maps.kannapolisnc.gov/arcgis/rest/services/Official_City_Zoning/MapServer/0/query",
            ["ZONINGCODE"],
        ),
        ["ZONINGCODE"],
    )
    cities = [
        ("Salisbury", index_polygons(load_polygons(seed, f"{host}/2/query", ["ZONING"]), ["ZONING"])),
        ("Kannapolis", kannapolis),
        ("Cleveland", index_polygons(load_polygons(seed, f"{host}/4/query", ["District"]), ["District"])),
        ("Landis", index_polygons(load_polygons(seed, f"{host}/5/query", ["ZONING"]), ["ZONING"])),
        ("Faith", index_polygons(load_polygons(seed, f"{host}/6/query", ["TYPE"]), ["TYPE"])),
        ("China Grove", index_polygons(load_polygons(seed, f"{host}/7/query", ["CLASSIFCAT"]), ["CLASSIFCAT"])),
        ("Rockwell", index_polygons(load_polygons(seed, f"{host}/8/query", ["TYPE"]), ["TYPE"])),
        ("Spencer", index_polygons(load_polygons(seed, f"{host}/9/query", ["TYPE"]), ["TYPE"])),
        ("East Spencer", index_polygons(load_polygons(seed, f"{host}/10/query", ["ZoningClas"]), ["ZoningClas"])),
        ("Granite Quarry", index_polygons(load_polygons(seed, f"{host}/11/query", ["ZONING"]), ["ZONING"])),
    ]
    kannapolis_county = index_polygons(load_polygons(seed, f"{host}/3/query", ["basedist"]), ["basedist"])
    county_zone = index_polygons(load_polygons(seed, f"{host}/12/query", ["ZONING"]), ["ZONING"])
    salisbury_flu = index_polygons(
        load_polygons(seed, "https://gis.salisburync.gov/arcgis/rest/services/EnerGov/MapServer/5/query", ["FLUM"]),
        ["FLUM"],
    )
    character = _labeled_index(
        load_polygons(
            seed,
            "https://services6.arcgis.com/U9SsvkRoA6RuruHj/arcgis/rest/services/CharacterUses/FeatureServer/0/query",
            ["Char_Dist", "LabelName"],
        ),
        "Char_Dist",
        "LabelName",
    )
    gaps = list(ROWAN_GAPS)
    features = []
    dropped = 0
    zoned = 0
    flu_n = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        acres = num(attrs.get("CALCACRE"))
        geometry, center = geometry_of(seed, item)
        parcel_id = clean(attrs.get("PARCEL_ID")) or clean(attrs.get("PIN"))
        if not geometry or not center or not parcel_id or not seed.in_band(acres):
            dropped += 1
            continue
        x, y = center
        district, zone = hit_smallest(cities, x, y)
        if not zone:
            zone = kannapolis_county.hit(x, y)
            if zone:
                district = "Kannapolis"
        if not zone:
            zone = county_zone.hit(x, y)
            if zone:
                district = "Rowan County"
        flu = None
        if district == "Salisbury":
            code = salisbury_flu.hit(x, y)
            if code:
                flu = flu_info(code, code, "Salisbury", "salisbury-flum")
        elif district == "Kannapolis":
            found = character.hit(x, y)
            if found:
                flu = flu_info(found[0], found[1], "Kannapolis", "kannapolis-character-areas")
        if zone:
            zoned += 1
        if flu:
            flu_n += 1
        total = positive(attrs.get("TOT_VAL"))
        features.append(
            base_feature(
                seed,
                county,
                markets,
                spec["source"],
                parcel_id,
                acres,
                geometry,
                center,
                gaps,
                owner=clean(attrs.get("OWNNAME")),
                owner2=clean(attrs.get("OWN2")),
                situs=situs_text(attrs.get("PROP_ADDRESS")),
                zoning=zone,
                zoning_district=district,
                jurisdiction=district,
                sale_price=positive(attrs.get("SALE_AMT")),
                sale_date=arcgis_date(attrs.get("DATESOLD")),
                sale_qualified=clean(attrs.get("QUALCODE")),
                market_value=total,
                assessed=total,
                mail1=clean(attrs.get("TAXADD1")),
                mail2=clean(attrs.get("TAXADD2")),
                mail_city=clean(attrs.get("CITY")),
                mail_state=clean(attrs.get("STATE")),
                mail_zip=zip_str(attrs.get("ZIPCODE")),
                appraiser_url="https://tax.rowancountync.gov/search/commonsearch.aspx?mode=realprop",
                flu=flu,
            )
        )
    features, extra = dedupe(features)
    zoned = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_n = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    gaps = publish_stats(
        features,
        gaps,
        f"Zoning joined on {zoned} of {len(features)} parcels. Future land use joined on {flu_n} (Salisbury and Kannapolis only).",
    )
    return features, gaps, len(raw), dropped + extra


def pull_lincoln(seed, county, markets, spec):
    raw = load_parcels(
        seed,
        spec["url"],
        "MAPPEDACRE>=5 AND MAPPEDACRE<=150",
        [
            "PIN",
            "PARCELID",
            "AKPAR_",
            "MAPPEDACRE",
            "NAME1",
            "NAME2",
            "ADDRESS1",
            "ADDRESS2",
            "CITY",
            "STATE",
            "ZIP",
            "PHYSICALADDR",
            "SDATE",
            "SALEPRICE",
            "QUALIFIEDCODE",
            "TOTALVALUE",
            "ZONING",
        ],
    )
    base = "https://arcgisserver.lincolncountync.gov/arcgis/rest/services/Server_OperationalSP/MapServer"
    lincolnton = index_polygons(load_polygons(seed, f"{base}/23/query", ["ZONECODE"]), ["ZONECODE"])
    county_zone = index_polygons(load_polygons(seed, f"{base}/25/query", ["ZONECODE"]), ["ZONECODE"])
    place_rows = []
    for feat in load_polygons(seed, f"{base}/16/query", ["NAME", "TYPE"]):
        name = norm_admin(attr_get(feat.get("attributes") or {}, "NAME"))
        if "MAIDEN" in name or "LINCOLNTON" in name:
            place_rows.append(feat)
    places = index_labels(place_rows, "NAME")
    city_flu = _labeled_index(
        load_polygons(seed, f"{base}/38/query", ["LANDUSECODE", "LANDUSEDESC"]),
        "LANDUSECODE",
        "LANDUSEDESC",
    )
    county_flu = _labeled_index(
        load_polygons(seed, f"{base}/35/query", ["LUP_2022", "Label"]),
        "LUP_2022",
        "Label",
    )
    gaps = list(LINCOLN_GAPS)
    features = []
    dropped = 0
    zoned = 0
    flu_n = 0
    maiden_n = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        acres = num(attrs.get("MAPPEDACRE"))
        geometry, center = geometry_of(seed, item)
        pin = clean(attrs.get("PIN"))
        if not geometry or not center or not pin or not seed.in_band(acres):
            dropped += 1
            continue
        x, y = center
        place = norm_admin(places.hit(x, y))
        zone = None
        district = None
        flu = None
        if "MAIDEN" in place:
            maiden_n += 1
            district = "Maiden"
        elif "LINCOLNTON" in place:
            zone = lincolnton.hit(x, y)
            district = "Lincolnton"
            found = city_flu.hit(x, y)
            if found:
                flu = flu_info(found[0], found[1], "Lincolnton", "lincolnton-land-use")
        else:
            zone = county_zone.hit(x, y)
            district = "Lincoln County"
            found = county_flu.hit(x, y)
            if found:
                flu = flu_info(found[0], found[1], "Lincoln County", "lincoln-blueprint-2043")
        if not zone and "MAIDEN" not in place:
            zone = usable_zone(attrs.get("ZONING"))
        if zone:
            zoned += 1
        if flu:
            flu_n += 1
        account = clean(attrs.get("AKPAR_")) or clean(attrs.get("PARCELID")) or pin
        total = positive(attrs.get("TOTALVALUE"))
        features.append(
            base_feature(
                seed,
                county,
                markets,
                spec["source"],
                pin,
                acres,
                geometry,
                center,
                gaps,
                owner=clean(attrs.get("NAME1")),
                owner2=clean(attrs.get("NAME2")),
                situs=situs_text(attrs.get("PHYSICALADDR")),
                zoning=zone,
                zoning_district=district,
                jurisdiction=district,
                sale_price=positive(attrs.get("SALEPRICE")),
                sale_date=arcgis_date(attrs.get("SDATE")),
                sale_qualified=clean(attrs.get("QUALIFIEDCODE")),
                market_value=total,
                assessed=total,
                mail1=clean(attrs.get("ADDRESS1")),
                mail2=clean(attrs.get("ADDRESS2")),
                mail_city=clean(attrs.get("CITY")),
                mail_state=clean(attrs.get("STATE")),
                mail_zip=zip_str(attrs.get("ZIP")),
                appraiser_url=quote_url(
                    "https://arcgisserver.lincolncountync.gov/taxparcelviewer/PropertyReport.aspx?akpar={akpar}&vacinity=false",
                    akpar=account,
                ),
                flu=flu,
            )
        )
    features, extra = dedupe(features)
    zoned = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_n = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    maiden_n = sum(1 for feature in features if (feature["properties"].get("zoningDistrict") or "") == "Maiden" and not feature["properties"].get("zoningCode"))
    gaps = publish_stats(
        features,
        gaps,
        f"Zoning joined on {zoned} of {len(features)} parcels. Future land use joined on {flu_n}. Maiden footprints left unmatched: {maiden_n}.",
    )
    return features, gaps, len(raw), dropped + extra


def pull_anson(seed, county, markets, spec):
    raw = load_parcels(
        seed,
        spec["url"],
        "ASSESSEDACREAGE>=5 AND ASSESSEDACREAGE<=150",
        [
            "PIN",
            "ACCTNUMBER",
            "ASSESSEDACREAGE",
            "NAME1",
            "NAME2",
            "MAILADDRESS",
            "MAILCITY",
            "MAILSTATE",
            "MAILZIP",
            "SITUSADDRESS",
            "PHYSADDRESS",
            "SALEPRICE",
            "DATEFLD",
            "TOTMKT",
            "CURTOTTOT",
            "CountyZoning",
            "LandUsePlan",
        ],
    )
    host = "https://ansoncountygis.com/arcgis/rest/services/ZoningLayers/MapServer"
    towns = [
        ("Wadesboro", index_polygons(load_polygons(seed, f"{host}/4/query", ["ZONECODE"]), ["ZONECODE"])),
        ("Ansonville", index_polygons(load_polygons(seed, f"{host}/0/query", ["ZONE_ID"]), ["ZONE_ID"])),
        ("Lilesville", index_polygons(load_polygons(seed, f"{host}/2/query", ["ZoningDistrict"]), ["ZoningDistrict"])),
        ("Morven", index_polygons(load_polygons(seed, f"{host}/3/query", ["TYPE"]), ["TYPE"])),
    ]
    ansonville_etj = index_polygons(load_polygons(seed, f"{host}/1/query", ["ZONECODE"]), ["ZONECODE"])
    county_zone = index_polygons(load_polygons(seed, f"{host}/5/query", ["ZONECODE2", "ZONECODE"]), ["ZONECODE2", "ZONECODE"])
    places = index_labels(
        load_polygons(seed, "https://ansoncountygis.com/arcgis/rest/services/WebApp2026/MapServer/12/query", ["NAME"]),
        "NAME",
    )
    gap_towns = {"PEACHLAND", "POLKTON", "MCFARLAN"}
    gaps = list(ANSON_GAPS)
    features = []
    dropped = 0
    zoned = 0
    flu_n = 0
    gap_hits = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        acres = num(attrs.get("ASSESSEDACREAGE"))
        geometry, center = geometry_of(seed, item)
        pin = clean(attrs.get("PIN"))
        if not geometry or not center or not pin or not seed.in_band(acres):
            dropped += 1
            continue
        x, y = center
        place = norm_admin(places.hit(x, y))
        district = clean(places.hit(x, y))
        zone = None
        if place in gap_towns:
            gap_hits += 1
        elif place == "ANSONVILLE":
            district, zone = "Ansonville", towns[1][1].hit(x, y) or ansonville_etj.hit(x, y)
        elif place:
            district, zone = hit_smallest(towns, x, y)
        if not zone and place not in gap_towns and place not in {"WADESBORO", "ANSONVILLE", "LILESVILLE", "MORVEN"}:
            zone = usable_zone(attrs.get("CountyZoning"))
            if zone:
                district = "Anson County"
            else:
                zone = county_zone.hit(x, y)
                if zone and usable_zone(zone):
                    district = "Anson County"
                else:
                    zone = None
        flu_code = usable_flu(attrs.get("LandUsePlan"))
        flu = flu_info(flu_code, flu_code, district or "Anson County", "anson-land-use-plan") if flu_code else None
        if zone:
            zoned += 1
        if flu:
            flu_n += 1
        features.append(
            base_feature(
                seed,
                county,
                markets,
                spec["source"],
                pin,
                acres,
                geometry,
                center,
                gaps,
                owner=clean(attrs.get("NAME1")),
                owner2=clean(attrs.get("NAME2")),
                situs=situs_text(attrs.get("SITUSADDRESS")) or situs_text(attrs.get("PHYSADDRESS")),
                zoning=zone,
                zoning_district=district,
                jurisdiction=district,
                sale_price=positive(attrs.get("SALEPRICE")),
                sale_date=arcgis_date(attrs.get("DATEFLD")),
                market_value=positive(attrs.get("TOTMKT")),
                assessed=positive(attrs.get("CURTOTTOT")),
                mail1=clean(attrs.get("MAILADDRESS")),
                mail_city=clean(attrs.get("MAILCITY")),
                mail_state=clean(attrs.get("MAILSTATE")),
                mail_zip=zip_str(attrs.get("MAILZIP")),
                appraiser_url="https://www.bttaxpayerportal.com/ITSPublicAN/",
                flu=flu,
            )
        )
    features, extra = dedupe(features)
    zoned = sum(1 for feature in features if feature["properties"].get("zoningCode"))
    flu_n = sum(1 for feature in features if (feature["properties"].get("flu") or {}).get("code"))
    gap_hits = sum(
        1
        for feature in features
        if norm_admin(feature["properties"].get("zoningDistrict")) in {"PEACHLAND", "POLKTON", "MCFARLAN"}
        and not feature["properties"].get("zoningCode")
    )
    gaps = publish_stats(
        features,
        gaps,
        f"Zoning joined on {zoned} of {len(features)} parcels. Land-use plan joined on {flu_n}. Peachland/Polkton/McFarlan footprints left unmatched: {gap_hits}.",
    )
    return features, gaps, len(raw), dropped + extra
