"""Unit tests for Forsyth County, North Carolina (MapForsyth), not Forsyth GA."""

from __future__ import annotations

import unittest

from forsyth_parcels import (
    FLU_LAYER,
    GEORGIA_FIPS,
    HP_ZONING,
    KE_ZONING,
    PARCEL_LAYER,
    SOURCE,
    SpatialIndex,
    apply_land_use,
    assert_nc_forsyth,
    assert_public_nc,
    cast_money,
    gma_suffix,
    map_parcel_attributes,
    parse_city_st_zip,
    parse_epoch_date,
    pin_key,
    viewer_url,
    _latest_qualified_sales,
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
        "joinPoint": [lon, lat],
        "situsCity": None,
        "pinKey": pin_key("6836-42-3032.00"),
        "zoningAttribute": "AG",
        "zoningCode": None,
        "jurisdictionPrefix": None,
        "jurisdictionCode": None,
        "flu": None,
        "lastSale": {"date": "2017-02-24", "price": None, "qualified": None},
        "tax": {"marketValue": None, "assessedValue": 100, "taxableValue": None, "taxes": None},
    }
    base.update(props)
    return {"type": "Feature", "properties": base, "geometry": {"type": "Polygon", "coordinates": []}}


def _index(feature: dict) -> SpatialIndex:
    index = SpatialIndex()
    index.add(feature)
    return index


class ForsythNcTest(unittest.TestCase):
    def test_rejects_forsyth_georgia(self) -> None:
        with self.assertRaises(RuntimeError):
            assert_nc_forsyth({"name": "Forsyth", "state": "Georgia", "fips": GEORGIA_FIPS})
        with self.assertRaises(RuntimeError):
            assert_public_nc("https://gis.forsythco.com/arcgis/rest/services/Parcels/MapServer/0")
        self.assertIn("Parcels_Hosted", PARCEL_LAYER)
        self.assertNotIn("cumming", PARCEL_LAYER.lower())
        assert_nc_forsyth({"name": "Forsyth", "state": "North Carolina", "fips": "37067"})

    def test_pin_and_mailing_and_money(self) -> None:
        self.assertEqual(pin_key("6836-42-3032.00"), pin_key("6836-42-3032.000"))
        self.assertEqual(pin_key("  6844-25-3548.00          "), "6844-25-3548")
        self.assertEqual(pin_key("5892-33-9988.010"), "5892-33-9988.01")
        self.assertEqual(parse_city_st_zip("WINSTON-SALEM NC 27105"), ("WINSTON-SALEM", "NC", "27105"))
        self.assertEqual(parse_epoch_date(1487894400000), "2017-02-24")
        self.assertIsNone(cast_money("0"))
        self.assertEqual(cast_money("6,571,700"), 6571700)
        self.assertEqual(gma_suffix("5"), "GMA 5 (Rural)")
        self.assertIn("/forsyth/parcel-detail/1541", viewer_url(1541, None))

    def test_parcel_attribute_map(self) -> None:
        mapped = map_parcel_attributes(
            {
                "TAXPIN": "6836-42-3032.00",
                "PIN": "6836-42-3032.00",
                "PARCEL_PK": 1541,
                "CALCULATEDACREAGE": 9.85,
                "CURRENTOWNERNAME1": "PLANT 1325 LLC",
                "CURRENTOWNERNAME2": None,
                "CURRENTOWNERADDRESS": "1325 IVY AVENUE",
                "CURRENTOWNERCITYSTZIP": "WINSTON-SALEM NC 27105",
                "PROPERTYADDRESS": "1325  Ivy AVE ",
                "CURRENTDEEDDATE": 1487894400000,
                "LASTQUALIFIEDSALEPRICE": 0,
                "TOTALVALUE": "0",
                "PRZONING": "GI; RM5",
                "Detailed_Property_Info_Link": "https://lrcpwa.ncptscloud.com/forsyth/parcel-detail/1541",
            }
        )
        assert mapped is not None
        self.assertEqual(mapped["situs"], "1325 Ivy AVE")
        self.assertEqual(mapped["mailCity"], "WINSTON-SALEM")
        self.assertIsNone(mapped["salePrice"])
        self.assertIsNone(mapped["assessed"])
        self.assertEqual(mapped["saleDate"], "2017-02-24")
        self.assertEqual(mapped["zoningAttribute"], "GI; RM5")
        self.assertTrue(mapped["appraiserUrl"].endswith("/1541"))

    def test_sales_keep_latest_qualified_only(self) -> None:
        def fetch(_url, params):
            if params.get("resultOffset") != "0":
                return {"features": []}
            return {
                "features": [
                    {
                        "attributes": {
                            "OBJECTID": 1,
                            "XFER_PIN": "6836-42-3032.00          ",
                            "XFER_XFERDATE": 1487894400000,
                            "XFER_SALEPRICE": 10,
                            "XFER_QUALCODE": "DQ",
                        }
                    },
                    {
                        "attributes": {
                            "OBJECTID": 2,
                            "XFER_PIN": "6836-42-3032.000",
                            "XFER_XFERDATE": 1500000000000,
                            "XFER_SALEPRICE": 99,
                            "XFER_QUALCODE": "Q",
                        }
                    },
                    {
                        "attributes": {
                            "OBJECTID": 3,
                            "XFER_PIN": "6836-42-3032.00",
                            "XFER_XFERDATE": 1600000000000,
                            "XFER_SALEPRICE": 50,
                            "XFER_QUALCODE": "Q         ",
                        }
                    },
                ]
            }

        sales = _latest_qualified_sales(fetch, "https://services1.arcgis.com/example/SalesApp_Hosted/FeatureServer/0/query")
        chosen = sales[pin_key("6836-42-3032.00")]
        self.assertEqual(chosen["price"], 50)
        self.assertEqual(chosen["qualified"], "Q")

    def test_spatial_join_prefers_kernersville_and_high_point(self) -> None:
        ke_zone = _index(_square(-80.10, 36.10, -80.06, 36.14, {"ZONING": "RS20"}))
        county = _index(_square(-80.20, 36.00, -80.00, 36.20, {"ZONING_DISTRICT": "AG", "ZONING_JURISDICTION": "KE"}))
        ke_flu = _index(_square(-80.10, 36.10, -80.06, 36.14, {"PROP_LU": "SCHOOL"}))
        limits = _index(_square(-80.10, 36.10, -80.06, 36.14, {"MUNICIPALITY": "KE"}))
        proposed = {
            pin_key("6836-42-3032.00"): {"code": "SFR", "label": "Neighborhood Residential", "areaPlan": "Kernersville"}
        }
        parcel = _parcel(-80.08, 36.12)
        apply_land_use(
            parcel,
            {
                "limits": limits,
                "countyZoning": county,
                "keZoning": ke_zone,
                "hpZoning": SpatialIndex(),
                "keFlu": ke_flu,
                "hpFlu": SpatialIndex(),
                "gma": _index(_square(-80.2, 36.0, -80.0, 36.2, {"GROWTHMANAGEMENTAREA": "5"})),
                "proposed": proposed,
                "sales": {pin_key("6836-42-3032.00"): {"date": "2020-09-13", "price": 50, "qualified": "Q"}},
                "values": {pin_key("6836-42-3032.00"): {"land": 204600, "improve": 0, "total": None}},
            },
        )
        props = parcel["properties"]
        self.assertEqual(props["zoningCode"], "RS20")
        self.assertEqual(props["jurisdictionPrefix"], "Kernersville")
        self.assertEqual(props["situsCity"], "Kernersville")
        self.assertEqual(props["flu"]["source"], "kernersville-land-use-plan")
        self.assertIn("GMA 5 (Rural)", props["flu"]["label"])
        self.assertEqual(props["lastSale"]["price"], 50)
        self.assertEqual(props["tax"]["landValue"], 204600)
        self.assertEqual(props["tax"]["improvementValue"], 0)
        self.assertIsNone(props["tax"]["marketValue"])
        self.assertNotIn("zoningAttribute", props)
        self.assertIn(KE_ZONING, KE_ZONING)

        rural = _parcel(-80.15, 36.05, pinKey="other")
        apply_land_use(
            rural,
            {
                "limits": _index(_square(-80.3, 35.9, -79.9, 36.3, {"MUNICIPALITY": "RH"})),
                "countyZoning": _index(_square(-80.3, 35.9, -79.9, 36.3, {"ZONING_DISTRICT": "AG", "ZONING_JURISDICTION": "FC"})),
                "keZoning": SpatialIndex(),
                "hpZoning": SpatialIndex(),
                "keFlu": SpatialIndex(),
                "hpFlu": SpatialIndex(),
                "gma": _index(_square(-80.3, 35.9, -79.9, 36.3, {"GROWTHMANAGEMENTAREA": "5"})),
                "proposed": {"other": {"code": "RUR", "label": "Rural", "areaPlan": "Rural Hall"}},
                "sales": {},
                "values": {},
            },
        )
        self.assertEqual(rural["properties"]["situsCity"], "Rural Hall")
        self.assertEqual(rural["properties"]["jurisdictionPrefix"], "Forsyth County")
        self.assertEqual(rural["properties"]["zoningCode"], "AG")
        self.assertTrue(any("FC" in gap or "Forsyth County" in gap for gap in rural["properties"]["dataGaps"]))
        self.assertIn("no dedicated FLU", " ".join(rural["properties"]["dataGaps"]))

        tip = _parcel(-80.02, 35.98, pinKey="hp-pin")
        apply_land_use(
            tip,
            {
                "limits": _index(_square(-80.05, 35.95, -79.99, 36.02, {"MUNICIPALITY": "HP"})),
                "countyZoning": _index(_square(-80.05, 35.95, -79.99, 36.02, {"ZONING_DISTRICT": "COUNTY-HP", "ZONING_JURISDICTION": "HP"})),
                "keZoning": SpatialIndex(),
                "hpZoning": _index(_square(-80.05, 35.95, -79.99, 36.02, {"ZONE": "LI", "DIST": "LI"})),
                "keFlu": SpatialIndex(),
                "hpFlu": _index(_square(-80.05, 35.95, -79.99, 36.02, {"PlaceTypes": "Parks - Green Space"})),
                "gma": SpatialIndex(),
                "proposed": {},
                "sales": {},
                "values": {},
            },
        )
        self.assertEqual(tip["properties"]["zoningCode"], "LI")
        self.assertEqual(tip["properties"]["jurisdictionPrefix"], "High Point")
        self.assertEqual(tip["properties"]["flu"]["source"], "highpoint-place-types")
        self.assertIn(HP_ZONING, HP_ZONING)

        bare = _parcel(-80.5, 36.2, pinKey="none", zoningAttribute=None)
        apply_land_use(
            bare,
            {
                "limits": SpatialIndex(),
                "countyZoning": SpatialIndex(),
                "keZoning": SpatialIndex(),
                "hpZoning": SpatialIndex(),
                "keFlu": SpatialIndex(),
                "hpFlu": SpatialIndex(),
                "gma": _index(_square(-81, 36, -80, 37, {"GROWTHMANAGEMENTAREA": "4"})),
                "proposed": {},
                "sales": {},
                "values": {},
            },
        )
        self.assertIsNone(bare["properties"]["flu"])
        self.assertIsNone(bare["properties"]["zoningCode"])

    def test_clemmons_proposed_lu_keeps_category_caveat(self) -> None:
        parcel = _parcel(-80.4, 36.02, pinKey="cl")
        apply_land_use(
            parcel,
            {
                "limits": _index(_square(-80.5, 35.9, -80.3, 36.1, {"MUNICIPALITY": "CL"})),
                "countyZoning": _index(_square(-80.5, 35.9, -80.3, 36.1, {"ZONING_DISTRICT": "RS-20", "ZONING_JURISDICTION": "CL"})),
                "keZoning": SpatialIndex(),
                "hpZoning": SpatialIndex(),
                "keFlu": SpatialIndex(),
                "hpFlu": SpatialIndex(),
                "gma": SpatialIndex(),
                "proposed": {"cl": {"code": "SFR", "label": "Neighborhood Residential", "areaPlan": "Clemmons"}},
                "sales": {},
                "values": {},
            },
        )
        self.assertEqual(parcel["properties"]["flu"]["source"], "forsyth-proposed-lu")
        self.assertEqual(parcel["properties"]["flu"]["jurisdiction"], "Clemmons")
        self.assertNotIn("areaPlan", parcel["properties"]["flu"])
        self.assertTrue(any("Clemmons" in gap for gap in parcel["properties"]["dataGaps"]))
        self.assertIn(FLU_LAYER.split("/rest/")[-1], FLU_LAYER)
        self.assertEqual(SOURCE, "nc-mapforsyth-37067")


if __name__ == "__main__":
    unittest.main()
