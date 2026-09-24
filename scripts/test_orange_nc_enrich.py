#!/usr/bin/env python3
"""Offline checks for the Orange County, NC parcel enrich."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import orange_nc_enrich as ox  # noqa: E402


def square(x: float, y: float, size: float, attrs: dict) -> dict:
    ring = [
        [x, y],
        [x + size, y],
        [x + size, y + size],
        [x, y + size],
        [x, y],
    ]
    return {"attributes": attrs, "geometry": {"rings": [ring]}}


class OrangeNcEnrichTests(unittest.TestCase):
    def test_shell_codes_are_not_districts(self) -> None:
        for code in ("CH", "CA", "HI", "ME", "DU", " ch "):
            self.assertIsNone(ox.district_code(code))
        self.assertEqual(ox.district_code("AR"), "AR")
        self.assertEqual(ox.district_code("R-1"), "R-1")

    def test_situs_prefers_primary_flag(self) -> None:
        chosen = ox.choose_situs(
            [
                {"Add_St": "1 SECONDARY ST", "PrimaryFlag": "NO", "MailingCity": "HILLSBOROUGH", "ZipCode": "27278"},
                {"Add_St": "9 PRIMARY RD", "PrimaryFlag": "YES", "MailingCity": "CHAPEL HILL", "ZipCode": "27514"},
            ]
        )
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen["situsAddress"], "9 PRIMARY RD")
        self.assertEqual(chosen["situsCity"], "CHAPEL HILL")
        self.assertEqual(chosen["situsZip"], "27514")

    def test_sale_date_and_owner(self) -> None:
        self.assertEqual(ox.sale_date(1746144000000, None), "2025-05-02")
        self.assertEqual(ox.sale_date(None, "May  2 2025 12:00AM"), "2025-05-02")
        self.assertEqual(ox.person_name("", "SMITH", "ADA"), "ADA SMITH")
        self.assertEqual(ox.person_name("SMITH ADA", "SMITH", "ADA"), "SMITH ADA")
        self.assertEqual(ox.appraiser_url("0800050553"), "https://property.spatialest.com/nc/orange/#/property/0800050553")

    def test_city_zoning_beats_county_shell_and_carrboro_flu_stays_empty(self) -> None:
        layers = {
            "county_zoning": [square(0, 0, 10, {"Zoning": "AR", "Zoning_Def": "Agricultural Residential", "Jur": "County"})],
            "county_flu": [square(0, 0, 10, {"Legend": "Rural Residential"})],
            "chapel_hill_zoning": [square(0, 0, 2, {"ZONING": "R-1", "NAME": "Residential"})],
            "chapel_hill_flu": [square(0, 0, 2, {"LANDUSE": "Low Residential"})],
            "carrboro_zoning": [square(3, 3, 1, {"ZONING": "RR", "DEFINITION": "Rural Residential"})],
            "hillsborough_zoning": [square(6, 6, 1, {"ZoningType": "R20"})],
            "hillsborough_flu": [square(6, 6, 1, {"MH_LU": "Rural Living"})],
            "municipal": [square(8, 8, 1, {"NAME": "MEBANE", "CITYCODE": "ME"})],
            "carrboro_conditional": [{"attributes": {"ZONING": "R2CZ", "PINs": "3333333333, 3333333334"}}],
        }
        # County shell polygons must not become districts even if they cover the city.
        layers["county_zoning"].append(square(0, 0, 2, {"Zoning": "CH", "Jur": "Chapel Hill", "Zoning_Admin": "Chapel Hill"}))
        indexes = ox.build_indexes(layers)

        chapel = ox.assign_land_use(
            1, 1, "Chapel Hill", "1111111111", county_attribute="", **indexes
        )
        self.assertEqual(chapel["zoningCode"], "R-1")
        self.assertEqual(chapel["jurisdictionCode"], "CH")
        self.assertEqual(chapel["flu"]["code"], "Low Residential")
        self.assertNotEqual(chapel["zoningCode"], "CH")

        county = ox.assign_land_use(5, 5, "County", "2222222222", county_attribute="RB", **indexes)
        self.assertEqual(county["zoningCode"], "RB")
        self.assertEqual(county["jurisdictionCode"], "OC")
        self.assertEqual(county["flu"]["source"], "orange-county-flu")

        carrboro = ox.assign_land_use(3.5, 3.5, "Carrboro", "3333333333", county_attribute="", **indexes)
        self.assertEqual(carrboro["zoningCode"], "R2CZ")
        self.assertEqual(carrboro["jurisdictionCode"], "CA")
        self.assertIsNone(carrboro["flu"])

        hillsborough = ox.assign_land_use(6.2, 6.2, "Hillsborough", "4444444444", county_attribute="", **indexes)
        self.assertEqual(hillsborough["zoningCode"], "R20")
        self.assertEqual(hillsborough["flu"]["code"], "Rural Living")

        mebane = ox.assign_land_use(8.2, 8.2, "Mebane", "5555555555", county_attribute="ME", **indexes)
        self.assertIsNone(mebane["zoningCode"])
        self.assertEqual(mebane["jurisdictionCode"], "ME")
        self.assertEqual(mebane["flu"]["source"], "orange-county-flu")

    def test_feature_mapping_keeps_band_and_mailing(self) -> None:
        raw = [
            {
                "attributes": {
                    "PIN": "0800050553",
                    "OWNER1": "MCFARLAND HOMESTEAD LLC",
                    "ADDRESS1": "4 BIG OAK CT",
                    "CITY": "DURHAM",
                    "STATE": "NC",
                    "ZIPCODE": "27713",
                    "CALC_ACRES": 12.75,
                    "DATESOLD": 1746144000000,
                    "STAMPVALUE": 50000,
                    "VALUATION": 82000,
                    "LANDVALUE": 82000,
                    "USEVALUE": 0,
                    "Zonings": "",
                    "Zoning_Admin": "County",
                },
                "geometry": {
                    "rings": [
                        [[-79.1, 36.0], [-79.09, 36.0], [-79.09, 36.01], [-79.1, 36.01], [-79.1, 36.0]]
                    ]
                },
            }
        ]
        addresses = {
            "0800050553": [
                {"PIN": "0800050553", "Add_St": "100 RURAL RD", "PrimaryFlag": "YES", "MailingCity": "HILLSBOROUGH", "ZipCode": "27278"}
            ]
        }
        features, stats = ox.features_from_parcels(
            raw,
            {"name": "Orange", "fips": "37135", "state": "North Carolina"},
            ["Raleigh-Durham"],
            addresses=addresses,
            indexes=ox._empty_indexes(),
            source=ox.SOURCE,
            acres_field="CALC_ACRES",
        )
        self.assertEqual(len(features), 1)
        props = features[0]["properties"]
        self.assertEqual(props["parcelId"], "0800050553")
        self.assertEqual(props["ownerName"], "MCFARLAND HOMESTEAD LLC")
        self.assertEqual(props["situsAddress"], "100 RURAL RD")
        self.assertEqual(props["mailingAddress"]["line1"], "4 BIG OAK CT")
        self.assertEqual(props["mailingAddress"]["city"], "DURHAM")
        self.assertEqual(props["lastSale"]["date"], "2025-05-02")
        self.assertEqual(props["lastSale"]["price"], 50000)
        self.assertEqual(props["lastSale"]["qualified"], "tax-stamp")
        self.assertEqual(props["tax"]["marketValue"], 82000)
        self.assertEqual(props["tax"]["assessedValue"], 82000)
        self.assertIsNone(props["tax"]["taxableValue"])
        self.assertTrue(props["appraiserUrl"].endswith("/property/0800050553"))
        self.assertEqual(props["marketIds"], ["Raleigh-Durham"])
        self.assertGreaterEqual(props["acreage"], 5)
        self.assertLessEqual(props["acreage"], 150)
        self.assertEqual(stats["situs"], 1)


if __name__ == "__main__":
    unittest.main()
