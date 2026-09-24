"""Unit tests for Henderson County routing, the Cities stub, and FLU fallback."""

from __future__ import annotations

import unittest

from henderson_parcels import (
    SpatialIndex,
    apply_land_use,
    canonical_city,
    is_stub_zone,
    map_parcel_attributes,
    parse_sale_date,
    route_jurisdiction,
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


def _parcel(lon: float, lat: float, **props) -> dict:
    base = {
        "centroid": [lon, lat],
        "parcelId": "9577786298",
        "situsCity": None,
        "zoningAggregated": "Cities",
        "cityCode": None,
        "etj": "COUNTY",
        "zoningCode": None,
        "zoningDistrict": None,
        "jurisdictionPrefix": None,
        "flu": None,
    }
    base.update(props)
    return {"type": "Feature", "properties": base, "geometry": {"type": "Polygon", "coordinates": []}}


class HendersonMappingTest(unittest.TestCase):
    def test_flat_rock_tax_subtypes_do_not_route_alone(self) -> None:
        self.assertIsNone(canonical_city("FLAT ROCK VH"))
        self.assertIsNone(canonical_city("FLAT ROCK BR"))
        self.assertEqual(canonical_city("FLAT ROCK"), "Flat Rock")
        self.assertEqual(
            route_jurisdiction(boundary_cities=[], etj="COUNTY", city_code="FLAT ROCK VH"),
            (None, "county"),
        )
        self.assertEqual(
            route_jurisdiction(boundary_cities=[], etj="FLAT ROCK", city_code="FLAT ROCK VH"),
            ("Flat Rock", "etj"),
        )
        self.assertEqual(
            route_jurisdiction(boundary_cities=["Flat Rock"], etj="COUNTY", city_code="FLAT ROCK GR"),
            ("Flat Rock", "limits"),
        )

    def test_cities_first_order(self) -> None:
        self.assertEqual(
            route_jurisdiction(boundary_cities=["Fletcher", "Hendersonville"], etj="COUNTY", city_code=None),
            ("Hendersonville", "limits"),
        )

    def test_sale_date_and_parcel_pk(self) -> None:
        mapped = map_parcel_attributes(
            {
                "PIN": "0507003820",
                "PARCEL_PK": 113959.0,
                "CALCULATED_ACRES": 12.5,
                "PROPERTY_OWNER": "EXAMPLE LLC",
                "LOCATION_ADDR": "0 NO ADDRESS ASSIGNED",
                "PHYADDR_CITY": "HENDERSONVILLE",
                "PKG_SALE_DATE": 1590695820000,
                "PKG_SALE_PRICE": 619000,
                "TOTAL_PROP_VALUE": 100000,
                "TOTAL_LAND_VALUE_ASSESSED": 80000,
                "TOTAL_BLDG_VALUE_ASSESSED": 20000,
                "Zoning_aggregated": "Cities",
                "CITY": "HENDERSONVILLE",
                "ETJ": "HENDERSONVILLE",
                "LAND_CLASS": "VACANT LAND",
            }
        )
        assert mapped is not None
        self.assertEqual(mapped["parcelId"], "0507003820")
        self.assertIsNone(mapped["situs"])
        self.assertEqual(mapped["saleDate"], parse_sale_date(1590695820000))
        self.assertEqual(mapped["saleDate"], "2020-05-28")
        self.assertEqual(mapped["assessed"], 100000)
        self.assertTrue(mapped["appraiserUrl"].endswith("/parcel-detail/113959"))
        self.assertTrue(is_stub_zone("Cities"))
        self.assertTrue(is_stub_zone("NO"))
        self.assertFalse(is_stub_zone("R2R"))

    def test_stub_is_not_zoning_and_city_flu_wins_inside_limits(self) -> None:
        boundaries = SpatialIndex()
        boundaries.add(_square(-82.5, 35.3, -82.4, 35.4, {"CITY": "HENDERSONVILLE"}))
        city = SpatialIndex()
        city.add(_square(-82.5, 35.3, -82.4, 35.4, {"Zoning": "R-1", "Zoning_Cla": "Residential"}))
        county = SpatialIndex()
        county.add(_square(-82.6, 35.2, -82.3, 35.5, {"ZONE_CODE": "Cities", "ZONING": "Cities"}))
        county.add(_square(-82.6, 35.2, -82.3, 35.5, {"ZONE_CODE": "R2R", "ZONING": "Residential 2 Rural"}))
        flu = SpatialIndex()
        flu.add(_square(-82.6, 35.2, -82.3, 35.5, {"FLU": "AR", "Land_Use": "Agriculture/Rural"}))
        parcel = _parcel(-82.45, 35.35, cityCode="HENDERSONVILLE", etj="HENDERSONVILLE")
        apply_land_use(
            parcel,
            boundaries=boundaries,
            zoning={"Hendersonville": city},
            county_zoning=county,
            county_flu=flu,
            hvl_flu_by_pin={"9577786298": "Family/Neighborhood Living"},
        )
        self.assertEqual(parcel["properties"]["zoningCode"], "R-1")
        self.assertEqual(parcel["properties"]["jurisdictionPrefix"], "Hendersonville")
        self.assertNotEqual(parcel["properties"]["zoningCode"], "Cities")
        self.assertEqual(parcel["properties"]["flu"]["source"], "hendersonville-2045-flu")
        outside = _parcel(-82.2, 35.1, parcelId="9577786298", cityCode="HENDERSONVILLE", etj="HENDERSONVILLE")
        apply_land_use(
            outside,
            boundaries=None,
            zoning={"Hendersonville": city},
            county_zoning=county,
            county_flu=flu,
            hvl_flu_by_pin={"9577786298": "Family/Neighborhood Living"},
        )
        self.assertEqual(outside["properties"]["flu"]["source"], "hendersonville-2045-flu")
        self.assertNotIn("zoningAggregated", parcel["properties"])

    def test_county_stub_polygons_are_skipped(self) -> None:
        county = SpatialIndex()
        county.add(_square(-82.8, 35.2, -82.6, 35.4, {"ZONE_CODE": "NO", "ZONING": "Municipal"}))
        county.add(_square(-82.8, 35.2, -82.6, 35.4, {"ZONE_CODE": "Cities", "ZONING": "Cities"}))
        real = SpatialIndex()
        real.add(_square(-82.7, 35.25, -82.65, 35.35, {"ZONE_CODE": "R1", "ZONING": "Residential 1"}))
        skipped = _parcel(-82.68, 35.3, zoningAggregated="Cities")
        apply_land_use(
            skipped,
            boundaries=None,
            zoning={},
            county_zoning=county,
            county_flu=None,
            hvl_flu_by_pin={},
        )
        self.assertIsNone(skipped["properties"]["zoningCode"])

        kept = _parcel(-82.68, 35.3, zoningAggregated="Residential 2 - Rural")
        apply_land_use(
            kept,
            boundaries=None,
            zoning={},
            county_zoning=real,
            county_flu=None,
            hvl_flu_by_pin={},
        )
        self.assertEqual(kept["properties"]["zoningCode"], "R1")
        self.assertEqual(kept["properties"]["jurisdictionPrefix"], "Henderson County")

    def test_gap_city_uses_county_flu_not_a_city_plan(self) -> None:
        boundaries = SpatialIndex()
        boundaries.add(_square(-82.55, 35.4, -82.45, 35.5, {"CITY": "FLETCHER"}))
        fletcher = SpatialIndex()
        fletcher.add(_square(-82.55, 35.4, -82.45, 35.5, {"Zoning": "R-1"}))
        flu = SpatialIndex()
        flu.add(_square(-82.6, 35.3, -82.4, 35.55, {"FLU": "TA", "Land_Use": "Transitional Area"}))
        parcel = _parcel(-82.5, 35.45, parcelId="100", cityCode="FLETCHER", etj="FLETCHER", zoningAggregated="Cities")
        apply_land_use(
            parcel,
            boundaries=boundaries,
            zoning={"Fletcher": fletcher},
            county_zoning=None,
            county_flu=flu,
            hvl_flu_by_pin={"100": "Downtown"},
        )
        self.assertEqual(parcel["properties"]["zoningCode"], "R-1")
        self.assertEqual(parcel["properties"]["jurisdictionPrefix"], "Fletcher")
        self.assertEqual(parcel["properties"]["flu"]["source"], "henderson-county-flu-2024")
        self.assertEqual(parcel["properties"]["flu"]["jurisdiction"], "Henderson County")
        self.assertIn("No dedicated public FLU for Fletcher", " ".join(parcel["properties"]["dataGaps"]))


if __name__ == "__main__":
    unittest.main()
