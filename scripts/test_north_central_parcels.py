#!/usr/bin/env python3
"""Rules for North-Central municipality labels. No network."""

from __future__ import annotations

import unittest

from north_central_parcels import (
    alachua_municipality,
    alachua_prefix,
    citrus_municipality,
    flu_record,
    hernando_municipality,
    matching_code,
    putnam_city_from_layer,
    usable_zoning,
)


class NorthCentralRules(unittest.TestCase):
    def test_alachua_jurisdiction_is_not_the_mailing_city(self) -> None:
        self.assertEqual(alachua_municipality(0), "Unincorporated Alachua County")
        self.assertEqual(alachua_municipality(300), "Gainesville")
        self.assertEqual(alachua_municipality(600), "LaCrosse")
        self.assertIsNone(alachua_municipality(None))

    def test_alachua_prefix_blocks_county_codes_inside_a_city(self) -> None:
        self.assertEqual(alachua_prefix(0), "0100")
        self.assertEqual(alachua_prefix(300), "0103")
        self.assertEqual(alachua_prefix(800), "0108")
        self.assertEqual(matching_code("0103RMF8", "0103"), "0103RMF8")
        self.assertIsNone(matching_code("0100A", "0103"))
        self.assertIsNone(matching_code(None, "0100"))

    def test_hernando_city_flag_and_placeholder_zoning(self) -> None:
        self.assertEqual(hernando_municipality("B"), "Brooksville")
        self.assertEqual(hernando_municipality("C"), "Unincorporated Hernando County")
        self.assertEqual(hernando_municipality(" "), "Unincorporated Hernando County")
        self.assertIsNone(usable_zoning("CITY"))
        self.assertEqual(usable_zoning("AG"), "AG")
        self.assertIsNone(flu_record("city", "Brooksville", "Brooksville", "test"))

    def test_citrus_and_putnam_city_names(self) -> None:
        self.assertEqual(citrus_municipality("CRYSTAL RIVER"), "Crystal River")
        self.assertEqual(citrus_municipality("INVERNESS"), "Inverness")
        self.assertEqual(citrus_municipality(None), "Unincorporated Citrus County")
        self.assertEqual(putnam_city_from_layer("City of Palatka"), "Palatka")
        self.assertEqual(putnam_city_from_layer("Town of Welaka"), "Welaka")
        self.assertIsNone(putnam_city_from_layer("County"))


if __name__ == "__main__":
    unittest.main()
