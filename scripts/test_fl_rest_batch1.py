#!/usr/bin/env python3
"""Pure checks for FL-rest batch 1. No network."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fl_rest_batch1 import (  # noqa: E402
    COUNTY_BBOX,
    FIPS,
    FRANKLIN_ZONING_FIELDS,
    GEOPLAN_FIPS,
    GEOPLAN_LABEL,
    JEFFERSON_ZONING_FIELDS,
    MARKETS,
    MAX_ACRES,
    MIN_ACRES,
    PARTIAL_FIPS,
    SEARCH_ONLY_FIPS,
    SPECS,
    acres_from_sqft,
    appraiser_url,
    assert_out_fields,
    dedupe_attribute_rows,
    fdor_parcel_key,
    fdor_where,
    gis_viewer_url,
    gis_viewer_url_alt,
    in_band,
    in_county,
    prefer_fdor_owner,
)


def test_twenty_counties_and_acre_band() -> None:
    assert FIPS == (
        "12013",
        "12023",
        "12029",
        "12035",
        "12037",
        "12039",
        "12045",
        "12047",
        "12059",
        "12063",
        "12065",
        "12067",
        "12077",
        "12079",
        "12083",
        "12121",
        "12123",
        "12125",
        "12129",
        "12133",
    )
    assert len(FIPS) == 20
    assert MIN_ACRES == 5.0 and MAX_ACRES == 150.0
    assert in_band(5) and in_band(150) and not in_band(4.999) and not in_band(150.001)
    assert acres_from_sqft(217800) == 5
    assert acres_from_sqft(6534000) == 150
    assert in_county("12013", -85.045, 30.443)
    assert not in_county("12013", -84.8, 33.6)
    assert in_county("12133", -85.54, 30.78)
    assert not in_county("12125", -81.6, 34.7)


def test_markets_and_coverage() -> None:
    assert MARKETS["12083"] == "North-Central Florida"
    for fips in ("12029", "12039", "12065", "12079", "12123", "12129"):
        assert MARKETS[fips] == "Big Bend"
    for fips in ("12023", "12035", "12047", "12067", "12121", "12125"):
        assert MARKETS[fips] == "North Florida"
    for fips in ("12013", "12037", "12045", "12059", "12063", "12077", "12133"):
        assert MARKETS[fips] == "Panhandle Florida"
    assert set(PARTIAL_FIPS) == {
        "12029",
        "12037",
        "12045",
        "12047",
        "12059",
        "12067",
        "12079",
        "12121",
        "12123",
        "12125",
    }
    for fips in FIPS:
        spec = SPECS[fips]
        assert spec["coverage"] == ("partial" if fips in PARTIAL_FIPS else "complete-gte-5ac")
        where = spec["parcels"]["where"]
        assert (">=5" in where and "<=150" in where) or (">=217800" in where and "<=6534000" in where)
        assert "/query" in spec["url"]
        assert "CO_NO=" not in spec["parcels"]["where"]


def test_deep_links_viewers_and_search_pages() -> None:
    assert set(SEARCH_ONLY_FIPS) == {"12039", "12079", "12083"}
    gadsden = appraiser_url("12039", "123")
    assert "GadsdenCountyFL" in gadsden and "KeyValue=" not in gadsden and "123" not in gadsden
    madison = appraiser_url("12079", "ABC")
    assert "MadisonCountyFL" in madison and "KeyValue=" not in madison
    marion = appraiser_url("12083", "34801-001-00")
    assert marion == "https://www.pa.marion.fl.us/PropertySearch.aspx"
    wakulla = appraiser_url("12129", "12-5S-03W-063-00808-000")
    assert "KeyValue=12-5S-03W-063-00808-000" in wakulla
    columbia = appraiser_url("12023", "26-5S-17-09398-000")
    assert columbia.endswith("ParcelNo=26-5S-17-09398-000")
    union = appraiser_url("12125", "12-34")
    assert "pin=12-34" in union
    for fips in FIPS:
        viewer = gis_viewer_url(fips)
        assert "/MapServer/" not in viewer and "/FeatureServer/" not in viewer and not viewer.endswith("/query")
        alt = gis_viewer_url_alt(fips)
        if alt:
            assert "/query" not in alt


def test_jefferson_pii_gadsden_owner_and_fdor_key() -> None:
    assert JEFFERSON_ZONING_FIELDS == ["parcelid", "Zoning"]
    assert "OwnerPhone" not in FRANKLIN_ZONING_FIELDS and "OwnerEmail" not in FRANKLIN_ZONING_FIELDS
    for spec in SPECS.values():
        assert_out_fields(spec["parcels"]["fields"])
        for overlay in spec["overlays"]:
            if overlay.get("fields"):
                assert_out_fields(overlay["fields"])
    try:
        assert_out_fields(["parcelid", "OwnerPhone"])
    except RuntimeError:
        pass
    else:
        raise AssertionError("OwnerPhone was accepted")
    owner, conflict = prefer_fdor_owner("SMITH JOHN", "JONES MARY")
    assert owner == "JONES MARY" and conflict
    same, same_conflict = prefer_fdor_owner("SMITH, JOHN", "SMITH JOHN")
    assert same == "SMITH JOHN" and not same_conflict
    blank, blank_conflict = prefer_fdor_owner("SMITH JOHN", None)
    assert blank == "SMITH JOHN" and not blank_conflict
    assert fdor_parcel_key("12129", "12-5S-03W-063-00808-000") == "125S03W06300808000"
    assert fdor_parcel_key("12013", "223S10000000040000") == "223S10000000040000"
    where = fdor_where(["A", "B"])
    assert where.startswith("PARCEL_ID IN (") and "CO_NO=" not in where
    collapsed = dedupe_attribute_rows(
        [{"parcelid": "1", "Zoning": "AG"}] * 14 + [{"parcelid": "1", "Zoning": "RES"}],
        "parcelid",
        "Zoning",
    )
    assert collapsed == {"1": "AG"}
    for fips in GEOPLAN_FIPS:
        assert GEOPLAN_LABEL in SPECS[fips]["featureGaps"]
        assert SPECS[fips]["coverage"] == "partial"
    joined = " ".join(" ".join(SPECS[fips]["gaps"]) for fips in FIPS)
    assert "Opportunity Zone" not in joined
    assert "school" not in joined.lower()
    assert "base flood" not in joined.lower()
    script = Path(__file__).with_name("fl_rest_batch1.py").read_text()
    assert 'method="POST"' not in script and "method='POST'" not in script
    assert set(COUNTY_BBOX) == set(FIPS)


if __name__ == "__main__":
    test_twenty_counties_and_acre_band()
    test_markets_and_coverage()
    test_deep_links_viewers_and_search_pages()
    test_jefferson_pii_gadsden_owner_and_fdor_key()
    print("fl-rest batch 1 guards ok")
