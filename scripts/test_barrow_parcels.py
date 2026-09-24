"""Unit tests for Barrow mailing, GIS acres, and city-overlay rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from barrow_parcels import (  # noqa: E402
    BRASELTON_FLU_QUERY,
    PARCEL_QUERY,
    STATHAM_FLU_QUERY,
    barrow_spec,
    choose_flu,
    choose_zoning,
    city_flu_overlay,
    compose_barrow_mailing,
    flu_stub_city,
    gis_acres,
    in_gis_band,
    looks_like_person_name,
    qpublic_parcel_url,
)


class BarrowMailingTest(unittest.TestCase):
    def test_co_owner_in_address1_does_not_become_the_street(self) -> None:
        mailing = compose_barrow_mailing(
            "MCLOCKLIN MELANIE N                     ",
            "1371 BETHLEHEM ROAD                     ",
            None,
        )
        self.assertEqual(mailing["ownerName2"], "MCLOCKLIN MELANIE N")
        self.assertEqual(mailing["line1"], "1371 BETHLEHEM ROAD")
        self.assertIsNone(mailing["line2"])

    def test_numbered_address1_is_the_street(self) -> None:
        mailing = compose_barrow_mailing(
            "6540 LANIER ISLANDS PKWY                ",
            "NULL",
            "NULL",
        )
        self.assertIsNone(mailing["ownerName2"])
        self.assertEqual(mailing["line1"], "6540 LANIER ISLANDS PKWY")
        self.assertIsNone(mailing["line2"])
        self.assertFalse(looks_like_person_name("NULL"))

    def test_address3_is_used_when_address2_is_empty(self) -> None:
        mailing = compose_barrow_mailing(None, None, "843 HWY 211 NW                          ")
        self.assertEqual(mailing["line1"], "843 HWY 211 NW")

    def test_suite_stays_on_line2(self) -> None:
        mailing = compose_barrow_mailing(
            None,
            "1450 LAKE ROBBINS DR                    ",
            "SUITE 430                               ",
        )
        self.assertEqual(mailing["line1"], "1450 LAKE ROBBINS DR")
        self.assertEqual(mailing["line2"], "SUITE 430")

    def test_po_box_is_not_a_person(self) -> None:
        mailing = compose_barrow_mailing("NULL", "P O BOX 550                             ", "NULL")
        self.assertEqual(mailing["line1"], "P O BOX 550")

    def test_second_person_line_is_not_the_street(self) -> None:
        mailing = compose_barrow_mailing(
            "LIMITED PARTNERSHIP AND",
            "BAXTER DOUGLAS P",
            "618 OLD HENRY GRADY RD",
        )
        self.assertIn("LIMITED PARTNERSHIP AND", mailing["ownerName2"] or "")
        self.assertIn("BAXTER DOUGLAS P", mailing["ownerName2"] or "")
        self.assertEqual(mailing["line1"], "618 OLD HENRY GRADY RD")
        self.assertTrue(looks_like_person_name("BAXTER DOUGLAS P"))


class BarrowAcresAndZoningTest(unittest.TestCase):
    def test_web_mercator_acres_are_inclusive_at_the_band_edges(self) -> None:
        self.assertEqual(gis_acres(5 * 4046.8564224), 5.0)
        self.assertEqual(gis_acres(150 * 4046.8564224), 150.0)
        self.assertTrue(in_gis_band(5.0))
        self.assertTrue(in_gis_band(150.0))
        self.assertFalse(in_gis_band(4.9999))
        self.assertFalse(in_gis_band(150.0001))

    def test_city_name_stubs_are_not_euclidean_districts(self) -> None:
        self.assertIsNone(choose_zoning("Winder", None))
        self.assertIsNone(choose_zoning("Auburn", None))
        self.assertEqual(choose_zoning("R1", None), "R1")
        self.assertEqual(choose_zoning("Winder", "R-1"), "R-1")
        self.assertEqual(choose_zoning("Bethlehem", "Bethlehem"), None)
        self.assertEqual(choose_zoning("AG", "R1"), "R1")

    def test_auburn_partial_flu_is_not_applied(self) -> None:
        self.assertIsNone(city_flu_overlay("Auburn", "Suburban"))
        self.assertEqual(city_flu_overlay("Winder", "Old Winder"), "Old Winder")
        self.assertIsNone(city_flu_overlay("Statham", None))
        flu = choose_flu("City of Winder", "Winder", "Old Winder", "Winder", "winder-2023-character")
        self.assertEqual(flu["source"], "winder-2023-character")
        self.assertEqual(flu["code"], "Old Winder")
        stub = choose_flu("City of Auburn", "Auburn", None, None, None)
        self.assertEqual(stub["source"], "barrow-flu2023")
        self.assertEqual(flu_stub_city(stub["label"]), "Auburn")

    def test_source_is_the_county_project_layer_not_a_lookalike(self) -> None:
        spec = barrow_spec()
        self.assertEqual(spec["url"], PARCEL_QUERY)
        self.assertIn("BarrowParcelswOwner_Project/FeatureServer/1", spec["url"])
        self.assertNotIn("HfsHDBmkGwb1UtID", spec["url"])
        self.assertNotIn("LandPro", spec["url"])
        self.assertNotIn("LandPro", STATHAM_FLU_QUERY)
        self.assertNotIn("LandPro", BRASELTON_FLU_QUERY)
        self.assertTrue(STATHAM_FLU_QUERY.endswith("/FeatureServer/5/query"))
        self.assertTrue(BRASELTON_FLU_QUERY.endswith("/FeatureServer/417/query"))
        self.assertEqual(spec["coverage"], "complete-gte-5ac")
        self.assertIsNone(spec.get("salePriceField"))
        joined = " ".join(spec["gaps"])
        self.assertIn("GIS area", joined)
        self.assertIn("qPublic", joined)
        self.assertIn("Norwalk", joined)

    def test_qpublic_deep_link_uses_the_parcel_id(self) -> None:
        url = qpublic_parcel_url("XX125  113")
        self.assertIn("App=BarrowCountyGA", url)
        self.assertIn("KeyValue=XX125%20%20113", url)
        self.assertNotIn("HfsHDBmkGwb1UtID", url)


if __name__ == "__main__":
    unittest.main()
