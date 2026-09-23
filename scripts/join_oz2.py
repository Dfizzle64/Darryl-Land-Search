#!/usr/bin/env python3
"""Join OZ 2.0 nomination eligibility onto the Orange County parcel fixture.

Official flags only — this script does not classify rural vs non-rural itself.

  - Rev. Proc. 2026-14 appendix (IRS xlsx): 2020 census tracts eligible for
    nomination as 2027 QOZs, with the Treasury/IRS Rural Status column.
    Eligible tracts are not designated. Florida has not nominated them, and
    Treasury has not certified a 2027 QOZ list.
  - Notice 2025-50 appendix (IRS PDF): 2018 designated QOZs comprised entirely
    of a rural area. Membership in that list is the only rural flag applied to
    current designated zones.
  - Census TIGER 2020 tract polygons: geometry for the eligible GEOIDs.
    Attribute flags never come from TIGER.

A few public OCPA parcels inside the rural-eligible tract are appended when
the sample has none, so the filter and parcel drawer can show GEOID
12095016605. That is not a county-wide extract.

Usage:
  python3 -m pip install pypdf   # PDF text for Notice 2025-50
  python3 scripts/join_oz2.py
"""

from __future__ import annotations

import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from join_flu import OC_FLU_URL, ORL_FLU_URL, oc_flu, orl_flu, point_query
from seed_fixtures import (
    OCPA_FIELDS,
    OCPA_URL,
    arcgis_query,
    centroid,
    clean_str,
    epoch_to_iso,
    nearest_aadt,
    parse_zoning,
    point_in_feature,
    rings_to_geojson,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"
PARCELS = FIXTURES / "parcels.geojson"
META = FIXTURES / "meta.json"
OZ_POLYS = FIXTURES / "opportunity-zones.geojson"
OZ2_POLYS = FIXTURES / "oz2-eligible.geojson"
OZ2_LOOKUP = FIXTURES / "oz2-lookup.json"
OZ2_TABLE = FIXTURES / "oz2-eligible-tracts.json"
NOTICE_GEOIDS = FIXTURES / "notice-2025-50-rural-geoids.json"
FLU_LOOKUP = FIXTURES / "flu-lookup.json"
INCOME_TRACTS = FIXTURES / "income-tracts.geojson"
INCOME_BLOCK_GROUPS = FIXTURES / "income-block-groups.geojson"
TRAFFIC = FIXTURES / "traffic.geojson"

RP_APPENDIX_URL = "https://www.irs.gov/pub/irs-drop/rp-26-14-appendix.xlsx"
NOTICE_2025_50_URL = "https://www.irs.gov/pub/irs-drop/n-25-50.pdf"
TIGER_TRACTS_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Census2020/MapServer/6/query"
)

# Handoff check against the appendix. The rural boolean still comes from the
# Rural Status column; this only fails the seed if Treasury's file no longer
# lists the tract the product is supposed to show.
EXPECTED_RURAL_GEOID = "12095016605"
COORD_PRECISION = 5
SAMPLE_CAP = 3
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def fetch_bytes(url: str, timeout: int = 120, retries: int = 3) -> bytes:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "orange-county-mf-pilot/0.4"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def fetch_json(url: str, params: dict | None = None, timeout: int = 90, retries: int = 3) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    return json.loads(fetch_bytes(url, timeout=timeout, retries=retries).decode("utf-8"))


def round_coords(value, precision: int = COORD_PRECISION):
    if isinstance(value, (int, float)):
        return round(float(value), precision)
    if isinstance(value, list):
        return [round_coords(item, precision) for item in value]
    return value


def load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for si in root.findall("m:si", NS):
        texts = [node.text or "" for node in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")]
        strings.append("".join(texts))
    return strings


def cell_text(cell: ET.Element, strings: list[str]) -> str:
    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return ""
    if cell.get("t") == "s":
        return strings[int(value.text)]
    return value.text


def geoid_from_excel(raw: str) -> str:
    digits = "".join(ch for ch in raw.strip() if ch.isdigit())
    # Excel stores GEOIDs as numbers, so state FIPS 01–09 lose their leading zero.
    if len(digits) == 10:
        digits = digits.zfill(11)
    return digits


def rural_from_status(status: str) -> bool:
    token = status.strip().lower()
    if token == "rural":
        return True
    if token == "non-rural":
        return False
    raise RuntimeError(f"Unexpected Rev. Proc. 2026-14 Rural Status {status!r}; refusing to infer one")


def load_orange_eligible() -> dict[str, dict]:
    payload = fetch_bytes(RP_APPENDIX_URL)
    archive = zipfile.ZipFile(io.BytesIO(payload))
    strings = load_shared_strings(archive)
    sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows = sheet.findall("m:sheetData/m:row", NS)
    header = [cell_text(cell, strings).strip() for cell in rows[0].findall("m:c", NS)]
    expected = ["State", "County", "Census Tract Number", "Rural Status"]
    if header[:4] != expected:
        raise RuntimeError(f"Rev. Proc. 2026-14 appendix columns changed: {header[:4]}")

    orange: dict[str, dict] = {}
    for row in rows[1:]:
        vals = ["", "", "", ""]
        for cell in row.findall("m:c", NS):
            ref = cell.get("r") or "A"
            idx = ord(ref[0]) - ord("A")
            if 0 <= idx < 4:
                vals[idx] = cell_text(cell, strings).strip()
        state, county, tract_raw, status = vals
        if state != "Florida" or county != "Orange County":
            continue
        geoid = geoid_from_excel(tract_raw)
        if len(geoid) != 11 or not geoid.startswith("12095"):
            raise RuntimeError(f"Orange County tract number {tract_raw!r} did not become a 12095 GEOID")
        orange[geoid] = {
            "tractGeoid": geoid,
            "rural": rural_from_status(status),
            "ruralStatus": "Rural" if rural_from_status(status) else "Non-rural",
            "state": state,
            "county": county,
        }
    if not orange:
        raise RuntimeError("Rev. Proc. 2026-14 appendix returned no Orange County, Florida tracts")
    if EXPECTED_RURAL_GEOID not in orange:
        raise RuntimeError(f"Appendix is missing expected Orange County GEOID {EXPECTED_RURAL_GEOID}")
    if orange[EXPECTED_RURAL_GEOID]["rural"] is not True:
        raise RuntimeError(f"{EXPECTED_RURAL_GEOID} is not Rural in the Rev. Proc. 2026-14 appendix")
    rural_ids = [geoid for geoid, row in orange.items() if row["rural"]]
    print(f"Rev. Proc. 2026-14 Orange County eligible tracts: {len(orange)}; rural: {rural_ids}")
    return orange


def fetch_tiger_tracts(geoids: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for start in range(0, len(geoids), 25):
        batch = geoids[start : start + 25]
        quoted = ",".join(f"'{geoid}'" for geoid in batch)
        data = fetch_json(
            TIGER_TRACTS_URL,
            {
                "where": f"GEOID IN ({quoted})",
                "outFields": "GEOID,NAME,TRACT,STATE,COUNTY",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
            },
        )
        if data.get("error"):
            raise RuntimeError(data["error"])
        for feature in data.get("features") or []:
            props = feature.get("properties") or {}
            geoid = str(props.get("GEOID") or "")
            geometry = feature.get("geometry")
            if geoid and geometry:
                found[geoid] = {
                    "type": "Feature",
                    "id": geoid,
                    "properties": {
                        "id": geoid,
                        "tractGeoid": geoid,
                        "tract": str(props.get("TRACT") or "") or None,
                        "name": props.get("NAME") or geoid,
                        "state": props.get("STATE"),
                        "county": props.get("COUNTY"),
                    },
                    "geometry": {
                        "type": geometry.get("type"),
                        "coordinates": round_coords(geometry.get("coordinates") or []),
                    },
                }
        time.sleep(0.15)
    missing = [geoid for geoid in geoids if geoid not in found]
    if missing:
        raise RuntimeError(f"Census TIGER 2020 is missing {len(missing)} eligible tracts, including {missing[:5]}")
    print(f"TIGER 2020 tracts: {len(found)}")
    return found


def load_notice_rural_geoids() -> set[str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Notice 2025-50 parsing needs pypdf. Install it with: python3 -m pip install pypdf") from exc
    payload = fetch_bytes(NOTICE_2025_50_URL)
    reader = PdfReader(io.BytesIO(payload))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    geoids = set(re.findall(r"\b\d{11}\b", text))
    if not (3200 <= len(geoids) <= 3400):
        raise RuntimeError(
            f"Notice 2025-50 parse found {len(geoids)} 11-digit GEOIDs; expected about 3,309. Refusing to guess rural flags."
        )
    orange = sorted(geoid for geoid in geoids if geoid.startswith("12095"))
    print(f"Notice 2025-50 rural designated GEOIDs: {len(geoids)}; Orange County FL: {orange or 'none'}")
    return geoids


def income_at(collection: dict, lon: float, lat: float) -> dict | None:
    for feature in collection.get("features") or []:
        if point_in_feature(lon, lat, feature):
            props = feature.get("properties") or {}
            return {
                "geoid": props.get("geoid"),
                "name": props.get("name"),
                "medianHouseholdIncome": props.get("medianHouseholdIncome"),
                "medianHouseholdIncomeMoe": props.get("medianHouseholdIncomeMoe"),
            }
    return None


def income_by_geoid(collection: dict, geoid: str) -> dict | None:
    for feature in collection.get("features") or []:
        props = feature.get("properties") or {}
        if props.get("geoid") == geoid:
            return {
                "geoid": geoid,
                "name": props.get("name"),
                "medianHouseholdIncome": props.get("medianHouseholdIncome"),
                "medianHouseholdIncomeMoe": props.get("medianHouseholdIncomeMoe"),
            }
    return None


def traffic_roads(collection: dict) -> list[tuple[dict, list]]:
    roads = []
    for feature in collection.get("features") or []:
        props = feature.get("properties") or {}
        line = (feature.get("geometry") or {}).get("coordinates") or []
        if len(line) < 2:
            continue
        roads.append(
            (
                {
                    "AADT": props.get("aadt"),
                    "YEAR_": props.get("year"),
                    "ROADWAY": props.get("roadwayId"),
                    "DESC_FRM": props.get("from"),
                    "DESC_TO": props.get("to"),
                },
                line,
            )
        )
    return roads


def flu_for_parcel(prefix: str | None, lon: float, lat: float) -> dict | None:
    try:
        if (prefix or "").upper() == "ORL":
            hits = point_query(ORL_FLU_URL, lon, lat, "LANDUSETYPE")
            if hits:
                found = orl_flu((hits[0] or {}).get("attributes") or {})
                if found:
                    return found
        hits = point_query(OC_FLU_URL, lon, lat, "LAND_USE,LABEL")
        if hits:
            found = oc_flu((hits[0] or {}).get("attributes") or {})
            if found and found.get("code") not in {None, "City"}:
                return found
    except Exception as exc:  # noqa: BLE001
        print(f"FLU join skipped at {lon},{lat}: {exc}")
    return None


def designated_hit(lon: float, lat: float, zones: list[dict]) -> dict | None:
    for zone in zones:
        if point_in_feature(lon, lat, zone):
            return zone.get("properties") or {}
    return None


def parcel_feature_from_ocpa(
    raw: dict,
    income_tracts: dict,
    income_block_groups: dict,
    roads: list,
    designated_zones: list[dict],
    rural_geoid: str,
) -> dict | None:
    attrs = raw.get("attributes") or {}
    geometry = rings_to_geojson(raw.get("geometry"))
    pid = clean_str(attrs.get("PARCEL"))
    if not geometry or not pid:
        return None
    lon, lat = centroid(geometry)
    zoning = parse_zoning(clean_str(attrs.get("ZONING_CODE")))
    tract_income = income_at(income_tracts, lon, lat) or income_by_geoid(income_tracts, rural_geoid)
    block_income = income_at(income_block_groups, lon, lat)
    hit = designated_hit(lon, lat, designated_zones)
    if hit:
        opportunity = {
            "inOpportunityZone": True,
            "tractGeoid": hit.get("tractGeoid"),
            "tractName": hit.get("name"),
            "source": "hud-fs-13",
            "designatedRural": None,
        }
    else:
        opportunity = {
            "inOpportunityZone": False,
            "tractGeoid": None,
            "tractName": None,
            "source": "hud-fs-13",
            "designatedRural": None,
        }
    return {
        "type": "Feature",
        "id": pid,
        "geometry": geometry,
        "properties": {
            "id": pid,
            "parcelId": pid,
            "situsAddress": clean_str(attrs.get("SITUS")),
            "situsCity": clean_str(attrs.get("CITY_SITUS")),
            "situsZip": clean_str(attrs.get("ZIP_SITUS")),
            "jurisdictionCode": clean_str(attrs.get("CITY_CODE")),
            "ownerName": clean_str(attrs.get("NAME1")),
            "ownerName2": clean_str(attrs.get("NAME2")),
            "propertyName": clean_str(attrs.get("PROP_NAME")),
            **zoning,
            "dorCode": clean_str(attrs.get("DOR_CODE")),
            "acreage": attrs.get("ACREAGE"),
            "centroid": [round(lon, 6), round(lat, 6)],
            "lastSale": {
                "date": epoch_to_iso(attrs.get("SALE_DATE")),
                "price": attrs.get("SALE_ADJ_VALUE") if epoch_to_iso(attrs.get("SALE_DATE")) else None,
                "qualified": clean_str(attrs.get("QUAL_CODE")),
            },
            "tax": {
                "marketValue": attrs.get("TOTAL_MKT"),
                "assessedValue": attrs.get("TOTAL_ASSD"),
                "taxableValue": attrs.get("TAXABLE"),
                "taxes": attrs.get("TAXES"),
            },
            "mailingAddress": {
                "line1": clean_str(attrs.get("ADD1")),
                "line2": clean_str(attrs.get("ADD2")),
                "city": clean_str(attrs.get("CITY")),
                "state": clean_str(attrs.get("STATE")),
                "zip": clean_str(attrs.get("ZIP")),
            },
            "incomeTract": tract_income,
            "incomeBlockGroup": block_income,
            "nearestRoad": nearest_aadt(lon, lat, roads) if roads else None,
            "flu": flu_for_parcel(zoning.get("jurisdictionPrefix"), lon, lat),
            "opportunityZone": opportunity,
            "source": "ocpa-webmap-parcels-fixture",
        },
    }


def centroids_in_feature(features: list[dict], zone: dict) -> int:
    count = 0
    for feature in features:
        centroid_xy = (feature.get("properties") or {}).get("centroid") or []
        if len(centroid_xy) == 2 and point_in_feature(float(centroid_xy[0]), float(centroid_xy[1]), zone):
            count += 1
    return count


def append_rural_sample(features: list[dict], rural_zone: dict, designated_zones: list[dict]) -> list[str]:
    if centroids_in_feature(features, rural_zone) > 0:
        print("Sample already has a parcel in the rural-eligible tract; not adding more")
        return []
    geometry = rural_zone.get("geometry") or {}
    coords = geometry.get("coordinates") or []
    flat: list[list[float]] = []

    def walk(value):
        if isinstance(value, list) and value and isinstance(value[0], (int, float)):
            flat.append(value[:2])
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(coords)
    if not flat:
        raise RuntimeError("Rural tract geometry has no coordinates")
    xmin = min(point[0] for point in flat)
    ymin = min(point[1] for point in flat)
    xmax = max(point[0] for point in flat)
    ymax = max(point[1] for point in flat)
    raw_features = arcgis_query(
        OCPA_URL,
        {
            "where": "ACREAGE >= 2 AND ACREAGE <= 120 AND CONDO_FLAG <> 'C'",
            "outFields": ",".join(OCPA_FIELDS),
            "returnGeometry": "true",
            "outSR": 4326,
            "geometry": f"{xmin},{ymin},{xmax},{ymax}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "orderByFields": "ACREAGE DESC",
        },
        page_size=80,
        max_records=80,
    )
    existing = {(feature.get("properties") or {}).get("id") for feature in features}
    inside = []
    for raw in raw_features:
        geom = rings_to_geojson(raw.get("geometry"))
        pid = clean_str((raw.get("attributes") or {}).get("PARCEL"))
        if not geom or not pid or pid in existing:
            continue
        lon, lat = centroid(geom)
        if point_in_feature(lon, lat, rural_zone):
            inside.append(raw)
    if not inside:
        raise RuntimeError(f"OCPA returned no parcels inside rural-eligible tract {EXPECTED_RURAL_GEOID}")

    def acres(raw: dict) -> float:
        try:
            return float((raw.get("attributes") or {}).get("ACREAGE") or 0)
        except (TypeError, ValueError):
            return 0

    def zoning_code(raw: dict) -> str:
        return str((raw.get("attributes") or {}).get("ZONING_CODE") or "")

    def situs(raw: dict) -> str:
        return str((raw.get("attributes") or {}).get("SITUS") or "").upper()

    chosen: list[dict] = []

    def take(predicate) -> None:
        if len(chosen) >= SAMPLE_CAP:
            return
        for raw in sorted(inside, key=acres):
            pid = clean_str((raw.get("attributes") or {}).get("PARCEL"))
            if any(clean_str((item.get("attributes") or {}).get("PARCEL")) == pid for item in chosen):
                continue
            if predicate(raw):
                chosen.append(raw)
                return

    take(lambda raw: "P-D" in zoning_code(raw))
    take(lambda raw: "COLONIAL" in situs(raw))
    take(lambda raw: True)

    income_tracts = json.loads(INCOME_TRACTS.read_text())
    income_block_groups = json.loads(INCOME_BLOCK_GROUPS.read_text())
    roads = traffic_roads(json.loads(TRAFFIC.read_text())) if TRAFFIC.exists() else []
    added_ids: list[str] = []
    for raw in chosen:
        feature = parcel_feature_from_ocpa(
            raw,
            income_tracts,
            income_block_groups,
            roads,
            designated_zones,
            EXPECTED_RURAL_GEOID,
        )
        if not feature:
            continue
        features.append(feature)
        added_ids.append(feature["properties"]["id"])
        print(
            "Added rural-tract parcel",
            feature["properties"]["id"],
            feature["properties"].get("situsAddress"),
            feature["properties"].get("zoningCode"),
            feature["properties"].get("acreage"),
        )
    if not added_ids:
        raise RuntimeError("Failed to build parcel features inside the rural-eligible tract")
    return added_ids


def oz2_info(hit: dict | None) -> dict:
    if not hit:
        return {
            "eligible": False,
            "rural": None,
            "tractGeoid": None,
            "tractName": None,
            "designation": "not-eligible",
            "source": "rev-proc-2026-14",
        }
    props = hit.get("properties") or hit
    return {
        "eligible": True,
        "rural": bool(props.get("rural")),
        "tractGeoid": props.get("tractGeoid"),
        "tractName": props.get("name"),
        "designation": "eligible-for-nomination",
        "source": "rev-proc-2026-14",
    }


def main() -> None:
    eligible = load_orange_eligible()
    tiger = fetch_tiger_tracts(sorted(eligible))
    zones = []
    for geoid in sorted(eligible):
        feature = tiger[geoid]
        props = feature["properties"]
        county_name = str(eligible[geoid].get("county") or "")
        if county_name.endswith(" County"):
            county_name = county_name[: -len(" County")].strip()
        props["county"] = county_name or None
        props["state"] = eligible[geoid].get("state")
        props["rural"] = eligible[geoid]["rural"]
        props["designation"] = "eligible-for-nomination"
        props["source"] = "rev-proc-2026-14"
        zones.append(feature)
    rural_zone = next(zone for zone in zones if zone["properties"]["tractGeoid"] == EXPECTED_RURAL_GEOID)

    notice = load_notice_rural_geoids()
    overlay = json.loads(OZ_POLYS.read_text()) if OZ_POLYS.exists() else {"type": "FeatureCollection", "features": []}
    designated_rural = 0
    for feature in overlay.get("features") or []:
        props = feature.setdefault("properties", {})
        geoid = str(props.get("tractGeoid") or "")
        props["rural"] = geoid in notice
        if props["rural"]:
            designated_rural += 1
    print(f"Designated Orange County QOZ tracts flagged rural by Notice 2025-50: {designated_rural}")

    collection = json.loads(PARCELS.read_text())
    features = collection.setdefault("features", [])
    added_ids = append_rural_sample(features, rural_zone, overlay.get("features") or [])

    lookup: dict[str, dict] = {}
    eligible_count = 0
    rural_parcel_count = 0
    for feature in features:
        props = feature.setdefault("properties", {})
        pid = props.get("id") or ""
        centroid_xy = props.get("centroid") or []
        if len(centroid_xy) != 2:
            info = oz2_info(None)
        else:
            hit = None
            for zone in zones:
                if point_in_feature(float(centroid_xy[0]), float(centroid_xy[1]), zone):
                    hit = zone
                    break
            info = oz2_info(hit)
        props["oz2Eligibility"] = info
        lookup[pid] = info
        if info["eligible"]:
            eligible_count += 1
        if info["rural"] is True:
            rural_parcel_count += 1

        opportunity = props.get("opportunityZone")
        if isinstance(opportunity, dict):
            if opportunity.get("inOpportunityZone") and opportunity.get("tractGeoid"):
                opportunity["designatedRural"] = str(opportunity["tractGeoid"]) in notice
            else:
                opportunity["designatedRural"] = None
            props["opportunityZone"] = opportunity

    if rural_parcel_count < 1:
        raise RuntimeError(f"No parcel centroid falls in rural-eligible tract {EXPECTED_RURAL_GEOID}")

    OZ2_POLYS.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "name": "orange-county-fl-oz2-eligible",
                "features": zones,
            },
            separators=(",", ":"),
        )
    )
    OZ_POLYS.write_text(json.dumps(overlay, separators=(",", ":")))
    PARCELS.write_text(json.dumps(collection, separators=(",", ":")))

    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rural_geoids = [geoid for geoid, row in sorted(eligible.items()) if row["rural"]]
    OZ2_TABLE.write_text(
        json.dumps(
            {
                "generatedAt": generated_at,
                "source": RP_APPENDIX_URL,
                "county": "Orange County, FL",
                "countyFips": "12095",
                "eligibleCount": len(eligible),
                "ruralCount": len(rural_geoids),
                "ruralGeoids": rural_geoids,
                "note": "Eligible for nomination under Rev. Proc. 2026-14. Not nominated or certified as 2027 QOZs.",
                "tracts": [eligible[geoid] for geoid in sorted(eligible)],
            },
            indent=2,
        )
    )
    NOTICE_GEOIDS.write_text(
        json.dumps(
            {
                "generatedAt": generated_at,
                "source": NOTICE_2025_50_URL,
                "count": len(notice),
                "orangeCountyFl": sorted(geoid for geoid in notice if geoid.startswith("12095")),
                "geoids": sorted(notice),
            },
            indent=2,
        )
    )
    OZ2_LOOKUP.write_text(
        json.dumps(
            {
                "generatedAt": generated_at,
                "parcelCount": len(features),
                "eligibleParcelCount": eligible_count,
                "ruralEligibleParcelCount": rural_parcel_count,
                "addedParcelIds": added_ids,
                "tractCount": len(zones),
                "ruralTractGeoids": rural_geoids,
                "source": RP_APPENDIX_URL,
                "geometrySource": TIGER_TRACTS_URL.replace("/query", ""),
                "designatedRuralSource": NOTICE_2025_50_URL,
                "designatedOrangeRuralCount": designated_rural,
                "joinMethod": "parcel-centroid-in-2020-census-tract",
                "notes": [
                    "OZ 2.0 eligibility and the rural flag come from the Rev. Proc. 2026-14 appendix Rural Status column.",
                    "These tracts are eligible for nomination. They are not designated 2027 Qualified Opportunity Zones.",
                    "Current designated-zone rural flags come from membership in the Notice 2025-50 appendix, not from a local classifier.",
                ],
                "byParcel": lookup,
            },
            indent=2,
        )
    )

    if added_ids and FLU_LOOKUP.exists():
        flu_lookup = json.loads(FLU_LOOKUP.read_text())
        by_parcel = flu_lookup.setdefault("byParcel", {})
        for feature in features:
            pid = (feature.get("properties") or {}).get("id")
            if pid in added_ids:
                by_parcel[pid] = (feature.get("properties") or {}).get("flu")
        flu_lookup["parcelCount"] = len(features)
        flu_lookup["joinedCount"] = sum(1 for feature in features if (feature.get("properties") or {}).get("flu"))
        FLU_LOOKUP.write_text(json.dumps(flu_lookup, indent=2))

    if META.exists():
        meta = json.loads(META.read_text())
        meta["parcelCount"] = len(features)
        meta["oz2JoinedAt"] = generated_at
        meta["oz2EligibleTractCount"] = len(zones)
        meta["oz2RuralTractCount"] = len(rural_geoids)
        meta["oz2RuralTractGeoids"] = rural_geoids
        meta["oz2EligibleParcelCount"] = eligible_count
        meta["oz2RuralParcelCount"] = rural_parcel_count
        meta["oz2Source"] = RP_APPENDIX_URL
        meta["oz2GeometrySource"] = TIGER_TRACTS_URL.replace("/query", "")
        meta["designatedRuralSource"] = NOTICE_2025_50_URL
        meta["designatedRuralOrangeCount"] = designated_rural
        meta["notice202550RuralGeoidCount"] = len(notice)
        if added_ids:
            meta["oz2SampleParcelIds"] = added_ids
            meta["fluJoinedCount"] = sum(1 for feature in features if (feature.get("properties") or {}).get("flu"))
        sources = meta.get("sources") or {}
        sources["oz2Eligible"] = RP_APPENDIX_URL
        sources["oz2Geometry"] = TIGER_TRACTS_URL.replace("/query", "")
        sources["designatedRural"] = NOTICE_2025_50_URL
        meta["sources"] = sources
        notes = meta.get("notes") or []
        oz2_note = (
            "OZ 2.0 tracts are 2020 census tracts eligible for nomination under Rev. Proc. 2026-14, "
            "joined by parcel centroid. Rural status is the appendix Rural Status column. "
            "They are not designated 2027 QOZs. Current designated rural flags follow Notice 2025-50."
        )
        if oz2_note not in notes:
            notes.append(oz2_note)
        meta["notes"] = notes
        META.write_text(json.dumps(meta, indent=2))

    print(
        json.dumps(
            {
                "eligibleTracts": len(zones),
                "ruralTracts": rural_geoids,
                "eligibleParcels": eligible_count,
                "ruralParcels": rural_parcel_count,
                "addedParcels": added_ids,
                "designatedOrangeRural": designated_rural,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"join_oz2 failed: {exc}", file=sys.stderr)
        raise
