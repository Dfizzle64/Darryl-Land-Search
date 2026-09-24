"""Unit checks for Bartow dissolve, situs, and the Incorporated zoning stub."""

from __future__ import annotations

import unittest

from bartow_parcels import (
    ZoningGrid,
    choose_acreage,
    compose_situs,
    in_bartow_bounds,
    normalize_zoning_code,
    positive_money,
    unique_rings,
)


class BartowParcelRules(unittest.TestCase):
    def test_situs_skips_blank_unit_and_zero_house_number(self):
        self.assertEqual(compose_situs(3745, "WAYSIDE RD               ", "    "), "3745 WAYSIDE RD")
        self.assertEqual(compose_situs(0, "MAIN ST", None), "MAIN ST")
        self.assertEqual(compose_situs(102, "OLD MILL RD", "B"), "102 OLD MILL RD B")
        self.assertIsNone(compose_situs(None, "   ", None))

    def test_acreage_is_not_summed_across_parts(self):
        self.assertEqual(choose_acreage([10.23, 10.23, 10.23]), 10.23)
        self.assertEqual(choose_acreage([18.4, 18.4, 600]), 18.4)
        self.assertIsNone(choose_acreage([None, ""]))

    def test_stacked_rings_collapse_and_distinct_parts_remain(self):
        ring = [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]
        other = [[3, 0], [3, 1], [4, 1], [4, 0], [3, 0]]
        merged, distinct = unique_rings([[ring], [ring], [ring]])
        self.assertEqual(distinct, 1)
        self.assertEqual(len(merged), 1)
        merged, distinct = unique_rings([[ring], [other]])
        self.assertEqual(distinct, 2)
        self.assertEqual(len(merged), 2)

    def test_incorporated_is_not_stored_and_florida_bartow_is_outside(self):
        self.assertEqual(normalize_zoning_code("Incorporated"), (None, "stub"))
        self.assertEqual(normalize_zoning_code("  A-1 "), ("A-1", "joined"))
        self.assertEqual(normalize_zoning_code(" "), (None, "miss"))
        self.assertTrue(in_bartow_bounds(-85.016, 34.320))
        self.assertFalse(in_bartow_bounds(-81.92, 27.96))
        self.assertIsNone(positive_money(0))
        self.assertEqual(positive_money(534532), 534532)

    def test_zoning_grid_prefers_county_code_over_city_stub(self):
        grid = ZoningGrid(cell=1, bounds=(-1, -1, 5, 5))
        county = [[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]
        # Clockwise Esri exterior (negative shoelace) so it is not treated as a hole.
        county = list(reversed(county))
        stub = [[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]
        stub = list(reversed(stub))
        self.assertTrue(grid.add("Incorporated", [stub]))
        self.assertTrue(grid.add("A-1", [county]))
        self.assertEqual(grid.code_at(1, 1), "A-1")
        stub_only = ZoningGrid(cell=1, bounds=(-1, -1, 5, 5))
        stub_only.add("Incorporated", [stub])
        self.assertEqual(normalize_zoning_code(stub_only.code_at(1, 1)), (None, "stub"))


if __name__ == "__main__":
    unittest.main()
