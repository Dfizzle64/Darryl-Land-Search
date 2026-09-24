"""Pure checks for the Big Bend parcel wire. No network."""

from __future__ import annotations

import unittest

from big_bend_parcels import (
    GAP_FIPS,
    PARTIAL_FIPS,
    STATUS,
    PolyIndex,
    in_band,
    leon_appraiser_url,
    parse_totacres,
    pick_leon_zone,
    quincy_flum_is_zoning,
    spec_for_fips,
    title_city,
)


class BigBendParcelRules(unittest.TestCase):
    def test_leon_link_uses_taxid_and_does_not_say_designated(self):
        url = leon_appraiser_url("2612204050000")
        self.assertEqual(url, "https://search.leonpa.gov/Property/Details/2612204050000")
        self.assertNotIn("designated", url.lower())

    def test_acre_band_and_blank_gadsden_acres(self):
        self.assertTrue(in_band(5))
        self.assertTrue(in_band(150))
        self.assertFalse(in_band(4.99))
        self.assertFalse(in_band(150.01))
        self.assertIsNone(parse_totacres("0000000.000"))
        self.assertEqual(parse_totacres("0000008.680"), 8.68)
        self.assertFalse(in_band(parse_totacres("0000000.000")))

    def test_situs_city_is_not_a_zoning_jurisdiction_by_itself(self):
        self.assertEqual(title_city("QUINCY"), "Quincy")
        self.assertIsNone(title_city("0"))
        self.assertIsNone(title_city("  "))

    def test_quincy_flum_is_not_stored_as_zoning(self):
        self.assertFalse(quincy_flum_is_zoning("Commercial"))
        self.assertFalse(quincy_flum_is_zoning("Central_Business"))

    def test_city_zoning_polygon_beats_county_polygon(self):
        city = {"attrs": {"JURISDICTION": "City", "ZONING": "CU"}, "bbox": (0, 0, 0.2, 0.2)}
        county = {"attrs": {"JURISDICTION": "County", "ZONING": "R"}, "bbox": (0, 0, 1, 1)}
        chosen = pick_leon_zone([county, city], "Tallahassee")
        self.assertEqual(chosen["attrs"]["ZONING"], "CU")
        rural = pick_leon_zone([county, city], "Leon County")
        self.assertEqual(rural["attrs"]["ZONING"], "R")

    def test_point_index_keeps_a_city_polygon(self):
        square = {
            "type": "Polygon",
            "coordinates": [[[-84.3, 30.4], [-84.2, 30.4], [-84.2, 30.5], [-84.3, 30.5], [-84.3, 30.4]]],
        }
        index = PolyIndex([{"geometry": square, "attrs": {"NAME": "TALLAHASSEE"}, "bbox": (-84.3, 30.4, -84.2, 30.5)}])
        self.assertEqual(index.hits(-84.25, 30.45)[0]["attrs"]["NAME"], "TALLAHASSEE")
        self.assertEqual(index.hits(-84.5, 30.45), [])

    def test_coverage_matches_the_card(self):
        leon = spec_for_fips("12073")
        self.assertEqual(leon["coverage"], "complete-gte-5ac")
        self.assertIn("TLC_OverlayParcel_D_WM", leon["gaps"][0])
        self.assertIn("Property/Details/{TAXID}", leon["gaps"][0])
        for fips in PARTIAL_FIPS:
            spec = spec_for_fips(fips)
            self.assertEqual(spec["coverage"], "sample")
            self.assertTrue(spec["gaps"][0].startswith("Partial"))
        for fips in GAP_FIPS:
            spec = spec_for_fips(fips)
            self.assertEqual(spec["kind"], "gap")
            self.assertIn("not designated", spec["gaps"][1])
            self.assertNotRegex(spec["gaps"][1], r"(?i)^designated")
        self.assertEqual(STATUS, "Eligible — not designated")
        self.assertIn("not designated", STATUS)


if __name__ == "__main__":
    unittest.main()
