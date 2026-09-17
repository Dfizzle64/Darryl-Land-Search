#!/usr/bin/env python3
"""Join public Future Land Use polygons onto the parcel fixture.

Sources (no paid vendors):
  - Orange County Open Data Future Land Use (AGOL_Open_Data / 21)
  - City of Orlando Future Land Use (AGOL_Open_Data / 83)

County layer 21 is unincorporated + annexed parcels that have not yet received
a city FLU. Code "City" means "inside a municipality" and is not a designation.
Orlando parcels are joined to layer 83 by centroid. Other municipalities have
no public FLU layer in this adapter — those parcels stay unknown.

Usage:
  python3 scripts/join_flu.py
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARCELS = ROOT / "data" / "fixtures" / "parcels.geojson"
META = ROOT / "data" / "fixtures" / "meta.json"
FLU_LOOKUP = ROOT / "data" / "fixtures" / "flu-lookup.json"

OC_FLU_URL = "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21/query"
ORL_FLU_URL = "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83/query"

OC_LABELS = {
    "R": "Rural / Agricultural",
    "1/1": "Rural Settlement 1/1",
    "1/2": "Rural Settlement 1/2",
    "1/5": "Rural Settlement 1/5",
    "LD": "Low Density Residential",
    "LM": "Low-Medium Density Residential",
    "MD": "Medium Density Residential",
    "HD": "High Density Residential",
    "TND": "Traditional Neighborhood",
    "NAC": "Neighborhood Activity Corridor",
    "NC": "Neighborhood Center",
    "NR": "Neighborhood Residential",
    "ACR": "Activity Center Residential",
    "ACMU": "Activity Center Mixed Use",
    "CVC": "Community Village Center",
    "V": "Village (Horizon West)",
    "O": "Office",
    "C": "Commercial",
    "I": "Industrial",
    "IN": "Institutional",
    "E": "Education",
    "P/R": "Parks / Recreation",
    "PRES": "Preservation",
    "PD": "Planned Development",
    "WB": "Water Body",
    "City": "Municipal (county placeholder)",
}

ORL_LABELS = {
    "RES-LOW": "Residential, Low Intensity",
    "RES-MED": "Residential, Medium Intensity",
    "RES-HIGH": "Residential, High Intensity",
    "MU-ND": "Mixed Use / Neighborhood Development",
    "MUC-MED": "Mixed Use Corridor, Medium Intensity",
    "MUC-HIGH": "Mixed Use Corridor, High Intensity",
    "NEIGH-AC": "Neighborhood Activity Center",
    "COMM-AC": "Community Activity Center",
    "UR-AC": "Urban Activity Center",
    "MET-AC": "Metropolitan Activity Center",
    "DT-AC": "Downtown Activity Center",
    "URB-VIL": "Urban Village",
    "OFFICE-LOW": "Office, Low Intensity",
    "OFFICE-MED": "Office, Medium Intensity",
    "OFFICE-HIGH": "Office, High Intensity",
    "INDUST": "Industrial",
    "CONSERV": "Conservation",
    "PUB-REC-INST": "Public / Recreational and Institutional",
    "AIR-HIGH": "Airport Support, High Intensity",
    "AIR-MED": "Airport Support, Medium Intensity",
}


def fetch_json(url: str, params: dict | None = None, timeout: int = 40, retries: int = 3) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "orange-county-mf-pilot/0.2"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def point_query(url: str, lon: float, lat: float, out_fields: str) -> list[dict]:
    geom = json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}})
    data = fetch_json(
        url,
        {
            "geometry": geom,
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": out_fields,
            "returnGeometry": "false",
            "f": "json",
        },
    )
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("features") or []


def oc_flu(attrs: dict) -> dict | None:
    code = (attrs.get("LAND_USE") or "").strip() or None
    if not code:
        return None
    label = (attrs.get("LABEL") or "").strip() or OC_LABELS.get(code) or code
    return {
        "code": code,
        "label": label,
        "jurisdiction": "ORG",
        "source": "ocfl-agol-21",
    }


def orl_flu(attrs: dict) -> dict | None:
    code = (attrs.get("LANDUSETYPE") or "").strip() or None
    if not code:
        return None
    return {
        "code": code,
        "label": ORL_LABELS.get(code, code),
        "jurisdiction": "ORL",
        "source": "ocfl-agol-83",
    }


def join_one(feature: dict) -> tuple[str, dict | None, str | None]:
    props = feature.get("properties") or {}
    pid = props.get("id") or ""
    centroid = props.get("centroid") or []
    if len(centroid) != 2:
        return pid, None, "missing-centroid"
    lon, lat = float(centroid[0]), float(centroid[1])
    prefix = (props.get("jurisdictionPrefix") or props.get("jurisdictionCode") or "").upper()
    try:
        orl = None
        if prefix == "ORL":
            hits = point_query(ORL_FLU_URL, lon, lat, "LANDUSETYPE")
            if hits:
                orl = orl_flu((hits[0] or {}).get("attributes") or {})
        oc = None
        hits = point_query(OC_FLU_URL, lon, lat, "LAND_USE,LABEL")
        if hits:
            oc = oc_flu((hits[0] or {}).get("attributes") or {})
        if orl:
            return pid, orl, None
        if oc and oc.get("code") not in {None, "City"}:
            return pid, oc, None
        if oc:
            return pid, None, "county-city-placeholder"
        return pid, None, "no-hit"
    except Exception as exc:  # noqa: BLE001
        return pid, None, f"error:{exc}"


def main() -> None:
    collection = json.loads(PARCELS.read_text())
    features = collection.get("features") or []
    print(f"Joining FLU onto {len(features)} parcels")
    lookup: dict[str, dict | None] = {}
    gaps: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(join_one, feat) for feat in features]
        done = 0
        for fut in as_completed(futures):
            pid, flu, gap = fut.result()
            lookup[pid] = flu
            if gap:
                gaps[gap] = gaps.get(gap, 0) + 1
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(features)}")

    joined = 0
    for feat in features:
        pid = (feat.get("properties") or {}).get("id")
        flu = lookup.get(pid)
        feat.setdefault("properties", {})["flu"] = flu
        if flu:
            joined += 1

    PARCELS.write_text(json.dumps(collection, separators=(",", ":")))
    FLU_LOOKUP.write_text(
        json.dumps(
            {
                "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "parcelCount": len(features),
                "joinedCount": joined,
                "gaps": gaps,
                "sources": {"orangeCounty": OC_FLU_URL.replace("/query", ""), "orlando": ORL_FLU_URL.replace("/query", "")},
                "byParcel": lookup,
            },
            indent=2,
        )
    )
    if META.exists():
        meta = json.loads(META.read_text())
        meta["fluJoinedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        meta["fluJoinedCount"] = joined
        meta["fluGaps"] = gaps
        sources = meta.get("sources") or {}
        sources["fluOrangeCounty"] = OC_FLU_URL.replace("/query", "")
        sources["fluOrlando"] = ORL_FLU_URL.replace("/query", "")
        meta["sources"] = sources
        notes = meta.get("notes") or []
        flu_note = "FLU is joined by parcel centroid to OC layer 21 and Orlando layer 83. Other municipal FLU is a known gap."
        if flu_note not in notes:
            notes.append(flu_note)
        meta["notes"] = notes
        META.write_text(json.dumps(meta, indent=2))
    print(json.dumps({"joined": joined, "total": len(features), "gaps": gaps}, indent=2))


if __name__ == "__main__":
    main()
