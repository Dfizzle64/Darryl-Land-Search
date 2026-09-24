#!/usr/bin/env python3
"""Pure checks for Treasure Coast source guards. No network."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from treasure_coast_parcels import (  # noqa: E402
    FORT_PIERCE_PROJECTS_LAYER,
    FORT_PIERCE_ZONING_LAYER,
    MARTIN_ZONE_STUBS,
    REJECT_NOTES,
    SPECS,
    foreign_extent_reason,
    fort_pierce_layer_role,
    in_band,
    martin_roll_is_thin_clip,
    parcel_pin,
    place_name,
    point_in_county,
    treasure_coast_spec,
    usable_code,
)


def test_rejects_tuscaloosa_ocoee_and_australia() -> None:
    assert "Tuscaloosa" in (foreign_extent_reason((-87.7, 33.1, -87.3, 33.4)) or "")
    assert "Ocoee" in (foreign_extent_reason((-81.58, 28.52, -81.50, 28.60)) or "")
    assert "Australia" in (foreign_extent_reason((144.8, -38.0, 145.2, -37.6)) or "")
    assert foreign_extent_reason((-80.88, 27.56, -80.32, 27.86)) is None
    assert foreign_extent_reason((-81.21, 27.12, -80.68, 27.64)) is None
    assert foreign_extent_reason((-80.99, 27.82, -80.44, 28.79)) is None


def test_martin_thin_clip_and_ocoee_not_in_county_bbox() -> None:
    assert martin_roll_is_thin_clip((-80.57, 27.01, -80.40, 27.07)) is True
    assert martin_roll_is_thin_clip((-80.86, 26.95, -79.92, 27.27)) is False
    assert point_in_county("12093", -81.54, 28.57) is False
    assert point_in_county("12093", -80.83, 27.24) is True


def test_fort_pierce_projects_are_not_zoning() -> None:
    assert FORT_PIERCE_PROJECTS_LAYER == 0
    assert FORT_PIERCE_ZONING_LAYER == 7
    assert fort_pierce_layer_role(0, "Current Project Development") == "reject-projects"
    assert fort_pierce_layer_role(7, "Zoning") == "zoning"
    assert fort_pierce_layer_role(9, "Opportunity Zones") == "reject-not-designation"
    assert "/FeatureServer/7/query" in (
        "https://services1.arcgis.com/oDRzuf2MGmdEHAbQ/arcgis/rest/services/Zoning/FeatureServer/7/query"
    )


def test_stubs_municipalities_and_acre_band() -> None:
    assert usable_code("STUART", MARTIN_ZONE_STUBS) is None
    assert usable_code("RS-3", MARTIN_ZONE_STUBS) == "RS-3"
    assert place_name("St. Lucie County") is None
    assert place_name("City of Stuart") == "Stuart"
    assert place_name("MELBOURNE") == "Melbourne"
    assert parcel_pin("31370000001183900001.0") == "31370000001183900001"
    assert in_band(5) and in_band(150) and not in_band(4.9) and not in_band(150.1)
    for fips, note in REJECT_NOTES.items():
        spec = treasure_coast_spec(fips)
        assert spec["kind"] == "treasure-coast"
        assert "not designated" in spec["gaps"][1].lower() or "not designated" in " ".join(spec["gaps"]).lower()
        assert note in spec["gaps"][0]
        assert fips in SPECS


if __name__ == "__main__":
    test_rejects_tuscaloosa_ocoee_and_australia()
    test_martin_thin_clip_and_ocoee_not_in_county_bbox()
    test_fort_pierce_projects_are_not_zoning()
    test_stubs_municipalities_and_acre_band()
    print("treasure coast guards ok")
