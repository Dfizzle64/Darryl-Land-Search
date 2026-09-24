"""Unit tests for Iredell attribute mapping and the municipal spatial join."""

from __future__ import annotations

import unittest

from iredell_parcels import (
    SpatialIndex,
    apply_land_use,
    assemble_situs,
    is_horizon_stub,
    map_taxsql_attributes,
    normalize_pin,
    parse_sale_date,
    zoning_from_mooresville,
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
        "situsCity": None,
        "zoningAttribute": "RA",
        "jurisdictionPrefix": None,
        "zoningCode": None,
        "flu": None,
    }
    base.update(props)
    return {"type": "Feature", "properties": base, "geometry": {"type": "Polygon", "coordinates": []}}


class IredellMappingTest(unittest.TestCase):
    def test_pin_strips_only_zero_fraction(self) -> None:
        self.assertEqual(normalize_pin("4751155000.000"), "4751155000")
        self.assertEqual(normalize_pin("4751155000.100"), "4751155000.100")
        self.assertIsNone(normalize_pin("  "))

    def test_situs_skips_empty_parts(self) -> None:
        self.assertEqual(
            assemble_situs({"HouseNumber": "141", "SDIR": None, "STREET": "PEAR TREE", "STYPE": "RD", "ST_SUFFIX": None}),
            "141 PEAR TREE RD",
        )
        self.assertEqual(
            assemble_situs({"HouseNumber": "", "STREET": "MOUNTAIN VIEW", "STYPE": "RD"}),
            "MOUNTAIN VIEW RD",
        )

    def test_sale_date_and_market_factor(self) -> None:
        attrs = {
            "PIN": "4751155000.000",
            "TaxAcres": 24,
            "Jan1Own1": "KELLY RAYMOND SCOTT REVOCABLE TRUST",
            "Jan1Own2": "",
            "Name": "KELLY RAYMOND S REVOC TRUST",
            "ADD1": "141 PEAR TREE RD",
            "CITY": "TROUTMAN",
            "STATE": "NC",
            "ZIP": "28166",
            "HouseNumber": "141",
            "STREET": "PEAR TREE",
            "STYPE": "RD",
            "CityLocationDescription": "00",
            "Sale_Date": "10/12/2017",
            "Sales_Price": 71500,
            "QualifiedCode": "Q",
            "Total_Value": 431430,
            "Zoning": "RA",
            "Land_Use_Code": "0120",
            "Market": 1.1,
        }
        mapped = map_taxsql_attributes(attrs)
        assert mapped is not None
        self.assertEqual(mapped["parcelId"], "4751155000")
        self.assertEqual(mapped["saleDate"], "2017-10-12")
        self.assertEqual(mapped["owner"], "KELLY RAYMOND SCOTT REVOCABLE TRUST")
        self.assertIsNone(mapped["owner2"])
        self.assertIsNone(mapped["city"])
        self.assertEqual(mapped["mailCity"], "TROUTMAN")
        self.assertIsNone(mapped["marketValue"])
        self.assertEqual(mapped["assessed"], 431430)
        self.assertEqual(parse_sale_date("12/18/2020"), "2020-12-18")
        zero = map_taxsql_attributes({**attrs, "Sales_Price": 0})
        assert zero is not None
        self.assertIsNone(zero["salePrice"])

    def test_horizon_stubs_are_not_flu(self) -> None:
        self.assertTrue(is_horizon_stub("Mooresville Municipal Planning Area"))
        self.assertTrue(is_horizon_stub("Statesville Municipal Planning Area"))
        self.assertFalse(is_horizon_stub("Low-Density Residential"))

    def test_mooresville_overlay_prefers_tax_code(self) -> None:
        code, district = zoning_from_mooresville({"ZDISPLAY": "CZ", "ZoningTax": "C-RG"})
        self.assertEqual(code, "C-RG")
        self.assertEqual(district, "CZ")

    def test_spatial_join_prefers_town_zoning_and_skips_stubs(self) -> None:
        town = SpatialIndex()
        town.add(_square(-80.81, 35.59, -80.79, 35.61, {"ZDISPLAY": "R-3", "ZoningTax": "R-3"}))
        county = SpatialIndex()
        county.add(_square(-80.9, 35.5, -80.7, 35.7, {"ZONING": "RA", "ZDISPLAY": "RA"}))
        horizon = SpatialIndex()
        horizon.add(_square(-80.9, 35.5, -80.7, 35.7, {"FUTURE_LANDUSE": "Mooresville Municipal Planning Area"}))
        fclu = SpatialIndex()
        fclu.add(_square(-80.81, 35.59, -80.79, 35.61, {"F2019_LU_1": "NRES"}))
        mooresville = _parcel(-80.8, 35.6, situsCity="Mooresville")
        apply_land_use(
            mooresville,
            zoning_layers=[
                {"name": "Mooresville", "kind": "mooresville", "index": town},
                {"name": "Iredell", "kind": "county", "index": county},
            ],
            city_limits=None,
            fclu=fclu,
            horizon=horizon,
        )
        self.assertEqual(mooresville["properties"]["zoningCode"], "R-3")
        self.assertEqual(mooresville["properties"]["jurisdictionPrefix"], "Mooresville")
        self.assertEqual(mooresville["properties"]["flu"]["code"], "NRES")
        self.assertEqual(mooresville["properties"]["flu"]["source"], "mooresville-fclu")
        self.assertNotIn("zoningAttribute", mooresville["properties"])

        rural = _parcel(-80.85, 35.65)
        apply_land_use(
            rural,
            zoning_layers=[{"name": "Iredell", "kind": "county", "index": county}],
            city_limits=None,
            fclu=fclu,
            horizon=horizon,
        )
        self.assertEqual(rural["properties"]["zoningCode"], "RA")
        self.assertIsNone(rural["properties"]["flu"])

        open_space = SpatialIndex()
        open_space.add(_square(-80.9, 35.5, -80.7, 35.7, {"FUTURE_LANDUSE": "Rural Conservation"}))
        kept = _parcel(-80.85, 35.65)
        apply_land_use(
            kept,
            zoning_layers=[{"name": "Iredell", "kind": "county", "index": county}],
            city_limits=None,
            fclu=None,
            horizon=open_space,
        )
        self.assertEqual(kept["properties"]["flu"]["source"], "iredell-horizon-2030")
        self.assertEqual(kept["properties"]["flu"]["code"], "Rural Conservation")

        statesville = _parcel(-80.85, 35.65, situsCity="Statesville")
        apply_land_use(
            statesville,
            zoning_layers=[{"name": "Statesville", "kind": "county", "index": county}],
            city_limits=None,
            fclu=fclu,
            horizon=open_space,
        )
        self.assertIsNone(statesville["properties"]["flu"])
        self.assertIn("No public FLU layer for this municipality.", statesville["properties"]["dataGaps"])


if __name__ == "__main__":
    unittest.main()
