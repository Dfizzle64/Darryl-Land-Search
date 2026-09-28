#!/usr/bin/env python3
"""Public 5.0–150.0 acre parcels for 20 Tennessee counties.

Geometry and owner come from the Tennessee OIR layer
Tennessee Property Boundaries Public Use (edited 2026-09-10). Sale date,
sale price, and appraisal are joined from AGOL TN_County_Parcel_Map
(edited 2023-11-22) on GISLINK and labeled 2023. Acreage is polygon area
because DEEDAC is often 0.

Hickman is not on that statewide layer. It uses the May 2023 CaptureCAMA
snapshot. Chester uses the county CaptureCAMA Parcels_12 layer: a blank
tax-record id falls back to the map id, and rows with neither id are dropped.

Bedford County, Pennsylvania and paid parcel vendors are rejected.
Opportunity Zone status is not set.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from parcel_geometry import esri_rings_to_geojson, net_acres, representative_point

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path("/tmp/dls-tn-oir")
MIN_ACRES = 5.0
MAX_ACRES = 150.0
VINTAGE_2023 = "2023"

OIR_QUERY = (
    "https://services1.arcgis.com/YuVBSS7Y1of2Qud1/arcgis/rest/services/"
    "Tennessee_Property_Boundaries_Public_Use/FeatureServer/0/query"
)
TNCPM_ROOT = (
    "https://services.arcgis.com/rD2ylXRs80UroD90/arcgis/rest/services/"
    "TN_County_Parcel_Map/FeatureServer"
)
HICKMAN_QUERY = (
    "https://maps.capturecama.com/arcgis/rest/services/Hickman/"
    "HickmanTN05182023/MapServer/9/query"
)
CHESTER_QUERY = (
    "https://gis.capturecama.com/arcgis/rest/services/ChesterTN/"
    "ChesterCapture/MapServer/7/query"
)
TPAD_PREFIX = "https://assessment.cot.tn.gov/TPAD/Parcel/GIS?gislink="

OIR_FIELDS = [
    "GISLINK",
    "PARCELID",
    "OWNER",
    "OWNER2",
    "ADDRESS",
    "DEEDAC",
    "LINK_TPAD",
    "COUNTY_NAME",
    "COUNTY_ID",
    "PARCEL_TYPE",
]
HICKMAN_FIELDS = [
    "GISLINK",
    "PARCELID",
    "OWNER",
    "OWNER2",
    "PROPADDR",
    "MAILADDR",
    "CITY",
    "STATE",
    "ZIP",
    "CALC_ACRE",
    "APRVAL",
    "MAP",
    "PARCEL",
]
CHESTER_FIELDS = [
    "L15Parce_2",
    "L15Parce_4",
    "GPDATA__PA",
    "GPDATA__GI",
    "GPDATA__OW",
    "GPDATA___2",
    "GPDATA__PR",
    "GPDATA__MA",
    "GPDATA__CI",
    "GPDATA__ST",
    "GPDATA__ZI",
    "GPDATA__30",
    "GPDATA__AP",
    "GPDATA__27",
]

# Paid vendors and the wrong Bedford / Chester County, Pennsylvania layers.
REJECTED_URL_TOKENS = (
    "regrid",
    "chesco.org",
    "pasda.psu.edu",
    "april2023parcels",
    "bedfordcountypa",
    "imagery.pasda",
)

COUNTIES: list[dict[str, Any]] = [
    {"fips": "47111", "name": "Macon", "mode": "oir", "oir": "MACON", "tncpm": 37},
    {"fips": "47043", "name": "Dickson", "mode": "oir", "oir": "DICKSON", "tncpm": 64},
    {"fips": "47129", "name": "Morgan", "mode": "oir", "oir": "MORGAN", "tncpm": 26},
    {"fips": "47143", "name": "Rhea", "mode": "oir", "oir": "RHEA", "tncpm": 20},
    {"fips": "47145", "name": "Roane", "mode": "oir", "oir": "ROANE", "tncpm": 19},
    {"fips": "47147", "name": "Robertson", "mode": "oir", "oir": "ROBERTSON", "tncpm": 18},
    {"fips": "47153", "name": "Sequatchie", "mode": "oir", "oir": "SEQUATCHIE", "tncpm": 16},
    {"fips": "47189", "name": "Wilson", "mode": "oir", "oir": "WILSON", "tncpm": 0},
    {"fips": "47081", "name": "Hickman", "mode": "hickman"},
    {"fips": "47023", "name": "Chester", "mode": "chester"},
    {"fips": "47003", "name": "Bedford", "mode": "oir", "oir": "BEDFORD", "tncpm": 82},
    {"fips": "47015", "name": "Cannon", "mode": "oir", "oir": "CANNON", "tncpm": 76},
    {"fips": "47071", "name": "Hardin", "mode": "oir", "oir": "HARDIN", "tncpm": 52},
    {"fips": "47133", "name": "Overton", "mode": "oir", "oir": "OVERTON", "tncpm": None},
    {"fips": "47155", "name": "Sevier", "mode": "oir", "oir": "SEVIER", "tncpm": 15},
    {"fips": "47141", "name": "Putnam", "mode": "oir", "oir": "PUTNAM", "tncpm": 21},
    {"fips": "47183", "name": "Weakley", "mode": "oir", "oir": "WEAKLEY", "tncpm": 2},
    {"fips": "47001", "name": "Anderson", "mode": "oir", "oir": "ANDERSON", "tncpm": 83},
    {"fips": "47029", "name": "Cocke", "mode": "oir", "oir": "COCKE", "tncpm": 70},
    {"fips": "47013", "name": "Campbell", "mode": "oir", "oir": "CAMPBELL", "tncpm": 77},
]
BY_FIPS = {row["fips"]: row for row in COUNTIES}


def reject_source_url(url: str) -> None:
    """Refuse paid vendors and the Pennsylvania namesakes of Bedford and Chester."""
    lowered = (url or "").lower()
    for token in REJECTED_URL_TOKENS:
        if token in lowered:
            raise RuntimeError(
                f"Refusing {url}. That endpoint is a paid vendor or a Pennsylvania "
                "Bedford/Chester layer, not a Tennessee public parcel source."
            )


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


def in_band(acres: float | None) -> bool:
    return acres is not None and MIN_ACRES <= acres <= MAX_ACRES


def gis_keys(value: Any) -> list[str]:
    text = clean(value)
    if not text:
        return []
    collapsed = "".join(text.split())
    if collapsed == text:
        return [text]
    return [text, collapsed]


def chester_parcel_id(attrs: dict[str, Any]) -> tuple[str | None, str]:
    """Tax-record id, else map id. Neither means the row is dropped."""
    tax_id = clean(attrs.get("GPDATA__PA"))
    map_id = clean(attrs.get("L15Parce_2"))
    if tax_id:
        return tax_id, "tax-record"
    if map_id:
        return map_id, "map"
    return None, "neither"


def tpad_url(explicit: Any, gislink: Any) -> str | None:
    link = clean(explicit)
    if link and link.lower().startswith("http"):
        reject_source_url(link)
        return link
    key = clean(gislink)
    if not key:
        return None
    return TPAD_PREFIX + urllib.parse.quote(key, safe="")


def assert_tennessee(lon: float, lat: float, source_url: str) -> None:
    """Abort if a coordinate falls in the Pennsylvania namesake, not Tennessee."""
    if lat > 39.0 and lon > -80.5:
        raise RuntimeError(
            f"Coordinate {lon:.4f},{lat:.4f} is in Pennsylvania, not Tennessee ({source_url})."
        )


def get_json(url: str, timeout: int = 120) -> dict:
    reject_source_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "darryl-land-search/tn-oir-parcels"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("error"):
        raise RuntimeError(json.dumps(data["error"])[:400])
    return data


def post_json(url: str, params: dict[str, str], timeout: int = 180, retries: int = 6) -> dict:
    reject_source_url(url)
    body = urllib.parse.urlencode(params).encode()
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "User-Agent": "darryl-land-search/tn-oir-parcels",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("error"):
                raise RuntimeError(json.dumps(data["error"])[:400])
            return data
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.4 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url[:140]}: {last}")


def fetch_object_ids(url: str, where: str) -> list[int]:
    data = post_json(url, {"where": where, "returnIdsOnly": "true", "f": "json"}, timeout=240)
    return [int(i) for i in (data.get("objectIds") or [])]


def fetch_id_chunk(
    url: str,
    chunk: list[int],
    fields: list[str],
    *,
    geometry: bool,
) -> list[dict]:
    """One object-id page. A failed page is split so a timeout does not drop the county."""
    params = {
        "objectIds": ",".join(str(i) for i in chunk),
        "outFields": ",".join(fields),
        "returnGeometry": "true" if geometry else "false",
        "f": "json",
    }
    if geometry:
        params["outSR"] = "4326"
    try:
        data = post_json(url, params, timeout=180)
    except RuntimeError:
        if len(chunk) > 12:
            mid = len(chunk) // 2
            left = fetch_id_chunk(url, chunk[:mid], fields, geometry=geometry)
            right = fetch_id_chunk(url, chunk[mid:], fields, geometry=geometry)
            return left + right
        raise
    return data.get("features") or []


def iter_by_ids(
    url: str,
    ids: list[int],
    fields: list[str],
    *,
    geometry: bool,
    batch: int = 50,
):
    """Yield one page at a time so a county's raw polygons are not all held at once."""
    total = len(ids)
    for start in range(0, total, batch):
        chunk = ids[start : start + batch]
        got = fetch_id_chunk(url, chunk, fields, geometry=geometry)
        done = min(start + len(chunk), total)
        if done == len(chunk) or done == total or done % 400 < batch:
            print(f"    {done}/{total}", flush=True)
        time.sleep(0.02)
        yield got


def fetch_by_ids(
    url: str,
    ids: list[int],
    fields: list[str],
    *,
    geometry: bool,
    batch: int = 50,
) -> list[dict]:
    features: list[dict] = []
    for got in iter_by_ids(url, ids, fields, geometry=geometry, batch=batch):
        features.extend(got)
    return features


def rings_of(feature: dict) -> list | None:
    geometry = feature.get("geometry") or {}
    rings = geometry.get("rings")
    if not rings:
        return None
    return rings


def tn_oir_spec(fips: str) -> dict:
    row = BY_FIPS[fips]
    mode = row["mode"]
    if mode == "hickman":
        return {
            "kind": "tn-oir",
            "url": HICKMAN_QUERY,
            "source": "tn-hickman-capturecama-202305",
            "coverage": "complete-gte-5ac",
            "gaps": hickman_gaps(),
        }
    if mode == "chester":
        return {
            "kind": "tn-oir",
            "url": CHESTER_QUERY,
            "source": "tn-chester-capturecama-parcels12",
            "coverage": "complete-gte-5ac",
            "gaps": chester_gaps(),
        }
    gaps = oir_gaps(row)
    return {
        "kind": "tn-oir",
        "url": OIR_QUERY,
        "source": f"tn-oir-public-use-{fips}",
        "coverage": "complete-gte-5ac",
        "gaps": gaps,
    }


def oir_gaps(row: dict) -> list[str]:
    notes = [
        "Geometry and owner are Tennessee OIR Tennessee Property Boundaries Public Use, edited 2026-09-10, PARCEL_TYPE=1. Acreage is computed from the polygon because DEEDAC is often 0. The filter is 5.0–150.0 acres inclusive. Vertices are not simplified.",
        "Sale date, sale price, and appraisal are joined from AGOL TN_County_Parcel_Map (edited 2023-11-22) on GISLINK where that county layer exists. The popup labels those fields as 2023 vintage. Assessed value, taxable value, and tax amount are not on that join. Zoning and future land use are not on these layers.",
        "The property-record link is LINK_TPAD when the OIR row publishes it, otherwise the TPAD GIS card for the same GISLINK. Opportunity Zone status was not inferred.",
        "Regrid and other paid parcel vendors were not used.",
    ]
    if row["fips"] == "47111":
        notes.insert(
            0,
            "Macon was a shelf gap because the generic Tennessee loader queried IMPACT COUNTY_ID=111, the FIPS suffix. The Comptroller county number is 56. TN_County_Parcel_Map Macon_Parcels is live and has 4,921 parcels with Parcels_CALC_ACRE from 5 through 150. This extract replaces that app-load gap.",
        )
    if row["fips"] == "47003":
        notes.insert(
            0,
            "Bedford is Bedford County, Tennessee (FIPS 47003). April2023Parcels and the Bedford County, Pennsylvania viewer were not used. Centroids outside Tennessee abort the load.",
        )
    if row["tncpm"] is None:
        notes.insert(
            1,
            "Overton is not a layer on TN_County_Parcel_Map, so sale date, sale price, and appraisal stay empty. That is not a 2023 value.",
        )
    return notes


def hickman_gaps() -> list[str]:
    return [
        "Hickman is not in the OIR statewide layer or TN_County_Parcel_Map. The only public polygon source used here is the CaptureCAMA snapshot HickmanTN05182023 (May 18, 2023).",
        "Acreage is CALC_ACRE from 5.0 through 150.0 inclusive. Owner, situs, mailing, and APRVAL come from that snapshot. APRVAL is labeled 2023 vintage. The snapshot has no sale date or sale price.",
        "The property-record link is the TPAD GIS card for GISLINK when that id is present. Opportunity Zone status was not inferred. Regrid was not used.",
    ]


def chester_gaps() -> list[str]:
    return [
        "Chester is not in the OIR statewide layer. Geometry and CAMA attributes are the public Chester County, Tennessee CaptureCAMA Parcels_12 layer (ChesterTN/ChesterCapture). Chester County, Pennsylvania (chesco.org and PASDA) was not used.",
        "Acreage is L15Parce_4, the layer's calculated acres, from 5.0 through 150.0 inclusive. 3.9% of that band have a blank tax-record id (GPDATA__PA). Those rows use the map id (L15Parce_2). Rows with neither id are dropped (79 in the band).",
        "Appraisal is GPDATA__30 and is labeled with the row's appraisal year when that year is published. The layer has no sale date or sale price. The TPAD link uses the map id. Opportunity Zone status was not inferred. Regrid was not used.",
    ]


def base_feature(
    *,
    county: dict,
    markets: list[str],
    parcel_id: str,
    acreage: float,
    geometry: dict,
    center: tuple[float, float],
    source: str,
    owner: str | None,
    situs: str | None,
    city: str | None = None,
    zip_code: str | None = None,
    mail1: str | None = None,
    mail_city: str | None = None,
    mail_state: str | None = None,
    mail_zip: str | None = None,
) -> dict:
    from seed_market_parcels import empty_feature, zip_str

    feature = empty_feature(
        fips=county["fips"],
        county=county["name"],
        state=county["state"],
        markets=markets,
        parcel_id=parcel_id,
        acreage=acreage,
        geometry=geometry,
        center=center,
        source=source,
        owner=owner,
        situs=situs,
        city=city,
        zip_code=zip_str(zip_code) if zip_code else None,
        mail1=mail1,
        mail_city=mail_city,
        mail_state=mail_state,
        mail_zip=zip_str(mail_zip) if mail_zip else None,
    )
    feature["properties"]["opportunityZone"] = None
    feature["properties"]["oz2Eligibility"] = None
    return feature


def remember(by_id: dict[str, dict], feature: dict) -> None:
    parcel_id = feature["properties"]["parcelId"]
    previous = by_id.get(parcel_id)
    if previous is None or (feature["properties"]["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
        by_id[parcel_id] = feature


def geometry_acres(feature: dict, source_url: str) -> tuple[dict | None, float, tuple[float, float] | None]:
    rings = rings_of(feature)
    if not rings:
        return None, 0.0, None
    geometry = esri_rings_to_geojson(rings, simplify=False)
    if not geometry:
        return None, 0.0, None
    acres = net_acres(rings)
    center = representative_point(geometry)
    if not center:
        return None, acres, None
    assert_tennessee(center[0], center[1], source_url)
    if not (-90.5 < center[0] < -81.4 and 34.8 < center[1] < 36.8):
        return None, acres, None
    return geometry, acres, center


def load_oir(row: dict, county: dict, markets: list[str], source: str) -> tuple[list[dict], dict]:
    where = f"COUNTY_NAME='{row['oir']}' AND PARCEL_TYPE=1"
    print(f"  OIR ids {where}", flush=True)
    ids = fetch_object_ids(OIR_QUERY, where)
    print(f"  OIR object ids {len(ids)}", flush=True)
    by_id: dict[str, dict] = {}
    dropped_geom = 0
    dropped_band = 0
    dropped_id = 0
    deed_in_band = 0
    fetched = 0
    considered = 0
    for page in iter_by_ids(OIR_QUERY, ids, OIR_FIELDS, geometry=True, batch=40):
        fetched += len(page)
        for item in page:
            considered += 1
            attrs = item.get("attributes") or {}
            county_name = clean(attrs.get("COUNTY_NAME"))
            if county_name and county_name.upper() != row["oir"]:
                raise RuntimeError(f"{row['fips']} received COUNTY_NAME {attrs.get('COUNTY_NAME')}")
            geometry, acres, center = geometry_acres(item, OIR_QUERY)
            if num(attrs.get("DEEDAC")) is not None and in_band(num(attrs.get("DEEDAC"))):
                deed_in_band += 1
            if not geometry or not center:
                dropped_geom += 1
                continue
            if not in_band(acres):
                dropped_band += 1
                continue
            parcel_id = clean(attrs.get("GISLINK")) or clean(attrs.get("PARCELID"))
            if not parcel_id:
                dropped_id += 1
                continue
            feature = base_feature(
                county=county,
                markets=markets,
                parcel_id=parcel_id,
                acreage=acres,
                geometry=geometry,
                center=center,
                source=source,
                owner=clean(attrs.get("OWNER")),
                situs=clean(attrs.get("ADDRESS")),
            )
            feature["properties"]["ownerName2"] = clean(attrs.get("OWNER2"))
            feature["properties"]["appraiserUrl"] = tpad_url(attrs.get("LINK_TPAD"), attrs.get("GISLINK"))
            feature["properties"]["_gislink"] = clean(attrs.get("GISLINK"))
            remember(by_id, feature)
    if fetched != len(ids):
        raise RuntimeError(f"{row['fips']} fetched {fetched} OIR features of {len(ids)} ids")
    stats = {
        "sourceRows": len(ids),
        "deedAcresInBand": deed_in_band,
        "droppedGeometry": dropped_geom,
        "droppedOutsideBand": dropped_band,
        "droppedNoId": dropped_id,
        "duplicateIdsCollapsed": considered - dropped_geom - dropped_band - dropped_id - len(by_id),
    }
    return list(by_id.values()), stats


def tncpm_field_map(layer_id: int) -> dict[str, str]:
    meta = get_json(f"{TNCPM_ROOT}/{layer_id}?f=json")
    # Layer metadata is a GET-style document; post_json still works for f=json.
    names = [field["name"] for field in meta.get("fields") or []]
    if not names:
        raise RuntimeError(f"TN_County_Parcel_Map layer {layer_id} returned no fields")

    def pick(suffix: str) -> str | None:
        hits = [name for name in names if name.upper().endswith(suffix) and "ASSESSMENT_DATA" in name.upper()]
        return hits[0] if hits else None

    gis = next((name for name in names if name.upper() == "PARCELS_GISLINK"), None)
    if not gis:
        raise RuntimeError(f"TN_County_Parcel_Map layer {layer_id} has no Parcels_GISLINK")
    return {
        "gis": gis,
        "price": pick("_PRICE") or "",
        "date": pick("_SALEDATE") or "",
        "value": pick("_APPRAISAL") or "",
    }


def load_tncpm(layer_id: int) -> tuple[dict[str, dict], dict[str, str]]:
    fields_map = tncpm_field_map(layer_id)
    fields = [name for name in (fields_map["gis"], fields_map["price"], fields_map["date"], fields_map["value"]) if name]
    url = f"{TNCPM_ROOT}/{layer_id}/query"
    ids = fetch_object_ids(url, "1=1")
    print(f"  TNCPM layer {layer_id} rows {len(ids)}", flush=True)
    raw = fetch_by_ids(url, ids, fields, geometry=False, batch=300)
    index: dict[str, dict] = {}
    for item in raw:
        attrs = item.get("attributes") or {}
        row = {
            "price": num(attrs.get(fields_map["price"])) if fields_map["price"] else None,
            "date": attrs.get(fields_map["date"]) if fields_map["date"] else None,
            "value": num(attrs.get(fields_map["value"])) if fields_map["value"] else None,
        }
        for key in gis_keys(attrs.get(fields_map["gis"])):
            current = index.get(key)
            if current is None or (row["price"] or 0) > (current["price"] or 0):
                index[key] = row
    return index, fields_map


def apply_2023_join(features: list[dict], layer_id: int | None) -> dict:
    from seed_market_parcels import epoch_to_iso

    matched = 0
    sales = 0
    values = 0
    if layer_id is None:
        for feature in features:
            feature["properties"].pop("_gislink", None)
        return {"tncpmLayer": None, "tncpmMatched": 0, "saleCount": 0, "appraisalCount": 0}
    index, _fields = load_tncpm(layer_id)
    for feature in features:
        props = feature["properties"]
        gislink = props.pop("_gislink", None)
        row = None
        for key in gis_keys(gislink):
            row = index.get(key)
            if row:
                break
        if not row:
            continue
        matched += 1
        price = row["price"] if row["price"] is not None and row["price"] > 0 else None
        sold = epoch_to_iso(row["date"])
        appraisal = row["value"] if row["value"] is not None and row["value"] > 0 else None
        if price is not None or sold is not None:
            props["lastSale"] = {"date": sold, "price": price, "qualified": None, "vintage": VINTAGE_2023}
            sales += 1
        if appraisal is not None:
            props["tax"]["marketValue"] = appraisal
            props["tax"]["vintage"] = VINTAGE_2023
            values += 1
    return {"tncpmLayer": layer_id, "tncpmMatched": matched, "saleCount": sales, "appraisalCount": values}


def load_hickman(county: dict, markets: list[str], source: str) -> tuple[list[dict], dict]:
    where = "CALC_ACRE>=5 AND CALC_ACRE<=150"
    ids = fetch_object_ids(HICKMAN_QUERY, where)
    print(f"  Hickman ids {len(ids)}", flush=True)
    by_id: dict[str, dict] = {}
    dropped = 0
    fetched = 0
    for page in iter_by_ids(HICKMAN_QUERY, ids, HICKMAN_FIELDS, geometry=True, batch=40):
        fetched += len(page)
        for item in page:
            attrs = item.get("attributes") or {}
            acres = num(attrs.get("CALC_ACRE"))
            geometry, _computed, center = geometry_acres(item, HICKMAN_QUERY)
            if not geometry or not center or not in_band(acres):
                dropped += 1
                continue
            parcel_id = clean(attrs.get("GISLINK")) or clean(attrs.get("PARCELID"))
            if not parcel_id:
                dropped += 1
                continue
            feature = base_feature(
                county=county,
                markets=markets,
                parcel_id=parcel_id,
                acreage=acres,
                geometry=geometry,
                center=center,
                source=source,
                owner=clean(attrs.get("OWNER")),
                situs=clean(attrs.get("PROPADDR")),
                city=clean(attrs.get("CITY")),
                zip_code=clean(attrs.get("ZIP")),
                mail1=clean(attrs.get("MAILADDR")),
                mail_city=clean(attrs.get("CITY")),
                mail_state=clean(attrs.get("STATE")),
                mail_zip=clean(attrs.get("ZIP")),
            )
            feature["properties"]["ownerName2"] = clean(attrs.get("OWNER2"))
            feature["properties"]["appraiserUrl"] = tpad_url(None, attrs.get("GISLINK"))
            appraisal = num(attrs.get("APRVAL"))
            if appraisal is not None and appraisal > 0:
                feature["properties"]["tax"]["marketValue"] = appraisal
                feature["properties"]["tax"]["vintage"] = VINTAGE_2023
            remember(by_id, feature)
    if fetched != len(ids):
        raise RuntimeError(f"Hickman fetched {fetched} of {len(ids)}")
    return list(by_id.values()), {"sourceRows": len(ids), "dropped": dropped, "kept": len(by_id)}


def load_chester(county: dict, markets: list[str], source: str) -> tuple[list[dict], dict]:
    where = "L15Parce_4>=5 AND L15Parce_4<=150"
    ids = fetch_object_ids(CHESTER_QUERY, where)
    print(f"  Chester ids {len(ids)}", flush=True)
    by_id: dict[str, dict] = {}
    dropped_neither = 0
    used_map = 0
    used_tax = 0
    outside = 0
    fetched = 0
    for page in iter_by_ids(CHESTER_QUERY, ids, CHESTER_FIELDS, geometry=True, batch=40):
        fetched += len(page)
        for item in page:
            attrs = item.get("attributes") or {}
            acres = num(attrs.get("L15Parce_4"))
            parcel_id, kind = chester_parcel_id(attrs)
            if kind == "neither" or not parcel_id:
                dropped_neither += 1
                continue
            geometry, _computed, center = geometry_acres(item, CHESTER_QUERY)
            if not geometry or not center or not in_band(acres):
                outside += 1
                continue
            feature = base_feature(
                county=county,
                markets=markets,
                parcel_id=parcel_id,
                acreage=acres,
                geometry=geometry,
                center=center,
                source=source,
                owner=clean(attrs.get("GPDATA__OW")),
                situs=clean(attrs.get("GPDATA__PR")),
                city=clean(attrs.get("GPDATA__CI")),
                zip_code=clean(attrs.get("GPDATA__ZI")),
                mail1=clean(attrs.get("GPDATA__MA")),
                mail_city=clean(attrs.get("GPDATA__CI")),
                mail_state=clean(attrs.get("GPDATA__ST")),
                mail_zip=clean(attrs.get("GPDATA__ZI")),
            )
            feature["properties"]["ownerName2"] = clean(attrs.get("GPDATA___2"))
            feature["properties"]["appraiserUrl"] = tpad_url(None, attrs.get("L15Parce_2") or attrs.get("GPDATA__GI"))
            appraisal = num(attrs.get("GPDATA__30"))
            year = clean(attrs.get("GPDATA__AP"))
            if appraisal is not None and appraisal > 0:
                feature["properties"]["tax"]["marketValue"] = appraisal
                if year and len(year) == 4 and year.isdigit():
                    feature["properties"]["tax"]["vintage"] = year
            if kind == "map":
                used_map += 1
            else:
                used_tax += 1
            remember(by_id, feature)
    if fetched != len(ids):
        raise RuntimeError(f"Chester fetched {fetched} of {len(ids)}")
    return list(by_id.values()), {
        "sourceRows": len(ids),
        "droppedNeitherId": dropped_neither,
        "droppedGeometryOrBand": outside,
        "usedTaxRecordId": used_tax,
        "usedMapId": used_map,
        "kept": len(by_id),
    }


def finalize_features(features: list[dict]) -> list[dict]:
    for feature in features:
        props = feature["properties"]
        if props.get("opportunityZone") not in (None,):
            raise RuntimeError("Opportunity Zone status must stay unset")
        acres = props.get("acreage")
        if not in_band(acres):
            raise RuntimeError(f"Parcel {props.get('parcelId')} is outside 5–150 acres ({acres})")
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise RuntimeError("Parcel geometry is not a polygon")
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features


def download_tn_oir(county: dict, markets: list[str], spec: dict) -> dict:
    from seed_market_parcels import county_row, write_tiles

    fips = county["fips"]
    row = BY_FIPS[fips]
    source = spec["source"]
    cache_path = CACHE_DIR / f"{fips}.json"
    print(f"Pulling {county['name']} County, Tennessee ({fips}) via {source}", flush=True)
    if cache_path.exists() and not spec.get("ignoreCache"):
        cached = json.loads(cache_path.read_text())
        features = cached["features"]
        stats = cached.get("stats") or {}
        for feature in features:
            feature["properties"]["marketIds"] = markets
        print(f"  cache hit {len(features)}", flush=True)
    else:
        if row["mode"] == "oir":
            features, stats = load_oir(row, county, markets, source)
            stats.update(apply_2023_join(features, row.get("tncpm")))
        elif row["mode"] == "hickman":
            features, stats = load_hickman(county, markets, source)
        else:
            features, stats = load_chester(county, markets, source)
        features = finalize_features(features)
        if len(features) < 500:
            raise RuntimeError(f"{fips} kept only {len(features)} parcels; refusing to replace the shelf")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"stats": stats, "features": features}, separators=(",", ":")))
        print(f"  kept {len(features)}", flush=True)
    features = finalize_features(features)
    path, lookup, tiles = write_tiles(county, features)
    tpad = sum(1 for feature in features if feature["properties"].get("appraiserUrl"))
    owners = sum(1 for feature in features if feature["properties"].get("ownerName"))
    return county_row(
        county,
        markets,
        feature_count=len(features),
        coverage="complete-gte-5ac",
        partition="tiles",
        path=path,
        lookup=lookup,
        source=source,
        query_url=spec["url"],
        gaps=list(spec.get("gaps") or []),
        source_count=stats.get("sourceRows"),
        dropped=(stats.get("droppedNeitherId") or 0) + (stats.get("dropped") or 0),
        tile_count=tiles,
        extra={
            "ingest": {
                **stats,
                "kept": len(features),
                "ownerCount": owners,
                "tpadCount": tpad,
                "opportunityZoneDesignated": 0,
                "simplified": False,
                "acreageBand": [MIN_ACRES, MAX_ACRES],
            }
        },
    )


def catalog_markets(fips: str) -> list[str]:
    catalog = json.loads((ROOT / "data" / "market-parcel-counties.json").read_text())
    found: list[str] = []
    for market in catalog["markets"]:
        for county in market["counties"]:
            if county["fips"] == fips and market["id"] not in found:
                found.append(market["id"])
    if not found:
        raise RuntimeError(f"{fips} is not in data/market-parcel-counties.json")
    return found


def main() -> None:
    from seed_market_parcels import rebuild_indexes

    parser = argparse.ArgumentParser()
    parser.add_argument("--county", action="append", default=[])
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    selected = {name.lower() for name in args.county}
    catalog = json.loads((ROOT / "data" / "market-parcel-counties.json").read_text())
    jobs = []
    for row in COUNTIES:
        if selected and row["name"].lower() not in selected and row["fips"] not in selected:
            continue
        county = {"name": row["name"], "state": "Tennessee", "fips": row["fips"]}
        markets = catalog_markets(row["fips"])
        spec = tn_oir_spec(row["fips"])
        if args.refresh:
            spec = dict(spec)
            spec["ignoreCache"] = True
        existing_path = ROOT / "data" / "fixtures" / "market-parcels" / "counties" / row["fips"] / "county.json"
        before = 0
        before_coverage = "absent"
        if existing_path.exists():
            existing = json.loads(existing_path.read_text())
            before = int(existing.get("featureCount") or 0)
            before_coverage = existing.get("coverage") or "absent"
        jobs.append((row, county, markets, spec, before, before_coverage))

    summary: list[dict] = []

    def run_one(job: tuple) -> dict:
        row, county, markets, spec, before, before_coverage = job
        try:
            written = download_tn_oir(county, markets, spec)
            return {
                "fips": row["fips"],
                "name": row["name"],
                "before": before,
                "beforeCoverage": before_coverage,
                "after": written["featureCount"],
                "source": written["source"],
                "status": "new" if before <= 0 else "upgraded",
            }
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED {row['name']} {row['fips']}: {exc}", flush=True)
            return {
                "fips": row["fips"],
                "name": row["name"],
                "before": before,
                "beforeCoverage": before_coverage,
                "after": before,
                "status": "failed",
                "reason": str(exc),
            }

    workers = max(1, min(args.workers, len(jobs) or 1))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_one, job) for job in jobs]
        for future in as_completed(futures):
            summary.append(future.result())
    summary.sort(key=lambda item: item["fips"])
    rebuild_indexes(catalog)
    report_path = CACHE_DIR / "summary.json"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
