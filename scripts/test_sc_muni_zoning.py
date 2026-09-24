#!/usr/bin/env python3
"""Unit tests for South Carolina municipal zoning joins. No network."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sc_muni_zoning as zoning


def parcel(parcel_id: str, lon: float, lat: float, **extra):
    props = {
        "parcelId": parcel_id,
        "acreage": 10,
        "centroid": [lon, lat],
        "zoningCode": None,
        "situsCity": None,
        "situsAddress": None,
        "jurisdictionCode": None,
        "lastSale": {"date": None, "price": None, "qualified": None},
        "flu": None,
        "opportunityZone": None,
        "oz2Eligibility": None,
    }
    props.update(extra)
    return {"type": "Feature", "properties": props, "geometry": None}


class ParcelKeysTest(unittest.TestCase):
    def test_dashed_tms_matches_digits_and_pid(self):
        left = set(zoning.parcel_keys("154-09-04-029"))
        right = set(zoning.parcel_keys("1540904029"))
        self.assertIn("154-09-04-029", left)
        self.assertTrue(left & right)
        self.assertIn("2080002013", set(zoning.parcel_keys("208-00-02-013")))
        self.assertIn("2090001049", set(zoning.parcel_keys("209-00-01-049")))

    def test_summerville_county_filter(self):
        rows = [
            {"County": "CHARLESTON", "Zone_Class": "PUD"},
            {"County": "Dorchester", "Zone_Class": "GR-2"},
            {"County": "BERKELEY", "Zone_Class": "R-1"},
        ]
        self.assertEqual(len(zoning.rows_for_county(rows, "CHARLESTON")), 1)
        self.assertEqual(zoning.rows_for_county(rows, "DORCHESTER")[0]["Zone_Class"], "GR-2")

    def test_attribute_overlay_city_wins_over_county(self):
        features = [parcel("154-09-04-029", -80.2, 33.0)]
        county = zoning.index_codes(
            [{"TMS": "154-09-04-029", "ZONINGCODE": "PUD_SV"}],
            ["TMS"],
            lambda row: row["ZONINGCODE"],
        )
        city = zoning.index_codes(
            [{"TMS": "154-09-04-029", "Zone_Class": "PUD"}],
            ["TMS"],
            lambda row: row["Zone_Class"],
        )
        zoning.overlay_attribute(features, county, "dorchester-county")
        zoning.overlay_attribute(features, city, "summerville-dorchester")
        self.assertEqual(features[0]["properties"]["zoningCode"], "PUD")
        self.assertEqual(features[0]["properties"]["_zoningSource"], "summerville-dorchester")
        self.assertIsNone(features[0]["properties"]["opportunityZone"])

    def test_spatial_skips_james_island_and_keeps_acreage(self):
        square = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-80.1, 32.7], [-80.0, 32.7], [-80.0, 32.8], [-80.1, 32.8], [-80.1, 32.7]]],
            },
            "properties": {"code": "R-4", "source": "charleston-county"},
        }
        index = zoning.GridIndex(0.05)
        index.add(square)
        kept = parcel("1", -80.05, 32.75, situsCity="JAMES ISLAND", acreage=5)
        other = parcel("2", -80.05, 32.75, situsCity="NORTH CHARLESTON", acreage=150)
        zoning.overlay_spatial([kept, other], index, field="zoning", skip=zoning.is_gap_place)
        self.assertIsNone(kept["properties"]["zoningCode"])
        self.assertEqual(other["properties"]["zoningCode"], "R-4")
        self.assertEqual(kept["properties"]["acreage"], 5)
        self.assertEqual(other["properties"]["acreage"], 150)

    def test_iop_plan_excludes_pdd_and_rejected_urls(self):
        urls = zoning.queried_iop_urls()
        self.assertTrue(urls)
        self.assertFalse(any("/PDD/" in url or url.rstrip("/").endswith("/PDD") for url in urls))
        self.assertIn("SR-1", [code for _svc, code in zoning.IOP_DISTRICTS])
        zoning.assert_urls_allowed(urls)
        with self.assertRaises(RuntimeError):
            zoning.assert_urls_allowed(["https://services.example.com/SimpsonvilleZoning/FeatureServer/0/query"])
        with self.assertRaises(RuntimeError):
            zoning.assert_urls_allowed(["https://services3.arcgis.com/YQLyddqtM8cTAr6Y/arcgis/rest/services/ZoningFireSewer/FeatureServer/2/query"])

    def test_north_charleston_prefers_zone_type(self):
        self.assertEqual(zoning.north_charleston_code({"ZONECODE": 9, "ZONETYPE": "B-2"}), "B-2")
        self.assertEqual(zoning.north_charleston_code({"ZONECODE": 9, "ZONETYPE": " "}), "9")

    def test_gap_place_names(self):
        self.assertTrue(zoning.is_gap_place(parcel("1", 0, 0, situsCity="Sullivan's Island")))
        self.assertTrue(zoning.is_gap_place(parcel("1", 0, 0, situsCity="ISLE OF PALMS")))
        self.assertFalse(zoning.is_gap_place(parcel("1", 0, 0, situsCity="Folly Beach")))

    def test_epoch_and_band_constants(self):
        self.assertEqual(zoning.epoch_to_iso(1649131200000), "2022-04-05")
        self.assertIsNone(zoning.epoch_to_iso(None))
        self.assertIn("Shelby", zoning.REJECTED[0]["reason"])
        self.assertTrue(any("James Island" in gap for gap in zoning.HONEST_GAPS))
        self.assertTrue(any("Mauldin" in gap for gap in zoning.HONEST_GAPS))


if __name__ == "__main__":
    unittest.main()
