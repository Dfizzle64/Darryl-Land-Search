import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wake_parcel_enrich import (
    JURISDICTIONS,
    ONEMAP_WHERE,
    PolyIndex,
    appraiser_url,
    epoch_to_iso,
    esri_parts,
    parse_mailing,
    point_in_ring,
)


class WakeParcelEnrichTests(unittest.TestCase):
    def test_mailing_city_line_is_addr2_or_addr3(self):
        local = parse_mailing("108 UTLEY BLUFFS DR", "HOLLY SPRINGS NC 27540-4452", None)
        self.assertEqual(local["line1"], "108 UTLEY BLUFFS DR")
        self.assertIsNone(local["line2"])
        self.assertEqual(local["city"], "HOLLY SPRINGS")
        self.assertEqual(local["state"], "NC")
        self.assertEqual(local["zip"], "27540")

        out_of_state = parse_mailing("JOHNSON BROTHERS LIQUOR CO", "1999 SHEPARD RD", "SAINT PAUL MN 55116-3210")
        self.assertEqual(out_of_state["line1"], "JOHNSON BROTHERS LIQUOR CO")
        self.assertEqual(out_of_state["line2"], "1999 SHEPARD RD")
        self.assertEqual(out_of_state["city"], "SAINT PAUL")
        self.assertEqual(out_of_state["zip"], "55116")

    def test_sale_epoch_ms(self):
        self.assertEqual(epoch_to_iso(1787270400000), "2026-08-21")
        self.assertEqual(epoch_to_iso("2020-01-15T00:00:00Z"), "2020-01-15")
        self.assertIsNone(epoch_to_iso(None))
        self.assertIsNone(epoch_to_iso(0))

    def test_appraiser_keeps_reid(self):
        self.assertEqual(
            appraiser_url("0022383"),
            "https://services.wakegov.com/realestate/Account.asp?id=0022383",
        )
        self.assertEqual(appraiser_url(None), "https://services.wakegov.com/realestate/")

    def test_onemap_filter_uses_cntyfips(self):
        self.assertIn("cntyfips='183'", ONEMAP_WHERE)

    def test_raleigh_zoning_is_mapserver_23(self):
        self.assertEqual(JURISDICTIONS["RA"]["zoning"]["layer"], 23)
        self.assertNotIn("flu", JURISDICTIONS["RO"])
        self.assertNotIn("flu", JURISDICTIONS["ZB"])
        self.assertIn("fluGap", JURISDICTIONS["RO"])
        self.assertIn("fluGap", JURISDICTIONS["ZB"])
        self.assertFalse(JURISDICTIONS["KN"]["flu"]["geometry"])

    def test_point_in_clockwise_ring(self):
        ring = [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]
        self.assertLess(sum(
            ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1] for i in range(len(ring) - 1)
        ), 0)
        self.assertTrue(point_in_ring(0.5, 0.5, ring))
        self.assertFalse(point_in_ring(1.5, 0.5, ring))
        parts = esri_parts({"rings": [ring]}, outer_negative=True)
        self.assertEqual(len(parts), 1)
        index = PolyIndex(cell=1)
        index.add({"rings": [ring]}, "R-40", outer_negative=True)
        self.assertEqual(index.hit(0.2, 0.2), "R-40")
        self.assertIsNone(index.hit(2, 2))


if __name__ == "__main__":
    unittest.main()
