#!/usr/bin/env python3
"""Unit checks for the Tennessee OIR parcel id and geometry rules."""

from __future__ import annotations

import unittest

from parcel_geometry import esri_rings_to_geojson
from tn_oir_parcels import chester_parcel_id, in_band, reject_source_url


class TnOirParcelTests(unittest.TestCase):
    def test_acre_band_is_inclusive(self) -> None:
        self.assertTrue(in_band(5.0))
        self.assertTrue(in_band(150.0))
        self.assertFalse(in_band(4.999))
        self.assertFalse(in_band(150.001))

    def test_chester_id_uses_tax_record_then_map_id(self) -> None:
        self.assertEqual(chester_parcel_id({"GPDATA__PA": "033C A 00500", "L15Parce_2": "012033"})[1], "tax-record")
        self.assertEqual(chester_parcel_id({"GPDATA__PA": " ", "L15Parce_2": "012086    03300"})[0], "012086    03300")
        self.assertEqual(chester_parcel_id({"GPDATA__PA": " ", "L15Parce_2": " "})[1], "neither")

    def test_bedford_pennsylvania_and_regrid_are_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            reject_source_url("https://imagery.pasda.psu.edu/arcgis/rest/services/pasda/ChesterCounty/MapServer/11")
        with self.assertRaises(RuntimeError):
            reject_source_url("https://gisprodops.chesco.org/server/rest/services/SharedInstance/siParcels/MapServer/0")
        with self.assertRaises(RuntimeError):
            reject_source_url("https://services.arcgis.com/example/April2023Parcels/FeatureServer/0")
        with self.assertRaises(RuntimeError):
            reject_source_url("https://app.regrid.com/parcels")

    def test_exact_rings_keep_a_vertex_the_cadastral_tolerance_drops(self) -> None:
        ring = [[0.0, 0.0], [0.5, 0.000005], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]
        exact = esri_rings_to_geojson([ring], simplify=False)
        simplified = esri_rings_to_geojson([ring], simplify=True)
        self.assertIsNotNone(exact)
        self.assertIsNotNone(simplified)
        exact_ring = exact["coordinates"][0]
        simple_ring = simplified["coordinates"][0]
        self.assertGreater(len(exact_ring), len(simple_ring))
        self.assertIn([0.5, 0.000005], exact_ring)


if __name__ == "__main__":
    unittest.main()
