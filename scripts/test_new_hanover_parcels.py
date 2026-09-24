"""Unit tests for New Hanover attribute mapping and the city-first join."""

from __future__ import annotations

import unittest

from new_hanover_parcels import (
    KURE_ZONING_GAP,
    SpatialIndex,
    WILMINGTON_FLU_GAP,
    apply_overlays,
    assemble_mail,
    assemble_situs,
    is_placeholder_zoning,
    map_tax_attributes,
    mapidkey_from_pin,
    parse_sale_price,
    wrightsville_code,
)


def _square(west: float, south: float, east: float, north: float, props: dict) -> dict:
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
        },
    }


def _index(*features: dict) -> SpatialIndex:
    index = SpatialIndex()
    for feature in features:
        index.add(feature)
    return index


def _parcel(lon: float, lat: float) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "centroid": [lon, lat],
            "zoningCode": None,
            "zoningDistrict": None,
            "jurisdictionPrefix": None,
            "jurisdictionCode": None,
            "flu": None,
            "opportunityZone": None,
            "oz2Eligibility": None,
            "dataGaps": [],
        },
        "geometry": {"type": "Polygon", "coordinates": []},
    }


class NewHanoverMappingTest(unittest.TestCase):
    def test_mapidkey_strips_zero_fraction(self) -> None:
        self.assertEqual(mapidkey_from_pin("3242-35-3445.000"), "3242-35-3445")
        self.assertEqual(mapidkey_from_pin("3242-35-3445.100"), "3242-35-3445.100")
        self.assertIsNone(mapidkey_from_pin("  "))

    def test_situs_and_zero_sale(self) -> None:
        self.assertEqual(
            assemble_situs({"ADRNO": 1129, "ADRDIR": None, "ADRSTR": "BARCLAY", "ADRSUF": "BLV", "UNITNO": None}),
            "1129 BARCLAY BLV",
        )
        self.assertIsNone(assemble_situs({"ADRNO": 0, "ADRSTR": None}))
        mail, _line2 = assemble_mail({"OWNER_STREET": "RIVER", "OWNER_STREETTYPE": "RD", "OWNER_ADDR1": None})
        self.assertEqual(mail, "RIVER RD")
        self.assertIsNone(parse_sale_price("0"))
        self.assertEqual(parse_sale_price("38500"), 38500)

    def test_tax_assessed_is_not_market_value(self) -> None:
        mapped = map_tax_attributes(
            {
                "OWN1": "GRAHAM CAMERON AG & TIMBER COMPANY LLC",
                "ADRNO": 1129,
                "ADRSTR": "BARCLAY",
                "ADRSUF": "BLV",
                "CITYNAME": "WILMINGTON",
                "OWNER_CITY": "WILMINGTON",
                "OWNER_STATE": "NC",
                "OWNER_ZIP": "28412",
                "APRTOT": 17890000,
                "SALE_DATE": "2025-06-06 00:00:00",
                "SALE_PRICE": "0",
                "LUC": "108",
                "ZONING": "RB",
                "MUNI": "WM",
            }
        )
        self.assertEqual(mapped["owner"], "GRAHAM CAMERON AG & TIMBER COMPANY LLC")
        self.assertEqual(mapped["situs"], "1129 BARCLAY BLV")
        self.assertEqual(mapped["city"], "Wilmington")
        self.assertEqual(mapped["assessed"], 17890000)
        self.assertIsNone(mapped["salePrice"])
        self.assertEqual(mapped["saleDate"], "2025-06-06")
        self.assertTrue(is_placeholder_zoning("CITY"))
        self.assertFalse(is_placeholder_zoning("R-15"))

    def test_wrightsville_code_strips_district_label(self) -> None:
        self.assertEqual(wrightsville_code("R-1 Zoning District"), "R-1")
        self.assertEqual(wrightsville_code("C-3 Zoning District\u00a0"), "C-3")

    def test_city_zoning_beats_county_stamp_and_flu_stays_out(self) -> None:
        wilmington = _index(_square(-77.95, 34.20, -77.90, 34.25, {"Zoning": "HDR", "CaseNumber": "Z-1"}))
        county = _index(_square(-78.0, 34.1, -77.8, 34.4, {"ZONING": "CITY", "ZONINGTXT": "CITY"}))
        flum = _index(_square(-78.0, 34.1, -77.8, 34.4, {"PlaceType": "GENERAL RESIDENTIAL"}))
        muni = _index(_square(-77.95, 34.20, -77.90, 34.25, {"CITY": "WILMINGTON", "JURIS": "WM"}))
        eligible = _index(
            _square(
                -77.95,
                34.20,
                -77.90,
                34.25,
                {"tractGeoid": "37129010100", "name": "Census Tract 101", "rural": False, "source": "rev-proc-2026-14"},
            )
        )
        designated = _index(_square(-77.94, 34.22, -77.93, 34.23, {"tractGeoid": "37129001000", "name": "Census tract 10", "rural": False}))
        feature = _parcel(-77.92, 34.22)
        apply_overlays(
            feature,
            municipalities=muni,
            city_zoning={"Wilmington": wilmington},
            county_zoning=county,
            flum=flum,
            designated=designated,
            eligible=eligible,
            designated_source="hud-oz",
        )
        props = feature["properties"]
        self.assertEqual(props["zoningCode"], "HDR")
        self.assertEqual(props["jurisdictionPrefix"], "Wilmington")
        self.assertIsNone(props["flu"])
        self.assertIn(WILMINGTON_FLU_GAP, props["dataGaps"])
        self.assertTrue(props["oz2Eligibility"]["eligible"])
        self.assertEqual(props["oz2Eligibility"]["designation"], "eligible-for-nomination")
        self.assertFalse(props["oz2Eligibility"]["rural"])
        self.assertFalse(props["opportunityZone"]["inOpportunityZone"])
        self.assertNotEqual(props["opportunityZone"]["inOpportunityZone"], props["oz2Eligibility"]["eligible"])

    def test_kure_beach_has_no_zoning_polygon(self) -> None:
        county = _index(_square(-77.95, 34.00, -77.90, 34.05, {"ZONING": "KB", "ZONINGTXT": "KB"}))
        muni = _index(_square(-77.95, 34.00, -77.90, 34.05, {"CITY": "KURE BEACH", "JURIS": "KB"}))
        feature = _parcel(-77.93, 34.02)
        apply_overlays(
            feature,
            municipalities=muni,
            city_zoning={},
            county_zoning=county,
            flum=None,
            designated=None,
            eligible=None,
            designated_source=None,
        )
        props = feature["properties"]
        self.assertIsNone(props["zoningCode"])
        self.assertIsNone(props["flu"])
        self.assertIn(KURE_ZONING_GAP, props["dataGaps"])
        self.assertEqual(props["jurisdictionCode"], "KB")

    def test_unincorporated_place_type_and_real_county_zone(self) -> None:
        county = _index(_square(-77.9, 34.3, -77.7, 34.5, {"ZONING": "R-15", "ZONINGTXT": "CZD R-15"}))
        flum = _index(_square(-77.9, 34.3, -77.7, 34.5, {"PlaceType": "COMMUNITY MIXED USE"}))
        muni = _index(_square(-77.9, 34.3, -77.7, 34.5, {"CITY": "UNINCORPORATED", "JURIS": "NHC"}))
        feature = _parcel(-77.8, 34.4)
        apply_overlays(
            feature,
            municipalities=muni,
            city_zoning={},
            county_zoning=county,
            flum=flum,
            designated=None,
            eligible=_index(),
            designated_source=None,
        )
        props = feature["properties"]
        self.assertEqual(props["zoningCode"], "R-15")
        self.assertEqual(props["zoningDistrict"], "CZD R-15")
        self.assertEqual(props["jurisdictionPrefix"], "New Hanover")
        self.assertEqual(props["flu"]["code"], "COMMUNITY MIXED USE")
        self.assertEqual(props["flu"]["source"], "plan-nhc-flum-8")
        self.assertEqual(props["oz2Eligibility"]["eligible"], False)
        self.assertEqual(props["oz2Eligibility"]["designation"], "not-eligible")
        self.assertIsNone(props["opportunityZone"])


if __name__ == "__main__":
    unittest.main()
