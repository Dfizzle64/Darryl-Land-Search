#!/usr/bin/env python3
"""Enrich Davidson County, North Carolina parcels (FIPS 37057).

This is Winston-Salem / Charlotte. It is not Davidson County, Tennessee (47037).

Wire source is the county OpenGov tax-parcel layer. NC OneMap is not used:
its sale date is empty for this county. Municipal zoning and Wallburg future
land use are joined from public city layers. OZ 2.0 eligibility (2020 tracts,
Rev. Proc. 2026-14) is stored separately from current designated QOZs (HUD
2010 tracts). Eligible is never copied into the designated field.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from parcel_geometry import esri_rings_to_geojson

ROOT = Path(__file__).resolve().parents[1]
ELIGIBLE_PACKS = ROOT / "data" / "fixtures" / "oz2-eligible-packs.geojson"

TAX_PARCELS = "https://webgis.co.davidson.nc.us/arcgis/rest/services/OpenGov/OpenGov/MapServer/6/query"
LEXINGTON_ZONING = (
    "https://services3.arcgis.com/Z7ioXMhIaRIEQx1O/arcgis/rest/services/"
    "CITY_ZONING_DISTRICTS_view/FeatureServer/0/query"
)
THOMASVILLE_ZONING = "https://maps.ptrc.org/arcgis/rest/services/Thomasville/Thomasville/MapServer/14/query"
WALLBURG_FLU = "https://maps.ptrc.org/arcgis/rest/services/Wallburg/Wallburg_LDP_2026/MapServer/1/query"
WALLBURG_ZONING = "https://maps.ptrc.org/arcgis/rest/services/Wallburg/Wallburg_LDP_2026/MapServer/3/query"
HUD_OZ = (
    "https://services.arcgis.com/VTyQ9soqVukalItT/ArcGIS/rest/services/"
    "Opportunity_Zones/FeatureServer/13/query"
)

# Generous WGS84 window around Davidson County, NC. Davidson County, TN is near -87.
NC_LON = (-80.75, -79.8)
NC_LAT = (35.3, 36.2)

# Checked against EconDev municipal boundaries, not the earlier card.
# 32 sits in Denton, 33 in Wallburg, 34 in Midway.
CITY_NAMES = {
    "07": "Lexington",
    "28": "Thomasville",
    "32": "Denton",
    "33": "Wallburg",
    "34": "Midway",
    "39": "High Point",
}
ROLL_ONLY_CITIES = {"Midway", "Denton", "High Point"}
UNINCORPORATED = "Unincorporated"

# 2020 tracts in the shipped Winston-Salem pack. 61903 is the only rural one.
ELIGIBLE_RURAL = {"37057061903"}
ELIGIBLE_GEOIDS = {
    "37057060800",
    "37057061203",
    "37057061204",
    "37057061300",
    "37057061400",
    "37057061501",
    "37057061600",
    "37057061803",
    "37057061903",
}

FLU_LABELS = {
    "AG": "Agricultural",
    "COM": "Commercial",
    "IND": "Industrial",
    "LDR": "Low-density residential",
    "MDR": "Medium-density residential",
    "MIX": "Mixed use",
    "PI": "Public / institutional",
    "REC": "Recreation",
}

APPRAISER_URL = "https://taxsearch.co.davidson.nc.us/RealEstateSearch"
SOURCE = "nc-davidson-opengov-37057"

BASE_GAPS = [
    "Acreage is Davidson County, NC legal acres (LegalLandType AC), not NC OneMap GIS acres.",
    "Sale day is not on the roll; the stored date is the first of the sale month.",
    "OZ 2.0 is Rev. Proc. 2026-14 nomination eligibility. It is not a designated Qualified Opportunity Zone.",
]


def fetch_json(url: str, params: dict | None = None, timeout: int = 180, retries: int = 5) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/davidson-nc"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:180]}: {last}")


def clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def city_code(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    if text.isdigit():
        return text.zfill(2)
    return text


def placeholder_zoning(code: str | None) -> bool:
    if not code:
        return False
    text = code.upper()
    if "CITY ZONING" in text or "TOWN ZONING" in text:
        return True
    return text in {"CITY OF HIGH POINT", "DENTON ETJ", "THOMASVILLE ZONING - ETJ"}


def point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_geometry(x: float, y: float, geometry: dict | None) -> bool:
    if not geometry:
        return False
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        if not coords or not point_in_ring(x, y, coords[0]):
            return False
        return not any(point_in_ring(x, y, hole) for hole in coords[1:])
    if kind == "MultiPolygon":
        for poly in coords:
            if poly and point_in_ring(x, y, poly[0]) and not any(point_in_ring(x, y, hole) for hole in poly[1:]):
                return True
    return False


def hits(x: float, y: float, features: list[dict]) -> list[dict]:
    return [feature for feature in features if point_in_geometry(x, y, feature.get("geometry"))]


def esri_features(data: dict) -> list[dict]:
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    if data.get("type") == "FeatureCollection":
        return [feature for feature in data.get("features") or [] if feature.get("geometry")]
    features: list[dict] = []
    for item in data.get("features") or []:
        geom = item.get("geometry") or {}
        if geom.get("rings"):
            geometry = esri_rings_to_geojson(geom["rings"])
        elif geom.get("type"):
            geometry = geom
        else:
            geometry = None
        if not geometry:
            continue
        props = item.get("attributes") or item.get("properties") or {}
        features.append({"type": "Feature", "geometry": geometry, "properties": props})
    return features


def fetch_layer(url: str, where: str, fields: str, *, geometry: bool) -> list[dict]:
    page = 2000
    offset = 0
    rows: list[dict] = []
    while True:
        params = {
            "where": where,
            "outFields": fields,
            "returnGeometry": "true" if geometry else "false",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": page,
            "orderByFields": "OBJECTID",
        }
        if geometry:
            params["outSR"] = "4326"
        data = fetch_json(url, params)
        if data.get("error") and offset == 0 and "orderByFields" in params:
            params.pop("orderByFields", None)
            data = fetch_json(url, params)
        if data.get("error"):
            raise RuntimeError(json.dumps(data["error"])[:300])
        batch = data.get("features") or []
        if geometry:
            rows.extend(esri_features({"features": batch}))
        else:
            rows.extend(batch)
        if not data.get("exceededTransferLimit") and len(batch) < page:
            break
        if not batch:
            break
        offset += len(batch)
        time.sleep(0.05)
    return rows


def load_eligible_tracts() -> list[dict]:
    collection = json.loads(ELIGIBLE_PACKS.read_text())
    found: dict[str, dict] = {}
    for feature in collection.get("features") or []:
        props = feature.get("properties") or {}
        geoid = str(props.get("tractGeoid") or "")
        if geoid not in ELIGIBLE_GEOIDS:
            continue
        if props.get("state") not in {None, "North Carolina"}:
            continue
        if props.get("county") not in {None, "Davidson"}:
            continue
        if props.get("designation") != "eligible-for-nomination":
            raise RuntimeError(f"{geoid} is not marked eligible-for-nomination in the tract pack")
        found[geoid] = feature
    missing = ELIGIBLE_GEOIDS - set(found)
    if missing:
        raise RuntimeError(f"Davidson NC eligible tract pack is missing {sorted(missing)}")
    for geoid, feature in found.items():
        rural = bool((feature.get("properties") or {}).get("rural"))
        if rural != (geoid in ELIGIBLE_RURAL):
            raise RuntimeError(f"{geoid} rural flag {rural} does not match the Rev. Proc. pack")
    return list(found.values())


def tract_name(tract: str, geoid: str) -> str:
    digits = "".join(ch for ch in tract if ch.isdigit()) or (geoid[-6:] if len(geoid) >= 6 else "")
    if not digits:
        return geoid or "Opportunity Zone"
    value = int(digits)
    if value % 100 == 0:
        pretty = str(value // 100)
    else:
        pretty = f"{value / 100:.2f}".rstrip("0")
    return f"Census tract {pretty}"


def load_designated_zones() -> list[dict]:
    data = fetch_json(
        HUD_OZ,
        {
            "where": "STATE='37' AND COUNTY='057'",
            "outFields": "GEOID10,TRACT,Rural,STATE,COUNTY",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        },
    )
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:300])
    features = []
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        geoid = str(props.get("GEOID10") or props.get("geoid") or "").strip()
        if not geoid.startswith("37057"):
            continue
        rural_raw = props.get("Rural") if props.get("Rural") is not None else props.get("rural")
        designated_rural = None
        if isinstance(rural_raw, str) and rural_raw.strip():
            designated_rural = rural_raw.strip().upper() in {"Y", "YES", "1", "TRUE"}
        tract = str(props.get("TRACT") or geoid[-6:])
        features.append(
            {
                "type": "Feature",
                "geometry": feature.get("geometry"),
                "properties": {
                    "tractGeoid": geoid,
                    "tractName": tract_name(tract, geoid),
                    "designatedRural": designated_rural,
                },
            }
        )
    if not features:
        raise RuntimeError("HUD returned no designated QOZ polygons for Davidson County, NC")
    return features


def lexington_index() -> dict[str, list[dict]]:
    rows = fetch_layer(
        LEXINGTON_ZONING,
        "1=1",
        "PIN,PARCEL_ID,ZoningDistrict,ZoningDistrictName",
        geometry=False,
    )
    grouped: dict[str, list[dict]] = {}
    for item in rows:
        attrs = item.get("attributes") or item.get("properties") or {}
        pin = clean(attrs.get("PIN"))
        if not pin:
            continue
        grouped.setdefault(pin, []).append(attrs)
    return grouped


def apply_municipality(feature: dict) -> str:
    props = feature["properties"]
    code = city_code(props.get("jurisdictionCode"))
    name = CITY_NAMES.get(code or "", UNINCORPORATED)
    props["jurisdictionCode"] = code
    props["jurisdictionPrefix"] = name
    props["situsCity"] = name
    return name


def apply_lexington(feature: dict, index: dict[str, list[dict]]) -> str:
    props = feature["properties"]
    rows = index.get(props.get("parcelId") or "") or []
    codes: list[str] = []
    for row in rows:
        code = clean(row.get("ZoningDistrict"))
        if code and code not in codes:
            codes.append(code)
    if not codes:
        return "miss"
    codes.sort()
    props["zoningCode"] = " / ".join(codes)
    props["zoningDistrict"] = None
    return "hit"


def apply_spatial_zoning(feature: dict, layer: list[dict], field: str) -> str:
    lon, lat = feature["properties"]["centroid"]
    found = []
    for item in hits(lon, lat, layer):
        code = clean((item.get("properties") or {}).get(field))
        if code and not placeholder_zoning(code) and code not in found:
            found.append(code)
    if not found:
        return "miss"
    found.sort()
    feature["properties"]["zoningCode"] = " / ".join(found)
    feature["properties"]["zoningDistrict"] = None
    return "hit"


def apply_wallburg_flu(feature: dict, layer: list[dict]) -> str:
    lon, lat = feature["properties"]["centroid"]
    codes: list[str] = []
    for item in hits(lon, lat, layer):
        code = clean((item.get("properties") or {}).get("FLU"))
        if code and code not in codes:
            codes.append(code)
    if not codes:
        return "miss"
    codes.sort()
    code = " / ".join(codes)
    label = " / ".join(FLU_LABELS.get(part, part) for part in codes)
    feature["properties"]["flu"] = {
        "code": code,
        "label": label,
        "jurisdiction": "Wallburg",
        "source": "ptrc-wallburg-ldp-2026",
    }
    return "hit"


def stamp_zones(feature: dict, eligible: list[dict], designated: list[dict] | None) -> None:
    """Eligibility and designation are different vintages and different fields."""
    props = feature["properties"]
    lon, lat = props["centroid"]
    eligible_hits = hits(lon, lat, eligible)
    if len(eligible_hits) > 1:
        # Prefer the rural flag we already validated; do not invent a second tract.
        eligible_hits = eligible_hits[:1]
    if eligible_hits:
        hp = eligible_hits[0]["properties"]
        geoid = str(hp.get("tractGeoid"))
        props["oz2Eligibility"] = {
            "eligible": True,
            "rural": bool(hp.get("rural")),
            "tractGeoid": geoid,
            "tractName": hp.get("name"),
            "designation": "eligible-for-nomination",
            "source": "rev-proc-2026-14",
        }
    else:
        props["oz2Eligibility"] = {
            "eligible": False,
            "rural": None,
            "tractGeoid": None,
            "tractName": None,
            "designation": "not-eligible",
            "source": "rev-proc-2026-14",
        }
    if designated is None:
        props["opportunityZone"] = None
        return
    zone_hits = hits(lon, lat, designated)
    if zone_hits:
        zp = zone_hits[0]["properties"]
        props["opportunityZone"] = {
            "inOpportunityZone": True,
            "tractGeoid": zp.get("tractGeoid"),
            "tractName": zp.get("tractName"),
            "source": "hud-fs-13",
            "designatedRural": zp.get("designatedRural"),
        }
    else:
        props["opportunityZone"] = {
            "inOpportunityZone": False,
            "tractGeoid": None,
            "tractName": None,
            "source": "hud-fs-13",
            "designatedRural": None,
        }


def assert_not_conflated(features: list[dict]) -> None:
    for feature in features:
        props = feature["properties"]
        oz2 = props.get("oz2Eligibility") or {}
        oz = props.get("opportunityZone") or {}
        designation = oz2.get("designation")
        if designation not in {None, "eligible-for-nomination", "not-eligible"}:
            raise RuntimeError(f"Bad OZ 2.0 designation on {props.get('id')}: {designation}")
        if oz.get("source") == "rev-proc-2026-14":
            raise RuntimeError(f"Designated QOZ used the eligibility source on {props.get('id')}")
        if oz2.get("eligible") and designation != "eligible-for-nomination":
            raise RuntimeError(f"Eligible parcel {props.get('id')} is not marked eligible-for-nomination")
        if oz2.get("tractGeoid") == "37057061903":
            if oz.get("inOpportunityZone") is True:
                raise RuntimeError("Rural-eligible tract 37057061903 was stamped as a designated QOZ")
            if oz2.get("rural") is not True:
                raise RuntimeError("Tract 37057061903 lost its rural eligibility flag")


def enrich_davidson_nc_parcels(features: list[dict]) -> tuple[list[dict], list[str], int]:
    kept: list[dict] = []
    outside = 0
    for feature in features:
        lon, lat = feature["properties"]["centroid"]
        if not (NC_LON[0] <= lon <= NC_LON[1] and NC_LAT[0] <= lat <= NC_LAT[1]):
            outside += 1
            continue
        if feature["properties"].get("countyFips") != "37057":
            raise RuntimeError("Refusing to enrich a parcel that is not FIPS 37057")
        kept.append(feature)
    if outside > max(25, len(features) // 100):
        raise RuntimeError(f"{outside} parcels fell outside Davidson County, NC. Refusing the extract.")

    notes: list[str] = []
    try:
        lex = lexington_index()
        print(f"  Lexington zoning pins {len(lex)}", flush=True)
    except Exception as exc:  # noqa: BLE001
        lex = {}
        notes.append(f"Lexington city zoning join failed ({exc}). City parcels keep LandZoning.")
    try:
        thomasville = fetch_layer(THOMASVILLE_ZONING, "1=1", "ZONING", geometry=True)
        print(f"  Thomasville zoning polygons {len(thomasville)}", flush=True)
    except Exception as exc:  # noqa: BLE001
        thomasville = []
        notes.append(f"Thomasville zoning join failed ({exc}). City parcels keep LandZoning.")
    try:
        wallburg_zoning = fetch_layer(WALLBURG_ZONING, "1=1", "ZONE_CODE", geometry=True)
        wallburg_flu = fetch_layer(WALLBURG_FLU, "1=1", "FLU", geometry=True)
        print(f"  Wallburg zoning {len(wallburg_zoning)} flu {len(wallburg_flu)}", flush=True)
    except Exception as exc:  # noqa: BLE001
        wallburg_zoning = []
        wallburg_flu = []
        notes.append(f"Wallburg zoning/FLU join failed ({exc}).")
    try:
        designated = load_designated_zones()
        print(f"  HUD designated tracts {len(designated)}", flush=True)
    except Exception as exc:  # noqa: BLE001
        designated = None
        notes.append(
            "Designated QOZ polygons could not be loaded from HUD. "
            "Eligibility was not copied into the designated field."
            f" ({exc})"
        )
    eligible = load_eligible_tracts()

    lex_hit = lex_miss = tv_hit = tv_miss = wb_z = wb_flu = 0
    muni_counts: dict[str, int] = {}
    for feature in kept:
        props = feature["properties"]
        props["source"] = SOURCE
        props["state"] = "North Carolina"
        props["countyName"] = "Davidson"
        props["countyFips"] = "37057"
        props["appraiserUrl"] = APPRAISER_URL
        if "Nashville" in (props.get("marketIds") or []):
            raise RuntimeError("Davidson NC parcel was tagged with the Nashville market")
        name = apply_municipality(feature)
        muni_counts[name] = muni_counts.get(name, 0) + 1
        props["flu"] = None
        zoning = props.get("zoningCode")
        if placeholder_zoning(zoning):
            props["zoningCode"] = None
        if name == "Lexington" and lex:
            if apply_lexington(feature, lex) == "hit":
                lex_hit += 1
            else:
                lex_miss += 1
        elif name == "Thomasville" and thomasville:
            if apply_spatial_zoning(feature, thomasville, "ZONING") == "hit":
                tv_hit += 1
            else:
                tv_miss += 1
        elif name == "Wallburg" and wallburg_zoning:
            if apply_spatial_zoning(feature, wallburg_zoning, "ZONE_CODE") == "hit":
                wb_z += 1
        if name == "Wallburg" and wallburg_flu:
            if apply_wallburg_flu(feature, wallburg_flu) == "hit":
                wb_flu += 1
        else:
            props["flu"] = None
        stamp_zones(feature, eligible, designated)
        gaps = list(BASE_GAPS)
        if not (props.get("flu") or {}).get("code"):
            gaps.append("No public future land use for this parcel. Wallburg's 2026 LDP is the only FLU layer joined.")
        if name in ROLL_ONLY_CITIES:
            gaps.append(
                f"{name} has no dedicated public zoning FeatureServer. The district is the tax-roll LandZoning code."
            )
        if name == UNINCORPORATED:
            gaps.append("Unincorporated district is the tax-roll LandZoning code. CITY ZONING placeholder labels are not used.")
        props["dataGaps"] = gaps

    assert_not_conflated(kept)
    muni_note = ", ".join(f"{key} {muni_counts[key]}" for key in sorted(muni_counts))
    notes.append(f"Municipality counts on the 5–150 acre roll: {muni_note}.")
    if lex:
        notes.append(f"Lexington city zoning matched {lex_hit} of {lex_hit + lex_miss} CityCode 07 parcels on PIN.")
    if thomasville:
        notes.append(f"Thomasville PTRC zoning covered {tv_hit} of {tv_hit + tv_miss} CityCode 28 parcels.")
    if wallburg_flu or wallburg_zoning:
        notes.append(f"Wallburg clip matched zoning on {wb_z} parcels and future land use on {wb_flu}.")
    eligible_n = sum(1 for feature in kept if (feature["properties"].get("oz2Eligibility") or {}).get("eligible"))
    designated_n = sum(
        1 for feature in kept if (feature["properties"].get("opportunityZone") or {}).get("inOpportunityZone")
    )
    notes.append(
        f"OZ 2.0 eligible parcels: {eligible_n}. Current designated QOZ parcels: {designated_n}. "
        "Those counts are allowed to differ; eligibility was not written into the designated field."
    )
    if outside:
        notes.append(f"Dropped {outside} parcels outside the Davidson County, North Carolina extent.")
    print(
        f"  municipalities {muni_counts} eligible {eligible_n} designated {designated_n}",
        flush=True,
    )
    return kept, notes, outside
