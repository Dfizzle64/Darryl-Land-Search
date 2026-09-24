"""Unit checks for the new-metro shelf that do not download parcels."""

from __future__ import annotations

import unittest

from new_metro_parcels import combine_codes, drop_nominal_sale, in_box, norm_id, specs


class NewMetroParcelsTest(unittest.TestCase):
    def test_rejects_broken_cmpdd_hosts(self) -> None:
        for spec in specs().values():
            urls = [spec["parcel"]["url"], *[layer["url"] for layer in spec["layers"]]]
            for url in urls:
                self.assertNotIn("gis3.cmpdd.org", url)
                self.assertNotIn("portal.cmpdd.org", url)
            if spec["fips"] in {"28121", "28089", "28029", "28127", "28149", "28163"}:
                self.assertIn("gis.cmpdd.org", spec["parcel"]["url"])

    def test_nominal_sales_and_ids(self) -> None:
        self.assertIsNone(drop_nominal_sale(1, {1.0, 100.0}))
        self.assertIsNone(drop_nominal_sale(100, {1.0, 100.0}))
        self.assertEqual(drop_nominal_sale(250000, {1.0, 100.0}), 250000)
        self.assertEqual(norm_id("172D  013A"), "172D013A")
        self.assertEqual(combine_codes(["C-3", "C-3", "I-1"]), "C-3 / I-1")

    def test_boxes_reject_the_lookalikes(self) -> None:
        boxes = {spec["fips"]: spec["box"] for spec in specs().values()}
        self.assertTrue(in_box(-83.28, 30.83, boxes["13185"]))
        self.assertFalse(in_box(-88.3, 33.5, boxes["13185"]))  # Lowndes MS
        self.assertTrue(in_box(-83.37, 33.95, boxes["13059"]))
        self.assertFalse(in_box(-78.0, 39.1, boxes["13059"]))  # Clarke VA
        self.assertTrue(in_box(-90.1, 32.5, boxes["28089"]))
        self.assertFalse(in_box(-88.8, 35.6, boxes["28089"]))  # Madison TN


if __name__ == "__main__":
    unittest.main()
