"""Bradley County, Tennessee parcels from Cleveland GIS Parcels_Impact.

Census FIPS is 47011. Comptroller county 006 is only the GIS filter. FIPS
47107 is McMinn County. Cleveland zoning polygons apply only inside the
Cleveland municipal boundary. Charleston and unincorporated Bradley keep the
assessor CAMA label. Future land use stays null. No Opportunity Zone
designation is assigned.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

BRADLEY_FIPS = "47011"
PARCEL_URL = (
    "https://utility.arcgis.com/usrsvcs/servers/93852593c94f4e178f338703adc6bca3"
    "/rest/services/Operational/OperationalLayersPRO/MapServer/2/query"
)
ZONING_URL = (
    "https://utility.arcgis.com/usrsvcs/servers/93852593c94f4e178f338703adc6bca3"
    "/rest/services/Operational/OperationalLayersPRO/MapServer/13/query"
)
BOUNDARY_URL = "https://gis.clevelandtn.gov/arcgis/rest/services/Operational/MunicipalBoundary/MapServer/0/query"
WHERE = "JUR='006' AND PARCEL_TYPE=1 AND CALC_ACRE>=5 AND CALC_ACRE<=150"
FIELDS = [
    "OBJECTID",
    "GISLINK",
    "JUR",
    "COUNTY_ID",
    "PARCEL_TYPE",
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
    "MAILLINE1",
    "MAILLINE2",
    "ZONING",
    "CALC_ACRE",
    "APPRAISAL",
    "SALEDATE",
    "PRICE",
    "LANDUSE",
    "PROPTYPE",
    "COUNTY",
]
SOURCE = "tn-cleveland-parcels-impact-47011"
# Bradley County, Tennessee. Excludes the old IMPACT COUNTY_ID=11 geometry near longitude -87.
BRADLEY_BOX = (-85.35, 34.9, -84.55, 35.4)


def bradley_spec() -> dict:
    return {
        "kind": "tn-bradley",
        "url": PARCEL_URL,
        "where": WHERE,
        "outFields": FIELDS,
        "source": SOURCE,
        "coverage": "complete-gte-5ac",
        "gaps": [],
    }


def _seed():
    import seed_market_parcels as seed

    return seed


def _page_attributes(url: str, where: str, out_fields: list[str], page: int = 2000) -> list[dict]:
    seed = _seed()
    rows: list[dict] = []
    offset = 0
    while True:
        data = seed.fetch_json(
            url,
            {
                "where": where,
                "outFields": ",".join(out_fields),
                "returnGeometry": "false",
                "orderByFields": "OBJECTID",
                "resultOffset": str(offset),
                "resultRecordCount": str(page),
                "f": "json",
            },
        )
        if data.get("error"):
            raise RuntimeError(str(data["error"])[:300])
        feats = data.get("features") or []
        rows.extend(item.get("attributes") or {} for item in feats)
        if not data.get("exceededTransferLimit") or not feats:
            break
        offset += len(feats)
    return rows


def _card_rank(attrs: dict) -> tuple:
    num = _seed().num
    taxyr = int(num(attrs.get("TAXYR")) or 0)
    parcel_id = str(attrs.get("PARCELID") or "")
    base = 1 if re.search(r"\s000\s+\d{4}\s*$", parcel_id) else 0
    appraisal = num(attrs.get("APPRAISAL")) or 0
    oid = int(attrs.get("OBJECTID") or 0)
    return (taxyr, base, appraisal, -oid)


def _choose_object_ids(rows: list[dict]) -> list[int]:
    clean = _seed().clean
    num = _seed().num
    best: dict[str, tuple] = {}
    for attrs in rows:
        link = clean(attrs.get("GISLINK"))
        if not link or not link.startswith("006"):
            continue
        jur = clean(attrs.get("JUR"))
        if jur and jur != "006":
            continue
        county_id = num(attrs.get("COUNTY_ID"))
        if county_id is not None and int(county_id) != 6:
            continue
        parcel_type = num(attrs.get("PARCEL_TYPE"))
        if parcel_type is not None and int(parcel_type) != 1:
            continue
        oid = attrs.get("OBJECTID")
        if oid is None:
            continue
        rank = _card_rank(attrs)
        current = best.get(link)
        if current is None or rank > current[0]:
            best[link] = (rank, int(oid))
    return [item[1] for item in best.values()]


def _point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geojson(x: float, y: float, geometry: dict | None) -> bool:
    if not geometry:
        return False
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if gtype == "Polygon":
        if not coords or not _point_in_ring(x, y, coords[0]):
            return False
        return all(not _point_in_ring(x, y, hole) for hole in coords[1:])
    if gtype == "MultiPolygon":
        for poly in coords:
            if poly and _point_in_ring(x, y, poly[0]) and all(not _point_in_ring(x, y, hole) for hole in poly[1:]):
                return True
    return False


def _geometry_bbox(geometry: dict) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def walk(node: object, depth: int) -> None:
        if depth == 0 and isinstance(node, (list, tuple)) and len(node) >= 2:
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        if isinstance(node, list):
            for child in node:
                walk(child, depth - 1)

    depth = 2 if geometry.get("type") == "Polygon" else 3
    walk(geometry.get("coordinates"), depth)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _parse_sale_date(value: Any) -> str | None:
    text = _seed().clean(value)
    if not text or text in {"0", "00000000"}:
        return None
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", text)
    if match:
        month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
            return f"{year:04d}-{month:02d}-{day:02d}"
        return None
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        year, month, day = int(iso.group(1)), int(iso.group(2)), int(iso.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
            return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def _situs(attrs: dict) -> str | None:
    clean = _seed().clean
    address = clean(attrs.get("ADDRESS"))
    if address:
        return address
    number = clean(attrs.get("ST_NUM"))
    street = clean(attrs.get("STREET"))
    parts = [part for part in (number, street) if part]
    return " ".join(parts) or None


def _load_boundary() -> dict:
    seed = _seed()
    data = seed.fetch_json(
        BOUNDARY_URL,
        {
            "where": "NAME='CLEVELAND'",
            "outFields": "NAME,LOCALFIPS",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "json",
        },
    )
    if data.get("error"):
        raise RuntimeError(str(data["error"])[:300])
    features = data.get("features") or []
    if len(features) != 1:
        raise RuntimeError(f"Expected one Cleveland municipal boundary, got {len(features)}")
    attrs = features[0].get("attributes") or {}
    if seed.clean(attrs.get("NAME")) != "CLEVELAND":
        raise RuntimeError("Municipal boundary NAME was not CLEVELAND")
    geometry, _acres = seed.rings_to_feature_geometry(features[0].get("geometry"))
    if not geometry:
        raise RuntimeError("Cleveland municipal boundary had no polygon")
    return geometry


def _load_zoning() -> list[dict]:
    seed = _seed()
    ids = seed.fetch_object_ids(ZONING_URL, "1=1")
    raw = seed.fetch_by_ids(ZONING_URL, ids, ["ZONECLASS", "ZONEDESC", "MUNICIPALITY"])
    zones: list[dict] = []
    for item in raw:
        attrs = item.get("attributes") or {}
        municipality = seed.clean(attrs.get("MUNICIPALITY"))
        if municipality and municipality.upper() not in {"CLEVELAND", "CITY OF CLEVELAND"}:
            continue
        code = seed.clean(attrs.get("ZONECLASS"))
        if not code:
            continue
        geometry, _acres = seed.rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            continue
        bbox = _geometry_bbox(geometry)
        if not bbox:
            continue
        zones.append({"code": code, "desc": seed.clean(attrs.get("ZONEDESC")), "geometry": geometry, "bbox": bbox})
    if len(zones) < 100:
        raise RuntimeError(f"Cleveland zoning polygons were incomplete ({len(zones)})")
    return zones


def _zone_at(lon: float, lat: float, zones: list[dict]) -> dict | None:
    found: dict | None = None
    found_area = None
    for zone in zones:
        minx, miny, maxx, maxy = zone["bbox"]
        if lon < minx or lon > maxx or lat < miny or lat > maxy:
            continue
        if not _point_in_geojson(lon, lat, zone["geometry"]):
            continue
        bbox_area = (maxx - minx) * (maxy - miny)
        if found is None or found_area is None or bbox_area < found_area:
            found = zone
            found_area = bbox_area
    return found


def _zoning_district(code: str, description: str | None, polygon: bool) -> str:
    if not polygon:
        return "CAMA first-pass label"
    desc = _seed().clean(description)
    if desc and desc.upper() != code.upper() and " " in desc:
        return desc
    return f"Mapped in Cleveland ({code})"


def _place(citynum: str | None, inside_cleveland: bool) -> str:
    if inside_cleveland:
        return "CLEVELAND"
    if citynum == "126":
        return "CHARLESTON"
    return "UNINCORPORATED"


def download_bradley(county: dict, markets: list[str], spec: dict) -> dict:
    seed = _seed()
    clean = seed.clean
    num = seed.num
    fips = county["fips"]
    if fips != BRADLEY_FIPS:
        raise RuntimeError(f"Bradley ingest is Census FIPS {BRADLEY_FIPS}, not {fips}")
    print(f"Pulling {county['name']} {county['state']} ({fips}) via {spec['source']}", flush=True)
    rows = _page_attributes(
        spec["url"],
        spec["where"],
        ["OBJECTID", "GISLINK", "JUR", "COUNTY_ID", "PARCEL_TYPE", "TAXYR", "PARCELID", "APPRAISAL"],
    )
    source_count = len(rows)
    print(f"  source rows {source_count}", flush=True)
    if source_count <= 0:
        raise RuntimeError("Cleveland Parcels_Impact returned no Bradley rows in the 5–150 acre band")
    winner_ids = _choose_object_ids(rows)
    print(f"  unique GISLINK {len(winner_ids)}", flush=True)
    raw = seed.fetch_by_ids(spec["url"], winner_ids, spec["outFields"])
    print("  loading Cleveland boundary and zoning districts", flush=True)
    boundary = _load_boundary()
    zones = _load_zoning()
    print(f"  zoning polygons {len(zones)}", flush=True)

    by_id: dict[str, dict] = {}
    outside = 0
    for item in raw:
        attrs = item.get("attributes") or {}
        link = clean(attrs.get("GISLINK"))
        jur = clean(attrs.get("JUR"))
        county_name = clean(attrs.get("COUNTY"))
        county_id = num(attrs.get("COUNTY_ID"))
        parcel_type = num(attrs.get("PARCEL_TYPE"))
        if (
            not link
            or not link.startswith("006")
            or jur != "006"
            or (county_name and county_name.upper() != "BRADLEY")
            or (county_id is not None and int(county_id) != 6)
            or (parcel_type is not None and int(parcel_type) != 1)
        ):
            continue
        geometry, _computed = seed.rings_to_feature_geometry(item.get("geometry"))
        if not geometry:
            continue
        center = seed.centroid_of(geometry)
        if not seed.plausible_centroid(center):
            continue
        acres = num(attrs.get("CALC_ACRE"))
        if not seed.in_band(acres):
            continue
        assert center is not None
        west, south, east, north = BRADLEY_BOX
        if not (west <= center[0] <= east and south <= center[1] <= north):
            outside += 1
            continue
        citynum = clean(attrs.get("CITYNUM"))
        inside = _point_in_geojson(center[0], center[1], boundary)
        place = _place(citynum, inside)
        zone = _zone_at(center[0], center[1], zones) if inside else None
        cama_zoning = clean(attrs.get("ZONING"))
        if zone:
            zoning_code = zone["code"]
            zoning_district = _zoning_district(zone["code"], zone["desc"], True)
        elif cama_zoning:
            zoning_code = cama_zoning
            zoning_district = _zoning_district(cama_zoning, None, False)
        else:
            zoning_code = None
            zoning_district = None
        if place == "CLEVELAND":
            situs_city = "Cleveland"
        elif place == "CHARLESTON":
            situs_city = "Charleston"
        else:
            situs_city = None
        price = num(attrs.get("PRICE"))
        if price is not None and price <= 0:
            price = None
        appraisal = num(attrs.get("APPRAISAL"))
        if appraisal is not None and appraisal <= 0:
            appraisal = None
        mail1 = clean(attrs.get("MAILADDR")) or clean(attrs.get("MAILLINE1"))
        gaps = [
            "Market value is the IMPACT appraisal. Assessed and taxable amounts are not on this layer. Opportunity Zone status is not assigned.",
            "No adopted future-land-use polygon is joined. The Cleveland urban growth boundary is growth context only.",
        ]
        if zone:
            gaps.append(
                "Zoning is a Cleveland Zoning Districts polygon (ZONECLASS), applied only because this parcel point is inside the Cleveland municipal boundary."
            )
        elif cama_zoning:
            gaps.append(
                "Zoning is the assessor CAMA ZONING label, not a polygon district. Unincorporated Bradley and Charleston have no public zoning FeatureServer."
            )
        else:
            gaps.append("No CAMA zoning label and no Cleveland zoning polygon on this parcel.")
        if citynum == "138" and not inside:
            gaps.append("CITYNUM 138 is outside the Cleveland municipal boundary, so Cleveland ZONECLASS was not applied.")
        feature = seed.empty_feature(
            fips=fips,
            county=county["name"],
            state=county["state"],
            markets=markets,
            parcel_id=link,
            acreage=acres,  # type: ignore[arg-type]
            geometry=geometry,
            center=center,
            source=spec["source"],
            owner=clean(attrs.get("OWNER")),
            situs=_situs(attrs),
            city=situs_city,
            zoning=zoning_code,
            dor=clean(attrs.get("LANDUSE")) or clean(attrs.get("PROPTYPE")),
            sale_price=price,
            sale_date=_parse_sale_date(attrs.get("SALEDATE")),
            market_value=appraisal,
            mail1=mail1,
            mail2=clean(attrs.get("MAILLINE2")),
            mail_city=clean(attrs.get("MAILCITY")),
            mail_state=clean(attrs.get("STATE")),
            mail_zip=seed.zip_str(attrs.get("ZIP")),
        )
        props = feature["properties"]
        props["ownerName2"] = clean(attrs.get("OWNER2"))
        props["jurisdictionCode"] = citynum
        props["jurisdictionPrefix"] = place
        props["zoningDistrict"] = zoning_district
        props["appraiserUrl"] = "https://assessment.cot.tn.gov/TPAD/Parcel/GIS?GISlink=" + urllib.parse.quote(link, safe="")
        props["dataGaps"] = gaps
        props["flu"] = None
        props["opportunityZone"] = None
        props["oz2Eligibility"] = None
        if props["countyFips"] != BRADLEY_FIPS or not str(props["id"]).startswith(f"{BRADLEY_FIPS}:"):
            raise RuntimeError("Bradley parcel id left the Census FIPS 47011 prefix")
        if place != "CLEVELAND" and zoning_district and not str(zoning_district).startswith("CAMA first-pass"):
            raise RuntimeError("Cleveland ZONECLASS was applied outside Cleveland")
        previous = by_id.get(link)
        if previous is None or (props["acreage"] or 0) > (previous["properties"]["acreage"] or 0):
            by_id[link] = feature
    if outside:
        raise RuntimeError(f"{outside} Bradley parcels fell outside the Tennessee box")
    features = list(by_id.values())
    features.sort(key=lambda row: row["properties"].get("acreage") or 0, reverse=True)
    if not features or not all(seed.in_band(feature["properties"].get("acreage")) for feature in features):
        raise RuntimeError("Bradley ingest emitted a parcel outside 5–150 acres")
    stats = {"cleveland": 0, "clevelandZone": 0, "charleston": 0, "unincorporated": 0, "citynumOutside": 0}
    for feature in features:
        props = feature["properties"]
        place = props.get("jurisdictionPrefix")
        if place == "CLEVELAND":
            stats["cleveland"] += 1
            if props.get("zoningDistrict") and not str(props["zoningDistrict"]).startswith("CAMA first-pass"):
                stats["clevelandZone"] += 1
        elif place == "CHARLESTON":
            stats["charleston"] += 1
        else:
            stats["unincorporated"] += 1
        if props.get("jurisdictionCode") == "138" and place != "CLEVELAND":
            stats["citynumOutside"] += 1
    dropped = source_count - len(features)
    gaps = [
        (
            f"City of Cleveland stays in Bradley County (Census FIPS 47011, Chattanooga). "
            f"{source_count} City of Cleveland GIS Parcels_Impact rows (JUR 006, parcel type 1, CALC_ACRE 5–150) "
            f"collapsed to {len(features)} GISLINK parcels at the latest TAXYR. "
            f"GEOID prefix is 47011, not Comptroller 006 and not 47107 (McMinn County)."
        ),
        (
            f"Cleveland Zoning Districts ZONECLASS is joined only inside the Cleveland municipal boundary "
            f"({stats['clevelandZone']} of {stats['cleveland']} Cleveland parcels). "
            f"Charleston ({stats['charleston']}) and unincorporated Bradley ({stats['unincorporated']}) "
            f"have no zoning polygon service; CAMA ZONING is a first-pass label only. "
            f"{stats['citynumOutside']} CITYNUM 138 parcels sit outside the city limits and did not receive ZONECLASS."
        ),
        "County zoning and Charleston zoning are PDF or municipal-code gaps. Future land use REST is a gap; the Cleveland urban growth boundary is not parcel FLU. Opportunity Zone flags are not invented by this ingest.",
        "Assessed and taxable values are left null. Market value is the IMPACT appraisal. Stacked CAMA cards that share a GISLINK keep the latest tax year, preferring the base 000 card.",
    ]
    path, lookup, tiles = seed.write_tiles(county, features)
    print(
        f"  kept {len(features)} cleveland={stats['cleveland']} zoned={stats['clevelandZone']} "
        f"charleston={stats['charleston']} unincorp={stats['unincorporated']}",
        flush=True,
    )
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
