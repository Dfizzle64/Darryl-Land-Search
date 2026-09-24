"""Unit checks for the Florida Heartland shelf. No network."""

from __future__ import annotations

import unittest

from heartland_parcels import (
    FIPS,
    SENTINELS,
    extent_outside_heartland,
    in_heartland,
    is_designation,
    parcel_keys,
    parse_date,
)


class HeartlandTests(unittest.TestCase):
    def test_acreage_band_is_inclusive_and_florida_only(self):
        self.assertTrue(in_heartland(-81.44, 27.50))  # Sebring
        self.assertTrue(in_heartland(-81.81, 27.55))  # Wauchula
        self.assertTrue(in_heartland(-81.09, 26.83))  # Moore Haven
        self.assertTrue(in_heartland(-81.44, 26.76))  # LaBelle
        self.assertTrue(in_heartland(-81.86, 27.22))  # Arcadia, Florida
        self.assertFalse(in_heartland(-95.05, 29.82))  # Highlands, Texas
        self.assertFalse(in_heartland(-97.50, 34.60))  # Hardee namesake, Oklahoma
        self.assertFalse(in_heartland(-94.97, 38.98))  # DeSoto, Kansas
        self.assertFalse(in_heartland(-82.20, 39.20))  # Glades namesake, Ohio
        self.assertEqual(FIPS, ("12055", "12049", "12043", "12051", "12027"))
        self.assertNotIn("28033", FIPS)

    def test_extent_rejects_namesakes(self):
        self.assertIsNone(extent_outside_heartland((-81.6, 27.0, -80.9, 27.7)))
        self.assertIsNotNone(extent_outside_heartland((-95.4, 29.6, -94.9, 30.0)))
        self.assertIsNotNone(extent_outside_heartland((-95.2, 38.7, -94.7, 39.2)))
        self.assertIsNotNone(extent_outside_heartland((-82.6, 38.9, -81.8, 39.4)))

    def test_city_name_is_not_a_zoning_district(self):
        for token in ("LABELLE", "LaBelle", "CLEWISTON", "Did Not Change", "N/A"):
            self.assertFalse(is_designation(token))
        self.assertTrue(is_designation("A-2"))
        self.assertTrue(is_designation("AU"))
        self.assertIn("LABELLE", SENTINELS)

    def test_parcel_keys_match_dashed_and_compact_ids(self):
        dashed = parcel_keys("09-34-25-0831-0000C-0005")
        compact = parcel_keys("09342508310000C0005")
        self.assertIn("09342508310000C0005", dashed)
        self.assertIn("09342508310000C0005", compact)
        self.assertEqual(parcel_keys("<a href=\"https://example.test\">01-33-23</a>"), [])

    def test_sale_dates(self):
        self.assertEqual(parse_date("9/27/2002"), "2002-09-27")
        self.assertEqual(parse_date("2022"), "2022-01-01")
        self.assertIsNone(parse_date("not-a-date"))


if __name__ == "__main__":
    unittest.main()
