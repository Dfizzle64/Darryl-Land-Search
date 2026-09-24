#!/usr/bin/env python3
"""North-Central Florida parcel extract.

Wire order: Alachua, Hernando (upgrade off the DOH-only roll), Citrus, Putnam.
Levy, Gilchrist, and Bradford stay on the DOH roll in seed_market_parcels.py.
Marion is not pulled here. Eligible tracts are not designated QOZs.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

FL_BBOX = (-87.65, 24.40, -79.95, 31.05)
COUNTY_BBOX = {
    "12001": (-82.70, 29.40, -82.00, 29.98),
    "12053": (-82.70, 28.25, -82.00, 28.72),
    "12017": (-82.85, 28.60, -82.20, 29.10),
    "12107": (-82.10, 29.25, -81.35, 29.90),
}

ALACHUA_JURIS = {
    0: "Unincorporated Alachua County",
    100: "Alachua",
    200: "Archer",
    300: "Gainesville",
    400: "Hawthorne",
    500: "High Springs",
    600: "LaCrosse",
    700: "Micanopy",
    800: "Newberry",
    900: "Waldo",
}

PLACEHOLDER_ZONING = {"CITY", "MUNICIPAL", "MUNI", "CITY LIMITS", "CITY LIMITS OF INV. OR C.R."}

APPRAISER = {
    "12001": "https://www.acpafl.org/",
    "12053": "https://hernandocountypa-florida.us/",
    "12017": "https://www.citruspa.org/",
    "12107": "https://pa.putnam-fl.com/",
}

ALACHUA_PARCELS = "https://services1.arcgis.com/MiBZ4u97DWldovjI/ArcGIS/rest/services/Parcels35/FeatureServer/0/query"
ALACHUA_ADDRESSES = "https://services1.arcgis.com/MiBZ4u97DWldovjI/ArcGIS/rest/services/AddressPoints/FeatureServer/0/query"
HERNANDO_PARCELS = "https://services2.arcgis.com/x5zvhhxfUuRDntRe/ArcGIS/rest/services/Parcels/FeatureServer/0/query"
HERNANDO_ZONING = "https://services2.arcgis.com/x5zvhhxfUuRDntRe/ArcGIS/rest/services/Zoning_Flu/FeatureServer/75/query"
HERNANDO_FLU = "https://services2.arcgis.com/x5zvhhxfUuRDntRe/ArcGIS/rest/services/Zoning_Flu/FeatureServer/0/query"
CITRUS_ZONING = "https://maps.citrusbocc.com/server/rest/services/PublicData/LandDevelopment/MapServer/9/query"
CITRUS_FLU = "https://maps.citrusbocc.com/server/rest/services/PublicData/LandDevelopment/MapServer/8/query"
CITRUS_CORPORATE = "https://maps.citrusbocc.com/server/rest/services/PublicData/LandDevelopment/MapServer/12/query"
CITRUS_INVERNESS_FLU = "https://maps.citrusbocc.com/server/rest/services/PublicData/Inverness_Zoning_Future_Land_Use_and_Address/MapServer/2/query"
PUTNAM_ZONING_ROOT = "https://gis.putnam-fl.com/arcserver/rest/services/ReferenceMap/Zoning_R/MapServer"
PUTNAM_PALATKA_ZONING = "https://gis.putnam-fl.com/arcserver/rest/services/Hosted/Municipal_Zoning__City_of_Palatka/FeatureServer/6/query"
PUTNAM_PALATKA_FLU = "https://gis.putnam-fl.com/arcserver/rest/services/Hosted/Municipal_Future_Land_Use__City_of_Palatka/FeatureServer/0/query"


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
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return parsed


def money(value: Any, minimum: float = 1) -> float | None:
    parsed = num(value)
    if parsed is None or parsed < minimum:
        return None
    return parsed


def title_place(value: str) -> str:
    text = " ".join(value.replace("_", " ").split())
    small = {"of", "the"}
    parts = []
    for index, word in enumerate(text.split(" ")):
        lower = word.lower()
        if index and lower in small:
            parts.append(lower)
        elif lower == "lacrosse":
            parts.append("LaCrosse")
        else:
            parts.append(lower.capitalize())
    return " ".join(parts)


def alachua_municipality(juris_no: Any) -> str | None:
    parsed = num(juris_no)
    if parsed is None:
        return None
    return ALACHUA_JURIS.get(int(parsed))


def alachua_prefix(juris_no: Any) -> str | None:
    parsed = num(juris_no)
    if parsed is None:
        return None
    juris = int(parsed)
    if juris == 0:
        return "0100"
    if juris not in ALACHUA_JURIS or juris % 100 != 0:
        return None
    return f"01{juris // 100:02d}"


def matching_code(code: Any, prefix: str | None) -> str | None:
    text = clean(code)
    if not text or not prefix:
        return None
    if not text.upper().startswith(prefix.upper()):
        return None
    return text


def hernando_municipality(juris: Any) -> str:
    text = clean(juris)
    if text and text.upper() == "B":
        return "Brooksville"
    return "Unincorporated Hernando County"


def usable_zoning(code: Any) -> str | None:
    text = clean(code)
    if not text:
        return None
    if text.upper() in PLACEHOLDER_ZONING:
        return None
    return text


def citrus_municipality(name: Any) -> str:
    text = clean(name)
    if not text:
        return "Unincorporated Citrus County"
    label = title_place(text)
    if label in {"Crystal River", "Inverness"}:
        return label
    return "Unincorporated Citrus County"


def putnam_city_from_layer(name: str) -> str | None:
    text = name.lower()
    for label in ("Palatka", "Crescent City", "Interlachen", "Pomona Park", "Welaka"):
        if label.lower() in text:
            return label
    return None


def flu_record(code: Any, label: Any, jurisdiction: str, source: str) -> dict | None:
    code_text = clean(code)
    label_text = clean(label)
    if code_text and code_text.upper() in PLACEHOLDER_ZONING | {"CITY"}:
        return None
    if not code_text and not label_text:
        return None
    if code_text and code_text.lower() == "city":
        return None
    return {
        "code": code_text or label_text,
        "label": label_text or code_text,
        "jurisdiction": jurisdiction,
        "source": source,
    }


def in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float]) -> bool:
    west, south, east, north = bbox
    return west <= lon <= east and south <= lat <= north


def in_county(fips: str, lon: float, lat: float) -> bool:
    bbox = COUNTY_BBOX.get(fips)
    return bool(bbox) and in_bbox(lon, lat, bbox) and in_bbox(lon, lat, FL_BBOX)


def iso_from_any(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                parsed = datetime.strptime(text[:10] if fmt == "%Y-%m-%d" and len(text) >= 10 else text, fmt).date()
            except ValueError:
                continue
            if 1950 <= parsed.year <= 2026:
                return parsed.isoformat()
        if not re.fullmatch(r"-?\d+(\.\d+)?", text):
            return None
    parsed_num = num(value)
    if parsed_num is None:
        return None
    if 19_500_101 <= parsed_num <= 20_261_231:
        text = f"{int(parsed_num):08d}"
        try:
            parsed = datetime.strptime(text, "%Y%m%d").date()
            if 1950 <= parsed.year <= 2026:
                return parsed.isoformat()
        except ValueError:
            pass
    try:
        if parsed_num > 10_000_000_000_000:
            seconds = parsed_num / 1_000_000
        elif parsed_num > 10_000_000_000:
            seconds = parsed_num / 1000
        elif parsed_num > 10_000_000:
            seconds = parsed_num
        else:
            parsed = (datetime(1899, 12, 30) + timedelta(days=float(parsed_num))).date()
            if 1950 <= parsed.year <= 2026:
                return parsed.isoformat()
            return None
        if not 0 <= seconds <= 4_102_444_800:
            return None
        parsed = datetime.utcfromtimestamp(seconds).date()
    except (OverflowError, OSError, ValueError):
        return None
    if 1950 <= parsed.year <= 2026:
        return parsed.isoformat()
    return None


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        yi = ring[i][1]
        yj = ring[j][1]
        if (yi > lat) != (yj > lat):
            xi = ring[i][0]
            xj = ring[j][0]
            denom = yj - yi
            if denom == 0:
                j = i
                continue
            cross = (xj - xi) * (lat - yi) / denom + xi
            if lon < cross:
                inside = not inside
        j = i
    return inside


class SpatialIndex:
    def __init__(self, cell: float = 0.03) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list] = defaultdict(list)
        self.kept = 0

    def add_geometry(self, geometry: dict | None, payload: dict) -> None:
        if not geometry:
            return
        if geometry.get("type") == "Polygon":
            self._add_rings(geometry.get("coordinates") or [], payload)
        elif geometry.get("type") == "MultiPolygon":
            for rings in geometry.get("coordinates") or []:
                self._add_rings(rings, payload)

    def _add_rings(self, rings: list, payload: dict) -> None:
        if not rings or len(rings[0]) < 4:
            return
        exterior = rings[0]
        west = min(point[0] for point in exterior)
        east = max(point[0] for point in exterior)
        south = min(point[1] for point in exterior)
        north = max(point[1] for point in exterior)
        if not in_bbox((west + east) / 2, (south + north) / 2, FL_BBOX):
            return
        record = (exterior, rings[1:], payload, west, south, east, north)
        for ix in range(int(west // self.cell), int(east // self.cell) + 1):
            for iy in range(int(south // self.cell), int(north // self.cell) + 1):
                self.buckets[(ix, iy)].append(record)
        self.kept += 1

    def hit(self, lon: float, lat: float) -> dict | None:
        for record in self.buckets.get((int(lon // self.cell), int(lat // self.cell)), []):
            exterior, holes, payload, west, south, east, north = record
            if not (west <= lon <= east and south <= lat <= north):
                continue
            if not point_in_ring(lon, lat, exterior):
                continue
            if any(point_in_ring(lon, lat, hole) for hole in holes):
                continue
            return payload
        return None


def fetch_paged(seed: Any, url: str, where: str, fields: list[str], geometry: bool) -> list[dict]:
    features: list[dict] = []
    offset = 0
    page = 2000
    order = True
    while True:
        params: dict[str, Any] = {
            "where": where,
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "f": "json",
            "resultOffset": str(offset),
            "resultRecordCount": str(page),
        }
        if order:
            params["orderByFields"] = "OBJECTID"
        if geometry:
            params["outSR"] = "4326"
        data = seed.fetch_json(url, params, timeout=180)
        if data.get("error") and order:
            order = False
            continue
        if data.get("error"):
            raise RuntimeError(json_error(data))
        batch = data.get("features") or []
        features.extend(batch)
        print(f"    {url.rsplit('/', 2)[-2]} {len(features)}", flush=True)
        if not data.get("exceededTransferLimit") and len(batch) < page:
            break
        if not batch:
            break
        offset += len(batch)
    return features


def json_error(data: dict) -> str:
    import json

    return json.dumps(data.get("error"))[:240]


def join_key(value: Any) -> str | None:
    parsed = num(value)
    if parsed is not None and abs(parsed - round(parsed)) < 1e-6:
        return str(int(round(parsed)))
    text = clean(value)
    if not text:
        return None
    return "".join(text.upper().split())


def fetch_where_ids(seed: Any, url: str, field: str, ids: list[Any], fields: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    step = 60
    unique_ids = []
    seen = set()
    for value in ids:
        key = join_key(value) if not isinstance(value, int) else str(value)
        if key and key not in seen:
            seen.add(key)
            unique_ids.append(value if isinstance(value, int) else key)
    for start in range(0, len(unique_ids), step):
        chunk = unique_ids[start : start + step]
        parts = []
        for value in chunk:
            if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
                parts.append(str(int(value)) if not isinstance(value, int) else str(value))
            else:
                escaped = str(value).replace("'", "''")
                parts.append(f"'{escaped}'")
        where = f"{field} IN ({','.join(parts)})"
        try:
            data = seed.fetch_json(
                url,
                {
                    "where": where,
                    "outFields": ",".join(fields),
                    "returnGeometry": "false",
                    "f": "json",
                },
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"    join batch failed {exc}", flush=True)
            continue
        if data.get("error"):
            print(f"    join batch error {json_error(data)}", flush=True)
            continue
        for feature in data.get("features") or []:
            attrs = feature.get("attributes") or {}
            key = join_key(attrs.get(field))
            if key:
                found[key] = attrs
        if start and start % 600 == 0:
            print(f"    joined {start}/{len(unique_ids)}", flush=True)
    return found


def load_index(seed: Any, url: str, fields: list[str], label: str, payload_of) -> SpatialIndex:
    index = SpatialIndex()
    try:
        rows = fetch_paged(seed, url, "1=1", fields, geometry=True)
    except Exception as exc:  # noqa: BLE001
        print(f"    {label} failed: {exc}", flush=True)
        return index
    for item in rows:
        geometry, _acres = seed.rings_to_feature_geometry(item.get("geometry"))
        payload = payload_of(item.get("attributes") or {})
        if payload:
            index.add_geometry(geometry, payload)
    print(f"    {label} indexed {index.kept}", flush=True)
    return index


def geometry_of(seed: Any, item: dict, fips: str) -> tuple[dict | None, tuple[float, float] | None, float | None]:
    geometry, computed = seed.rings_to_feature_geometry(item.get("geometry"))
    if not geometry:
        return None, None, computed
    center = seed.centroid_of(geometry)
    if not seed.plausible_centroid(center) or not in_county(fips, center[0], center[1]):
        return None, None, computed
    return geometry, center, computed


def remember(by_id: dict[str, dict], feature: dict) -> None:
    parcel_id = feature["properties"]["parcelId"]
    previous = by_id.get(parcel_id)
    if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
        by_id[parcel_id] = feature


def finish(seed: Any, county: dict, markets: list[str], spec: dict, features: list[dict], gaps: list[str], source_count: int, dropped: int) -> dict:
    if features and not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{county['fips']} emitted a parcel outside 5–150 acres")
    coverage = spec.get("coverage") or "complete-gte-5ac"
    path, lookup, tiles = (None, None, 0)
    if features:
        path, lookup, tiles = seed.write_tiles(county, features)
    else:
        coverage = "gap"
        gaps = ["No parcels survived the 5–150 acre and county extent checks.", *gaps]
    print(f"  kept {len(features)} {county['name']} ({coverage})", flush=True)
    return seed.county_row(
        county,
        markets,
        feature_count=len(features),
        coverage=coverage if features else "gap",
        partition="tiles" if features else "none",
        path=path,
        lookup=lookup,
        source=spec["source"],
        query_url=spec.get("url"),
        gaps=gaps,
        source_count=source_count,
        dropped=dropped,
        tile_count=tiles,
    )


def pull_alachua(seed: Any, county: dict, markets: list[str]) -> tuple[list[dict], list[str], int, int]:
    fields = [
        "parcel",
        "firstName1",
        "Address1",
        "Address2",
        "city",
        "state",
        "zip",
        "acres",
        "JurisNo",
        "CityDescription",
        "puse",
        "JustValue",
        "TaxAmount",
        "ZONECODE",
        "ZONEDISTRICT",
        "ZoneDefin",
        "FluCode",
        "FluPolicy",
        "FluDefin",
        "SaleDate",
        "SaleAmount",
        "Link_ACPA",
    ]
    where = "acres>=5 AND acres<=150"
    ids = seed.fetch_object_ids(ALACHUA_PARCELS, where)
    raw = seed.fetch_by_ids(ALACHUA_PARCELS, ids, fields)
    parcel_ids = [clean((item.get("attributes") or {}).get("parcel")) for item in raw]
    parcel_ids = [parcel_id for parcel_id in parcel_ids if parcel_id]
    addresses = fetch_where_ids(seed, ALACHUA_ADDRESSES, "PARCEL", parcel_ids, ["PARCEL", "FULLADDR", "ZIP5", "MUNICIPALITY"])
    by_id: dict[str, dict] = {}
    dropped = 0
    prefix_miss = 0
    unknown_juris = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, center, computed = geometry_of(seed, item, "12001")
        acres = num(attrs.get("acres"))
        if acres is None:
            acres = computed
        parcel_id = clean(attrs.get("parcel"))
        municipality = alachua_municipality(attrs.get("JurisNo"))
        if not geometry or not center or not parcel_id or not seed.in_band(acres):
            dropped += 1
            continue
        if municipality is None:
            unknown_juris += 1
            municipality = "Unincorporated Alachua County"
        prefix = alachua_prefix(attrs.get("JurisNo"))
        zoning = clean(attrs.get("ZONEDISTRICT")) if matching_code(attrs.get("ZONECODE"), prefix) else None
        flu_code = matching_code(attrs.get("FluCode"), prefix)
        if clean(attrs.get("ZONECODE")) and zoning is None:
            prefix_miss += 1
        address = addresses.get(join_key(parcel_id) or "") or {}
        feature = seed.empty_feature(
            fips="12001",
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source="fl-alachua-parcels35-12001",
            owner=clean(attrs.get("firstName1")),
            situs=clean(address.get("FULLADDR")),
            city=clean(address.get("MUNICIPALITY")),
            zip_code=seed.zip_str(address.get("ZIP5")),
            zoning=zoning,
            zoning_district=clean(attrs.get("ZoneDefin")) if zoning else None,
            jurisdiction=municipality,
            dor=clean(attrs.get("puse")),
            sale_price=money(attrs.get("SaleAmount")),
            sale_date=iso_from_any(attrs.get("SaleDate")),
            market_value=money(attrs.get("JustValue"), 100),
            taxes=money(attrs.get("TaxAmount"), 0.01),
            mail1=clean(attrs.get("Address1")),
            mail2=clean(attrs.get("Address2")),
            mail_city=clean(attrs.get("city")),
            mail_state=clean(attrs.get("state")),
            mail_zip=seed.zip_str(attrs.get("zip")),
            flu=flu_record(flu_code, attrs.get("FluDefin") or attrs.get("FluPolicy"), municipality, "alachua-parcels35-flu"),
            appraiser_url=clean(attrs.get("Link_ACPA")) or APPRAISER["12001"],
        )
        if not feature["properties"]["situsAddress"]:
            feature["properties"]["dataGaps"] = ["No situs on the address-point join. Parcel city is the mailing city and was not used as the site address."]
        remember(by_id, feature)
    gaps = [
        "Jurisdiction is JurisNo on Parcels35, not the situs or mailing city. Gainesville postal addresses outside the city stay Unincorporated Alachua County.",
        "Zoning and FLU are stored only when ZONECODE/FluCode starts with the jurisdiction prefix (0100 county, 0103 Gainesville, and the same pattern for the other cities). A mismatched county code on a city parcel is left blank.",
        f"Zoning prefix mismatches left blank: {prefix_miss}.",
        "Address1/city/zip on Parcels35 are the owner mailing address. Situs comes from AddressPoints.",
        "Assessed value is not on Parcels35. JustValue is stored as market value. TaxAmount is the tax bill when present.",
        "Gainesville's separate FLU service requires a token and was not used. City FLU is the parcel FluCode when the prefix matches.",
        "City zoning codes are labels, not Orange County multifamily districts.",
        f"Parcels with an unrecognized JurisNo: {unknown_juris}.",
    ]
    return list(by_id.values()), gaps, len(raw), dropped


def pull_hernando(seed: Any, county: dict, markets: list[str]) -> tuple[list[dict], list[str], int, int]:
    fields = [
        "PARCEL_KEY",
        "ACRES",
        "SITUS_ADDRESS",
        "SITUS_CITY",
        "SITUS_ZIP5",
        "OWNER_NAME",
        "OWNER_NAME2",
        "MAIL_ADDR1",
        "MAIL_CITY",
        "MAIL_STATE",
        "MAIL_POSTALCODE",
        "CER_JURISDICTION",
        "CER_LEVY_CODE",
        "CER_JUST_VALUE",
        "CER_ASSESSED_CNTY",
        "CER_TAXABLE_CNTY",
        "CER_DOR_CODE",
        "LSALE_DATE",
        "LSALE_PRICE",
        "LSALE_QUALCD",
        "TAXES_YEAR1",
    ]
    where = "ACRES>=5 AND ACRES<=150"
    ids = seed.fetch_object_ids(HERNANDO_PARCELS, where)
    raw = seed.fetch_by_ids(HERNANDO_PARCELS, ids, fields)
    keys = []
    for item in raw:
        key = num((item.get("attributes") or {}).get("PARCEL_KEY"))
        if key is not None:
            keys.append(int(key))
    zoning_by_key = fetch_where_ids(
        seed,
        HERNANDO_ZONING,
        "KEY_NUMBER",
        keys,
        ["KEY_NUMBER", "ZONING", "ZONEDESC", "SPLIT_ZONE1"],
    )
    flu_index = load_index(
        seed,
        HERNANDO_FLU,
        ["FLU", "LABEL"],
        "Hernando FLU",
        lambda attrs: None
        if not usable_zoning(attrs.get("FLU")) or str(attrs.get("FLU") or "").lower() == "city"
        else {"code": clean(attrs.get("FLU")), "label": clean(attrs.get("LABEL")) or clean(attrs.get("FLU"))},
    )
    by_id: dict[str, dict] = {}
    dropped = 0
    brooksville = 0
    city_placeholder = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        geometry, center, computed = geometry_of(seed, item, "12053")
        acres = num(attrs.get("ACRES"))
        if acres is None:
            acres = computed
        key = num(attrs.get("PARCEL_KEY"))
        parcel_id = str(int(key)) if key is not None else None
        if not geometry or not center or not parcel_id or not seed.in_band(acres):
            dropped += 1
            continue
        municipality = hernando_municipality(attrs.get("CER_JURISDICTION"))
        zone_attrs = zoning_by_key.get(parcel_id) or {}
        zoning = usable_zoning(zone_attrs.get("ZONING"))
        if municipality == "Brooksville":
            brooksville += 1
            if clean(zone_attrs.get("ZONING")) and zoning is None:
                city_placeholder += 1
            zoning = None
        flu_hit = None if municipality == "Brooksville" else flu_index.hit(center[0], center[1])
        feature = seed.empty_feature(
            fips="12053",
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=parcel_id,
            acreage=acres,
            geometry=geometry,
            center=center,
            source="fl-hernando-parcels-12053",
            owner=clean(attrs.get("OWNER_NAME")),
            owner2=clean(attrs.get("OWNER_NAME2")),
            situs=clean(attrs.get("SITUS_ADDRESS")),
            city=clean(attrs.get("SITUS_CITY")),
            zip_code=seed.zip_str(attrs.get("SITUS_ZIP5")),
            zoning=zoning,
            zoning_district=clean(zone_attrs.get("ZONEDESC")) if zoning else None,
            jurisdiction=municipality,
            dor=clean(attrs.get("CER_DOR_CODE")),
            sale_price=money(attrs.get("LSALE_PRICE")),
            sale_date=iso_from_any(attrs.get("LSALE_DATE")),
            sale_qualified=clean(attrs.get("LSALE_QUALCD")),
            market_value=money(attrs.get("CER_JUST_VALUE"), 100),
            assessed=money(attrs.get("CER_ASSESSED_CNTY"), 1),
            taxable=money(attrs.get("CER_TAXABLE_CNTY"), 1),
            taxes=money(attrs.get("TAXES_YEAR1"), 0.01),
            mail1=clean(attrs.get("MAIL_ADDR1")),
            mail_city=clean(attrs.get("MAIL_CITY")),
            mail_state=clean(attrs.get("MAIL_STATE")),
            mail_zip=seed.zip_str(attrs.get("MAIL_POSTALCODE")),
            flu=flu_record(flu_hit.get("code") if flu_hit else None, flu_hit.get("label") if flu_hit else None, municipality, "hernando-zoning-flu-layer0")
            if flu_hit
            else None,
            appraiser_url=APPRAISER["12053"],
        )
        if municipality == "Brooksville":
            feature["properties"]["dataGaps"] = [
                "Brooksville zoning on the county layer is the placeholder CITY and was not stored. No public Brooksville zoning or FLU service was verified.",
            ]
        remember(by_id, feature)
    gaps = [
        "Upgrade off Florida DOH. Parcels, owner, situs, and values are Hernando County Parcels (gis.V_PARCELS).",
        "Municipality is CER_JURISDICTION: B is Brooksville and C is unincorporated. Situs city Brooksville, Spring Hill, or Weeki Wachee is not the city limit.",
        "Spring Hill is an unincorporated place. Weeki Wachee levy code CWWE is not stored as a municipality.",
        "County zoning joins on KEY_NUMBER. The value CITY is a placeholder and is not a zoning district.",
        f"Brooksville parcels left without city zoning: {brooksville} (placeholder rows {city_placeholder}).",
        "County future land use skips polygons whose FLU code is city. Those are the Brooksville hole, not a city FLU map.",
        "No public Brooksville or Weeki Wachee zoning/FLU FeatureServer was verified.",
    ]
    if flu_index.kept == 0:
        gaps.insert(0, "Hernando future-land-use overlay did not load. FLU was left blank.")
    return list(by_id.values()), gaps, len(raw), dropped


def doh_rows(seed: Any, layer: int) -> list[dict]:
    url = f"{seed.DOH_BASE}/{layer}/query"
    where = f"LND_SQFOOT >= {seed.MIN_SQFT} AND LND_SQFOOT <= {seed.MAX_SQFT}"
    ids = seed.fetch_object_ids(url, where)
    return seed.fetch_by_ids(url, ids, seed.DOH_FIELDS)


def doh_feature(seed: Any, county: dict, markets: list[str], item: dict, source: str, fips: str) -> dict | None:
    attrs = item.get("attributes") or {}
    geometry, center, computed = geometry_of(seed, item, fips)
    acres = num(attrs.get("LND_SQFOOT"))
    if acres is not None:
        acres = acres / 43560
    if acres is None:
        acres = computed
    parcel_id = clean(attrs.get("PARCEL_ID"))
    if not geometry or not center or not parcel_id or not seed.in_band(acres):
        return None
    return seed.empty_feature(
        fips=fips,
        county=county["name"],
        state=county["state"],
        markets=markets,
        parcel_id=parcel_id,
        acreage=acres,
        geometry=geometry,
        center=center,
        source=source,
        owner=clean(attrs.get("OWN_NAME")),
        situs=clean(attrs.get("PHY_ADDR1")),
        city=clean(attrs.get("PHY_CITY")),
        zip_code=seed.zip_str(attrs.get("PHY_ZIPCD")),
        dor=clean(attrs.get("DOR_UC")),
        sale_price=money(attrs.get("SALE_PRC1")),
        sale_date=seed.sale_date(attrs.get("SALE_YR1"), attrs.get("SALE_MO1")),
        sale_qualified=clean(attrs.get("QUAL_CD1")),
        market_value=money(attrs.get("JV"), 100),
        assessed=money(attrs.get("AV_SD"), 1),
        taxable=money(attrs.get("TV_SD"), 1),
        mail1=clean(attrs.get("OWN_ADDR1")),
        mail2=clean(attrs.get("OWN_ADDR2")),
        mail_city=clean(attrs.get("OWN_CITY")),
        mail_state=clean(attrs.get("OWN_STATE")),
        mail_zip=seed.zip_str(attrs.get("OWN_ZIPCD")),
        appraiser_url=APPRAISER[fips],
    )


def pull_citrus(seed: Any, county: dict, markets: list[str]) -> tuple[list[dict], list[str], int, int]:
    raw = doh_rows(seed, 8)
    corporate = load_index(
        seed,
        CITRUS_CORPORATE,
        ["CORPNAME"],
        "Citrus cities",
        lambda attrs: {"name": citrus_municipality(attrs.get("CORPNAME"))} if clean(attrs.get("CORPNAME")) else None,
    )
    zoning_index = load_index(
        seed,
        CITRUS_ZONING,
        ["HANSEN__PRCLZON_ZONING", "HANSEN_TBL302_DESCRIPT"],
        "Citrus zoning",
        lambda attrs: {"code": usable_zoning(attrs.get("HANSEN__PRCLZON_ZONING")), "label": clean(attrs.get("HANSEN_TBL302_DESCRIPT"))}
        if usable_zoning(attrs.get("HANSEN__PRCLZON_ZONING"))
        else None,
    )
    flu_index = load_index(
        seed,
        CITRUS_FLU,
        ["HANSEN__PRCLUSE_LANDUSE", "HANSEN_TABL146_DESCRIPT"],
        "Citrus FLU",
        lambda attrs: {"code": usable_zoning(attrs.get("HANSEN__PRCLUSE_LANDUSE")), "label": clean(attrs.get("HANSEN_TABL146_DESCRIPT"))}
        if usable_zoning(attrs.get("HANSEN__PRCLUSE_LANDUSE"))
        else None,
    )
    inverness = load_index(
        seed,
        CITRUS_INVERNESS_FLU,
        ["FLU", "INV_FLU"],
        "Inverness FLU",
        lambda attrs: {"zoning": clean(attrs.get("INV_FLU")), "flu": clean(attrs.get("FLU"))}
        if clean(attrs.get("INV_FLU")) or clean(attrs.get("FLU"))
        else None,
    )
    by_id: dict[str, dict] = {}
    dropped = 0
    crystal = 0
    inverness_n = 0
    for item in raw:
        feature = doh_feature(seed, county, markets, item, "fl-citrus-doh-municipal-12017", "12017")
        if feature is None:
            dropped += 1
            continue
        lon, lat = feature["properties"]["centroid"]
        city_hit = corporate.hit(lon, lat)
        municipality = city_hit["name"] if city_hit else "Unincorporated Citrus County"
        feature["properties"]["jurisdictionCode"] = municipality
        if municipality == "Crystal River":
            crystal += 1
            feature["properties"]["zoningCode"] = None
            feature["properties"]["flu"] = None
            feature["properties"]["dataGaps"] = ["Crystal River has no verified public zoning or FLU service. County CITY placeholders were not used."]
        elif municipality == "Inverness":
            inverness_n += 1
            hit = inverness.hit(lon, lat)
            feature["properties"]["zoningCode"] = usable_zoning(hit.get("zoning")) if hit else None
            feature["properties"]["flu"] = flu_record(hit.get("flu") if hit else None, hit.get("flu") if hit else None, "Inverness", "citrus-inverness-flu") if hit else None
            if not feature["properties"]["zoningCode"]:
                feature["properties"]["dataGaps"] = ["Inverness zoning polygon missed this centroid."]
        else:
            zone = zoning_index.hit(lon, lat)
            land = flu_index.hit(lon, lat)
            feature["properties"]["zoningCode"] = zone.get("code") if zone else None
            feature["properties"]["zoningDistrict"] = zone.get("label") if zone else None
            feature["properties"]["flu"] = flu_record(land.get("code") if land else None, land.get("label") if land else None, municipality, "citrus-land-development-landuse") if land else None
        remember(by_id, feature)
    gaps = [
        "Parcel polygons, owner, situs, and tax values are Florida DOH EHWATER layer 8. Citrus County lots have no acre or owner field, and lot PRCLKEY is empty, so zoning is a centroid join.",
        "Municipality is the corporate-limit layer (Inverness or Crystal River). PHY_CITY is the postal city and is not the city limit.",
        "County zoning and land use values CITY are placeholders and are not stored.",
        f"Inverness parcels: {inverness_n}. Zoning is INV_FLU and future land use is FLU on the city layer.",
        f"Crystal River parcels left without city zoning: {crystal}.",
        "No public Crystal River zoning or FLU FeatureServer was verified.",
        "County zoning codes are not Orange County multifamily districts.",
    ]
    if zoning_index.kept == 0:
        gaps.insert(0, "Citrus county zoning overlay failed to load. Unincorporated zoning was left blank.")
    return list(by_id.values()), gaps, len(raw), dropped


def putnam_layers(seed: Any) -> list[tuple[str, str, str]]:
    """Return (query url, city, code field) for municipal zoning district layers."""
    found: list[tuple[str, str, str]] = []
    try:
        meta = seed.fetch_json(PUTNAM_ZONING_ROOT, {"f": "json"}, timeout=60)
    except Exception as exc:  # noqa: BLE001
        print(f"    Putnam Zoning_R failed: {exc}", flush=True)
        meta = {}
    for layer in meta.get("layers") or []:
        name = str(layer.get("name") or "")
        city = putnam_city_from_layer(name)
        layer_id = layer.get("id")
        if not city or layer_id is None:
            continue
        url = f"{PUTNAM_ZONING_ROOT}/{layer_id}"
        try:
            info = seed.fetch_json(url, {"f": "json"}, timeout=60)
        except Exception as exc:  # noqa: BLE001
            print(f"    Putnam {name} failed: {exc}", flush=True)
            continue
        names = [field.get("name") for field in info.get("fields") or []]
        code_field = next((item for item in ("zoneclass", "ZONECLASS", "ZONING", "ZONE", "ZONECODE") if item in names), None)
        if code_field:
            found.append((f"{url}/query", city, code_field))
    return found


def pull_putnam(seed: Any, county: dict, markets: list[str]) -> tuple[list[dict], list[str], int, int]:
    raw = doh_rows(seed, 53)
    indexes: list[tuple[str, SpatialIndex]] = []
    for url, city, code_field in putnam_layers(seed):
        index = load_index(
            seed,
            url,
            [code_field, "zonedesc", "ZONEDESC"],
            f"Putnam {city}",
            lambda attrs, field=code_field, city_name=city: {"city": city_name, "code": usable_zoning(attrs.get(field)), "label": clean(attrs.get("zonedesc") or attrs.get("ZONEDESC"))}
            if usable_zoning(attrs.get(field))
            else {"city": city_name, "code": None, "label": None},
        )
        if index.kept:
            indexes.append((city, index))
    palatka_flu = load_index(
        seed,
        PUTNAM_PALATKA_FLU,
        ["LANDUSECOD", "LANDUSEDES", "zoneclass"],
        "Palatka FLU",
        lambda attrs: {"code": clean(attrs.get("LANDUSECOD") or attrs.get("zoneclass")), "label": clean(attrs.get("LANDUSEDES"))}
        if clean(attrs.get("LANDUSECOD") or attrs.get("zoneclass") or attrs.get("LANDUSEDES"))
        else None,
    )
    by_id: dict[str, dict] = {}
    dropped = 0
    for item in raw:
        feature = doh_feature(seed, county, markets, item, "fl-putnam-doh-municipal-12107", "12107")
        if feature is None:
            dropped += 1
            continue
        lon, lat = feature["properties"]["centroid"]
        hit = None
        for _city, index in indexes:
            hit = index.hit(lon, lat)
            if hit:
                break
        if hit and hit.get("city"):
            municipality = hit["city"]
            feature["properties"]["jurisdictionCode"] = municipality
            feature["properties"]["zoningCode"] = hit.get("code")
            feature["properties"]["zoningDistrict"] = hit.get("label")
            city_counts[municipality] += 1
            if municipality == "Palatka":
                flu_hit = palatka_flu.hit(lon, lat)
                feature["properties"]["flu"] = flu_record(
                    flu_hit.get("code") if flu_hit else None,
                    flu_hit.get("label") if flu_hit else None,
                    "Palatka",
                    "putnam-palatka-flu",
                ) if flu_hit else None
        else:
            feature["properties"]["jurisdictionCode"] = "Unincorporated Putnam County"
        remember(by_id, feature)
    features = list(by_id.values())
    stored_counts: dict[str, int] = defaultdict(int)
    for feature in features:
        label = feature["properties"].get("jurisdictionCode") or "Unincorporated Putnam County"
        stored_counts[label] += 1
    gaps = [
        "Optional Putnam pull. Parcel polygons and tax attributes are Florida DOH EHWATER layer 53.",
        "The property-appraiser COMMUNITY field is Unincorporated on essentially every row, so it is not used as a municipality.",
        "Municipal zoning is a centroid join to ReferenceMap/Zoning_R city layers when those layers published a zone field.",
        "Unincorporated zoning and future land use services returned an error and were not joined.",
        "Crescent City, Interlachen, Pomona Park, and Welaka future land use was not on a verified public layer separate from zoning.",
        f"Stored jurisdiction counts: {dict(stored_counts)}.",
        "PHY_CITY remains the postal city. It is not the municipality.",
    ]
    if not indexes:
        gaps.insert(0, "Putnam municipal zoning layers did not load. Jurisdiction falls back to unincorporated and zoning stays blank.")
    if palatka_flu.kept == 0:
        gaps.append("Palatka future-land-use service did not load. Palatka FLU was left blank.")
    if len(raw) != len(features):
        gaps.append(
            f"{len(raw)} source rows stored as {len(features)} parcels "
            f"({dropped} failed the acreage or county-extent check; the rest were duplicate parcel ids)."
        )
    return features, gaps, len(raw), dropped


def pull(seed: Any, county: dict, markets: list[str], spec: dict) -> dict:
    print(f"Pulling {county['name']} via north-central {spec['source']}", flush=True)
    dispatch = {
        "12001": pull_alachua,
        "12053": pull_hernando,
        "12017": pull_citrus,
        "12107": pull_putnam,
    }
    handler = dispatch.get(county["fips"])
    if handler is None:
        raise RuntimeError(f"No north-central puller for {county['fips']}")
    features, gaps, source_count, dropped = handler(seed, county, markets)
    return finish(seed, county, markets, spec, features, gaps, source_count, dropped)
