#!/usr/bin/env python3
"""Pure checks for Wave 0 South Florida. No network."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from south_florida_parcels import (  # noqa: E402
    BROWARD_FDOR,
    BROWARD_PARCELS,
    FIPS,
    MAX_ACRES,
    MIN_ACRES,
    REJECTED_URLS,
    SPECS,
    acres_from_sqft,
    appraiser_url,
    gis_viewer_url,
    in_band,
    in_county,
    miami_where,
    rejected_url,
    south_florida_spec,
    usable_code,
)


def test_four_counties_and_acre_band() -> None:
    assert FIPS == ("12086", "12011", "12099")
    assert "12087" not in FIPS
    assert MIN_ACRES == 5.0 and MAX_ACRES == 150.0
    assert in_band(5) and in_band(150) and not in_band(4.999) and not in_band(150.001)
    assert acres_from_sqft(217800) == 5
    assert acres_from_sqft(6534000) == 150
    assert in_county("12086", -80.2846, 25.7020)
    assert in_county("12087", -81.8042, 24.5624)
    assert not in_county("12087", -77.6, 43.15)
    assert in_county("12011", -80.231, 26.333)
    assert in_county("12099", -80.145, 26.646)


def test_cards_are_the_source_urls() -> None:
    assert SPECS["12086"]["url"] == "https://gisweb.miamidade.gov/arcgis/rest/services/MD_LandInformation/MapServer/26/query"
    assert SPECS["12086"]["layerId"] == 26
    assert SPECS["12086"]["status"] == "live"
    assert SPECS["12087"]["url"].endswith("/Parcels/MapServer/0/query")
    assert SPECS["12011"]["status"] == "partial"
    assert SPECS["12011"]["url"] == BROWARD_PARCELS
    assert SPECS["12011"]["camaUrl"] == BROWARD_FDOR
    assert "CO_NO=16" in " ".join(SPECS["12011"]["gaps"])
    assert SPECS["12099"]["url"].endswith("/PARCEL_INFO/FeatureServer/4/query")
    assert SPECS["12099"]["layerId"] == 4
    for fips in FIPS:
        spec = south_florida_spec(fips)
        assert spec["kind"] == "south-florida"
        assert rejected_url(spec["url"]) is None
        assert "BMSDParcelAddress" not in spec["url"]


def test_deep_links_and_rejected_hosts() -> None:
    miami = appraiser_url("12086", "30-4131-053-0060")
    assert miami == "https://apps.miamidadepa.gov/ComparableSales/#/?folio=3041310530060"
    assert "PropertySearch" not in miami
    monroe = appraiser_url("12087", "00000010-000200")
    assert "AppID=605" in monroe and "KeyValue=00000010-000200" in monroe
    assert appraiser_url("12011", "474135010090").startswith("https://bcpa.net/RecInfo.asp?URL_Folio=")
    palm = appraiser_url("12099", "18424415160010010")
    assert palm.startswith("https://pbcpao.gov/Property/Details?parcelId=")
    assert "papa" not in palm
    for needle in ("maps.monroecounty.gov", "gis.bcpa.net", "pbcgov.org/papa", "BMSDParcelAddress"):
        assert needle in REJECTED_URLS
    assert gis_viewer_url("12086", "MIAMI", zoned=True).endswith("/MapServer/19")
    assert gis_viewer_url("12086", "Unincorporated", zoned=True).endswith("/MapServer/18")
    assert gis_viewer_url("12086", None, zoned=False).endswith("/MapServer/26")
    assert gis_viewer_url("12087", "Monroe", zoned=True).endswith("/APO_GIS/MapServer/19")
    assert "Broward_Municipal_Service_District_Zoning/FeatureServer/2" in gis_viewer_url(
        "12011", "Unincorporated", zoned=True
    )
    assert gis_viewer_url("12011", "Broward municipal mosaic", zoned=True).endswith("/MapServer/9")
    assert gis_viewer_url("12099", "Unincorporated", zoned=True).endswith("/MapServer/9")
    assert gis_viewer_url("12099", None, zoned=False).endswith("/FeatureServer/4")
    assert "/query" not in gis_viewer_url("12011", None, zoned=False)


def test_primary_zone_and_blank_codes_are_not_zoning() -> None:
    assert "PRIMARY_ZONE" in " ".join(SPECS["12086"]["gaps"])
    assert usable_code("PRIMARY_ZONE") == "PRIMARY_ZONE"
    assert usable_code("N/A") is None
    assert usable_code("WATER") is None
    assert usable_code("RU-4") == "RU-4"
    assert "LOT_SIZE" in miami_where()
    assert "5.0" in " ".join(SPECS["12086"]["gaps"]) or "5.0–150.0" in " ".join(SPECS["12086"]["gaps"])
    joined = " ".join(" ".join(SPECS[fips]["gaps"]) for fips in FIPS)
    assert "Opportunity Zone" not in joined
    assert "school" not in joined.lower()
    assert "base flood" not in joined.lower()


if __name__ == "__main__":
    test_four_counties_and_acre_band()
    test_cards_are_the_source_urls()
    test_deep_links_and_rejected_hosts()
    test_primary_zone_and_blank_codes_are_not_zoning()
    print("south florida guards ok")
