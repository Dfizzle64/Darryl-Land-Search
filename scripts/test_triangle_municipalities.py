"""Routing and join tests for Triangle municipalities. No network."""

from __future__ import annotations

import unittest

from triangle_municipalities import (
    DURHAM_GAPS,
    FOLLOWUP_GAPS,
    TIP_IDS,
    WIRED_COUNTY_FIPS,
    MUNICIPALITIES,
    ZONING_LAYERS,
    appraiser_url,
    apply_triangle_joins,
    epoch_ms_to_iso,
    index_polygons,
    layers_for_county,
    place_type_for_county,
    route_municipalities,
    zoning_is_annotated,
    zoning_needs_polygon,
)


def _square(lon: float, lat: float, size: float = 0.02) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon, lat],
            [lon + size, lat],
            [lon + size, lat + size],
            [lon, lat + size],
            [lon, lat],
        ]],
    }


def _parcel(parcel_id: str, lon: float, lat: float, city: str | None, etj: str | None, zoning: str | None) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "parcelId": parcel_id,
            "centroid": [lon, lat],
            "zoningCode": None,
            "zoningDistrict": None,
            "flu": None,
            "dataGaps": [],
            "jurisdictionCode": None,
            "_durhamCity": city,
            "_durhamEtj": etj,
            "_zoningAttribute": zoning,
        },
        "geometry": _square(lon, lat, 0.001),
    }


class TriangleMunicipalityTests(unittest.TestCase):
    def test_routes_city_etj_and_mixed_labels(self) -> None:
        self.assertEqual(route_municipalities("CHAPEL HILL", "CHAPEL-HILL"), ["chapel-hill"])
        self.assertEqual(route_municipalities(None, "DURHAM COUNTY"), ["durham-county"])
        self.assertEqual(route_municipalities("DURHAM", "DURHAM CITY"), ["durham-city"])
        self.assertEqual(
            route_municipalities("DURHAM,CHAPEL HILL", "CHAPEL-HILL,DURHAM COUNTY"),
            ["durham-city", "chapel-hill", "durham-county"],
        )
        self.assertEqual(route_municipalities("CARY", None), ["cary"])
        self.assertEqual(route_municipalities(None, None), [])

    def test_null_and_tip_mixed_zoning_needs_a_polygon(self) -> None:
        self.assertTrue(zoning_needs_polygon(None, ["durham-city"]))
        self.assertTrue(zoning_needs_polygon("", ["durham-county"]))
        self.assertTrue(zoning_needs_polygon("CHAP HILL,R-1", ["chapel-hill"]))
        self.assertTrue(zoning_is_annotated("COUNTY,R-5-CZD"))
        self.assertTrue(zoning_needs_polygon("RS-8", ["chapel-hill"]))
        self.assertFalse(zoning_needs_polygon("RS-8", ["durham-city"]))
        self.assertFalse(zoning_needs_polygon("UC(D)", ["durham-city"]))

    def test_registry_keeps_wake_and_orange_as_follow_ups(self) -> None:
        self.assertEqual(WIRED_COUNTY_FIPS, {"37063"})
        self.assertIn("37183", FOLLOWUP_GAPS)
        self.assertIn("37135", FOLLOWUP_GAPS)
        by_id = {muni["id"]: muni for muni in MUNICIPALITIES}
        self.assertEqual(set(by_id), {"durham-city", "durham-county", "chapel-hill", "morrisville", "raleigh", "cary"})
        self.assertEqual(by_id["chapel-hill"]["counties"], ["37063", "37135"])
        self.assertIsNone(by_id["chapel-hill"]["flu"])
        self.assertEqual(by_id["raleigh"]["counties"], ["37063", "37183"])
        self.assertEqual(by_id["cary"]["counties"], ["37063", "37183"])
        self.assertEqual(by_id["morrisville"]["counties"], ["37063", "37183"])
        self.assertEqual({layer["id"] for layer in layers_for_county("37183")}, {"morrisville-zoning", "raleigh-zoning", "cary-zoning"})
        self.assertEqual([layer["id"] for layer in layers_for_county("37135")], ["chapel-hill-zoning"])
        self.assertIsNone(place_type_for_county("37183"))
        self.assertIsNone(place_type_for_county("37135"))
        self.assertIsNotNone(place_type_for_county("37063"))
        self.assertTrue(any("REID" in gap for gap in DURHAM_GAPS))
        self.assertTrue(any("ImageServer" in gap for gap in DURHAM_GAPS))
        cary = next(layer for layer in ZONING_LAYERS if layer["id"] == "cary-zoning")
        self.assertEqual(cary["outFields"], ["CLASS", "NAME"])
        self.assertTrue(all(muni in TIP_IDS for muni in ("chapel-hill", "morrisville", "raleigh", "cary")))

    def test_sale_epoch_and_appraiser_link(self) -> None:
        self.assertEqual(epoch_ms_to_iso(1639544460000), "2021-12-15")
        self.assertEqual(epoch_ms_to_iso(1475816460000), "2016-10-07")
        self.assertIsNone(epoch_ms_to_iso(None))
        self.assertIsNone(epoch_ms_to_iso(0))
        self.assertIn("PARCELPK=762", appraiser_url("100805", 762.0))
        self.assertTrue(appraiser_url("100000", None).endswith("REID=100000"))

    def test_join_keeps_durham_attribute_and_skips_tip_flu(self) -> None:
        udo, _ = index_polygons(
            [{"geometry": _square(-78.95, 35.99, 0.05), "attributes": {"UDO_LABEL": "RS-M", "ZONE_CODE": "RS-M", "ZONE_GEN": "RES"}}],
            next(layer["read"] for layer in ZONING_LAYERS if layer["id"] == "durham-udo"),
        )
        chapel, _ = index_polygons(
            [{"geometry": _square(-78.90, 35.90, 0.04), "attributes": {"ZONING": "R-1", "NAME": "Residential"}}],
            next(layer["read"] for layer in ZONING_LAYERS if layer["id"] == "chapel-hill-zoning"),
        )
        place, _ = index_polygons(
            [
                {
                    "geometry": _square(-78.96, 35.98, 0.08),
                    "attributes": {"PlaceType": "ATH", "PlaceTypeName": "Apartment & Townhouse Neighborhood"},
                }
            ],
            place_type_for_county("37063")["read"],
        )
        durham = _parcel("100", -78.94, 36.00, "DURHAM", "DURHAM CITY", "RS-8")
        empty = _parcel("101", -78.93, 36.01, "DURHAM", "DURHAM CITY", None)
        chapel_parcel = _parcel("140", -78.885, 35.92, "CHAPEL HILL", "CHAPEL-HILL", "CHAP HILL,R-1")
        stats = apply_triangle_joins(
            [durham, empty, chapel_parcel],
            {"durham-udo": udo, "chapel-hill-zoning": chapel},
            place,
        )
        self.assertEqual(durham["properties"]["zoningCode"], "RS-8")
        self.assertEqual(durham["properties"]["municipalityId"], "durham-city")
        self.assertEqual(durham["properties"]["flu"]["code"], "ATH")
        self.assertEqual(durham["properties"]["flu"]["jurisdiction"], "Durham")
        self.assertNotIn("_zoningAttribute", durham["properties"])
        self.assertEqual(empty["properties"]["zoningCode"], "RS-M")
        self.assertEqual(empty["properties"]["municipality"], "Durham")
        self.assertEqual(chapel_parcel["properties"]["zoningCode"], "R-1")
        self.assertEqual(chapel_parcel["properties"]["municipalityId"], "chapel-hill")
        self.assertIsNone(chapel_parcel["properties"]["flu"])
        self.assertTrue(any("ImageServer" in gap for gap in chapel_parcel["properties"]["dataGaps"]))
        self.assertGreaterEqual(stats["flu-joined"], 2)
        self.assertEqual(stats["flu-tip-gap"], 1)

    def test_city_tip_ignores_durham_etj_and_udo(self) -> None:
        udo, _ = index_polygons(
            [{"geometry": _square(-78.95, 35.99, 0.05), "attributes": {"UDO_LABEL": "RR", "ZONE_CODE": "RR"}}],
            next(layer["read"] for layer in ZONING_LAYERS if layer["id"] == "durham-udo"),
        )
        raleigh, _ = index_polygons([], next(layer["read"] for layer in ZONING_LAYERS if layer["id"] == "raleigh-zoning"))
        parcel = _parcel("157725", -78.94, 36.00, "RALEIGH", "DURHAM COUNTY", "RR")
        apply_triangle_joins([parcel], {"durham-udo": udo, "raleigh-zoning": raleigh}, None)
        self.assertEqual(parcel["properties"]["municipalityId"], "raleigh")
        self.assertEqual(parcel["properties"]["zoningCode"], "RR")
        self.assertIsNone(parcel["properties"]["flu"])

    def test_pure_tip_miss_does_not_borrow_durham_udo(self) -> None:
        udo, _ = index_polygons(
            [{"geometry": _square(-78.95, 35.99, 0.05), "attributes": {"UDO_LABEL": "RS-M", "ZONE_CODE": "RS-M"}}],
            next(layer["read"] for layer in ZONING_LAYERS if layer["id"] == "durham-udo"),
        )
        chapel, _ = index_polygons([], next(layer["read"] for layer in ZONING_LAYERS if layer["id"] == "chapel-hill-zoning"))
        parcel = _parcel("140", -78.94, 36.00, "CHAPEL HILL", "CHAPEL-HILL", "R-4")
        apply_triangle_joins([parcel], {"durham-udo": udo, "chapel-hill-zoning": chapel}, None)
        self.assertEqual(parcel["properties"]["zoningCode"], "R-4")
        self.assertEqual(parcel["properties"]["municipalityId"], "chapel-hill")
        self.assertIsNone(parcel["properties"]["flu"])
        self.assertTrue(any("attribute kept" in gap for gap in parcel["properties"]["dataGaps"]))


if __name__ == "__main__":
    unittest.main()
