import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_drone_manifest import bounds_from_gdalinfo, build_manifest

class DroneManifestTests(unittest.TestCase):
    def test_bounds_order_lat_lon(self):
        data={"wgs84Extent":{"type":"Polygon","coordinates":[[
            [121.65,-4.23],[121.68,-4.23],[121.68,-4.20],[121.65,-4.20],[121.65,-4.23]
        ]]}}
        self.assertEqual(bounds_from_gdalinfo(data),[[-4.23,121.65],[-4.20,121.68]])
        m=build_manifest(data,"Survey 0101","2026-11-21",15,19)
        self.assertEqual(m["maxNativeZoom"],19)
        self.assertEqual(m["bounds"][0][0],-4.23)

    def test_missing_georeference_fails(self):
        with self.assertRaisesRegex(ValueError,"no usable WGS84 extent"):
            bounds_from_gdalinfo({})

    def test_reject_invalid_zoom(self):
        data={"wgs84Extent":{"type":"Polygon","coordinates":[[
            [121,-4],[122,-4],[122,-5],[121,-5],[121,-4]
        ]]}}
        with self.assertRaisesRegex(ValueError,"Zoom range"):
            build_manifest(data,"Bad","",20,15)

if __name__=="__main__":
    unittest.main()
