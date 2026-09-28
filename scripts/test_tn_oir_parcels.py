#!/usr/bin/env python3
"""Unit checks for the Tennessee OIR parcel id and geometry rules."""

from __future__ import annotations

import unittest

import json
from copy import deepcopy

from parcel_geometry import esri_rings_to_geojson
from tn_oir_parcels import BY_FIPS, ROOT, chester_parcel_id, in_band, positive, reject_source_url, slash_date_to_iso, yymmdd_to_iso
from tn_parcel_cards import (
    card_sale_date,
    load_cards,
    normalize_use,
    resolve_acreage,
    resolve_card,
    sales_join_kind,
    select_parcel_layers,
    stamp_mapped_sale,
)


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

    def test_cards_match_published_endpoints_and_ignore_layer_order(self) -> None:
        overlay = {
            row["fips"]: row
            for row in json.loads((ROOT / "data" / "tn-rural-parcel-sources.json").read_text())["counties"]
        }
        self.assertEqual(set(overlay), set(BY_FIPS))
        for fips, published in overlay.items():
            resolved = BY_FIPS[fips]
            self.assertEqual(resolved["mode"], published["mode"], fips)
            self.assertEqual(resolved["queryUrl"], published["queryUrl"], fips)
            self.assertEqual(resolved["where"], published["where"], fips)
            self.assertEqual(resolved["source"], published["source"], fips)
            self.assertEqual(resolved["tncpmLayer"], published.get("tncpmLayer"), fips)
            self.assertEqual(resolved["salesVintage"], published.get("salesVintage"), fips)
            self.assertEqual(resolved["acreageMethod"], "geodesic", fips)
            self.assertEqual(resolved.get("joins"), published.get("joins"), fips)
            if fips == "47155":
                self.assertEqual(resolved["salesJoin"]["url"], published["salesJoin"]["url"])
                self.assertEqual(resolved["salesJoin"]["idField"], "GISLINK")
                self.assertEqual(resolved["salesJoin"]["dateField"], "SALEDATE")
                self.assertEqual(resolved["salesJoin"]["marketField"], "APPRAISAL")
                self.assertEqual(resolved["salesJoin"]["assessedField"], "ASSESSMENT")
            if fips == "47133":
                self.assertIn("Overton_Parcels", resolved["salesJoin"]["url"])
                self.assertEqual(resolved["salesJoin"]["dateField"], "SALEDATE")
                self.assertEqual(sales_join_kind(resolved), "overton-ucdd")
            if published.get("tncpmLayer") is not None:
                self.assertEqual(sales_join_kind(resolved), "tncpm")
                self.assertIsNone(resolved.get("salesJoin"))
        self.assertEqual(sales_join_kind(BY_FIPS["47155"]), "sevier-cama")
        self.assertEqual(sales_join_kind(BY_FIPS["47023"]), "none")
        self.assertIsNone(BY_FIPS["47111"]["acreageField"])
        macon = next(card for card in load_cards() if card["fips"] == "47111")
        reversed_card = deepcopy(macon)
        reversed_card["layers"] = list(reversed(macon["layers"]))
        self.assertEqual(normalize_use(reversed_card["layers"][0].get("use")), "sibling-fallback")
        flipped = resolve_card(reversed_card, overlay["47111"])
        self.assertEqual(flipped["queryUrl"], BY_FIPS["47111"]["queryUrl"])
        self.assertEqual(flipped["tncpmLayer"], 37)
        self.assertNotIn("IMPACT", flipped["queryUrl"])

    def test_sibling_fallback_listed_first_is_not_the_geometry_source(self) -> None:
        oir = (
            "https://services1.arcgis.com/YuVBSS7Y1of2Qud1/arcgis/rest/services/"
            "Tennessee_Property_Boundaries_Public_Use/FeatureServer/0"
        )
        sales = (
            "https://services.arcgis.com/rD2ylXRs80UroD90/arcgis/rest/services/"
            "TN_County_Parcel_Map/FeatureServer/4"
        )
        card = {
            "fips": "47999",
            "jurisdiction": "Example County",
            "layers": [
                {
                    "role": "parcels",
                    "use": "sibling-fallback (2023 sale/value, not primary for this county)",
                    "restUrl": "https://maps.cot.tn.gov/server3/rest/services/IMPACT/Parcels/FeatureServer/0",
                    "acreageField": "CALC_ACRE",
                    "fieldMap": {"GISLINK": "parcelId", "CALC_ACRE": "acreage"},
                },
                {
                    "role": "parcels",
                    "use": "sales-value-join",
                    "restUrl": sales,
                    "fieldMap": {
                        "Parcels_GISLINK": "parcelId",
                        "Assessment_Data_99_PRICE": "lastSale.price",
                        "Assessment_Data_99_SALEDATE": "lastSale.date",
                        "Assessment_Data_99_APPRAISAL": "tax.marketValue",
                    },
                },
                {
                    "role": "parcels",
                    "use": "primary-geometry-owner",
                    "restUrl": oir,
                    "acreageField": None,
                    "fieldMap": {"GISLINK": "parcelId", "OWNER": "ownerName", "ADDRESS": "situsAddress"},
                },
            ],
            "parcelSetup": {
                "geometryOwnerSource": oir,
                "geometryOwnerFilter": "COUNTY_ID=99",
                "salesValueSource": sales,
                "salesValueVintage": 2023,
                "acreageFilter": "5–150 ac on geodesic polygon area computed from OIR geometry",
            },
        }
        primary, sale = select_parcel_layers(card)
        self.assertIn("Tennessee_Property_Boundaries_Public_Use", primary["restUrl"])
        self.assertEqual(primary["use"], "primary-geometry-owner")
        self.assertIn("TN_County_Parcel_Map", sale["restUrl"])
        row = resolve_card(card)
        self.assertEqual(row["where"], "COUNTY_ID=99")
        self.assertEqual(row["tncpmLayer"], 4)
        self.assertEqual(row["acreageMethod"], "geodesic")
        self.assertIsNone(row["acreageField"])
        self.assertNotIn("IMPACT", row["queryUrl"])
        self.assertEqual(sales_join_kind(row), "tncpm")

    def test_null_acreage_field_is_geodesic_and_sale_stamps_follow_the_card(self) -> None:
        method, field = resolve_acreage({"acreageField": None}, {"acreageFilter": ""})
        self.assertEqual((method, field), ("geodesic", None))
        with self.assertRaises(RuntimeError):
            resolve_acreage({"acreageField": "CALC_ACRE"}, {"acreageFilter": "use CALC_ACRE"})
        self.assertEqual(card_sale_date("3/4/2020"), "2020-03-04")
        self.assertEqual(card_sale_date("220315"), "2022-03-15")
        self.assertEqual(card_sale_date(1_640_995_200_000), "2022-01-01")
        props = {"tax": {}}
        stamped = stamp_mapped_sale(
            props,
            {"SALEDATE": "10/17/2002", "PRICE": 0, "APPRAISAL": 1200, "ZONING": "A-1"},
            {
                "dateField": "SALEDATE",
                "priceField": "PRICE",
                "marketField": "APPRAISAL",
                "zoningField": "ZONING",
            },
            "2023",
            stamp_zoning=False,
        )
        self.assertTrue(stamped["sale"])
        self.assertIsNone(props["lastSale"]["price"])
        self.assertEqual(props["lastSale"]["vintage"], "2023")
        self.assertEqual(props["tax"]["vintage"], "2023")
        self.assertNotIn("zoningCode", props)
        blank = {"tax": {}}
        stamp_mapped_sale(
            blank,
            {"GPDATA__LA": "241024", "GPDATA__30": 50},
            {"dateField": "GPDATA__LA", "marketField": "GPDATA__30"},
            None,
        )
        self.assertEqual(blank["lastSale"]["date"], "2024-10-24")
        self.assertNotIn("vintage", blank["lastSale"])
        self.assertNotIn("vintage", blank["tax"])

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
