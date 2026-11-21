"""DXF importer smoke tests using synthetic CAD; no client drawings committed."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cad_parcels_to_geojson as importer


class CADImportTests(unittest.TestCase):
    def test_valid_closed_polygons_only(self):
        with tempfile.TemporaryDirectory() as root:
            input_file = Path(root) / "synthetic.dxf"
            doc = ezdxf.new("R2013")
            space = doc.modelspace()
            space.add_lwpolyline(
                [(106.811, -6.310), (106.812, -6.310), (106.812, -6.311), (106.811, -6.311)],
                close=True, dxfattribs={"layer": "PARCEL"}
            )
            space.add_lwpolyline(
                [(106.812, -6.310), (106.813, -6.310), (106.813, -6.311)],
                close=False, dxfattribs={"layer": "PARCEL"}
            )
            space.add_line((0, 0), (1, 1), dxfattribs={"layer": "PARCEL"})
            space.add_lwpolyline(
                [(106.81, -6.31), (106.82, -6.31), (106.82, -6.32)],
                close=True, dxfattribs={"layer": "OTHER"}
            )
            doc.saveas(input_file)
            fc, matched, skipped = importer.convert(input_file, "EPSG:4326", ["PARCEL"])
            self.assertEqual(fc["type"], "FeatureCollection")
            self.assertEqual(matched, 3)
            self.assertEqual(len(fc["features"]), 1)
            self.assertEqual(skipped["open polyline"], 1)
            feature = fc["features"][0]
            self.assertEqual(feature["properties"]["status"], "UNVERIFIED")
            self.assertTrue(feature["properties"]["area_m2"] > 0)
            self.assertEqual(feature["geometry"]["coordinates"][0][0],
                             feature["geometry"]["coordinates"][0][-1])

    def test_repeated_endpoint_without_closed_bit_and_curved_bulge(self):
        with tempfile.TemporaryDirectory() as root:
            input_file = Path(root) / "bulge.dxf"
            doc = ezdxf.new("R2013")
            doc.modelspace().add_lwpolyline(
                [(500000, 9530100, 0, 0, 0),
                 (500080, 9530100, 0, 0, 0.4),
                 (500080, 9530180, 0, 0, 0),
                 (500000, 9530180, 0, 0, 0),
                 (500000, 9530100, 0, 0, 0)],
                format="xyseb",
                close=False,
                dxfattribs={"layer": "PARCEL"}
            )
            doc.saveas(input_file)
            fc, matched, skipped = importer.convert(input_file, "EPSG:32751", ["PARCEL"])
            self.assertEqual(matched, 1)
            self.assertEqual(len(fc["features"]), 1)
            self.assertFalse(skipped)
            coords = fc["features"][0]["geometry"]["coordinates"][0]
            self.assertGreater(len(coords), 5, "Bulge arc must be tessellated")
            self.assertEqual(coords[0], coords[-1])
            self.assertGreater(fc["features"][0]["properties"]["area_m2"], 0)

    def test_requires_nonempty_matching_layer(self):
        with tempfile.TemporaryDirectory() as root:
            input_file = Path(root) / "empty.dxf"
            doc = ezdxf.new("R2013")
            doc.modelspace().add_line((0, 0), (1, 1), dxfattribs={"layer": "ROAD"})
            doc.saveas(input_file)
            with self.assertRaisesRegex(ValueError, "No modelspace entities"):
                importer.convert(input_file, "EPSG:4326", ["PARCEL"])


if __name__ == "__main__":
    unittest.main()
