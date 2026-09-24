"""Unit checks for Tuscaloosa and Montgomery specs. No network."""

from __future__ import annotations

import unittest

from al_msa_parcels import (
    FRAMEWORK_ZONING_SERVICE,
    NY_MONTGOMERY_ORG,
    NY_MONTGOMERY_PARCEL_MIRROR,
    PARCEL_SPECS,
    WETUMPKA_ZONING_SERVICE,
    al_county_spec,
    apply_joins_local,
    assert_public_alabama_url,
    epoch_to_iso,
    parcel_key,
    parcel_only_market_summaries,
    summarize_joined,
)


def square(west: float, south: float, east: float, north: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
    }


class AlMsaParcelTests(unittest.TestCase):
    def test_rejects_ny_mirror_wetumpka_and_framework(self):
        for url in (NY_MONTGOMERY_PARCEL_MIRROR, WETUMPKA_ZONING_SERVICE, FRAMEWORK_ZONING_SERVICE):
            with self.assertRaises(RuntimeError):
                assert_public_alabama_url(url)
        for spec in PARCEL_SPECS.values():
            self.assertNotIn(NY_MONTGOMERY_ORG, spec["url"])
            self.assertNotIn("Montgomery_County_Parcels", spec["url"])
            self.assertNotIn("Framework_Zoning_Map", spec["url"])
            self.assertNotIn("6AasMFHPoqawuioF", spec["url"])
            assert_public_alabama_url(spec["url"])
        montgomery = al_county_spec("01101")
        self.assertIsNotNone(montgomery)
        assert montgomery is not None
        self.assertIn("gis.montgomeryal.gov", montgomery["url"])
        self.assertNotIn("salePriceField", montgomery)

    def test_parcel_key_strips_northport_punctuation(self):
        self.assertEqual(parcel_key("31-01-02-3-001-056.035"), "3101023001056035")
        self.assertEqual(parcel_key("0101110000002000"), "0101110000002000")
        self.assertIsNone(parcel_key(" "))
        self.assertIsNone(parcel_key(None))

    def test_epoch_date_only(self):
        self.assertEqual(epoch_to_iso(1544594400000), "2018-12-12")
        self.assertEqual(epoch_to_iso("2018-12-12T06:00:00Z"), "2018-12-12")
        self.assertIsNone(epoch_to_iso(None))
        self.assertIsNone(epoch_to_iso(0))

    def test_local_join_keeps_sale_price_null_and_prefers_northport_key(self):
        prepared = {
            "northportByKey": {
                "1906240001004000": {
                    "jurisdiction": "Northport",
                    "code": "RS-SD",
                    "label": "20-RS-SD",
                    "key": "1906240001004000",
                    "vintage": None,
                    "area": 10,
                    "bbox": (-87.6, 33.2, -87.5, 33.3),
                    "geometry": square(-87.6, 33.2, -87.5, 33.3),
                }
            },
            "northport": {},
            "tuscaloosa": {},
            "flu": {},
            "montgomery": {},
            "millbrook": {},
            "prattville": {},
        }
        feature = {
            "properties": {
                "parcelId": "1906240001004000",
                "centroid": [-87.55, 33.25],
                "lastSale": {"date": "2018-12-12", "price": 250000, "qualified": "Q"},
                "zoningCode": None,
                "flu": None,
            }
        }
        apply_joins_local([feature], "tuscaloosa", prepared, "https://www.alabamagis.com/tuscaloosa/")
        props = feature["properties"]
        self.assertEqual(props["zoningCode"], "RS-SD")
        self.assertEqual(props["jurisdictionCode"], "Northport")
        self.assertIsNone(props["lastSale"]["price"])
        self.assertEqual(props["lastSale"]["date"], "2018-12-12")
        self.assertIsNone(props["oz2Eligibility"])
        self.assertIsNone(props["opportunityZone"])
        stats = summarize_joined([feature])
        self.assertEqual(stats["salePriceNonNull"], 0)
        self.assertEqual(stats["zoningJoined"], 1)

    def test_prattville_join_flags_vintage_and_does_not_invent_a_price(self):
        zone = {
            "jurisdiction": "Prattville",
            "code": "R-2",
            "label": None,
            "key": None,
            "vintage": "partial",
            "area": 1,
            "bbox": (-86.5, 32.4, -86.4, 32.5),
            "geometry": square(-86.5, 32.4, -86.4, 32.5),
        }
        from al_msa_parcels import _index_zones

        prepared = {
            "northportByKey": {},
            "northport": {},
            "tuscaloosa": {},
            "flu": {},
            "montgomery": {},
            "millbrook": {},
            "prattville": _index_zones([zone]),
        }
        inside = {
            "properties": {
                "parcelId": "1",
                "centroid": [-86.45, 32.45],
                "lastSale": {"date": None, "price": None, "qualified": None},
            }
        }
        outside = {
            "properties": {
                "parcelId": "2",
                "centroid": [-86.1, 32.2],
                "lastSale": {"date": None, "price": None, "qualified": None},
            }
        }
        apply_joins_local([inside, outside], "autauga", prepared, None)
        self.assertEqual(inside["properties"]["jurisdictionCode"], "Prattville")
        self.assertTrue(any("1987" in gap for gap in inside["properties"]["dataGaps"]))
        self.assertIsNone(inside["properties"]["lastSale"]["price"])
        self.assertIsNone(outside["properties"]["zoningCode"])
        self.assertIsNone(outside["properties"].get("flu"))

    def test_parcel_only_markets_add_no_eligible_rows(self):
        stubs = parcel_only_market_summaries()
        self.assertEqual([item["market"] for item in stubs], ["Tuscaloosa", "Montgomery"])
        for item in stubs:
            self.assertEqual(item["rowCount"], 0)
            self.assertEqual(item["ruralCount"], 0)
            self.assertEqual(item["urbanCount"], 0)
            self.assertTrue(item["parcelOnly"])
            self.assertRegex(item["eligibleTractNote"], r"(?i)marked designated")
            self.assertNotRegex(item["eligibleTractNote"], r"(?i)^designated")


if __name__ == "__main__":
    unittest.main()
