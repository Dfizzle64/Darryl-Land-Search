#!/usr/bin/env python3
"""Public 5.0–150.0 acre parcels for 20 Tennessee counties.

Parcel layers are chosen from data/tn-parcel-cards by each layer's use
label and the card's parcelSetup block. The first role:parcels layer is
never the source. After a refreshed card changes a URL, re-pull only
that county:

    python3 scripts/tn_oir_parcels.py --county Sevier --refresh

data/tn-rural-parcel-sources.json still holds zoning join URLs and the
published source id. A new county is a YAML card plus a catalog row.

The source rule wins over older card text. Geometry and owner come from
the Tennessee OIR layer Tennessee Property Boundaries Public Use (edited
2026-09-10). Sale date, sale price, and appraisal are joined from AGOL
TN_County_Parcel_Map (edited 2023-11-22) on GISLINK and labeled 2023.
Acreage is polygon area because DEEDAC is often 0.

Hickman uses the May 2023 CaptureCAMA snapshot and labels value 2020.
Chester uses the county CaptureCAMA Parcels_12 layer: the parcel id is
the CAMA GISLINK, then the map id, and rows with neither id are dropped.
Chester has no public sale field, so sale data stays empty, and value is
labeled 2026. Sevier geometry and owner stay on OIR. Sevier sale and
value come from the Sevierville countywide CAMA and are labeled 2025.
Overton sale and value come from UCDD Overton_Parcels and are labeled
2019. Wilson sale and value fields are the uppercase ASSESSMENT_DATA_95
names. Acreage for every county is geodesic polygon area. A sale date
later than the pull date is dropped. The TPAD link is not fetched.

Bedford County, Pennsylvania, Utah Sevier County, and paid parcel vendors
are rejected. Opportunity Zone status is not set.
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

from parcel_geometry import esri_rings_to_geojson, geodesic_acres, representative_point

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "data" / "tn-rural-parcel-sources.json"
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
CHESTER_PORTAL = "https://chester.capturecama.com/CAMA/CAPortal/CZ_MainPage.aspx"
HICKMAN_PORTAL = "https://hickman.capturecama.com/CAMA/CAPortal/CZ_MainPage.aspx"
# Browsers open this card. Server and datacenter fetches get 403, so ingest,
# tests, and the build must not request it.
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
    "ASMT",
    "TAXYR",
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
    "GPDATA__26",
    "GPDATA__AP",
    "GPDATA__27",
]

# Paid vendors, the Pennsylvania namesakes of Bedford and Chester, and Utah Sevier.
REJECTED_URL_TOKENS = (
    "regrid",
    "chesco.org",
    "pasda.psu.edu",
    "april2023parcels",
    "bedfordcountypa",
    "imagery.pasda",
    "gis.utah.gov",
    "agrc.utah",
)


def reject_source_url(url: str) -> None:
    """Refuse paid vendors and the out-of-state namesakes of these counties."""
    lowered = (url or "").lower()
    for token in REJECTED_URL_TOKENS:
        if token in lowered:
            raise RuntimeError(
                f"Refusing {url}. That endpoint is a paid vendor, a Pennsylvania "
                "Bedford/Chester layer, or Utah Sevier County parcels."
            )


def assert_sevier_primary(row: dict) -> None:
    """Sevier geometry is OIR. Sale and value come from the 2025 county CAMA."""
    if row.get("fips") != "47155":
        return
    url = row.get("queryUrl") or ""
    sales = ((row.get("salesJoin") or {}).get("url")) or ""
    if "Tennessee_Property_Boundaries_Public_Use" not in url:
        raise RuntimeError("Sevier geometry and owner must come from the OIR statewide layer")
    if "GIS_Department_Layers/MapServer/57" not in sales:
        raise RuntimeError("Sevier sale and value must come from the Sevierville countywide CAMA")
    if str(row.get("salesVintage")) != "2025":
        raise RuntimeError("Sevier salesValueVintage must be 2025")
    if row.get("tncpmLayer") is not None:
        raise RuntimeError("Sevier does not take sale and value from the 2023 TN_County_Parcel_Map join")
    reject_source_url(url)
    reject_source_url(sales)


def load_source_rows(path: Path | None = None) -> list[dict[str, Any]]:
    """Resolve parcel endpoints from the YAML cards. The JSON file is the zoning overlay."""
    from tn_parcel_cards import load_cards, resolve_card

    source_path = path or SOURCES_PATH
    payload = json.loads(source_path.read_text())
    overlays = payload.get("counties")
    if not isinstance(overlays, list) or not overlays:
        raise RuntimeError(f"{source_path} has no counties")
    by_overlay: dict[str, dict] = {}
    for overlay in overlays:
        fips = overlay.get("fips")
        if not fips or fips in by_overlay:
            raise RuntimeError(f"Duplicate or blank FIPS in {source_path}")
        by_overlay[fips] = overlay
    cards = load_cards()
    card_fips = {str(card["fips"]) for card in cards}
    missing = sorted(set(by_overlay) - card_fips)
    if missing:
        raise RuntimeError(f"Missing parcel cards for {', '.join(missing)}")
    rows: list[dict[str, Any]] = []
    for card in cards:
        row = resolve_card(card, by_overlay.get(str(card["fips"])))
        if not row.get("queryUrl") or not row.get("mode") or not row.get("source"):
            raise RuntimeError(f"{row.get('fips')} is missing mode, source, or queryUrl")
        if row.get("acreageMethod") != "geodesic":
            raise RuntimeError(f"{row['fips']} must filter on geodesic polygon area")
        reject_source_url(row["queryUrl"])
        sales_url = ((row.get("salesJoin") or {}).get("url")) or ""
        if sales_url:
            reject_source_url(sales_url)
        assert_sevier_primary(row)
        for join_url in (row.get("joins") or {}).values():
            if isinstance(join_url, str):
                reject_source_url(join_url)
        rows.append(row)
    return rows


COUNTIES: list[dict[str, Any]] = load_source_rows()
BY_FIPS = {row["fips"]: row for row in COUNTIES}


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


def positive(value: Any) -> float | None:
    parsed = num(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def yymmdd_to_iso(value: Any) -> str | None:
    """Some CaptureCAMA dates are YYMMDD. Two-digit years 70–99 are 19xx."""
    text = clean(value)
    if not text or not text.isdigit():
        return None
    if len(text) == 6:
        year = int(text[:2])
        year = 1900 + year if year >= 70 else 2000 + year
        month = int(text[2:4])
        day = int(text[4:6])
    elif len(text) == 8:
        year = int(text[:4])
        month = int(text[4:6])
        day = int(text[6:8])
    else:
        return None
    if not (1900 <= year <= 2026 and 1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def slash_date_to_iso(value: Any) -> str | None:
    """UCDD Overton sale dates are M/D/YYYY."""
    text = clean(value)
    if not text or "/" not in text:
        return None
    parts = text.split("/")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    month, day, year = (int(part) for part in parts)
    if not (1900 <= year <= 2026 and 1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def trailing_year(value: Any) -> str | None:
    text = clean(value)
    if not text:
        return None
    token = text.split()[-1]
    if len(token) == 4 and token.isdigit() and 1990 <= int(token) <= 2026:
        return token
    return None


def gis_keys(value: Any) -> list[str]:
    text = clean(value)
    if not text:
        return []
    collapsed = "".join(text.split())
    if collapsed == text:
        return [text]
    return [text, collapsed]


def chester_parcel_id(attrs: dict[str, Any]) -> tuple[str | None, str]:
    """CAMA GISLINK, else map id. Neither means the row is dropped."""
    gislink = clean(attrs.get("GPDATA__GI"))
    map_id = clean(attrs.get("L15Parce_2"))
    if gislink:
        return gislink, "cama-gislink"
    if map_id:
        return map_id, "map"
    return None, "neither"


def acceptable_sale_date(value: str | None, *, today: Any = None) -> str | None:
    """Drop blank dates and junk years after the pull date, such as 2325."""
    from datetime import date

    text = clean(value)
    if not text:
        return None
    try:
        parsed = date.fromisoformat(text[:10])
    except ValueError:
        return None
    current = today or date.today()
    if parsed > current:
        return None
    return parsed.isoformat()


def tpad_url(explicit: Any, gislink: Any) -> str | None:
    """Store the TPAD card link. Do not fetch it; datacenters receive 403."""
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
        gaps = hickman_gaps()
    elif mode == "chester":
        gaps = chester_gaps()
    elif mode == "county-hosted":
        gaps = sevier_gaps()
    else:
        gaps = oir_gaps(row)
    return {
        "kind": "tn-oir",
        "url": row["queryUrl"],
        "source": row["source"],
        "coverage": "complete-gte-5ac",
        "gaps": gaps,
    }


def oir_gaps(row: dict) -> list[str]:
    vintage = row.get("salesVintage") or "2023"
    notes = [
        "Geometry and owner are Tennessee OIR Tennessee Property Boundaries Public Use, edited 2026-09-10, filtered by Comptroller COUNTY_ID. Acreage is the geodesic area of the polygon because DEEDAC is often 0. The filter is 5.0–150.0 acres inclusive. Vertices are not simplified.",
        f"Sale date, sale price, and appraisal are joined on GISLINK and labeled {vintage} in the popup when a value is present. A GISLINK with no match is left without sale or value. Assessed value, taxable value, and tax amount are not on the TN_County_Parcel_Map join.",
        "The property-record link is LINK_TPAD when the OIR row publishes it, otherwise the TPAD GIS card for the same GISLINK. Opportunity Zone status was not inferred.",
        "Regrid and other paid parcel vendors were not used.",
    ]
    if row["fips"] == "47111":
        notes.insert(
            0,
            "Macon was a shelf gap because the generic Tennessee loader queried IMPACT COUNTY_ID=111, the FIPS suffix. The Comptroller county number is 56. This extract uses OIR COUNTY_ID=56.",
        )
    if row["fips"] == "47003":
        notes.insert(
            0,
            "Bedford is Bedford County, Tennessee (FIPS 47003). April2023Parcels and the Bedford County, Pennsylvania viewer were not used. Centroids outside Tennessee abort the load.",
        )
    if row["fips"] == "47133":
        notes[1] = (
            "Overton is not a layer on TN_County_Parcel_Map. Sale date, sale price, appraisal, and mailing are joined from UCDD Overton_Parcels on GISLINK. The latest tax year on that roll is 2019, so those fields are labeled 2019. Owner and geometry stay on the 2026 OIR layer. An unmatched GISLINK is left without sale or value."
        )
    if row["fips"] == "47155":
        notes[1] = (
            "Sevier sale date, sale price, appraisal, assessed value, and mailing are joined from the Sevierville countywide CAMA (GIS_Department_Layers MapServer/57) on GISLINK. That CAMA is labeled 2025. The 2023 TN_County_Parcel_Map layer is not the sale source. Owner and geometry stay on the 2026 OIR layer. An unmatched GISLINK is left without sale or value."
        )
    if row.get("salesGap"):
        notes[1] = (
            "Sale date, sale price, and appraisal stay empty. "
            "The card's sales-value source is a gap: TN_County_Parcel_Map does not publish this county, "
            "and the only bulk CAMA is IMPACT, which returns HTTP 403 from this network. "
            "The TPAD link is stored and not requested. Owner phone and email are not ingested."
        )
    sales_url = ((row.get("salesJoin") or {}).get("url")) or ""
    if row.get("tncpmLayer") is None and sales_url and "tn_county_parcel_map" not in sales_url.lower() and not row.get("salesGap"):
        notes[1] = (
            f"Sale date, sale price, and appraisal are joined from the card sales-value layer ({sales_url}) on GISLINK and labeled {vintage} when a value is present. "
            "A GISLINK with no match is left without sale or value. The 2023 TN_County_Parcel_Map sibling is not the sale source. Owner phone and email are not ingested."
        )
    if row.get("missingMarketValueField"):
        notes.append(
            f"Pass 2 records {row['missingMarketValueField']} as missing on the sale/value layer. "
            "Market value stays empty. Land market value is not copied in its place. Sale date and sale price are still joined."
        )
    return notes


def sevier_gaps() -> list[str]:
    return [
        "Sevier parcels are the county-hosted Sevierville GIS layer GIS_Department_Layers MapServer/57. The statewide OIR layer and TN_County_Parcel_Map are not the primary source. Utah AGRC Sevier County parcels were not used.",
        "Acreage is computed from the polygon. The filter is 5.0–150.0 acres inclusive. Vertices are not simplified. CALC_ACRE is recorded as a source statistic and is not the filter.",
        "Owner, situs, mailing, sale date, sale price, appraisal, and assessed value come from that county layer. A sale price of 0 is treated as no price. Those sale and value fields are the county CAMA and are not labeled 2023.",
        "The property-record link is the Comptroller TPAD GIS card for the GISLINK. Opportunity Zone status was not inferred. Regrid and other paid parcel vendors were not used.",
    ]


def hickman_gaps() -> list[str]:
    return [
        "Hickman is not in the OIR statewide layer or TN_County_Parcel_Map. The only public polygon source used here is the CaptureCAMA snapshot HickmanTN05182023 (May 18, 2023).",
        "Acreage is the geodesic area of the polygon, from 5.0 through 150.0 inclusive. Owner and situs street come from that snapshot. CITY, STATE, and ZIP are the mailing city, not the situs city. APRVAL is market value and ASMT is assessed value, labeled 2020. TAXYR on this layer is not a year. There is no sale date or sale price.",
        "Hickman is outside Comptroller TPAD. The property-record link is the CaptureCAMA citizen portal, not a TPAD GIS card. The research card has no zoning or future-land-use FeatureServer. Opportunity Zone status was not inferred. Regrid was not used.",
    ]


def chester_gaps() -> list[str]:
    return [
        "Chester is not in the OIR statewide layer. Geometry and CAMA attributes are the public Chester County, Tennessee CaptureCAMA Parcels_12 layer (ChesterTN/ChesterCapture). Chester County, Pennsylvania (chesco.org and PASDA) was not used.",
        "Acreage is the geodesic area of the polygon, from 5.0 through 150.0 inclusive. The parcel id is GPDATA__GI, falling back to the map id L15Parce_2. Rows with neither id are dropped.",
        "GPDATA__30 is market value and GPDATA__26 is assessed value, labeled 2026. This layer has no public sale date or sale price, so sale data stays empty. GPDATA__LA is the record's last-updated date and is not a sale. GPDATA__CI is the mailing city, not the situs city. There is no confirmed parcel deep link, so the link is the CaptureCAMA citizen portal. Opportunity Zone status was not inferred. Regrid was not used.",
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
    acres = geodesic_acres(rings)
    center = representative_point(geometry)
    if not center:
        return None, acres, None
    assert_tennessee(center[0], center[1], source_url)
    if not (-90.5 < center[0] < -81.4 and 34.8 < center[1] < 36.8):
        return None, acres, None
    return geometry, acres, center


def load_oir(row: dict, county: dict, markets: list[str], source: str) -> tuple[list[dict], dict]:
    url = row["queryUrl"]
    oir_name = row["oirName"]
    where = row.get("where") or f"COUNTY_NAME='{oir_name}' AND PARCEL_TYPE=1"
    print(f"  OIR ids {where}", flush=True)
    ids = fetch_object_ids(url, where)
    print(f"  OIR object ids {len(ids)}", flush=True)
    by_id: dict[str, dict] = {}
    dropped_geom = 0
    dropped_band = 0
    dropped_id = 0
    deed_in_band = 0
    fetched = 0
    considered = 0
    for page in iter_by_ids(url, ids, OIR_FIELDS, geometry=True, batch=40):
        fetched += len(page)
        for item in page:
            considered += 1
            attrs = item.get("attributes") or {}
            county_name = clean(attrs.get("COUNTY_NAME"))
            if county_name and county_name.upper() != oir_name:
                raise RuntimeError(f"{row['fips']} received COUNTY_NAME {attrs.get('COUNTY_NAME')}")
            found_county = num(attrs.get("COUNTY_ID"))
            if row.get("countyId") is not None and found_county is not None and int(found_county) != int(row["countyId"]):
                raise RuntimeError(f"{row['fips']} received COUNTY_ID {attrs.get('COUNTY_ID')}")
            geometry, acres, center = geometry_acres(item, url)
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


def tncpm_field_map(layer_id: int, explicit: dict | None = None) -> dict[str, str]:
    meta = get_json(f"{TNCPM_ROOT}/{layer_id}?f=json")
    # Layer metadata is a GET-style document; post_json still works for f=json.
    names = [field["name"] for field in meta.get("fields") or []]
    if not names:
        raise RuntimeError(f"TN_County_Parcel_Map layer {layer_id} returned no fields")
    requested = explicit or {}

    def resolve(wanted: str, suffix: str) -> str:
        if wanted:
            exact = next((name for name in names if name == wanted), None)
            if exact:
                return exact
            folded = next((name for name in names if name.upper() == wanted.upper()), None)
            if folded:
                return folded
            raise RuntimeError(f"TN_County_Parcel_Map layer {layer_id} has no field {wanted}")
        hits = [name for name in names if name.upper().endswith(suffix) and "ASSESSMENT_DATA" in name.upper()]
        return hits[0] if hits else ""

    gis = resolve(requested.get("gis") or "", "") if requested.get("gis") else next(
        (name for name in names if name.upper() == "PARCELS_GISLINK"), None
    )
    if not gis:
        raise RuntimeError(f"TN_County_Parcel_Map layer {layer_id} has no Parcels_GISLINK")
    return {
        "gis": gis,
        "price": resolve(requested.get("price") or "", "_PRICE"),
        "date": resolve(requested.get("date") or "", "_SALEDATE"),
        "value": resolve(requested.get("value") or "", "_APPRAISAL"),
    }


def load_tncpm(layer_id: int, explicit: dict | None = None) -> tuple[dict[str, dict], dict[str, str]]:
    fields_map = tncpm_field_map(layer_id, explicit)
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


def apply_2023_join(
    features: list[dict],
    layer_id: int | None,
    vintage: str = VINTAGE_2023,
    explicit_fields: dict | None = None,
) -> dict:
    from seed_market_parcels import epoch_to_iso

    matched = 0
    sales = 0
    values = 0
    if layer_id is None:
        for feature in features:
            feature["properties"].pop("_gislink", None)
        return {"tncpmLayer": None, "tncpmMatched": 0, "saleCount": 0, "appraisalCount": 0, "gislinkMatchRate": None}
    index, _fields = load_tncpm(layer_id, explicit_fields)
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
        sold = acceptable_sale_date(epoch_to_iso(row["date"]))
        appraisal = row["value"] if row["value"] is not None and row["value"] > 0 else None
        if price is not None or sold is not None:
            props["lastSale"] = {"date": sold, "price": price, "qualified": None, "vintage": vintage}
            sales += 1
        if appraisal is not None:
            props["tax"]["marketValue"] = appraisal
            props["tax"]["vintage"] = vintage
            values += 1
    rate = (matched / len(features)) if features else None
    return {
        "tncpmLayer": layer_id,
        "tncpmMatched": matched,
        "saleCount": sales,
        "appraisalCount": values,
        "gislinkMatchRate": round(rate, 4) if rate is not None else None,
        "salesVintage": vintage,
    }


def load_county_hosted(row: dict, county: dict, markets: list[str], source: str) -> tuple[list[dict], dict]:
    """Primary polygons and CAMA from a county layer. Acreage is the polygon, not a 2023 join."""
    from seed_market_parcels import epoch_to_iso

    assert_sevier_primary(row)
    url = row["queryUrl"]
    fields_map = row.get("fields") or {}
    required = ("id", "owner", "situs", "saleDate", "salePrice", "marketValue", "calcAcres")
    missing = [name for name in required if not fields_map.get(name)]
    if missing:
        raise RuntimeError(f"{row['fips']} county-hosted field map is missing {', '.join(missing)}")
    out_fields = list(dict.fromkeys(value for value in fields_map.values() if value))
    where = row.get("where") or "1=1"
    print(f"  county-hosted ids {url} {where}", flush=True)
    ids = fetch_object_ids(url, where)
    print(f"  county-hosted object ids {len(ids)}", flush=True)
    by_id: dict[str, dict] = {}
    dropped_geom = 0
    dropped_band = 0
    dropped_id = 0
    dropped_prefix = 0
    calc_in_band = 0
    fetched = 0
    considered = 0
    prefix = clean(row.get("gislinkPrefix"))
    expected_county = row.get("countyId")
    county_field = fields_map.get("countyId")
    for page in iter_by_ids(url, ids, out_fields, geometry=True, batch=40):
        fetched += len(page)
        for item in page:
            considered += 1
            attrs = item.get("attributes") or {}
            if expected_county is not None and county_field:
                found_county = num(attrs.get(county_field))
                # This layer stores 0 when the comptroller id was not filled in.
                if found_county is not None and int(found_county) not in (0, int(expected_county)):
                    raise RuntimeError(
                        f"{row['fips']} received COUNTY_ID {attrs.get(county_field)} from {url}"
                    )
            if in_band(num(attrs.get(fields_map["calcAcres"]))):
                calc_in_band += 1
            geometry, acres, center = geometry_acres(item, url)
            if not geometry or not center:
                dropped_geom += 1
                continue
            if not in_band(acres):
                dropped_band += 1
                continue
            parcel_id = clean(attrs.get(fields_map["id"])) or clean(attrs.get(fields_map.get("altId") or ""))
            if not parcel_id:
                dropped_id += 1
                continue
            if prefix and not "".join(parcel_id.split()).startswith(prefix):
                dropped_prefix += 1
                continue
            feature = base_feature(
                county=county,
                markets=markets,
                parcel_id=parcel_id,
                acreage=acres,
                geometry=geometry,
                center=center,
                source=source,
                owner=clean(attrs.get(fields_map["owner"])),
                situs=clean(attrs.get(fields_map["situs"])),
                mail1=clean(attrs.get(fields_map.get("mail1") or "")),
                mail_city=clean(attrs.get(fields_map.get("mailCity") or "")),
                mail_state=clean(attrs.get(fields_map.get("mailState") or "")),
                mail_zip=clean(attrs.get(fields_map.get("mailZip") or "")),
            )
            props = feature["properties"]
            props["ownerName2"] = clean(attrs.get(fields_map.get("owner2") or ""))
            props["appraiserUrl"] = tpad_url(None, parcel_id)
            sold = acceptable_sale_date(epoch_to_iso(attrs.get(fields_map["saleDate"])))
            price = positive(attrs.get(fields_map["salePrice"]))
            if sold is not None or price is not None:
                props["lastSale"] = {"date": sold, "price": price, "qualified": None}
            appraisal = positive(attrs.get(fields_map["marketValue"]))
            assessed = positive(attrs.get(fields_map.get("assessedValue") or ""))
            if appraisal is not None:
                props["tax"]["marketValue"] = appraisal
            if assessed is not None:
                props["tax"]["assessedValue"] = assessed
            remember(by_id, feature)
    if fetched != len(ids):
        raise RuntimeError(f"{row['fips']} fetched {fetched} county features of {len(ids)} ids")
    if dropped_prefix and not by_id:
        raise RuntimeError(f"{row['fips']} dropped every row for GISLINK prefix {prefix}")
    kept = list(by_id.values())
    sales = sum(
        1
        for feature in kept
        if feature["properties"]["lastSale"].get("date") or feature["properties"]["lastSale"].get("price") is not None
    )
    appraisals = sum(1 for feature in kept if feature["properties"]["tax"].get("marketValue") is not None)
    assessed_count = sum(1 for feature in kept if feature["properties"]["tax"].get("assessedValue") is not None)
    stats = {
        "sourceRows": len(ids),
        "calcAcresInBand": calc_in_band,
        "droppedGeometry": dropped_geom,
        "droppedOutsideBand": dropped_band,
        "droppedNoId": dropped_id,
        "droppedWrongPrefix": dropped_prefix,
        "duplicateIdsCollapsed": considered - dropped_geom - dropped_band - dropped_id - dropped_prefix - len(by_id),
        "saleCount": sales,
        "appraisalCount": appraisals,
        "assessedCount": assessed_count,
        "saleVintage": None,
    }
    return kept, stats


def load_hickman(row: dict, county: dict, markets: list[str], source: str) -> tuple[list[dict], dict]:
    url = row["queryUrl"]
    where = row.get("where") or "1=1"
    portal = row.get("portal") or HICKMAN_PORTAL
    vintage = row.get("salesVintage") or VINTAGE_2023
    ids = fetch_object_ids(url, where)
    print(f"  Hickman ids {len(ids)}", flush=True)
    by_id: dict[str, dict] = {}
    dropped = 0
    calc_in_band = 0
    fetched = 0
    for page in iter_by_ids(url, ids, HICKMAN_FIELDS, geometry=True, batch=40):
        fetched += len(page)
        for item in page:
            attrs = item.get("attributes") or {}
            if in_band(num(attrs.get("CALC_ACRE"))):
                calc_in_band += 1
            geometry, acres, center = geometry_acres(item, url)
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
                mail1=clean(attrs.get("MAILADDR")),
                mail_city=clean(attrs.get("CITY")),
                mail_state=clean(attrs.get("STATE")),
                mail_zip=clean(attrs.get("ZIP")),
            )
            feature["properties"]["ownerName2"] = clean(attrs.get("OWNER2"))
            feature["properties"]["appraiserUrl"] = portal
            appraisal = num(attrs.get("APRVAL"))
            assessed = num(attrs.get("ASMT"))
            if appraisal is not None and appraisal > 0:
                feature["properties"]["tax"]["marketValue"] = appraisal
            if assessed is not None and assessed > 0:
                feature["properties"]["tax"]["assessedValue"] = assessed
            if feature["properties"]["tax"]["marketValue"] or feature["properties"]["tax"]["assessedValue"]:
                feature["properties"]["tax"]["vintage"] = vintage
            remember(by_id, feature)
    if fetched != len(ids):
        raise RuntimeError(f"Hickman fetched {fetched} of {len(ids)}")
    return list(by_id.values()), {
        "sourceRows": len(ids),
        "calcAcresInBand": calc_in_band,
        "dropped": dropped,
        "kept": len(by_id),
        "salesVintage": vintage,
    }


def load_chester(row: dict, county: dict, markets: list[str], source: str) -> tuple[list[dict], dict]:
    url = row["queryUrl"]
    where = row.get("where") or "1=1"
    portal = row.get("portal") or CHESTER_PORTAL
    vintage = row.get("salesVintage")
    ids = fetch_object_ids(url, where)
    print(f"  Chester ids {len(ids)}", flush=True)
    by_id: dict[str, dict] = {}
    dropped_neither = 0
    used_map = 0
    used_gis = 0
    outside = 0
    calc_in_band = 0
    fetched = 0
    for page in iter_by_ids(url, ids, CHESTER_FIELDS, geometry=True, batch=40):
        fetched += len(page)
        for item in page:
            attrs = item.get("attributes") or {}
            if in_band(num(attrs.get("L15Parce_4"))):
                calc_in_band += 1
            parcel_id, kind = chester_parcel_id(attrs)
            if kind == "neither" or not parcel_id:
                dropped_neither += 1
                continue
            geometry, acres, center = geometry_acres(item, url)
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
                mail1=clean(attrs.get("GPDATA__MA")),
                mail_city=clean(attrs.get("GPDATA__CI")),
                mail_state=clean(attrs.get("GPDATA__ST")),
                mail_zip=clean(attrs.get("GPDATA__ZI")),
            )
            feature["properties"]["ownerName2"] = clean(attrs.get("GPDATA___2"))
            feature["properties"]["appraiserUrl"] = portal
            appraisal = num(attrs.get("GPDATA__30"))
            assessed = num(attrs.get("GPDATA__26"))
            if appraisal is not None and appraisal > 0:
                feature["properties"]["tax"]["marketValue"] = appraisal
            if assessed is not None and assessed > 0:
                feature["properties"]["tax"]["assessedValue"] = assessed
            if vintage and (
                feature["properties"]["tax"].get("marketValue") is not None
                or feature["properties"]["tax"].get("assessedValue") is not None
            ):
                feature["properties"]["tax"]["vintage"] = str(vintage)
            if kind == "map":
                used_map += 1
            else:
                used_gis += 1
            remember(by_id, feature)
    if fetched != len(ids):
        raise RuntimeError(f"Chester fetched {fetched} of {len(ids)}")
    return list(by_id.values()), {
        "sourceRows": len(ids),
        "calcAcresInBand": calc_in_band,
        "droppedNeitherId": dropped_neither,
        "droppedGeometryOrBand": outside,
        "usedCamaGislink": used_gis,
        "usedMapId": used_map,
        "salesVintage": str(vintage) if vintage else None,
        "kept": len(by_id),
    }


def finalize_features(features: list[dict]) -> list[dict]:
    for feature in features:
        props = feature["properties"]
        if props.get("opportunityZone") not in (None,):
            raise RuntimeError("Opportunity Zone status must stay unset")
        for key in list(props):
            if "phone" in key.lower() or "email" in key.lower():
                raise RuntimeError(f"Refusing to keep owner contact field {key}")
        mail = props.get("mailingAddress") or {}
        if isinstance(mail, dict):
            for key in mail:
                if "phone" in key.lower() or "email" in key.lower():
                    raise RuntimeError(f"Refusing to keep mailing contact field {key}")
        acres = props.get("acreage")
        if not in_band(acres):
            raise RuntimeError(f"Parcel {props.get('parcelId')} is outside 5–150 acres ({acres})")
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise RuntimeError("Parcel geometry is not a polygon")
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    return features


def load_card_geometry(row: dict, county: dict, markets: list[str], source: str) -> tuple[list[dict], dict]:
    """Geometry for a card that is not OIR, Hickman, or Chester. Acreage is geodesic."""
    from tn_parcel_cards import stamp_mapped_sale

    if row.get("acreageMethod") != "geodesic":
        raise RuntimeError(f"{row['fips']} card geometry must use geodesic area")
    url = row["queryUrl"]
    where = row.get("where") or "1=1"
    fields = row.get("geometryFields") or {}
    wanted = [
        fields[key]
        for key in (
            "parcelId",
            "parcelIdAlt",
            "ownerName",
            "ownerName2",
            "situsAddress",
            "appraiserSearchUrlPerParcel",
        )
        if fields.get(key)
    ]
    sales = row.get("salesJoin") or {}
    if row.get("salesOnGeometry"):
        for key in (
            "dateField",
            "priceField",
            "marketField",
            "assessedField",
            "mail1",
            "mailCity",
            "mailState",
            "mailZip",
            "zoningField",
        ):
            if sales.get(key):
                wanted.append(sales[key])
    wanted = list(dict.fromkeys(wanted))
    if not fields.get("parcelId"):
        raise RuntimeError(f"{row['fips']} primary layer has no parcelId field")
    ids = fetch_object_ids(url, where)
    print(f"  card geometry ids {len(ids)} {where}", flush=True)
    by_id: dict[str, dict] = {}
    dropped = 0
    fetched = 0
    for page in iter_by_ids(url, ids, wanted, geometry=True, batch=40):
        fetched += len(page)
        for item in page:
            attrs = item.get("attributes") or {}
            geometry, acres, center = geometry_acres(item, url)
            if not geometry or not center or not in_band(acres):
                dropped += 1
                continue
            parcel_id = clean(attrs.get(fields.get("parcelId"))) or clean(attrs.get(fields.get("parcelIdAlt")))
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
                owner=clean(attrs.get(fields.get("ownerName"))),
                situs=clean(attrs.get(fields.get("situsAddress"))),
            )
            feature["properties"]["ownerName2"] = clean(attrs.get(fields.get("ownerName2")))
            link = clean(attrs.get(fields.get("appraiserSearchUrlPerParcel")))
            feature["properties"]["appraiserUrl"] = link or tpad_url(None, parcel_id)
            feature["properties"]["_gislink"] = parcel_id
            if row.get("salesOnGeometry"):
                stamp_mapped_sale(
                    feature["properties"],
                    attrs,
                    sales,
                    row.get("salesVintage"),
                    stamp_zoning=bool(row.get("stampSalesZoning")),
                )
            remember(by_id, feature)
    if fetched != len(ids):
        raise RuntimeError(f"{row['fips']} fetched {fetched} card features of {len(ids)} ids")
    return list(by_id.values()), {
        "sourceRows": len(ids),
        "dropped": dropped,
        "kept": len(by_id),
        "salesVintage": row.get("salesVintage"),
        "acreageMethod": "geodesic",
    }


def download_tn_oir(county: dict, markets: list[str], spec: dict) -> dict:
    from seed_market_parcels import county_row, write_tiles

    fips = county["fips"]
    row = BY_FIPS[fips]
    if row.get("acreageMethod") != "geodesic":
        raise RuntimeError(
            f"{fips} has no acreage filter on geodesic polygon area "
            f"(acreageField={row.get('acreageField')!r})"
        )
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
            stats.update(
                apply_2023_join(
                    features,
                    row.get("tncpmLayer"),
                    str(row.get("salesVintage") or VINTAGE_2023),
                    row.get("tncpmFields"),
                )
            )
        elif row["mode"] == "hickman":
            features, stats = load_hickman(row, county, markets, source)
        elif row["mode"] == "chester":
            features, stats = load_chester(row, county, markets, source)
        elif row["mode"] == "county-hosted":
            features, stats = load_county_hosted(row, county, markets, source)
        elif row["mode"] == "card":
            features, stats = load_card_geometry(row, county, markets, source)
        else:
            raise RuntimeError(f"{fips} has unknown mode {row['mode']}")
        features = finalize_features(features)
        if len(features) < 500:
            raise RuntimeError(f"{fips} kept only {len(features)} parcels; refusing to replace the shelf")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"stats": stats, "features": features}, separators=(",", ":")))
        print(f"  kept {len(features)}", flush=True)
    from tn_card_joins import apply_card_details

    join_stats = apply_card_details(features, row)
    gap_notes = list(join_stats.pop("gapNotes", []))
    stats = {**stats, **join_stats}
    if "salesVintage" not in stats:
        stats["salesVintage"] = row.get("salesVintage")
    rate = stats.get("gislinkMatchRate")
    if isinstance(rate, float) and rate < 0.9:
        gap_notes.append(
            f"GISLINK matched {rate:.1%} of kept parcels on the sale/value layer. "
            "Unmatched parcels are published without sale or value."
        )
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
        gaps=list(spec.get("gaps") or []) + gap_notes,
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
    parser.add_argument(
        "--sources",
        default=str(SOURCES_PATH),
        help="Zoning-join overlay. Parcel endpoints come from data/tn-parcel-cards.",
    )
    args = parser.parse_args()
    global COUNTIES, BY_FIPS
    COUNTIES = load_source_rows(Path(args.sources))
    BY_FIPS = {row["fips"]: row for row in COUNTIES}
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
