#!/usr/bin/env python3
"""Unit checks for the Tennessee OIR parcel id and geometry rules."""

from __future__ import annotations

import unittest

from parcel_geometry import esri_rings_to_geojson
from tn_oir_parcels import BY_FIPS, chester_parcel_id, in_band, positive, reject_source_url, slash_date_to_iso, yymmdd_to_iso


class TnOirParcelTests(unittest.TestCase):
    def test_acre_band_is_inclusive(self) -> None:
        self.assertTrue(in_band(5.0))
        self.assertTrue(in_band(150.0))
        self.assertFalse(in_band(4.999))
        self.assertFalse(in_band(150.001))

    def test_chester_id_uses_cama_gislink_then_map_id(self) -> None:
        self.assertEqual(
            chester_parcel_id({"GPDATA__GI": "012033    00500", "L15Parce_2": "012033", "GPDATA__PA": "033C A 00500"})[0],
            "012033    00500",
        )
        self.assertEqual(chester_parcel_id({"GPDATA__GI": " ", "L15Parce_2": "012086    03300"})[1], "map")
        self.assertEqual(chester_parcel_id({"GPDATA__GI": " ", "L15Parce_2": " "})[1], "neither")

    def test_bedford_pennsylvania_and_regrid_are_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            reject_source_url("https://imagery.pasda.psu.edu/arcgis/rest/services/pasda/ChesterCounty/MapServer/11")
        with self.assertRaises(RuntimeError):
            reject_source_url("https://gisprodops.chesco.org/server/rest/services/SharedInstance/siParcels/MapServer/0")
        with self.assertRaises(RuntimeError):
            reject_source_url("https://services.arcgis.com/example/April2023Parcels/FeatureServer/0")
        with self.assertRaises(RuntimeError):
            reject_source_url("https://app.regrid.com/parcels")
        with self.assertRaises(RuntimeError):
            reject_source_url("https://opendata.gis.utah.gov/datasets/utah::sevier-county-parcels")

    def test_manifest_keeps_oir_and_sevier_county_layer(self) -> None:
        sevier = BY_FIPS["47155"]
        self.assertEqual(sevier["mode"], "oir")
        self.assertEqual(sevier["source"], "tn-oir-public-use-47155")
        self.assertIn("Tennessee_Property_Boundaries_Public_Use", sevier["queryUrl"])
        self.assertEqual(sevier["salesVintage"], "2025")
        self.assertIn("GIS_Department_Layers/MapServer/57", sevier["salesJoin"]["url"])
        self.assertIsNone(sevier["tncpmLayer"])
        self.assertEqual(BY_FIPS["47133"]["salesVintage"], "2023")
        self.assertIsNone(BY_FIPS["47023"]["salesVintage"])
        self.assertEqual(BY_FIPS["47111"]["where"], "COUNTY_ID=56")
        macon = BY_FIPS["47111"]
        self.assertEqual(macon["mode"], "oir")
        self.assertIn("Tennessee_Property_Boundaries_Public_Use", macon["queryUrl"])
        self.assertEqual(BY_FIPS["47081"]["mode"], "hickman")
        self.assertEqual(BY_FIPS["47023"]["mode"], "chester")
        self.assertEqual(len(BY_FIPS), 20)

    def test_positive_drops_zero_prices(self) -> None:
        self.assertIsNone(positive(0))
        self.assertIsNone(positive(-5))
        self.assertEqual(positive("95100"), 95100.0)

    def test_card_date_formats(self) -> None:
        self.assertEqual(yymmdd_to_iso("220315"), "2022-03-15")
        self.assertEqual(yymmdd_to_iso("241024"), "2024-10-24")
        self.assertEqual(yymmdd_to_iso("990101"), "1999-01-01")
        self.assertIsNone(yymmdd_to_iso("229999"))
        self.assertEqual(slash_date_to_iso("10/17/2002"), "2002-10-17")
        self.assertIsNone(slash_date_to_iso(" "))

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
