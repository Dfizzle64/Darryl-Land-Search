#!/usr/bin/env python3
"""City-limit join rules. No network."""

from __future__ import annotations

import unittest

import join_fl_muni_overlays as muni


def square(lon: float, lat: float, size: float, props: dict | None = None) -> dict:
    ring = [
        [lon, lat],
        [lon + size, lat],
        [lon + size, lat + size],
        [lon, lat + size],
        [lon, lat],
    ]
    feature = muni.prepare_feature({"type": "Polygon", "coordinates": [ring]}, props or {})
    assert feature is not None
    return feature


def city(prefix: str, limits: list[dict], zoning: list[dict], flu: list[dict], code: str = "ZoningCode", flu_code: str = "FLUCode") -> dict:
    return {
        "id": prefix.lower(),
        "name": prefix,
        "prefix": prefix,
        "rejected": None,
        "limitsIndex": muni.index_features(limits),
        "zoningIndex": muni.index_features(zoning),
        "fluIndex": muni.index_features(flu),
        "zoning": {"code": code, "label": code, "url": "https://example.test/zoning/query"},
        "flu": {"code": flu_code, "label": flu_code, "url": "https://example.test/flu/query"},
    }


class JoinRules(unittest.TestCase):
    def test_edgewood_texas_is_outside_florida(self) -> None:
        self.assertTrue(muni.is_edgewood_tx(-96.65, 32.70))
        self.assertFalse(muni.in_florida(-96.65, 32.70))
        self.assertTrue(muni.in_florida(-81.27, 28.80))
        self.assertFalse(muni.in_florida(-78.42, 35.37))  # Bonita, North Carolina
        self.assertFalse(muni.in_florida(-82.36, 34.75))  # Fort Myers situs in South Carolina

    def test_rejects_a_layer_centered_on_edgewood_texas(self) -> None:
        feature = square(-96.70, 32.60, 0.05, {"ZoningCode": "R-1"})
        reason = muni.layer_rejection([feature], (-96.68, 32.62), "Edgewood zoning", True)
        self.assertIsNotNone(reason)
        self.assertIn("Edgewood", reason or "")

    def test_accepts_a_florida_city_polygon(self) -> None:
        feature = square(-81.30, 28.78, 0.08, {"ZONECODE": "SR1"})
        reason = muni.layer_rejection([feature], (-81.27, 28.80), "Sanford limits", True)
        self.assertIsNone(reason)

    def test_stamps_inside_city_and_leaves_outside_null(self) -> None:
        limits = square(-81.30, 28.78, 0.08)
        zoning = square(-81.30, 28.78, 0.04, {"ZoningCode": "R-1 SINGLE FAMILY MEDIUM"})
        flu = square(-81.30, 28.78, 0.08, {"FLUCode": "LDR"})
        spec = city("SAN", [limits], [zoning], [flu])
        inside = {
            "type": "Feature",
            "properties": {
                "state": "Florida",
                "centroid": [-81.29, 28.79],
                "zoningCode": None,
                "zoningDistrict": None,
                "flu": None,
                "countyFips": "12117",
            },
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        }
        outside = {
            "type": "Feature",
            "properties": {
                "state": "Florida",
                "centroid": [-81.10, 28.79],
                "zoningCode": None,
                "zoningDistrict": None,
                "flu": None,
            },
        }
        self.assertEqual(muni.join_feature(inside, [spec]), "san")
        self.assertEqual(inside["properties"]["zoningCode"], "R-1")
        self.assertEqual(inside["properties"]["flu"]["code"], "LDR")
        self.assertEqual(inside["properties"]["flu"]["jurisdiction"], "SAN")
        self.assertIsNone(muni.join_feature(outside, [spec]))
        self.assertIsNone(outside["properties"]["zoningCode"])
        self.assertIsNone(outside["properties"]["flu"])

    def test_city_layer_replaces_a_county_stub_inside_the_city(self) -> None:
        limits = square(-81.80, 28.52, 0.08)
        zoning = square(-81.80, 28.52, 0.08, {"ZoningCode": "PUD PLANNED UNIT DEVELOPMENT"})
        flu = square(-81.80, 28.52, 0.08, {"FLUCode": "Commercial"})
        spec = city("CLM", [limits], [zoning], [flu])
        feature = {
            "type": "Feature",
            "properties": {
                "state": "Florida",
                "centroid": [-81.77, 28.55],
                "zoningCode": "City",
                "zoningDistrict": "City",
                "flu": {"code": "City", "label": "City", "jurisdiction": "ORG", "source": "county"},
            },
        }
        self.assertEqual(muni.join_feature(feature, [spec]), "clm")
        self.assertEqual(feature["properties"]["zoningCode"], "PUD")
        self.assertEqual(feature["properties"]["flu"]["code"], "Commercial")
        self.assertNotEqual(feature["properties"]["flu"]["jurisdiction"], "ORG")

    def test_miss_inside_the_city_does_not_invent_a_code(self) -> None:
        limits = square(-81.66, 28.78, 0.08)
        zoning = square(-81.66, 28.78, 0.01, {"ZoningCode": "R-2"})
        spec = city("MTD", [limits], [zoning], [])
        feature = {
            "type": "Feature",
            "properties": {
                "state": "Florida",
                "centroid": [-81.60, 28.82],
                "zoningCode": None,
                "flu": None,
            },
        }
        self.assertEqual(muni.join_feature(feature, [spec]), "mtd")
        self.assertIsNone(feature["properties"]["zoningCode"])
        self.assertIsNone(feature["properties"]["flu"])
        self.assertEqual(feature["properties"]["jurisdictionPrefix"], "MTD")

    def test_smallest_polygon_wins(self) -> None:
        big = square(-81.42, 28.27, 0.08, {"ZoningCode": "AG"})
        small = square(-81.41, 28.28, 0.02, {"ZoningCode": "CBD"})
        limits = square(-81.42, 28.27, 0.08)
        spec = city("KIS", [limits], [big, small], [])
        feature = {
            "type": "Feature",
            "properties": {"state": "Florida", "centroid": [-81.405, 28.285], "zoningCode": None, "flu": None},
        }
        muni.join_feature(feature, [spec])
        self.assertEqual(feature["properties"]["zoningCode"], "CBD")

    def test_pensacola_is_not_one_of_the_seven(self) -> None:
        ids = {city["id"] for city in muni.CITIES}
        self.assertEqual(
            ids,
            {"sanford", "kissimmee", "clermont", "mount-dora", "sanibel", "fort-myers", "bonita-springs"},
        )
        self.assertNotIn("pensacola", ids)
        self.assertNotIn("edgewood", ids)


if __name__ == "__main__":
    unittest.main()
