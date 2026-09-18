#!/usr/bin/env python3
"""Refresh zoning / FLU coverage notes from public GIS + the local knowledge files.

This does not scrape Municode and does not call an LLM. It:
  1. Lists unique OCPA jurisdiction+district codes in the parcel fixture
  2. Checks them against data/zoning-config.json
  3. Pulls unique FLU codes from Orange County and Orlando open-data layers
  4. Checks them against data/flu-config.json
  5. Writes data/fixtures/zoning-coverage.json for the in-app knowledge panel

Re-research of use tables is a documented human/agent pass: edit the JSON
knowledge files, then re-run this script.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARCELS = ROOT / "data" / "fixtures" / "parcels.geojson"
ZONING = ROOT / "data" / "zoning-config.json"
FLU = ROOT / "data" / "flu-config.json"
OUT = ROOT / "data" / "fixtures" / "zoning-coverage.json"

OC_FLU_URL = "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/21/query"
ORL_FLU_URL = "https://ocgis4.ocfl.net/arcgis/rest/services/AGOL_Open_Data/MapServer/83/query"


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


def distinct_field(url: str, field: str) -> list[str]:
    data = fetch_json(
        url,
        {
            "where": "1=1",
            "outFields": field,
            "returnDistinctValues": "true",
            "returnGeometry": "false",
            "f": "json",
        },
    )
    values = []
    for feat in data.get("features") or []:
        raw = ((feat.get("attributes") or {}).get(field) or "")
        text = str(raw).strip()
        if text:
            values.append(text)
    return sorted(set(values))


def token_matches(token: str, aliases: list[str], district: str) -> bool:
    d = district.upper()
    names = [token.upper(), *[a.upper() for a in aliases]]
    for name in names:
        if d == name:
            return True
        if d.startswith(name) and (len(d) == len(name) or not d[len(name) : len(name) + 1].isdigit()):
            return True
        if d.endswith(" " + name) or d.endswith("-" + name):
            return True
    return False


def main() -> None:
    parcels = json.loads(PARCELS.read_text())
    zoning = json.loads(ZONING.read_text())
    flu = json.loads(FLU.read_text())

    observed: Counter[tuple[str, str]] = Counter()
    for feat in parcels.get("features") or []:
        props = feat.get("properties") or {}
        prefix = (props.get("jurisdictionPrefix") or "?")
        district = (props.get("zoningDistrict") or "?")
        observed[(prefix, district)] += 1

    pd_tokens = zoning.get("plannedDevelopmentTokens") or []
    uncovered = []
    covered = []
    for (prefix, district), count in sorted(observed.items(), key=lambda item: (-item[1], item[0])):
        juris = next((j for j in zoning.get("jurisdictions") or [] if j.get("code") == prefix), None)
        hit = None
        if juris:
            for token in juris.get("districts") or []:
                if token_matches(token.get("token", ""), token.get("aliases") or [], district):
                    hit = {"kind": "district", "status": token.get("status"), "token": token.get("token")}
                    break
        if not hit:
            for token in pd_tokens:
                if token_matches(token.get("token", ""), token.get("aliases") or [], district):
                    hit = {"kind": "planned-development", "status": "maybe", "token": token.get("token")}
                    break
        row = {"jurisdiction": prefix, "district": district, "parcelCount": count, "match": hit}
        if hit:
            covered.append(row)
        else:
            uncovered.append(row)

    oc_flu_codes: list[str] = []
    orl_flu_codes: list[str] = []
    flu_error = None
    try:
        oc_flu_codes = distinct_field(OC_FLU_URL, "LAND_USE")
        orl_flu_codes = distinct_field(ORL_FLU_URL, "LANDUSETYPE")
    except Exception as exc:  # noqa: BLE001
        flu_error = str(exc)

    flu_known = {(c.get("jurisdiction"), c.get("code")) for c in flu.get("categories") or []}
    flu_uncovered = []

    def flu_is_known(jurisdiction: str, code: str) -> bool:
        if (jurisdiction, code) in flu_known:
            return True
        base = code.split("/", 1)[0]
        return (jurisdiction, base) in flu_known

    for code in oc_flu_codes:
        if not flu_is_known("ORG", code):
            flu_uncovered.append({"jurisdiction": "ORG", "code": code})
    for code in orl_flu_codes:
        if not flu_is_known("ORL", code):
            flu_uncovered.append({"jurisdiction": "ORL", "code": code})

    report = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "zoningConfigUpdatedAt": zoning.get("updatedAt"),
        "fluConfigUpdatedAt": flu.get("updatedAt"),
        "jurisdictionsInConfig": [
            {
                "code": j.get("code"),
                "name": j.get("name"),
                "coverage": j.get("coverage"),
                "districtCount": len(j.get("districts") or []),
            }
            for j in zoning.get("jurisdictions") or []
        ],
        "observedDistricts": len(observed),
        "coveredObservedDistricts": len(covered),
        "uncoveredObservedDistricts": uncovered,
        "fluGisCodes": {"orangeCounty": oc_flu_codes, "orlando": orl_flu_codes, "error": flu_error},
        "fluUncoveredGisCodes": flu_uncovered,
        "researchWorkflow": [
            "Edit data/zoning-config.json (per-jurisdiction districts, citations in why).",
            "Edit data/flu-config.json (GIS code → MF-supportive flag).",
            "Run npm run seed:flu to re-join FLU polygons onto parcels.",
            "Run npm run seed:zoning to refresh this coverage report.",
            "Do not call an LLM from the browser; this is an offline/scripted maintain pass.",
        ],
    }
    OUT.write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "observed": len(observed),
                "uncoveredZoning": len(uncovered),
                "fluUncovered": len(flu_uncovered),
                "out": str(OUT),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
