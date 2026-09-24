#!/usr/bin/env python3
"""Pure checks for Jacksonville shed joins. No network."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jax_shed_parcels as jax


class JaxShedTests(unittest.TestCase):
    def test_florida_and_county_extents(self) -> None:
        self.assertTrue(jax.in_florida(-81.65, 30.33))
        self.assertFalse(jax.in_florida(-84.5, 33.7))
        self.assertTrue(jax.in_county("12031", -81.65, 30.33))
        self.assertFalse(jax.in_county("12031", -81.65, 29.7))
        self.assertTrue(jax.in_county("12003", -82.14, 30.31))
        self.assertFalse(jax.in_county("12003", -81.6, 30.33))

    def test_duval_sale_and_separate_cities(self) -> None:
        self.assertEqual(jax.compose_duval_sale(4, 4, 2019), "2019-04-04")
        self.assertEqual(jax.compose_duval_sale(5, 13, 2025), "2025-05-13")
        self.assertIsNone(jax.compose_duval_sale(1, 1, 1800))
        self.assertEqual(jax.separate_duval_city(" atlantic   beach "), "Atlantic Beach")
        self.assertEqual(jax.separate_duval_city("JACKSONVILLE BEACH"), "Jacksonville Beach")
        self.assertIsNone(jax.separate_duval_city("JACKSONVILLE"))

    def test_excel_sale_serial_and_baker_city_line(self) -> None:
        self.assertEqual(jax.iso_from_any(46266), "2026-09-01")
        self.assertEqual(jax.iso_from_any("5/30/2025"), "2025-05-30")
        self.assertEqual(jax.iso_from_any("2024-08-16"), "2024-08-16")
        self.assertEqual(jax.iso_from_any(20240816), "2024-08-16")
        self.assertIsNone(jax.iso_from_any(1898))
        self.assertIsNone(jax.iso_from_any(10**18))
        self.assertEqual(jax.split_city_line("MACCLENNY, FL 32063"), ("MACCLENNY", "FL", "32063"))

    def test_point_in_ring_and_most_local_polygon(self) -> None:
        ring = [[-81.7, 30.2], [-81.5, 30.2], [-81.5, 30.4], [-81.7, 30.4], [-81.7, 30.2]]
        self.assertTrue(jax.point_in_ring(-81.6, 30.3, ring))
        self.assertFalse(jax.point_in_ring(-81.4, 30.3, ring))
        index = jax.SpatialIndex(cell=0.05)
        index.add([ring], {"name": "county"})
        small = [[-81.61, 30.29], [-81.59, 30.29], [-81.59, 30.31], [-81.61, 30.31], [-81.61, 30.29]]
        index.add([small], {"name": "city"})
        self.assertEqual(index.query(-81.6, 30.3), {"name": "city"})
        self.assertEqual(index.query(-81.68, 30.22), {"name": "county"})
        self.assertIsNone(index.query(-80.2, 25.8))

    def test_compact_parcel_ids(self) -> None:
        self.assertEqual(jax.compact_id("164240 0660"), "1642400660")
        self.assertEqual(jax.compact_id("007966-012-00"), "007966-012-00")


if __name__ == "__main__":
    unittest.main()
