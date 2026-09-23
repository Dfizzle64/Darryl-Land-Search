"""Unit tests for DeKalb attribute mapping and municipal joins."""

from __future__ import annotations

import unittest

from dekalb_parcels import (
    apply_city_layers,
    apply_unincorporated,
    assign_jurisdictions,
    attribute_index,
    extent_rejection,
    lookup_parcel,
    map_assessment,
    parcel_keys,
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


def _parcel(lon: float, lat: float, parcel_id: str, jurisdiction: str | None = None) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "parcelId": parcel_id,
            "centroid": [lon, lat],
            "jurisdictionCode": jurisdiction,
            "zoningCode": None,
            "zoningDistrict": None,
            "flu": None,
            "lastSale": {"date": None, "price": None, "qualified": None},
            "opportunityZone": None,
            "oz2Eligibility": None,
            "_rollZoning": "R-100",
            "_rollLandUse": "SUB",
        },
        "geometry": {"type": "Polygon", "coordinates": []},
    }


class DekalbMappingTest(unittest.TestCase):
    def test_assessment_keeps_owner_tax_and_leaves_sales_empty(self) -> None:
        mapped = map_assessment(
            {
                "PARCELID": "06 249 01 004",
                "ACREAGE": 8.2,
                "SITEADDRESS": "2745 Bankers Industrial Drive Doraville, GA 30360",
                "CITY": "Doraville",
                "ZIP": "30360",
                "OWNERNME1": "BPVIF V HOLDINGS 5 LLC",
                "OWNERNME2": " ",
                "PSTLADDRESS": "1111 BROADWAY ST STE 1670",
                "PSTLCITY": "OAKLAND",
                "PSTLSTATE": "CA",
                "PSTLZIP5": "94607",
                "TOTAPR1": 9736900,
                "CNTASSDVAL": 3894760,
                "CNTTXBLVAL": 0,
                "ZONING": "M",
                "LANDUSE": None,
                "CVTTXDSCRP": "DORAVILLE-ANNEX",
                "SALE_PRICE": 100,
            }
        )
        self.assertIsNotNone(mapped)
        assert mapped is not None
        self.assertEqual(mapped["parcelId"], "06 249 01 004")
        self.assertEqual(mapped["acreage"], 8.2)
        self.assertEqual(mapped["ownerName"], "BPVIF V HOLDINGS 5 LLC")
        self.assertIsNone(mapped["ownerName2"])
        self.assertEqual(mapped["marketValue"], 9736900)
        self.assertEqual(mapped["assessedValue"], 3894760)
        self.assertIsNone(mapped["taxableValue"])
        self.assertEqual(mapped["taxDistrict"], "DORAVILLE-ANNEX")
        self.assertNotIn("salePrice", mapped)
        self.assertNotIn("saleDate", mapped)

    def test_acreage_band(self) -> None:
        self.assertIsNone(map_assessment({"PARCELID": "1", "ACREAGE": 4.9}))
        self.assertIsNone(map_assessment({"PARCELID": "1", "ACREAGE": 150.1}))
        self.assertIsNone(map_assessment({"PARCELID": " ", "ACREAGE": 10}))

    def test_parcel_keys_ignore_spacing(self) -> None:
        self.assertIn("1821901078", parcel_keys("18 219 01 078"))
        index = attribute_index([{"PARCEL_ID": "18 219 01 078", "ZONING": "RE"}], ["PARCEL_ID"])
        self.assertEqual(lookup_parcel(index, "1821901078")["ZONING"], "RE")


class DekalbExtentTest(unittest.TestCase):
    def test_rejects_decatur_illinois_and_other_dekalb_counties(self) -> None:
        il = extent_rejection((-89.03, 39.79, -88.80, 39.93), "https://maps.decaturil.gov/arcgis/rest/services/Public/zoning/FeatureServer/0/query")
        self.assertIn("Illinois", il or "")
        self.assertIn("Decatur", il or "")
        self.assertIn("Alabama", extent_rejection((-86.1, 34.4, -85.6, 34.8)) or "")
        self.assertIn("Illinois", extent_rejection((-88.9, 41.7, -88.5, 42.0)) or "")
        self.assertIn("Indiana", extent_rejection((-85.1, 41.3, -84.9, 41.5)) or "")
        self.assertIn("Tennessee", extent_rejection((-85.9, 35.9, -85.6, 36.1)) or "")

    def test_keeps_decatur_georgia_and_atlanta_citywide(self) -> None:
        self.assertIsNone(extent_rejection((-84.316, 33.751, -84.275, 33.794)))
        self.assertIsNone(extent_rejection((-84.551, 33.648, -84.290, 33.887)))
        self.assertIsNone(
            extent_rejection(
                (-84.316, 33.751, -84.275, 33.794),
                "https://services.arcgis.com/36QtML6Mf01B1N0W/arcgis/rest/services/Zoning/FeatureServer/0/query",
            )
        )


class DekalbJoinTest(unittest.TestCase):
    def _world(self) -> tuple[list[dict], list[dict]]:
        boundaries = [
            _square(-84.32, 33.75, -84.27, 33.80, {"NAME": "Decatur"}),
            _square(-84.30, 33.84, -84.27, 33.90, {"NAME": "Chamblee"}),
            _square(-84.40, 33.80, -84.30, 33.92, {"NAME": "Atlanta"}),
            _square(-84.20, 33.70, -84.15, 33.75, {"NAME": "Stone Mountain"}),
        ]
        features = [
            _parcel(-84.30, 33.77, "15 001", None),
            _parcel(-84.29, 33.86, "18 001", None),
            _parcel(-84.35, 33.85, "17 001", None),
            _parcel(-84.18, 33.72, "18 900", None),
            _parcel(-84.10, 33.70, "16 001", None),
        ]
        assign_jurisdictions(features, boundaries)
        return features, boundaries

    def test_cities_are_first_class_and_gaps_stay_blank(self) -> None:
        features, _boundaries = self._world()
        cities = [
            {
                "name": "Decatur",
                "join": "spatial",
                "zoning": {
                    "method": "spatial",
                    "spatial": _index([_square(-84.32, 33.75, -84.27, 33.80, {"ZONECLASS": "R-60", "ZONEDESC": "Single Family"})]),
                    "codeField": "ZONECLASS",
                    "labelField": "ZONEDESC",
                    "source": "decatur-ga-zoning",
                    "featureCount": 1,
                },
                "flu": {
                    "method": "spatial",
                    "spatial": _index([_square(-84.32, 33.75, -84.27, 33.80, {"LANDUSECODE": "RL", "LANDUSEDESC": "Low Density"})]),
                    "codeField": "LANDUSECODE",
                    "labelField": "LANDUSEDESC",
                    "source": "decatur-ga-flu",
                    "featureCount": 1,
                },
            },
            {
                "name": "Chamblee",
                "join": "attribute",
                "note": "FLU only",
                "zoning": None,
                "flu": {
                    "method": "attribute",
                    "index": attribute_index([{"PARCELID": "18 001", "LANDUSECODE": "MIX", "LANDUSEDESC": "Mixed Use"}], ["PARCELID"]),
                    "codeField": "LANDUSECODE",
                    "labelField": "LANDUSEDESC",
                    "source": "chamblee-flu",
                    "featureCount": 1,
                },
            },
            {
                "name": "Atlanta",
                "join": "spatial",
                "zoning": {
                    "method": "spatial",
                    "spatial": _index([_square(-84.55, 33.65, -84.29, 33.90, {"ZONECLASS": "RG-3"})]),
                    "codeField": "ZONECLASS",
                    "source": "atlanta-zoning",
                    "featureCount": 1,
                },
                "flu": None,
            },
            {
                "name": "Stone Mountain",
                "zoning": None,
                "flu": None,
                "fluGap": "No public zoning or future land use FeatureServer.",
            },
        ]
        summaries = apply_city_layers(features, cities)
        by_name = {row["name"]: row for row in summaries}
        decatur, chamblee, atlanta, stone, uninc = features
        self.assertEqual(decatur["properties"]["jurisdictionCode"], "Decatur")
        self.assertEqual(decatur["properties"]["zoningCode"], "R-60")
        self.assertEqual(decatur["properties"]["zoningDistrict"], "Decatur:R-60")
        self.assertEqual(decatur["properties"]["flu"]["jurisdiction"], "Decatur")
        self.assertIsNone(chamblee["properties"]["zoningCode"])
        self.assertEqual(chamblee["properties"]["flu"]["code"], "MIX")
        self.assertEqual(atlanta["properties"]["zoningDistrict"], "Atlanta:RG-3")
        self.assertIsNone(stone["properties"]["zoningCode"])
        self.assertIsNone(stone["properties"]["flu"])
        self.assertEqual(by_name["Chamblee"]["zoningJoined"], 0)
        self.assertEqual(by_name["Chamblee"]["fluJoined"], 1)
        self.assertEqual(by_name["Stone Mountain"]["zoningJoined"], 0)
        self.assertIn("No public", by_name["Stone Mountain"]["fluGap"])

        county = {
            "zoning": {
                "method": "spatial",
                "spatial": _index([_square(-84.5, 33.5, -84.0, 34.0, {"ZONECLASS": "M", "ZONEDESC": "Industrial"})]),
                "codeField": "ZONECLASS",
                "labelField": "ZONEDESC",
                "source": "dekalb-zoning",
                "featureCount": 1,
            },
            "flu": {
                "method": "spatial",
                "spatial": _index([_square(-84.5, 33.5, -84.0, 34.0, {"LANDUSECODE": "IND", "LANDUSEDESC": "Industrial"})]),
                "codeField": "LANDUSECODE",
                "labelField": "LANDUSEDESC",
                "source": "dekalb-flu",
                "featureCount": 1,
            },
        }
        stats = apply_unincorporated(features, county)
        self.assertEqual(decatur["properties"]["zoningCode"], "R-60")
        self.assertIsNone(chamblee["properties"]["zoningCode"])
        self.assertIsNone(stone["properties"]["zoningCode"])
        self.assertEqual(uninc["properties"]["jurisdictionCode"], "Unincorporated")
        self.assertEqual(uninc["properties"]["zoningDistrict"], "DeKalb:M")
        self.assertEqual(uninc["properties"]["flu"]["jurisdiction"], "DeKalb")
        self.assertEqual(stats["parcelCount"], 1)
        self.assertIsNone(decatur["properties"]["lastSale"]["price"])
        self.assertIsNone(decatur["properties"]["opportunityZone"])
        self.assertIsNone(decatur["properties"]["oz2Eligibility"])


def _index(features: list[dict]):
    from dekalb_parcels import SpatialIndex

    index = SpatialIndex()
    for feature in features:
        index.add(feature)
    return index


if __name__ == "__main__":
    unittest.main()
