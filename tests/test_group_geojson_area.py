"""Unit tests for explicit multi-part Area grouping."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from group_geojson_area import group_area


def feature(code, min_lon, min_lat, width=0.0005):
    ring=[
        [min_lon,min_lat],[min_lon+width,min_lat],
        [min_lon+width,min_lat+width],[min_lon,min_lat+width],
        [min_lon,min_lat]
    ]
    return {"type":"Feature", "properties":{"code":code,"cad_handle":code},
            "geometry":{"type":"Polygon","coordinates":[ring]}}


class GroupAreaTests(unittest.TestCase):
    def test_two_disjoint_polygons_become_one_area(self):
        source={"type":"FeatureCollection","features":[
            feature("A",121.67,-4.24),feature("B",121.68,-4.23)
        ]}
        result=group_area(source,"0101","0101 WORKSHOP AND OFFICE AREA")
        self.assertEqual(len(result["features"]),1)
        feat=result["features"][0]
        self.assertEqual(feat["geometry"]["type"],"MultiPolygon")
        self.assertEqual(len(feat["geometry"]["coordinates"]),2)
        self.assertEqual(feat["properties"]["code"],"0101")
        self.assertEqual(feat["properties"]["geometry_parts"],2)
        self.assertGreater(feat["properties"]["area_m2"],0)

    def test_reject_overlap_and_single_feature(self):
        source={"type":"FeatureCollection","features":[
            feature("A",121.67,-4.24),feature("B",121.6702,-4.2398)
        ]}
        with self.assertRaisesRegex(ValueError,"invalid"):
            group_area(source,"0101","Test")
        with self.assertRaisesRegex(ValueError,"at least two"):
            group_area({"type":"FeatureCollection","features":source["features"][:1]},"0101","Test")


if __name__=="__main__":
    unittest.main()
