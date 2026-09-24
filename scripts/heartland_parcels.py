"""Florida Heartland inland shelf (5.0–150.0 acres).

Public GIS only. Counties, in wire order: Highlands, Hardee, Glades, Hendry, DeSoto.
Attribute-join on a parcel id when the overlay has one. Otherwise intersect the
representative point. City zoning and future land use stay inside the city.

Namesakes are rejected before a join: Highlands TX, Hardee OK, DeSoto KS,
Glades OH, and Memphis's DeSoto County, Mississippi (28033).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from parcel_geometry import esri_rings_to_geojson, polygon_parts, representative_point
from parcel_geometry import _inside_polygon

FIPS = ("12055", "12049", "12043", "12051", "12027")

# Peninsular Florida Heartland. North of ~31 is Ohio/Kansas; west of ~88 is Texas/Oklahoma.
HEARTLAND_BBOX = (-82.25, 26.05, -80.65, 27.85)

SENTINELS = {
    "LABELLE",
    "LA BELLE",
    "CLEWISTON",
    "CITY OF LABELLE",
    "CITY OF CLEWISTON",
    "DID NOT CHANGE",
    "N/A",
    "NA",
    "NONE",
    "NULL",
    "UNKNOWN",
    "TBD",
}

HIGHLANDS_CITY_GAP = ("SEBRING", "AVON PARK", "LAKE PLACID")

# Root Parcels FeatureServer is not the public PAO layer (token-gated). Do not query it.
REJECTED_HIGHLANDS_ROOT = "https://gis.highlandsfl.gov/server/rest/services/Parcels/FeatureServer"
# Glades MapServers on gis1.hcpao.org have query disabled. Do not call them.
REJECTED_GLADES_HCPAO = "https://gis1.hcpao.org"

PAO = "https://gis.highlandsfl.gov/server/rest/services/Layers/PAO_Parcels/FeatureServer/0/query"
HIGHLANDS_ZONING = "https://gis.highlandsfl.gov/server/rest/services/Layers/Zoning/FeatureServer/0/query"
HIGHLANDS_FLUM = "https://gis.highlandsfl.gov/server/rest/services/Layers/FLUM/FeatureServer/0/query"
HARDEE_PARCELS = "https://gis.hardeecounty.net/arcgis/rest/services/InfoMap/MapServer/5/query"
HARDEE_LU = "https://gis.hardeecounty.net/arcgis/rest/services/LandUseZoning/MapServer"
GLADES_PARCELS = "https://services6.arcgis.com/90Aakxb3SLGcQGor/arcgis/rest/services/glades_parcels_2026_06_01/FeatureServer/0/query"
GLADES_ZONING = "https://services6.arcgis.com/90Aakxb3SLGcQGor/arcgis/rest/services/GladesCounty_Zoning_03192026/FeatureServer/4/query"
GLADES_FLU = "https://services6.arcgis.com/90Aakxb3SLGcQGor/arcgis/rest/services/GladesCounty_FLU_03192026/FeatureServer/0/query"
HENDRY_PARCELS = "https://services7.arcgis.com/8l7Qq5t0CPLAJwJK/arcgis/rest/services/Parcels_Feb2024/FeatureServer/0/query"
HENDRY_ZONING = "https://services7.arcgis.com/8l7Qq5t0CPLAJwJK/arcgis/rest/services/Zoning/FeatureServer/1/query"
HENDRY_FLU = "https://services7.arcgis.com/8l7Qq5t0CPLAJwJK/arcgis/rest/services/Future_Land_Use___Zoning_Map_WFL1/FeatureServer/8/query"
LABELLE_LIMITS = "https://services7.arcgis.com/8l7Qq5t0CPLAJwJK/arcgis/rest/services/LaBelle_City_Limits/FeatureServer/0/query"
DESOTO_PARCELS = "https://www25.swfwmd.state.fl.us/arcgis12/rest/services/BaseVector/parcel_search/MapServer/3/query"
ARCADIA_ZONING = "https://services5.arcgis.com/gutFqkMq9XlLck8D/arcgis/rest/services/City_of_Arcadia_Zoning/FeatureServer/0/query"
ARCADIA_FLU = "https://services5.arcgis.com/gutFqkMq9XlLck8D/arcgis/rest/services/City_of_Arcadia_Future_Land_Use/FeatureServer/0/query"

SPECS: dict[str, dict] = {
    "12055": {
        "kind": "heartland",
        "source": "fl-highlands-pao-12055",
        "coverage": "complete-gte-5ac",
        "url": PAO,
        "gaps": [
            "Acreage is PAO Calculated_Acres, 5.0–150.0 inclusive. The root Parcels FeatureServer was not used (it is token-gated, not the public PAO layer).",
            "County Zoning.ZON and FLUM.FLUM are attribute-joined on PARCELNO = STRAP_NUM. STRAP is not the zoning key.",
            "Sebring, Avon Park, and Lake Placid have no public city zoning REST. County zoning and FLUM are used inside those cities. City codes are not invented.",
        ],
    },
    "12049": {
        "kind": "heartland",
        "source": "fl-hardee-infomap-12049",
        "coverage": "complete-gte-5ac",
        "url": HARDEE_PARCELS,
        "gaps": [
            "Parcels are InfoMap Owner Parcels (TOTACRES). SWFWMD parcel_search was not needed.",
            "County zoning and future land use are a spatial intersect (no parcel id on those layers).",
            "Wauchula, Bowling Green, and Zolfo Springs zoning and FLU join on PARCEL / Parcel_Id when it matches PIN_DSP, otherwise by intersect. They do not cover unincorporated Hardee.",
            "InfoMap has the last situs and owner. It has no sale price or assessed value.",
        ],
    },
    "12043": {
        "kind": "heartland",
        "source": "fl-glades-agol-2026-06-12043",
        "coverage": "complete-gte-5ac",
        "url": GLADES_PARCELS,
        "gaps": [
            "Parcels are AGOL glades_parcels_2026_06_01. Acreage is the acreage field.",
            "Zoning (GladesCounty_Zoning_03192026 layer 4) and FLU (GladesCounty_FLU_03192026) are spatial. Neither layer has a parcel id.",
            "gis1.hcpao.org Glades MapServers were not used (query disabled).",
        ],
    },
    "12051": {
        "kind": "heartland",
        "source": "fl-hendry-parcels-feb2024-12051",
        "coverage": "complete-gte-5ac",
        "url": HENDRY_PARCELS,
        "gaps": [
            "Parcels are Parcels_Feb2024 (February 2024 vintage), not a later Hendry roll. Acreage is MAP_ACRES.",
            "County zoning is an attribute join on PIN / PARCELNO. Current_Zo values LABELLE and CLEWISTON are city names, not districts, and stay blank.",
            "Future land use is a spatial intersect. LaBelle city limits mark the city boundary only. No LaBelle zoning layer was joined.",
        ],
    },
    "12027": {
        "kind": "heartland",
        "source": "fl-desoto-swfwmd-12027",
        "coverage": "partial",
        "url": DESOTO_PARCELS,
        "gaps": [
            "Parcels are SWFWMD parcel_search DeSoto (CNTYFIPS 027). ACRES is empty; AREANO is the acreage. This is not DeSoto County, Kansas, and not DeSoto County, Mississippi (28033).",
            "Arcadia zoning and future land use are attribute-joined on PARCEL_ID inside the city only.",
            "Unincorporated DeSoto zoning and FLU are not published. They stay blank. The SWFWMD ZONING column is empty and was not used to fill that gap.",
        ],
    },
}


def heartland_spec(fips: str) -> dict:
    spec = SPECS[fips]
    return {
        "kind": spec["kind"],
        "source": spec["source"],
        "coverage": spec["coverage"],
        "url": spec["url"],
        "gaps": list(spec["gaps"]),
    }


def in_heartland(lon: float, lat: float) -> bool:
    west, south, east, north = HEARTLAND_BBOX
    return west <= lon <= east and south <= lat <= north


def extent_outside_heartland(bbox: tuple[float | None, float | None, float | None, float | None]) -> str | None:
    west, south, east, north = bbox
    if west is None or south is None or east is None or north is None:
        return "layer returned no WGS84 extent"
    if north < 24 or south > 31.2 or east < -88 or west > -79.2:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} is outside peninsular Florida "
            "(namesake county). Not joined."
        )
    hw, hs, he, hn = HEARTLAND_BBOX
    if east < hw or west > he or north < hs or south > hn:
        return (
            f"extent {west:.3f},{south:.3f},{east:.3f},{north:.3f} does not intersect "
            "Florida Heartland. Not joined."
        )
    return None


def is_designation(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return False
    if text.upper() in SENTINELS:
        return False
    return True


def parcel_keys(value: Any) -> list[str]:
    text = _clean(value)
    if not text or text.startswith("<"):
        return []
    upper = text.upper()
    compact = re.sub(r"[^A-Z0-9]", "", upper)
    keys: list[str] = []
    for key in (upper, compact):
        if key and key not in keys:
            keys.append(key)
    return keys


def parse_date(value: Any) -> str | None:
    text = _clean(value)
    if text:
        match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
        if match:
            month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[:10] if len(text) >= 10 else text):
            return text[:10]
    number = _num(value)
    if number is not None and number > 10_000_000_000:
        from datetime import datetime, timezone

        try:
            moment = datetime.fromtimestamp(number / 1000, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        if 1900 <= moment.year <= 2100:
            return moment.date().isoformat()
    if number is not None and 1900 <= number <= 2100 and float(number).is_integer():
        return f"{int(number):04d}-01-01"
    return None


def contains_point(geometry: dict | None, x: float, y: float) -> bool:
    if not geometry:
        return False
    return any(_inside_polygon(x, y, poly) for poly in polygon_parts(geometry))


class SpatialIndex:
    def __init__(self, cell: float = 0.02) -> None:
        self.cell = cell
        self.buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)
        self.broad: list[dict] = []

    def add(self, feature: dict) -> None:
        bbox = _bbox(feature.get("geometry"))
        if not bbox:
            return
        west, south, east, north = bbox
        feature["_bboxArea"] = max(0.0, (east - west) * (north - south))
        ix0, ix1 = _cell(west, self.cell), _cell(east, self.cell)
        iy0, iy1 = _cell(south, self.cell), _cell(north, self.cell)
        if (ix1 - ix0 + 1) * (iy1 - iy0 + 1) > 400:
            self.broad.append(feature)
            return
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self.buckets[(ix, iy)].append(feature)

    def hit(self, x: float, y: float) -> dict | None:
        found: list[dict] = []
        for feature in self.buckets.get((_cell(x, self.cell), _cell(y, self.cell)), []):
            if contains_point(feature.get("geometry"), x, y):
                found.append(feature)
        for feature in self.broad:
            if contains_point(feature.get("geometry"), x, y):
                found.append(feature)
        if not found:
            return None
        found.sort(key=lambda item: item.get("_bboxArea") or 0)
        return found[0]


def index_features(features: list[dict]) -> SpatialIndex:
    index = SpatialIndex()
    for feature in features:
        if feature.get("geometry"):
            index.add(feature)
    return index


def _set_zoning(feature: dict, code: str, jurisdiction: str, *, district: str | None = None, force: bool = False) -> bool:
    if not is_designation(code):
        return False
    props = feature["properties"]
    if props.get("zoningCode") and not force:
        return False
    props["zoningCode"] = code.strip()
    label = district.strip() if district and district.strip() and district.strip() != code.strip() else code.strip()
    props["zoningDistrict"] = f"{jurisdiction}:{label}"
    props["jurisdictionCode"] = jurisdiction
    return True


def _set_flu(feature: dict, code: str, jurisdiction: str, source: str, *, label: str | None = None, force: bool = False) -> bool:
    if not is_designation(code):
        return False
    props = feature["properties"]
    if props.get("flu") and not force:
        return False
    props["flu"] = {
        "code": code.strip(),
        "label": (label or code).strip(),
        "jurisdiction": jurisdiction,
        "source": source,
    }
    return True


def _lookup(features: list[dict], id_fields: list[str]) -> dict[str, dict]:
    table: dict[str, dict] = {}
    for feature in features:
        attrs = feature.get("properties") or {}
        for field in id_fields:
            for key in parcel_keys(attrs.get(field)):
                table.setdefault(key, attrs)
    return table


def _match_attrs(table: dict[str, dict], parcel_id: str | None) -> dict | None:
    for key in parcel_keys(parcel_id):
        found = table.get(key)
        if found:
            return found
    return None


def download_heartland(county: dict, markets: list[str], spec: dict) -> dict:
    import seed_market_parcels as seed

    fips = county["fips"]
    print(f"Pulling {county['name']} FL ({fips}) via {spec['source']}", flush=True)
    cache_path = seed.CACHE_DIR / f"{fips}-heartland-v1.json"
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = seed.json.loads(cache_path.read_text())
        if cached.get("version") == 1 and cached.get("features"):
            print(f"  cache hit {len(cached['features'])}", flush=True)
            return _write(seed, county, markets, spec, cached["features"], cached.get("notes") or [])

    notes: list[str] = []
    if fips == "12055":
        features = _highlands(seed, county, markets, notes)
    elif fips == "12049":
        features = _hardee(seed, county, markets, notes)
    elif fips == "12043":
        features = _glades(seed, county, markets, notes)
    elif fips == "12051":
        features = _hendry(seed, county, markets, notes)
    elif fips == "12027":
        features = _desoto(seed, county, markets, notes)
    else:
        raise RuntimeError(f"{fips} is not a Florida Heartland county")

    if not features:
        raise RuntimeError(f"{fips} kept no Heartland parcels")
    if not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError(f"{fips} emitted a parcel outside 5–150 acres")
    if any(not in_heartland(*feature["properties"]["centroid"]) for feature in features):
        raise RuntimeError(f"{fips} emitted a parcel outside Florida Heartland")
    seed.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(seed.json.dumps({"version": 1, "notes": notes, "features": features}, separators=(",", ":")))
    return _write(seed, county, markets, spec, features, notes)


def _write(seed: Any, county: dict, markets: list[str], spec: dict, features: list[dict], notes: list[str]) -> dict:
    for feature in features:
        feature["properties"]["marketIds"] = list(markets)
    path, lookup, tiles = seed.write_tiles(county, features)
    gaps = [*(spec.get("gaps") or []), *notes]
    print(f"  kept {len(features)} ({spec['coverage']})", flush=True)
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
        source_count=len(features),
        dropped=0,
        tile_count=tiles,
    )


def _highlands(seed: Any, county: dict, markets: list[str], notes: list[str]) -> list[dict]:
    _require_extent(seed, PAO, "Highlands PAO parcels")
    raw = _fetch(seed, PAO, "Calculated_Acres>=5 AND Calculated_Acres<=150", [
        "PARCELNO", "STRAP", "Calculated_Acres", "Owner_Name_1", "Owne_Name_2", "SITEADDRESS",
        "Site_Add_C", "Site_Add_Z", "DOR_Code", "Sale_Date_1", "Sale_Price_1", "Assessed_Value",
        "Taxable_Value", "Mailing_Address_Line_1", "Mailing_Address_Line_2", "Mailing_CI",
        "Mailing_ST", "Mailing_ZI",
    ], geometry=True)
    features = []
    for item in raw:
        attrs = item["properties"]
        feature = _feature(
            seed, county, markets, "fl-highlands-pao-12055",
            parcel_id=_clean(attrs.get("PARCELNO")),
            acres=_num(attrs.get("Calculated_Acres")),
            geometry=item.get("geometry"),
            owner=_clean(attrs.get("Owner_Name_1")),
            owner2=_clean(attrs.get("Owne_Name_2")),
            situs=_clean(attrs.get("SITEADDRESS")),
            city=_clean(attrs.get("Site_Add_C")),
            zip_code=seed.zip_str(attrs.get("Site_Add_Z")),
            dor=_clean(attrs.get("DOR_Code")),
            sale_price=_positive(_num(attrs.get("Sale_Price_1"))),
            sale_date=parse_date(attrs.get("Sale_Date_1")),
            assessed=_positive(_num(attrs.get("Assessed_Value"))),
            taxable=_positive(_num(attrs.get("Taxable_Value"))),
            mail1=_clean(attrs.get("Mailing_Address_Line_1")),
            mail2=_clean(attrs.get("Mailing_Address_Line_2")),
            mail_city=_clean(attrs.get("Mailing_CI")),
            mail_state=_clean(attrs.get("Mailing_ST")),
            mail_zip=seed.zip_str(attrs.get("Mailing_ZI")),
        )
        if feature:
            features.append(feature)
    features = _dedupe(features)
    zoning = _attributes(seed, HIGHLANDS_ZONING, ["STRAP_NUM", "ZON", "FLUM"])
    flum = _attributes(seed, HIGHLANDS_FLUM, ["STRAP_NUM", "FLUM"])
    zon_table = _lookup(zoning, ["STRAP_NUM"])
    flu_table = _lookup(flum, ["STRAP_NUM"])
    zoned = 0
    flued = 0
    city_gap = 0
    for feature in features:
        props = feature["properties"]
        zhit = _match_attrs(zon_table, props.get("parcelId"))
        fhit = _match_attrs(flu_table, props.get("parcelId"))
        if zhit and _set_zoning(feature, _clean(zhit.get("ZON")) or "", "Highlands"):
            zoned += 1
        flu_code = _clean((fhit or {}).get("FLUM")) or _clean((zhit or {}).get("FLUM"))
        if flu_code and _set_flu(feature, flu_code, "Highlands", "highlands-flum"):
            flued += 1
        city = (props.get("situsCity") or "").upper()
        if city in HIGHLANDS_CITY_GAP:
            city_gap += 1
            _gap(feature, "City zoning REST is a gap. County zoning and FLUM are used inside this city.")
    notes.append(
        f"Highlands attribute join on PARCELNO: zoning {zoned}/{len(features)}, FLUM {flued}/{len(features)}. "
        f"{city_gap} parcels sit in Sebring, Avon Park, or Lake Placid and keep the county code."
    )
    return features


def _hardee(seed: Any, county: dict, markets: list[str], notes: list[str]) -> list[dict]:
    _require_extent(seed, HARDEE_PARCELS, "Hardee InfoMap Owner Parcels")
    raw = _fetch(seed, HARDEE_PARCELS, "TOTACRES>=5 AND TOTACRES<=150", [
        "PIN_DSP", "OWNNAME", "STREET", "SITUSCITY", "SITUSZIP", "TOTACRES", "STR_NUM",
    ], geometry=True)
    features = []
    for item in raw:
        attrs = item["properties"]
        street = _clean(attrs.get("STREET"))
        number = _clean(attrs.get("STR_NUM"))
        situs = " ".join(part for part in (number, street) if part and part not in {"0", "00"}) or None
        feature = _feature(
            seed, county, markets, "fl-hardee-infomap-12049",
            parcel_id=_clean(attrs.get("PIN_DSP")),
            acres=_num(attrs.get("TOTACRES")),
            geometry=item.get("geometry"),
            owner=_clean(attrs.get("OWNNAME")),
            situs=situs,
            city=_title_city(attrs.get("SITUSCITY")),
            zip_code=seed.zip_str(attrs.get("SITUSZIP")),
        )
        if feature:
            features.append(feature)
    features = _dedupe(features)
    county_zon = _polygons(seed, f"{HARDEE_LU}/20/query", ["ZONING", "CLASS"])
    county_flu = _polygons(seed, f"{HARDEE_LU}/16/query", ["LANDUSECODE", "LANDUSEDESC", "CODE"])
    zoned = _spatial_zoning(features, index_features(county_zon), "ZONING", "Hardee", district_field="CLASS")
    flued = _spatial_flu(features, index_features(county_flu), "LANDUSECODE", "LANDUSEDESC", "Hardee", "hardee-county-flu")
    cities = (
        ("Bowling Green", 17, 13, ["ZON", "FLU", "Parcel_Id"], ["FLU", "ZON", "Parcel_Id"]),
        ("Wauchula", 18, 14, ["ZON", "FLU", "PARCEL", "Parcel_Id"], ["FLU", "ZON", "PARCEL", "Parcel_Id"]),
        ("Zolfo Springs", 19, 15, ["ZON", "FLU", "PARCEL", "Parcel_Id"], ["FLU", "ZON", "PARCEL", "Parcel_Id"]),
    )
    city_zoned = 0
    city_flued = 0
    for name, zon_id, flu_id, zon_fields, flu_fields in cities:
        zoning = _polygons(seed, f"{HARDEE_LU}/{zon_id}/query", zon_fields)
        flu = _polygons(seed, f"{HARDEE_LU}/{flu_id}/query", flu_fields)
        z_table = _lookup(zoning, ["PARCEL", "Parcel_Id"])
        f_table = _lookup(flu, ["PARCEL", "Parcel_Id"])
        z_index = index_features(zoning)
        f_index = index_features(flu)
        for feature in features:
            props = feature["properties"]
            zhit = _match_attrs(z_table, props.get("parcelId"))
            if zhit and _set_zoning(feature, _clean(zhit.get("ZON")) or "", name, force=True):
                city_zoned += 1
            elif not zhit:
                spatial = z_index.hit(*props["centroid"])
                if spatial and _set_zoning(feature, _clean(spatial["properties"].get("ZON")) or "", name, force=True):
                    city_zoned += 1
            fhit = _match_attrs(f_table, props.get("parcelId"))
            if fhit and _set_flu(feature, _clean(fhit.get("FLU")) or "", name, f"hardee-{_slug(name)}-flu", force=True):
                city_flued += 1
            elif not fhit:
                spatial = f_index.hit(*props["centroid"])
                if spatial and _set_flu(feature, _clean(spatial["properties"].get("FLU")) or "", name, f"hardee-{_slug(name)}-flu", force=True):
                    city_flued += 1
    notes.append(
        f"Hardee county spatial join: zoning {zoned}/{len(features)}, FLU {flued}/{len(features)}. "
        f"City override zoning {city_zoned}, FLU {city_flued} (Wauchula, Bowling Green, Zolfo Springs)."
    )
    return features


def _glades(seed: Any, county: dict, markets: list[str], notes: list[str]) -> list[dict]:
    _require_extent(seed, GLADES_PARCELS, "Glades parcels 2026-06")
    raw = _fetch(seed, GLADES_PARCELS, "acreage>=5 AND acreage<=150", [
        "PARCELNO", "acreage", "own1", "own2", "str_num", "str_predir", "str_name", "str_sfx",
        "s_city", "s_zip", "addr_1", "addr_2", "o_city", "o_state", "o_zip", "use_cd",
        "prc1", "dos1", "tax_val", "bxcm_val",
    ], geometry=True)
    features = []
    for item in raw:
        attrs = item["properties"]
        situs = " ".join(
            part for part in (
                _clean(attrs.get("str_num")),
                _clean(attrs.get("str_predir")),
                _clean(attrs.get("str_name")),
                _clean(attrs.get("str_sfx")),
            ) if part and part not in {"0"}
        ) or None
        feature = _feature(
            seed, county, markets, "fl-glades-agol-2026-06-12043",
            parcel_id=_clean(attrs.get("PARCELNO")),
            acres=_num(attrs.get("acreage")),
            geometry=item.get("geometry"),
            owner=_clean(attrs.get("own1")),
            owner2=_clean(attrs.get("own2")),
            situs=situs,
            city=_title_city(attrs.get("s_city")),
            zip_code=seed.zip_str(attrs.get("s_zip")),
            dor=_clean(attrs.get("use_cd")),
            sale_price=_positive(_num(attrs.get("prc1"))),
            sale_date=parse_date(attrs.get("dos1")),
            market_value=_positive(_num(attrs.get("bxcm_val"))),
            assessed=_positive(_num(attrs.get("tax_val"))),
            mail1=_clean(attrs.get("addr_1")),
            mail2=_clean(attrs.get("addr_2")),
            mail_city=_clean(attrs.get("o_city")),
            mail_state=_clean(attrs.get("o_state")),
            mail_zip=seed.zip_str(attrs.get("o_zip")),
        )
        if feature:
            features.append(feature)
    features = _dedupe(features)
    zoning = _polygons(seed, GLADES_ZONING, ["Zoning", "ZonDistNam"])
    flu = _polygons(seed, GLADES_FLU, ["FLU"])
    zoned = _spatial_zoning(features, index_features(zoning), "Zoning", "Glades", district_field="ZonDistNam")
    flued = _spatial_flu(features, index_features(flu), "FLU", None, "Glades", "glades-flu-2026-03")
    notes.append(f"Glades spatial join: zoning {zoned}/{len(features)}, FLU {flued}/{len(features)} (March 2026 layers).")
    return features


def _hendry(seed: Any, county: dict, markets: list[str], notes: list[str]) -> list[dict]:
    _require_extent(seed, HENDRY_PARCELS, "Hendry Parcels_Feb2024")
    raw = _fetch(seed, HENDRY_PARCELS, "MAP_ACRES>=5 AND MAP_ACRES<=150", [
        "PIN", "PARCELNO", "MAP_ACRES", "OWNAME", "LOCADD", "LAT", "LON", "PUSE1", "TJUST", "TASSD",
    ], geometry=True)
    features = []
    for item in raw:
        attrs = item["properties"]
        feature = _feature(
            seed, county, markets, "fl-hendry-parcels-feb2024-12051",
            parcel_id=_clean(attrs.get("PIN")) or _clean(attrs.get("PARCELNO")),
            acres=_num(attrs.get("MAP_ACRES")),
            geometry=item.get("geometry"),
            owner=_clean(attrs.get("OWNAME")),
            situs=_clean(attrs.get("LOCADD")),
            dor=_clean(attrs.get("PUSE1")),
            market_value=_positive(_num(attrs.get("TJUST"))),
            assessed=_positive(_num(attrs.get("TASSD"))),
        )
        if not feature:
            continue
        lat = _num(attrs.get("LAT"))
        lon = _num(attrs.get("LON"))
        if lat and lon and not in_heartland(lon, lat):
            continue
        features.append(feature)
    features = _dedupe(features)
    zoning = _attributes(seed, HENDRY_ZONING, ["PIN", "PARCELNO", "Current_Zo"])
    table = _lookup(zoning, ["PIN", "PARCELNO"])
    limits = _polygons(seed, LABELLE_LIMITS, ["Name"], where="Name='City of LaBelle'")
    limit_index = index_features(limits)
    flu = _polygons(seed, HENDRY_FLU, ["FLU"])
    zoned = 0
    blanked = 0
    inside = 0
    for feature in features:
        props = feature["properties"]
        hit = _match_attrs(table, props.get("parcelId"))
        code = _clean((hit or {}).get("Current_Zo"))
        if code and not is_designation(code):
            blanked += 1
            code = None
        if code and _set_zoning(feature, code, "Hendry"):
            zoned += 1
        if limit_index.hit(*props["centroid"]):
            inside += 1
            if not props.get("situsCity"):
                props["situsCity"] = "LaBelle"
            if not props.get("zoningCode"):
                _gap(feature, "Inside LaBelle. County Current_Zo is not a district here, and no city zoning layer was joined.")
    flued = _spatial_flu(features, index_features(flu), "FLU", None, "Hendry", "hendry-flu")
    notes.append(
        f"Hendry Feb 2024 roll. Zoning attribute join {zoned}/{len(features)}. "
        f"{blanked} city-name sentinels left blank. {inside} parcels fall inside LaBelle city limits. FLU spatial {flued}/{len(features)}."
    )
    return features


def _desoto(seed: Any, county: dict, markets: list[str], notes: list[str]) -> list[dict]:
    _require_extent(seed, DESOTO_PARCELS, "SWFWMD DeSoto parcels")
    where = "AREANO>=5 AND AREANO<=150 AND CNTYFIPS='027'"
    raw = _fetch(seed, DESOTO_PARCELS, where, [
        "PARCELID", "PARNO", "ALTKEY", "AREANO", "CNTYNAME", "CNTYFIPS", "OWNERNAME", "SITEADD",
        "SCITY", "SZIP", "MAILADD", "MCITY", "MSTATE", "MZIP", "SALE1_AMT", "SALE1_YEAR", "SALE1_DATE",
        "ASSD_TOT", "PARVAL", "DORUSECODE", "PARUSECODE", "OBJECTID",
    ], geometry=True)
    features = []
    for item in raw:
        attrs = item["properties"]
        name = (_clean(attrs.get("CNTYNAME")) or "").upper()
        fips = _clean(attrs.get("CNTYFIPS"))
        if fips not in {"027", "12027"} and name not in {"DESOTO", "DE SOTO"}:
            continue
        parcel_id = _clean(attrs.get("PARCELID")) or _clean(attrs.get("PARNO")) or _clean(attrs.get("ALTKEY"))
        if parcel_id in {None, ""}:
            oid = attrs.get("OBJECTID")
            parcel_id = f"oid-{oid}" if oid is not None else None
        feature = _feature(
            seed, county, markets, "fl-desoto-swfwmd-12027",
            parcel_id=parcel_id,
            acres=_num(attrs.get("AREANO")),
            geometry=item.get("geometry"),
            owner=_clean(attrs.get("OWNERNAME")),
            situs=_clean(attrs.get("SITEADD")),
            city=_title_city(attrs.get("SCITY")),
            zip_code=seed.zip_str(attrs.get("SZIP")),
            dor=_clean(attrs.get("DORUSECODE")) or _clean(attrs.get("PARUSECODE")),
            sale_price=_positive(_num(attrs.get("SALE1_AMT"))),
            sale_date=parse_date(attrs.get("SALE1_DATE")) or parse_date(attrs.get("SALE1_YEAR")),
            assessed=_positive(_num(attrs.get("ASSD_TOT"))) or _positive(_num(attrs.get("PARVAL"))),
            mail1=_clean(attrs.get("MAILADD")),
            mail_city=_clean(attrs.get("MCITY")),
            mail_state=_clean(attrs.get("MSTATE")),
            mail_zip=seed.zip_str(attrs.get("MZIP")),
        )
        if feature:
            features.append(feature)
    features = _dedupe(features)
    _require_extent(seed, ARCADIA_ZONING, "Arcadia zoning")
    zoning = _attributes(seed, ARCADIA_ZONING, ["PARCEL_ID", "PARCEL", "ZON", "CITY", "COUNTY"])
    flu = _attributes(seed, ARCADIA_FLU, ["PARCEL_ID", "PARCEL", "FLU", "CITY", "COUNTY"])
    z_table = _lookup(zoning, ["PARCEL_ID", "PARCEL"])
    f_table = _lookup(flu, ["PARCEL_ID", "PARCEL"])
    zoned = 0
    flued = 0
    for feature in features:
        props = feature["properties"]
        zhit = _match_attrs(z_table, props.get("parcelId"))
        city_name = (_clean((zhit or {}).get("CITY")) or "").upper()
        county_name = (_clean((zhit or {}).get("COUNTY")) or "").upper()
        if zhit and (city_name in {"", "ARCADIA"}) and county_name in {"", "DESOTO", "DE SOTO"}:
            if _set_zoning(feature, _clean(zhit.get("ZON")) or "", "Arcadia"):
                zoned += 1
        fhit = _match_attrs(f_table, props.get("parcelId"))
        flu_city = (_clean((fhit or {}).get("CITY")) or "").upper()
        flu_county = (_clean((fhit or {}).get("COUNTY")) or "").upper()
        if fhit and flu_city in {"", "ARCADIA"} and flu_county in {"", "DESOTO", "DE SOTO"}:
            if _set_flu(feature, _clean(fhit.get("FLU")) or "", "Arcadia", "arcadia-flu"):
                flued += 1
                if not props.get("jurisdictionCode"):
                    props["jurisdictionCode"] = "Arcadia"
        if props.get("jurisdictionCode") != "Arcadia":
            _gap(feature, "Unincorporated DeSoto zoning and FLU are not published.")
    notes.append(
        f"DeSoto partial. Arcadia attribute join zoning {zoned}/{len(features)}, FLU {flued}/{len(features)}. "
        f"Unincorporated parcels stay blank."
    )
    return features


def _spatial_zoning(features: list[dict], index: SpatialIndex, field: str, jurisdiction: str, *, district_field: str | None = None) -> int:
    matched = 0
    for feature in features:
        hit = index.hit(*feature["properties"]["centroid"])
        if not hit:
            continue
        district = _clean(hit["properties"].get(district_field)) if district_field else None
        if _set_zoning(feature, _clean(hit["properties"].get(field)) or "", jurisdiction, district=district):
            matched += 1
    return matched


def _spatial_flu(features: list[dict], index: SpatialIndex, field: str, label_field: str | None, jurisdiction: str, source: str) -> int:
    matched = 0
    for feature in features:
        if feature["properties"].get("flu"):
            continue
        hit = index.hit(*feature["properties"]["centroid"])
        if not hit:
            continue
        label = _clean(hit["properties"].get(label_field)) if label_field else None
        if _set_flu(feature, _clean(hit["properties"].get(field)) or "", jurisdiction, source, label=label):
            matched += 1
    return matched


def _feature(seed: Any, county: dict, markets: list[str], source: str, **kwargs: Any) -> dict | None:
    geometry = kwargs.get("geometry")
    if not geometry:
        return None
    center = representative_point(geometry)
    if not center or not in_heartland(*center):
        return None
    acres = kwargs.get("acres")
    if not seed.in_band(acres):
        return None
    parcel_id = kwargs.get("parcel_id")
    if not parcel_id:
        return None
    feature = seed.empty_feature(
        fips=county["fips"],
        county=county["name"],
        state="Florida",
        markets=markets,
        parcel_id=parcel_id,
        acreage=acres,
        geometry=geometry,
        center=center,
        source=source,
        owner=kwargs.get("owner"),
        situs=kwargs.get("situs"),
        city=kwargs.get("city"),
        zip_code=kwargs.get("zip_code"),
        dor=kwargs.get("dor"),
        sale_price=kwargs.get("sale_price"),
        sale_date=kwargs.get("sale_date"),
        assessed=kwargs.get("assessed"),
        taxable=kwargs.get("taxable"),
        market_value=kwargs.get("market_value"),
        mail1=kwargs.get("mail1"),
        mail2=kwargs.get("mail2"),
        mail_city=kwargs.get("mail_city"),
        mail_state=kwargs.get("mail_state"),
        mail_zip=kwargs.get("mail_zip"),
    )
    if kwargs.get("owner2"):
        feature["properties"]["ownerName2"] = kwargs["owner2"]
    return feature


def _dedupe(features: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for feature in features:
        parcel_id = feature["properties"]["parcelId"]
        previous = by_id.get(parcel_id)
        if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[parcel_id] = feature
    rows = list(by_id.values())
    rows.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return rows


def _gap(feature: dict, text: str) -> None:
    gaps = feature["properties"].setdefault("dataGaps", [])
    if text not in gaps:
        gaps.append(text)


def _require_extent(seed: Any, url: str, label: str) -> None:
    bbox = _extent(seed, url)
    problem = extent_outside_heartland(bbox)
    if problem:
        raise RuntimeError(f"{label}: {problem}")
    west, south, east, north = bbox
    print(f"  {label} extent {west:.3f},{south:.3f},{east:.3f},{north:.3f}", flush=True)


def _extent(seed: Any, url: str, where: str = "1=1") -> tuple[float | None, float | None, float | None, float | None]:
    data = seed.fetch_json(url, {"where": where, "returnExtentOnly": "true", "outSR": "4326", "f": "json"})
    if data.get("error"):
        raise RuntimeError(seed.json.dumps(data["error"])[:240])
    extent = data.get("extent") or {}
    return extent.get("xmin"), extent.get("ymin"), extent.get("xmax"), extent.get("ymax")


def _fetch(seed: Any, url: str, where: str, fields: list[str], *, geometry: bool, batch: int | None = None) -> list[dict]:
    ids = seed.fetch_object_ids(url, where)
    try:
        expected = seed.count_where(url, where)
    except Exception:  # noqa: BLE001
        expected = len(ids)
    if expected > len(ids) + 5:
        print(f"  object ids {len(ids)} < count {expected}; paging {url.split('/rest/services/')[-1][:70]}", flush=True)
        return _fetch_paged(seed, url, where, fields, geometry=geometry, expected=expected)
    print(f"  rows {len(ids)} {url.split('/rest/services/')[-1][:80]}", flush=True)
    page = batch if batch is not None else (60 if geometry else 200)
    features: list[dict] = []
    for start in range(0, len(ids), page):
        chunk = ids[start : start + page]
        features.extend(_fetch_chunk(seed, url, chunk, fields, geometry=geometry))
        done = min(start + len(chunk), len(ids))
        if done == len(ids) or done % 2000 == 0:
            print(f"    {done}/{len(ids)}", flush=True)
    return features


def _fetch_chunk(seed: Any, url: str, chunk: list[int], fields: list[str], *, geometry: bool) -> list[dict]:
    params = {
        "objectIds": ",".join(str(i) for i in chunk),
        "outFields": ",".join(fields),
        "returnGeometry": "true" if geometry else "false",
        "outSR": "4326",
        "f": "json",
    }
    try:
        data = seed.fetch_json(url, params, timeout=180)
    except Exception:
        if len(chunk) <= 1:
            raise
        mid = max(1, len(chunk) // 2)
        return _fetch_chunk(seed, url, chunk[:mid], fields, geometry=geometry) + _fetch_chunk(
            seed, url, chunk[mid:], fields, geometry=geometry
        )
    if data.get("error"):
        if len(chunk) <= 1:
            raise RuntimeError(seed.json.dumps(data["error"])[:300])
        mid = max(1, len(chunk) // 2)
        return _fetch_chunk(seed, url, chunk[:mid], fields, geometry=geometry) + _fetch_chunk(
            seed, url, chunk[mid:], fields, geometry=geometry
        )
    features: list[dict] = []
    for item in data.get("features") or []:
        attrs = item.get("attributes") or {}
        geom = None
        if geometry:
            rings = (item.get("geometry") or {}).get("rings")
            geom = esri_rings_to_geojson(rings) if rings else None
            if not geom:
                continue
        features.append({"type": "Feature", "geometry": geom, "properties": attrs})
    return features


def _fetch_paged(seed: Any, url: str, where: str, fields: list[str], *, geometry: bool, expected: int) -> list[dict]:
    page = 200 if not geometry else 80
    features: list[dict] = []
    offset = 0
    seen = 0
    while offset < expected + page:
        params = {
            "where": where,
            "outFields": ",".join(fields),
            "returnGeometry": "true" if geometry else "false",
            "outSR": "4326",
            "resultOffset": str(offset),
            "resultRecordCount": str(page),
            "orderByFields": "OBJECTID",
            "f": "json",
        }
        data = seed.fetch_json(url, params, timeout=180)
        if data.get("error"):
            raise RuntimeError(seed.json.dumps(data["error"])[:300])
        batch = data.get("features") or []
        if not batch:
            break
        for item in batch:
            attrs = item.get("attributes") or {}
            geom = None
            if geometry:
                rings = (item.get("geometry") or {}).get("rings")
                geom = esri_rings_to_geojson(rings) if rings else None
                if not geom:
                    continue
            features.append({"type": "Feature", "geometry": geom, "properties": attrs})
        seen += len(batch)
        offset += len(batch)
        print(f"    {seen}/{expected}", flush=True)
        if len(batch) < page and not data.get("exceededTransferLimit"):
            break
    return features


def _attributes(seed: Any, url: str, fields: list[str], where: str = "1=1") -> list[dict]:
    _require_extent(seed, url, url.split("/rest/services/")[-1][:70])
    return _fetch(seed, url, where, fields, geometry=False)


def _polygons(seed: Any, url: str, fields: list[str], where: str = "1=1") -> list[dict]:
    _require_extent(seed, url, url.split("/rest/services/")[-1][:70])
    return _fetch(seed, url, where, fields, geometry=True, batch=100)


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        return None
    return parsed


def _positive(value: float | None) -> float | None:
    if value is None or value <= 0:
        return None
    return value


def _title_city(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    return " ".join(part.capitalize() for part in text.split())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _bbox(geometry: dict | None) -> tuple[float, float, float, float] | None:
    if not geometry:
        return None
    xs: list[float] = []
    ys: list[float] = []
    for poly in polygon_parts(geometry):
        for ring in poly:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _cell(value: float, size: float) -> int:
    return int(value // size)
