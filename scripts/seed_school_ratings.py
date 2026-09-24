#!/usr/bin/env python3
"""Build the public school-rating fixture.

Florida letter grades come from the Florida Department of Education Know Your
Schools endpoint that powers https://edudata.fldoe.org/ReportCards/Schools.html
(the same 2025-26 grades published as SchoolGrades26.xlsx). North Carolina
letter grades come from the DPI School Report Card researcher file
(rcd_acc_spg1, subgroup ALL) joined to NCES CCD school IDs.

The workbook on fldoe.org blocks many automated clients. This script uses the
public report-card API instead of inventing grades. Other states stay off this
file; the app links their official report-card sites and says the rating is
not in the extract.

Refresh:
  python3 scripts/seed_school_ratings.py
  # or, if you already downloaded the sources:
  python3 scripts/seed_school_ratings.py --ccd /tmp/ccd.zip --nc-xlsx /tmp/spg1.xlsx
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import threading
import time
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fixtures" / "screening" / "school-ratings.json"

FL_LIST = "https://edudata.fldoe.org/api/Dropdown/GetSchoolList/"
FL_BASE = "https://edudata.fldoe.org/api/RCContent/GetBase/{}"
FL_PAGE = "https://edudata.fldoe.org/ReportCards/Schools.html?district={district}&school={school}"
NC_ZIP = "https://www.dpi.nc.gov/src-data-set-2024-251-2/open"
NC_MEMBER = "src_datasets_2425_1_of_2/rcd_acc_spg1.xlsx"
CCD_ZIP = "https://nces.ed.gov/ccd/data/zip/ccd_sch_029_2324_w_1a_073124.zip"
CCD_NAME = "ccd_sch_029_2324_w_1a_073124.csv"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
}
AJAX = {
    **UA,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://edudata.fldoe.org/ReportCards/Schools.html",
}
CACHE = Path("/tmp/darryl-fl-grades.jsonl")


def fetch(url: str, headers: dict[str, str], timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def florida_ids() -> list[str]:
    payload = json.loads(fetch(FL_LIST, AJAX))
    ids: list[str] = []
    for group in payload.get("results") or []:
        for child in group.get("children") or []:
            school_id = str(child.get("id") or "").strip()
            if school_id:
                ids.append(school_id)
    return ids


def florida_headers(school_id: str) -> dict[str, str]:
    district = school_id[:-4] if len(school_id) > 4 else school_id
    school = school_id[-4:] if len(school_id) > 4 else school_id
    return {
        **AJAX,
        "Referer": FL_PAGE.format(district=district, school=school),
    }


def florida_school(school_id: str) -> dict | None:
    """One report card. HTTP 400 can be a real Invalid RCID or a rate limit, so retry it."""
    last_error: Exception | None = None
    for attempt in range(6):
        try:
            raw = fetch(FL_BASE.format(school_id), florida_headers(school_id), timeout=40)
            text = raw.decode("utf-8", "replace").strip()
            if text in {'"Invalid Path"', "Invalid Path"}:
                return None
            if "Invalid RCID" in text and attempt < 5:
                time.sleep(1.2 + attempt)
                continue
            if text.startswith('"') and "Invalid RCID" in text:
                return None
            rows = json.loads(text)
            if isinstance(rows, dict):
                rows = [rows]
            if not rows:
                return None
            row = rows[0]
            lat = _float(row.get("LATITUDE"))
            lon = _float(row.get("LONGITUDE"))
            if lat is None or lon is None:
                return None
            grade = _rating(row.get("grade"))
            improvement = _rating(row.get("improvement_rating"))
            district = str(row.get("district_number") or "").strip()
            school = str(row.get("school_number") or "").strip()
            return {
                "id": school_id,
                "name": str(row.get("school_name_l") or row.get("school_name_s") or "").strip(),
                "grade": grade,
                "improvement": improvement if not grade else None,
                "city": str(row.get("PHYSICAL_CITY") or "").strip() or None,
                "level": str(row.get("school_type") or "").strip() or None,
                "district": district,
                "school": school,
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "reportCardUrl": FL_PAGE.format(district=district, school=school),
            }
        except Exception as error:  # noqa: BLE001 — retry transient DOE errors
            last_error = error
            time.sleep(1.5 + attempt * 0.8)
    print(f"skip {school_id}: {last_error}", file=sys.stderr)
    return None


def _float(value: object) -> float | None:
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return None
    if number == 0 or abs(number) > 180:
        return None
    return number


def _rating(value: object) -> str | None:
    text = str(value or "").strip().upper()
    if text in {"A", "B", "C", "D", "F", "I"}:
        return text
    # Florida alternative-school improvement ratings.
    aliases = {
        "COMMENDABLE": "Commendable",
        "MAINTAINING": "Maintaining",
        "UNSATISFACTORY": "Unsatisfactory",
    }
    return aliases.get(text)


def nces_index(ccd_zip: Path) -> dict[tuple[str, int, int], str]:
    """Map (state, district number, school number) to a 12-digit NCES school id."""
    index: dict[tuple[str, int, int], str] = {}
    with zipfile.ZipFile(ccd_zip) as archive:
        with archive.open(CCD_NAME) as handle:
            reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8", newline=""))
            for row in reader:
                state = (row.get("ST") or "").strip()
                if state not in {"FL", "NC"}:
                    continue
                parts = (row.get("ST_SCHID") or "").split("-")
                if len(parts) != 3 or parts[0] != state:
                    continue
                if not parts[1].isdigit() or not parts[2].isdigit():
                    continue
                nces = (row.get("NCESSCH") or "").strip()
                if not nces.isdigit():
                    continue
                index[(state, int(parts[1]), int(parts[2]))] = nces.zfill(12)
    return index


NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def nc_grades(xlsx: Path) -> dict[str, str]:
    """agency_code (6-digit LEA+school) -> letter, subgroup ALL only."""
    with zipfile.ZipFile(xlsx) as workbook:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            for item in root.findall(f"{NS}si"):
                shared.append("".join((node.text or "") for node in item.findall(f".//{NS}t")))
        sheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))

    def cell_value(cell: ET.Element) -> str:
        node = cell.find(f"{NS}v")
        if node is None or node.text is None:
            return ""
        if cell.attrib.get("t") == "s":
            return shared[int(node.text)]
        return node.text

    def col_index(ref: str) -> int:
        letters = "".join(ch for ch in ref if ch.isalpha())
        index = 0
        for ch in letters:
            index = index * 26 + ord(ch) - 64
        return index - 1

    grades: dict[str, str] = {}
    header: dict[str, int] | None = None
    for row in sheet.findall(f"{NS}sheetData/{NS}row"):
        values: dict[int, str] = {}
        for cell in row.findall(f"{NS}c"):
            values[col_index(cell.attrib.get("r", "A1"))] = cell_value(cell)
        if header is None:
            header = {name: index for index, name in values.items()}
            continue
        assert header is not None
        subgroup = values.get(header.get("subgroup", -1), "")
        if subgroup != "ALL":
            continue
        code = values.get(header.get("agency_code", -1), "").strip()
        grade = values.get(header.get("spg_grade", -1), "").strip().upper()
        if code.isdigit() and len(code) == 6 and grade in {"A", "B", "C", "D", "F"}:
            grades[code] = grade
    return grades


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url}")
    dest.write_bytes(fetch(url, UA, timeout=180))


def ensure_nc_xlsx(path: Path | None) -> Path:
    if path and path.exists():
        return path
    cache = Path("/tmp/darryl-nc-src.zip")
    download(NC_ZIP, cache)
    extracted = Path("/tmp/darryl-rcd_acc_spg1.xlsx")
    if not extracted.exists():
        with zipfile.ZipFile(cache) as archive:
            extracted.write_bytes(archive.read(NC_MEMBER))
    return extracted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ccd", type=Path, default=None)
    parser.add_argument("--nc-xlsx", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    ccd = args.ccd or Path("/tmp/darryl-ccd.zip")
    download(CCD_ZIP, ccd)
    nc_xlsx = ensure_nc_xlsx(args.nc_xlsx)
    print("indexing NCES ids")
    nces = nces_index(ccd)
    print(f"NCES keys {len(nces)}")
    print("reading NC school performance grades")
    nc_by_code = nc_grades(nc_xlsx)
    print(f"NC grades {len(nc_by_code)}")

    nc_by_nces: dict[str, str] = {}
    for (state, district, school), nces_id in nces.items():
        if state != "NC":
            continue
        grade = nc_by_code.get(f"{district:03d}{school:03d}")
        if grade:
            nc_by_nces[nces_id] = grade
    print(f"NC grades joined to NCES {len(nc_by_nces)}")

    ids = florida_ids()
    print(f"Florida schools {len(ids)}")
    cached: dict[str, dict] = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("id"):
                cached[row["id"]] = row
        print(f"resuming Florida cache {len(cached)}")
    pending = [school_id for school_id in ids if school_id not in cached]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    write_lock = threading.Lock()

    def harvest(school_id: str) -> dict | None:
        time.sleep(0.35)
        row = florida_school(school_id)
        if row:
            with write_lock:
                with CACHE.open("a") as handle:
                    handle.write(json.dumps(row) + "\n")
        return row

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(harvest, school_id) for school_id in pending]
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(pending)} new")
            future.result()
    florida = []
    seen: set[str] = set()
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            school_id = row.get("id")
            if school_id and school_id not in seen:
                seen.add(school_id)
                florida.append(row)
    florida.sort(key=lambda row: row["id"])
    graded = 0
    for row in florida:
        district = row["district"]
        school = row["school"]
        if str(district).isdigit() and str(school).isdigit():
            row["district"] = f"{int(district):02d}"
            row["school"] = f"{int(school):04d}"
            row["reportCardUrl"] = FL_PAGE.format(district=row["district"], school=row["school"])
            row["nces"] = nces.get(("FL", int(district), int(school)))
        else:
            row["nces"] = None
        if row["grade"] or row["improvement"]:
            graded += 1
    print(f"Florida points {len(florida)} with a rating {graded}")

    payload = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "florida": {
            "year": "2025-26",
            "source": "Florida Department of Education school grades, via the public Know Your Schools report card (GetBase). Same release as SchoolGrades26.xlsx.",
            "sourceUrl": "https://edudata.fldoe.org/ReportCards/Schools.html",
            "workbookUrl": "https://www.fldoe.org/file/18534/SchoolGrades26.xlsx",
            "schools": florida,
        },
        "northCarolina": {
            "year": "2024-25",
            "source": "North Carolina Department of Public Instruction School Performance Grades (School Report Card researcher file, final letter grade, subgroup ALL).",
            "sourceUrl": "https://www.dpi.nc.gov/data-reports/school-report-cards/school-report-card-resources-researchers",
            "byNces": nc_by_nces,
        },
        "gaps": [
            "Georgia, South Carolina, Tennessee, and Alabama do not have a letter-grade extract in this fixture. The map still plots NCES public-school locations and links the state report card.",
            "A Florida school with no A–F grade and no improvement rating is plotted without a letter. That is an unpublished grade, not a zero.",
            "North Carolina schools that do not join an NCES id keep no grade rather than a guessed match.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
