"""Offline checks for Rutherford parcel mapping. Network enrich is not required."""

from __future__ import annotations

import unittest

from rutherford_parcels import (
    APPRAISER_URL,
    assign_overlays,
    join_owners,
    normalize_rutherford_feature,
    situs_address,
)
from seed_market_parcels import centroid_of, empty_feature, in_band, plausible_centroid, rings_to_feature_geometry


def square(lon: float, lat: float) -> dict:
    ring = [
        [lon, lat],
        [lon + 0.01, lat],
        [lon + 0.01, lat + 0.01],
        [lon, lat + 0.01],
        [lon, lat],
    ]
    return {"rings": [ring]}


def parcel(attrs: dict) -> dict:
    feature = normalize_rutherford_feature(
        attrs,
        square(-86.48, 35.78),
        county={"fips": "47149", "name": "Rutherford", "state": "Tennessee"},
        markets=["Nashville"],
        empty_feature=empty_feature,
        rings_to_feature_geometry=rings_to_feature_geometry,
        centroid_of=centroid_of,
        plausible_centroid=plausible_centroid,
        in_band=in_band,
    )
    assert feature is not None
    return feature


class RutherfordMappingTest(unittest.TestCase):
    def test_owners_situs_sale_tax_and_ids(self) -> None:
        self.assertEqual(join_owners({"Owner1": " A ", "Owner2": "", "Owner3": "B"}), ("A", "B"))
        self.assertEqual(situs_address({"STREETADDRESS": None, "FormattedLocation": "5989 MORGAN RD"}), "5989 MORGAN RD")
        feature = parcel(
            {
                "PARCEL_TYPE": 1,
                "ParcelID": "140-015.02-000",
                "GISLINK": "140    01502",
                "PropertyID": 79969,
                "CAMAACCT": "R0079969",
                "CITYCODE": "000",
                "CALCACRES": 45.67,
                "DEEDACRES": 46.89,
                "Owner1": "TIDWELL LIVING TRUST",
                "Owner2": "TIDWELL TRUSTEE JAMES SETH",
                "Owner3": "",
                "MailingAddress": "5989 MORGAN RD",
                "MailingCity": "ROCKVALE",
                "MailingState": "TN",
                "MailingZipCode": "37153",
                "STREETADDRESS": None,
                "FormattedLocation": "5989 MORGAN RD",
                "CITY": "ROCKVALE",
                "ZIP": "37153",
                "SaleDate": 1502082000000,
                "SalePrice": 0,
                "LegalReference": "1597-3182",
                "Grantor": "TIDWELL JAMES S ETUX",
                "Grantee": "TIDWELL LIVING TRUST",
                "TotalLandValue": 123200,
                "TotalBuildingValue": 324000,
                "TotalYardItemValue": 12000,
                "TotalValue": 459200,
                "TotalAssessedValue": 114800,
                "TotalLandValueWithAg": 598457,
                "AgriculturalCredit": 475257,
                "ZONING": None,
            }
        )
        props = feature["properties"]
        self.assertEqual(props["id"], "47149:140-015.02-000")
        self.assertEqual(props["parcelId"], "140-015.02-000")
        self.assertEqual(props["gisLink"], "140    01502")
        self.assertEqual(props["cityCode"], "000")
        self.assertEqual(props["jurisdictionPrefix"], "RUT")
        self.assertEqual(props["ownerName"], "TIDWELL LIVING TRUST")
        self.assertEqual(props["ownerName2"], "TIDWELL TRUSTEE JAMES SETH")
        self.assertEqual(props["situsAddress"], "5989 MORGAN RD")
        self.assertEqual(props["mailingAddress"]["state"], "TN")
        self.assertEqual(props["lastSale"]["date"], "2017-08-07")
        self.assertIsNone(props["lastSale"]["price"])
        self.assertEqual(props["lastSale"]["legalReference"], "1597-3182")
        self.assertEqual(props["tax"]["marketValue"], 459200)
        self.assertEqual(props["tax"]["assessedValue"], 114800)
        self.assertEqual(props["tax"]["landValue"], 123200)
        self.assertEqual(props["tax"]["buildingValue"], 324000)
        self.assertIsNone(props["tax"]["taxableValue"])
        self.assertEqual(props["appraiserUrl"], APPRAISER_URL)
        self.assertEqual(props["acreage"], 45.67)
        self.assertIsNone(props["flu"])
        self.assertNotIn("IMPACT", props["source"])

    def test_drops_rows_outside_the_band_or_wrong_subtype(self) -> None:
        self.assertIsNone(
            normalize_rutherford_feature(
                {"PARCEL_TYPE": 1, "ParcelID": "x", "CALCACRES": 4.9, "CITYCODE": "000"},
                square(-86.48, 35.78),
                county={"fips": "47149", "name": "Rutherford", "state": "Tennessee"},
                markets=["Nashville"],
                empty_feature=empty_feature,
                rings_to_feature_geometry=rings_to_feature_geometry,
                centroid_of=centroid_of,
                plausible_centroid=plausible_centroid,
                in_band=in_band,
            )
        )
        self.assertIsNone(
            normalize_rutherford_feature(
                {"PARCEL_TYPE": 2, "ParcelID": "x", "CALCACRES": 10, "CITYCODE": "000"},
                square(-86.48, 35.78),
                county={"fips": "47149", "name": "Rutherford", "state": "Tennessee"},
                markets=["Nashville"],
                empty_feature=empty_feature,
                rings_to_feature_geometry=rings_to_feature_geometry,
                centroid_of=centroid_of,
                plausible_centroid=plausible_centroid,
                in_band=in_band,
            )
        )

    def test_city_code_routes_zoning_and_flu(self) -> None:
        city = parcel({"PARCEL_TYPE": 1, "ParcelID": "city", "CITYCODE": "515", "CALCACRES": 12, "ZONING": "OLD"})
        town = parcel({"PARCEL_TYPE": 1, "ParcelID": "town", "CITYCODE": "674", "CALCACRES": 12, "ZONING": "OLD"})
        rural = parcel(
            {
                "PARCEL_TYPE": 1,
                "ParcelID": "rural",
                "CITYCODE": "000",
                "CALCACRES": 12,
                "GISLINK": "140    01502",
                "ZONING": None,
            }
        )
        eagle = parcel({"PARCEL_TYPE": 1, "ParcelID": "eagle", "CITYCODE": "227", "CALCACRES": 12, "ZONING": "R-1"})
        # Same point hits every index. Routing must still follow CITYCODE.
        shared = {
            "type": "Feature",
            "geometry": city["geometry"],
            "properties": {"district": "SHOULD-NOT-LEAK", "label": "nope"},
        }

        class Always:
            def hit(self, _x: float, _y: float) -> dict:
                return shared

        mur = Always()
        mur.properties_payload = {"district": "RM-12", "label": "RM"}  # type: ignore[attr-defined]

        class Index:
            def __init__(self, district: str, label: str | None = None, flu: dict | None = None) -> None:
                self.payload = flu or {"district": district, "label": label}

            def hit(self, _x: float, _y: float) -> dict:
                return {"properties": self.payload}

        stats = assign_overlays(
            [city, town, rural, eagle],
            murfreesboro=Index("RM-12", "Residential"),  # type: ignore[arg-type]
            smyrna=Index("R-5", "R-5 HIGH DENSITY RESIDENTIAL"),  # type: ignore[arg-type]
            smyrna_source="smyrna-town-mapserver-24",
            lavergne=Index("C-4"),  # type: ignore[arg-type]
            county_zoning=Index("RMF", "RESIDENTIAL MULTI-FAMILY"),  # type: ignore[arg-type]
            rsa=Index("", flu={"code": "MUR-MF", "label": "Multifamily", "source": "murfreesboro-rsa-flu-2023"}),  # type: ignore[arg-type]
            characters={"140    01502": {"code": "RUT-SFR", "label": "SFR · R", "jurisdiction": "RUT", "source": "rutherford-character-areas"}},
        )
        self.assertEqual(city["properties"]["zoningCode"], "MUR-RM-12")
        self.assertEqual(city["properties"]["zoningSource"], "murfreesboro-govunits-zoning")
        self.assertEqual(city["properties"]["flu"]["code"], "MUR-MF")
        self.assertNotEqual(city["properties"]["flu"]["source"], "rutherford-character-areas")
        self.assertEqual(town["properties"]["zoningCode"], "SMY-R-5")
        self.assertIsNone(town["properties"]["flu"])
        self.assertEqual(rural["properties"]["zoningCode"], "RUT-RMF")
        self.assertEqual(rural["properties"]["flu"]["source"], "rutherford-character-areas")
        self.assertEqual(eagle["properties"]["zoningCode"], "EAG-R-1")
        self.assertEqual(eagle["properties"]["zoningSource"], "eagleville-parcel-attribute")
        self.assertIsNone(eagle["properties"]["flu"])
        self.assertGreater(stats["murfreesboroZoning"], 0)
        self.assertIn("2025-10-09", " ".join(parcel({"PARCEL_TYPE": 1, "ParcelID": "lv", "CITYCODE": "400", "CALCACRES": 8})["properties"]["dataGaps"]))


if __name__ == "__main__":
    unittest.main()
