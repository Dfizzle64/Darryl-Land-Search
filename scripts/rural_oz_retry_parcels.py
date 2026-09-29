#!/usr/bin/env python3
"""Retry rural Opportunity Zone parcels that earlier batches could not pull.

South Carolina Sumter (45085) uses the batch 2 loader and the card FeatureServer.
Georgia Butts (13035), Franklin (13119), Grady (13131), and Habersham (13137)
use the card Schneider WFS. Those hosts are queried with 10-feature pages,
returnIdsOnly, and an OBJECTID window, with backoff. Habersham's historical
Roktech MapServer on the card is tried once. A county that still does not
answer is skipped. TLS verification stays on.

Does not add a market shelf. Does not store an Opportunity Zone status, a
school grade, or a base flood elevation. Household income stays the ACS
B19013_001E join. Owner phone and email are not ingested.
"""

from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import sc_rural_oz_batch2_parcels as sc2
import seed_market_parcels as seed

ROOT = seed.ROOT
REPORT_PATH = ROOT / "data" / "fixtures" / "market-parcels" / "rural-oz-retry-result.json"
CTX = ssl.create_default_context()
UA = {"User-Agent": "darryl-land-search/market-parcels"}

GA = {
    "13035": {
        "name": "Butts",
        "url": "https://wfs.schneidercorp.com/arcgis/rest/services/ButtsCountyGA_WFS/MapServer/0",
        "alts": [],
    },
    "13119": {
        "name": "Franklin",
        "url": "https://wfs.schneidercorp.com/arcgis/rest/services/FranklinCountyGA_WFS/MapServer/0",
        "alts": [],
    },
    "13131": {
        "name": "Grady",
        "url": "https://wfs.schneidercorp.com/arcgis/rest/services/GradyCountyGA_WFS/MapServer/0",
        "alts": [],
    },
    "13137": {
        "name": "Habersham",
        "url": "https://wfs.schneidercorp.com/arcgis/rest/services/HabershamCountyGA_WFS/MapServer/4",
        "alts": [
            "https://arcgis4.roktech.net/arcgis/rest/services/habersham/habersham_rokmaps/MapServer/8",
            "https://arcgis5.roktech.net/arcgis/rest/services/habersham/habersham_rokmaps/MapServer/8",
        ],
    },
}


def fetch(url: str, timeout: int = 40) -> tuple[bool, str]:
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
            return True, resp.read()[:500].decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def query(base: str, params: dict, timeout: int = 45) -> tuple[bool, str]:
    url = base.rstrip("/") + "/query?" + urllib.parse.urlencode(params)
    return fetch(url, timeout)


def alive(body: str) -> bool:
    return "features" in body or '"objectIds"' in body or '"fields"' in body and "server machines" not in body


def probe_county(spec: dict) -> str | None:
    """Return an error string, or None when a small public query returns features."""
    errors: list[str] = []
    base = spec["url"]
    checks = [
        ("meta", lambda: fetch(base + "?f=json", 30)),
        (
            "page-10",
            lambda: query(
                base,
                {
                    "where": "1=1",
                    "outFields": "*",
                    "returnGeometry": "false",
                    "resultRecordCount": "10",
                    "f": "json",
                },
                50,
            ),
        ),
        ("returnIdsOnly", lambda: query(base, {"where": "1=1", "returnIdsOnly": "true", "f": "json"}, 50)),
        (
            "objectid-1-25",
            lambda: query(
                base,
                {"where": "OBJECTID>=1 AND OBJECTID<=25", "outFields": "*", "returnGeometry": "false", "f": "json"},
                50,
            ),
        ),
    ]
    for _round, delay in enumerate((0, 20, 40, 60, 90, 120)):
        if delay:
            time.sleep(delay)
        for label, call in checks:
            ok, body = call()
            snippet = body.replace("\n", " ")[:240]
            if ok and alive(body):
                return None
            errors.append(f"{label}: {snippet}")
    for alt in spec["alts"]:
        ok, body = fetch(alt + "?f=json", 25)
        errors.append(f"{alt}: {body.replace(chr(10), ' ')[:240]}")
    return "; ".join(errors[-6:])


def main() -> None:
    if "--probe-ga" not in sys.argv:
        print("Pass --probe-ga to retry Schneider. Sumter is loaded by scripts/sc_rural_oz_batch2_parcels.py.")
        print(f"Report: {REPORT_PATH.relative_to(ROOT)}")
        return
    sc2.install_patches()
    skipped = []
    for fips, spec in GA.items():
        print(f"PROBE {spec['name']} {fips}", flush=True)
        reason = probe_county(spec)
        if reason is None:
            print(f"  {spec['name']} answered; pull it with the Georgia batch loader before writing over the gap.")
            continue
        print(f"  SKIP {spec['name']}: {reason[:180]}", flush=True)
        skipped.append({"fips": fips, "name": spec["name"], "queryUrl": spec["url"], "reason": reason})
    if REPORT_PATH.exists() and skipped:
        report = json.loads(REPORT_PATH.read_text())
        report["skipped"] = skipped
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(skipped, indent=2)[:2000])


if __name__ == "__main__":
    sys.exit(main())
